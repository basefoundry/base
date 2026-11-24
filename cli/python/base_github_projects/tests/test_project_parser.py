from __future__ import annotations

from base_github_projects import engine


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
