# base_cli Design

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

## Author Experience

```python
import base_cli

app = base_cli.App(name="greet", version="0.1.0")


@app.command()
@base_cli.option("--name", required=True, help="Name to greet.")
def main(ctx: base_cli.Context, name: str) -> None:
    ctx.log.info("Hello, %s", name)


if __name__ == "__main__":
    app()
```

The command function receives `ctx` as its first argument. Infrastructure is
created immediately before command execution and cleaned up afterward.

## Package Layout

```text
cli/python/base_cli/
  __init__.py
  app.py
  config.py
  context.py
  logging.py
  paths.py
  redaction.py
  testing.py
```

## Context

`Context` is the center of the API:

```python
ctx.cli_name       # str
ctx.run_id         # str
ctx.base_home      # Path | None
ctx.project_root   # Path | None
ctx.manifest_path  # Path | None
ctx.state_dir      # ~/.base.d/cli/<cli-name>
ctx.log_dir        # state_dir/logs
ctx.cache_dir      # state_dir/cache
ctx.temp_dir       # state_dir/tmp/<run-id>
ctx.log_file       # log_dir/<run-id>.log
ctx.config         # dict
ctx.environment    # str
ctx.debug          # bool
ctx.keep_temp      # bool
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

All Base-owned user state remains under `~/.base.d`.

```text
~/.base.d/
  cli/
    <cli-name>/
      logs/
        <run-id>.log
      cache/
      tmp/
        <run-id>/
```

Directory lifecycle:

| Directory | Created | Removed |
|---|---|---|
| `logs/` | before command execution | never by default |
| `cache/` | before command execution | explicit CLI logic only |
| `tmp/<run-id>/` | before command execution | after command execution unless kept |

## Logging

Every run gets two streams:

| Stream | Destination | Level | Format |
|---|---|---|---|
| user | stderr | INFO by default, DEBUG with `--debug` | concise text |
| persistent | `ctx.log_file` | DEBUG | timestamped text |

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

For v1, sensitive values are redacted from automatic invocation logging. More
advanced redaction of arbitrary log messages can follow after the basic CLI
shape is stable.

## Configuration

Configuration is resolved from lowest to highest precedence:

1. Code defaults
2. System config: `/etc/base.d/config.yaml`
3. User config: `~/.base.d/config.yaml`
4. Project config: `<project-root>/.base/config.yaml`
5. Environment variables
6. Command line options
7. Explicit runtime API overrides

V1 implements the shape and context fields, but only needs a minimal config
loader: YAML files are merged when present, environment is read from
`BASE_CLI_ENVIRONMENT`, and CLI options can override `--environment`, `--debug`,
`--keep-temp`, and `--log-file`.

Standard environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `BASE_CLI_ENVIRONMENT` | active environment | `dev` |
| `BASE_CLI_LOG_LEVEL` | user stream log level | `info` |
| `BASE_CLI_KEEP_TEMP` | keep run temp directory | `false` |
| `BASE_CLI_TEMP_RETENTION_DAYS` | prune retained temp dirs older than N days | `7` |

## Standard Options

Every `base_cli.App` command gets:

| Option | Purpose |
|---|---|
| `--debug` | enable DEBUG on the user-facing stream |
| `--environment <name>` | set the active environment |
| `--config <path>` | load an additional config file |
| `--keep-temp` | preserve this run's temp directory |
| `--log-file <path>` | override the persistent log file |
| `--version` | show the CLI version when configured |
| `--help` | Click help |

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
result = base_cli.testing.invoke(app, ["--debug"])
```

This wraps Click's test runner and gives tests access to isolated `HOME`,
captured output, and generated Base state.

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
- subcommand groups
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
