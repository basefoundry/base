# basectl ci

`basectl ci` is a future non-interactive entry point for running Base in CI
systems. It should reuse the same setup, check, doctor, and project manifest
logic as local development, but it should avoid user-facing prompts and
macOS-specific UI behaviors.

## Goals

- Run predictably in CI without interactive prompts.
- Emit structured output suitable for CI logs and downstream tooling.
- Reuse project manifests rather than adding a CI-only manifest format.
- Make Linux support useful before Base has a complete Linux bootstrap story.

## Proposed Interface

```bash
basectl ci setup <project> [--format text|json]
basectl ci check <project> [--format text|json]
basectl ci doctor <project> [--format text|json]
```

The default mode should be non-interactive. If a required action cannot be
performed without prompting, `basectl ci` should fail with a clear fix message.

## Behavior

`basectl ci setup <project>` should:

- set CI-oriented defaults such as `BASE_CI=true`
- skip shell profile updates
- disable macOS notifications
- avoid Xcode or UI installer prompts
- run project artifact setup through the same manifest path as `basectl setup`

`basectl ci check <project>` should:

- run read-only Base and project checks
- prefer JSON output when `--format json` is supplied
- exit non-zero only for errors, not warnings

`basectl ci doctor <project>` should:

- produce actionable diagnostics with fix commands
- support `--format json`
- keep warning and error severity distinct

## Linux Relationship

The first useful version can support "runtime-only Linux":

- Base commands run under Linux when prerequisites already exist.
- Bootstrap/install remains documented as manual.
- Project checks and Python artifact reconciliation work in CI.

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
