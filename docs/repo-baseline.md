# Repository Baseline

`basectl repo` standardizes the first useful layer of a Base-managed
repository. It is intentionally smaller than project scaffolding: Base creates
common repo hygiene files, a minimal manifest, and a validation command, while
the project still owns its source tree, language framework, packaging, and
product-specific setup.

## Commands

Create a new repo baseline:

```bash
basectl repo init base-demo --repo codeforester/base-demo
```

`repo init` creates the local files, creates the GitHub repository if it does
not already exist, and then configures that GitHub repository when
`--repo <owner/name>` is provided or an existing `origin` remote can be
inferred. New GitHub repositories are private by default; pass `--public` only
when public visibility is intentional. That keeps the common new-repo path to
one command. Use `--no-configure` when GitHub setup should be skipped or when
local-only initialization is desired.

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
  --repo codeforester/base-demo \
  --pr
```

`--pr` requires the target path to be an existing, clean Git worktree. It creates
or uses the predictable branch `base/repo-baseline-<name>`, writes any missing
baseline files, commits only the baseline file set, pushes the branch to
`origin`, and opens a GitHub pull request against the repository default branch.
This path is for reviewable file changes only; it does not create the GitHub
repository or change repository settings and labels. Run `basectl repo
configure` separately when GitHub-side configuration should be applied.

Check the local baseline:

```bash
basectl repo check ~/work/base-demo
```

Seed optional repo-local agent guidance:

```bash
basectl repo agent-guidance ~/work/base-demo --repo-name base-demo
```

Reapply GitHub-side repository settings and labels:

```bash
basectl repo configure ~/work/base-demo --repo codeforester/base-demo
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
<login>` to override the owner, `--project-schema base-roadmap` to select the
schema, and repeat `--initiative-option <name>` to seed repository-specific
Initiative values. If `.github/base-project.yml` exists, Base reads repo-owned
`Area` and `Initiative` options from that file and adds missing Project options
without deleting or renaming existing options.
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
    size: S
```

`areas` and `initiatives` are applied by `repo configure`. `issue_defaults` is
validated and reserved for issue intake automation; it does not set fields on
existing issues during Project configuration.

## Local Baseline

`repo init` creates these files when they do not already exist:

- `README.md`
- `VERSION`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `.github/pull_request_template.md`
- `LICENSE`
- `.gitignore`
- `base_manifest.yaml`
- `tests/validate.sh`
- `.github/workflows/tests.yml`

Existing files are left unchanged. This makes `repo init` useful both for a
fresh directory and for bringing a small existing repository up to Base's
minimum expectations.

The generated `base_manifest.yaml` declares the project name and a test command:

```yaml
schema_version: 1

project:
  name: base-demo

test:
  command: ./tests/validate.sh
```

The generated validation script checks for the required baseline files. It is
not a replacement for project tests; it is the seed contract that lets
`basectl test <project>` work immediately.

## Optional Agent Guidance

`repo agent-guidance` creates repo-local guidance files for agent-assisted
development when they do not already exist:

- `AGENTS.md`
- `skills.md`
- `.github/pull_request_template.md`

The command accepts `--repo-name <name>`, `--default-branch <name>`, and
`--validation-command <command>` so generated examples match the repository.
Defaults are inferred from the target path, `main`, and `./tests/validate.sh`.

Existing files are left unchanged. This keeps the guidance layer safe for repos
that already have their own instructions or pull request template.

Preview the files without writing them:

```bash
basectl repo agent-guidance ~/work/base-demo --repo-name base-demo --dry-run
```

Include the optional guidance files in local baseline checks only when the repo
has opted into this layer:

```bash
basectl repo check ~/work/base-demo --agent-guidance
```

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
branch deletion and non-fast-forward updates such as force pushes. It does not
require status checks, approval counts, CODEOWNERS, teams, or repository
secrets. Pass `--no-protect-default-branch` when a repository intentionally
skips this Base-managed ruleset.

GitHub rulesets are available for public repositories on GitHub Free and for
public and private repositories on GitHub Pro, Team, or Enterprise plans. When
GitHub reports that rulesets are unavailable for a private repository's plan,
`repo configure` leaves the supported settings and labels in place, logs a
warning, and skips default branch protection.

The Project metadata schema creates or updates single-select Project fields on
the repo Project:

- `Status`: `Triage`, `Backlog`, `Ready`, `In Progress`, `In Review`, `Done`
- `Priority`: `P0`, `P1`, `P2`, `P3`
- `Area`: `CLI`, `Setup`, `Workspace`, `Manifest`, `Runtime`, `Shell`,
  `Python`, `Docs`, `CI`, `Packaging`, `Security`, `Product`
- `Size`: `S`, `M`, `L`
- `Initiative`: `BanyanLabs Dogfood`, `Workspace Handling`, `pyproject/uv`,
  `v1.0 Readiness`, `Adoption Polish`, plus values passed with
  `--initiative-option`

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

The default branch protection policy does not manage required status checks,
approval counts, repository secrets, teams, CODEOWNERS, or Base-specific PR
sections such as `Demo Impact`. The optional agent guidance baseline also does
not install Superpowers, manage `~/.codex/config.toml`, or vendor third-party
methodology files. Those are separate workflow and policy decisions. Base can
grow those capabilities once the baseline command has proven useful for real
repos such as the Base demo project.
