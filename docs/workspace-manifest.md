# Workspace Manifest

Base uses "workspace" in a precise way: a workspace is a local directory that
contains sibling repositories. A workspace manifest is an optional local file
that describes which repositories are expected to belong to that workspace.

Workspace status, check, doctor, and clone commands can use a manifest when the
user configures `workspace.manifest` in `~/.base.d/config.yaml` or supplies
`--manifest <path>`. The command-line flag takes precedence over the configured
manifest. Without either source, status, check, and doctor keep their
discovered-project behavior, while `basectl workspace clone` reports that a
manifest is required.

Teams can also configure `workspace.manifest_source` and refresh the local
manifest explicitly with `basectl workspace pull`. Pull supports local paths,
`file://` URLs, and raw `https://` file URLs. It rejects cleartext `http://`
sources by default, validates fetched content before writing, and does not
mutate project repositories.

## Vocabulary

`workspace.root` is a machine-local setting in `~/.base.d/config.yaml`. It tells
Base where to scan for repositories:

```yaml
workspace:
  root: ~/work
  manifest: ~/work/base-workspace/workspace.yaml
  manifest_source: https://raw.githubusercontent.com/example/platform/main/workspace.yaml
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

`basectl workspace status` reads the latest project check record from
`~/.base.d/<project>/checks/last.json` when it exists. Text output shows the
check date in the `LAST CHECK` column, while JSON output includes the full
timestamp and check status. Projects without a recorded check show `-` in text
output and `null` in JSON output.

With `--manifest <path>`, the same commands also report expected repositories,
missing required and optional repositories, and discovered Base-managed
projects outside the manifest.

`basectl workspace clone --manifest <path>` uses the expected repository list
as an explicit clone plan. It clones missing required repositories by default,
reports missing optional repositories without cloning them, and includes
optional repositories only with `--include-optional`. Existing repositories are
checked through `basectl repo clone` so matching checkouts are treated as
already satisfied and conflicts stay visible.

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
- what clone URL and default branch should be shown or used by explicit clone
  commands

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
    url: git@github.com:basefoundry/base.git
    default_branch: main
    required: true

  - name: bankbuddy
    url: git@github.com:codeforester/bankbuddy.git
    default_branch: main
    required: false

  - name: banyanlabs
    url: git@github.com:basefoundry/banyanlabs.git
    default_branch: main
    required: true
```

`schema_version` is required. Versioning the contract early lets future Base
versions reject unsupported workspace manifest shapes with clear upgrade
guidance.

`workspace.name` is a human-facing name for reports and onboarding output.

`repos[].name` is the local directory name under the workspace root and the
stable identifier used in reports.

`repos[].url` is optional v1 metadata for a Git clone URL. The
`basectl workspace clone` command supports HTTPS, SSH, Git protocol,
SCP-style SSH, `file://`, and absolute local path repository sources. It
otherwise falls back to `repos[].name` when no URL is provided. Cleartext
`http://` repository URLs are rejected by default. Base does not parse
credentials or manage authentication.

`repos[].default_branch` is advisory metadata for reports and future clone
validation. It should default to the remote's default branch when omitted, but
implementation should avoid network calls unless the command explicitly needs
them.

`repos[].required` defaults to `true`. Optional repositories should appear in
status reports without failing the whole workspace when they are absent.

## Location And Sources

The v1 implementation supports an explicit local file:

```bash
basectl workspace status --manifest ~/work/workspace.yaml
```

The manifest should live outside individual project repositories unless a team
intentionally keeps it in a dedicated workspace-config repository. A local file
keeps the trust model simple: Base reads only a path the user named.

Teams can also configure a canonical manifest source in
`workspace.manifest_source` and refresh the local manifest with the explicit
`basectl workspace pull` command. Pull supports local paths, `file://` URLs,
and raw `https://` file URLs; cleartext `http://` sources are rejected by
default. Remote source fetching is therefore an explicit manifest-file update,
not passive workspace discovery, and it does not clone, pull, reset, or rewrite
project repositories.

### Accepted Source Formats

`workspace.manifest_source` accepts these source shapes:

```yaml
workspace:
  manifest_source: file:///Users/alex/work/platform/workspace.yaml
```

```yaml
workspace:
  manifest_source: https://raw.githubusercontent.com/example/platform/main/workspace.yaml
```

```yaml
workspace:
  manifest_source: ~/work/platform/workspace.yaml
```

```yaml
workspace:
  manifest_source: /opt/base/workspaces/platform.yaml
```

Use Git SSH clone URLs such as `git@github.com:example/service.git` only in
workspace manifest `repos[].url` entries. They identify repositories to clone;
they are not workspace manifest source URLs.

## Trust And Authentication

Base should delegate repository authentication to Git, SSH, and the GitHub CLI.
It should not store, read, print, or manage credentials.

Remote workspace manifest sources should use HTTPS. Cleartext HTTP is rejected
by default because a workspace manifest controls expected repositories and
clone plans. If a future internal workflow proves that insecure transport is
needed, it should use an explicit opt-in rather than making HTTP ordinary
configuration.

Workspace manifest validation may check that clone URLs are syntactically
present. Network reachability, SSH key readiness, and GitHub authentication
belong in explicit check or doctor behavior, not in passive parsing.

## Existing Repositories

When a repository already exists at the expected local path, Base should leave
its files alone by default.

`basectl workspace clone` delegates existing repositories to `basectl repo clone`,
which treats matching checkouts as already satisfied and reports
conflicting origins as errors. Future mutating commands such as update need
their own dry-run output and confirmation rules. A workspace manifest must not
imply that Base can overwrite, pull, reset, or otherwise mutate existing
checkouts.

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

With `workspace.manifest` configured, those commands add expected-repo
awareness. `--manifest <path>` does the same for a single command and overrides
the configured manifest:

```bash
basectl workspace status --manifest ~/work/workspace.yaml
basectl workspace check --manifest ~/work/workspace.yaml
basectl workspace doctor --manifest ~/work/workspace.yaml
```

Without a configured manifest or `--manifest`, commands report discovered local
projects only.

To refresh a configured local manifest from a canonical source:

```bash
basectl workspace pull --dry-run
basectl workspace pull
```

For a one-off source or destination override:

```bash
basectl workspace pull \
  --source https://raw.githubusercontent.com/example/platform/main/workspace.yaml \
  --manifest ~/work/base-workspace/workspace.yaml \
  --dry-run
```

With a configured or explicit manifest, commands report both expected
repositories and discovered projects, including missing expected repositories
and extra discovered projects.

The init path bootstraps a workspace from a workspace configuration repository:

```bash
basectl workspace init basefoundry/base-workspace --dry-run
basectl workspace init basefoundry/base-workspace
basectl workspace init base-workspace --owner basefoundry --path ~/work/base-workspace
```

The positional argument is a workspace source, not the workspace name. The
source can be a local path, a GitHub URL, `owner/repo`, or a short repository
name resolved by `--owner <owner>` or `github.default_owner`. `--path` controls
where the workspace configuration repository is checked out or read.
`--workspace` controls where member repositories are cloned. If neither
`--workspace` nor configured `workspace.root` is available, init uses the parent
of the workspace configuration repo path as the workspace root.

Init validates the workspace manifest before cloning member repositories. When
the workspace source is remote, init first delegates the workspace configuration
repo checkout to `basectl repo clone`, then delegates member repository
materialization to `basectl workspace clone`. A remote dry-run can stop after the
configuration repo clone plan when the local manifest is not available yet.

The clone path requires a manifest from either config or the command line:

```bash
basectl workspace clone --manifest ~/work/workspace.yaml --dry-run
basectl workspace clone --manifest ~/work/workspace.yaml
basectl workspace clone --manifest ~/work/workspace.yaml --include-optional
basectl workspace clone --dry-run
```

By default it clones missing required repositories and skips missing optional
repositories. `--dry-run` forwards to each delegated `basectl repo clone`
operation so the resolved repository specs, destinations, and conflicts can be
reviewed before the filesystem changes.

The configure path applies the existing single-repo repair behavior across the
workspace:

```bash
basectl workspace configure --dry-run
basectl workspace configure
basectl workspace configure --manifest ~/work/workspace.yaml --dry-run
```

Without a manifest, Base scans discovered local Base-managed projects under the
workspace root and delegates each supported GitHub checkout to
`basectl repo configure <path> --repo <owner/name>`. With a manifest, Base walks
the expected repository set, skips missing or non-Base-managed repositories, and
uses the manifest URL when it identifies a GitHub repository. The command
continues after per-repo failures and reports configured, skipped, and failed
counts. Use this after shared repo or Project schema changes when each local
repo should receive the same idempotent `repo configure` repair path.

## Relationship To Onboarding

`basectl onboard` currently guides first-run Base setup. It should not become a
project-specific installer.

A future workspace onboarding command can build on this manifest and the
explicit clone path. It should still keep project artifact setup separate from
repository checkout and retain explicit confirmation and dry-run behavior.

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

With `--format json`, workspace status includes `python_runtime` for each
ready, inspectable Base-managed project environment. The object reports the
environment manager, virtualenv path, interpreter path, and actual Python minor
version so users can quickly compare project runtimes across a workspace.

`basectl workspace check --manifest <path>` and
`basectl workspace doctor --manifest <path>` include normal project diagnostics
for present Base-managed projects. They also emit stable workspace findings for
repository presence, outside-manifest discovered projects, and present
repositories without a Base project manifest.

`basectl workspace clone --manifest <path>` clones or validates expected
repositories through `basectl repo clone`. It clones missing required
repositories by default, skips missing optional repositories unless
`--include-optional` is supplied, and exits nonzero when any delegated clone or
checkout validation fails.

`basectl workspace configure --manifest <path>` configures present Base-managed
expected repositories through `basectl repo configure`. It skips missing
repositories and present repositories without `base_manifest.yaml`, and exits
nonzero only when a delegated configure command fails.

The v1 implementation is intentionally still conservative. Clone is explicit;
configure is explicit; update, pull, reset, project setup, and authentication
management remain outside the workspace manifest contract.
