from __future__ import annotations

from pathlib import Path

from base_release import engine


def test_release_readiness_helpers_are_split_from_engine() -> None:
    engine_path = Path(engine.__file__)
    readiness_path = engine_path.with_name("release_readiness.py")

    assert readiness_path.exists()
    assert "def release_findings" in readiness_path.read_text(encoding="utf-8")
    assert "def release_findings" not in engine_path.read_text(encoding="utf-8")


def test_release_publish_helpers_are_split_from_engine() -> None:
    engine_path = Path(engine.__file__)
    publish_path = engine_path.with_name("release_publish.py")

    assert publish_path.exists()
    assert "def run_release_step" in publish_path.read_text(encoding="utf-8")
    assert "def run_release_step" not in engine_path.read_text(encoding="utf-8")


def test_release_parser_helpers_are_split_from_engine() -> None:
    engine_path = Path(engine.__file__)
    parser_path = engine_path.with_name("release_parser.py")

    assert parser_path.exists()
    assert "def parse_release_args" in parser_path.read_text(encoding="utf-8")
    assert "def parse_release_args" not in engine_path.read_text(encoding="utf-8")
