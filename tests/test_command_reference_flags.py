from __future__ import annotations

import re
from pathlib import Path

from tests import stability_compatibility as compatibility


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMAND_REFERENCE = REPO_ROOT / "docs" / "command-reference.md"
LONG_OPTION = re.compile(r"--[A-Za-z0-9][\w-]*")
COMMON_OPTIONS = {"--help"}
SHARED_HELP_ROWS = {
    # These rows intentionally split one implementation's combined help surface.
    "basectl run [project] <command>",
    "basectl run [project] --list",
    "basectl build [project] [target...]",
    "basectl build [project] --list",
    "basectl setup --ci [project]",
    "basectl logs",
    "basectl logs --latest",
    "basectl logs --open",
    "basectl logs --tail",
    "basectl history",
    "basectl history --report",
    "basectl gh auth status",
}


def rows() -> list[tuple[str, set[str]]]:
    result: list[tuple[str, set[str]]] = []
    for line in COMMAND_REFERENCE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `basectl "):
            continue
        protected = line.replace(r"\|", "\x00")
        cells = [cell.replace("\x00", "|").strip() for cell in protected.strip().strip("|").split("|")]
        command = cells[0].strip("`")
        flags = cells[2]
        if "passes through" in flags or "field options" in flags or command in SHARED_HELP_ROWS:
            continue
        documented = set(LONG_OPTION.findall(flags))
        documented.update(LONG_OPTION.findall(command))
        result.append((command, documented))
    return result


def test_command_reference_lists_each_owned_help_option() -> None:
    documented_rows = rows()
    contracts = compatibility.runtime_command_contract(REPO_ROOT, [command for command, _ in documented_rows])
    mismatches: list[str] = []
    for command, documented in documented_rows:
        actual = {
            option for option in contracts[command]["flags"] if option.startswith("--")
        } - COMMON_OPTIONS
        for option in sorted(actual - documented):
            mismatches.append(f"{command}: help exposes undocumented {option}")
        for option in sorted(documented - actual):
            mismatches.append(f"{command}: docs list missing help option {option}")

    assert not mismatches, "command-reference/help option mismatches:\n" + "\n".join(mismatches)
