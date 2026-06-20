from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .project_config import ProjectConfig
from .project_model import (
    DEFAULT_TEMPLATE_PROJECT,
    FIELD_OPTION_TO_PROJECT_FIELD,
    STANDARD_TEMPLATE_VIEWS,
    ConfigureAction,
    ProjectArguments,
    ProjectInfo,
    ProjectView,
)


@dataclass(frozen=True)
class ProjectReplacement:
    legacy_project: ProjectInfo
    legacy_title: str
    view_errors: tuple[str, ...]


@dataclass(frozen=True)
class ConfigureDryRunPlan:
    actions: tuple[ConfigureAction, ...]
    would_copy_template: bool = False
    replacement: ProjectReplacement | None = None
    project_config: ProjectConfig | None = None


def standard_template_view_errors(views: tuple[ProjectView, ...]) -> tuple[str, ...]:
    by_name = {view.name: view for view in views}
    errors: list[str] = []
    for expected in STANDARD_TEMPLATE_VIEWS:
        actual = by_name.get(expected.name)
        if actual is None:
            errors.append(f"{expected.name} view is missing")
        elif actual.layout != expected.layout:
            errors.append(f"{expected.name} view has layout {actual.layout}; expected {expected.layout}")
    return tuple(errors)


def legacy_project_title(project_title: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{project_title}-legacy-{timestamp}"


def render_dry_run_configure(args: ProjectArguments, plan: ConfigureDryRunPlan) -> None:
    print(
        f"[DRY-RUN] Would configure GitHub Project '{args.project_title}' "
        f"for '{args.repo or args.owner or ''}' with --schema {args.schema}."
    )
    if plan.replacement is not None:
        render_replacement_dry_run(args, plan.replacement)
    elif plan.would_copy_template:
        print(f"[DRY-RUN] Would copy GitHub Project '{DEFAULT_TEMPLATE_PROJECT}' to '{args.project_title}'.")
    if args.repo:
        print(f"[DRY-RUN] Would link GitHub Project '{args.project_title}' to repository '{args.repo}'.")
        print(f"[DRY-RUN] Would backfill issues from '{args.repo}' into GitHub Project '{args.project_title}'.")
    if args.copy_fields_from_project:
        print(f"[DRY-RUN] Would copy missing item field values from GitHub Project '{args.copy_fields_from_project}'.")
    if args.config_path:
        print(f"[DRY-RUN] Would read GitHub Project config from '{args.config_path}'.")
    render_project_config_dry_run(plan.project_config or ProjectConfig())
    print("[DRY-RUN] Fields: Status, Priority, Area, Size, Initiative")
    if args.initiative_options:
        for option in args.initiative_options:
            print(f"[DRY-RUN] Would ensure Initiative option {option}.")
    for action in plan.actions:
        print(f"[DRY-RUN] Would {action.message}")


def render_replacement_dry_run(args: ProjectArguments, replacement: ProjectReplacement) -> None:
    print(f"[DRY-RUN] Would replace existing GitHub Project '{args.project_title}'.")
    for error in replacement.view_errors:
        print(f"[DRY-RUN] Existing Project view mismatch: {error}.")
    print(f"[DRY-RUN] Would rename existing GitHub Project '{args.project_title}' to '{replacement.legacy_title}'.")
    print(f"[DRY-RUN] Would copy GitHub Project '{DEFAULT_TEMPLATE_PROJECT}' to '{args.project_title}'.")
    print(
        f"[DRY-RUN] Would copy missing item field values from legacy GitHub Project "
        f"'{replacement.legacy_title}' into '{args.project_title}'."
    )
    print(f"[DRY-RUN] Would close legacy GitHub Project '{replacement.legacy_title}' after replacement succeeds.")


def render_project_config_dry_run(config: ProjectConfig) -> None:
    for option in config.areas:
        print(f"[DRY-RUN] Would ensure Area option {option}.")
    for option in config.initiatives:
        print(f"[DRY-RUN] Would ensure Initiative option {option}.")
    if config.issue_defaults:
        rendered = ", ".join(
            f"{FIELD_OPTION_TO_PROJECT_FIELD[key]}={value}"
            for key, value in config.issue_defaults.items()
            if key in FIELD_OPTION_TO_PROJECT_FIELD
        )
        print(f"[DRY-RUN] Would apply issue defaults to missing Project item fields: {rendered}.")
