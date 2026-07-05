from __future__ import annotations

import subprocess

import pytest

from base_github_projects import engine
from base_github_projects import project_git
from base_github_projects import project_graphql


def test_infer_repo_from_git_passes_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(
        ["git", "config", "--get", "remote.origin.url"],
        0,
        stdout="git@github.com:basefoundry/base.git\n",
        stderr="",
    )

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["git", "config", "--get", "remote.origin.url"]
        assert kwargs["timeout"] == project_git.GIT_COMMAND_TIMEOUT_SECONDS
        return completed

    monkeypatch.setattr(project_git.subprocess, "run", fake_run)

    assert engine.infer_repo_from_git() == "basefoundry/base"


def test_infer_repo_from_git_returns_none_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(project_git.subprocess, "run", fake_run)

    assert engine.infer_repo_from_git() is None


def test_run_graphql_passes_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(
        ["gh", "api", "graphql", "--input", "-"],
        0,
        stdout='{"data": {"viewer": {"login": "codeforester"}}}',
        stderr="",
    )

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["gh", "api", "graphql", "--input", "-"]
        assert kwargs["timeout"] == project_graphql.GITHUB_GRAPHQL_TIMEOUT_SECONDS
        return completed

    monkeypatch.setattr(project_graphql.subprocess, "run", fake_run)

    assert engine.run_graphql("query Viewer { viewer { login } }", {}) == {
        "data": {"viewer": {"login": "codeforester"}}
    }


def test_run_graphql_reports_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(project_graphql.subprocess, "run", fake_run)

    with pytest.raises(engine.ProjectError) as excinfo:
        engine.run_graphql("query Viewer { viewer { login } }", {})

    assert "Timed out running GitHub GraphQL request after" in str(excinfo.value)
