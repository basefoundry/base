# Project Installer Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a maintained reusable project installer template that projects can
print or write through `basectl repo installer-template`.

**Architecture:** Keep the template source in `templates/project-install.sh`.
Extend the existing Bash `repo` subcommand with a small printer/writer command
that reuses Base's current idempotent executable file writer. Document project
customization in `docs/project-installers.md`.

**Tech Stack:** Bash, existing `basectl repo` shell helpers, BATS, ShellCheck,
and Markdown docs.

---

## File Structure

- Create `templates/project-install.sh`: maintained copyable starter installer.
- Modify `cli/bash/commands/basectl/subcommands/repo.sh`: add
  `installer-template` usage, printer, writer, parser, and dispatcher entry.
- Modify `cli/bash/commands/basectl/tests/repo.bats`: add RED tests for the new
  command.
- Modify `docs/project-installers.md`: replace the sketch with the template
  command and customization guidance.
- Add `docs/superpowers/specs/2026-06-09-project-installer-template-design.md`:
  design record.
- Add `docs/superpowers/plans/2026-06-09-project-installer-template.md`: this
  plan.

## Task 1: RED Command Tests

**Files:**
- Modify `cli/bash/commands/basectl/tests/repo.bats`

- [ ] Add a help assertion for `basectl repo installer-template [path]`.
- [ ] Add a test that runs `basectl repo installer-template` and asserts stdout
  contains:
  - `PROJECT_NAME="${PROJECT_NAME:-example-project}"`
  - `PROJECT_REPO_URL="${PROJECT_REPO_URL:-https://github.com/example/example-project.git}"`
  - `basectl" setup --manifest "$PROJECT_DIR/base_manifest.yaml" "$PROJECT_NAME"`
- [ ] Add a test that runs `basectl repo installer-template "$repo_dir/install.sh"`
  and asserts the file exists and is executable.
- [ ] Add a test that pre-creates `install.sh`, runs the command, and asserts
  the custom content is unchanged.
- [ ] Add a dry-run test that asserts no file is written.
- [ ] Run focused BATS and verify RED.

Command:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

Expected RED result: new tests fail because `installer-template` is not a known
repo subcommand.

## Task 2: Template File

**Files:**
- Create `templates/project-install.sh`

- [ ] Add a Bash script with editable defaults for project name, repo URL,
  workspace, Base directory, project directory, Base install URL, and profile
  update behavior.
- [ ] Add helpers for logging, command execution, failure handling, temporary
  installer cleanup, workspace creation, Base install/update, project
  clone/update, setup, optional profile update, and success output.
- [ ] Make the script call Base's maintained `install.sh` rather than
  reimplementing Base setup.
- [ ] Run ShellCheck on the template and fix any findings.

Command:

```bash
shellcheck -S error templates/project-install.sh
```

## Task 3: Repo Command Implementation

**Files:**
- Modify `cli/bash/commands/basectl/subcommands/repo.sh`

- [ ] Add `basectl repo installer-template [path] [options]` to usage.
- [ ] Add `base_repo_print_installer_template()` that prints
  `templates/project-install.sh` from `BASE_HOME`.
- [ ] Add `base_repo_write_installer_template()` that writes an executable copy
  to a requested path using the existing no-overwrite semantics.
- [ ] Add `base_repo_installer_template()` option parsing for:
  - optional path
  - `--dry-run`
  - `-v`
  - help
- [ ] Add dispatcher support for `installer-template`.
- [ ] Run focused BATS and verify GREEN.

Command:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

## Task 4: Documentation

**Files:**
- Modify `docs/project-installers.md`

- [ ] Replace the old sketch with commands for printing or writing the template.
- [ ] Add a Banyan Labs customization example that changes `PROJECT_NAME`,
  `PROJECT_REPO_URL`, and project-specific next-step messaging.
- [ ] Keep the product boundary language: Base provides mechanics, the project
  owns narrative and final instructions.
- [ ] Run Markdown whitespace validation.

Command:

```bash
git diff --check -- docs/project-installers.md
```

## Task 5: Validation

- [ ] Run focused repo BATS:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

- [ ] Run ShellCheck:

```bash
shellcheck -S error templates/project-install.sh cli/bash/commands/basectl/subcommands/repo.sh
```

- [ ] Run full Base validation:

```bash
env -u BASE_HOME ./bin/base-test
```

- [ ] Run whitespace validation:

```bash
git diff --check
```

## Task 6: Publish

- [ ] Commit implementation.
- [ ] Push `enhancement/512-20260609-project-installer-template`.
- [ ] Open a PR closing #512.
- [ ] Watch CI.
- [ ] Merge when checks are green.
- [ ] Sync local `master`.
- [ ] Remove the #512 worktree and local branch.
