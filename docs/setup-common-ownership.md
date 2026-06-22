# `setup_common.sh` Ownership Reduction

Status: design note for #929.

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
| 657-793 | Base bootstrap Python package checks and reusable Bash library diagnostics. | Keep in Bash for now. The library source is known during runtime bootstrap before Python dispatch. |
| 799-969 | Project manifest resolution, uv-manager detection, project virtualenv path choice, and project check-result file location. | Move project routing and uv/venv decisions to Python. See #1008. |
| 970-1108 | Doctor visual status, project virtualenv JSON snippets, and array splicing for pre-venv diagnostics. | Move structured JSON payload assembly to Python. Doctor-only text presentation may move to `doctor.sh` after JSON ownership is reduced. |
| 1109-1363 | Python project setup/check/doctor layer invocation and pre-venv fallback handling. | Keep Bash as the dispatcher, but consume Python-owned project routing metadata from #1008. |
| 1364-1388 | `base_dev` profile layer invocation. | Keep Bash as the dispatcher. Internal AI tool/profile extraction belongs in `base_dev` work, not this file. |
| 1389-1882 | Base host check probe execution, probe result files, text rendering, and setup/check status recording. | Keep host probes in Bash. Move reusable diagnostic formatting and JSON assembly to Python in #1009. |
| 1883-2121 | Handwritten JSON escaping, status merging, finding-id mapping, and `check --format json` top-level rendering. | Move to Python serialization in #1009. |
| 2122-2170 | Top-level install orchestration for CI runtime and macOS setup. | Keep in Bash setup. It sequences first-mile host work before optional Python project/profile layers. |

## Python-Owned Moves

### #1008: Project Environment Routing

The strongest ownership mismatch is project routing. Bash currently resolves
the project manifest, parses `python.manager: uv` with `awk`, selects the
project virtualenv path, and decides whether to call Python directly or through
`base-wrapper`.

The Python layer already owns manifests, uv checks, Python project policy, and
artifact reconciliation. The follow-up should make Python return the project
metadata Bash needs, then keep Bash focused on dispatch and exit handling.

Expected result:

- Bash no longer parses `python.manager: uv` directly.
- Base-managed and uv-managed project virtualenv paths come from Python-owned
  manifest/project metadata.
- Existing `setup`, `check`, and `doctor` behavior stays unchanged through
  focused Python tests plus BATS or integration coverage.

### #1009: Setup/Check JSON Diagnostics

The second clear mismatch is JSON output. `setup_common.sh` currently escapes
JSON strings by hand, merges diagnostic statuses, maps Base finding IDs, and
splices Base, profile, and project payloads into a top-level object.

Python already has diagnostic payload helpers in `base_setup.checks`, and JSON
serialization is a better Python responsibility. Bash can continue to collect
host probe results and call a Python formatter for structured output.

Expected result:

- `basectl check --format json` keeps the current schema and exit behavior.
- Host probes can remain Bash-owned until a later issue proves a better probe
  boundary.
- `setup_common.sh` no longer owns generic JSON escaping or top-level JSON
  object rendering for Base check results.

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

1. Implement #1008 first. Project routing affects setup, check, doctor, uv
   projects, and `base-wrapper` dispatch, so it should establish the clean
   Python metadata contract before JSON work depends on it.
2. Implement #1009 second. Once project routing is less Bash-owned, structured
   JSON formatting can move without carrying additional manifest logic along.
3. Reassess command-helper cleanup after both PRs merge. If the remaining
   doctor text or host probe code is still hard to navigate, create a narrower
   issue with line-level evidence and test coverage.
