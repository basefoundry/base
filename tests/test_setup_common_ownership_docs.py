import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_COMMON_DOC = REPO_ROOT / "docs" / "setup-common-ownership.md"
SETUP_COMMON_SCRIPT = (
    REPO_ROOT / "cli" / "bash" / "commands" / "basectl" / "subcommands" / "setup_common.sh"
)
SETUP_LINUX_DEBIAN_SCRIPT = (
    REPO_ROOT / "cli" / "bash" / "commands" / "basectl" / "subcommands" / "setup_linux_debian.sh"
)
DOCS_README = REPO_ROOT / "docs" / "README.md"


def setup_common_doc() -> str:
    return SETUP_COMMON_DOC.read_text(encoding="utf-8")


def setup_common_script() -> str:
    return SETUP_COMMON_SCRIPT.read_text(encoding="utf-8")


def setup_shell_sources() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            SETUP_COMMON_SCRIPT,
            SETUP_LINUX_DEBIAN_SCRIPT,
        )
    )


def shell_function_names(source: str) -> set[str]:
    return set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\(\) \{", source, flags=re.MULTILINE))


def documented_setup_function_anchors(markdown: str) -> set[str]:
    return set(re.findall(r"`(setup_[a-z0-9_]+)\(\)`", markdown))


def test_setup_common_ownership_doc_is_linked_from_docs_map() -> None:
    readme = DOCS_README.read_text(encoding="utf-8")

    assert "[`setup_common.sh` Ownership Reduction](setup-common-ownership.md)" in readme


def test_setup_common_ownership_doc_records_current_strategy() -> None:
    text = setup_common_doc()

    required_sections = (
        "## Guardrails",
        "## Current Responsibility Map",
        "## Decomposition Strategy",
        "## Source-Guard Protocol",
        "## Recommended PR Sequence",
    )
    for section in required_sections:
        assert section in text

    assert "#1570" in text
    assert "#1564" in text
    assert "#1009" not in text
    assert "setup_linux_debian.sh" in text
    assert "setup_macos_homebrew.sh" in text
    assert "setup_venv.sh" in text
    assert "setup_profiles.sh" in text
    assert "setup_notifications.sh" in text
    assert "Move structured check/doctor JSON assembly into Python-owned code" in text


def test_setup_common_ownership_doc_function_anchors_exist() -> None:
    anchors = documented_setup_function_anchors(setup_common_doc())
    actual_functions = shell_function_names(setup_shell_sources())

    assert anchors, "setup_common ownership doc should anchor the map to setup_* functions"
    missing = sorted(anchors - actual_functions)
    assert not missing, "documented setup_common function anchors are missing: " + ", ".join(missing)


def test_setup_common_sources_linux_debian_helper() -> None:
    common_source = setup_common_script()
    linux_debian_source = SETUP_LINUX_DEBIAN_SCRIPT.read_text(encoding="utf-8")

    assert 'source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_linux_debian.sh"' in common_source
    assert "_base_setup_linux_debian_sourced" in linux_debian_source
