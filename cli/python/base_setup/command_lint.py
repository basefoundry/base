from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path

from . import process
from .checks import ArtifactCheck
from .manifest import BaseManifest
from .uv import manifest_uses_uv_project_manager


SHELL_BUILTINS = {
    ".",
    ":",
    "[",
    "[[",
    "!",
    "case",
    "cd",
    "command",
    "do",
    "done",
    "echo",
    "elif",
    "else",
    "esac",
    "eval",
    "exec",
    "export",
    "false",
    "fi",
    "for",
    "function",
    "if",
    "printf",
    "select",
    "source",
    "test",
    "then",
    "time",
    "true",
    "until",
    "while",
}


@dataclass(frozen=True)
class CommandDeclaration:
    field: str
    command: str
    runner: str | None
    working_dir: str = "."


def check_manifest_commands(manifest: BaseManifest) -> tuple[ArtifactCheck, ...]:
    checks: list[ArtifactCheck] = []
    for declaration in command_declarations(manifest):
        check = check_command_declaration(manifest, declaration)
        if check is not None:
            checks.append(check)
    return tuple(checks)


def command_declarations(manifest: BaseManifest) -> tuple[CommandDeclaration, ...]:
    declarations: list[CommandDeclaration] = []
    if manifest.test is not None and manifest.test.command is not None:
        declarations.append(CommandDeclaration("test.command", manifest.test.command, manifest.test.runner))

    for command_name, command_config in manifest.commands.items():
        declarations.append(
            CommandDeclaration(f"commands.{command_name}.command", command_config.command, command_config.runner)
        )

    if manifest.build is not None:
        for target_name, target_config in manifest.build.targets.items():
            declarations.append(
                CommandDeclaration(
                    f"build.targets.{target_name}.command",
                    target_config.command,
                    target_config.runner,
                    target_config.working_dir,
                )
            )

    return tuple(declarations)


def check_command_declaration(
    manifest: BaseManifest,
    declaration: CommandDeclaration,
) -> ArtifactCheck | None:
    executable = first_executable(declaration.command)
    if executable is None or executable in SHELL_BUILTINS or is_dynamic_executable(executable):
        return None

    if is_path_like_command(executable):
        if Path(executable).is_absolute():
            return check_absolute_executable_path(manifest, declaration, executable)
        return check_project_script_path(manifest, declaration, executable)

    if declaration.runner == "uv":
        return None

    if command_available(manifest, executable):
        return None

    return ArtifactCheck(
        name=declaration.field,
        ok=False,
        message=(
            f"{declaration.field} starts with executable '{executable}', but it was not found on PATH "
            "or in the project virtual environment."
        ),
        fix=(
            f"Install '{executable}', declare an appropriate runner, "
            f"or update {declaration.field} in '{manifest.path}'."
        ),
        finding_id="BASE-P160",
        status="warn",
        details={"executable": executable, "field": declaration.field},
    )


def first_executable(command: str) -> str | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None

    for token in tokens:
        if is_variable_assignment(token):
            continue
        return token
    return None


def is_variable_assignment(token: str) -> bool:
    if "=" not in token or token.startswith("="):
        return False
    name, _value = token.split("=", 1)
    return name.replace("_", "A").isalnum() and not name[0].isdigit()


def is_path_like_command(executable: str) -> bool:
    return "/" in executable


def is_dynamic_executable(executable: str) -> bool:
    return executable.startswith("~") or any(character in executable for character in "$`*?[]{}")


def check_absolute_executable_path(
    manifest: BaseManifest,
    declaration: CommandDeclaration,
    executable: str,
) -> ArtifactCheck | None:
    executable_path = Path(executable)
    if executable_path.is_file() and os.access(executable_path, os.X_OK):
        return None

    return ArtifactCheck(
        name=declaration.field,
        ok=False,
        message=f"{declaration.field} starts with executable path '{executable}', but it is not executable.",
        fix=(
            f"Install or repair '{executable}', declare an appropriate runner, "
            f"or update {declaration.field} in '{manifest.path}'."
        ),
        finding_id="BASE-P160",
        status="warn",
        details={"executable": executable, "field": declaration.field},
    )


def check_project_script_path(
    manifest: BaseManifest,
    declaration: CommandDeclaration,
    executable: str,
) -> ArtifactCheck | None:
    project_root = manifest.path.parent.resolve()
    working_dir = resolve_working_dir(project_root, declaration.working_dir)
    if working_dir is None:
        return None

    executable_path = Path(executable)
    resolved_path = executable_path if executable_path.is_absolute() else (working_dir / executable_path).resolve()
    relative_display = display_path(project_root, resolved_path)

    try:
        resolved_path.relative_to(project_root)
    except ValueError:
        return ArtifactCheck(
            name=declaration.field,
            ok=False,
            message=(
                f"{declaration.field} references script path '{executable}', "
                "which resolves outside the project root."
            ),
            fix=f"Move the script under the project root or update {declaration.field} in '{manifest.path}'.",
            finding_id="BASE-P161",
            status="warn",
            details={"path": str(resolved_path), "field": declaration.field},
        )

    if not resolved_path.exists():
        return ArtifactCheck(
            name=declaration.field,
            ok=False,
            message=f"{declaration.field} references project script '{relative_display}', but it does not exist.",
            fix=f"Create '{relative_display}' or update {declaration.field} in '{manifest.path}'.",
            finding_id="BASE-P161",
            status="warn",
            details={"path": str(resolved_path), "field": declaration.field},
        )
    if not resolved_path.is_file():
        return ArtifactCheck(
            name=declaration.field,
            ok=False,
            message=f"{declaration.field} references project script '{relative_display}', but it is not a file.",
            fix=f"Replace '{relative_display}' with a script file or update {declaration.field} in '{manifest.path}'.",
            finding_id="BASE-P161",
            status="warn",
            details={"path": str(resolved_path), "field": declaration.field},
        )
    if not os.access(resolved_path, os.X_OK):
        return ArtifactCheck(
            name=declaration.field,
            ok=False,
            message=f"{declaration.field} references project script '{relative_display}', but it is not executable.",
            fix=f"Make '{relative_display}' executable or update {declaration.field} in '{manifest.path}'.",
            finding_id="BASE-P161",
            status="warn",
            details={"path": str(resolved_path), "field": declaration.field},
        )
    return None


def resolve_working_dir(project_root: Path, declared_working_dir: str) -> Path | None:
    working_dir = Path(declared_working_dir)
    if working_dir.is_absolute():
        return None

    resolved = (project_root / working_dir).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError:
        return None
    if not resolved.is_dir():
        return None
    return resolved


def display_path(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def command_available(manifest: BaseManifest, executable: str) -> bool:
    if process.command_exists(executable):
        return True

    project_root = manifest.path.parent
    if manifest_uses_uv_project_manager(manifest):
        venv_bin = project_root / ".venv" / "bin" / executable
    else:
        venv_bin = Path.home() / ".base.d" / manifest.project_name / ".venv" / "bin" / executable
    return venv_bin.is_file() and os.access(venv_bin, os.X_OK)
