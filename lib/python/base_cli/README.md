# `base_cli`

`base_cli` is Base's small Python framework for writing command-line tools that
feel consistent across Base and Base-supported projects.

It is intentionally thin. Click still owns argument parsing and command
execution, while `base_cli` adds the Base-specific behavior every project CLI
should get by default:

- standard command options such as `--debug`, `--quiet`, `--environment`,
  `--config`, `--keep-temp`, and `--log-file`
- structured logging to stderr and, by default, to a persistent per-run log file
- Base project discovery through `base_manifest.yaml`
- config loading with predictable precedence
- per-run temp directories, persistent cache directories, and cleanup hooks
- sensitive argument redaction in debug invocation logs
- a command context object shared by command code and helper functions
- test helpers built on Click's `CliRunner`

## Design Goals

Base CLI tools should be easy to write, but not magical. A command should be
explicitly registered, receive an explicit `Context`, and use standard Python
functions instead of import-time side effects.

The package follows these rules:

- **Decorator-driven setup**: commands opt in by creating an `App` and
  decorating a function.
- **Logs go to stderr**: user-facing program output can stay on stdout, while
  logs remain redirectable and skippable.
- **Every run has a context**: logs, paths, config, environment, manifest, and
  cleanup are available through one object.
- **No import-time filesystem writes**: state directories are created only when
  a command runs.
- **Base-aware, Click-compatible**: command authors keep using familiar Click
  concepts such as options and arguments.

## Minimal Command

```python
from __future__ import annotations

import base_cli


app = base_cli.App(name="hello", version="0.1.0")


@app.command()
@base_cli.option("--name", required=True)
def main(ctx: base_cli.Context, name: str) -> None:
    ctx.log.info("starting hello")
    print(f"hello {name}")


if __name__ == "__main__":
    raise SystemExit(base_cli.run_app(app))
```

Running this command directly as a Python package automatically adds the
standard Base options:

```bash
hello --name Ada
hello --debug --name Ada
hello --quiet --name Ada
hello --environment prod --name Ada
hello --keep-temp --name Ada
hello --log-file /tmp/hello.log --name Ada
```

Long options with values use space-separated syntax. `base_cli.run_app()` rejects
equals-form values such as `--name=Ada` before Click parses arguments.
These are direct package options. Public `basectl` launchers expose `-v` for
command-level debug logs and command-specific flags from
`basectl <command> --help`; they do not expose `--debug`, `--quiet`,
`--log-file`, `--config`, `--environment`, or `--keep-temp` as public
`basectl` options.

## Command Registration

Use `App` when you want a named command:

```python
app = base_cli.App(name="base-projects", version="0.1.0")
```

Register the command function explicitly:

```python
@app.command()
def main(ctx: base_cli.Context) -> None:
    ...
```

The command function always receives `ctx` as its first argument. User-defined
options and arguments are passed after the Base standard options have been
removed from Click's keyword arguments.

For small scripts, the module-level decorators are available:

```python
@base_cli.command()
def main(ctx: base_cli.Context) -> None:
    ...
```

In Base itself, prefer an explicit `App` so command names and versions are
obvious at the top of the module.

Use `@app.subcommand()` when one CLI needs multiple verbs while keeping Base's
standard context, logging, redaction, and cleanup lifecycle for each invocation:

```python
app = base_cli.App(
    name="workspace-tools",
    version="0.1.0",
    help="Inspect and sync workspace projects.",
)


@app.subcommand()
@base_cli.argument("project")
def status(ctx: base_cli.Context, project: str) -> None:
    ctx.log.info("checking %s", project)


@app.subcommand("sync")
@base_cli.option("--dry-run", is_flag=True)
def sync_project(ctx: base_cli.Context, dry_run: bool) -> None:
    if ctx.dry_run:
        ctx.log.info("previewing sync")
```

Subcommands use the same `base_cli.option()` and `base_cli.argument()` metadata
as single commands. `App(help=...)` appears in the command group's `--help`
output. For subcommand apps, prefer standard Base options before the subcommand
name, for example `workspace-tools --debug status demo`. The post-subcommand
form, such as `workspace-tools status --debug demo`, remains accepted for
compatibility. Use either `@app.command()` for a single-command CLI or
`@app.subcommand()` for a command group; do not mix the two registration styles
on one `App`.

## Options And Arguments

`base_cli.option` and `base_cli.argument` mirror Click's decorators:

```python
@app.command()
@base_cli.argument("project")
@base_cli.option("--workspace", type=str)
def main(ctx: base_cli.Context, project: str, workspace: str | None) -> None:
    ...
```

Use `sensitive=True` for options whose values should not appear in invocation
logs:

```python
@base_cli.option("--token", sensitive=True, required=True)
def main(ctx: base_cli.Context, token: str) -> None:
    ...
```

Both `--token secret` and an externally supplied `--token=secret` token are
redacted in debug logs, even though Base command invocation rejects equals-form
option values before Click parses them.

Use `dry_run=True` when a nonstandard option should drive `ctx.dry_run` and
Base's default durable-write suppression:

```python
@base_cli.option("--preview", is_flag=True, dry_run=True)
def main(ctx: base_cli.Context, preview: bool) -> None:
    if ctx.dry_run:
        ctx.log.info("previewing changes")
```

The conventional `dry_run` parameter is recognized automatically, so commands
using `@base_cli.option("--dry-run", is_flag=True)` do not need the marker.
Only one option on a command may be marked `dry_run=True`; duplicate dry-run
markers fail during command registration so authors do not accidentally ship an
option that is ignored by `ctx.dry_run`.

## Standard Options

Every `base_cli.App` command gets these options:

- `--debug`: enable DEBUG logging on the user-facing stderr stream.
- `--quiet`, `-q`: suppress INFO logs on the user-facing stderr stream.
- `--environment <name>`: set `ctx.environment` for the run.
- `--config <path>`: merge an additional YAML config file.
- `--keep-temp`: preserve the run's temp directory after command completion.
- `--log-file <path>`: write the persistent log to a specific file.
- `--version`: shown when the `App` was created with a version.

The command receives only its own application-specific options. Standard options
are consumed before the command function is called.

## Exit Codes

Use `base_cli.ExitCode` when command code or tests need to name Base's standard
command result meanings:

- `ExitCode.SUCCESS` (`0`): the command completed successfully.
- `ExitCode.FAILURE` (`1`): the command was valid, but an operational problem
  prevented successful completion.
- `ExitCode.USAGE_ERROR` (`2`): the command could not proceed because user
  input, configuration, or environment setup was invalid or incomplete.

Existing commands can keep returning integers. New code should prefer the named
constants when it makes intent clearer:

```python
if ctx.project_root is None:
    ctx.log.error("run this command from a Base project")
    return base_cli.ExitCode.USAGE_ERROR
```

## Context

`Context` is the object command code should pass around instead of rediscovering
Base paths or global settings.

Important fields include:

- `ctx.cli_name`: normalized CLI name used for state paths and logger names.
- `ctx.run_id`: timestamp plus short random suffix for this invocation.
- `ctx.base_home`: resolved `BASE_HOME`, when available.
- `ctx.project_root`: directory containing the nearest `base_manifest.yaml`.
- `ctx.workspace_root`: configured workspace root from `~/.base.d/config.yaml`.
- `ctx.manifest_path`: nearest discovered Base manifest.
- `ctx.history_scope`: whether this record is a primary or internal event.
- `ctx.history_parent_run_id`: parent `basectl` invocation ID, when delegated.
- `ctx.runtime_owner`: `base` or `project`.
- `ctx.owner_root`: owner namespace root under the Base cache root.
- `ctx.run_root`: this invocation's run bundle.
- `ctx.state_dir`: owner root (compatibility alias).
- `ctx.log_dir`: run-bundle log directory.
- `ctx.cache_dir`: persistent component cache directory.
- `ctx.temp_dir`: per-run temp directory inside the bundle.
- `ctx.log_file`: persistent log file for this run, or `None` when persistent
  logging is disabled.
- `ctx.config`: merged configuration dictionary.
- `ctx.user_config`: typed user configuration from `~/.base.d/config.yaml`.
- `ctx.environment`: active environment, defaulting to `dev`.
- `ctx.debug`: whether debug logging is enabled for the stderr stream.
- `ctx.quiet`: whether INFO logs are suppressed on the stderr stream.
- `ctx.dry_run`: whether the command is running in a no-durable-write mode.
- `ctx.keep_temp`: whether `ctx.temp_dir` should survive cleanup.
- `ctx.log`: standard Python logger configured by Base.

Helpers can retrieve the active context without threading it through every call:

```python
from base_cli import get_current_context


def helper() -> None:
    ctx = get_current_context()
    ctx.log.debug("helper is running")
```

`get_current_context()` is valid only while a `base_cli.App` command is running.

## Logging

`base_cli` configures two handlers:

- a user-facing stderr handler at INFO by default, DEBUG with `--debug`, or
  WARNING with `--quiet` / `-q`
- a persistent file handler that records DEBUG logs when persistent logging is
  enabled

`--quiet` suppresses INFO output on the user-facing stream but still shows
warnings and errors. `--debug` and `--quiet` cannot be used together. Persistent
log files still receive DEBUG-level detail, including INFO messages suppressed
from stderr.

Advanced tests and CI wrappers can call `base_cli.configure_logger(...,
stream=..., formatter=...)` to capture user-facing logs or apply a custom
formatter without replacing Base's logger setup. Leave those arguments as
`None` to keep the default stderr stream and `BaseCliFormatter`. Base CLI log
timestamps use the host's local timezone and include its numeric offset by
default. When the wrapper sets `LOG_UTC=1` (for example via
`basectl --utc-wrapper`), they use UTC and include an explicit `UTC` marker.

This setting affects log presentation only. Run metadata, history records, and
run IDs retain their canonical UTC representation.

Commands that inspect runtime artifacts can use `base_cli.App(log_to_file=False)`
to keep the standard context, `--debug`, and `--quiet` behavior without creating
default `logs/`, `cache/`, or `tmp/<run-id>/` directories. `base_logs` uses this
mode so `basectl logs` does not appear in its own output; `base_history` does
the same for `basectl history`. An explicit `--log-file <path>` still enables
file logging for that invocation.

Commands running with `ctx.dry_run` also skip default `logs/`, `cache/`, and
`tmp/<run-id>/` creation. Passing `--log-file <path>` still writes to that
explicit file so tests and diagnostics can inspect dry-run logs when needed.

For Python-backed commands with persistent logs, `base_cli.App` also writes a
best-effort final history record to `<base-cache-root>/base/history/runs.jsonl`.
History records contain redacted command metadata, timing, exit status, project
context when known, and a pointer to the raw log file. History writes are local
only and do not fail the user command when the index cannot be updated.

High-frequency tools can set `base_cli.App(max_log_files=<count>)` to keep at
most that many default persistent log files across the owner's run bundles.
Retention runs during startup after the current run's default log file is
resolved, and the current run's log file is never pruned. The policy is skipped
for `ctx.dry_run`,
`log_to_file=False`, and explicit `--log-file` paths so no-durable-write modes
and caller-selected log locations stay under caller control. Use this as a
small guardrail for busy local tools; `basectl clean` remains the broader
maintenance command for caches, logs, and retained temp files.

Logs use the same general shape as Base Bash logs:

```text
2026-05-26 12:34:56 INFO    path/to/file.py:42 message
```

Use either `ctx.log` directly:

```python
ctx.log.info("processed %s items", count)
```

or the convenience functions:

```python
base_cli.log_debug("cache_dir=%s", ctx.cache_dir)
base_cli.log_info("done")
base_cli.log_warning("using fallback")
base_cli.log_error("failed")
```

Program output should still use stdout when another command might consume it.
Logs should stay on stderr so users can redirect or ignore logs without losing
the real command output.

## Config Precedence

Configuration is loaded from YAML files and environment variables in this order:

1. user config: `~/.base.d/config.yaml`
2. project config: `<project>/.base/config.yaml`
3. explicit config from `--config`
4. environment variables
5. direct command-line standard options

Environment variables currently recognized by the config layer:

- `BASE_CLI_ENVIRONMENT`
- `BASE_CLI_LOG_LEVEL`
- `BASE_CLI_KEEP_TEMP`

`LOG_DEBUG=1` or `LOG_DEBUG=true` is also accepted as an internal compatibility
fallback for wrapper/debug paths when `BASE_CLI_LOG_LEVEL` is unset. Prefer
`BASE_CLI_LOG_LEVEL=debug` for user-facing Python CLI debug logging.

Command-line standard options are applied after config is loaded. For example,
`--environment prod` overrides `environment: dev` from config.

`ctx.config` exposes the merged raw configuration after user, project,
explicit, and environment layers are applied. `ctx.user_config` exposes only the
typed machine-local user config, including `workspace.root`,
`workspace.manifest`, and IDE
preferences, so command code does not need to re-read `~/.base.d/config.yaml`
for those structured values.

The user config file is machine-local by default. Base owns the semantics of
`~/.base.d/config.yaml`, while users own backup and sync choices such as iCloud,
chezmoi, dotfiles repositories, Time Machine, or manual copy. See
`docs/local-config.md` for the product-level boundary.

## Project Discovery

When a command runs, `base_cli` walks upward from the current working directory
looking for `base_manifest.yaml`.

If found:

- `ctx.manifest_path` points to the manifest
- `ctx.project_root` points to the manifest's parent directory

If no manifest is found, both fields are `None`. Commands that require a Base
project should validate this explicitly and return a clear usage error or
actionable message.

## Runtime Directories

Runtime state is rooted at `~/Library/Caches/base` on macOS and `~/.cache/base`
elsewhere. `BASE_CACHE_DIR` overrides the root. See
[`docs/cache-ownership-and-layout.md`](../../../docs/cache-ownership-and-layout.md)
for the owner-aware layout. Base control-plane commands use `base/`; a
Base-compliant project's own commands use `projects/<project>/<checkout-id>/`.
Each invocation is a run bundle containing private (`0600`) `run.json`,
`logs/`, and `tmp/`,
while persistent component caches live in the owner's `cache/components/`.
`basectl clean --older-than <age>` removes old bundles and component caches;
`--keep-last <count>` retains the newest completed bundles per owner.

Use `ctx.on_cleanup()` for cleanup work that should happen even when helper code
does not own the main command wrapper:

```python
def close_connection() -> None:
    connection.close()


ctx.on_cleanup(close_connection)
```

Cleanup hooks run before temp directory removal. Hook failures are logged as
warnings and do not prevent later hooks from running.

## Testing

Use `base_cli.testing.invoke` for unit tests:

```python
from pathlib import Path

from base_cli.testing import invoke


def test_command(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    result = invoke(
        app,
        ["--name", "Ada"],
        home=tmp_path,
        cwd=project,
        manifest={"project": {"name": "demo"}, "artifacts": []},
    )

    assert result.exit_code == 0
    assert "hello Ada" in result.stdout
```

The helper wraps Click's `CliRunner`, sets `HOME` when requested, supplies
`cwd` to Base's context discovery without mutating process-global cwd, and keeps
stderr separate on Click versions that support it. Use `cwd` for commands whose
behavior depends on project discovery, including tests that intentionally run
outside a Base project. Pass
`manifest={...}` with `cwd` to write a temporary `base_manifest.yaml` before
the command runs.

When `home` is supplied, `invoke()` also defaults `BASE_CACHE_DIR` to
`<home>/.cache/base` so helper-based tests do not inherit a developer's real
cache root. Pass `env={"BASE_CACHE_DIR": str(path)}` when a test needs an
explicit cache location.

## When To Use `base_cli`

Use `base_cli` for Python commands that are part of Base or a Base-supported
project and need standard Base behavior.

Base public command engines under `cli/python/base_*/engine.py` should
instantiate `base_cli.App` so standard options, logging, redaction, runtime
state, and local command history stay consistent. If a future public Python
engine intentionally bypasses this lifecycle, document the reason in code and
in this guide, then add it as an explicit lifecycle-audit exemption. Shell-only
helpers that avoid Python startup, such as `basectl config path`, do not create
Python logs or history records; once a `basectl` path enters a Python command
package, it should participate in `base_cli.App`.

It is a good fit for:

- project discovery commands
- setup and artifact management commands
- developer workflow commands
- CLIs that need predictable logs, temp directories, and config precedence

It is not meant to replace Click, Typer, argparse, or rich terminal UI
frameworks. It is the Base layer around command lifecycle, context, logging,
configuration, and state.
