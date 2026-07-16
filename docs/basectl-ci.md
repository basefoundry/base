# CI-Safe Mode

`--ci` is the CI-safe mode for Base setup, readiness checks, and diagnostics.
It reuses the same setup, check, doctor, and project manifest logic as local
development, while avoiding user-facing prompts and macOS-specific UI
behaviors.

It is not a CI runner. It does not run project tests, launch GitHub Actions
locally, or create Ubuntu or Multipass virtual machines. CI systems compose it
with their own runners and test commands.

## Goals

- Run predictably in CI without interactive prompts.
- Emit structured output suitable for CI logs and downstream tooling.
- Reuse project manifests rather than adding a CI-only manifest format.
- Make Linux support useful before Base has a complete Linux bootstrap story.

## Interface

```bash
basectl setup --ci [project] [--format text|json]
basectl check --ci [project] [--format text|json]
basectl doctor --ci [project] [--format text|json]
```

All commands also accept `--manifest <path>` for CI jobs that know the manifest
path directly, plus `--profile <list>` for opt-in prerequisite profiles.
`basectl setup --ci` additionally accepts `--recreate-venv`.

The default mode is non-interactive. If a required action cannot be performed
without prompting, the command fails with a clear fix message.

`basectl ci setup|check|doctor` remains a backward-compatible alias for the
same behavior. The alias prepends `--ci` and passes all remaining arguments to
the underlying command unchanged, so that command's help, option validation,
and exit codes are authoritative. New docs and automation should prefer the
`--ci` flag on the underlying command.

## Behavior

`basectl setup --ci <project>` should:

- set CI-oriented defaults such as `BASE_CI=true`
- skip shell profile updates
- disable macOS notifications
- avoid Xcode or UI installer prompts
- run project artifact setup through the same manifest path as `basectl setup`
- emit a small JSON wrapper when `--format json` is requested

For `basectl setup --ci <project> --format json`, stdout is reserved for the JSON
wrapper. The `output` field contains a compact final status line. On failures,
`output_lines` also includes compacted non-empty setup output lines so CI logs
retain intermediate context without embedding timestamped Base log prefixes in
the JSON payload. The raw setup stream is still mirrored to stderr.

`BASE_CI=true` is the Base-specific CI marker. Setup and diagnostic code use it
to select non-interactive, CI-safe behavior, including the runtime-only Linux
path that can allow system Python when Homebrew bootstrap is not available.
`CI=true` is also set for compatibility with common CI-aware tools.

`basectl check --ci <project>` should:

- run read-only Base and project checks
- emit JSON output when `--format json` is supplied
- exit non-zero only for errors, not warnings

`basectl doctor --ci <project>` should:

- produce actionable diagnostics with fix commands
- support `--format json`
- keep warning and error severity distinct

## Relationship To Tests

`basectl check --ci <project>` verifies readiness for a CI environment. It does
not execute the project's declared test command. Use `basectl test <project>` to
run the manifest-declared test command, or `bin/base-test` in the Base
repository when the job needs the full source-checkout validation suite.

## Linux Relationship

The first useful version supports "runtime-only Linux":

- Base commands run under Linux when prerequisites already exist.
- Bootstrap/install remains documented as manual.
- Project checks and Python artifact reconciliation work in CI.
- Linux CI checks validate Python availability, the Base virtual environment,
  and Base Python bootstrap packages without requiring Homebrew or Xcode.

Full Linux bootstrap can come later through the Linux support plan.

The optional `linux-lab` profile prepares or checks local Multipass tooling for
manual Ubuntu lab work on macOS. It does not create or mutate VM instances.

## Non-Goals

- Do not invent a second manifest format for CI.
- Do not run project tests or replace `basectl test`.
- Do not launch GitHub Actions locally.
- Do not create or mutate Ubuntu or Multipass VM instances.
- Do not make CI mutate user dotfiles.
- Do not start GUI installers or display notifications.
- Do not hide missing prerequisites behind best-effort behavior.

## Acceptance Criteria

- `basectl check --ci <project> --format json` is deterministic and parseable.
- `basectl doctor --ci <project> --format json` reports ok, warn, and error
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
  run: ./bin/basectl check --ci base --format json

- name: Run Base source-checkout tests
  run: env -u BASE_HOME ./bin/base-test
```

This example is a minimal starter for source-checkout CI. The `check --ci` step
validates Base readiness; the separate `bin/base-test` step runs the repository's
full validation suite. Workflows that install Python packages or third-party
Actions should also follow the
[CI Supply Chain Policy](ci-supply-chain-policy.md), including pinned
`requirements-dev.txt` installs for Base-managed CI dependencies.

The Homebrew formula bundles Base's Python runtime environment. A source
checkout CI job that prepares `~/.base.d/base/.venv` manually must install the
same bootstrap packages that Base uses to read manifests and run Python command
entry points. Add project-specific packages separately when the target project's
manifest requires them.

## Reusable GitHub Actions Workflow

Base also publishes a reusable workflow for repositories that want the standard
`basectl check --ci` readiness contract without copying the setup steps into
every repository:

```yaml
name: Base check

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  base-check:
    permissions:
      contents: read
    uses: basefoundry/base/.github/workflows/base-check.yml@<base-ref-or-sha>
    with:
      project: my-project
      manifest-path: base_manifest.yaml
```

For production repositories, pin the reusable workflow ref to a reviewed Base
release tag or commit SHA. The default `source-checkout` mode checks out the
caller repository, checks out Base source at the same commit as the reusable
workflow, checks out `base-bash-libs`, prepares the Base Python runtime, and
runs:

```bash
basectl check --ci <project> --format json --manifest <caller-manifest>
```

Supported inputs:

| Input | Default | Purpose |
| --- | --- | --- |
| `project` | required | Base project name to pass to `basectl check --ci`. |
| `manifest-path` | `base_manifest.yaml` | Manifest path relative to the caller repository root. |
| `setup-mode` | `source-checkout` | `source-checkout` prepares Base from source; `preinstalled` uses `basectl` already on `PATH`. |
| `base-ref` | workflow commit | Optional Base ref override for `source-checkout` mode. Leave empty to use the pinned reusable workflow commit. |
| `profiles` | empty | Optional comma-separated prerequisite profiles, such as `dev` or `sre`. |
| `output-format` | `json` | `basectl check` output format: `json` or `text`. |
| `python-version` | `3.13` | Python used to prepare the Base source runtime. |

The workflow's `base-bash-libs` checkout is pinned inside the workflow file to
match Base's CI supply-chain policy. Update that pin through a Base workflow-pin
maintenance PR, not from caller workflow inputs.

Use a repository-local workflow instead of the reusable workflow when the job
must start services, install project-specific system packages, run tests, use
secrets, or perform setup that must happen before `basectl check --ci`. In that
case, keep the direct command step and follow the CI supply-chain policy for
pinned actions and dependency installation.
