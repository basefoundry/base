# uv-Managed Python Projects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Base issue #359 with explicit uv-managed Python project support and generic command runners.

**Architecture:** Extend the strict manifest parser with a small `python` model and command runner metadata. Keep command execution in the existing Bash project command helper layer, and keep uv setup/check behavior in the Python `base_setup` package. Activation and project venv resolution should derive the repo-local `.venv` only when the manifest explicitly declares `python.manager: uv`.

**Tech Stack:** Python 3 dataclasses and unittest/pytest, Bash subcommands with BATS tests, existing Base manifest/check/doctor pipelines, Markdown docs.

---

### Task 1: Manifest Model

**Files:**
- Modify: `cli/python/base_setup/manifest.py`
- Modify: `cli/python/base_setup/tests/test_manifest.py`

- [x] Add `PythonConfig(manager: str | None)` and validate only `manager: uv`.
- [x] Add `runner` support to `test`, `commands`, `demo`, `build.targets`, and `release`.
- [x] Preserve existing scalar command syntax for `commands`.
- [x] Reject unsupported runner values and malformed command objects.
- [x] Run `PYTHONPATH="$PWD/lib/python:$PWD/cli/python" python -m pytest cli/python/base_setup/tests/test_manifest.py -q`.

### Task 2: Project Command Resolution

**Files:**
- Modify: `cli/python/base_projects/engine.py`
- Modify: `cli/python/base_projects/tests/test_engine.py`

- [x] Return command runner metadata from `test-command`, `run-command`, `run-commands`, `demo-script`, and build target resolvers.
- [x] Keep resolver output backward-compatible for commands without runners where practical.
- [x] Run `PYTHONPATH="$PWD/lib/python:$PWD/cli/python" python -m pytest cli/python/base_projects/tests/test_engine.py cli/python/base_projects/tests/test_build_targets.py -q`.

### Task 3: Bash Runner Execution

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/project_command_helpers.sh`
- Modify: `cli/bash/commands/basectl/subcommands/test.sh`
- Modify: `cli/bash/commands/basectl/subcommands/run.sh`
- Modify: `cli/bash/commands/basectl/subcommands/demo.sh`
- Modify: `cli/bash/commands/basectl/subcommands/build.sh`
- Modify: corresponding BATS tests under `cli/bash/commands/basectl/tests/`

- [x] Add helper functions that format and execute runner-wrapped commands.
- [x] Implement `runner: uv` as `uv run -- <command>`.
- [x] Fail command invocation clearly when `uv` is missing.
- [x] Preserve existing dry-run and extra-arg display behavior.
- [x] Run focused BATS tests for `test`, `run`, `demo`, `build`, and helper behavior.

### Task 4: uv Project Setup and Diagnostics

**Files:**
- Create: `cli/python/base_setup/uv.py`
- Modify: `cli/python/base_setup/engine.py`
- Modify: `cli/python/base_setup/tests/test_diagnostics.py`
- Add or modify focused uv tests under `cli/python/base_setup/tests/`

- [x] Add `reconcile_uv_project()` that delegates to `uv sync` from the project root when `python.manager: uv`.
- [x] Add uv diagnostics for missing uv, missing `pyproject.toml`, missing `uv.lock`, declared uv runners, and stale Base-managed venvs.
- [x] Keep check/doctor warnings non-blocking unless an existing error-level check fails.
- [x] Run focused Python diagnostics/setup tests.

### Task 5: Activation and Docs

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/activate.sh`
- Modify: `cli/bash/commands/basectl/tests/activate.bats`
- Modify: `README.md`
- Modify: `docs/python-manifest.md`
- Modify: `docs/runtime-environment.md`
- Modify: `docs/doctor-findings.md`
- Modify: `CHANGELOG.md`

- [x] Make activation prefer project `.venv` only for explicit `python.manager: uv`.
- [x] Update existing interim uv docs to describe the full explicit contract.
- [x] Add stable doctor finding IDs for uv manager and uv runner diagnostics.
- [x] Run `git diff --check`.

### Task 6: Full Validation and PR

**Files:**
- All changed files.

- [x] Run focused Python and BATS tests touched by this change.
- [x] Run `env -u BASE_HOME ./bin/base-test`.
- [ ] Open a PR with `Fixes #359`, validation evidence, demo impact, and AI context note.
