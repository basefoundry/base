from __future__ import annotations

import string


RELEASE_TITLE_PLACEHOLDERS = {"repository", "version", "tag"}
ALLOWED_RELEASE_TITLE_PLACEHOLDERS = "{repository}, {version}, {tag}"


def release_title_template_error(value: str) -> str:
    try:
        parts = tuple(string.Formatter().parse(value))
    except ValueError:
        return f"must use valid placeholders: {ALLOWED_RELEASE_TITLE_PLACEHOLDERS}."

    unsupported: list[str] = []
    for _literal, placeholder, _format_spec, _conversion in parts:
        if placeholder is None:
            continue
        if placeholder not in RELEASE_TITLE_PLACEHOLDERS:
            unsupported.append(placeholder or "<positional>")
    if not unsupported:
        return ""

    bad = ", ".join(sorted(set(unsupported)))
    return f"has unsupported placeholders: {bad}. Allowed: {ALLOWED_RELEASE_TITLE_PLACEHOLDERS}."
