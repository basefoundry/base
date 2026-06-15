# uv-Managed Python Projects Design

Issue: #359

## Summary

Base should support uv-managed Python projects through explicit delegation. A
project opts into full uv project behavior with `python.manager: uv`. Individual
commands opt into uv execution with `runner: uv`. These two declarations are
independent so composite projects can mix Go, Node, shell, Python, and uv-backed
tools without making the whole project a uv project.

## Goals

- Add a structured `python:` manifest section with `manager: uv`.
- Treat a uv-managed project as owning its repo-local `.venv`.
- Delegate uv project setup to `uv sync`.
- Report uv project and uv runner diagnostics through existing check/doctor
  flows.
- Add a generic command `runner` field, with `uv` as the first supported
  runner.
- Support command runners for `test`, `commands`, `demo`, `build.targets`, and
  the manifest model used by release metadata.
- Keep all behavior explicit; Base must not infer uv behavior merely because
  `pyproject.toml` or `uv.lock` exists.

## Non-Goals

- Do not make Base a Python package manager.
- Do not install or resolve Python dependencies directly from
  `pyproject.toml`.
- Do not automatically wrap all commands in `uv run`.
- Do not require `python.manager: uv` for command-level `runner: uv`.
- Do not force uv projects to use Base's historical
  `~/.base.d/<project>/.venv` project venv path.

## Manifest Shape

Full uv project support:

```yaml
python:
  manager: uv
```

Command-level uv execution:

```yaml
test:
  command: pytest
  runner: uv

commands:
  taxbuddy:
    command: taxbuddy
    runner: uv
```

Composite project example:

```yaml
commands:
  api:
    command: go run ./cmd/api

  audit:
    command: pytest tests/audit
    runner: uv

  web:
    command: npm run dev
```

## Execution Model

When `runner` is absent, Base preserves the existing shell execution behavior.
When `runner: uv` is present, Base executes the declared command through
`uv run`. Extra arguments are appended after `--` so command arguments do not
get interpreted as uv options.

Base validates the manifest shape eagerly. Check/doctor warn when a declared
runner needs a missing tool. Command invocation fails hard when its runner tool
is unavailable.

## uv Project Ownership

When `python.manager: uv` is present and `BASE_PROJECT_VENV_DIR` is not already
set by the caller, the project virtual environment is:

```text
<project-root>/.venv
```

`basectl setup <project>` delegates to `uv sync` from the project root.
`basectl activate <project>`, `basectl test`, `basectl run`, `basectl demo`, and
`basectl build` should expose that same venv path in `BASE_PROJECT_VENV_DIR`.

If a uv project also has the historical Base-managed venv under
`~/.base.d/<project>/.venv`, Base should treat it as stale/transitional state
and report a warning rather than using it.

## Diagnostics

Diagnostics should be warning-oriented unless setup or command invocation needs
the tool immediately:

- uv manager configured and uv exists: ok
- uv manager configured and uv missing: warning in check/doctor
- `runner: uv` declared and uv missing: warning in check/doctor
- `runner: uv` invoked and uv missing: hard command failure
- uv manager configured with missing `pyproject.toml`: warning
- uv manager configured without `uv.lock`: warning
- stale Base-managed project venv for uv project: warning

## Testing

Tests should cover manifest parsing, invalid manifest shapes, resolver output,
command execution wrapping, setup delegation, uv diagnostics, and activation
venv selection. Tests should fake `uv` with a fixture executable and must not
perform network access or real dependency resolution.
