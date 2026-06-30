# Base Workflow Context

## Pre-Edit Workflow Gate

Before modifying Base files, classify the request.

For implementation work in `basefoundry/base`, do not edit on `main`. Create
or choose the GitHub issue, set the required Project metadata, move Project
`Status` to `In Progress`, create the issue branch and dedicated worktree, and
verify the active branch is not `main` before editing files.

Read-only investigation, design-only discussion, and requests explicitly scoped
to local-only/no-PR work may stay outside this gate. If the scope turns into
issue-backed implementation work after edits have started, stop, create or
choose the issue, move the work onto the issue branch/worktree, and then
continue.

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
allows it. When an issue is tracked in the repo-named Project, move its status
through `In Progress`, `In Review`, and `Done` as the work advances. Repo-named
Project metadata uses five fields: `Status`, `Priority`, `Area`, `Size`, and
`Initiative`.
Use the smallest accurate `Size` when creating issues: `T` for tiny obvious
work, `S` for normal small work or unknown scope, `M` for interacting changes,
and `L` only for work that should probably be split. The default remains `S`
when automation cannot infer scope.
Issue creation is unassigned by default unless `basectl gh issue create`
receives `--assignee <login>` or `.github/base-project.yml` sets
`project.issue_defaults.assignee`; use `--no-assignee` to skip that repo-local
default for a specific issue.
Starter issues for first external contributors use the `good first issue`
label only when the issue has explicit acceptance criteria, concrete Project
metadata, `Size` `T` or `S`, and local validation that does not require private
state. Use `help wanted` without `good first issue` for broader work where
outside help is useful but deeper Base context is needed.

When updating GitHub issues, pull requests, labels, comments, or Project
metadata, protect the API budget. Use a read-plan-write flow: fetch the target
IDs and current values, compute the minimal local diff, then write only changed
fields. Do not run parallel mutating GitHub requests. Prefer exact issue and
Project item updates, exact-item GraphQL mutations, or
`basectl gh project issue set-fields` with known targets over broad scans. Cache
IDs during the train, pause between bulk writes, and obey `retry-after`,
`x-ratelimit-reset`, secondary-limit, and content-generation-limit responses. If
a limit is hit, stop writes and report completed and remaining targets before
resuming later. Consider GitHub Apps only for recurring multi-repo automation
that needs a separate installation budget and narrowly scoped permissions.

Base-managed repositories should carry `.github/workflows/project-intake.yml`
as the fallback for issues created outside `basectl gh issue create`.
`basectl repo init` seeds it for new repositories, and `basectl repo configure`
creates it when missing from older repositories.
When a shared repo or Project schema repair needs to roll across a local repo
family, use `basectl workspace configure --dry-run` first, then
`basectl workspace configure`; it delegates to the same idempotent per-repo
`repo configure` path and reports configured, skipped, and failed repos.
If a repo Project has GitHub's default `View 1` instead of the standard Base
views, use `basectl repo configure --replace-project` with `--repo`; Base
archives the old Project and recreates it from `base-project-template`.
Already-standard Projects are left intact and continue through metadata repair.

## Branch And Worktree Flow

Use a dedicated worktree for PR work. Branch names follow:

```text
<category>/<issue>-<YYYYMMDD>-<slug>
```

The standard worktree location is:

```text
~/work/base-worktrees/<slug>
```

Start from current `origin/main`, keep the worktree while the PR is open, and
clean it up after merge.

## Pull Requests

Pull requests are issue-backed by default and scoped to one issue unless there
is a documented exception. `basectl gh pr create` adds `Fixes #<issue>` from
Base branch names by default; pass `--no-fixes` only when the PR should not
close the issue automatically. If `base_manifest.yaml` declares `github.pr`,
the command renders required PR sections from that project policy. PR bodies
should include:

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
First external PRs should start from an issue labeled `good first issue`.
Contributor-facing guidance lives in `CONTRIBUTING.md`; the workflow policy and
starter-issue criteria live in `docs/github-workflow.md`.
When running the full source-checkout suite from a linked issue worktree under
`~/work/base-worktrees/<slug>`, set the reusable library path explicitly:

```bash
BASE_BASH_LIBS_DIR=~/work/base-bash-libs/lib/bash env -u BASE_HOME ./bin/base-test
```

## Release Flow

Base releases are explicit ceremonies. Ordinary PRs do not update `VERSION`.
Release-prep PRs update `VERSION`, README release text, and `CHANGELOG.md`.

The `basectl release check|plan|notes` commands are read-only inspection
commands. `basectl release publish` is guarded and creates the annotated tag and
GitHub Release after checks pass. The Homebrew tap update happens in
`basefoundry/homebrew-base` after the Base tag and GitHub Release exist.
Supported macOS tap releases should publish Homebrew bottles before the tap PR
is merged: run the tap's `Build Base Bottles` workflow from the tap release
branch, let it upload bottle assets to the tap release `base-vX.Y.Z`, and commit
the generated `bottle do` stanza back to `Formula/base.rb`.
Homebrew formula audits should be run by formula name, for example
`brew audit --new --formula basefoundry/base/base` and
`brew audit --new --formula basefoundry/base/base-bash-libs`. Keep
`base-bash-libs` core-ready as a standalone dependency so a future
Homebrew/core `basefoundry` formula can declare `depends_on "base-bash-libs"`.
Setup parallelism should follow `docs/setup-parallelism.md`: model setup as a
deterministic plan and parallelize only read-only preflight/planning work before
considering mutating installers.

## AI Context Maintenance

Every meaningful PR should evaluate whether `.ai-context/` needs an update.
Expected updates include command changes, architecture changes, workflow
changes, manifest schema changes, release/status changes, and durable product
decisions.
