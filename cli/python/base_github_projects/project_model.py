from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SelectOption:
    name: str
    color: str
    description: str
    option_id: str | None = None


@dataclass(frozen=True)
class SelectFieldSpec:
    name: str
    options: tuple[SelectOption, ...]


@dataclass(frozen=True)
class ProjectSchema:
    fields: tuple[SelectFieldSpec, ...]

    def field_by_name(self, name: str) -> SelectFieldSpec:
        for field in self.fields:
            if field.name == name:
                return field
        raise KeyError(name)


@dataclass(frozen=True)
class ProjectField:
    field_id: str
    name: str
    data_type: str
    options: tuple[SelectOption, ...] = ()


@dataclass(frozen=True)
class Finding:
    status: str
    name: str
    message: str


@dataclass(frozen=True)
class ConfigureAction:
    action: str
    name: str
    message: str


@dataclass(frozen=True)
class FieldUpdate:
    field_id: str
    option_id: str
    field_name: str
    option_name: str


@dataclass(frozen=True)
class ProjectInfo:
    project_id: str
    title: str


@dataclass(frozen=True)
class ProjectView:
    name: str
    layout: str


@dataclass(frozen=True)
class OwnerInfo:
    owner_id: str
    login: str
    project: ProjectInfo | None


@dataclass(frozen=True)
class ProjectArguments:
    area: str
    command: str
    project_title: str | None = None
    owner: str | None = None
    repo: str | None = None
    schema: str = "base-project"
    config_path: str | None = None
    copy_fields_from_project: str | None = None
    initiative_options: tuple[str, ...] = ()
    replace_project: bool = False
    dry_run: bool = False
    issue_number: int | None = None
    field_values: dict[str, str] | None = None


BASE_PROJECT_SCHEMA = ProjectSchema(
    fields=(
        SelectFieldSpec(
            "Status",
            (
                SelectOption("Triage", "GRAY", "Needs clarification or initial classification."),
                SelectOption("Backlog", "BLUE", "Accepted but not yet scheduled."),
                SelectOption("Ready", "GREEN", "Scoped enough to pick up."),
                SelectOption("In Progress", "YELLOW", "Actively being worked on."),
                SelectOption("In Review", "ORANGE", "Pull request open, waiting on checks or review."),
                SelectOption("Done", "PURPLE", "Completed or no further work remains."),
            ),
        ),
        SelectFieldSpec(
            "Priority",
            (
                SelectOption("P0", "RED", "Urgent or blocking."),
                SelectOption("P1", "ORANGE", "High priority."),
                SelectOption("P2", "YELLOW", "Normal priority."),
                SelectOption("P3", "BLUE", "Low priority or opportunistic."),
            ),
        ),
        SelectFieldSpec(
            "Area",
            (
                SelectOption("CLI", "GRAY", "Command surface and user-facing CLI behavior."),
                SelectOption("Setup", "GRAY", "Installation, setup, check, and doctor behavior."),
                SelectOption("Workspace", "GRAY", "Workspace discovery and workspace-level commands."),
                SelectOption("Manifest", "GRAY", "Manifest schema and project contract handling."),
                SelectOption("Runtime", "GRAY", "Activation, shell runtime, and environment behavior."),
                SelectOption("Shell", "GRAY", "Shell libraries, completions, and startup files."),
                SelectOption("Python", "GRAY", "Python command packages and shared Python helpers."),
                SelectOption("Docs", "GRAY", "Documentation and AI context."),
                SelectOption("CI", "GRAY", "Continuous integration and validation automation."),
                SelectOption("Packaging", "GRAY", "Release, Homebrew, installer, and distribution work."),
                SelectOption("Security", "GRAY", "Permission, secret-handling, and hardening work."),
                SelectOption("Product", "GRAY", "Product direction, roadmap, and adoption work."),
            ),
        ),
        SelectFieldSpec(
            "Size",
            (
                SelectOption("T", "BLUE", "Tiny, obvious change with no cross-module behavior."),
                SelectOption("S", "GREEN", "Small, focused change."),
                SelectOption("M", "YELLOW", "Medium change with multiple files or interactions."),
                SelectOption("L", "ORANGE", "Large change that should be split if possible."),
            ),
        ),
        SelectFieldSpec(
            "Initiative",
            (
                SelectOption("BanyanLabs Dogfood", "GRAY", "Dogfood Base through BanyanLabs."),
                SelectOption("Workspace Handling", "GRAY", "Workspace discovery and orchestration."),
                SelectOption("pyproject/uv", "GRAY", "Python packaging and uv integration."),
                SelectOption("v1.0 Readiness", "GRAY", "Stable public release readiness."),
                SelectOption("Adoption Polish", "GRAY", "Install, docs, and adoption polish."),
            ),
        ),
    )
)

DEFAULT_TEMPLATE_PROJECT = "base-project-template"
STANDARD_TEMPLATE_VIEWS = (
    ProjectView("Backlog", "TABLE_LAYOUT"),
    ProjectView("Board", "BOARD_LAYOUT"),
    ProjectView("By Status", "TABLE_LAYOUT"),
    ProjectView("Roadmap", "ROADMAP_LAYOUT"),
)
FIELD_OPTION_TO_PROJECT_FIELD = {
    "status": "Status",
    "priority": "Priority",
    "area": "Area",
    "initiative": "Initiative",
    "size": "Size",
}
