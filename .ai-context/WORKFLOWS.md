# Base Workflow Context

## Issue-First Work

Base uses GitHub Issues as the public product backlog. Implementation work
should start from a GitHub issue with one primary category label:

- `bug`
- `enhancement`
- `documentation`
- `ci`
- `security`

Do not create new `type:*` labels.

Issues created by automation should be assigned to `codeforester` when GitHub
allows it. When an issue is tracked in the Base Roadmap Project, move its
status through `In Progress`, `In Review`, and `Done` as the work advances.
Base roadmap Project metadata uses five fields: `Status`, `Priority`, `Area`,
`Size`, and `Initiative`.

## Branch And Worktree Flow

Use a dedicated worktree for PR work. Branch names follow:

```text
<category>/<issue>-<YYYYMMDD>-<slug>
```

The standard worktree location is:

```text
~/work/base-worktrees/<slug>
```

Start from current `origin/master`, keep the worktree while the PR is open, and
clean it up after merge.

## Pull Requests

Pull requests are issue-backed by default and scoped to one issue unless there
is a documented exception. PR bodies should include:

- summary of what changed and why
- issue reference such as `Fixes #<issue>` or `Closes #<issue>`
- validation commands and relevant output
- `Demo Impact`
- notes or tradeoffs when helpful
- whether `.ai-context/` was updated or not applicable

The issue owns milestone and Project tracking. PRs should inherit relevant
labels but should not be added as duplicate Project items by default.

## Validation

Prefer the narrowest check that proves the change, then broaden when shared
behavior is touched.

Common commands:

```bash
git diff --check
basectl test base
```

Python tests run with:

```bash
PYTHONPATH=lib/python:cli/python python -m pytest
```

Integration tests live under `tests/integration/` and run against temporary
homes, workspaces, and fake projects. Add integration coverage for
cross-command workflows, setup/check/doctor interactions, shell profile
behavior, installation layout assumptions, or public behavior that cannot be
proven by a focused unit test.

Documentation-only changes usually need `git diff --check`.

## Release Flow

Base releases are explicit ceremonies. Ordinary PRs do not update `VERSION`.
Release-prep PRs update `VERSION`, README release text, and `CHANGELOG.md`.

The `basectl release check|plan|notes` commands are read-only inspection
commands. `basectl release publish` is guarded and creates the annotated tag and
GitHub Release after checks pass. The Homebrew tap update happens in
`codeforester/homebrew-base` after the Base tag and GitHub Release exist.
Supported macOS tap releases should publish Homebrew bottles before the tap PR
is merged: run the tap's `Build Base Bottles` workflow from the tap release
branch, let it upload bottle assets to the tap release `base-vX.Y.Z`, and commit
the generated `bottle do` stanza back to `Formula/base.rb`.

## AI Context Maintenance

Every meaningful PR should evaluate whether `.ai-context/` needs an update.
Expected updates include command changes, architecture changes, workflow
changes, manifest schema changes, release/status changes, and durable product
decisions.
