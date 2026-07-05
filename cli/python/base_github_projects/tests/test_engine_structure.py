from __future__ import annotations

from pathlib import Path

from base_github_projects import engine


def test_project_parser_is_split_from_engine() -> None:
    engine_path = Path(engine.__file__)
    parser_path = engine_path.with_name("project_parser.py")

    assert parser_path.exists()
    assert "def parse_project_options" in parser_path.read_text(encoding="utf-8")
    assert "def parse_project_options" not in engine_path.read_text(encoding="utf-8")


def test_project_graphql_transport_is_split_from_engine() -> None:
    engine_path = Path(engine.__file__)
    graphql_path = engine_path.with_name("project_graphql.py")

    assert graphql_path.exists()
    assert "def run_graphql" in graphql_path.read_text(encoding="utf-8")
    assert "def run_graphql" not in engine_path.read_text(encoding="utf-8")


def test_project_schema_planning_is_split_from_engine() -> None:
    engine_path = Path(engine.__file__)
    schema_path = engine_path.with_name("project_schema.py")

    assert schema_path.exists()
    assert "def configuration_plan" in schema_path.read_text(encoding="utf-8")
    assert "def configuration_plan" not in engine_path.read_text(encoding="utf-8")


def test_project_git_helpers_are_split_from_engine() -> None:
    engine_path = Path(engine.__file__)
    git_path = engine_path.with_name("project_git.py")

    assert git_path.exists()
    assert "def infer_repo_from_git" in git_path.read_text(encoding="utf-8")
    assert "def infer_repo_from_git" not in engine_path.read_text(encoding="utf-8")
