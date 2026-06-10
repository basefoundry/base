# Guarded Release Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add guarded `basectl release publish` and complete Homebrew handoff reporting.

**Architecture:** Keep release behavior in `cli/python/base_release/engine.py`, extending the existing argument parser and release context. Add small helpers for publish readiness, confirmation, Git/GitHub command execution, release URLs, and Homebrew handoff rendering. Keep Bash as a thin dispatcher that recognizes `publish`.

**Tech Stack:** Python standard library, `base_cli.App`, Git CLI, GitHub CLI, Bash subcommand dispatch, BATS, pytest/unittest, pylint.

---

### Task 1: Python Publish RED Tests

**Files:**
- Modify: `cli/python/base_release/tests/test_engine.py`

- [ ] Add tests for `publish --dry-run --version 1.2.3 --manifest <path>` that stub readiness and assert no publish commands run.
- [ ] Add tests for `publish --version 1.2.3 --manifest <path>` without `--yes` in a non-interactive test harness.
- [ ] Add tests for `publish --version 1.2.3 --manifest <path> --yes` that stub Git/GitHub command execution and assert annotated tag, tag push, and `gh release create` command construction.
- [ ] Add tests that readiness errors and an existing GitHub Release prevent publish.
- [ ] Add tests for GitHub-only and Homebrew-required handoff output.
- [ ] Run:

```bash
BASE_HOME="$PWD" PYTHONPATH="$PWD/lib/python:$PWD/cli/python" /Users/rameshhp/.base.d/base/.venv/bin/python -m pytest cli/python/base_release/tests/test_engine.py -q
```

Expected: new tests fail because `publish`, `--dry-run`, `--yes`, and full Homebrew handoff rendering are not implemented yet.

### Task 2: Python Publish Implementation

**Files:**
- Modify: `cli/python/base_release/engine.py`

- [ ] Extend `ReleaseArguments` with `dry_run` and `yes`.
- [ ] Allow `publish` as a release command.
- [ ] Add `release_publish_command`.
- [ ] Add `github_release_finding` using `gh release view`.
- [ ] Add non-interactive confirmation protection unless `--yes` or `--dry-run`.
- [ ] Add `run_release_step` for Git/GitHub commands.
- [ ] Create annotated tags, push tags, and create GitHub Releases from a temp notes file.
- [ ] Render tag and release URLs.
- [ ] Extract Homebrew handoff rendering into a reusable helper used by `plan` and `publish`.
- [ ] Run the release engine tests and pylint until green.

### Task 3: Bash Dispatch and Completions

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/release.sh`
- Modify: `cli/bash/commands/basectl/tests/release.bats`
- Modify: `cli/bash/commands/basectl/tests/help.bats`
- Modify: `lib/shell/completions/basectl_completion.sh`
- Modify: `lib/shell/completions/basectl_completion.zsh`

- [ ] Add `publish` to help and subcommand validation.
- [ ] Add `--dry-run` and `--yes` to release completion options.
- [ ] Add BATS assertions for help and dispatch.
- [ ] Run:

```bash
BASE_HOME="$PWD" bats cli/bash/commands/basectl/tests/release.bats cli/bash/commands/basectl/tests/help.bats cli/bash/commands/basectl/tests/completions.bats
```

Expected: BATS passes after the Bash and completion updates.

### Task 4: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/release-process.md`
- Modify: `docs/architecture.md`
- Modify: `docs/execution-model.md`
- Modify: `CHANGELOG.md`

- [ ] Document `basectl release publish --version X.Y.Z --dry-run`.
- [ ] Document `basectl release publish --version X.Y.Z --yes`.
- [ ] Clarify that publish creates the GitHub-side release artifacts only.
- [ ] Clarify that Homebrew tap updates remain manual handoff work.
- [ ] Run `git diff --check`.

### Task 5: Final Verification and PR

**Files:**
- All changed files.

- [ ] Run focused Python tests.
- [ ] Run focused BATS tests.
- [ ] Smoke `basectl release publish --dry-run` against a temporary release project with a stubbed `gh`.
- [ ] Run `git diff --check`.
- [ ] Run `env -u BASE_HOME ./bin/base-test`.
- [ ] Open a PR that closes #543 and #544, and closes #540 if the child slices are complete.
- [ ] Watch GitHub Actions, merge when green, sync master, and clean up.
