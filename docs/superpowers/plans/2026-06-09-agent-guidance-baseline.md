# Agent Guidance Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in `basectl repo agent-guidance` command and opt-in
`repo check --agent-guidance` validation for repo-local agent guidance files.

**Architecture:** Reuse the existing `basectl repo` shell implementation and
no-overwrite writer helpers. Keep generated guidance separate from the default
repository baseline, and make checks enforce it only when the caller passes an
explicit flag.

**Tech Stack:** Bash, existing `basectl repo` helpers, BATS, ShellCheck, Zsh
syntax checks, and Markdown docs.

---

## File Structure

- Modify `cli/bash/commands/basectl/subcommands/repo.sh`: add command usage,
  guidance file writers, opt-in baseline check, option parsing, and dispatcher
  support.
- Modify `cli/bash/commands/basectl/tests/repo.bats`: add RED tests for help,
  dry-run, file creation, preservation, and opt-in check behavior.
- Modify `cli/bash/commands/basectl/tests/help.bats`: update umbrella help
  expectations.
- Modify `cli/bash/commands/basectl/tests/completions.bats`: add Bash
  completion expectations for the new command and option flag.
- Modify `lib/shell/completions/basectl_completion.sh`: complete
  `repo agent-guidance` and `repo check --agent-guidance`.
- Modify `lib/shell/completions/basectl_completion.zsh`: add the same Zsh
  completion surface.
- Modify `docs/repo-baseline.md`, `docs/README.md`,
  `cli/bash/commands/basectl/README.md`, and `README.md`: document the optional
  agent guidance layer.
- Add `docs/superpowers/specs/2026-06-09-agent-guidance-baseline-design.md`:
  design record.
- Add `docs/superpowers/plans/2026-06-09-agent-guidance-baseline.md`: this plan.

## Task 1: RED Tests

- [ ] Add help assertions for `basectl repo agent-guidance [path]`.
- [ ] Add a dry-run test that expects planned creation of `AGENTS.md`,
  `skills.md`, and `.github/pull_request_template.md`, with no files written.
- [ ] Add a write test that checks generated files contain the repo name,
  default branch, worktree path, labels, and validation command.
- [ ] Add a preservation test that pre-creates guidance files and confirms
  content stays unchanged.
- [ ] Add `repo check --agent-guidance` tests for missing guidance files and
  successful guidance checks after generation.
- [ ] Add completion/help expectations for `agent-guidance` and
  `--agent-guidance`.
- [ ] Run focused BATS and verify RED.

Command:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

Expected RED result: new tests fail because `agent-guidance` and
`--agent-guidance` are not implemented.

## Task 2: Repo Command Implementation

- [ ] Define the optional agent guidance file list in `repo.sh`.
- [ ] Add writers for `AGENTS.md`, `skills.md`, and the PR template, reusing
  `base_repo_write_stream`.
- [ ] Add `base_repo_write_agent_guidance()` to write all three files and
  preserve existing files.
- [ ] Add `base_repo_check_agent_guidance()` to warn on missing files and pass
  when all optional guidance files exist.
- [ ] Add `base_repo_agent_guidance()` parser with optional path, `--repo-name`,
  `--default-branch`, `--validation-command`, `--dry-run`, `-v`, and help.
- [ ] Extend `base_repo_check()` to accept `--agent-guidance` and combine its
  status with the standard baseline check.
- [ ] Extend dispatcher support for `agent-guidance`.
- [ ] Run focused BATS and verify GREEN.

Command:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

## Task 3: Help, Completions, And Docs

- [ ] Update umbrella help and command README surfaces.
- [ ] Update Bash and Zsh completions for the new command and flag.
- [ ] Document usage and boundaries in `docs/repo-baseline.md`.
- [ ] Update docs maps where command summaries mention `repo`.
- [ ] Run focused help/completion tests.

Commands:

```bash
bats cli/bash/commands/basectl/tests/help.bats cli/bash/commands/basectl/tests/completions.bats
zsh -n lib/shell/completions/basectl_completion.zsh
```

## Task 4: Validation

- [ ] Run focused repo tests:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

- [ ] Run help and completion tests:

```bash
bats cli/bash/commands/basectl/tests/help.bats cli/bash/commands/basectl/tests/completions.bats
```

- [ ] Run shell checks:

```bash
shellcheck -S error cli/bash/commands/basectl/subcommands/repo.sh lib/shell/completions/basectl_completion.sh
zsh -n lib/shell/completions/basectl_completion.zsh
```

- [ ] Run whitespace validation:

```bash
git diff --check
```

- [ ] Run full Base validation:

```bash
env -u BASE_HOME ./bin/base-test
```

## Task 5: Publish

- [ ] Commit implementation.
- [ ] Push `enhancement/522-20260609-agent-guidance`.
- [ ] Open a PR closing #522.
- [ ] Watch CI.
- [ ] Merge when checks are green.
- [ ] Sync local `master`.
- [ ] Remove the #522 worktree and local branch.
