# Project Git Remote Reachability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit opt-in project Git remote reachability diagnostic without changing default local-only project checks.

**Architecture:** Extend the existing `base_setup.git_remote` project diagnostic unit with a new `BASE-P083` reachability check that delegates to `git ls-remote`. Thread a `--remote-network` opt-in flag from `basectl check|doctor` through the Bash project wrapper and `base_setup` pre-venv/normal actions.

**Tech Stack:** Bash `basectl` wrappers, Python `base_setup`, Git CLI, pytest, BATS.

---

### Task 1: Add Opt-In Python Reachability Diagnostics

**Files:**
- Modify: `cli/python/base_setup/git_remote.py`
- Modify: `cli/python/base_setup/engine.py`
- Test: `cli/python/base_setup/tests/test_git_remote.py`

- [ ] **Step 1: Write failing tests**

Add tests that call `check_git_remote(manifest, check_network=True)` and assert:
- default `check_git_remote(manifest)` does not run `git ls-remote`
- reachable remotes add `BASE-P083` with `network_checked: true`, `reachable: true`, provider, transport, remote, and sanitized URL details
- failed remotes add warning `BASE-P083` with `failure_category: unreachable`
- timed-out remotes add warning `BASE-P083` with `failure_category: timeout`
- credential-bearing URLs are not present in serialized JSON

- [ ] **Step 2: Verify tests fail**

Run:

```bash
env -u BASE_HOME PYTHONPATH=$PWD/lib/python:$PWD/cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m pytest cli/python/base_setup/tests/test_git_remote.py -q
```

Expected: FAIL because `check_git_remote()` does not accept `check_network`.

- [ ] **Step 3: Implement minimal Python support**

Add a `check_network: bool = False` argument to `check_git_remote()` and pass it through from `pre_venv_manifest_checks()` and `manifest_checks()`. Implement a bounded `git ls-remote --exit-code <sanitized-or-local-url> HEAD` call through a new helper that maps success to `ok`, timeout/unreachable to `warn`, and never prints credential-bearing URLs.

- [ ] **Step 4: Verify Python tests pass**

Run the same pytest command and expect all tests to pass.

### Task 2: Expose the Opt-In Flag Through User Commands

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/check.sh`
- Modify: `cli/bash/commands/basectl/subcommands/doctor.sh`
- Modify: `cli/bash/commands/basectl/subcommands/setup_common.sh`
- Test: `cli/bash/commands/basectl/tests/check.bats`
- Test: `cli/bash/commands/basectl/tests/doctor.bats`

- [ ] **Step 1: Write failing BATS tests**

Add tests showing `basectl check demo --remote-network --format json` and `basectl doctor demo --remote-network --format json` pass `--remote-network` to `python -m base_setup` for both normal and pre-venv project paths.

- [ ] **Step 2: Verify BATS tests fail**

Run:

```bash
env -u BASE_HOME bats cli/bash/commands/basectl/tests/check.bats cli/bash/commands/basectl/tests/doctor.bats
```

Expected: FAIL because the wrappers reject or omit `--remote-network`.

- [ ] **Step 3: Implement flag plumbing**

Parse `--remote-network` in `check.sh` and `doctor.sh`, export `BASE_SETUP_REMOTE_NETWORK=true`, append `--remote-network` when invoking `base_setup` in `setup_common.sh`, and document the flag in command help.

- [ ] **Step 4: Verify BATS tests pass**

Run the same BATS command and expect success.

### Task 3: Document Finding and Validate

**Files:**
- Modify: `docs/doctor-findings.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Document `BASE-P083`**

Add `BASE-P083` as the explicit opt-in project Git remote reachability diagnostic. State that default project check/doctor remain local-only.

- [ ] **Step 2: Run final validation**

Run:

```bash
env -u BASE_HOME ./bin/base-test
git diff --check
```

Expected: both pass.
