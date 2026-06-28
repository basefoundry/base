from __future__ import annotations

import fnmatch
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli.paths import discover_manifest
from base_setup.github_manifest import GithubPrConfig
from base_setup.manifest import ManifestError, read_manifest


class PrPolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrPolicyInputs:
    issue_number: int | None = None
    labels: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    template_body: str | None = None
    project_root: Path | None = None


def render_pr_body(policy: GithubPrConfig, inputs: PrPolicyInputs) -> str:
    body = _template_body(policy, inputs).rstrip()
    section_names = required_section_names(policy, labels=inputs.labels, paths=inputs.paths)
    existing_sections = _existing_section_names(body)
    issue_link_added = _has_issue_link(body, inputs.issue_number)

    blocks = [body] if body else []
    for section_name in section_names:
        normalized_name = _normalize_section_name(section_name)
        if normalized_name in existing_sections:
            continue
        if normalized_name == "issue" and inputs.issue_number is not None:
            blocks.append(f"## {section_name}\n\nFixes #{inputs.issue_number}")
            issue_link_added = True
        else:
            blocks.append(f"## {section_name}")
        existing_sections.add(normalized_name)

    if inputs.issue_number is not None and not issue_link_added:
        blocks.append(f"Fixes #{inputs.issue_number}")

    if not blocks:
        return ""
    return "\n\n".join(blocks).rstrip() + "\n"


def required_section_names(
    policy: GithubPrConfig,
    *,
    labels: tuple[str, ...] = (),
    paths: tuple[str, ...] = (),
) -> tuple[str, ...]:
    sections: list[str] = list(policy.required_sections.default)
    normalized_labels = {_normalize_label(label) for label in labels}

    for label, label_sections in policy.required_sections.labels.items():
        if _normalize_label(label) in normalized_labels:
            sections.extend(label_sections)

    for path_pattern, path_sections in policy.required_sections.paths.items():
        if any(fnmatch.fnmatchcase(path, path_pattern) for path in paths):
            sections.extend(path_sections)

    return _dedupe_section_names(sections)


def body_from_manifest(
    manifest_path: Path,
    *,
    issue_number: int | None = None,
    labels: tuple[str, ...] = (),
    paths: tuple[str, ...] = (),
) -> str:
    manifest = read_manifest(manifest_path)
    if manifest.github.pr is None:
        return f"Fixes #{issue_number}\n" if issue_number is not None else ""
    return render_pr_body(
        manifest.github.pr,
        PrPolicyInputs(
            issue_number=issue_number,
            labels=labels,
            paths=paths,
            project_root=manifest.path.parent,
        ),
    )


app = base_cli.App(
    name="base_pr_policy",
    help="Render Base-managed GitHub pull request policy content.",
)


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("command", required=False)
@base_cli.option("--manifest", help="Path to base_manifest.yaml.")
@base_cli.option("--issue", type=int, help="Issue number to link with Fixes #<number>.")
@base_cli.option("--label", "labels", multiple=True, help="Issue or PR label name.")
@base_cli.option("--path", "paths", multiple=True, help="Changed path relative to the repo root.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    command: str | None,
    manifest: str | None,
    issue: int | None,
    labels: tuple[str, ...],
    paths: tuple[str, ...],
) -> int:
    if command != "body":
        ctx.log.error("Expected command 'body'.")
        return base_cli.ExitCode.USAGE_ERROR
    manifest_path = Path(manifest).expanduser().resolve() if manifest else discover_manifest(Path.cwd())
    if manifest_path is None:
        ctx.log.error("No base_manifest.yaml found from the current directory upward.")
        return base_cli.ExitCode.USAGE_ERROR
    try:
        body = body_from_manifest(
            manifest_path,
            issue_number=issue,
            labels=labels,
            paths=paths,
        )
    except (ManifestError, PrPolicyError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE
    sys.stdout.write(body)
    return base_cli.ExitCode.SUCCESS


def _template_body(policy: GithubPrConfig, inputs: PrPolicyInputs) -> str:
    if inputs.template_body is not None:
        return inputs.template_body
    if policy.template is None:
        return ""
    if inputs.project_root is None:
        return ""

    project_root = inputs.project_root.resolve()
    template_path = (project_root / policy.template).resolve()
    try:
        template_path.relative_to(project_root)
    except ValueError as exc:
        raise PrPolicyError(f"{policy.template}: PR template must stay inside the project root.") from exc
    try:
        return template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PrPolicyError(f"{template_path}: unable to read PR template: {exc}") from exc


def _existing_section_names(body: str) -> set[str]:
    names: set[str] = set()
    for line in body.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*(?:#+\s*)?$", line)
        if match:
            names.add(_normalize_section_name(match.group(1)))
    return names


def _has_issue_link(body: str, issue_number: int | None) -> bool:
    if issue_number is None:
        return False
    pattern = re.compile(rf"\b(?:Fixes|Closes|Resolves)\s+#{issue_number}\b", re.IGNORECASE)
    return bool(pattern.search(body))


def _dedupe_section_names(sections: list[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for section in sections:
        normalized = _normalize_section_name(section)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(section)
    return tuple(deduped)


def _normalize_label(label: str) -> str:
    return label.strip().casefold()


def _normalize_section_name(section_name: str) -> str:
    return re.sub(r"\s+", " ", section_name.strip()).casefold()
