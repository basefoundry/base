from __future__ import annotations

import pytest

from base_github_projects import engine
from base_github_projects.project_issue_fields_command import ISSUE_FIELD_NAMES, PROJECT_FIELD_KEYS
from base_github_projects.project_parser import ISSUE_FIELD_OPTIONS, ISSUE_FIELD_OPTION_TO_KEY


FIELD_OPTION_VALUES = {
    "--status": "In Progress",
    "--priority": "P2",
    "--area": "CLI",
    "--initiative": "Contract Hardening",
    "--size": "S",
    "--effort": "Small",
    "--risk-tier": "High",
    "--start-date": "2026-12-01",
    "--target-date": "2026-12-31",
}


@pytest.mark.parametrize("option", ISSUE_FIELD_OPTIONS)
@pytest.mark.parametrize("inline", (False, True), ids=("spaced", "inline"))
def test_issue_field_options_map_to_command_keys(option: str, inline: bool) -> None:
    value = FIELD_OPTION_VALUES[option]
    field_argument = (f"{option}={value}",) if inline else (option, value)
    args = engine.parse_args(
        (
            "project", "issue", "set-fields", "2711", "--project", "base",
            "--repo", "basefoundry/base", *field_argument,
        )
    )
    key = ISSUE_FIELD_OPTION_TO_KEY[option]

    assert key in ISSUE_FIELD_NAMES or key in PROJECT_FIELD_KEYS
    assert args.field_values == {key: value}


def test_parse_project_issue_set_fields_accepts_cross_repo_opt_in() -> None:
    args = engine.parse_args(
        (
            "project",
            "issue",
            "set-fields",
            "1604",
            "--project",
            "Base Roadmap",
            "--owner",
            "basefoundry",
            "--repo",
            "basefoundry/base-cli",
            "--allow-cross-repo",
            "--priority",
            "P2",
        )
    )

    assert args.command == "issue-set-fields"
    assert args.repo == "basefoundry/base-cli"
    assert args.allow_cross_repo is True
    assert args.field_values == {"priority": "P2"}


def test_parse_project_issue_copy_fields_requires_direction_and_preserves_write_options() -> None:
    args = engine.parse_args(
        (
            "project",
            "issue",
            "copy-fields",
            "--project",
            "Base Roadmap",
            "--owner",
            "basefoundry",
            "--direction",
            "issue-to-project",
            "--write",
            "--export",
            "/secure/base-before.json",
        )
    )

    assert args.command == "issue-copy-fields"
    assert args.copy_direction == "issue-to-project"
    assert args.write is True
    assert args.export_path == "/secure/base-before.json"


def test_parse_project_issue_copy_fields_rejects_missing_direction() -> None:
    try:
        engine.parse_args(("project", "issue", "copy-fields", "--project", "Base Roadmap"))
    except engine.ProjectUsageError as exc:
        assert "requires --direction" in str(exc)
    else:
        raise AssertionError("copy-fields must require an explicit direction")
