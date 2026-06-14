# `base_cli`

`base_cli` is Base's small Python framework for writing command-line tools that
feel consistent across Base and Base-supported projects.

It is intentionally thin. Click still owns argument parsing and command
execution, while `base_cli` adds the Base-specific behavior every project CLI
should get by default:

- standard command options such as `--debug`, `--environment`, `--config`,
  `--keep-temp`, and `--log-file`
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
    app()
```

Running this command automatically adds the standard Base options:

```bash
hello --name Ada
hello --debug --name Ada
hello --environment prod --name Ada
hello --keep-temp --name Ada
hello --log-file /tmp/hello.log --name Ada
```

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

Both `--token secret` and `--token=secret` are redacted in debug logs.

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

## Standard Options

Every `base_cli.App` command gets these options:

- `--debug`: enable DEBUG logging on the user-facing stderr stream.
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
- `ctx.manifest_path`: nearest discovered Base manifest.
- `ctx.state_dir`: per-CLI runtime directory under the Base cache root.
- `ctx.log_dir`: persistent log directory.
- `ctx.cache_dir`: persistent cache directory.
- `ctx.temp_dir`: per-run temp directory.
- `ctx.log_file`: persistent log file for this run, or `None` when persistent
  logging is disabled.
- `ctx.config`: merged configuration dictionary.
- `ctx.environment`: active environment, defaulting to `dev`.
- `ctx.debug`: whether debug logging is enabled for the stderr stream.
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

- a user-facing stderr handler at INFO by default, DEBUG with `--debug`
- a persistent file handler that records DEBUG logs when persistent logging is
  enabled

Commands that inspect runtime artifacts can use `base_cli.App(log_to_file=False)`
to keep the standard context and `--debug` behavior without creating default
`logs/`, `cache/`, or `tmp/<run-id>/` directories. `base_logs` uses this mode so
`basectl logs` does not appear in its own output. An explicit `--log-file <path>`
still enables file logging for that invocation.

Commands running with `ctx.dry_run` also skip default `logs/`, `cache/`, and
`tmp/<run-id>/` creation. Passing `--log-file <path>` still writes to that
explicit file so tests and diagnostics can inspect dry-run logs when needed.

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

Command-line standard options are applied after config is loaded. For example,
`--environment prod` overrides `environment: dev` from config.

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

On macOS, current runtime state is rooted at `~/Library/Caches/base`:

```text
~/Library/Caches/base/cli/<cli-name>/
  logs/
  cache/
  tmp/<run-id>/
```

On Linux and other non-macOS platforms, the default is `~/.cache/base`. Use
`BASE_CACHE_DIR` to override the root for tests, CI, or unusual local
environments.

`logs/` and `cache/` are runtime artifacts that can be pruned with
`basectl clean --older-than <age>`. Logs can also be pruned with
`basectl clean --keep-last <count>`, which keeps the newest log files per CLI log
directory. `tmp/<run-id>/` is deleted automatically after the command returns
unless `--keep-temp` is set; retained temp entries can also be pruned by
`basectl clean`.

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
    (project / "base_manifest.yaml").write_text("project:\n  name: demo\n")

    result = invoke(app, ["--name", "Ada"], home=tmp_path, cwd=project)

    assert result.exit_code == 0
    assert "hello Ada" in result.stdout
```

The helper wraps Click's `CliRunner`, sets `HOME` when requested, changes to
`cwd` only for the invocation, and keeps stderr separate on Click versions that
support it. Use `cwd` for commands whose behavior depends on project discovery,
including tests that intentionally run outside a Base project.

When `home` is supplied, `invoke()` also defaults `BASE_CACHE_DIR` to
`<home>/.cache/base` so helper-based tests do not inherit a developer's real
cache root. Pass `env={"BASE_CACHE_DIR": str(path)}` when a test needs an
explicit cache location.

## When To Use `base_cli`

Use `base_cli` for Python commands that are part of Base or a Base-supported
project and need standard Base behavior.

It is a good fit for:

- project discovery commands
- setup and artifact management commands
- developer workflow commands
- CLIs that need predictable logs, temp directories, and config precedence

It is not meant to replace Click, Typer, argparse, or rich terminal UI
frameworks. It is the Base layer around command lifecycle, context, logging,
configuration, and state.
