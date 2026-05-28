from __future__ import annotations

import json
import sys
from pathlib import Path

from base_cli.config import load_user_config, user_config_path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "show"
    if command in ("-h", "--help", "help"):
        print_usage()
        return 0
    if len(args) > 1:
        print_usage(file=sys.stderr)
        print(f"ERROR: config {command} does not accept arguments.", file=sys.stderr)
        return 2
    if command == "show":
        return show_config_command()
    if command == "doctor":
        return doctor_config_command()

    print_usage(file=sys.stderr)
    print(f"ERROR: Unknown config command '{command}'. Supported commands: show, doctor.", file=sys.stderr)
    return 2


def print_usage(file=sys.stdout) -> None:
    print(
        """Usage:
  base_config show
  base_config doctor

Purpose:
  Inspect Base's machine-local user config.""",
        file=file,
    )


def show_config_command() -> int:
    try:
        config = load_user_config()
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(config, indent=2, sort_keys=True))
    return 0


def doctor_config_command() -> int:
    path = user_config_path()
    print("\nBase config doctor\n")
    print_finding("ok", "path", f"Config path: {path}")
    if path.exists():
        if path.is_symlink():
            print_finding("ok", "symlink", f"Config path is a symlink to '{safe_resolve(path)}'.")
        else:
            print_finding("ok", "file", "Config file exists.")
    else:
        print_finding("warn", "file", "Config file is missing; Base will use an empty user config.")
        return 0

    try:
        config = load_user_config()
    except (RuntimeError, ValueError) as exc:
        print_finding("error", "yaml", str(exc))
        return 1

    print_finding("ok", "yaml", "Config YAML is valid.")
    print_finding("ok", "mapping", f"Config contains {len(config)} top-level key(s).")
    return 0


def safe_resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError:
        return path


def print_finding(status: str, name: str, message: str) -> None:
    print(f"{status:<5}  {name:<12}  {message}")
