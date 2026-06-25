from __future__ import annotations

from pathlib import Path

import pytest

from base_github_projects import engine


def test_parse_project_issue_defaults_requires_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("BASE_CACHE_DIR", str(tmp_path / ".cache" / "base"))

    status = engine.main(["project", "issue", "defaults"])

    captured = capsys.readouterr()
    assert status == 2
    assert "project issue defaults --config <path>" in captured.err
    assert "requires --config" in captured.err


def test_project_issue_defaults_command_prints_project_config_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("BASE_CACHE_DIR", str(tmp_path / ".cache" / "base"))
    config_path = tmp_path / "base-project.yml"
    config_path.write_text(
        "\n".join(
            (
                "project:",
                "  issue_defaults:",
                "    status: Backlog",
                "    priority: P1",
                "    size: T",
                "    area: CLI",
                "    initiative: Adoption Polish",
                "    assignee: codeforester",
            )
        ),
        encoding="utf-8",
    )

    status = engine.main(["project", "issue", "defaults", "--config", str(config_path)])

    assert status == 0
    assert capsys.readouterr().out == (
        "status\tBacklog\n"
        "priority\tP1\n"
        "size\tT\n"
        "area\tCLI\n"
        "initiative\tAdoption Polish\n"
        "assignee\tcodeforester\n"
    )


def test_project_issue_defaults_command_rejects_invalid_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("BASE_CACHE_DIR", str(tmp_path / ".cache" / "base"))
    config_path = tmp_path / "base-project.yml"
    config_path.write_text(
        "\n".join(
            (
                "project:",
                "  issue_defaults:",
                "    labels: bug",
            )
        ),
        encoding="utf-8",
    )

    status = engine.main(["project", "issue", "defaults", "--config", str(config_path)])

    captured = capsys.readouterr()
    assert status == 2
    assert "project.issue_defaults contains unsupported keys: labels" in captured.err
