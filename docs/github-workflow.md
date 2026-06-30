# GitHub Workflow

Base uses GitHub Issues as the public product backlog and Git worktrees for
parallel pull request trains. This page captures the repository workflow so
humans and AI-assisted development agents follow the same rules.

## Pre-Edit Workflow Gate

Before modifying Base files, classify the request.

For implementation work in `basefoundry/base`, do not edit on `main`. Create
or choose the GitHub issue, set the required Project metadata, move Project
`Status` to `In Progress`, create the issue branch and dedicated worktree, and
verify the active branch is not `main` before editing files.

This gate does not apply to read-only investigation, design-only discussion, or
requests explicitly scoped to local-only/no-PR work. If the scope changes into
issue-backed implementation work after edits have started, stop, create or
choose the issue, move the work onto the issue branch/worktree, and then
continue.

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
- `good first issue`
  Small, well-scoped issues that an external contributor can complete without
  private maintainer context.
- `help wanted`
  Issues where maintainers want outside contribution, even if the work is too
  broad or specialized to be a first contribution.

Avoid creating new `type:*` labels. Older issues may still carry historical
`type:fix`, `type:feat`, `type:chore`, or `type:docs` labels, but new work
should use the labels above.

## Starter Issues

Use `good first issue` only when the issue is genuinely ready for a first
external PR. Starter issues should have:

- clear acceptance criteria in the issue body
- one primary category label, usually `documentation`, `ci`, or a very narrow
  `enhancement`
- Project fields set before advertising the issue: `Status` `Ready`,
  `Priority` `P3` or `P2`, a concrete `Area`, `Initiative`, and `Size` `T` or
  `S`
- a validation path that can be run locally without credentials, paid services,
  or private repository state

Good first issues should not require architectural decisions, cross-command
refactors, release coordination, secret configuration, or knowledge that only
maintainers have. Use `help wanted` without `good first issue` when outside
help is welcome but the work needs deeper Base context.

Maintainers should keep at least one real starter issue open when the project is
inviting new contributors. If no open backlog item qualifies, create a small
documentation, fixture, or test-hygiene issue instead of labeling broad design
work as a starter task.

## Issue Assignment

Issues created by automation for the Base repository should be assigned to the
current primary maintainer. Today that maintainer is `codeforester`, and
`.github/base-project.yml` carries the same repo-local default for
`basectl gh issue create`.

If assignment fails, the automation should mention that in its summary instead
of silently leaving the issue unassigned.

## Issue Project Metadata

When an issue is tracked in the repo-named Project, use the standard Base
Project fields:

- `Status`: `Triage`, `Backlog`, `Ready`, `In Progress`, `In Review`, `Done`
- `Priority`: `P0`, `P1`, `P2`, `P3`
- `Area`: `CLI`, `Setup`, `Workspace`, `Manifest`, `Runtime`, `Shell`,
  `Python`, `Docs`, `CI`, `Packaging`, `Security`, `Product`
- `Size`: `T`, `S`, `M`, `L`
- `Initiative`: `BanyanLabs Dogfood`, `Workspace Handling`, `pyproject/uv`,
  `v1.0 Readiness`, `Adoption Polish`

Use the smallest accurate `Size` when creating or triaging an issue:

- `T`: tiny, obvious change; usually one file or one Project metadata action,
  with no design decision or cross-module behavior.
- `S`: small, focused change that may still need tests, docs, or a few files.
- `M`: medium change with multiple files or interactions.
- `L`: large change that should be split if possible.

Automation defaults to `S` when no explicit size is supplied. Agents creating
issues should pass an explicit size when the scope is already clear; use `S`
when the issue still needs normal triage.

Keep the issue's `Status` field aligned with the implementation train:

- Set `Status` to `In Progress` before creating the implementation branch or
  starting work in a worktree.
- Set `Status` to `In Review` when the pull request opens.
- After the pull request merges and the issue closes, verify `Status` is
  `Done`; update it explicitly if automation did not.
- If Project V2 access is unavailable, the issue is not in the Project, or the
  status update fails, mention that in the work summary instead of silently
  skipping it.

Do not add pull requests as separate Project items by default. The issue owns
milestone and Project tracking so roadmap views do not double count the work.

`basectl repo init` and `basectl repo configure` configure a repo-named Project
by default when a GitHub repository is available. Base copies
`base-project-template` when the repo Project is missing, links the Project to
the repository, and backfills existing repository issues. When
`.github/base-project.yml` exists, Base also adds missing repo-specific `Area`
and `Initiative` options from that file and applies the same file's
Project-field `issue_defaults` to Project issue items that are missing those
values. The same config can set `project.issue_defaults.assignee` as a
repo-local issue creation default. `basectl gh issue create` uses those
defaults immediately when it creates an issue and adds it to the repo Project.

Base-managed repositories also carry `.github/workflows/project-intake.yml`.
That workflow is a repo-visible fallback for issues created through GitHub UI,
plain `gh issue create`, or external connectors that can bypass
`basectl gh issue create` and GitHub's hidden Project auto-add filters.
`basectl repo configure` creates this workflow when it is missing from older
Base-managed repositories. Set a `BASE_PROJECT_TOKEN` Actions secret with
Project write access so the workflow can idempotently add the issue to the
repo-named Project and set `Status`, `Priority`, `Size`, `Area`, and
`Initiative` from the generated defaults on issue open, reopen, and close
events. `basectl repo configure` verifies that the secret exists when Project
support is enabled and prints a `gh secret set BASE_PROJECT_TOKEN` command when
the required secret is missing. Without that secret, Project Intake fails before
running Project operations.
Use `basectl gh project` directly for lower-level Project inspection,
schema repair, or issue field updates.
When migrating from an existing shared Project, pass
`--copy-project-fields-from <title>` to copy missing `Status`, `Priority`,
`Area`, `Initiative`, and `Size` issue item values into the repo Project without
overwriting values already set there. Older Base issues may have been tracked in
`Base Roadmap`; use that title only as the migration source when copying legacy
field values into the current repo-named Project.

```bash
basectl gh project doctor --project base --owner basefoundry
basectl gh project configure --project base --owner basefoundry --schema base-project
basectl repo configure ~/work/base --repo basefoundry/base --copy-project-fields-from "Base Roadmap"
basectl gh project issue set-fields 604 --repo basefoundry/base --project base --owner basefoundry --status Backlog --priority P2 --area CLI --initiative "v1.0 Readiness" --size M
```

## Preferred GitHub Interface

Use `basectl gh` as the preferred interface for Base repository GitHub
workflows when it supports the operation.

This keeps Base dogfooding its own workflow tool for common issue, branch, PR,
and repository hygiene tasks. For example, prefer `basectl gh issue create`,
`basectl gh issue start`, `basectl gh pr create`, and `basectl gh branch prune`
over hand-written `gh` commands when those commands are available and local
tooling is authenticated.

`basectl gh issue create` defaults to the `enhancement` category when
`--category` is omitted and prints that choice. Issues are unassigned unless
`--assignee <login>` is passed or `.github/base-project.yml` sets
`project.issue_defaults.assignee`; pass `--no-assignee` to ignore a repo-local
default for one issue. `basectl gh pr create` auto-injects `Fixes #<issue>`
when the current branch follows the Base `<category>/<issue>-<YYYYMMDD>-<slug>`
convention; pass `--no-fixes` when the PR should not close the issue
automatically. When `base_manifest.yaml` declares `github.pr`, PR creation
renders the body from that project policy and still preserves the issue link.

Fallbacks are allowed when `basectl gh` does not support the needed operation,
when local GitHub CLI authentication is unavailable, or when the GitHub
connector provides a safer structured API for the task. In those cases, use the
GitHub connector, raw `gh`, or `git` as appropriate and keep the resulting
issue labels, branch names, assignments, and PR bodies aligned with this
policy.

## GitHub API Budget Discipline

Treat GitHub API budget, especially Project V2 mutation capacity and
content-generating issue, PR, label, and comment writes, as shared
infrastructure. Agents and scripts should be quiet, exact, and idempotent even
when the primary API rate limit still has capacity.

Use these rules for issue and Project writes:

- Serialize mutating requests. Do not run parallel `gh issue`, `gh pr`,
  `gh label`, comment, or Project field writes against the same repository or
  Project.
- Prefer exact-item GraphQL or Base wrapper operations when the issue, PR, or
  Project item is already known. Avoid broad Project scans to update one issue.
- Read the current item state first, compute the minimal diff, and write only
  fields that actually need to change.
- Reuse data gathered earlier in the run instead of refetching the same issue,
  Project item, or field schema repeatedly.
- Page through lists only when the task genuinely needs a list. Stop once the
  target item is found.
- Keep dry runs read-only. They may explain planned writes, but should not probe
  by performing and undoing mutations.

If GitHub reports rate limiting, abuse detection, a secondary limit,
content-generation throttling, `retry-after`, or `x-ratelimit-reset`, stop
mutating immediately. Wait for any reset or retry window GitHub provides, then
retry the smallest failed operation once. If pressure continues, leave the item
unchanged, report the exact operation that failed, and resume later instead of
looping or widening the scan.

GitHub Apps are appropriate for recurring multi-repo automation that needs its
own installation-level rate budget and narrowly scoped permissions. They are not
required for ordinary one-off Base issue, PR, or Project updates from a local
development session.

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

Before committing or opening a pull request, verify the active branch is not
`main` and follows the issue-backed branch convention.

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

Before creating a worktree, check whether the current checkout is already a
linked worktree for the intended issue:

```bash
git rev-parse --git-dir
git rev-parse --git-common-dir
git branch --show-current
git rev-parse --show-superproject-working-tree
```

When the git directory differs from the common directory, and the checkout is
not a submodule, the current checkout is already a linked worktree. A
non-empty `--show-superproject-working-tree` result means the checkout is a
submodule and should be treated as a normal repository for worktree detection.
Continue in an existing issue worktree instead of creating a nested or
duplicate worktree. If the checkout is a normal repository, create the issue
worktree from current `origin/main`.

Create a worktree from current `origin/main`:

```bash
git fetch origin main
git worktree add -b documentation/241-20260529-document-github-workflow \
  ~/work/base-worktrees/documentation-241-github-workflow origin/main
```

Keep the worktree while the pull request is open so review feedback can be
handled on the same branch. Cleanup happens after merge, or after an explicit
discard decision.

After a pull request is merged:

```bash
git -C ~/work/base pull --ff-only origin main
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

Projects can declare their PR body policy in `base_manifest.yaml`:

```yaml
github:
  pr:
    template: .github/pull_request_template.md
    required_sections:
      default:
        - Summary
        - Issue
        - Validation
      labels:
        needs-demo:
          - Demo Impact
        security:
          - Security Notes
        breaking-change:
          - Migration Notes
      paths:
        docs/**:
          - Docs Impact
        migrations/**:
          - Migration Plan
          - Rollback Plan
```

`default` sections are always rendered. `labels` and `paths` add sections when
the linked issue or changed files match. Missing sections are appended to the
configured template, and duplicate headings are skipped.

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
work. Follow the issue Project status transitions above instead of adding a
separate PR item to the Project.

PR reviewers are PR-specific and should be selected from the implementation
surface, ownership, and risk of the change rather than copied from the issue.

### Review Feedback

Review feedback should be handled as technical input, not as an automatic patch
queue. Before implementing a suggestion, check whether it is correct for Base's
architecture, product boundaries, supported platforms, and current tests.

Implement clear, correct feedback directly. Push back or ask for clarification
when feedback would:

- move project-specific behavior into Base
- make `check` or `doctor` mutate local state
- broaden a narrow PR into an architecture change
- conflict with existing command contracts or validation rules
- add unused behavior that is not required by the issue

Fix one review item or related group at a time, then rerun the narrowest
verification that proves the change.

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

Milestones represent release intent, not workflow state. Active 1.x release
planning should live in the repository's
[GitHub Milestones](https://github.com/basefoundry/base/milestones); the
examples below are shipped historical milestones kept as a product-roadmap
record.

Historical shipped Base milestones:

- `SHIPPED - v0.1.0 - Public baseline`
  Current public baseline for Base's first installable product shape.
- `SHIPPED - v0.2.0 - Adoption polish`
  Installer, Homebrew, README, changelog, issue templates, and workflow polish.
- `SHIPPED - v0.3.0 - Project orchestration`
  Project test execution, mise integration, manifest refinement, and a real
  Base-managed demo project.
- `SHIPPED - v0.4.0 - CI and Linux foundation`
  Linux runtime support and CI-oriented `basectl ci` behavior.
- `SHIPPED - v1.0.0 - Stable public release`
  Stable manifest contracts, compatibility expectations, and upgrade policy.

Every issue does not need a milestone. Use milestones when the issue contributes
to a concrete release goal.

For the release checklist itself, including `VERSION`, changelog, tags, GitHub
Releases, and the follow-up `basefoundry/homebrew-base` tap update, see
[Release Process](release-process.md).

## Projects

Use one operational GitHub Project per repository. The repo Project title should
match the repository name, and new repo Projects should be copied from
`base-project-template`.

Recommended fields:

- `Status`: Triage, Backlog, Ready, In Progress, In Review, Done
- `Priority`: P0, P1, P2, P3
- `Area`: repo-specific options declared in `.github/base-project.yml`
- `Size`: T, S, M, L
- `Initiative`: repo-specific options declared in `.github/base-project.yml`

Keep `Status`, `Priority`, and `Size` standardized across repos. Keep `Area`
and `Initiative` repo-specific, and let `basectl repo configure` add missing
options additively from the repo config file.

Useful views:

- Backlog table for open Backlog issues
- Board by status
- By Status table
- Roadmap timeline

If a repo Project exists with nonstandard views such as GitHub's default
`View 1`, repair it with `basectl repo configure --replace-project`. Base
archives the old Project by renaming and closing it, creates a fresh Project
from `base-project-template`, backfills repository issues, and copies missing
issue field values from the legacy Project. The new Project has a different
Project number and URL. If the Project already has the standard Base views,
`--replace-project` leaves it intact and continues normal metadata repair.

Repo Projects show workflow and prioritization. Milestones show release
grouping. Cross-repo portfolio Projects should be curated roll-ups rather than
the default destination for every repo issue.
