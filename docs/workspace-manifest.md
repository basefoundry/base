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
"how does each repository prepare itself?"

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
`~/.base.d/<project>/checks/last.json` when it exists. Records are written by
`basectl check <project>` and `basectl workspace check`. Text output shows the
check date in the `LAST CHECK` column, while JSON output includes the full
timestamp and check status. Projects without a recorded check show `-` in text
output and `null` in JSON output.

JSON status output includes a top-level `status` aggregate in addition to each
project's status. It uses the same status vocabulary and precedence as workspace
reports: `error` takes precedence over `warn`, which takes precedence over `ok`.
An empty workspace has aggregate status `ok`.

```json
{
  "workspace": "/Users/example/work",
  "status": "warn",
  "project_count": 2,
  "projects": [
    {"name": "base", "status": "ok"},
    {"name": "demo", "status": "warn"}
  ]
}
```

The latest-check record is optional persistence state. If a check succeeds but
cannot save that record, the check result remains authoritative and workspace
status reports the missing record as `-` or `null` until a later check can save
one. Text output emits one warning per affected project with the record path;
JSON and YAML expose the same details in the top-level `record_warnings`
collection. Persistence warnings do not change the workspace health status or
command exit code.

With `--manifest <path>`, the same commands also report expected repositories,
missing required and optional repositories, and discovered Base-managed
projects outside the manifest.

`basectl workspace onboarding --manifest <path>` is the first-day summary for a
new teammate. It reads the same manifest and local repository state, then shows
each expected repository, the expected local path, whether it is present,
whether Base can read `base_manifest.yaml`, and the next action. JSON output is
available for onboarding scripts or docs generators:

```bash
basectl workspace onboarding --manifest ~/work/base-workspace/workspace.yaml
basectl workspace onboarding --manifest ~/work/base-workspace/workspace.yaml --format json
```

The onboarding report is read-only. It prints clone commands for missing
repositories when the manifest provides `repos[].url`, and it prints the
standard Base setup and validation commands for repositories with valid project
manifests. It does not clone repositories, run setup, create virtual
environments, or execute project tests.

`basectl workspace agent-brief --manifest <path>` is the local handoff summary
for a human or coding agent. It includes every expected repository plus
discovered Base-managed projects outside the manifest, and supports the same
text or stable JSON output choice:

```bash
basectl workspace agent-brief --manifest ~/work/base-workspace/workspace.yaml
basectl workspace agent-brief --manifest ~/work/base-workspace/workspace.yaml --format json
```

The brief reports the Base repository baseline and agent-guidance file
contracts, `.ai-context` Markdown availability, project environment state, and
an inferred validation path. The generated repository baseline uses an
executable `tests/validate.sh`; Base's own manifest-declared
`test.command: ./bin/base-test` is used for the Base repository instead. When
only a manifest-declared test is available, its execution stays behind a
recommended `basectl test` so Base retains runner, trust, and environment
ownership. The brief never executes those commands. It does not use GitHub,
generate guidance or context files, clone repositories, or change setup state.

`basectl workspace clone --manifest <path>` uses the expected repository list
as an explicit clone plan. It clones missing required GitHub repositories by
default, reports missing optional repositories without cloning them, and
includes optional repositories only with `--include-optional`. The current
materialization path delegates to `basectl repo clone`, so GitLab, Bitbucket,
internal Git, and local repository URLs are accepted as manifest metadata for
read-only reports but are not automatically cloned by this command today. Clone
non-GitHub repositories with ordinary Git first, then let Base discover the
local checkout.

## Design Goal

The workspace manifest should make team onboarding inspectable and repeatable
without turning Base into a secrets manager, Git credential manager, repo sync
tool, or project-specific installer.

It should let Base answer:

- which repositories are expected in this workspace
- which expected repositories are already present
- which expected repositories are missing
- what a new teammate should do next for each expected repository
- which discovered repositories are outside the expected set
- which repositories are required versus optional
- which local repositories have baseline, agent-guidance, context, and
  validation evidence for an agent handoff
- what clone URL and default branch should be shown in reports, and what
  GitHub clone target should be used by explicit clone commands

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

`repos[].url` is optional v1 metadata for a Git clone URL. Manifest validation
accepts HTTPS, SSH, Git protocol, SCP-style SSH, `file://`, and absolute local
path repository sources so workspace reports can describe GitHub, GitLab,
Bitbucket, internal Git, and local repositories. Cleartext `http://`
repository URLs, embedded URL credentials, and secret-shaped query or fragment
parameters are rejected before any report or clone plan is rendered. Keep
credentials in Git credential helpers or SSH configuration; Base does not
parse credentials or manage authentication.

The current `basectl workspace clone` implementation only materializes GitHub
repositories because it delegates to `basectl repo clone`. Non-GitHub URLs
remain useful metadata for status, check, and doctor output, but users should
clone those repositories with ordinary Git until Base grows provider-specific
clone support.

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
default. Local file URLs percent-decode the path exactly once, accept only an
empty or `localhost` authority, and reject malformed escapes or remote
authorities. Remote source fetching is therefore an explicit manifest-file
update, not passive workspace discovery, and it does not clone, pull, reset, or
rewrite project repositories.

### Update Existing Checkouts

Use `basectl workspace update` when the repositories are already materialized
and you want one Git update across the workspace:

```bash
basectl workspace update --dry-run
basectl workspace update
basectl workspace update --workspace ~/workspace --manifest ~/workspace/base-workspace/workspace.yaml
```

Update walks the manifest in order and runs `git pull --ff-only` in each
present repository. It continues after individual failures and reports
updated, unchanged, skipped, and failed counts. Missing optional repositories
are skipped; missing required repositories are failures. The command never
clones, resets, force-updates, or refreshes the manifest. When the manifest's
`base` path is the active `BASE_HOME` checkout, it is skipped to protect the
control plane. A separate workspace checkout of `base` is updated normally.
Text output is rendered as one repository/action/result table; raw Git output
is retained for debug diagnostics, while failures include concise repository
context and exit details in the report. Use `workspace pull` separately when
the manifest file itself must be refreshed from `workspace.manifest_source`.

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

Base should delegate repository authentication to Git and SSH. GitHub-specific
commands also delegate to the GitHub CLI. Base should not store, read, print,
or manage credentials.

Remote workspace manifest sources should use HTTPS. Cleartext HTTP is rejected
by default because a workspace manifest controls expected repositories and
clone plans. If a future internal workflow proves that insecure transport is
needed, it should use an explicit opt-in rather than making HTTP ordinary
configuration.

Workspace manifest validation may check that clone URLs are syntactically
present. Network reachability, SSH key readiness, and forge authentication
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

The first workspace inspection commands should continue to work without a
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
source can be a local path or local `file://` URL, a GitHub URL, `owner/repo`,
or a short repository name resolved by `--owner <owner>` or
`github.default_owner`. Init uses the same one-time percent decoding and
empty-or-`localhost` authority policy as workspace pull. `--path` controls where
the workspace configuration repository is checked out or read.
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

The configure path exposes the existing single-repo repair behavior across the
workspace:

```bash
basectl workspace configure
basectl workspace configure --apply
basectl workspace configure --apply --yes
basectl workspace configure --manifest ~/work/workspace.yaml --dry-run
```

`workspace configure` is a dry-run by default. Use `--apply` to authorize
changes; an interactive run asks for confirmation after printing the affected
repositories. Use `--apply --yes` for a reviewed non-interactive run. `--yes`
without `--apply` is rejected and never authorizes changes. The explicit
`--dry-run` form remains supported as an alias for the default behavior.

Without a manifest, Base scans discovered local Base-managed projects under the
workspace root and delegates each supported GitHub checkout to
`basectl repo configure <path> --repo <owner/name>`. With a manifest, Base walks
the expected repository set, skips missing or non-Base-managed repositories, and
uses the manifest URL when it identifies a GitHub repository. The command
continues after per-repo failures and reports configured, skipped, and failed
counts. Use this after shared repo or Project schema changes when each local
repo should receive the same idempotent `repo configure` repair path.

The setup path prepares existing project checkouts from the manifest:

```bash
basectl workspace setup --dry-run
basectl workspace setup
basectl workspace setup --manifest ~/work/workspace.yaml --yes
```

Setup walks repositories in manifest order. The active `base` checkout is
reported and skipped because it is the control plane; missing checkouts and
repositories without a valid Base manifest are also skipped from execution.
Each eligible repository is delegated to its local `basectl setup --manifest
<path> <project>` command. `--yes` forwards confirmation to those commands.
The command continues after per-repository failures and reports setup,
skipped, and failed counts. Required missing checkouts and invalid required
manifests count as failures, including in dry-run mode, so a dry-run can be
used to validate the expected workspace before applying changes.

## Relationship To Onboarding And Agent Handoff

`basectl onboard` guides first-run Base setup. It should not become a
project-specific installer.

`basectl workspace onboarding` now builds a read-only first-day summary from
the workspace manifest. It reports expected repositories, local checkout state,
manifest state, and suggested next actions in text or JSON without cloning
repositories, running project setup, or executing manifest-declared commands.
That keeps project artifact setup, repository checkout, and command trust as
separate explicit concerns.

`basectl workspace agent-brief` is a separate report rather than an onboarding
mode because its readiness signals and JSON schema serve a different consumer.
A Base-managed repository is reported structurally ready for handoff only when
its manifest is valid, an executable interpreter file is present at its
expected project environment path, its Base baseline and agent-guidance file contracts are
complete, and a validation path is available. The interpreter state is
`present_unverified`: the brief does not execute it or any repository command.
The recommended repository check and validation still need to run separately
and may fail. `.ai-context` is reported but is not a hard requirement of the
existing `repo check --agent-ready` contract.

Missing expected repositories receive clone or materialization hints.
Present expected repositories without a Base manifest remain `unmanaged`; the
brief can report generic guidance, context, and validation evidence without
suggesting Base adoption. Base-managed repositories with an incomplete
contract receive ordered, non-mutating suggestions such as
`repo init --agent-ready`, `repo agent-guidance`, `repo check --agent-ready`,
setup, and validation. An incomplete baseline uses `repo init --agent-ready`
without a redundant separate guidance action.

This brief is workspace-scoped local evidence. The issue-oriented handoff
bundle tracked in #1562 remains separate and may compose issue, branch,
history, diagnostics, and exported context later.

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

For the canonical `python_runtime` field definition and JSON shape, see
[Python Manifest](python-manifest.md#workspace-status-python_runtime).

`basectl workspace check --manifest <path>` includes normal project diagnostics
for present Base-managed projects and renders check-oriented status, names, and
messages in text output. `basectl workspace doctor --manifest <path>` renders
the same read-only evidence as actionable findings with stable IDs and fix
guidance. Both commands emit stable workspace findings for repository
presence, outside-manifest discovered projects, and present repositories
without a Base project manifest; their JSON diagnostic items remain compatible.

`basectl workspace agent-brief --manifest <path>` reports one item per expected
repository plus each extra locally discovered Base-managed project. JSON uses
schema version `1` and stable nested signal keys for `baseline`,
`agent_guidance`, `ai_context`, and `validation`. The command exits successfully
when it can construct the brief; individual repository readiness is data, not a
workspace-command failure code.

The text table exposes the venv and validation states directly. In JSON schema
version `1`, the important state meanings are:

- `base_managed` is true when a present repository has a valid or invalid Base
  project manifest. It is false for missing and unmanaged repositories.
- `project` is the parsed Base project name for a valid manifest and `null` for
  missing, unmanaged, or invalid repositories.
- `venv: present_unverified` means the expected executable interpreter file
  exists. The brief never executes it. `missing`, `unknown`, and
  `not_applicable` represent the other local static states.
- `handoff_status` is one of `missing_required`, `missing_optional`,
  `unmanaged`, `needs_manifest_repair`, `needs_baseline`, `needs_setup`,
  `needs_agent_guidance`, or `ready`. `ready` is structural readiness from
  non-executing evidence, not proof that checks or tests pass.
- baseline status is `complete` or `incomplete` for Base-managed repositories,
  `not_applicable` for unmanaged repositories, and `unavailable` when the
  repository is missing.
- agent-guidance status is `complete` or `incomplete` for Base-managed
  repositories; generic unmanaged guidance uses `present`, `partial`, or
  `missing`; a missing repository uses `unavailable`.
- AI-context status is `present`, `missing`, `invalid`, or `unavailable`.
  Validation status is `available` or `unavailable`, with source
  `repo_baseline`, `manifest_test`, or `null`. Its `command` is the recommended,
  non-executed validation path, or `null` when unavailable.

The readiness fraction counts expected required repositories only; optional and
extra local repositories do not change the denominator. Manifest repository
URLs with embedded credentials or secret-shaped query or fragment parameters
are rejected without echoing the secret. Every report and suggested clone
action also applies the shared repository URL sanitizer defensively. Ordinary
`git@host:path` SSH URLs remain intact. When only a manifest-declared test
command supplies validation, the brief recommends `basectl test`; it does not
expose or execute the raw command.

`basectl workspace clone --manifest <path>` clones or validates expected
repositories through `basectl repo clone`. It clones missing required
repositories by default, skips missing optional repositories unless
`--include-optional` is supplied, and exits nonzero when any delegated clone or
checkout validation fails. Text output uses a stable repository/action/result
table: existing repositories are `present`, newly materialized repositories are
`cloned`, optional omissions are `skipped`, dry-run operations are `planned`,
and failures include concise details and exit codes. Successful delegated clone
output is suppressed in normal interactive mode, while the completion summary
reports aggregate present, cloned, skipped, and failed counts.
Timestamped delegated Base log records remain available in debug diagnostics
rather than being rendered as indented failure details.

`basectl workspace configure --manifest <path> --apply` configures present
Base-managed expected repositories through `basectl repo configure`. Without
`--apply`, it only previews the delegated calls. It skips missing repositories
and present repositories without `base_manifest.yaml`, and exits nonzero only
when a delegated configure command fails.

The v1 implementation is intentionally still conservative. Clone, update,
configure, and project setup are explicit; reset and authentication management
remain outside the workspace manifest contract.
