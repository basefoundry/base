# basectl ci

`basectl ci` is the non-interactive entry point for running Base in CI systems.
It reuses the same setup, check, doctor, and project manifest logic as local
development, while avoiding user-facing prompts and macOS-specific UI
behaviors.

## Goals

- Run predictably in CI without interactive prompts.
- Emit structured output suitable for CI logs and downstream tooling.
- Reuse project manifests rather than adding a CI-only manifest format.
- Make Linux support useful before Base has a complete Linux bootstrap story.

## Interface

```bash
basectl ci setup <project> [--format text|json]
basectl ci check <project> [--format text|json]
basectl ci doctor <project> [--format text|json]
```

All commands also accept `--manifest <path>` for CI jobs that know the manifest
path directly, plus `--profile <list>` for opt-in prerequisite profiles.
`basectl ci setup` additionally accepts `--recreate-venv`.

The default mode is non-interactive. If a required action cannot be performed
without prompting, `basectl ci` fails with a clear fix message.

## Behavior

`basectl ci setup <project>` should:

- set CI-oriented defaults such as `BASE_CI=true`
- skip shell profile updates
- disable macOS notifications
- avoid Xcode or UI installer prompts
- run project artifact setup through the same manifest path as `basectl setup`
- emit a small JSON wrapper when `--format json` is requested

For `basectl ci setup <project> --format json`, stdout is reserved for the JSON
wrapper. The `output` field contains a compact final status line. On failures,
`output_lines` also includes compacted non-empty setup output lines so CI logs
retain intermediate context without embedding timestamped Base log prefixes in
the JSON payload. The raw setup stream is still mirrored to stderr.

`BASE_CI=true` is the Base-specific CI marker. Setup and diagnostic code use it
to select non-interactive, CI-safe behavior, including the runtime-only Linux
path that can allow system Python when Homebrew bootstrap is not available.
`CI=true` is also set for compatibility with common CI-aware tools.

`basectl ci check <project>` should:

- run read-only Base and project checks
- emit JSON output when `--format json` is supplied
- exit non-zero only for errors, not warnings

`basectl ci doctor <project>` should:

- produce actionable diagnostics with fix commands
- support `--format json`
- keep warning and error severity distinct

## Linux Relationship

The first useful version supports "runtime-only Linux":

- Base commands run under Linux when prerequisites already exist.
- Bootstrap/install remains documented as manual.
- Project checks and Python artifact reconciliation work in CI.
- Linux CI checks validate Python availability, the Base virtual environment,
  and Base Python bootstrap packages without requiring Homebrew or Xcode.

Full Linux bootstrap can come later through the Linux support plan.

## Non-Goals

- Do not invent a second manifest format for CI.
- Do not make CI mutate user dotfiles.
- Do not start GUI installers or display notifications.
- Do not hide missing prerequisites behind best-effort behavior.

## Acceptance Criteria

- `basectl ci check <project> --format json` is deterministic and parseable.
- `basectl ci doctor <project> --format json` reports ok, warn, and error
  findings.
- The command works in GitHub Actions on Ubuntu when Python and project
  prerequisites are already installed.
- The implementation has tests for non-interactive behavior and exit codes.

## Example GitHub Actions Step

```yaml
- name: Prepare Base runtime
  run: |
    mkdir -p "$HOME/.base.d/base"
    python -m venv "$HOME/.base.d/base/.venv"
    "$HOME/.base.d/base/.venv/bin/python" -m pip install --upgrade pip
    "$HOME/.base.d/base/.venv/bin/python" -m pip install PyYAML click

- name: Check Base project
  run: ./bin/basectl ci check base --format json
```

This example is a minimal starter for source-checkout CI. Workflows that install
Python packages or third-party Actions should also follow the
[CI Supply Chain Policy](ci-supply-chain-policy.md), including pinned
`requirements-dev.txt` installs for Base-managed CI dependencies.

The Homebrew formula bundles Base's Python runtime environment. A source
checkout CI job that prepares `~/.base.d/base/.venv` manually must install the
same bootstrap packages that Base uses to read manifests and run Python command
entry points. Add project-specific packages separately when the target project's
manifest requires them.
