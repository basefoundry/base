"""Project-field identity and standard-before-Legacy role resolution."""
from __future__ import annotations

from collections.abc import Iterable

LEGACY_NAMES = {"Priority": "Legacy priority", "Size": "Legacy size"}


def resolve_project_field(fields: Iterable[object], name: str) -> object | None:
    fields = tuple(fields)
    for candidate in (name, LEGACY_NAMES.get(name)):
        if candidate is None:
            continue
        for field in fields:
            if field.name == candidate and not getattr(field, "is_issue_field", False):
                return field
    return None


def has_issue_field_clash(fields: Iterable[object], name: str) -> bool:
    fields = tuple(fields)
    return name in LEGACY_NAMES and resolve_project_field(fields, name) is None and any(
        field.name == name and getattr(field, "is_issue_field", False) for field in fields
    )


def clash_message(name: str) -> str:
    return (
        f"{name} conflicts with an organization issue field displayed in the Project. "
        f"Set project.field_source to issue_fields, or add the '{LEGACY_NAMES[name]}' Project field."
    )
