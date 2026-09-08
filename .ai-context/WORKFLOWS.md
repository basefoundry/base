# Base Workflow Context

## Pre-Edit Workflow Gate

Before modifying Base files, follow the canonical [pre-edit workflow
gate](../docs/github-workflow.md#pre-edit-workflow-gate). It distinguishes
issue-backed implementation from read-only investigation, design discussion,
and explicitly local-only work; implementation begins in an issue-backed
worktree rather than on `main`.

## Issue-First Work

Base uses GitHub Issues as the public product backlog. Use the canonical
[GitHub Workflow](../docs/github-workflow.md) for issue labels, assignment,
repo-named Project metadata and status, readiness, API-budget safeguards, and
repository workflow configuration. Keep this file focused on AI-context-specific
guidance, including agent-ready repo baselines, and link there instead of
copying those rules.

Project Intake prefers the standard `gh project` path, then uses the REST
Projects API when GraphQL quota exhaustion or owner resolution makes that path
unavailable. Both transports preserve existing non-empty planning fields and
must verify Status, Priority, Size, Area, and Initiative before success.

## Branch And Worktree Flow

Use the canonical [branch and worktree
flow](../docs/github-workflow.md#worktrees) for branch naming, worktree
location, review lifetime, and cleanup. This context file does not repeat
those repository-wide rules.

## Pull Requests

Pull requests are issue-backed by default and scoped to one issue. Follow the
canonical [GitHub Workflow](../docs/github-workflow.md) for PR creation,
required body sections, metadata, and issue/Project tracking. Keep this file's
AI-context-specific guidance separate from that repository-wide policy.

When a replacement PR supersedes another, follow the canonical [superseded PR
closure procedure](../docs/github-workflow.md#superseded-pull-requests).

## Validation

Prefer the narrowest check that proves the change, then broaden when shared
behavior is touched.

The `Tests` workflow validates pull requests and pushes to `main`; it does not
run a duplicate push workflow for feature branches. Its concurrency group uses
the pull-request number, or the Git ref for default-branch runs, so superseded
commits cancel without affecting unrelated pull requests.

Every `base-bash-libs` checkout in that workflow uses one immutable GA revision.
The workflow contract test guards against an RC or mixed dependency pin
returning across the platform and source-checkout jobs.

The `Security scanners` job is a required merge check. In addition to Bandit,
pip-audit, and ShellCheck, it runs the checksum-pinned Gitleaks release through
`tests/scan-secrets.sh`; findings are fully redacted. GitHub secret scanning and
provider push protection are the repository-native first layer, while Gitleaks
covers generic patterns unavailable through this repository's GitHub plan.

First-mile Homebrew installation remains mutable by default and logs that
policy. Managed environments can opt into checksum verification with paired
installer URL and SHA-256 overrides; the bootstrap documentation records why
Base does not hard-code a checksum for Homebrew's independently changing
`HEAD` installer.

Common commands:

```bash
git diff --check
basectl test base
```

Python tests run with:

```bash
BASE_CLI_SOURCE_DIR=../base-cli/lib/python \
PYTHONPATH=../base-cli/lib/python:lib/python:cli/python \
python -m pytest
```

Python CI also enables branch coverage, writes `coverage.json`, and runs
`python -m tests.coverage_gate coverage.json`. The gate keeps separate 85%
statement, 76% branch, and 84% combined floors; see
[`docs/testing.md`](../docs/testing.md) for the reproducible command and Bash
coverage policy.

The shared `base_cli` framework is maintained in the standalone `base-cli`
repository. Source-checkout tests resolve it from `BASE_CLI_SOURCE_DIR`, a
sibling `../base-cli/lib/python` checkout, or the installed `base-cli`
development dependency; Base no longer provides an in-tree copy.

The scheduled/manual `Base Demo E2E` workflow runs the macOS setup, check, test,
and non-interactive demo loop against the external `basefoundry/base-demo`
repository. Keep its failure ownership visible: `Base bug` covers Base
dispatch/runtime failures, while `base-demo manifest needs updating` covers
manifest, artifact, or declared-command drift.

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

Base releases are explicit ceremonies. Ordinary PRs do not update `VERSION` or
`DEVELOPMENT_VERSION`. `VERSION` is the latest published release, while
`DEVELOPMENT_VERSION` names the next development line used by untagged source
checkouts. Release-prep PRs update `VERSION`, README release text, and
`CHANGELOG.md`; after publication, advance `DEVELOPMENT_VERSION` for the next
development line.

Repositories that publish versioned artifacts can opt into the shared release
contract with `basectl repo configure --release --repo <owner/name>`. The
command adds missing release metadata and an agent-facing
`docs/release-process.md` guide without overwriting repository-specific
release declarations or instructions. Use `basectl repo check --release` to
verify adoption before starting release preparation.

The `basectl release check|plan|notes` commands are read-only inspection
commands. `basectl release publish` is guarded and creates the annotated tag and
GitHub Release after checks pass. The Homebrew tap update happens in
`basefoundry/homebrew-base` after the Base tag and GitHub Release exist.
Coordinated ecosystem releases additionally pass `--bom <path>` to `release
check` and `release publish`. The BOM is the authoritative cross-repository
attestation: required rows must use immutable commits and report passing
evidence, while moving-source rows are advisory and non-blocking. Validate and
fingerprint a record with `bin/base-release-bom`; attach the BOM and digest to
the resulting release evidence.
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

Project-originated IDE app, extension, and global user-setting mutations are a
separate setup consent boundary. `basectl setup --dry-run` must be reviewed,
and applying the plan requires `--allow-project-ide-mutations`; `--yes` alone
does not authorize it. Manifest command trust remains bound to the
`base_manifest.yaml` SHA-256 only, so status and execution guidance warns that
referenced scripts, direct executable files, Git HEAD, and uncommitted working
tree changes are not independently verified or invalidating inputs.

## AI Context Maintenance

Every meaningful PR should evaluate whether `.ai-context/` needs an update.
Expected updates include command changes, architecture changes, workflow
changes, manifest schema changes, release/status changes, and durable product
decisions.
