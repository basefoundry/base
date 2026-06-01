# GitHub Workflow

Base uses GitHub Issues as the public product backlog and Git worktrees for
parallel pull request trains. This page captures the repository workflow so
humans and AI-assisted development agents follow the same rules.

## Labels

Base uses GitHub default-style labels instead of `type:*` labels.

Use one primary category label on each issue:

- `bug`
  Unexpected behavior, correctness issues, regressions, and defects.
- `enhancement`
  New capabilities, product improvements, refactors, and most maintenance work.
- `documentation`
  Documentation-only changes.
- `ci`
  GitHub Actions, test automation, release automation, and CI reliability.
- `security`
  Security hardening, dependency pinning, static analysis, and permission
  tightening.

Avoid creating new `type:*` labels. Older issues may still carry historical
`type:fix`, `type:feat`, `type:chore`, or `type:docs` labels, but new work
should use the labels above.

## Issue Assignment

Issues created by Codex or other automation for the Base repository should be
assigned to `codeforester`.

If assignment fails, the automation should mention that in its summary instead
of silently leaving the issue unassigned.

## Preferred GitHub Interface

Use `basectl gh` as the preferred interface for Base repository GitHub
workflows when it supports the operation.

This keeps Base dogfooding its own workflow tool for common issue, branch, PR,
and repository hygiene tasks. For example, prefer `basectl gh issue create`,
`basectl gh issue start`, `basectl gh pr create`, and `basectl gh branch prune`
over hand-written `gh` commands when those commands are available and local
tooling is authenticated.

Fallbacks are allowed when `basectl gh` does not support the needed operation,
when local GitHub CLI authentication is unavailable, or when the GitHub
connector provides a safer structured API for the task. In those cases, use the
GitHub connector, raw `gh`, or `git` as appropriate and keep the resulting
issue labels, branch names, assignments, and PR bodies aligned with this
policy.

## Branch Names

Branch names should be derived from the issue category:

```text
<category>/<issue>-<YYYYMMDD>-<slug>
```

Examples:

```text
bug/245-20260529-fix-profile-project-prompt
enhancement/222-20260529-add-changelog
documentation/241-20260529-document-github-workflow
ci/246-20260529-pin-shellcheck-version
security/247-20260529-restrict-log-permissions
```

Use `enhancement/` for maintenance work unless the issue is more specifically
`documentation`, `ci`, or `security`.

## Worktrees

All pull request implementation work should happen in a dedicated worktree.

The main checkout can stay as the user's active working copy:

```text
~/work/base
```

Issue work should use:

```text
~/work/base-worktrees/<slug>
```

Create a worktree from current `origin/master`:

```bash
git fetch origin master
git worktree add -b documentation/241-20260529-document-github-workflow \
  ~/work/base-worktrees/documentation-241-github-workflow origin/master
```

After a pull request is merged:

```bash
git -C ~/work/base pull --ff-only origin master
git -C ~/work/base worktree remove ~/work/base-worktrees/<slug>
git -C ~/work/base branch -d <branch>
git -C ~/work/base push origin --delete <branch>
```

Delete remote branches after merge unless there is a specific reason to keep
one around.

Base can also help with branch cleanup:

```bash
basectl gh branch prune
basectl gh branch prune --yes
basectl gh branch prune --remote --yes
```

The command is dry-run by default. It reports merged local branches as delete
candidates, reports branches attached to worktrees as skipped, and keeps remote
cleanup scoped to stale `origin/*` tracking refs. Removing stale worktree
directories is intentionally a separate workflow because it deletes files on
disk.

## Pull Requests

Keep each PR scoped to one issue.

PR bodies should include:

- a short summary of the change
- the validation commands that were run
- `Fixes #<issue>` or `Closes #<issue>` when the merge should close the issue

Prefer small PR trains over large mixed PRs. A train may contain several
worktrees and PRs, but each PR should still close one issue cleanly.

## Milestones

Milestones represent release intent, not workflow state.

Suggested Base milestones:

- `v0.1.0 - Public baseline`
  Current public baseline for Base's first installable product shape.
- `v0.2.0 - Adoption polish`
  Installer, Homebrew, README, changelog, issue templates, and workflow polish.
- `v0.3.0 - Project orchestration`
  Project test execution, mise integration, manifest refinement, and a real
  Base-managed demo project.
- `v0.4.0 - CI and Linux foundation`
  Linux runtime support, CI-oriented behavior, and `basectl ci` planning.
- `v1.0.0 - Stable public release`
  Stable manifest contracts, compatibility expectations, and upgrade policy.

Every issue does not need a milestone. Use milestones when the issue contributes
to a concrete release goal.

## Projects

Use one GitHub Project first: `Base Roadmap`.

Recommended fields:

- `Status`: Triage, Backlog, Ready, In Progress, In Review, Done
- `Priority`: P0, P1, P2, P3
- `Area`: CLI, Setup, Manifest, Shell, Python, Docs, CI, Packaging, Security,
  Product
- `Size`: S, M, L
- `PR Train`: optional text field for batch work

Useful views:

- Board by status
- Priority view
- Release view grouped by milestone
- Bugs and CI
- Ready for PR train

Projects show workflow and prioritization. Milestones show release grouping.
