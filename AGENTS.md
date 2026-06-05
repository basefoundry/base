# Codex Guidance

This file gives coding agents the repository-specific rules for Base. It is a
navigation layer over the existing contributor docs, not a replacement for
them.

## Working Agreement

- Follow `CONTRIBUTING.md` for workflow and `STANDARDS.md` for code standards.
- Keep Base focused as the shared developer workspace control plane.
- Keep project-specific setup, service code, and application behavior in the
  owning project repository unless Base is explicitly the right shared layer.
- When the user explicitly says a session is design-only or asks for no code
  changes, stay in discussion mode and do not edit files.
- Surface unresolved product or architecture decisions instead of silently
  choosing defaults for broad changes.

## GitHub Workflow

- Create or choose a GitHub issue before implementation work.
- Use one primary category label: `bug`, `enhancement`, `documentation`, `ci`,
  or `security`.
- Do not create or apply `type:*` issue labels.
- Assign Codex-created issues to `codeforester` when GitHub allows it.
- Prefer `basectl gh` for supported issue, branch, PR, check, and cleanup
  operations.
- Fall back to the GitHub connector, raw `gh`, or `git` when `basectl gh` does
  not support the needed operation or local tooling is unavailable.
- Branch from `origin/master` with
  `<category>/<issue>-<YYYYMMDD>-<slug>`.
- Use a dedicated worktree under `~/work/base-worktrees/<slug>` for PR work.
- Link PRs with `Fixes #<issue>` or `Closes #<issue>` when merge should close
  the issue.
- After merge, sync `master`, remove the worktree, and delete local and remote
  branches.

See `docs/github-workflow.md` for the full policy, including PR body sections,
milestones, GitHub Projects, and cleanup rules.

## Validation

- Run the narrowest relevant checks first, then broaden when shared behavior is
  touched.
- For documentation-only changes, run `git diff --check`.
- For general Base changes, run `basectl test base` and `git diff --check`.
- For shell changes, include the relevant BATS tests and ShellCheck when
  available.
- For Python changes, run the relevant pytest target with Base's existing
  `PYTHONPATH` conventions.
- For setup, doctor, workspace discovery, profile, runtime shell, or
  cross-command behavior, run the matching integration checks described in
  `docs/testing.md`.
- If a required check cannot be run locally, say so in the PR and final
  summary.

## Change Boundaries

- Keep public launchers in `bin/` thin.
- Keep Bash command implementations under `cli/bash/commands/<command>/`.
- Keep Python framework code under `lib/python/` and command packages under
  `cli/python/`.
- Use structured parsers or existing Base helpers instead of ad hoc text
  manipulation when the repo provides one.
- Keep stdout for user or automation output; send logs and diagnostics to
  stderr.
- Do not rely on `set -e`, `set -u`, or `set -o pipefail` in Base shell code.
- Do not add repo-level Codex settings for personal model, approval, or sandbox
  defaults. Those belong in the user's Codex configuration unless the change is
  explicitly about shared repository runtime behavior.
