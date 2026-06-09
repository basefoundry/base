# Parallel Base Check Probes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run independent Base environment probes concurrently for
`basectl check` while preserving deterministic text and JSON output.

**Architecture:** Keep the existing result arrays and renderers. Add
result-file helpers plus background probe helpers inside
`setup_common.sh`; the collector waits for probes, reads files in the old order,
and then appends to the existing arrays.

**Tech Stack:** Bash 4-compatible shell functions, existing BATS test helpers,
and the current Base check/doctor rendering functions.

---

## File Structure

- Modify `cli/bash/commands/basectl/subcommands/setup_common.sh`: result file
  writer/parser, background Base probe helpers, and parallel
  `setup_collect_base_check_results()`.
- Modify `cli/bash/commands/basectl/tests/setup_helpers.bash`: test-only Xcode
  wait hook used to prove probes overlap.
- Modify `cli/bash/commands/basectl/tests/check.bats`: RED coverage for
  deterministic ordered text and JSON output while probes overlap.
- Add `docs/superpowers/specs/2026-06-09-parallel-base-check-probes-design.md`:
  design record.
- Add `docs/superpowers/plans/2026-06-09-parallel-base-check-probes.md`: this
  plan.

## Task 1: RED Text Ordering and Parallelism Test

**Files:**
- Modify: `cli/bash/commands/basectl/tests/setup_helpers.bash`
- Modify: `cli/bash/commands/basectl/tests/check.bats`

- [ ] Add a test-only wait hook to `create_xcode_stubs()` so `xcode-select -p`
  waits for the package probe marker when
  `BASE_SETUP_TEST_XCODE_WAIT_FOR_PIP_SHOW=true`.
- [ ] Add a `basectl check` text-mode test that enables the hook, sets all
  dependencies as installed, and expects status 0.
- [ ] Assert the output line order remains Homebrew, Xcode, Python, venv,
  PyYAML, click.
- [ ] Run the focused BATS file and verify the new test fails on the current
  serial collector.

Command:

```bash
bats cli/bash/commands/basectl/tests/check.bats
```

Expected RED result: the new text test fails because serial collection checks
Xcode before any package probe can create `pip-show.log`.

## Task 2: RED JSON Ordering and Parallelism Test

**Files:**
- Modify: `cli/bash/commands/basectl/tests/check.bats`

- [ ] Add a `basectl check --format json` test using the same Xcode wait hook.
- [ ] Assert status 0 and empty stderr.
- [ ] Assert JSON finding order remains BASE-D001 through BASE-D006.
- [ ] Run the focused BATS file and verify the new JSON test fails on the
  current serial collector.

Command:

```bash
bats cli/bash/commands/basectl/tests/check.bats
```

Expected RED result: the JSON test fails for the same serial-order reason.

## Task 3: Result File Helpers

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/setup_common.sh`

- [ ] Add `setup_write_check_result_file()` that writes `name`, `ok`,
  `message`, `recovery`, and `debug` lines to a probe result file.
- [ ] Add `setup_parse_check_result_file()` that loads those fields into
  internal scratch variables.
- [ ] Add `setup_add_parsed_check_result()` that appends parsed fields to the
  existing `_BASE_SETUP_CHECK_*` arrays.
- [ ] Add a fatal error when a probe result file is missing or malformed.

## Task 4: Probe Helpers

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/setup_common.sh`

- [ ] Add one result-producing helper for each Base environment check:
  Homebrew, Xcode, Python formula, Base venv, PyYAML, and click.
- [ ] Make each probe write exactly one result file and return 0 for expected
  missing-dependency outcomes.
- [ ] Keep `setup_refresh_brew_path` out of the Homebrew background probe.

## Task 5: Parallel Collector

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/setup_common.sh`

- [ ] Replace the serial body of `setup_collect_base_check_results()` with a
  temporary directory, six background probes, `wait`, ordered result loading,
  and cleanup.
- [ ] Read the Homebrew result first and run `setup_refresh_brew_path` in the
  parent when Homebrew exists.
- [ ] Preserve fatal refresh behavior for text `basectl check`.
- [ ] Preserve warning-style refresh behavior for JSON/doctor callers.
- [ ] Preserve existing finding names, messages, recovery text, debug messages,
  and return status.

## Task 6: Validation

- [ ] Run focused BATS coverage:

```bash
bats cli/bash/commands/basectl/tests/check.bats
```

- [ ] Run full Base validation:

```bash
env -u BASE_HOME ./bin/base-test
```

- [ ] Run whitespace validation:

```bash
git diff --check
```

## Task 7: Publish

- [ ] Commit the implementation.
- [ ] Push `enhancement/510-20260609-parallel-base-check-probes`.
- [ ] Open a PR closing #510.
- [ ] Watch CI.
- [ ] Merge when checks are green.
- [ ] Sync local `master`.
- [ ] Remove the #510 worktree and local branch.
