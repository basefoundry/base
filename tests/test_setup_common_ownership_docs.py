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
SETUP_MACOS_HOMEBREW_SCRIPT = (
    REPO_ROOT / "cli" / "bash" / "commands" / "basectl" / "subcommands" / "setup_macos_homebrew.sh"
)
SETUP_VENV_SCRIPT = (
    REPO_ROOT / "cli" / "bash" / "commands" / "basectl" / "subcommands" / "setup_venv.sh"
)
SETUP_PROFILES_SCRIPT = (
    REPO_ROOT / "cli" / "bash" / "commands" / "basectl" / "subcommands" / "setup_profiles.sh"
)
SETUP_PROJECT_ARTIFACTS_SCRIPT = (
    REPO_ROOT
    / "cli"
    / "bash"
    / "commands"
    / "basectl"
    / "subcommands"
    / "setup_project_artifacts.sh"
)
SETUP_DOCTOR_VISUAL_SCRIPT = (
    REPO_ROOT
    / "cli"
    / "bash"
    / "commands"
    / "basectl"
    / "subcommands"
    / "setup_doctor_visual.sh"
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
            SETUP_MACOS_HOMEBREW_SCRIPT,
            SETUP_VENV_SCRIPT,
            SETUP_PROFILES_SCRIPT,
            SETUP_PROJECT_ARTIFACTS_SCRIPT,
            SETUP_DOCTOR_VISUAL_SCRIPT,
        )
    )


def shell_function_names(source: str) -> set[str]:
    return set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\(\) \{", source, flags=re.MULTILINE))


def documented_setup_function_anchors(markdown: str) -> set[str]:
    return set(re.findall(r"`(setup_[a-z0-9_]+)\(\)`", markdown))


def documented_setup_rows(markdown: str) -> list[tuple[str, int, int, set[str]]]:
    rows: list[tuple[str, int, int, set[str]]] = []
    row_pattern = re.compile(
        r"^\| `(?P<path>[^`]+)` (?P<start>\d+)-(?P<end>\d+) \|.*\| (?P<anchors>.*?) \|$"
    )
    for line in markdown.splitlines():
        match = row_pattern.match(line)
        if match is None:
            continue
        anchors = set(re.findall(r"`(setup_[a-z0-9_]+)\(\)`", match.group("anchors")))
        rows.append(
            (
                match.group("path"),
                int(match.group("start")),
                int(match.group("end")),
                anchors,
            )
        )
    return rows


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
        "## Close-Out Decisions",
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
    assert "setup_project_artifacts.sh" in text
    assert "setup_notifications.sh" in text
    assert "#1591" in text
    assert "cohesive functional domain" in text
    assert "line-count threshold" in text
    assert "notification helper is intentionally deferred" in text
    assert "Structured check/doctor JSON assembly moved into Python-owned code" in text


def test_setup_common_ownership_doc_function_anchors_exist() -> None:
    anchors = documented_setup_function_anchors(setup_common_doc())
    actual_functions = shell_function_names(setup_shell_sources())

    assert anchors, "setup_common ownership doc should anchor the map to setup_* functions"
    missing = sorted(anchors - actual_functions)
    assert not missing, "documented setup_common function anchors are missing: " + ", ".join(missing)


def test_setup_common_ownership_doc_ranges_contain_function_anchors() -> None:
    for path, start, end, anchors in documented_setup_rows(setup_common_doc()):
        script = REPO_ROOT / "cli" / "bash" / "commands" / "basectl" / "subcommands" / path
        lines = script.read_text(encoding="utf-8").splitlines()
        assert end <= len(lines), f"{path} range ends at {end}, but the file has {len(lines)} lines"
        function_lines = {
            name: line_number
            for line_number, line in enumerate(lines, start=1)
            for name in re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\(\) \{", line)
        }
        for anchor in anchors:
            assert anchor in function_lines, f"{anchor} is not defined in {path}"
            assert start <= function_lines[anchor] <= end, (
                f"{anchor} is at line {function_lines[anchor]} outside {path} {start}-{end}"
            )


def test_setup_common_sources_linux_debian_helper() -> None:
    common_source = setup_common_script()
    linux_debian_source = SETUP_LINUX_DEBIAN_SCRIPT.read_text(encoding="utf-8")

    assert 'source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_linux_debian.sh"' in common_source
    assert "_base_setup_linux_debian_sourced" in linux_debian_source


def test_setup_common_sources_macos_homebrew_helper() -> None:
    common_source = setup_common_script()
    macos_homebrew_source = SETUP_MACOS_HOMEBREW_SCRIPT.read_text(encoding="utf-8")

    assert 'source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_macos_homebrew.sh"' in common_source
    assert "_base_setup_macos_homebrew_sourced" in macos_homebrew_source


def test_setup_common_sources_venv_helper() -> None:
    common_source = setup_common_script()
    venv_source = SETUP_VENV_SCRIPT.read_text(encoding="utf-8")

    assert 'source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_venv.sh"' in common_source
    assert "_base_setup_venv_sourced" in venv_source


def test_setup_common_sources_profiles_helper() -> None:
    common_source = setup_common_script()
    profiles_source = SETUP_PROFILES_SCRIPT.read_text(encoding="utf-8")

    assert 'source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_profiles.sh"' in common_source
    assert "_base_setup_profiles_sourced" in profiles_source


def test_setup_common_sources_project_artifacts_helper() -> None:
    common_source = setup_common_script()
    project_artifacts_source = SETUP_PROJECT_ARTIFACTS_SCRIPT.read_text(
        encoding="utf-8"
    )

    assert (
        'source "$BASE_HOME/cli/bash/commands/basectl/subcommands/'
        'setup_project_artifacts.sh"'
    ) in common_source
    assert "_base_setup_project_artifacts_sourced" in project_artifacts_source
