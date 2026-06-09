# IDE Diagnostic Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for
> tracking.

**Goal:** Cache read-only IDE probes once per IDE during check/doctor
diagnostics while preserving one finding per declared extension or setting.

**Architecture:** Keep finding construction in `cli/python/base_setup/ide.py`.
Introduce an internal `IdeDiagnosticSnapshot` that lazily caches CLI
availability, extension listings, settings path, and parsed settings for a
single IDE within one diagnostic collection pass.

**Tech Stack:** Python standard library dataclasses plus the existing Base
diagnostic helpers.

---

## File Structure

- Modify `cli/python/base_setup/ide.py`: add `IdeDiagnosticSnapshot`, use it in
  IDE extension/settings check collection.
- Modify `cli/python/base_setup/tests/test_ide_extensions.py`: add RED coverage
  for extension probe reuse.
- Modify `cli/python/base_setup/tests/test_ide_settings.py`: add RED coverage
  for settings probe reuse.
- Add `docs/superpowers/specs/2026-06-09-ide-diagnostic-cache-design.md`: design
  record.
- Add `docs/superpowers/plans/2026-06-09-ide-diagnostic-cache.md`: this plan.

## Task 1: Failing Extension Cache Test

**Files:**
- Modify: `cli/python/base_setup/tests/test_ide_extensions.py`

- [ ] Add a test with one IDE and two declared extensions.
- [ ] Patch `base_setup.process.command_exists` and
  `base_setup.ide.list_ide_extensions`.
- [ ] Assert both probes are called once.
- [ ] Assert two findings are still returned in manifest order.
- [ ] Run the focused test and verify it fails before implementation.

## Task 2: Failing Settings Cache Test

**Files:**
- Modify: `cli/python/base_setup/tests/test_ide_settings.py`

- [ ] Add a test with one IDE and two declared settings.
- [ ] Patch `base_setup.ide.ide_settings_file` and
  `base_setup.ide.read_ide_settings`.
- [ ] Assert both probes are called once.
- [ ] Assert two findings are still returned in manifest order.
- [ ] Run the focused test and verify it fails before implementation.

## Task 3: Snapshot Implementation

**Files:**
- Modify: `cli/python/base_setup/ide.py`

- [ ] Import `dataclass`.
- [ ] Add `IdeDiagnosticSnapshot` with lazy cached methods for CLI
  availability, installed extensions, settings file, and current settings.
- [ ] Update `check_ide_extensions()` to create and reuse one snapshot per IDE.
- [ ] Update `check_ide_extension()` to accept an optional snapshot while keeping
  existing direct-call behavior.
- [ ] Update `check_ide_settings()` to create and reuse one snapshot per IDE.
- [ ] Update `check_ide_setting()` to accept an optional snapshot while keeping
  existing direct-call behavior.

## Task 4: Validation

- [ ] Run focused IDE extension tests:

```bash
PYTHONPATH=lib/python:cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m unittest cli/python/base_setup/tests/test_ide_extensions.py
```

- [ ] Run focused IDE settings tests:

```bash
PYTHONPATH=lib/python:cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m unittest cli/python/base_setup/tests/test_ide_settings.py
```

- [ ] Run the full Base validation suite:

```bash
env -u BASE_HOME ./bin/base-test
```

- [ ] Run whitespace validation:

```bash
git diff --check
```

## Task 5: Publish

- [ ] Commit the implementation.
- [ ] Push the branch.
- [ ] Open a PR closing #509.
- [ ] Watch CI.
- [ ] Merge when checks are green.
- [ ] Sync local `master` and remove the #509 worktree.
