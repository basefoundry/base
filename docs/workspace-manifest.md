# Workspace Manifest

Base uses "workspace" in a precise way: a workspace is a local directory that
contains sibling repositories. A workspace manifest is an optional local file
that describes which repositories are expected to belong to that workspace.

Read-only workspace commands can use a manifest when the user supplies
`--manifest <path>`. Without that flag, workspace commands keep their
discovered-project behavior.

## Vocabulary

`workspace.root` is a machine-local setting in `~/.base.d/config.yaml`. It tells
Base where to scan for repositories:

```yaml
workspace:
  root: ~/work
```

A discovered repository is a direct child of the workspace root. Base scans
only direct children by default.

A Base-managed project is a discovered repository with a `base_manifest.yaml`.
The project manifest remains the source of truth for that repository's setup,
activation, commands, tests, demo, IDE requirements, and health declarations.

A workspace manifest is a team-shared contract that lists repositories that
should exist in a workspace. It answers "which repos belong together?", not
"how does each repo set itself up?"

An expected repository is listed in the workspace manifest. It may or may not
exist locally yet.

A discovered project exists locally and has `base_manifest.yaml`. It may or may
not be listed in a workspace manifest.

## Current Behavior

Workspace commands operate on discovered local repositories when no manifest is
supplied:

```bash
basectl projects list
basectl workspace status
basectl workspace check
basectl workspace doctor
```

With `--manifest <path>`, the same commands also report expected repositories,
missing required and optional repositories, and discovered Base-managed
projects outside the manifest.

## Design Goal

The workspace manifest should make team onboarding inspectable and repeatable
without turning Base into a secrets manager, Git credential manager, repo sync
tool, or project-specific installer.

It should let Base answer:

- which repositories are expected in this workspace
- which expected repositories are already present
- which expected repositories are missing
- which discovered repositories are outside the expected set
- which repositories are required versus optional
- what clone URL and default branch should be shown or used later

Each repository still owns its own `base_manifest.yaml`. The workspace manifest
must not duplicate project setup, test, run, activation, demo, or health
contracts.

## Manifest Shape

```yaml
schema_version: 1

workspace:
  name: banyanlabs

repos:
  - name: base
    url: git@github.com:codeforester/base.git
    default_branch: master
    required: true

  - name: bankbuddy
    url: git@github.com:codeforester/bankbuddy.git
    default_branch: main
    required: false

  - name: banyanlabs
    url: git@github.com:codeforester/banyanlabs.git
    default_branch: main
    required: true
```

`schema_version` is required. Versioning the contract early lets future Base
versions reject unsupported workspace manifest shapes with clear upgrade
guidance.

`workspace.name` is a human-facing name for reports and onboarding output.

`repos[].name` is the local directory name under the workspace root and the
stable identifier used in reports.

`repos[].url` is optional v1 report metadata for a Git clone URL. Base may pass
it to Git when clone support exists later; Base should not parse credentials or
manage authentication.

`repos[].default_branch` is advisory metadata for reports and future clone
validation. It should default to the remote's default branch when omitted, but
implementation should avoid network calls unless the command explicitly needs
them.

`repos[].required` defaults to `true`. Optional repositories should appear in
status reports without failing the whole workspace when they are absent.

## Location

The v1 implementation supports an explicit local file:

```bash
basectl workspace status --manifest ~/work/workspace.yaml
```

The manifest should live outside individual project repositories unless a team
intentionally keeps it in a dedicated workspace-config repository. A local file
keeps the trust model simple: Base reads only a path the user named.

URL support should be deferred. Fetching remote manifests creates questions
about caching, trust, authentication, redirects, and offline behavior. A
project-owned or team-owned installer can fetch a manifest and then hand Base a
local path when that workflow is needed.

## Trust And Authentication

Base should delegate repository authentication to Git, SSH, and the GitHub CLI.
It should not store, read, print, or manage credentials.

Workspace manifest validation may check that clone URLs are syntactically
present. Network reachability, SSH key readiness, and GitHub authentication
belong in explicit check or doctor behavior, not in passive parsing.

## Existing Repositories

When a repository already exists at the expected local path, Base should leave
it alone by default.

Future mutating commands may offer explicit actions such as clone or update,
but they need their own dry-run output and confirmation rules. A workspace
manifest must not imply that Base can overwrite, pull, reset, or otherwise
mutate existing checkouts.

## Partial Failure

Workspace commands should treat partial failure as normal. A missing optional
repo, invalid project manifest, broken virtual environment, or Git diagnostic
failure should be represented as an item in the workspace report instead of
making the entire scan useless.

Suggested report states:

- `ok`: required local state is present and healthy
- `warn`: optional or recoverable issue
- `error`: required state is missing or invalid
- `unknown`: Base cannot determine state without a command it has not run

Command exit status should be nonzero when any required item has an `error`.
Warnings should not fail automation by default.

## Relationship To Workspace Commands

The first read-only workspace commands should continue to work without a
workspace manifest:

```bash
basectl workspace status
basectl workspace check
basectl workspace doctor
```

Once manifest support is implemented, the manifest should add expected-repo
awareness:

```bash
basectl workspace status --manifest ~/work/workspace.yaml
basectl workspace check --manifest ~/work/workspace.yaml
basectl workspace doctor --manifest ~/work/workspace.yaml
```

Without `--manifest`, commands report discovered local projects only.

With `--manifest`, commands report both expected repositories and discovered
projects, including missing expected repositories and extra discovered projects.

## Relationship To Onboarding

`basectl onboard` currently guides first-run Base setup. It should not become a
project-specific installer.

A future workspace onboarding command can build on this manifest only after the
read-only manifest reporting model is stable. That future command would need
explicit confirmation and dry-run behavior for cloning missing repositories and
setting up project artifacts.

## Non-Goals

The workspace manifest should not:

- replace `base_manifest.yaml`
- duplicate per-project setup, commands, tests, demos, or health checks
- manage secrets, SSH keys, tokens, or GitHub authentication
- silently clone, pull, reset, or overwrite repositories
- assume all repositories use Base
- require every repository in the workspace to share one language stack
- introduce nested project discovery or manifest inheritance

## V1 Runtime Behavior

`basectl workspace status --manifest <path>` reports one row per expected
repository, plus discovered Base-managed projects that are outside the manifest.
Missing required repositories are errors. Missing optional repositories are
warnings. Present repositories without `base_manifest.yaml` are allowed and
reported with project diagnostics skipped.

`basectl workspace check --manifest <path>` and
`basectl workspace doctor --manifest <path>` include normal project diagnostics
for present Base-managed projects. They also emit stable workspace findings for
repository presence, outside-manifest discovered projects, and present
repositories without a Base project manifest.

The read-only v1 implementation is intentionally the foundation for future
clone/onboard behavior. Explicit clone or update commands should be designed
only after this reporting model proves useful.
