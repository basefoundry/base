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
- `needs-demo`
  Changes that should update Base's self-demo, the `base-demo` reference
  project, or demo documentation. See [Demo Maintenance](demo-maintenance.md).

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
basectl gh worktree prune
basectl gh worktree prune --yes
```

The command is dry-run by default. It reports merged local branches as delete
candidates, reports branches attached to worktrees as skipped, and treats
`--remote` as GitHub remote branch cleanup plus stale `origin/*` tracking-ref
cleanup. Because Base usually uses squash merges, pruning checks GitHub PR state
when available and falls back to Git ancestry when offline.

Remote branch pruning is deliberately conservative. Base deletes a GitHub branch
only when GitHub confirms a merged pull request for that exact branch name. It
does not delete the default branch, the current branch, or a branch attached to a
local worktree. After safe GitHub branches are deleted, Base prunes stale local
`origin/*` refs.

Worktree pruning is also dry-run by default. It removes only clean, non-current
worktrees whose branches are confirmed merged into the default branch or through
a merged GitHub PR, then deletes the now-free local branch when safe.

## Pull Requests

Base pull requests are issue-backed by default. The issue is the planning
record: it owns the problem statement, category, priority, milestone, and
Project tracking. The PR is the implementation and review record: it explains
what changed, how it was validated, and whether the change is ready to merge.

Keep each PR scoped to one issue by default.

PR bodies should include:

- a short summary of the change
- the validation commands that were run
- `Fixes #<issue>` or `Closes #<issue>` when the merge should close the issue
- `Demo Impact` when the issue or PR carries `needs-demo`

Prefer small PR trains over large mixed PRs. A train may contain several
worktrees and PRs, but each PR should still close one issue cleanly.

### PR Metadata Inheritance

When a PR is opened for an issue, inherit metadata selectively:

- Copy the primary category label from the issue to the PR.
- Copy special workflow labels such as `needs-demo` to the PR.
- Assign the PR to the implementer when assignment is useful for review
  queues.
- Link the PR to the issue with `Closes #<issue>` when the merge should close
  the issue.
- Use `Refs #<issue>` when the PR is related to an issue but should not close
  it.

Do not copy milestone or GitHub Project fields to the PR by default. Keep those
on the issue so release planning and Project views do not double count the same
work. When a PR opens, move the issue's Project status to `In Review` instead
of adding a separate PR item to the Project.

PR reviewers are PR-specific and should be selected from the implementation
surface, ownership, and risk of the change rather than copied from the issue.

### Multi-Issue PRs

One PR may close multiple issues only when the work is atomic and splitting it
would create artificial churn. Acceptable examples include:

- one small implementation that naturally fixes two related bugs
- a mechanical documentation or test cleanup across several tiny issues
- a parent issue plus tightly scoped sub-issues
- one refactor that unlocks several tightly related follow-ups

Split the PR instead when:

- the issues have different milestones or release intent
- the issues have different primary categories
- one issue is user-facing and another is internal cleanup
- one issue requires demo, migration, security, or release-note handling and
  the other does not
- review would be harder because the concerns are unrelated

For a multi-issue PR, choose one primary issue:

- The branch name uses the primary issue number.
- The PR title is based on the primary issue.
- Inherited labels come from the primary issue plus any special labels needed
  for the full PR scope.
- The PR body lists every closed or referenced issue.

Example:

```markdown
## Issue

Closes #123
Closes #124
Refs #130
```

Use `Refs` for related or partial issues that should remain open.

### PR Body Sections

Base uses a minimal standard PR body:

```markdown
## Summary

-

## Issue

Closes #

## Validation

-

## Demo Impact

None.

## Notes

None.
```

`Demo Impact` is required for Base PRs so demo-related changes are considered
intentionally. Use `None.` when the change does not affect Base's demo,
Base-managed demo project, demo docs, or user-visible flows that should be
shown in a demo.

When the issue or PR carries `needs-demo`, `Demo Impact` must explain what demo
content should change. Do not leave it as `None.` for a `needs-demo` PR.

Additional sections are added only when a Base policy, label, or touched area
requires them. Examples include:

- `Security Notes` for security-sensitive changes
- `Migration Notes` for breaking manifest, config, or CLI behavior
- `Release Notes` for user-visible release highlights
- `Docs Impact` for changes that require external documentation updates

Do not add every possible section to every PR. Extra sections should carry
signal, not template noise.

### Base-Managed Project Policy

This policy is for the Base repository. Future Base-managed projects should be
able to declare their own PR workflow requirements instead of inheriting
Base-specific sections such as `Demo Impact` unconditionally.

Base should provide the workflow mechanism and defaults. Each project should
own its labels, required sections, path-triggered sections, and review policy.

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

For the release checklist itself, including `VERSION`, changelog, tags, GitHub
Releases, and the follow-up `codeforester/homebrew-base` tap update, see
[Release Process](release-process.md).

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
