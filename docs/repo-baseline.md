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

`repo init` creates the local files and then configures the GitHub repository
when `--repo <owner/name>` is provided or an existing `origin` remote can be
inferred. That keeps the common new-repo path to one command. Use
`--no-configure` when the GitHub repo does not exist yet or when local-only
initialization is desired.

Without `--path`, `repo init` creates the repository under the configured
workspace root:

1. `workspace.root` from `~/.base.d/config.yaml` when configured.
2. The parent directory of `BASE_HOME` when no workspace root is configured.

That keeps `repo init base-demo` stable even when it is run from inside another
repository or from a nested directory such as `~/work/base/docs`. Use
`--path <path>` when the new repository should live somewhere else.

Check the local baseline:

```bash
basectl repo check ~/work/base-demo
```

Reapply GitHub-side repository settings and labels:

```bash
basectl repo configure ~/work/base-demo --repo codeforester/base-demo
```

`repo configure` is idempotent and safe to rerun when repository settings drift.
Use `--dry-run` on `repo init` or `repo configure` to print the planned file and
GitHub changes without applying them.

## Local Baseline

`repo init` creates these files when they do not already exist:

- `README.md`
- `VERSION`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
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

## GitHub Configuration

`repo init` and `repo configure` standardize the current GitHub repository
policy:

- Issues enabled
- Projects enabled
- squash merge enabled
- merge commits disabled
- rebase merge disabled
- delete branch on merge enabled
- squash commit message set to PR title and description

They also create or update these labels:

- `bug`
- `enhancement`
- `documentation`
- `ci`
- `security`
- `needs-demo`

In apply mode, GitHub configuration requires the GitHub CLI and an authenticated
session:

```bash
gh auth login -h github.com
```

Dry-run mode does not require authentication because it only prints the planned
`gh` commands.

## Boundaries

The MVP does not create the remote GitHub repository, configure branch
protection, manage repository secrets, create teams, or add CODEOWNERS. Those
are separate workflow and policy decisions. Base can grow those capabilities
once the baseline command has proven useful for real repos such as the Base demo
project.
