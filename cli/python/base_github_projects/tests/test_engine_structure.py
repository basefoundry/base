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
