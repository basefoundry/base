# `setup_common.sh` Ownership Reduction

Status: design note for #929, refreshed after the project-routing migration.

`cli/bash/commands/basectl/subcommands/setup_common.sh` is intentionally
shared by `basectl setup`, `basectl check`, `basectl doctor`, and
`basectl update-profile`. Its size is a maintainability signal, but the safe
response is ownership reduction, not a mechanical split into sourced shell
fragments.

This note maps the current responsibilities, identifies the behavior that should
move to Python or command helpers, and records the implementation issues that
are clear enough to pursue.

## Guardrails

- Preserve the single-file sourceable library standard from
  [STANDARDS.md](../STANDARDS.md). Do not split shell code by topic just because
  one file is long.
- Keep Bash responsible for host bootstrap and command orchestration.
- Keep Python responsible for manifest parsing, structured project data,
  artifact decisions, and JSON output.
- Do not change setup, check, or doctor behavior in the design slice.
- Add implementation issues only for boundaries that are clear enough to test
  and review independently.

## Responsibility Map

| Lines | Current responsibility | Target owner |
| --- | --- | --- |
| 35-209 | Shared setup state, profile flags, dry-run/recreate/notification toggles. | Keep in Bash orchestration. This is cross-command state used before Python may be available. |
| 210-401 | Base virtualenv health, package names, environment gates, and recovery messages. | Mostly Bash setup. Python may eventually own package policy, but host readiness still starts in Bash. |
| 402-441 | macOS completion notification. | Keep in Bash setup. It is local process/UI orchestration, not structured product logic. |
| 442-656 | Homebrew, Xcode CLT, Homebrew-managed Python, and Base virtualenv creation. | Keep in Bash setup. These are first-mile host bootstrap operations. |
| 657-1025 | Base bootstrap Python package checks, reusable Bash library diagnostics, and the helper that invokes Python diagnostic JSON commands. | Keep bootstrap checks in Bash for now. The library source is known during runtime bootstrap before Python dispatch. Move remaining structured JSON assembly to Python in #1009. |
| 1027-1179 | Project manifest resolution, Python route invocation, check-result file location, user config seeding, and fallback project virtualenv helpers. | Project routing and uv/venv selection are Python-owned through `base_setup.project_routing`; Bash consumes the TSV metadata and keeps only dispatch/fallback helpers. |
| 1181-1305 | Doctor visual status, project virtualenv JSON snippets, and array splicing for pre-venv diagnostics. | Move structured JSON payload assembly to Python. Doctor-only text presentation may move to `doctor.sh` after JSON ownership is reduced. |
| 1307-1552 | Python project setup/check/doctor layer invocation and pre-venv fallback handling. | Keep Bash as the dispatcher, consuming Python-owned project routing metadata from `base_setup --action route`. |
| 1554-1577 | `base_dev` profile layer invocation. | Keep Bash as the dispatcher. Internal AI tool/profile extraction belongs in `base_dev` work, not this file. |
| 1579-2079 | Base host check probe execution, probe result files, text rendering, and setup/check status recording. | Keep host probes in Bash. Move reusable diagnostic formatting and JSON assembly to Python in #1009. |
| 2081-2128 | Status merging and `check --format json` top-level rendering through Python diagnostic helpers. | Move the remaining top-level assembly responsibility to Python serialization in #1009. |
| 2130-2178 | Top-level install orchestration for CI runtime and macOS setup. | Keep in Bash setup. It sequences first-mile host work before optional Python project/profile layers. |

## Python-Owned Moves

### Completed: Project Environment Routing

Project routing has moved to Python. Bash still resolves the manifest path used
for dispatch, then calls `base_setup --action route` to get a tab-separated
metadata contract containing the project name, root, manifest path, virtualenv
path, and uv-manager flag.

The Python layer owns manifest parsing, `python.manager: uv` interpretation,
project virtualenv path selection, and the JSON/text route formatter through
`base_setup.project_routing`. Bash no longer parses `python.manager: uv`
directly.

Current result:

- Base-managed and uv-managed project virtualenv paths come from Python-owned
  manifest/project metadata.
- `setup_common.sh` validates the returned route fields, uses the uv-manager
  flag only for dispatch decisions, and keeps setup/check/doctor behavior in
  the shell orchestration layer.
- `BASE_PROJECT_VENV_DIR` remains part of the Python route contract for
  non-Base projects.

### Remaining: Setup/Check JSON Diagnostics (#1009)

The second clear mismatch is JSON output. `setup_common.sh` now delegates JSON
serialization to `base_setup.diagnostics`, but it still owns top-level
diagnostic status merging, check argument assembly, and Base/profile/project
payload splicing before calling the Python formatter.

Python already has diagnostic payload helpers in `base_setup.checks`, and JSON
serialization is a better Python responsibility. Bash can continue to collect
host probe results and call a Python formatter for structured output.

Expected result:

- `basectl check --format json` keeps the current schema and exit behavior.
- Host probes can remain Bash-owned until a later issue proves a better probe
  boundary.
- `setup_common.sh` no longer owns top-level JSON payload assembly for Base
  check results.

## Command-Helper Candidates

Do not create issues for these yet:

- Doctor visual text formatting may move to `doctor.sh`, but only after #1009
  removes the structured JSON responsibilities from the same area.
- Profile argument parsing can stay shared while setup, check, and doctor all
  accept the same profile flags.
- Completion notification belongs with setup orchestration unless another
  command starts using the same behavior.

These are possible cleanup slices, not proven ownership moves.

## Shell Boundary Decision

No new sourced shell boundary is justified now.

A future command-local host-prerequisite helper could be justified only if the
Homebrew/Xcode/Python probe and install surface becomes independently useful
outside `setup_common.sh`. Until then, introducing another shell file would add
source ordering and namespace risk without reducing product ownership.

Keep `setup_common.sh` navigable through section ordering, stable
`setup_*` function prefixes, focused tests, and Python ownership reduction where
structured data belongs.

## Follow-Up Sequence

1. Implement #1009 next. Project routing is now less Bash-owned, so structured
   JSON formatting can move without carrying additional manifest logic along.
2. Reassess command-helper cleanup after #1009 merges. If the remaining
   doctor text or host probe code is still hard to navigate, create a narrower
   issue with line-level evidence and test coverage.
