from __future__ import annotations


def missing_issue_field_option_message(field_name: str, option_name: str, project_title: str) -> str:
    if field_name == "Initiative":
        return (
            f"Initiative option '{option_name}' was not found in Project '{project_title}'. "
            f'Run `basectl gh project configure --project "{project_title}" '
            f'--initiative-option "{option_name}"` first.'
        )
    if field_name == "Size":
        return (
            f"Size option '{option_name}' was not found in Project '{project_title}'. "
            f'Run `basectl gh project configure --project "{project_title}"` first.'
        )
    return f"{field_name} option '{option_name}' was not found in Project '{project_title}'."
