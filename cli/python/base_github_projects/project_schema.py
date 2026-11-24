from __future__ import annotations

from pathlib import Path

import base_cli

from base_projects.command_helpers import ProjectUsageError

from .project_config import ProjectConfig, ProjectConfigError
from .project_config import read_project_config as _read_project_config
from .project_errors import missing_issue_field_option_message
from .project_model import BASE_PROJECT_SCHEMA, FIELD_OPTION_TO_PROJECT_FIELD
from .project_model import ConfigureAction, FieldUpdate, Finding
from .project_model import ProjectArguments, ProjectField, ProjectSchema
from .project_model import SelectFieldSpec, SelectOption

ISSUE_DEFAULT_OUTPUT_ORDER = (
    "field_source", "status", "priority", "size", "effort", "risk_tier", "start_date",
    "target_date", "area", "initiative", "assignee",
)


def schema_for_args(args: ProjectArguments) -> ProjectSchema:
    if args.schema != "base-project":
        raise ProjectUsageError("Only project schema 'base-project' is supported.")
    config = project_config_for_args(args)
    schema = BASE_PROJECT_SCHEMA
    if config.field_source == "issue_fields":
        schema = ProjectSchema(tuple(field for field in schema.fields if field.name not in {"Priority", "Size"}))
    elif config.field_source == "project_fields":
        schema = ProjectSchema(
            tuple(
                SelectFieldSpec(
                    {"Priority": "Legacy priority", "Size": "Legacy size"}.get(field.name, field.name),
                    field.options,
                )
                for field in schema.fields
            )
        )
    if args.initiative_options:
        return schema_with_project_config(
            schema_with_initiatives(schema, args.initiative_options),
            config,
        )
    return schema_with_project_config(schema, config)


def project_config_for_args(args: ProjectArguments) -> ProjectConfig:
    if not args.config_path:
        return ProjectConfig()
    return read_project_config(Path(args.config_path))


def issue_field_values_for_args(args: ProjectArguments) -> dict[str, str]:
    config = project_config_for_args(args)
    defaults = normalize_field_values(config.field_source, config.issue_defaults)
    defaults.update(normalize_field_values(config.field_source, args.field_values or {}))
    return defaults


def issue_defaults_command(args: ProjectArguments) -> int:
    config = project_config_for_args(args)
    for key in ISSUE_DEFAULT_OUTPUT_ORDER:
        value = config.field_source if key == "field_source" else config.issue_defaults.get(key)
        if value:
            print(f"{key}\t{value}")
    return base_cli.ExitCode.SUCCESS


def project_field_defaults_for_config(config: ProjectConfig) -> dict[str, str]:
    defaults: dict[str, str] = {}
    for value_key, field_name in FIELD_OPTION_TO_PROJECT_FIELD.items():
        if config.field_source == "issue_fields" and value_key in {"priority", "size"}:
            continue
        option_name = config.issue_defaults.get(value_key)
        if option_name:
            defaults[field_name] = option_name
    if config.field_source == "project_fields" and "effort" in config.issue_defaults:
        effort = config.issue_defaults["effort"]
        size = {"Tiny": "T", "Small": "S", "Medium": "M", "Large": "L"}.get(effort)
        if size is None:
            raise ProjectUsageError(f"Unknown Effort default '{effort}'.")
        defaults["Size"] = size
    return defaults


def normalize_field_values(field_source: str | None, values: dict[str, str]) -> dict[str, str]:
    """Resolve the Size compatibility alias against the configured field home."""
    normalized = dict(values)
    effort = normalized.pop("effort", None)
    size = normalized.pop("size", None)
    if effort and size:
        raise ProjectUsageError("Use either --effort or --size, not both.")
    selected = effort or size
    if selected is not None:
        if field_source == "issue_fields":
            if effort is None:
                selected = {"T": "Tiny", "S": "Small", "M": "Medium", "L": "Large"}.get(selected, selected)
            normalized["effort"] = selected
        else:
            if effort is not None:
                selected = {"Tiny": "T", "Small": "S", "Medium": "M", "Large": "L"}.get(selected, selected)
            normalized["size"] = selected
    return normalized


def read_project_config(path: Path) -> ProjectConfig:
    try:
        return _read_project_config(path)
    except ProjectConfigError as exc:
        raise ProjectUsageError(str(exc)) from exc


def schema_with_initiatives(schema: ProjectSchema, initiative_options: tuple[str, ...]) -> ProjectSchema:
    return schema_with_extra_options(schema, "Initiative", initiative_options, "Project-specific initiative.")


def schema_with_project_config(schema: ProjectSchema, config: ProjectConfig) -> ProjectSchema:
    schema = schema_with_extra_options(schema, "Area", config.areas, "Repository-specific area.")
    return schema_with_extra_options(schema, "Initiative", config.initiatives, "Repository-specific initiative.")


def schema_with_extra_options(
    schema: ProjectSchema, field_name: str, option_names: tuple[str, ...], description: str
) -> ProjectSchema:
    if not option_names:
        return schema
    fields: list[SelectFieldSpec] = []
    for field in schema.fields:
        if field.name != field_name:
            fields.append(field)
            continue
        existing = {option.name for option in field.options}
        options = list(field.options)
        for option_name in option_names:
            if option_name not in existing:
                options.append(SelectOption(option_name, "GRAY", description))
                existing.add(option_name)
        fields.append(SelectFieldSpec(field.name, tuple(options)))
    return ProjectSchema(tuple(fields))


def compare_schema(fields: tuple[ProjectField, ...], schema: ProjectSchema) -> tuple[Finding, ...]:
    by_name = {field.name: field for field in fields}
    findings: list[Finding] = []
    for spec in schema.fields:
        field = by_name.get(spec.name)
        if field is None:
            findings.append(Finding("missing", spec.name, f"{spec.name} field is missing."))
            continue
        if field.data_type != "SINGLE_SELECT":
            findings.append(
                Finding("error", spec.name, f"{spec.name} exists with type {field.data_type}; expected SINGLE_SELECT.")
            )
            continue
        existing_options = {option.name for option in field.options}
        for option in spec.options:
            if option.name not in existing_options:
                findings.append(Finding("missing-option", spec.name, f"{spec.name} option {option.name} is missing."))
    return tuple(findings)


def configuration_plan(
    *, project_exists: bool, fields: tuple[ProjectField, ...], schema: ProjectSchema
) -> tuple[ConfigureAction, ...]:
    actions: list[ConfigureAction] = []
    if not project_exists:
        actions.append(ConfigureAction("create-project", "Project", "Create GitHub Project."))
    by_name = {field.name: field for field in fields}
    for spec in schema.fields:
        field = by_name.get(spec.name)
        if field is None:
            actions.append(ConfigureAction("create-field", spec.name, f"Create {spec.name} as SINGLE_SELECT."))
            continue
        if field.data_type != "SINGLE_SELECT":
            message = f"{spec.name} exists with type {field.data_type}; expected SINGLE_SELECT."
            actions.append(ConfigureAction("error", spec.name, message))
            continue
        existing_options = {option.name for option in field.options}
        missing_options = [option.name for option in spec.options if option.name not in existing_options]
        if missing_options:
            actions.append(
                ConfigureAction("update-field", spec.name, f"Add missing options: {', '.join(missing_options)}.")
            )
    return tuple(actions)


def merged_options(field: ProjectField, spec: SelectFieldSpec) -> tuple[SelectOption, ...]:
    merged = list(field.options)
    names = {option.name for option in merged}
    for option in spec.options:
        if option.name not in names:
            merged.append(option)
            names.add(option.name)
    return tuple(merged)


def options_payload(options: tuple[SelectOption, ...]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for option in options:
        item = {"name": option.name, "color": option.color, "description": option.description}
        if option.option_id:
            item["id"] = option.option_id
        payload.append(item)
    return payload


def missing_option_names(field: ProjectField, spec: SelectFieldSpec) -> tuple[str, ...]:
    existing = {option.name for option in field.options}
    return tuple(option.name for option in spec.options if option.name not in existing)


def resolve_issue_field_updates(
    fields: tuple[ProjectField, ...], values: dict[str, str], *, project_title: str
) -> tuple[FieldUpdate, ...]:
    by_name = {field.name: field for field in fields}
    updates: list[FieldUpdate] = []
    for value_key, field_name in FIELD_OPTION_TO_PROJECT_FIELD.items():
        option_name = values.get(value_key)
        if not option_name:
            continue
        if field_name not in by_name and value_key == "priority" and "Legacy priority" in by_name:
            field_name = "Legacy priority"
        elif field_name not in by_name and value_key == "size" and "Legacy size" in by_name:
            field_name = "Legacy size"
        field = by_name.get(field_name)
        if field is None:
            raise ProjectUsageError(f"{field_name} field was not found in Project '{project_title}'.")
        option = find_option(field, option_name)
        if option is None or option.option_id is None:
            raise ProjectUsageError(missing_issue_field_option_message(field_name, option_name, project_title))
        updates.append(FieldUpdate(field.field_id, option.option_id, field_name, option_name))
    return tuple(updates)


def find_option(field: ProjectField, name: str) -> SelectOption | None:
    for option in field.options:
        if option.name == name:
            return option
    return None
