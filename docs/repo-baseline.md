# Repository Baseline

`basectl repo` standardizes the first useful layer of a Base-managed
repository. It is intentionally smaller than project scaffolding: Base creates
common repo hygiene files, a minimal manifest, and a validation command, while
the project still owns its source tree, language framework, packaging, and
product-specific setup.

## Commands

Clone an existing GitHub repository into the configured workspace:

```bash
basectl repo clone basefoundry/base-demo
basectl repo clone base-demo --owner basefoundry
```

`repo clone` is for repositories that already exist on GitHub. Without
`--path`, it clones to `<workspace.root>/<repo>` when `workspace.root` is set in
`~/.base.d/config.yaml`; otherwise it falls back to the parent directory of
`BASE_HOME`. Short repository names require `--owner <owner>` or a
`github.default_owner` value in the user config:

```yaml
github:
  default_owner: basefoundry
  clone_protocol: ssh
```

`github.clone_protocol` may be `ssh` or `https`; it controls the clone URL shown
in planning output while the actual clone delegates to `gh repo clone`.
`--dry-run` prints the resolved repository, destination, clone tool, clone URL,
and command without modifying the filesystem. If the destination already exists
and its `origin` points at the requested GitHub repository, Base treats the clone
as already satisfied. If the destination exists with another origin, Base fails
with an actionable conflict.

Create a new repo baseline:

```bash
basectl repo init base-demo --repo basefoundry/base-demo
```

`repo init` creates the local files, creates the GitHub repository if it does
not already exist, and then configures that GitHub repository when
`--repo <owner/name>` is provided or an existing `origin` remote can be
inferred. New GitHub repositories are private by default; pass `--public` only
when public visibility is intentional. That keeps the common new-repo path to
one command. Use `--no-configure` when GitHub setup should be skipped or when
local-only initialization is desired. Add `--agent-ready` when the baseline
should also seed `AGENTS.md` and `skills.md` for agent-assisted development.

Use `--language <csv>` to record the repository's language profile in the
generated `base_manifest.yaml`. The option may be repeated, and CSV and
repeated forms are equivalent:

```bash
basectl repo init platform \
  --language go,javascript \
  --language typescript
```

The initial vocabulary includes `python`, `go`/`golang`, `java`,
`javascript`/`js`, `typescript`/`ts`, `c`, and `cpp`/`c++`. Base normalizes
aliases, removes duplicates, and keeps the first-seen order. Language selection
is explicit; Base does not infer it by scanning repository files. In this first
slice, non-Python languages are metadata only. Selecting `python` also writes
the explicit `python.manager: uv` contract; it does not silently change an
existing manifest.

Without `--path`, `repo init` creates the repository under the configured
workspace root:

1. `workspace.root` from `~/.base.d/config.yaml` when configured.
2. The parent directory of `BASE_HOME` when no workspace root is configured.

That keeps `repo init base-demo` stable even when it is run from inside another
repository or from a nested directory such as `~/work/base/docs`. Use
`--path <path>` when the new repository should live somewhere else.

Open the generated baseline through a pull request when the target repository
already exists:

```bash
basectl repo init base-demo \
  --path ~/work/base-demo \
  --repo basefoundry/base-demo \
  --issue 123 \
  --pr
```

`--pr` requires `--issue <number>` and the target path to be an existing, clean
Git worktree. It creates or uses the canonical branch
`<category>/<issue>-<YYYYMMDD>-repo-baseline-<name>`, writes any missing
baseline files, commits only the baseline file set, pushes the branch to
`origin`, and opens a GitHub pull request against the repository default branch.
Real PR runs derive and verify the issue's standard category label; offline
`--pr --dry-run` previews also require `--category <name>`.
When `--agent-ready` is passed, the baseline PR also includes `AGENTS.md` and
`skills.md`.
When the generated baseline produces file changes, `repo init --pr` stops after
opening the pull request. After that pull request is merged, rerun the same
`repo init --pr` command; when there are no baseline file changes left, it
continues with the same GitHub-side configuration that `repo init` normally
performs. `repo configure` remains available when only GitHub-side settings need
to be repaired or resynced.

Check the local baseline:

```bash
basectl repo check ~/work/base-demo
basectl repo check ~/work/base-demo --agent-ready
```

Seed optional repo-local agent guidance:

```bash
basectl repo init base-demo --repo basefoundry/base-demo --agent-ready
basectl repo agent-guidance ~/work/base-demo --repo-name base-demo
basectl repo agent-guidance ~/work/base-demo --repo-name base-demo --issue 123 --category enhancement --pr --dry-run
```

Reapply GitHub-side repository settings and labels:

```bash
basectl repo configure ~/work/base-demo --repo basefoundry/base-demo
```

`repo configure` is idempotent and safe to rerun when repository settings drift.
Use `--dry-run` on `repo init` or `repo configure` to print the planned file and
GitHub changes without applying them. In dry-run mode, `repo init` explicitly
reports whether it would create a GitHub repository or why GitHub creation is
being skipped.

`repo init` and `repo configure` also configure a repo-named GitHub Project by
default when a GitHub repository is known. If the Project is missing, Base copies
`base-project-template`, links the new Project to the repository, and backfills
the repository's existing issues into it. Pass `--no-project` to skip Project V2
metadata, `--project <title>` to override the Project title, `--project-owner
<login>` to override the owner, `--project-schema base-project` to select the
schema, and repeat `--initiative-option <name>` to seed repository-specific
Initiative values. If `.github/base-project.yml` exists, Base reads repo-owned
`Area` and `Initiative` options from that file and adds missing Project options
without deleting or renaming existing options. Base also applies the file's
`issue_defaults` to repo Project issue items when those field values are still
blank.
During migration from an older shared Project, pass
`--copy-project-fields-from <title>` to copy missing Project item field values
by issue, field name, and option name into the repo Project. Existing target
values are preserved.
If a repo Project already exists but its views do not match the Base standard,
pass `--replace-project` during `repo configure`. Base renames and closes the
old Project, copies `base-project-template` into a new Project with the original
title, links the new Project to the repository, backfills repository issues,
copies missing issue field values from the legacy Project, and then applies repo
defaults. Replacement changes the Project number and URL, so keep the closed
legacy Project as the audit trail. Already-standard Projects are left intact
and continue through normal metadata repair.
`basectl gh project` is the lower-level direct surface for Project inspection,
schema repair, and issue field updates.

Repo Project taxonomy config uses this shape:

```yaml
project:
  areas:
    - Demo App
    - Documentation
  initiatives:
    - Demo Polish
    - Portfolio Dashboard
  issue_defaults:
    status: Backlog
    priority: P2
    area: Product
    initiative: Adoption Polish
    size: S
```

`areas` and `initiatives` are applied by `repo configure`. `issue_defaults` is
validated by Project tooling, used by `basectl gh issue create` when it adds new
issues to the repo Project, and applied by `repo configure` to existing Project
issue items that are missing those field values.
When Project metadata is enabled, `repo configure` also creates missing
repo-owned Project support files such as `.github/base-project.yml` and
`.github/workflows/project-intake.yml` without overwriting existing files. This
lets older Base-managed repositories pick up the external-issue intake fallback
without rerunning a full repository initialization.
Independently of Project metadata, `repo configure` also seeds a missing
`.github/workflows/issue-branch-policy.yml` so older repositories can adopt the
semantic branch check through a reviewed commit.

## Local Baseline

`repo init` creates these files when they do not already exist:

- `README.md`
- `VERSION`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `.github/pull_request_template.md`
- `.github/base-project.yml`
- `LICENSE`
- `.gitignore`
- `base_manifest.yaml`
- `tests/validate.sh`
- `.github/workflows/issue-branch-policy.yml`
- `.github/workflows/project-intake.yml`
- `.github/workflows/tests.yml`

Existing files are left unchanged. This makes `repo init` useful both for a
fresh directory and for bringing a small existing repository up to Base's
minimum expectations.

The generated `base_manifest.yaml` declares the project name and a test command.
When language profiles are selected, it also records the normalized languages
and applies the Python uv profile:

```yaml
schema_version: 1

project:
  name: base-demo
  languages:
    - python
    - javascript

python:
  manager: uv

test:
  command: ./tests/validate.sh
```

The generated validation script checks for the required baseline files. It is
not a replacement for project tests; it is the seed contract that lets
`basectl test <project>` work immediately.

The generated `.github/workflows/project-intake.yml` handles issue open,
reopen, close, and manual dispatch events. It is a visible fallback for issues
created outside `basectl gh issue create`: the workflow idempotently adds the
issue to the repo-named Project and sets `Status`, `Priority`, `Size`, `Area`,
and `Initiative` from the generated defaults. Set a `BASE_PROJECT_TOKEN`
Actions secret with Project write access. `basectl repo configure` checks for
`BASE_PROJECT_TOKEN` when Project support is enabled and reports the
`gh secret set BASE_PROJECT_TOKEN` command if the secret is missing. Without
that secret, Project Intake fails before running Project operations. During
Project operations, the generated workflow retries retryable GitHub API pressure
once after the reported `Retry-After` or rate-limit reset delay when available.
`401 Unauthorized` / `Bad credentials` errors remain clear token configuration
failures with `BASE_PROJECT_TOKEN` rotation guidance and can be rerun through
`workflow_dispatch` after the secret is repaired.

For older repositories that predate this workflow, rerun
`basectl repo configure <path> --repo <owner/name>` to create the missing
workflow while leaving existing files unchanged.

Generated workflows use Base's shared CI hardening defaults: least-privilege
workflow permissions, concurrency cancellation, job timeouts, and pinned
first-party actions where actions are used. Existing workflow files are still
left unchanged; rerun `repo init` or `repo configure` only creates missing
baseline workflows.

The generated `.github/base-project.yml` starts with the shared issue defaults
and empty repo-specific taxonomy lists:

```yaml
project:
  areas: []
  initiatives: []
  issue_defaults:
    status: Backlog
    priority: P2
    area: Product
    initiative: Adoption Polish
    size: S
```

Edit `areas`, `initiatives`, or the default `area`/`initiative` in the baseline
pull request before merging when the repository already knows its taxonomy.
Leaving the option lists empty is valid; future `repo configure` runs still
apply the shared Project fields and issue defaults.

## Optional Agent Guidance

`repo init --agent-ready` includes the agent instructions and skills index in a
new baseline. For existing repositories, `repo agent-guidance` creates
repo-local guidance files for agent-assisted development when they do not
already exist:

- `AGENTS.md`
- `skills.md`
- `.github/pull_request_template.md`

The command accepts `--repo-name <name>`, `--default-branch <name>`, and
`--validation-command <command>` so generated examples match the repository.
The default branch is inferred from the target Git checkout when possible and
falls back to `main` with a note. Other defaults come from the target path and
`./tests/validate.sh`.

Existing files are left unchanged. This keeps the guidance layer safe for repos
that already have their own instructions or pull request template. After each
non-dry-run execution, Base prints how many guidance files were created and
which existing files were left unchanged.

Use `--pr --issue <number>` to commit generated guidance files on a canonical
issue-backed branch and open a draft pull request. The target path must be the
root of a clean Git worktree. Base infers the GitHub repository from the target
`origin` remote, or you can pass `--repo <owner/name>` explicitly. Only the
generated guidance files are staged for the helper commit. Real PR runs derive
and verify the issue's standard category label. Because dry-run remains offline,
`--pr --dry-run` also requires `--category <name>`.

Preview the files without writing them:

```bash
basectl repo agent-guidance ~/work/base-demo --repo-name base-demo --dry-run
basectl repo agent-guidance ~/work/base-demo --repo-name base-demo --issue 123 --category enhancement --pr --dry-run
```

Include the optional guidance files in local baseline checks only when the repo
has opted into this layer:

```bash
basectl repo check ~/work/base-demo --agent-guidance
basectl repo check ~/work/base-demo --agent-ready
```

Use `--agent-guidance` when checking only the standalone optional guidance
layer. Use `--agent-ready` when checking the same file contract through the
`repo init --agent-ready` repair path; missing files are reported with a
no-overwrite `repo init ... --agent-ready` fix command.

## Git Workflow

The generated `CONTRIBUTING.md` and pull request template seed a portable
Base-managed project workflow:

- create or choose a GitHub issue before implementation work
- use one standard category label: `bug`, `enhancement`, `documentation`, `ci`,
  or `security`
- branch from the issue with `<category>/<issue>-<YYYYMMDD>-<slug>`
- use a dedicated Git worktree for each pull request
- keep each pull request scoped to the issue and link it with `Fixes #<issue>`
  or `Closes #<issue>` when the merge should close the issue
- run project checks before opening or updating the pull request
- update `CHANGELOG.md` only for notable user-visible or release-worthy changes
- after merge, sync the default branch, remove the worktree, and delete merged
  local and remote branches when safe

The generated pull request template keeps the project baseline intentionally
portable: `Summary`, `Issue`, `Validation`, `Notes`, and a short checklist.
Base-specific sections such as `Demo Impact` belong only in projects that
choose that policy.

Projects that need generated PR body sections can declare them in
`base_manifest.yaml` under `github.pr.required_sections`. Use `default` for
sections every PR should carry, `labels` for issue or PR label triggers, and
`paths` for changed-file globs.

## GitHub Configuration

`repo init` creates the GitHub repository when needed, using private visibility
unless `--public` is passed. Then `repo init` and `repo configure` standardize
the current GitHub repository policy:

- Issues enabled
- Projects enabled
- squash merge enabled
- merge commits disabled
- rebase merge disabled
- delete branch on merge enabled
- squash commit message set to PR title and description
- Base-managed default branch protection enabled
- Base-managed branch naming enforcement enabled for non-default branches
- trusted issue/category branch policy workflow installed
- standard GitHub Project metadata enabled

They also create or update these labels:

- `bug`
- `enhancement`
- `documentation`
- `ci`
- `security`
- `needs-demo`

Default branch protection is intentionally modest. `repo configure` creates or
updates a named repository ruleset, `Base default branch protection`, targeting
`~DEFAULT_BRANCH`. The ruleset requires pull requests before merge and blocks
branch deletion and non-fast-forward updates such as force pushes. When the
trusted Issue Branch Policy workflow is active and has produced a recent
trusted success, the ruleset also requires `base/issue-branch-policy`, bound to
the GitHub Actions integration. It does not manage other status checks,
approval counts, CODEOWNERS, teams, or repository secrets. Pass
`--no-protect-default-branch` when a repository intentionally skips this
Base-managed ruleset.

Branch naming enforcement is tool-independent. `repo configure` creates or
updates the active `Base branch naming` ruleset for all non-default branches and
requires `<category>/<issue>-<YYYYMMDD>-<slug>`, using one of the standard Base
categories. The CLI and semantic workflow also reject impossible calendar
dates. This rejects nonconforming remote branches whether they come from a
human, an AI tool, a GitHub Action, or a Base helper.

The generated `.github/workflows/issue-branch-policy.yml` verifies the semantic
half of the convention: the referenced number must be an issue with exactly one
standard category label, and the branch prefix must match it. The workflow uses
`pull_request_target`, does not check out or execute pull-request code, and
publishes `base/issue-branch-policy` to the PR head SHA. Issue label events
queue default-branch revalidation runs for matching open pull requests, using
the same head-SHA concurrency key as ordinary pull request validation. Each run
validates every open pull request sharing that SHA, and synchronize events
revalidate peers left on the previous SHA. Because GitHub commit statuses are
SHA-scoped, the workflow is an asynchronous semantic gate; the branch naming
ruleset remains the immediate enforcement boundary for branches created in the
repository. Fork branches cannot be governed by the repository's branch-name
ruleset, so their semantic validation occurs through the workflow. `repo configure`
seeds the workflow when it is missing, but only makes its status required after
the workflow is present on the default branch and a recent default-branch
dispatch has produced a trusted GitHub Actions status. Feature-branch runs are
ignored. Base pins the requirement to that integration and preserves an
already-bound requirement if retained run history later expires. Commit and
merge a newly seeded workflow, dispatch it on the default branch for a pull
request, then rerun `repo configure` to activate the required status.

GitHub rulesets are available for public repositories on GitHub Free and for
public and private repositories on GitHub Pro, Team, or Enterprise plans. When
GitHub reports that rulesets are unavailable for a private repository's plan,
`repo configure` leaves the supported settings and labels in place, logs a
warning, and skips the unavailable Base-managed rulesets.

The Project metadata schema creates or updates single-select Project fields on
the repo Project:

- `Status`: `Triage`, `Backlog`, `Ready`, `In Progress`, `In Review`, `Done`
- `Priority`: `P0`, `P1`, `P2`, `P3`
- `Area`: `CLI`, `Setup`, `Workspace`, `Manifest`, `Runtime`, `Shell`,
  `Python`, `Docs`, `CI`, `Packaging`, `Security`, `Product`
- `Size`: `T`, `S`, `M`, `L`
- `Initiative`: `BanyanLabs Dogfood`, `BanyanLabs Dogfooding`,
  `Workspace Handling`, `pyproject/uv`, `v1.0 Readiness`, `Adoption Polish`,
  `Contract Hardening`, `Agentic Coding Platform`, plus values passed with
  `--initiative-option`

`T` means a tiny, obvious issue with no design decision or cross-module
behavior. `S` remains the generated and fallback default because new issues are
not always fully scoped at creation time. `basectl repo configure` and
`basectl gh project configure` add missing shared Project options
additively; existing item values are preserved.

`--copy-project-fields-from <title>` copies these single-select fields when the
source Project item has a value and the target repo Project item does not:
`Status`, `Priority`, `Area`, `Initiative`, and `Size`. Values are skipped and
reported when the repo Project does not have a matching option.

When Project V2 access is unavailable, `repo init` and `repo configure` log a
warning that includes `gh auth refresh -h github.com -s project`, keep the
supported repository settings in place, and skip Project metadata. Other
Project errors remain failures because they can indicate a conflicting field
schema or a broken GitHub request.

In apply mode, GitHub configuration requires the GitHub CLI and an authenticated
session:

```bash
gh auth login -h github.com
```

Dry-run mode does not require authentication because it only prints the planned
`gh` commands.

## Boundaries

The default branch protection policy manages only the Base-owned
`base/issue-branch-policy` required status. It does not manage other required
checks, approval counts, repository secrets, teams, CODEOWNERS, or Base-specific
PR sections such as `Demo Impact`. The optional agent guidance baseline also
does not install Superpowers, manage `~/.codex/config.toml`, or vendor
third-party methodology files.
