import re
from dataclasses import fields
from pathlib import Path

from base_cli.context import Context


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_CLI_DOC = REPO_ROOT / "docs" / "base-cli.md"
INTERNAL_CONTEXT_FIELDS = {"cleanup_hooks"}


def context_section() -> str:
    text = BASE_CLI_DOC.read_text(encoding="utf-8")
    start = text.index("## Context")
    end = text.index("## State Directories")
    return text[start:end]


def test_base_cli_context_docs_list_public_context_fields() -> None:
    documented_fields = set(re.findall(r"ctx\.([a-z_]+)", context_section()))
    public_context_fields = {field.name for field in fields(Context)} - INTERNAL_CONTEXT_FIELDS

    assert public_context_fields <= documented_fields
