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

## Standalone Package Boundary

`base_cli` is maintained in the standalone
[`base-cli`](https://github.com/basefoundry/base-cli) repository and published
as the `base-cli` distribution. Base consumes it through the provider contract
below; Base-owned command behavior remains in `cli/python/`.

Treat the package boundary as a design constraint for new Base work:

- keep imports cheap, side-effect free, and safe on every supported platform;
- keep the public API explicit through `base_cli.__all__`;
- avoid putting command-specific `basectl` behavior in the runtime package;
- keep Base-owned names such as `BASE_HOME`, `BASE_CACHE_DIR`,
  `base_manifest.yaml`, and `~/.base.d` isolated and easy to adapter-wrap later;
- document and test platform-sensitive path, cache, subprocess, signal,
  encoding, and filesystem assumptions before treating them as package-stable;
- reassess IDE and project-schema helpers before extraction so Base-specific
  schema ownership does not leak into a general-purpose CLI runtime.

The standalone repository owns package metadata, versioning, licensing, public
API tests, and release workflow. Base owns provider selection and compatibility
tests for its own command integration. Base-specific command-protocol schemas
and the `BASE_COMMAND_PROTOCOL_V1` Bash compatibility header live in
`cli/python/base_cli_adapters/protocol.py`; the standalone package owns only
generic protocol framing and schema registration.
Base history and log filtering similarly use an adapter-owned compatibility
policy for legacy `base_` command names; standalone consumers can provide
their own normalizer to the generic `base_cli.command_filters` helpers.

## Standalone Provider Resolution

Base consumes `base_cli` through the same source-versus-installed
provider model used by `base-bash-libs`:

1. an explicit `BASE_CLI_SOURCE_DIR` source root for tests and nonstandard worktrees;
2. the sibling checkout `$BASE_HOME/../base-cli/lib/python` during source
   development;
3. the installed `base-cli` distribution in Base's selected Python environment.

The source roots contain `base_cli/__init__.py`; callers continue to use the
normal `import base_cli` API. Base injects a source root into `PYTHONPATH` only
when one of the first two providers is selected. With no source checkout,
Python resolves the installed distribution normally. `BASE_CLI_SOURCE` reports
the selected provider, and an explicit or sibling path that exists but is
malformed fails loudly instead of silently selecting a different version.

The release-pinned provider, currently **v0.4.3**, is authoritative for released
Base. Compatible moving source checkouts are also supported for development;
their version string alone does not establish compatibility. CI runs the full
source suite against both the pinned tag and current `base-cli` main, using
sibling resolution, and checks installed and explicit-source capabilities in
each job. A moving-source pass does not replace immutable release-BOM evidence.

Before dispatch, Base's isolated Python entrypoint checks the capabilities
listed in `base_cli_adapters.provider`, including protocol, history, context,
configuration, path, runtime layout, and run-index refresh dependencies. An
incompatible provider reports its selected path and repair instructions. Source
overrides continue to take precedence over installed packages: installing the
pin cannot repair an incompatible source override that remains selected.

The private `base_cli._runtime.refresh_run_bundle_index` dependency is loaded
through that compatibility boundary. The provider owns locking and index bytes;
Base requires version `1` and the `bundles` collection in its compatibility
fixture and permits provider-owned additive metadata. Context documentation
covers named public fields, excluding underscore-prefixed implementation state
and `cleanup_hooks`; new public fields still require documentation.

For direct diagnostics with the selected interpreter and source root:

```bash
BASE_CLI_SOURCE=explicit BASE_CLI_RUNTIME_SOURCE_ROOT=../base-cli/lib/python \
  ~/.base.d/base/.venv/bin/python -I \
  "$PWD/cli/python/base_cli_adapters/module_entrypoint.py" --check-provider
```

Omit the source-root override to inspect the installed provider. Public Base
launchers set these internal selection values through the resolver. The
standalone repository owns its build metadata, versioning, license, and release
workflow; Base owns only provider selection and its compatibility contract.

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
`base_cli.run_app()` preserves Click's native option syntax, including both
space-separated values such as `--name Ada` and equals-form values such as
`--name=Ada`.

## Package Layout

See the package source and API layout in the standalone
[`base-cli` repository](https://github.com/basefoundry/base-cli/tree/main/lib/python/base_cli).

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
ctx.application_home  # Path | None; neutral application-home alias
ctx.project_name   # selected project name, or None
ctx.project_root   # Path | None
ctx.manifest_path  # Path | None
ctx.history_scope  # public history scope (internal children are not indexed)
ctx.history_parent_run_id  # shared parent run ID, or None
ctx.workspace_root # configured workspace root, or None
ctx.runtime_owner  # base or project
ctx.owner_root     # owner namespace root under the cache root
ctx.run_root       # this invocation's run bundle
ctx.state_dir      # owner_root (compatibility alias)
ctx.log_dir        # run_root/logs
ctx.cache_dir      # owner_root/cache/components/<cli-name>
ctx.temp_dir       # run_root/tmp/<cli-name>/<run-id>
ctx.log_file       # run_root/logs/primary.log, or None when disabled
ctx.config         # consumer-owned configuration payload
ctx.framework_config # validated framework lifecycle settings, or None
ctx.config_provenance # configuration source mapping, when provided
ctx.user_config    # typed user config from ~/.base.d/config.yaml
ctx.application_context # optional consumer application state
ctx.services        # optional consumer services
ctx.history_display_command  # consumer policy for persisted command labels
ctx.environment    # str
ctx.debug          # bool
ctx.dry_run        # bool
ctx.keep_temp      # bool
ctx.quiet          # bool
ctx.json_output    # bool
ctx.rich           # bool; optional Rich integration enabled
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
    runs/<run-id>__<command>__<project>/{run.json,logs/,tmp/}
    cache/components/<cli-name>/
  projects/<project>/<checkout-id>/
    runs/<run-id>__<command>__<project>/{run.json,logs/,tmp/}
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
| `run.json`, `logs/`, `tmp/` | before command execution | run-bundle cleanup; `tmp/` is removed unless `--keep-temp` is requested |
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
| user | stderr | INFO by default, DEBUG with `--debug` | Local timestamp, level, source, message |
| persistent | `ctx.log_file` when enabled | DEBUG | Local timestamp, level, source, message |

Python user-facing logs default to the host's local timezone. The local offset
is included in each timestamp. `--utc-wrapper` switches Bash wrapper and library
logs to UTC, but does not change Python CLI log timestamps:

When `basectl --color` is used on a terminal, Python user-facing logs use the
same level colors as Bash logs. Persistent log files remain plain text, and
`NO_COLOR` disables colors.

```text
2026-05-23 12:31:04 -0700 INFO    cli/python/base_setup/engine.py:67 Reading Base manifest at '.../base_manifest.yaml'.
2026-05-23 19:31:04 UTC INFO    cli/python/base_setup/engine.py:67 Reading Base manifest at '.../base_manifest.yaml'.
```

The timestamp policy for persisted data is separate: `run.json`, history
records, primary run lifecycle entries, and UTC-based run IDs remain in UTC.
This keeps machine-readable metadata stable while keeping interactive logs
natural to read on the local machine.

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
4. Explicit config selected by `--config`
5. Recognized environment variables
6. Command-line standard options

The `--config` option selects an additional config file that is merged after
project config and before environment variables. It is therefore a config
source layer, while options such as `--environment`, `--debug`, and
`--keep-temp` remain the final command-line layer.

V1 intentionally does not read machine-wide or organization-wide config
implicitly. In particular, Base must not silently load `/etc/base.d/config.yaml`
or any other global policy file during local CLI startup. That keeps a new
checkout and a local developer shell deterministic unless the user or wrapper
explicitly opts into an additional config source.

V1 implements the shape and context fields, but only needs a minimal config
loader: YAML files are merged when present, recognized environment values are
applied after the explicit config source, and CLI options can override
`--environment`, `--debug`, `--keep-temp`, and `--log-file`.

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

Long option values accept either Click form, for example `--environment prod`
or `--environment=prod`.

These are direct Python package options. Public `basectl` launchers expose
`-v` for command-level debug logs and command-specific flags from
`basectl <command> --help`; they do not expose `--debug`, `--quiet`,
`--log-file`, `--config`, or `--environment` as public `basectl` options.
The wrapper-level `basectl --keep-temp <command>` option explicitly preserves
the complete temporary tree for that run.

## Interrupt And Cleanup

`base_cli` may register signal handlers while a command is running. It must not
register them on import. Cleanup should:

1. call user cleanup hooks
2. flush and close log handlers
3. remove `ctx.temp_dir` and empty temporary parents unless `keep_temp` is true

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
