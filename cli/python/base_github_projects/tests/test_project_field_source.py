from __future__ import annotations

from pathlib import Path

import pytest

from base_github_projects import engine, project_schema
from base_github_projects.project_config import ProjectConfigError, read_project_config


@pytest.mark.parametrize(
    ("yaml", "expected_source"),
    [
        ("project:\n  issue_defaults:\n    status: Backlog\n", None),
        ("project:\n  field_source: issue_fields\n", "issue_fields"),
        ("project:\n  field_source: project_fields\n", "project_fields"),
    ],
)
def test_project_config_accepts_all_three_field_source_states(
    tmp_path: Path, yaml: str, expected_source: str | None
) -> None:
    path = tmp_path / "base-project.yml"
    path.write_text(yaml, encoding="utf-8")

    config = read_project_config(path)

    assert config.field_source == expected_source


def test_project_config_rejects_unknown_field_source(tmp_path: Path) -> None:
    path = tmp_path / "base-project.yml"
    path.write_text("project:\n  field_source: auto\n", encoding="utf-8")

    with pytest.raises(ProjectConfigError, match="project.field_source must be one of"):
        read_project_config(path)


@pytest.mark.parametrize(
    ("source", "expected_names"),
    [
        (None, {"Priority", "Size"}),
        ("issue_fields", set()),
        ("project_fields", {"Legacy priority", "Legacy size"}),
    ],
)
def test_schema_uses_project_fields_for_the_selected_source(
    tmp_path: Path, source: str | None, expected_names: set[str]
) -> None:
    path = tmp_path / "base-project.yml"
    field_source = f"  field_source: {source}\n" if source else ""
    path.write_text(f"project:\n{field_source}" if field_source else "project: {}\n", encoding="utf-8")
    args = engine.ProjectArguments(area="project", command="doctor", config_path=str(path))

    names = {field.name for field in project_schema.schema_for_args(args).fields}

    assert {name for name in names if name in {"Priority", "Size", "Legacy priority", "Legacy size"}} == expected_names
