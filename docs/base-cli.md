# base_cli Runtime Package

`base_cli` is the Python CLI foundation for Base and Base-supported projects.
It wraps Click with Base conventions for runtime context, logging, run-scoped
temporary files, cache directories, configuration, and manifest-aware project
execution.

The goal is **minimal boilerplate**, not magic. Importing `base_cli` must be
cheap and side-effect free. Runtime infrastructure is initialized explicitly
when a `base_cli.App` command is invoked.

## Goals

- Make Base Python CLIs consistent without hiding Click.
- Provide a single context object with Base, project, logging, temp, and cache
  information.
- Keep CLI code readable and close to ordinary Python functions.
- Support Base itself and project CLIs that live in repositories managed by
  Base.
- Use `~/.base.d` for Base-owned user state.
- Keep v1 local-only. Cloud telemetry is intentionally out of scope.

## Non-Goals For V1

- No cloud log upload.
- No plugin system.
- No daemon/syslog integration beyond clean non-interactive behavior.
- No full caching framework.
- No automatic initialization on import.

## Future Extraction Boundary

`base_cli` should remain in the Base repository until Base's platform contract is
stable enough to support an independent Python package. The future extraction
target is a small Click-compatible runtime package that could move to its own
repository and later be published to PyPI, but that split should wait until
Linux support and the intended Windows/WSL support story have both matured.

Until then, treat extraction readiness as a design constraint for new
`base_cli` work:

- keep imports cheap, side-effect free, and safe on every supported platform;
- keep the public API explicit through `base_cli.__all__`;
- avoid putting command-specific `basectl` behavior in the runtime package;
- keep Base-owned names such as `BASE_HOME`, `BASE_CACHE_DIR`,
  `base_manifest.yaml`, and `~/.base.d` isolated and easy to adapter-wrap later;
- document and test platform-sensitive path, cache, subprocess, signal,
  encoding, and filesystem assumptions before treating them as package-stable;
- reassess IDE and project-schema helpers before extraction so Base-specific
  schema ownership does not leak into a general-purpose CLI runtime.

Extraction preparation should not add PyPI metadata, create a second repository,
or rename public APIs early. The useful work now is to keep the package boundary
clean while Linux and Windows evidence shapes the eventual public contract.

## Author Experience

```python
import base_cli

app = base_cli.App(name="greet", version="0.1.0")


@app.command()
@base_cli.option("--name", required=True, help="Name to greet.")
def main(ctx: base_cli.Context, name: str) -> None:
    ctx.log.info("Hello, %s", name)


if __name__ == "__main__":
    raise SystemExit(base_cli.run_app(app))
```

The command function receives `ctx` as its first argument. Infrastructure is
created immediately before command execution and cleaned up afterward.
`base_cli.run_app()` applies Base's command syntax guard before Click parses
arguments: long options with values must use space-separated syntax, such as
`--name Ada`; equals-form values such as `--name=Ada` are rejected.

## Package Layout

```text
lib/python/base_cli/
  __init__.py
  app.py
  config.py
  context.py
  logging.py
  paths.py
  redaction.py
  testing.py
```

## Command Shape

`App.command()` remains the simple path for a CLI with one entry point. A CLI
that needs multiple verbs should use `App.subcommand()`:

```python
app = base_cli.App(name="workspace-tools")


@app.subcommand()
def status(ctx: base_cli.Context) -> None:
    ...


@app.subcommand("sync")
@base_cli.option("--dry-run", is_flag=True)
def sync_project(ctx: base_cli.Context, dry_run: bool) -> None:
    ...
```

Each subcommand receives its own fresh `Context`, run ID, log file, temp/cache
paths, cleanup hooks, project discovery, standard options, and sensitive-option
redaction. `App.command()` and `App.subcommand()` are mutually exclusive on one
`App` so command authors do not accidentally mix single-command and group-style
registration.

## Context

`Context` is the center of the API:

```python
ctx.cli_name       # str
ctx.run_id         # str
ctx.base_home      # Path | None
ctx.project_name   # selected project name, or None
ctx.project_root   # Path | None
ctx.manifest_path  # Path | None
ctx.history_scope  # primary or internal
ctx.history_parent_run_id  # parent basectl invocation ID, or None
ctx.workspace_root # configured workspace root, or None
ctx.runtime_owner  # base or project
ctx.owner_root     # owner namespace root under the cache root
ctx.run_root       # this invocation's run bundle
ctx.state_dir      # owner_root (compatibility alias)
ctx.log_dir        # run_root/logs or run_root/logs/internal/<cli-name>
ctx.cache_dir      # owner_root/cache/components/<cli-name>
ctx.temp_dir       # run_root/tmp/<cli-name>/<run-id>
ctx.log_file       # primary.log or an internal component log, or None when disabled
ctx.config         # dict
ctx.user_config    # typed user config from ~/.base.d/config.yaml
ctx.environment    # str
ctx.debug          # bool
ctx.dry_run        # bool
ctx.keep_temp      # bool
ctx.quiet          # bool
ctx.log            # logging.Logger
```

Project discovery walks upward from the invocation directory looking for
`base_manifest.yaml`. If found, `project_root` is the manifest's parent and
`manifest_path` points to the manifest. The context does not need to fully parse
the manifest in v1; deeper manifest interpretation belongs to project setup and
artifact management.

`base_home` is read from `BASE_HOME` when available and otherwise remains
`None`. Python CLIs invoked through Base wrappers should have `BASE_HOME` set.

## State Directories

Base separates durable user state from disposable runtime artifacts. Durable
config and project virtual environments live under `~/.base.d`. Per-run logs
and temp directories live in owner-aware bundles under the Base runtime cache
root.

```text
<base-cache-root>/
  base/
    history/runs.jsonl
    runs/<run-id>/{run.json,logs/,tmp/}
    cache/components/<cli-name>/
  projects/<project>/<checkout-id>/
    runs/<run-id>/{run.json,logs/,tmp/}
    cache/components/<cli-name>/
        <run-id>/
```

The default cache root is:

| Platform | Runtime cache root |
|---|---|
| macOS | `~/Library/Caches/base` |
| Linux and other non-macOS platforms | `~/.cache/base` |

Set `BASE_CACHE_DIR` to override this root for tests, CI, or unusual local
layouts.

Directory lifecycle:

| Directory | Created | Removed |
|---|---|---|
| `run.json`, `logs/`, `tmp/` | before command execution | run-bundle cleanup |
| `cache/components/` | when a component needs it | explicit CLI cleanup |

Commands running with `ctx.dry_run` skip default `logs/`, `cache/`, and
`tmp/<run-id>/` creation unless an explicit log file is supplied.

Commands that inspect runtime artifacts can opt out of default persistent log
creation with `base_cli.App(log_to_file=False)`. That still provides a context
and the standard user-facing stderr logger, including `--debug`, but leaves
`ctx.log_file` as `None` and does not create the default `logs/`, `cache/`, or
`tmp/<run-id>/` directories. `base_logs` uses this mode so `basectl logs` does
not create a new log entry while listing logs. Passing `--log-file <path>` still
writes to that explicit file.

## Logging

Every run gets two streams:

| Stream | Destination | Level | Format |
|---|---|---|---|
| user | stderr | INFO by default, DEBUG with `--debug` | UTC timestamp, level, source, message |
| persistent | `ctx.log_file` when enabled | DEBUG | UTC timestamp, level, source, message |

Python user-facing logs should visually align with Bash `lib_std.sh` logs while
making the timezone explicit:

```text
2026-05-23 19:31:04 UTC INFO    cli/python/base_setup/engine.py:67 Reading Base manifest at '.../base_manifest.yaml'.
```

`base_cli` logs invocation metadata at DEBUG level:

- CLI name
- run ID
- argv with sensitive values redacted
- platform
- Python version
- project root and manifest path when discovered

The public convenience API mirrors the logger:

```python
base_cli.log_debug("message")
base_cli.log_info("message")
base_cli.log_warning("message")
base_cli.log_error("message")
base_cli.log_critical("message")
```

These functions log to the current active context. CLI code should prefer
`ctx.log` when it already has a context.

## Redaction

Options may be marked sensitive:

```python
@base_cli.option("--api-key", sensitive=True)
```

Options may also be marked as the command's dry-run control when they use a
nonstandard parameter name:

```python
@base_cli.option("--preview", is_flag=True, dry_run=True)
```

For v1, sensitive values are redacted from automatic invocation logging. More
advanced redaction of arbitrary log messages can follow after the basic CLI
shape is stable.

## Configuration

Configuration is resolved from lowest to highest precedence:

1. Code defaults
2. User config: `~/.base.d/config.yaml`
3. Project config: `<project-root>/.base/config.yaml`
4. Environment variables
5. Command line options
6. Explicit runtime API overrides

V1 intentionally does not read machine-wide or organization-wide config
implicitly. In particular, Base must not silently load `/etc/base.d/config.yaml`
or any other global policy file during local CLI startup. That keeps a new
checkout and a local developer shell deterministic unless the user or wrapper
explicitly opts into an additional config source.

V1 implements the shape and context fields, but only needs a minimal config
loader: YAML files are merged when present, environment is read from
`BASE_CLI_ENVIRONMENT`, and CLI options can override `--environment`, `--debug`,
`--keep-temp`, and `--log-file`.

`ctx.config` remains the merged raw configuration dictionary. `ctx.user_config`
is the typed machine-local user config, so command authors can read
`ctx.user_config.workspace.root` and IDE preferences without re-parsing the user
config file.

Standard environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `BASE_CLI_ENVIRONMENT` | active environment | `dev` |
| `BASE_CLI_LOG_LEVEL` | user stream log level | `info` |
| `BASE_CLI_KEEP_TEMP` | keep run temp directory | `false` |
| `BASE_CLI_TEMP_RETENTION_DAYS` | prune retained temp dirs older than N days | `7` |

### Future Organization Policy

Base may later support machine- or organization-managed defaults, but that
feature should be designed as explicit policy rather than another hidden config
layer.

Recommended shape:

1. Organization policy lives outside project repositories and user-managed Base
   state. `/etc/base.d/config.yaml` is acceptable on managed machines, but it is
   not special unless explicitly enabled.
2. Users or enterprise wrappers opt in with an environment variable such as
   `BASE_ORG_CONFIG=/etc/base.d/config.yaml`, or a future Base launcher flag
   with equivalent behavior.
3. `base_cli` exposes the resolved config source list through context and a
   future inspection command, so users can see exactly which files influenced a
   run.
4. Policy config is normally a defaults layer between code defaults and user
   config. A later enforcement model may add locked keys, but locked policy must
   be visible in inspection output and should fail loudly when a user or project
   attempts to override it.
5. Missing, unreadable, or invalid opt-in policy files fail the command instead
   of being silently skipped. Optional policy should be represented by not
   setting the opt-in variable.

## Standard Options

Direct `base_cli.App` command packages get:

| Option | Purpose |
|---|---|
| `--debug` | enable DEBUG on the user-facing stream |
| `--environment <name>` | set the active environment |
| `--config <path>` | load an additional config file |
| `--keep-temp` | preserve this run's temp directory |
| `--log-file <path>` | override the persistent log file |
| `--version` | show the CLI version when configured |
| `--help` | Click help |

Long option values must use the space-separated form, for example
`--environment prod`. Base rejects `--option=value` before Click parses
arguments.

These are direct Python package options. Public `basectl` launchers expose
`-v` for command-level debug logs and command-specific flags from
`basectl <command> --help`; they do not expose `--debug`, `--quiet`,
`--log-file`, `--config`, `--environment`, or `--keep-temp` as public
`basectl` options.

## Interrupt And Cleanup

`base_cli` may register signal handlers while a command is running. It must not
register them on import. Cleanup should:

1. call user cleanup hooks
2. flush and close log handlers
3. remove `ctx.temp_dir` unless `keep_temp` is true

CLI authors can register hooks:

```python
ctx.on_cleanup(close_connection)
```

## Testing

The package should include a small test helper:

```python
result = base_cli.testing.invoke(app, ["--debug"], cwd=project_root)
```

This wraps Click's test runner and gives tests access to isolated `HOME`,
captured output, generated Base state, and an explicit invocation directory for
project discovery or no-project test cases.

When a test `HOME` is supplied, the helper should default `BASE_CACHE_DIR` to
`<home>/.cache/base` so invocations do not inherit a developer's real cache
root. Tests that need a custom cache path can pass an explicit environment
override.

## Phases

### V1

- `App`
- `Context`
- Click wrapper decorators
- standard options
- state directories under `~/.base.d`
- user and file logging
- run-scoped temp directory cleanup
- cache directory provisioning
- sensitive option redaction for invocation logging
- manifest/project discovery
- testing helper

### V2

- richer YAML config merging
- project manifest loading helpers
- version discovery conventions
- nested command-group helpers beyond the current `App.subcommand()` API
- better error formatting and exit code conventions

### V3

- headless/syslog behavior
- retained-temp pruning
- structured persistent logs

### V4

- optional cloud telemetry, with explicit opt-in, documented payloads, and
  organization-level policy controls.

## Summary

`base_cli` should feel like Click with Base batteries included. It should make
the common path short, make runtime state visible through `Context`, and avoid
surprising import-time side effects.
