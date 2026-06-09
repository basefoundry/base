# Agent Guidance Baseline Design

## Context

Issue #522 asks Base to seed an optional repo-local guidance layer for
agent-assisted development. Base already owns a small repository hygiene
baseline through `basectl repo init`, but that baseline intentionally avoids
agent-specific files. The new layer should be opt-in, preserve existing project
guidance, and stay separate from user-local Codex or Superpowers configuration.

## Command Shape

Add a focused command:

```bash
basectl repo agent-guidance [path] [options]
```

The command defaults to the current directory and accepts:

- `--repo-name <name>` to fill repo-specific examples. Defaults to the basename
  of the target path.
- `--default-branch <name>` to fill branch-sync examples. Defaults to `main`.
- `--validation-command <command>` to fill validation guidance. Defaults to
  `./tests/validate.sh`.
- `--dry-run` to print the files that would be created without writing them.

The command creates these files when they do not already exist:

- `AGENTS.md`
- `skills.md`
- `.github/pull_request_template.md`

Existing files are left unchanged. This mirrors `repo init` and keeps project
ownership clear.

## Generated Guidance

`AGENTS.md` seeds repository-wide agent instructions: issue-first work,
branch/worktree naming, validation, documentation expectations, and cleanup.
It uses generated values for repository name, default branch, worktree path,
standard labels, and validation command.

`skills.md` seeds a repo-local skill index for project-specific workflows. It
does not vendor third-party methodology files or install any tool.

`.github/pull_request_template.md` seeds a lightweight PR template with summary,
issue link, validation, reviewer notes, and checklist items that match the Base
repo workflow.

## Check Behavior

`basectl repo check [path]` remains unchanged by default.

Add `basectl repo check [path] --agent-guidance` to include the optional
guidance files in the check. Missing files are warnings and produce a non-zero
exit, consistent with the existing repository baseline check.

## Boundaries

This change does not install Superpowers, manage `~/.codex/config.toml`, infer
agent policy from global machine settings, overwrite existing guidance, or make
agent guidance part of the default repository baseline.

## Validation

Add Bats coverage for command help, dry-run output, file creation, existing-file
preservation, opt-in check failures, and opt-in check success. Update Bash and
Zsh completions and docs, then run the targeted Bats suites, shell syntax
checks, and the full Base test suite.
