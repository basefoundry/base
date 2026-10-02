from __future__ import annotations

import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMAND_REFERENCE = REPO_ROOT / "docs" / "command-reference.md"
LONG_OPTION = re.compile(r"--[A-Za-z0-9][\w-]*")
COMMON_OPTIONS = {"--help", "--version"}
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


def probe_arguments(command: str) -> list[str]:
    if command == "basectl uninstall <project>|--all":
        return ["uninstall", "--all"]
    if command == "basectl gh pr create/status/checks/ready/merge":
        return ["gh", "pr", "create"]
    tokens = shlex.split(command)[1:]
    return [token for token in tokens if not (token.startswith("<") or token.startswith("["))]


def help_options(output: str) -> set[str]:
    options: set[str] = set()
    in_options = False
    for line in output.splitlines():
        if line.strip() == "Options:":
            in_options = True
            continue
        if in_options and line and not line[0].isspace():
            break
        if in_options:
            options.update(LONG_OPTION.findall(line.strip().split("  ", 1)[0]))
    return options - COMMON_OPTIONS


def test_command_reference_lists_each_owned_help_option() -> None:
    environment = os.environ.copy()
    environment["BASE_BASH_LIBS_DIR"] = str(REPO_ROOT.parents[1] / "base-bash-libs" / "lib" / "bash")
    missing: list[str] = []
    with tempfile.TemporaryDirectory(prefix="base-command-reference-") as cache_dir:
        environment["BASE_CACHE_DIR"] = cache_dir
        for command, documented in rows():
            completed = subprocess.run(
                [str(REPO_ROOT / "bin" / "basectl"), *probe_arguments(command), "--help"],
                cwd=REPO_ROOT,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            assert completed.returncode == 0, completed.stderr or completed.stdout
            options = help_options(completed.stdout or completed.stderr)
            missing.extend(f"{command}: {option}" for option in sorted(options - documented))

    assert not missing, "undocumented command-reference flags:\n" + "\n".join(missing)
