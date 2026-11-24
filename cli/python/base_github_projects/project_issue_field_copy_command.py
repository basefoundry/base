from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import base_cli

from .project_model import FieldUpdate, ProjectArguments, ProjectField, ProjectIssueData
from .project_operations import ProjectOperations


PRIORITY_FORWARD = {"P0": "Urgent", "P1": "High", "P2": "Medium", "P3": "Low"}
EFFORT_FORWARD = {"T": "Tiny", "S": "Small", "M": "Medium", "L": "Large"}
PRIORITY_REVERSE = {value: key for key, value in PRIORITY_FORWARD.items()}
EFFORT_REVERSE = {value: key for key, value in EFFORT_FORWARD.items()}


def copy_issue_fields_command(args: ProjectArguments, ops: ProjectOperations) -> int:
    owner = ops.require_owner(args)
    owner_info = ops.find_owner_and_project(owner, args.project_title or "")
    if owner_info.project is None:
        raise ops.ProjectError(f"Project '{args.project_title}' was not found for owner '{owner}'.")
    project = owner_info.project
    items = ops.fetch_project_issue_items(project.project_id)
    fields = ops.fetch_project_fields(project.project_id)
    direction = args.copy_direction or ""
    if direction not in {"project-to-issue", "issue-to-project"}:
        raise ops.ProjectUsageError("Copy direction must be project-to-issue or issue-to-project.")

    try:
        plan = make_copy_plan(items, fields, direction, project_title=project.title)
    except ValueError as exc:
        raise ops.ProjectUsageError(str(exc)) from exc
    changed_items = [row for row in plan if row["changes"]]
    if args.write:
        if not args.export_path:
            raise ops.ProjectUsageError("--write requires --export <path> for the before-state snapshot.")
        try:
            write_before_state(Path(args.export_path), project, direction, items)
        except OSError as exc:
            raise ops.ProjectUsageError(f"Could not write before-state export '{args.export_path}': {exc}.") from exc
        field_ids_by_owner: dict[str, dict[str, int]] = {}
        for row in changed_items:
            item = row["item"]
            if direction == "project-to-issue":
                repo_owner = item.repository.split("/", 1)[0]
                if repo_owner not in field_ids_by_owner:
                    field_ids_by_owner[repo_owner] = ops.organization_issue_field_ids(repo_owner)
                field_ids = field_ids_by_owner[repo_owner]
                ops.write_issue_field_values(
                    repo_owner,
                    item.repository,
                    item.number,
                    row["changes"],
                    field_ids=field_ids,
                )
            else:
                for update in row["changes"]:
                    ops.update_item_field(project.project_id, item.item_id, update)
        items = ops.fetch_project_issue_items(project.project_id)
        try:
            plan = make_copy_plan(items, fields, direction, project_title=project.title)
        except ValueError as exc:
            raise ops.ProjectUsageError(str(exc)) from exc

    report(plan, direction, dry_run=not args.write)
    has_write_mismatch = any(row["mismatches"] for row in plan) and args.write
    return base_cli.ExitCode.FAILURE if has_write_mismatch else base_cli.ExitCode.SUCCESS


def make_copy_plan(
    items: tuple[ProjectIssueData, ...],
    fields: tuple[ProjectField, ...],
    direction: str,
    *,
    project_title: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        if direction == "project-to-issue":
            source = {
                "Priority": first_value(item.project_values, "Legacy priority", "Priority"),
                "Effort": first_value(item.project_values, "Legacy size", "Size"),
            }
            expected = {
                name: mapped_value(value, PRIORITY_FORWARD if name == "Priority" else EFFORT_FORWARD, item, name)
                for name, value in source.items()
                if value
            }
            changes = {
                name: value for name, value in expected.items()
                if item.issue_values.get(name) != value
            }
            actual = dict(item.issue_values)
            actual.update(changes if direction == "project-to-issue" else {})
            mismatches = [
                {"field": name, "expected": value, "actual": item.issue_values.get(name, "")}
                for name, value in expected.items()
                if item.issue_values.get(name) != value
            ]
        else:
            source = {
                "Priority": item.issue_values.get("Priority", ""),
                "Effort": item.issue_values.get("Effort", ""),
            }
            target_names = {
                "Priority": project_field_name(fields, "Legacy priority", "Priority", project_title),
                "Effort": project_field_name(fields, "Legacy size", "Size", project_title),
            }
            expected = {
                target_names[name]: mapped_value(
                    value, PRIORITY_REVERSE if name == "Priority" else EFFORT_REVERSE, item, name
                )
                for name, value in source.items()
                if value
            }
            changes: list[FieldUpdate] = []
            mismatches = []
            for name, value in expected.items():
                field = next(field for field in fields if field.name == name)
                option = next((option for option in field.options if option.name == value), None)
                if option is None or option.option_id is None:
                    raise ValueError(f"Project field '{name}' has no option '{value}'.")
                actual_value = item.project_values.get(name, "")
                if actual_value != value:
                    changes.append(FieldUpdate(field.field_id, option.option_id, name, value))
                    mismatches.append({"field": name, "expected": value, "actual": actual_value})
            actual = dict(item.project_values)
            for update in changes:
                actual[update.field_name] = update.option_name
        rows.append(
            {
                "item": item,
                "expected": expected,
                "actual": actual,
                "changes": changes,
                "mismatches": mismatches,
            }
        )
    return rows


def first_value(values: dict[str, str], *names: str) -> str:
    for name in names:
        if values.get(name):
            return values[name]
    return ""


def project_field_name(fields: tuple[ProjectField, ...], preferred: str, fallback: str, title: str) -> str:
    names = {field.name for field in fields}
    if preferred in names:
        return preferred
    if fallback in names:
        return fallback
    raise ValueError(f"Project '{title}' is missing '{preferred}' and '{fallback}' fields.")


def mapped_value(value: str, mapping: dict[str, str], item: ProjectIssueData, field: str) -> str:
    if value in mapping:
        return mapping[value]
    # A repeated copy can encounter already-migrated values on either side.
    if value in set(mapping.values()):
        return value
    raise ValueError(f"{item.repository}#{item.number} has unmapped {field} value '{value}'.")


def write_before_state(path: Path, project: Any, direction: str, items: tuple[ProjectIssueData, ...]) -> None:
    snapshot = {
        "format": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "project": {"title": project.title, "id": project.project_id},
        "direction": direction,
        "items": [
            {
                "repository": item.repository,
                "issue_number": item.number,
                "issue_id": item.issue_id,
                "project_item_id": item.item_id,
                "title": item.title,
                "project_values": item.project_values,
                "issue_values": item.issue_values,
            }
            for item in items
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(snapshot, stream, indent=2, sort_keys=True)
        stream.write("\n")


def report(rows: list[dict[str, Any]], direction: str, *, dry_run: bool) -> None:
    target_fields = (
        ("Priority", "Effort")
        if direction == "project-to-issue"
        else ("Legacy priority", "Legacy size", "Priority", "Size")
    )
    pending = sum(len(row["changes"]) for row in rows)
    mismatch_count = sum(len(row["mismatches"]) for row in rows)
    print(f"Direction: {direction}")
    print(f"Mode: {'dry run' if dry_run else 'write'}")
    print(f"Items scanned: {len(rows)}")
    print(f"Values to change: {pending if dry_run else 0}")
    print("Per-value counts:")
    for field in target_fields:
        counts = Counter(
            row["actual"][field]
            for row in rows
            if field in row["actual"] and row["actual"][field]
        )
        if counts:
            print(f"  {field}: " + ", ".join(f"{name}={count}" for name, count in sorted(counts.items())))
    if dry_run:
        print("Readback mismatches: not checked (dry run)")
        print("No values were written. Pass --write --export <path> to save the before-state and apply differences.")
    else:
        print(f"Readback mismatches: {mismatch_count}")
        for row in rows:
            item = row["item"]
            for mismatch in row["mismatches"]:
                print(
                    f"  {item.repository}#{item.number} {mismatch['field']}: "
                    f"expected {mismatch['expected']!r}, read {mismatch['actual']!r}"
                )
        if mismatch_count == 0:
            print("Readback verified with zero mismatches.")
        else:
            print("Keep the before-state export and investigate before cutover.", file=sys.stderr)
