from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import base_cli
from base_cli.config import UserConfig, load_user_config, read_user_config, user_config_path
from base_cli.redaction import REDACTED, is_secret_key, redact_text_value


app = base_cli.App(
    name="base_config",
    help="Inspect Base's machine-local user config.",
)


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("command", required=False, metavar="[show|doctor]")
@base_cli.argument("arguments", nargs=-1)
def run(ctx: base_cli.Context, command: str | None, arguments: tuple[str, ...]) -> int:
    del ctx
    command = command or "show"
    if command == "show":
        if arguments:
            print_usage(file=sys.stderr)
            print("ERROR: config show does not accept arguments.", file=sys.stderr)
            return 2
        return show_config_command()
    if command == "doctor":
        if arguments:
            print_usage(file=sys.stderr)
            print("ERROR: config doctor does not accept arguments.", file=sys.stderr)
            return 2
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
  Inspect Base's machine-local user config.

Notes:
  - config show redacts secret-shaped keys and URL credentials.""",
        file=file,
    )


def show_config_command() -> int:
    try:
        config = load_user_config()
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(redact_config(config), indent=2, sort_keys=True))
    return 0


def redact_config(value: Any, key: str | None = None) -> Any:
    if key is not None and is_secret_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {name: redact_config(item, str(name)) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_config(item) for item in value]
    if isinstance(value, str):
        return redact_text_value(value)
    return value


def doctor_config_command() -> int:
    path = user_config_path()
    print("\nBase config doctor\n")
    print_finding("ok", "path", f"Config path: {path}")
    if path.is_symlink():
        if path.exists():
            print_finding("ok", "symlink", f"Config path is a symlink to '{safe_resolve(path)}'.")
        else:
            print_finding("warn", "symlink", f"Config path is a broken symlink to '{safe_resolve(path)}'.")
            return 0
    elif path.exists():
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
    try:
        user_config = read_user_config()
    except (RuntimeError, ValueError) as exc:
        print_finding("error", "schema", str(exc))
        return 1

    print_workspace_findings(user_config)
    print_github_findings(user_config)
    return 0


def print_workspace_findings(user_config: UserConfig) -> None:
    if user_config.workspace.root is None:
        print_finding(
            "warn",
            "workspace",
            "workspace.root is not configured; project discovery falls back to BASE_HOME's parent.",
        )
    elif user_config.workspace.root.is_dir():
        print_finding("ok", "workspace", f"workspace.root points to '{user_config.workspace.root}'.")
    else:
        print_finding("warn", "workspace", f"workspace.root '{user_config.workspace.root}' is not a directory.")


def print_github_findings(user_config: UserConfig) -> None:
    if user_config.github.default_owner is None:
        print_finding(
            "ok",
            "github_owner",
            "github.default_owner is not configured; short repo clone names require --owner.",
        )
    else:
        print_finding("ok", "github_owner", f"github.default_owner is '{user_config.github.default_owner}'.")

    if user_config.github.clone_protocol is None:
        print_finding(
            "ok",
            "github_proto",
            "github.clone_protocol is not configured; repo clone defaults to 'ssh'.",
        )
    else:
        print_finding("ok", "github_proto", f"github.clone_protocol is '{user_config.github.clone_protocol}'.")


def safe_resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError:
        return path


def print_finding(status: str, name: str, message: str) -> None:
    print(f"{status:<5}  {name:<12}  {message}")
