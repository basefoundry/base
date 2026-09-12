import re
from pathlib import Path

from base_cli.context import Context
from base_cli_adapters.provider import public_context_field_names


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_CLI_DOC = REPO_ROOT / "docs" / "base-cli.md"


def context_section() -> str:
    text = BASE_CLI_DOC.read_text(encoding="utf-8")
    start = text.index("## Context")
    end = text.index("## State Directories")
    return text[start:end]


def test_base_cli_context_docs_list_public_context_fields() -> None:
    documented_fields = set(re.findall(r"ctx\.([a-z_]+)", context_section()))
    public_context_fields = public_context_field_names(Context)

    assert public_context_fields <= documented_fields
