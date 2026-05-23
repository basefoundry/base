# base_cli — Design Specification

> The Python standardization layer for all CLIs in the Base ecosystem.

---

## 1. Overview

`base_cli` is a Python package that sits on top of [Click](https://click.palletsprojects.com/) and provides a unified, opinionated framework for building CLIs within the Base ecosystem. It eliminates boilerplate, enforces consistency, and transparently handles cross-cutting concerns — logging, temp files, cache, configuration, interrupt handling, and cloud telemetry — so CLI authors focus entirely on business logic.

### Design Philosophy

- **Transparency first**: Infrastructure initializes automatically on import. CLI authors do not configure it.
- **Opinionated by default**: Sensible defaults for all behaviors; overrides are explicit and layered.
- **Simplicity is the ultimate sophistication**: Every decision prioritizes clarity over clever abstraction.
- **Cross-platform**: Works on macOS (Apple Silicon and Intel) and Linux without platform-specific code from CLI authors.
- **Supports both interactive and headless modes**: User-facing CLIs and background daemons (systemd, launchd) are first-class citizens.

---

## 2. Package Name and Import

```python
import base_cli
```

A single import is all that is required. All infrastructure initializes automatically.

```python
# CLI author's main.py — complete boilerplate-free example
import base_cli

@base_cli.command()
@base_cli.option("--name", help="Your name")
def greet(name):
    base_cli.log_info(f"Hello, {name}")
```

---

## 3. Initialization on Import

When `base_cli` is imported, the following happens automatically — in order, silently, and quickly:

1. Detect runtime mode: interactive TTY vs. headless daemon
2. Resolve the CLI name from `sys.argv[0]`
3. Create the standard directory structure under `~/.based/` (see Section 4)
4. Initialize the dual logging streams (see Section 5)
5. Log the full invocation — CLI name + all arguments — at DEBUG level
6. Create a temporary directory for this run (see Section 7)
7. Register signal handlers for interrupt and termination (see Section 9)

No network calls are made on import. Initialization is fast and side-effect-free from the CLI author's perspective.

---

## 4. Standard Directory Structure

All Base-managed state lives under `~/.based/` in the user's home directory.

```
~/.based/
  cli/
    <cli-name>/
      logs/
        2025-04-15T10-30-00_abc123.log   # one file per run
        2025-04-14T09-00-00_xyz789.log
      cache/
        ...                               # persistent across runs
      tmp/
        2025-04-15T10-30-00_abc123/       # ephemeral, per-run
```

The CLI name is derived from the invoked script name (the basename of `sys.argv[0]`, without extension).

### Directory Lifecycle

| Directory | Created | Destroyed |
|---|---|---|
| `logs/` | On first run | Never (retention policy applies) |
| `cache/` | On first run | Never (explicit clear or CLI logic) |
| `tmp/<run>/` | On import | On exit (unless `BASE_CLI_KEEP_TEMP=true`) |

---

## 5. Logging

### Dual-Stream Architecture

Every CLI run produces two independent logging streams:

| Stream | Destination | Level | Format |
|---|---|---|---|
| User stream | stdout / stderr | User-configured (default: INFO) | Human-readable, optionally colorized |
| Persistent stream | `~/.based/cli/<name>/logs/<timestamp>.log` | Always DEBUG | Structured, with timestamps |

The persistent stream is always DEBUG regardless of the user's chosen level. This ensures full diagnostic context is available after a failure — even if the user did not request verbose output at runtime.

### Log Levels

`base_cli` uses Python's standard `logging` module with its five built-in levels. No custom levels are added.

| Level | User stream | Persistent stream |
|---|---|---|
| DEBUG | Only if `--debug` flag set | Always |
| INFO | Yes (default) | Always |
| WARNING | Yes | Always |
| ERROR | Yes | Always |
| CRITICAL | Yes | Always |

### Logging API

```python
base_cli.log_debug("message")
base_cli.log_info("message")
base_cli.log_warning("message")
base_cli.log_error("message")
base_cli.log_critical("message")

# Sensitive data — shown to user but redacted from file and cloud upload
base_cli.log_info("Token accepted", redact=True)
```

The `redact=True` parameter is available on all five logging functions. When set, the message is shown on the user-facing stream but replaced with `[REDACTED]` in the persistent log and excluded from cloud uploads.

### Automatic Invocation Logging

On every run, `base_cli` automatically logs at DEBUG level:

- Full command invocation (`sys.argv`)
- Timestamp and run ID
- Platform (OS, architecture)
- Python version
- Environment name (if set)

CLI authors do not write any of this.

### Headless / Daemon Mode

When no TTY is detected (e.g., running under systemd or launchd), the user-facing stream is automatically redirected to syslog or a structured JSON log format suitable for log aggregation. The persistent file stream continues as normal.

---

## 6. Configuration

### Layered Override Model

Configuration is resolved in this priority order (highest to lowest):

| Priority | Source | Example |
|---|---|---|
| 1 (highest) | Code hooks — explicit API calls | `base_cli.set_log_level("debug")` |
| 2 | Config file | `~/.based/config.yaml` or project-level |
| 3 | Command line arguments | `--debug`, `--environment prod` |
| 4 (lowest) | Environment variables | `BASE_CLI_LOG_LEVEL=debug` |

### Config File

Config files are always YAML. They are discovered in this order:

1. Current working directory: `.based.yaml`
2. User home directory: `~/.based/config.yaml`
3. System-wide: `/etc/based/config.yaml`

Project-level config (CWD) takes precedence over user-level, which takes precedence over system-level.

### Environment-Specific Config

When an environment is set (via `--environment` or `BASE_CLI_ENVIRONMENT`), `base_cli` additionally loads:

```
~/.based/config.<environment>.yaml
```

For example, `BASE_CLI_ENVIRONMENT=prod` loads `~/.based/config.prod.yaml`. Environment configs merge with the base config; the environment-specific values override.

Supported environments are open-ended (e.g., `dev`, `staging`, `prod`). `base_cli` does not hard-code environment names.

### Key Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `BASE_CLI_LOG_LEVEL` | User-facing log level | `info` |
| `BASE_CLI_ENVIRONMENT` | Active environment | `dev` |
| `BASE_CLI_KEEP_TEMP` | Preserve temp dir after run | `false` |
| `BASE_CLI_TEMP_RETENTION_DAYS` | Days to keep old temp dirs | `7` |
| `BASE_CLI_NO_CLOUD_UPLOAD` | Disable cloud log upload | `false` |
| `BASE_CLI_CLOUD_BUCKET` | Cloud bucket for log upload | _(unset)_ |

---

## 7. Temporary File Handling

### Automatic Lifecycle

On import, `base_cli` creates a run-scoped temp directory using Python's `tempfile` module, which handles platform differences (macOS, Linux) automatically.

```python
# Accessible to CLI authors as:
base_cli.temp_dir   # Path object pointing to the run's temp directory
```

The temp directory is automatically deleted on clean exit and on interrupt (see Section 9), unless `BASE_CLI_KEEP_TEMP=true`.

### Retention Policy

When `BASE_CLI_KEEP_TEMP=true`, temp directories from previous runs are preserved. To prevent unbounded growth, `base_cli` prunes temp directories older than `BASE_CLI_TEMP_RETENTION_DAYS` (default: 7 days) at the start of each run.

### No Output File Management

Output files produced by a CLI are the CLI author's responsibility. `base_cli` does not manage output paths. The user specifies output locations through CLI arguments or config.

---

## 8. Cache Management

### Persistent Cache Directory

```python
base_cli.cache_dir   # Path object pointing to ~/.based/cli/<name>/cache/
```

The cache directory persists across runs. `base_cli` provides the directory; individual CLIs decide what to store and when to invalidate.

Cache management is intentionally minimal at the base_cli level — it is a convention and location standard, not a full caching framework.

---

## 9. Interrupt Handling

### Default Behavior

`base_cli` registers signal handlers for `SIGINT` (Ctrl+C) and `SIGTERM` on import. On interrupt:

1. Flush and close all log file handles
2. Write a final log entry noting the interruption
3. Clean up the temp directory (unless `BASE_CLI_KEEP_TEMP=true`)
4. Call any registered user cleanup hooks (in registration order)
5. Exit cleanly

### User Cleanup Hooks

CLI authors can register optional cleanup functions:

```python
def my_cleanup():
    # close connections, finalize output, etc.
    pass

base_cli.on_interrupt(my_cleanup)
```

Multiple hooks can be registered. They are called in the order registered, after base_cli's own cleanup.

---

## 10. Command Line Argument Handling

### Click as the Foundation

`base_cli` wraps [Click](https://click.palletsprojects.com/) — the standard Python CLI framework — to enforce uniformity while preserving Click's full power. CLI authors use `base_cli` decorators, which delegate to Click under the hood.

```python
# Instead of @click.command(), use:
@base_cli.command()

# Instead of @click.option(), use:
@base_cli.option()
```

### Why a Wrapper?

Without the wrapper layer, there is no mechanism to:
- Automatically redact sensitive arguments before logging or cloud upload
- Inject standard arguments across all CLIs uniformly
- Integrate argument parsing with the logging and config systems
- Enforce consistent error handling and exit codes

### Sensitive Argument Redaction

CLI authors annotate sensitive arguments at definition time:

```python
@base_cli.option("--api-key", sensitive=True, help="API key")
```

When `sensitive=True`, the argument value is:
- Never written to the persistent log file
- Never included in cloud uploads
- Replaced with `[REDACTED]` in all log output

### Standard Arguments — Provided by base_cli for All CLIs

The following arguments are automatically available in every CLI without the author declaring them:

| Argument | Purpose |
|---|---|
| `--debug` | Enable DEBUG level on user-facing stream |
| `--environment` | Set the active environment (dev/staging/prod) |
| `--config` | Path to a custom config file |
| `--no-cloud-upload` | Disable cloud log upload for this run |
| `--log-file` | Override the default log file location |
| `--version` | Show CLI version (auto-populated) |
| `--help` | Show help (provided by Click) |

---

## 11. Cloud Log Telemetry

### Purpose

When CLIs run across many engineers' laptops, `base_cli` can aggregate logs to a central cloud bucket. This enables:

- Usage analytics: which CLIs are most used, which subcommands are popular
- Error pattern detection: what failures occur most frequently
- Remote debugging: support staff can retrieve logs without user involvement

### Upload Behavior

Log upload happens asynchronously on CLI exit. `base_cli` uploads logs accumulated since the last successful upload (delta upload, not full history). Logs are scrubbed of sensitive data before upload.

Upload is a no-op if `BASE_CLI_CLOUD_BUCKET` is not configured or `BASE_CLI_NO_CLOUD_UPLOAD=true`.

### Multi-Cloud Design

The upload mechanism is abstracted behind a provider interface. AWS S3 is the initial implementation. Additional providers (Azure Blob Storage, Google Cloud Storage) can be added as plugins.

```yaml
# ~/.based/config.yaml
cloud:
  provider: aws
  bucket: my-org-cli-logs
  region: us-west-2
  retention_days: 90
```

### Privacy and Consent

- Sensitive arguments (marked `sensitive=True`) are never uploaded
- Log messages marked `redact=True` are excluded from uploads
- Upload can be disabled globally via environment variable or per-run via `--no-cloud-upload`
- Future: explicit opt-in model with clear documentation of what is uploaded

---

## 12. Platform Support

| Platform | Status |
|---|---|
| macOS (Apple Silicon) | Primary |
| macOS (Intel) | Supported via Python/Homebrew abstraction |
| Linux | Supported |

Platform-specific differences (temp directory locations, signal handling, syslog integration) are handled internally by `base_cli` using Python's standard library. CLI authors write platform-agnostic code.

---

## 13. Future Considerations

- **Go equivalent**: `base_cli_go` — a Go package implementing the same philosophy for Go-based CLIs. Separate namespace, same conventions.
- **Config file per CLI**: In addition to the project-level config, individual CLIs may support their own config file in a future iteration.
- **Plugin system**: Extend cloud upload providers and other behaviors via a plugin registry.
- **Usage dashboard**: A companion CLI (`based stats`) to visualize local and cloud-aggregated usage.

---

## 14. Summary — What CLI Authors Get for Free

By adding `import base_cli` to their `main.py`, every CLI author automatically receives:

- Dual-stream logging (user-facing + always-debug file)
- Automatic invocation logging (args, platform, timestamp)
- Standard directory structure under `~/.based/`
- Temp directory created and cleaned up per run
- Cache directory provisioned and accessible
- Interrupt handling with cleanup
- Standard CLI arguments (`--debug`, `--environment`, `--config`, etc.)
- Sensitive argument and log redaction framework
- Cloud log upload (when configured)
- Cross-platform compatibility (macOS + Linux)

All of this with **zero configuration code** in the CLI itself.

---

*base_cli — Infrastructure that gets out of the way.*
