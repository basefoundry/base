from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .project_config import ProjectConfig
from .project_item_fields import FieldCopySummary
from .project_model import ConfigureAction
from .project_model import FieldUpdate
from .project_model import Finding
from .project_model import OwnerInfo
from .project_model import ProjectArguments
from .project_model import ProjectField
from .project_model import ProjectInfo
from .project_model import ProjectSchema
from .project_model import ProjectView
from .project_model import SelectFieldSpec


class ConfigurationPlan(Protocol):
    def __call__(
        self,
        *,
        project_exists: bool,
        fields: tuple[ProjectField, ...],
        schema: ProjectSchema,
    ) -> tuple[ConfigureAction, ...]:
        """Plan Project configuration changes."""


class ResolveIssueFieldUpdates(Protocol):
    def __call__(
        self,
        fields: tuple[ProjectField, ...],
        values: dict[str, str],
        *,
        project_title: str,
    ) -> tuple[FieldUpdate, ...]:
        """Resolve issue field updates from command arguments."""


class UpdateProject(Protocol):
    def __call__(
        self,
        project_id: str,
        *,
        title: str | None = None,
        closed: bool | None = None,
    ) -> None:
        """Update mutable GitHub Project metadata."""


@dataclass(frozen=True)
class ProjectOperations:
    """Typed operations surface passed to GitHub Project command helpers."""

    ProjectError: type[Exception]
    ProjectUsageError: type[Exception]
    add_project_item: Callable[[str, str], str]
    apply_missing_project_item_defaults: Callable[[str, tuple[ProjectField, ...], dict[str, str]], FieldCopySummary]
    backfill_repository_issues: Callable[[str, str], int]
    compare_schema: Callable[[tuple[ProjectField, ...], ProjectSchema], tuple[Finding, ...]]
    configuration_plan: ConfigurationPlan
    copy_missing_project_item_fields: Callable[[str, str], FieldCopySummary]
    copy_template_project: Callable[[str, str, str], ProjectInfo]
    create_project: Callable[[str, str], ProjectInfo]
    create_single_select_field: Callable[[str, SelectFieldSpec], None]
    fetch_issue_id: Callable[[str, str, int], str]
    fetch_project_fields: Callable[[str], tuple[ProjectField, ...]]
    fetch_project_views: Callable[[str], tuple[ProjectView, ...]]
    find_owner_and_project: Callable[[str, str], OwnerInfo]
    find_project_item_id: Callable[[str, str], str | None]
    issue_field_values_for_args: Callable[[ProjectArguments], dict[str, str]]
    link_project_to_repository: Callable[[str, str], None]
    missing_option_names: Callable[[ProjectField, SelectFieldSpec], tuple[str, ...]]
    project_config_for_args: Callable[[ProjectArguments], ProjectConfig]
    project_field_defaults_for_config: Callable[[ProjectConfig], dict[str, str]]
    require_owner: Callable[[ProjectArguments], str]
    require_repo: Callable[[ProjectArguments], str]
    resolve_issue_field_updates: ResolveIssueFieldUpdates
    schema_for_args: Callable[[ProjectArguments], ProjectSchema]
    split_repo: Callable[[str], tuple[str, str]]
    update_item_field: Callable[[str, str, FieldUpdate], None]
    update_project: UpdateProject
    update_single_select_field: Callable[[ProjectField, SelectFieldSpec], None]
    verify_standard_template_views: Callable[[tuple[ProjectView, ...]], None]
