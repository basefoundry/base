# basectl Quick Reference

Status: maintained command reference
Last reviewed: 2026-07-25

This page is a compact lookup table for the current `basectl` command surface.
Run `basectl help <nested path>` or append `--help` to that path for the same
leaf-specific usage. Run `basectl --help` for the journey-oriented command map.

Use space-separated values for long options, for example `--format json`.
Base rejects `--option=value` syntax before command delegation. Arguments after
`--` belong to the delegated project command and may use that command's native
syntax.

For report commands documented with `text|csv|tsv|yaml|json`, an omitted
`--format` (or `--format text`) is a pretty table on a terminal and headerless
TSV when stdout is redirected. See [Output formats](output-formats.md) for
stable field order, JSON/YAML compatibility, stderr behavior, and the
command-specific exceptions.

`basectl` exposes `-v` as the public command-level debug switch. Direct
`base_cli` package standard options such as `--debug`, `--quiet`, `--log-file`,
`--config` and `--environment` are private to Python package execution and are
rejected by `basectl`. Use `basectl -x <command>` to enable Bash xtrace before
the command runs. Use `basectl --keep-temp <command>` when temporary run files
must be preserved for diagnosis; they are removed by default.

## Stability Tiers

Commands documented here are stable public CLI unless a focused feature
document explicitly marks the command, flag, output shape, or generated artifact
as experimental. Prefer documented `--format json` payloads for automation and
avoid scripting against human-readable tables, logs, or private `base_cli`
package options.

See [Base Stability Tiers](stability-tiers.md) for the full stable,
experimental, and internal support contract.
The four read-only control-plane payloads using the shared v1 envelope are
defined in [Inspection JSON](inspection-json.md).

## Source Control And Forge Boundary

Base assumes Git as the source-control system. Non-Git SCMs such as Mercurial,
Perforce, and Subversion are out of scope.

Base is GitHub-primary today. Local project commands work for non-GitHub Git
repositories once they are checked out locally and declare `base_manifest.yaml`.
Repository creation, cloning, configuration, issue, pull-request, Project, and
release automation are GitHub-specific unless a command explicitly says
otherwise. See
[Source Control And Forge Support](source-control-and-forge-support.md) for the
full compatibility contract.

## Install And Bootstrap

| Command | What it does | Important flags |
|---|---|---|
| `basectl setup [project]` | Install or reconcile Base and optional project artifacts. Project-originated IDE app, extension, and user-setting mutations require separate approval. | `--ci`, `--format <text\|json>`, `--profile <dev,sre,ai>`, `--dry-run`, `--manifest <path>`, `--allow-project-ide-mutations`, `--recreate-venv`, `--upgrade-pip`, `--notify`, `--no-notify` |
| `basectl update-profile` | Create, refresh, or remove Base-managed Bash and Zsh startup snippets, backing up existing dotfiles before changes. | `--defaults`, `--no-defaults`, `--remove`, `--dry-run` |
| `basectl update [project]` | Update a Base-managed project checkout through Git, or update Base through Homebrew when Base is Homebrew-managed, then run setup for the selected project. | `--dry-run` |
| `basectl onboard [project]` | Guide first-run setup through check, setup, shell profile, doctor, project discovery, and read-only manifest trust status. Defaults to `base`. | `--profile <list>`, `--dry-run`, `--yes`, `--allow-project-ide-mutations`, `--no-profile` |
| `basectl version` | Show the installed Base version. | none |

### Setup Profiles And Behavior

`basectl setup` deliberately pins its default Homebrew Python formula so setup is
reproducible across machines. The current default is `python@3.13`. Override it
with `BASE_SETUP_PYTHON_FORMULA` when a workspace needs a different formula.
After this Bash bootstrap layer creates Base's own Python environment, setup
installs Base bootstrap Python packages into that environment. Shell-only
project reconciliation runs from that Base runtime and does not copy those
packages into a project venv. Projects that explicitly declare `python:` or a
`python-package` artifact keep the project-runtime path: Base first seeds the
target project venv with `bootstrap: true` default artifacts and then invokes
the Python project setup layer through `base-wrapper --project <project>`.
Prerequisite profiles are opt-in. Use `--profile dev` to install Base
contributor tools from `lib/base/dev_manifest.yaml`. On macOS that includes
Homebrew-managed BATS, GitHub CLI, and ShellCheck. On Ubuntu/Debian it installs
Base-owned apt-backed tools such as BATS and ShellCheck. It installs GitHub CLI
from GitHub CLI's official Debian/Ubuntu apt repository/keyring instead of the
default distro package; authentication remains user-owned. Use `--profile sre`
for the initial site-reliability profile in
`lib/base/sre_manifest.yaml`, which installs local diagnostic tools such as
`kubectl`, `helm`, `k9s`, `httpie`, `grpcurl`, `jq`, `yq`, `nmap`, and `mtr`.
Use `--profile ai` for optional AI coding tools: Codex CLI and Claude Code.
Use `--profile linux-lab` on a macOS host to install and check Multipass for
local Ubuntu lab VMs. Profiles compose with a comma-separated list.

```bash
basectl setup --profile dev
basectl setup --profile sre
basectl setup --profile ai
basectl setup --profile linux-lab --dry-run
basectl setup --profile linux-lab
basectl setup --profile dev,sre
basectl setup --profile dev,ai
basectl setup --profile dev,linux-lab
basectl check --profile sre
basectl check --profile ai
basectl check --profile linux-lab
basectl doctor --profile sre
basectl doctor --profile ai
basectl doctor --profile linux-lab
```

AI coding tools are intentionally not part of the plain `dev` or `sre` profile.
`basectl setup --profile ai` uses official remote installers only when that
profile is explicitly requested. Base checks tool presence and version output,
but it does not manage accounts, credentials, model access, or organization
policy.

The `linux-lab` profile is intentionally host-scoped. It installs or checks the
Multipass CLI on macOS through `brew install --cask multipass`, but Base does
not create, start, mount, or delete Multipass instances during setup. Review
the planned install with `--dry-run`, then create lab VMs with
`multipass launch` when you are ready.

For the complete Homebrew, Codex CLI, Claude Code, uv, and mise installer
inventory; the distinction between consent and integrity; dry-run behavior;
and managed-device checksum guidance, see
[Remote Installer Policy](remote-installer-policy.md).

Setup intentionally stays serial for mutating installers and state writes until
Base has a setup-plan/preflight layer that can prove safe concurrency boundaries.
See [`basectl setup` parallelism](setup-parallelism.md).

On macOS, `basectl setup` sends a best-effort notification when setup completes
or fails after running for at least 30 seconds. Notifications are skipped during
`--dry-run` and never change the setup exit status. Use `basectl setup --notify`
to force a notification for quick runs, `basectl setup --no-notify` or
`BASE_SETUP_NOTIFY=false` to disable notifications, and
`BASE_SETUP_NOTIFY_MIN_SECONDS` to tune the default threshold. When `--notify`
is requested on macOS, Base warns if `osascript` is not available.

## Daily Project Loop

| Command | What it does | Important flags |
|---|---|---|
| `basectl projects list` | Discover Base-managed projects under the workspace root. | `--workspace <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl activate <project>` | Start an interactive Base Bash runtime shell for a project. | `--workspace <path>`, `--no-cd` |
| `basectl test [project]` | Run the project's declared test command from the project root. | `--project <name>`, `--workspace <path>`, `--dry-run`, `-- <args>` |
| `basectl run [project] <command>` | Run a named manifest command from the project root. | `--project <name>`, `--workspace <path>`, `--dry-run`, `-- <args>` |
| `basectl run [project] --list` | List runnable commands declared by a project manifest. | `--project <name>`, `--workspace <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl build [project] [target...]` | Run declared build targets, or `build.default` when no target is provided. | `--project <name>`, `--workspace <path>`, `--dry-run`, `-- <args>` |
| `basectl build [project] --list` | List build targets declared by a project manifest. | `--project <name>`, `--workspace <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl demo [project]` | Run a project-owned demo script. | `--project <name>`, `--workspace <path>`, `--dry-run`, `-- <args>` |
| `basectl devcontainer [project]` | Preview or write `.devcontainer/devcontainer.json` from a Base manifest. Dry-run is the default. | `--workspace <path>`, `--format <text\|json>`, `--write` |
| `basectl devenv-report [project]` | Classify Base manifest fields for Nix/devenv planning without generating files or requiring Nix. | `--workspace <path>`, `--format <text\|json>` |
| `basectl trust status [project]` | Show one project's manifest trust status, or all discovered command-bearing projects. | `--workspace <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl trust allow <project>` | Approve the current manifest command contract on this machine. | `--workspace <path>`, `--manifest-sha256 <sha256>` |
| `basectl trust revoke <project>` | Remove local manifest command approval. | `--workspace <path>` |

Manifest-declared `test`, `run`, `build`, `demo`, and activation surfaces are
project-owned code executed from the project root. Review manifests from
unfamiliar repositories before running them; use `--dry-run` or `--list` where
available and inspect `activate.source` directly before activation.

These four lifecycle commands use one project-selection order: `--project
<name>`, then a backward-compatible first positional value when it names a
registered project, then the nearest `base_manifest.yaml` from the current
directory. If none applies, Base returns a controlled error. `--workspace`
changes where named projects are discovered; it does not replace nearest-
manifest traversal. From a workspace root with no project manifest, pass
`--project <name>` or a registered positional project.

For `run` and `build`, a registered first positional value keeps its legacy
project meaning even when the current manifest declares a command or target
with the same name. Select the current project explicitly to disambiguate, for
example `basectl run --project current api` or `basectl build --project current
api`. Bash and Zsh completion use the same read-only resolution rules.

`basectl run --list --format json` and `basectl build --list --format json`
are stable, side-effect-free automation contracts. Each object has
`schema_version: 1`, a `project` object (`name`, `root`, `manifest_path`), and
an ordered `commands` or `targets` array. Each command item has `name`,
`command`, and `runner` (`string` or `null`). Each target item has `name`,
`working_dir`, `command`, `description` (`string` or `null`), and `runner`
(`string` or `null`). These keys are always present. Listing and completion
read manifest metadata only: they do not execute project commands or grant
manifest trust.

## Diagnostics And Logs

| Command | What it does | Important flags |
|---|---|---|
| `basectl setup --ci [project]` | Run setup with CI-safe defaults. Does not run tests or create runners/VMs. | `--format <text\|json>`, `--manifest <path>`, `--profile <list>`, `--recreate-venv`, `--upgrade-pip` |
| `basectl check [project]` | Check Base readiness and, when selected by project name or `--manifest`, manifest-declared project requirements. It does not install or repair prerequisites, modify project files, or run tests. Normal runs write local logs/history; project checks also record `~/.base.d/<project>/checks/last.json`. | `--ci`, `--profile <list>`, `--format <text\|json>`, `--manifest <path>`, `--remote-network` |
| `basectl doctor [project]` | Explain Base and optional project findings with stable finding IDs and fixes. | `--ci`, `--profile <list>`, `--format <text\|json>`, `--manifest <path>`, `--remote-network`, `--no-color` |
| `basectl doctor explain <finding-id>` | Print local, deterministic guidance for a stable finding ID. | `--format <text\|json>` |
| `basectl logs` | List recent Base CLI runtime logs. | `--command <name[,name...]>`, `--limit <count>` |
| `basectl logs last-failed` | Print the latest failed command metadata plus a bounded redacted log tail. | `--command <name[,name...]>`, `--lines <count>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl logs --latest` | Print the newest matching log path only. | `--command <name[,name...]>` |
| `basectl history` | List one record per public Base command invocation. | `--project <name>`, `--command <name[,name...]>`, `--status <ok\|warn\|error>`, `--limit <count>`, `--format <text\|csv\|tsv\|yaml\|json>`, `--oldest-first`, `--last <duration>`, `--since <time>`, `--until <time>`, `--local-time` |
| `basectl history --report` | Print a local Markdown or JSON activity report from history and log metadata. | `--limit <count>`, `--format <markdown\|json>`, `--oldest-first`, `--last <duration>`, `--since <time>`, `--until <time>`, `--local-time` |
| `basectl logs --open` | Open the newest matching log in `PAGER` or `EDITOR`. | `--command <name[,name...]>` |
| `basectl logs --tail` | Tail and follow the newest matching log. | `--command <name[,name...]>`, `--lines <count>` |
| `basectl clean` | Preview cleanup of completed Base run bundles and component caches; use `--yes` to delete matches. Active runs are retained and reported. | `--older-than <age>`, `--keep-last <count>`, `--dry-run`, `--yes` |
| `basectl config path` | Print the local Base config path. | none |
| `basectl config show` | Show local Base config as redacted JSON. | none |
| `basectl config doctor` | Diagnose local Base config. | none |

## Workspace

| Command | What it does | Important flags |
|---|---|---|
| `basectl workspace status` | Show read-only workspace project status and latest recorded project check dates. Uses `workspace.manifest` from user config unless `--manifest` is supplied. | `--workspace <path>`, `--manifest <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl workspace check` | Render check-oriented readiness state across workspace projects. Text output summarizes check names and messages; JSON keeps the diagnostic envelope. Uses `workspace.manifest` from user config unless `--manifest` is supplied. | `--workspace <path>`, `--manifest <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl workspace doctor` | Render actionable workspace diagnostics with stable finding IDs and fix guidance. Uses `workspace.manifest` from user config unless `--manifest` is supplied. | `--workspace <path>`, `--manifest <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl workspace onboarding` | Summarize expected-repository first-day state and next actions without cloning or setup. Requires a configured or explicit workspace manifest. | `--workspace <path>`, `--manifest <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl workspace agent-brief` | Report local baseline, agent-guidance, AI-context, environment, and validation evidence for expected and extra Base-managed repositories without mutation or network calls. Requires a configured or explicit workspace manifest. | `--workspace <path>`, `--manifest <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl workspace clone` | Clone or validate expected repositories from a workspace manifest. Missing-repository materialization is GitHub-only today because this path delegates to `repo clone`. Uses `workspace.manifest` from user config unless `--manifest` is supplied. Text output uses a stable repository/action/result table with aggregate counts. | `--workspace <path>`, `--manifest <path>`, `--include-optional`, `--dry-run` |
| `basectl workspace pull` | Explicitly fetch and validate a canonical workspace manifest source before updating the local workspace manifest. Uses `workspace.manifest_source` and `workspace.manifest` from user config unless flags are supplied. | `--source <url-or-path>`, `--manifest <path>`, `--dry-run` |
| `basectl workspace update` | Run `git pull --ff-only` across present repositories in manifest order, including the active Base checkout when it is the manifest's `base` target. Continues after failures, skips missing optional repositories, treats missing required repositories as failures, and reports updated/unchanged/skipped/failed counts. | `--workspace <path>`, `--manifest <path>`, `--dry-run` |
| `basectl workspace init <workspace-source>` | Initialize a workspace from a workspace configuration repository, update local workspace config, and optionally materialize member repositories. | `--owner <owner>`, `--path <path>`, `--workspace <path>`, `--manifest <path>`, `--include-optional`, `--dry-run` |
| `basectl workspace configure` | Preview the existing `repo configure` repair path by default across discovered Base-managed workspace repositories or an explicit workspace manifest. Use `--apply` to authorize changes; interactive runs prompt unless `--yes` is supplied. Skips missing, non-Base-managed, or non-GitHub repos and continues after per-repo failures. | `--workspace <path>`, `--manifest <path>`, `--dry-run`, `--apply`, `--yes` |
| `basectl workspace setup` | Set up eligible repositories from a workspace manifest in manifest order by delegating to each repository's local `basectl setup` command. Skips ineligible repositories, continues after per-repo failures, and reports setup/skipped/failed counts. | `--workspace <path>`, `--manifest <path>`, `--dry-run`, `--yes` |

## Repository And GitHub Workflow

This section is intentionally GitHub-specific except for local baseline
inspection. Use ordinary Git to clone non-GitHub repositories, then use the
daily project loop commands from the local checkout.

| Command | What it does | Important flags |
|---|---|---|
| `basectl repo init <name>` | Create a Base-managed repository baseline, including `.github/base-project.yml`, and optionally create/configure the GitHub repo. Use `--path .` for the current checkout. If `--repo` creates a new remote, init attaches `origin`, creates an initial commit, and pushes; existing remotes are never implicitly pushed. Use `--pr --issue <number>` for an explicit baseline PR. Real PR runs derive the issue category; offline `--pr --dry-run` also requires `--category <name>`. Use `--agent-ready` to seed `AGENTS.md` and `skills.md` with the baseline, or `--release` to seed the generic release contract and process docs. Use repeatable `--language <csv>` values to seed normalized `project.languages` metadata; selecting `python` also writes `python.manager: uv`. | `--path <path>`, `--repo <owner/name>`, `--issue <number>`, `--category <name>`, `--language <csv>`, `--description <text>`, `--license <SPDX>`, `--public`, `--private`, `--pr`, `--agent-ready`, `--release`, `--project <title>`, `--project-owner <login>`, `--project-schema <schema>`, `--copy-project-fields-from <title>`, `--initiative-option <name>`, `--no-configure`, `--no-project`, `--no-protect-default-branch`, `--dry-run` |
| `basectl repo clone <name-or-owner/name>` | Clone one GitHub repository into the configured Base workspace, treating matching existing checkouts as already satisfied. | `--owner <owner>`, `--path <path>`, `--dry-run` |
| `basectl repo check [path]` | Verify the local repository baseline. Stable inspection JSON uses the shared v1 envelope. | `--agent-guidance`, `--agent-ready`, `--release`, `--format <text\|json>` |
| `basectl repo configure [path]` | Apply Base-managed GitHub repository settings, labels, default branch protection, non-default branch naming enforcement, the trusted issue/category branch policy workflow, and repo Project metadata. After a default-branch dispatch produces a recent trusted success, its GitHub-Actions-bound PR-head status becomes required. Reads `.github/base-project.yml` to seed options and fill missing issue defaults when present; `--release` also seeds the generic release contract and process docs, while `--replace-project` repairs a nonstandard Project layout. | `--repo <owner/name>`, `--project <title>`, `--project-owner <login>`, `--project-schema <schema>`, `--copy-project-fields-from <title>`, `--initiative-option <name>`, `--release`, `--replace-project`, `--no-project`, `--no-protect-default-branch`, `--dry-run` |
| `basectl repo agent-guidance [path]` | Seed optional repo-local agent guidance files, optionally through a draft PR. Real PR runs derive the issue category; offline `--pr --dry-run` also requires `--category <name>`. | `--repo <owner/name>`, `--repo-name <name>`, `--default-branch <name>`, `--validation-command <cmd>`, `--issue <number>`, `--category <name>`, `--pr`, `--dry-run` |
| `basectl repo installer-template [path]` | Write the maintained project installer starter script to a path, defaulting to `./install.sh`, optionally through a draft PR. Real PR runs derive the issue category; offline `--pr --dry-run` also requires `--category <name>`. | `--print`, `--repo <owner/name>`, `--issue <number>`, `--category <name>`, `--pr`, `--dry-run` |
| `basectl gh issue list` | List GitHub issues through `gh`. | passes through `gh` options |
| `basectl gh issue create` | Create an issue with Base category conventions, assign it, and add repo Project metadata when the repo is known. Defaults to `--category enhancement` and Project `Size=S` when omitted. Use `--assignee <login>` to assign explicitly or `--no-assignee` to bypass a repository default. Project updates are limited to Projects linked to the issue repository unless `--allow-cross-repo` is explicitly supplied. | `--category <bug\|enhancement\|documentation\|ci\|security>`, `--title <title>`, `--body <body>`, `--repo <owner/name>`, `--assignee <login>`, `--no-assignee`, `--project <title>`, `--project-owner <login>`, `--size <T\|S\|M\|L>`, `--no-project`, `--allow-cross-repo` |
| `basectl gh issue readiness <number>` | Check whether an issue has the required body sections and, when Project coordinates are supplied, Base Project fields before assignment. Omitting Project coordinates reports a partial result. Stable inspection JSON uses the shared v1 envelope. | `--repo <owner/name>`, `--project-owner <login>`, `--project-number <number>`, `--format <text\|json>` |
| `basectl gh issue start <number>` | Start the issue-backed branch workflow after verifying the issue has exactly one standard category; an explicit `--category` must match that label. The issue repository resolves from an explicit selector, then `GH_REPO`, then `origin`. | `--category <category>`, `--title <title>`, `--repo <owner/name>`, `-R <owner/name>` |
| `basectl gh auth status` | Inspect GitHub authentication state without displaying token values. Warns when an environment token takes precedence over stored credentials and distinguishes network failures from unavailable login. | `--hostname <host>` |
| `basectl gh auth refresh` | Explicitly refresh the stored GitHub credential and optionally request additional OAuth scopes. It does not alter `GH_TOKEN` or other environment-provided credentials. | `--hostname <host>`, repeatable `--scope <scope>`, `--scopes <scope,...>`, `--clipboard` |
| `basectl gh pr create/status/checks/ready/merge` | Create and manage pull requests through Base's workflow wrapper. `pr create` rejects a noncanonical current branch before invoking GitHub, auto-injects `Fixes #<issue>` unless `--no-fixes` is passed, and uses `github.pr` from `base_manifest.yaml` when present. | passes through `gh` options; `pr create` also accepts `--no-fixes` |
| `basectl gh branch stale` | Report stale local branches. Stable inspection JSON uses the shared v1 envelope. | `--days <days>`, `--format <text\|json>` |
| `basectl gh branch prune` | Prune safe merged branches. Pass `--closed-unmerged` to include branches whose pull requests were closed without merging. | `--dry-run`, `--yes`, `--remote`, `--closed-unmerged` |
| `basectl gh worktree prune` | Prune stale merged worktrees. Pass `--closed-unmerged` to include clean worktrees tied to closed, unmerged pull requests. | `--dry-run`, `--yes`, `--closed-unmerged` |
| `basectl gh project doctor` | Inspect GitHub Project metadata against the Base Project schema. | `--project <title>`, `--owner <login>`, `--schema base-project` |
| `basectl gh project configure` | Create or repair Base-managed Project metadata. | `--project <title>`, `--owner <login>`, `--repo <owner/name>`, `--schema base-project`, `--config <path>`, `--copy-fields-from <title>`, `--replace-project`, `--initiative-option <name>`, `--dry-run` |
| `basectl gh project issue set-fields <number>` | Add an issue to the Project if needed and update metadata fields. The target Project must be linked to the issue repository unless the intentional cross-repository exception is enabled. | `--project <title>`, `--repo <owner/name>`, `--config <path>`, `--allow-cross-repo`, field options |

## Release And Context

| Command | What it does | Important flags |
|---|---|---|
| `basectl release check --version <version>` | Inspect release readiness without publishing. Supports all five report formats; JSON uses the shared v1 inspection envelope. | `--manifest <path>`, `--format <text\|csv\|tsv\|yaml\|json>` |
| `basectl release plan --version <version>` | Print the release plan and downstream handoff details. | `--manifest <path>` |
| `basectl release notes --version <version>` | Extract release notes for the requested version. | `--manifest <path>` |
| `basectl release publish --version <version>` | Create the annotated Git tag and GitHub Release only after the configured repository, origin fetch/push URLs, live remote default branch, and local full `HEAD` SHA match; recheck before tagging and verify the local, pushed, and GitHub tag SHAs. | `--manifest <path>`, `--dry-run`, `--yes` |
| `basectl docs` | Open the Base documentation home page on GitHub. | `--show-url` |
| `basectl export-context [project]` | Export a project's `.ai-context/` directory as Markdown or Zip. | `--workspace <path>`, `--format <markdown\|zip>`, `--output <path>`, `--print`, `--list-files` |
| `basectl prompt list` | List repo-owned Markdown prompts that Base can render for AI-assisted workflows. | none |
| `basectl prompt product-self-review` | Print the periodic Base product self-review prompt with current Base metadata. | `--output <path>` |

## Detailed Product Layers And Shipped Commands

> **Deep reference:** This section is intentionally skippable on a first read.
> It preserves the detailed command and runtime reference for contributors and
> evaluators; start with [Quickstart](../README.md#quickstart), then use the focused
> [Command Quick Reference](command-reference.md) and
> [Technical Overview](technical-overview.md) when you need command detail.

Base's primary product outcome is readiness and handoff. The command and runtime
details below preserve discovery of the shipped execution contract, workflow
packs, and adapters that support that outcome.

### 1. Core Outcome And Enabling Execution Contract

Base should give the user one entry point for setting up and validating a
project or a workspace that contains multiple project repositories.

Current implemented commands include:

- `basectl setup [project]`
- `basectl check`
- `basectl doctor`
- `basectl <setup|check|doctor> --ci [project]`
- `basectl clean --older-than <age>`
- `basectl clean --keep-last <count>`
- `basectl config path`
- `basectl config show`
- `basectl config doctor`
- `basectl update-profile`
- `basectl update`
- `basectl projects list`
- `basectl workspace <status|check|doctor|onboarding|agent-brief|clone|pull|update|init|configure|setup>`
- `basectl trust status [project]`
- `basectl trust <allow|revoke> <project>`
- `basectl repo init <name>`
- `basectl repo clone <name-or-owner/name>`
- `basectl repo check [path]`
- `basectl repo configure [path]`
- `basectl repo agent-guidance [path]`
- `basectl repo installer-template [path]`
- `basectl gh <area> <command>`
- `basectl release check --version <version>`
- `basectl release plan --version <version>`
- `basectl release notes --version <version>`
- `basectl release publish --version <version>`
- `basectl prompt list`
- `basectl prompt product-self-review`
- `basectl activate <project>`
- `basectl test [project]`
- `basectl build [project] [target...]`
- `basectl demo [project]`
- `basectl run [project] <command>`
- `basectl export-context [project]`
- `basectl logs [options]`
- `basectl devcontainer [project]`
- `basectl devenv-report [project]`
- `basectl docs`
- `basectl onboard`
- `basectl history [--report]`
- `basectl version`

Use `basectl --help` for the journey-oriented command map. For a group or leaf,
`basectl help <nested path>` and `basectl <nested path> --help` show the same
public usage without exposing private Python runtime options.

`--ci` runs setup, check, and doctor with CI-safe defaults such as
non-interactive behavior and JSON-capable output. The deprecated `basectl ci`
compatibility alias remains available for v1.x consumers; use the flag on the
underlying command for new scripts.
The CI-safe lifecycle commands do not run project tests, launch GitHub Actions
locally, or create Ubuntu/Multipass VMs. Use `basectl test` for a project's
declared test command and `bin/base-test` for Base's full source-checkout
validation suite. See
[CI-safe mode](basectl-ci.md) for the CI contract, and
[Command Quick Reference](command-reference.md) for a scannable command
lookup table.

The important idea is that the user should not need to memorize a different
bootstrap story for every repository in the workspace.

Base should be able to discover participating project repositories checked out
under a shared workspace root, for example:

```text
~/work/
  base/
  banyanlabs/
  bankbuddy/
  blend/
  brew/
```

Over time, each project repo can declare how Base should interact with it,
likely through a small project manifest or well-defined conventions.

The first version of that manifest is `base_manifest.yaml` at a project repo
root. It declares the project name and the project contracts Base should
orchestrate:

```yaml
schema_version: 1

project:
  name: example

brewfile: Brewfile

mise: .mise.toml

artifacts:
  - type: python-package
    name: requests
    version: latest

health:
  required_env:
    - DATABASE_URL
    - REDIS_URL
  required_ports:
    - name: postgres
      host: 127.0.0.1
      port: 5432
      state: listening
    - name: app
      port: 8000
      state: free

activate:
  source:
    - .base/activate.sh

test:
  command: pytest tests/

commands:
  dev: uvicorn app:app --reload
  lint: ruff check .
```

`schema_version` is optional for existing manifests and defaults to `1`. It is
an integer compatibility marker for the manifest contract, not a Base release
number. Base rejects manifests with a newer schema version than it understands
and asks the user to upgrade Base.

The manifest intentionally describes what the project needs and which
project-owned commands Base should expose. Base's direction is
delegation-first: use mature tools for the domains they already own, and keep
Base responsible for participation semantics, readiness diagnostics, explicit
execution trust, lifecycle guidance, onboarding, and handoff evidence. Project
environments and command execution remain owned by their declared substrates.

Manifest-declared commands are trusted project code. Base executes
`test.command`, `build.targets.*.command`, `commands.*`, `demo.script`, and
`activate.source` entries from the project root. Review manifests from
unfamiliar repositories before running `basectl test`, `basectl build`,
`basectl run`, `basectl demo`, or manifest-backed `basectl activate`; use
`--dry-run` and `--list` first for command surfaces that support read-only
inspection, and inspect `activate.source` entries directly before activation.
`basectl check <project>` and `basectl doctor <project>` include advisory
command-lint warnings for obvious missing executables or project scripts;
those warnings do not make an untrusted manifest safe to run. See
[Manifest Command Trust](manifest-command-trust.md) for the local allow
flow before first execution of unfamiliar manifest commands.

The optional top-level `brewfile` field points to a Homebrew `Brewfile` relative
to the project root. When present, `basectl setup` runs
`brew bundle --file=<project-root>/<brewfile>` before reconciling artifacts. Use
this for ordinary Homebrew formulae and casks instead of adding every Homebrew
package to Base's hand-curated artifact registry.

The optional top-level `health.required_env` list declares environment variables
the project needs in the local shell. `basectl check <project>` and
`basectl doctor <project>` report whether those variables are present and
non-empty. Base only checks presence; it never reads, prints, or logs the
variable values.

The optional top-level `health.required_ports` list declares local TCP ports
the project expects to be either `listening` or `free`. Each entry must include
`port` and `state`; `host` defaults to `127.0.0.1`, and `name` is an optional
display label. Base checks whether a TCP connection succeeds on the declared
endpoint. It does not start or stop services, inspect process ownership, or
perform Docker Compose health checks.

The optional top-level `activate.source` list declares project-root-relative
shell scripts to source when `basectl activate <project>` starts the runtime
shell. Base sources those scripts after the Base runtime and project virtual
environment are ready, rejects paths outside the project root, reports missing
scripts clearly, and logs only the sourced script path.

Future manifest fields should follow the same rule. A `mise` field causes Base
to run `mise install` from the project root when a project chooses that
substrate. A `test` field gives `basectl test` a single project-owned command
to run. A `commands` map gives `basectl run` named project commands that run
from the project root with the same Base project environment contract as
`basectl test`. Projects that keep tasks in `mise` can declare `test.mise`
instead:

```yaml
test:
  mise: test

commands:
  dev: mise run dev
  lint: mise run lint
```

Commands may declare a generic `runner`. The first supported runner is `uv`:

```yaml
test:
  command: pytest
  runner: uv

commands:
  taxbuddy:
    command: taxbuddy
    runner: uv
```

`runner: uv` routes that command through `uv run -- ...`. It is independent of
the project-level Python manager, so composite projects can use uv for one
Python utility while keeping other commands in Go, Node, shell, or `mise`.

For a polyglot project such as `banyanlabs`, keep Base at the workspace
orchestration layer and let the language-native tools own their usual files.
Base should see a small manifest contract:

```yaml
schema_version: 1

project:
  name: banyanlabs

brewfile: Brewfile

mise: .mise.toml

test:
  mise: test
```

Then `.mise.toml` can pin the project runtimes and expose the task Base should
delegate to:

```toml
[tools]
go = "1.22"
java = "temurin-21"

[tasks.test]
run = "go test ./... && ./gradlew test"
```

Use the `Brewfile` for ordinary workstation tools such as Maven, Gradle,
`golangci-lint`, `protobuf`, or Docker-related CLIs when Homebrew is the right
installer. Keep Go dependencies in `go.mod`/`go.sum` and Java dependencies in
Maven or Gradle project files. Base does not need first-class `go-package` or
`java-package` artifact types until it has a Base-specific behavior to add on
top of those native ecosystems.

Base does not run arbitrary setup hooks from the manifest. Projects should use
typed Base contracts or project-owned installers/tasks until there is an
explicit, reviewable hook contract for when hooks run, where they run, whether
they are interactive, and how dry-run/check/doctor report them. See
[Setup Hooks Boundary](setup-hooks.md).

The curated built-in artifact registry lives in
`lib/base/artifact-registry.yaml` using schema version `1`, and
`cli/python/base_setup/registry.py` loads and validates that data before setup,
check, or doctor use it. The registry should stay small and Base-aware.
`python-package` artifacts are pass-through PyPI package names and install into
the project virtual environment at `<project-root>/.venv` for non-Base projects
by default. Projects that need the historical external location can declare
`python.venv_location: external`.
Homebrew-managed `tool` artifacts currently support `version: latest`;
`basectl check` and `basectl doctor` treat an installed but outdated Homebrew
package as unhealthy, and `basectl setup` upgrades it. Ordinary Homebrew tools
should move toward Brewfile delegation. Pinned Homebrew versions fail clearly
until Base grows explicit versioned tool support. The registry boundary is
captured in [Artifact Adapter Registry](artifact-adapter-registry.md).

The optional structured `python:` manifest section supports uv-managed Python
projects:

```yaml
python:
  manager: uv
```

For uv-managed projects, Base delegates setup to `uv sync`, uses the
project-local `.venv` for activation and project commands, and skips
Base-managed `python-package` reconciliation. See
[Python Manifest Section](python-manifest.md).
Projects without a top-level `python:` section or any `python-package`
artifacts are treated as shell-only for setup and diagnostics. Base parses and
reconciles those manifests from its own runtime, does not create a project
`.venv` for its control plane, and reports workspace venv state as
`not_applicable`. An explicit `python: {}` keeps the existing Base-managed
project venv contract; `project.languages: [python]` remains taxonomy only.
Use `basectl check <project> --format json` for detailed runtime diagnostics
and `basectl workspace status --format json` to compare actual project Python
versions across a workspace.

Artifacts may include `bootstrap: true` when they are part of the minimum Python
runtime contract needed before Base can reconcile a project's remaining
artifacts. Base currently uses this marker in `lib/base/default_manifest.yaml`
for `click`, `PyYAML`, and `tomli` for Python 3.10 TOML parsing.

You can inspect the projects Base can see with:

```bash
basectl projects list
basectl projects list --format json
basectl workspace status
basectl workspace status --format json
basectl workspace status --manifest ~/work/workspace.yaml
basectl workspace check
basectl workspace doctor
basectl workspace onboarding --manifest ~/work/workspace.yaml
basectl workspace agent-brief --manifest ~/work/workspace.yaml --format json
basectl workspace init basefoundry/base-workspace --dry-run
basectl workspace clone --manifest ~/work/workspace.yaml --dry-run
basectl workspace configure
basectl workspace configure --apply
basectl workspace setup --manifest ~/work/workspace.yaml --dry-run
basectl workspace update --manifest ~/work/workspace.yaml --dry-run
```

By default this scans `workspace.root` from `~/.base.d/config.yaml` when that
value is configured. If it is not configured, Base falls back to the parent
directory of `BASE_HOME`, which matches the source-checkout sibling-repo layout.
Use `--workspace <path>` to inspect a different workspace root for one command.
Project list output is tab-separated as `<project-name><TAB><path>`.
In a source checkout, `basectl projects list` can run before `basectl setup`
when the ambient `python3` has Base's bootstrap Python dependencies available;
otherwise it reports a targeted setup diagnostic.
`basectl projects list` and the read-only workspace status, doctor, onboarding,
and agent-brief commands support `--format json` for
machine-readable output.
Workspace clone, pull, init, configure, and setup use text output only. Status reports
each discovered project's manifest validity, whether the Base-managed project
virtual environment is present, and the latest recorded `basectl check
<project>` or `basectl workspace check` date when one exists. Check records live
under `~/.base.d/<project>/checks/last.json`; status JSON includes the full
timestamp and recorded check status.
Check and doctor run project diagnostics across discovered projects and keep
invalid project manifests visible as per-project findings. Workspace check also
refreshes each checked project's last-check record after rendering its report;
record-write failures are logged without changing the diagnostic result.

`basectl workspace onboarding` is also shipped. It summarizes first-day
workspace onboarding from a workspace manifest without cloning repositories or
running setup. It reports ready, needs-setup, invalid-manifest,
missing-required, and missing-optional repository states with next actions as a
read-only text or JSON view.

`basectl workspace agent-brief` turns the same manifest and local repository
state into a handoff-readiness view. It includes expected repositories and
extra locally discovered Base-managed projects, then reports repository
baseline, agent-guidance, `.ai-context`, environment, and validation evidence.
Readiness is structural: a ready repository has a valid manifest, an executable
interpreter file at the expected project-environment path, complete Base
baseline and agent-guidance file contracts, and an available validation path.
The executable interpreter is reported as `present_unverified`; the brief never
executes it. The recommended repository check and validation commands still
need to run separately and may fail. `.ai-context` is reported as useful context, not
required by the existing agent-ready repository contract. Present repositories
without a Base manifest remain `unmanaged`; the brief reports generic guidance,
context, and validation evidence when available but does not recommend Base
adoption. The command does not clone, run setup or validation, mutate repository
checkouts, update workspace manifests, write repo guidance or context, or make
network calls.

Set `workspace.manifest` in `~/.base.d/config.yaml`, or use `--manifest <path>`
with `basectl workspace status`, `check`, `doctor`, `onboarding`, or
`agent-brief`, to include expected repositories from a local workspace
manifest. The command-line `--manifest` value takes precedence over the
configured manifest. Missing required repositories are errors, missing optional
repositories are warnings, and Base-managed projects outside the manifest stay
visible as warnings.

Use `basectl workspace clone --manifest <path>`, or configure
`workspace.manifest`, to materialize the missing required GitHub repositories
from that manifest. The command keeps existing repositories visible, delegates
each repository operation to `basectl repo clone`, and supports `--dry-run` for
a no-write preview. Text output uses a stable repository/action/result table:
existing repositories are `present`, newly materialized repositories are
`cloned`, optional omissions are `skipped`, dry-run operations are `planned`,
and failures include concise details and exit codes. Successful delegated clone
output is suppressed in normal interactive mode; timestamped delegated Base log
records remain in debug diagnostics rather than being rendered as detail lines.
Optional repositories are
reported but skipped unless `--include-optional` is supplied. Workspace manifests may list non-GitHub Git
URLs for reporting, but automatic materialization through `workspace clone` is
GitHub-only today; clone GitLab, Bitbucket, internal Git, or local repositories
with ordinary Git first, then let Base discover the local checkout.

An external multi-repository manager may materialize repositories before Base
discovers opted-in projects. Base does not currently import or synchronize
`mani.yaml`, the clone configuration emitted by `gita freeze`, `.repos`,
Android Repo manifests, or `west.yml`.
Until a separately designed adapter exists, either let the external tool remain
the only repository-set authority and use Base's local discovery, or maintain a
deliberate Base workspace manifest for Base-specific expected-set semantics.

Use `basectl workspace init <workspace-source>` for first-run bootstrap from a
workspace configuration repository. The source can be a local path, GitHub URL,
`owner/repo`, or a short repository name resolved with `--owner <owner>` or
`github.default_owner`. `--path <path>` controls where the workspace
configuration repo is checked out or read. `--workspace <path>` controls where
member repositories are cloned. Init validates `workspace.yaml` before
materializing member repositories and then delegates those clones through
`basectl workspace clone`.

Use `basectl workspace pull`, or `basectl workspace pull --dry-run`, when
`workspace.manifest_source` and `workspace.manifest` are configured to refresh a
local workspace manifest explicitly. `--source <url-or-path>` and
`--manifest <path>` override those configured values for one command. Pull
validates the fetched manifest before writing and never mutates project
repositories.

Use `basectl workspace update --dry-run` to preview running `git pull --ff-only`
across the existing repositories in manifest order, then run
`basectl workspace update` to apply it. Update never clones, resets, or changes
the workspace manifest. It continues after individual Git failures, reports
updated/unchanged/skipped/failed counts, skips missing optional repositories,
and treats missing required repositories as failures. If the manifest points at
the active `BASE_HOME/base` checkout, that control plane is skipped; a separate
workspace checkout of `base` is updated normally. Text output uses a stable
repository/action/result table; raw Git output is retained for debug
diagnostics, and failures include concise repository and exit details.

Use `basectl workspace configure` to preview applying `basectl repo configure`
across Base-managed repositories in the workspace, then run
`basectl workspace configure --apply` to authorize the repair path. Interactive
runs ask for confirmation; use `--apply --yes` only after reviewing the plan in
automation. With
`--manifest <path>`, Base walks the expected repository set, skips missing or
non-Base-managed repositories, and continues after per-repo failures. Without a
manifest, Base scans discovered local Base-managed projects under the workspace
root. This is the fastest way to roll out shared repo or Project schema repairs
across a local repository set while keeping each repository's `repo configure`
behavior idempotent.

Use `basectl workspace setup --dry-run` to preview project setup across the
expected repositories, then run `basectl workspace setup` to execute it. Setup
walks the manifest in order, skips the active `base` control plane and
repositories that are not eligible for Base setup, and delegates each eligible
repository to its local `basectl setup --manifest <path> <project>` command.
Use `--yes` to forward setup confirmation to each delegated command. A setup
failure does not prevent later repositories from running; the final counts
report setup, skipped, and failed repositories and the command exits nonzero
when any setup target fails. Required missing checkouts and invalid required
manifests are also reported as failures during a dry run, so the preview can be
used as a CI gate without modifying repositories.

Start a new Base-managed repository with:

```bash
basectl repo init example --repo basefoundry/example
```

This creates the local repository baseline: README, version, changelog,
contributing guide, Apache-2.0 license, `.gitignore`, `base_manifest.yaml`, a
`tests/validate.sh` contract, and a GitHub Actions workflow that runs it.
By default, `repo init` creates the repository under `workspace.root` from
`~/.base.d/config.yaml`; if that is not configured, it falls back to the parent
directory of `BASE_HOME`. Use `--path <path>` for an explicit location.
When refreshing the current checkout, pass the repository name plus `--path .`;
`.` is a path value, not the `repo init` name. `repo init` also creates the
GitHub repository when needed and then standardizes its settings when
`--repo <owner/name>` is provided or when an existing `origin` remote can be
inferred. Newly created GitHub repositories are private by default; pass
`--public` when a public repository is intentional. When `repo init` creates
the remote, it also attaches `origin`, creates an initial commit, and pushes
the current branch. Existing remotes are never implicitly pushed. Use
`--pr --issue <number>` on an existing clean Git worktree to commit baseline
changes on a canonical issue-backed branch, push that branch to `origin`, and
open a pull request. Use `--no-configure` to skip the GitHub step, or rerun it
later with `basectl repo configure`. The generated license defaults to
`Apache-2.0`, matching Base.
Real PR runs derive and verify the issue category;
offline `--pr --dry-run` previews also require `--category <name>`. Add
`--agent-ready` when a new baseline should also include `AGENTS.md` and
`skills.md` for repo-local agent workflow guidance.
Use repeatable `--language <csv>` values to record an explicit, normalized
polyglot profile in `project.languages`; selecting `python` also generates the
explicit `python.manager: uv` manifest contract.

Clone an existing GitHub repository into the configured workspace with:

```bash
basectl repo clone basefoundry/example
basectl repo clone example --owner basefoundry
```

Short names can use `github.default_owner` from `~/.base.d/config.yaml`.
Without `--path`, `repo clone` writes to `<workspace.root>/<repo>`, and
`--dry-run` prints the resolved repository, destination, clone tool, and clone
URL without touching the filesystem. Existing matching checkouts are treated as
already satisfied; conflicting destinations fail with guidance.

`repo clone` and `repo configure` are GitHub automation surfaces. For
non-GitHub Git repositories, use the forge's normal Git clone path and then use
Base's local project loop from the resulting checkout.

Check and repair the repo baseline with:

```bash
basectl repo check ~/work/example
basectl repo check ~/work/example --format json
basectl repo configure ~/work/example --repo basefoundry/example
```

The JSON form is a stable v1 inspection contract for automation. The same
envelope is available from release readiness, issue readiness, and stale-branch
inspection; see [Inspection JSON](inspection-json.md).

Seed optional repo-local agent guidance with:

```bash
basectl repo init example --repo basefoundry/example --agent-ready
basectl repo agent-guidance ~/work/example --repo-name example
basectl repo agent-guidance ~/work/example --repo-name example --issue 123 --category enhancement --pr --dry-run
basectl repo check ~/work/example --agent-guidance
basectl repo check ~/work/example --agent-ready
```

Use `repo init --agent-ready` for new baselines that should include agent
guidance from the first pull request. Use `repo agent-guidance` to add or repair
that optional layer in an existing repository. Use `repo check --agent-ready`
when a repo should satisfy the baseline-integrated agent readiness contract.

Use `--pr --issue <number>` on `repo agent-guidance` or `repo
installer-template` when the generated helper files should go through review
first. The target must be a clean Git worktree, the GitHub repository is
inferred from `origin` unless `--repo <owner/name>` is provided, and the opened
pull request is a draft on the canonical issue-backed branch. Real PR runs
derive and verify the issue's standard category label; offline `--pr --dry-run`
previews require `--category <name>` explicitly.

`repo configure` is intentionally idempotent. It enables Issues and Projects,
standardizes merge settings, deletes branches after merge, applies the
Base-managed default branch protection and branch naming rulesets, seeds the
trusted Issue Branch Policy workflow, configures a repo-named GitHub Project
copied from `base-project-template`, and creates the standard GitHub labels
documented in [Repository Baseline](repo-baseline.md). Once that workflow
is active and a default-branch dispatch has produced a recent trusted success,
rerunning `repo configure` makes its GitHub-Actions-bound
`base/issue-branch-policy` PR-head status required without weakening an
existing requirement when run history expires.
When `.github/base-project.yml` exists, `repo configure` also adds missing
shared Project field options, adds repo-specific `Area` and `Initiative`
Project options from that file, and applies its `issue_defaults` to Project
issue items that are missing those values.
`repo init` also seeds `.github/workflows/project-intake.yml`, a visible
fallback for issues created outside `basectl gh issue create`. `repo configure`
creates the workflow when it is missing from older Base-managed repositories.
The baseline also includes `.github/workflows/issue-branch-policy.yml`, which
does not require a secret, never checks out pull-request code, and automatically
queues default-branch revalidation for matching open pull requests when an
issue category label changes.
Set a `BASE_PROJECT_TOKEN` Actions secret with Project write access so that
workflow can add issue items and apply the repo Project defaults on issue open,
reopen, and close events. `repo configure` checks for that secret when Project
support is enabled and prints a `gh secret set BASE_PROJECT_TOKEN` command when
the required secret is missing.
Pass `--no-protect-default-branch` when a repository intentionally skips that
ruleset. Pass `--no-project` when a repository intentionally skips Base-managed
Project metadata, or `--project`, `--project-owner`, and
`--initiative-option` when the default Project title or Initiative values need
to vary by repository. During Project migration, pass
`--copy-project-fields-from <title>` to copy missing issue item field values
from an existing Project into the repo Project without overwriting values that
are already set. When an existing repo Project has the right fields and issue
items but the wrong GitHub view layout, pass `--replace-project` to replace it
from `base-project-template`. Base renames and closes the old Project as a
legacy archive, creates a fresh Project with the original title, links it to the
repo, backfills repo issues, and copies missing issue item fields from the
legacy Project before applying repo defaults. The repaired Project gets a new
Project number and URL. If the existing Project already has the standard Base
views, `--replace-project` leaves it intact and continues normal metadata
repair.

Run a discovered project's declared test command with:

```bash
basectl test example
```

When the current directory is inside a Base-managed project, the project name
can be omitted:

```bash
basectl test
```

Base runs the manifest `test.command` or `mise run <test.mise>` from the project
root, exports `BASE_PROJECT`, `BASE_PROJECT_ROOT`, `BASE_PROJECT_MANIFEST`, and
`BASE_PROJECT_VENV_DIR`, prepends the project virtual environment when it
exists, and returns the command's exit status. Use `--dry-run` to inspect the
resolved command without running it.

Pass additional arguments to the project's test command after `--`:

```bash
basectl test example -- -k focused_case
```

For `test.mise`, Base passes those arguments after `mise run <task> --`.

Run a discovered project's declared build targets with:

```bash
basectl build
basectl build example
basectl build example api worker
basectl build --project example api worker
```

The `build` contract is intentionally declarative. Base does not infer how to
compile Go, Java, C++, Node.js, or any other language. The project declares the
targets it owns:

```yaml
build:
  default:
    - api
    - worker
  targets:
    api:
      description: Build the API service.
      working_dir: services/api
      command: go build ./cmd/api
    worker:
      description: Build the worker service.
      working_dir: services/worker
      command: go build ./cmd/worker
```

`basectl build [project]` runs `build.default` sequentially. `basectl build
[project] <target> [target...]` runs only the named targets. Base exports the
same project environment variables as `basectl test`, prepends the project
virtual environment when it exists, changes into each target's `working_dir`,
and returns the first failing build command's exit status.

Use `--list` or `--dry-run` to inspect the manifest contract:

```bash
basectl build example --list
basectl build --list --format json
basectl build example --dry-run
```

Run other manifest-declared project commands with:

```bash
basectl run dev
basectl run example dev
basectl run example lint
basectl run --project example dev
```

The `commands` map is intentionally small and declarative:

```yaml
commands:
  dev: uvicorn app:app --reload
  audit:
    command: pytest tests/audit
    runner: uv
  lint: ruff check .
  format: ruff format .
```

`basectl run [project] <command>` runs the command from the project root,
exports the same `BASE_PROJECT`, `BASE_PROJECT_ROOT`,
`BASE_PROJECT_MANIFEST`, and `BASE_PROJECT_VENV_DIR` variables as
`basectl test`, prepends the project virtual environment when it exists, and
returns the command's exit status. Use `basectl run [project] --list` to see a
project's runnable commands. When the current directory is inside a
Base-managed project, `basectl run --list` lists that project.

`run`, `build`, `test`, and `demo` select projects in one order: explicit
`--project <name>`, a backward-compatible first positional project when that
name is registered, then the nearest `base_manifest.yaml`. At a workspace root
with no nearest manifest, pass `--project` or a registered positional project.
`--workspace` controls named-project discovery and does not scan arbitrary
directories. If a current command or build target has the same name as a
registered project, the legacy project interpretation wins; use `--project
<current-name>` to select the current command or target explicitly.

`basectl run --list --format json` and `basectl build --list --format json`
return stable `schema_version: 1` objects for automation. These list paths only
read manifest metadata; they do not execute commands or grant manifest trust.

Pass additional arguments after `--`:

```bash
basectl run example lint -- --fix
```

The command name `test` is reserved for the top-level `test` contract, so
`basectl run example test` delegates to the same command as
`basectl test example`.

Export a project's AI context pack with:

```bash
basectl export-context example
basectl export-context example --format zip --output /tmp/example-ai-context.zip
basectl export-context --print
basectl export-context --list-files
```

`basectl export-context` reads `.ai-context/` from the current or named
Base-managed project. Markdown exports combine context Markdown files with
stable source headings, using `.ai-context/INDEX.md` order when available and
falling back to deterministic filename order for unlisted files. Zip exports
contain only files from `.ai-context/` so they can be uploaded manually.
Exports fail closed on a symlinked context root, symlinked descendants, and
special files; only regular files stored inside the real context directory are
eligible.

Preview a Dev Containers configuration from a project manifest with:

```bash
basectl devcontainer example
basectl devcontainer example --format json
basectl devcontainer example --write
```

`basectl devcontainer` is dry-run by default and reports unsupported or
ambiguous manifest fields instead of guessing container behavior. `--write`
creates `.devcontainer/devcontainer.json` only when that file does not already
exist.

Inspect Nix/devenv compatibility without generating files with:

```bash
basectl devenv-report example
basectl devenv-report example --format json
```

`basectl devenv-report` classifies present manifest fields as supported,
unsupported, lossy, or project-owned so teams can evaluate Nix/devenv adoption
without installing or invoking Nix.

Open Base's documentation home page on GitHub with:

```bash
basectl docs
basectl docs --show-url
```

`basectl docs` opens the GitHub README because the README is the starting point
for the rest of Base's documentation. Use `--show-url` to print the URL without
opening a browser.

Print repo-owned AI workflow prompts with:

```bash
basectl prompt list
basectl prompt product-self-review
basectl prompt product-self-review --output /tmp/base-product-self-review.md
```

`basectl prompt` renders maintained Markdown prompts from Base's repo-visible
prompt library. The command prints prompts to stdout by default and can write
rendered Markdown to a path with `--output`; Base does not run the review or
send the prompt to any provider. The
first built-in prompt, `product-self-review`, is the periodic product
assessment ritual for revisiting Base's originality, usefulness, adoption
potential, creator-skill evidence, risks, and next directions.

Once a project is discoverable, activate it with:

```bash
basectl activate example
```

Activation spawns a project-specific Bash runtime shell, changes to the project
root, sets `BASE_PROJECT` and related project variables, adds project-owned
commands from `$PROJECT_ROOT/bin` when that directory exists, and activates the
project virtual environment at `<project-root>/.venv` by default. If the
manifest declares `activate.source`, Base then sources each declared script in
order. Exit that shell to return to the original environment.

The activated runtime shell is always Bash, even when the user's login shell is
Zsh. `BASE_ACTIVATE_SHELL` may point to another Bash executable, but it must not
point to Zsh or another non-Bash shell. Zsh-specific aliases, options,
completions, and prompt customizations are not loaded inside the activated Base
runtime shell.

Use `basectl activate example --no-cd` to keep the caller's current directory
while still loading the selected project's Base runtime environment.

Invoking `basectl` with no arguments in a terminal starts the default
interactive Base shell. It uses the nearest `base_manifest.yaml` above the
current directory to choose the active project, then preserves the current
directory. If no project manifest is found, it falls back to the `base` project.

Clean old Base CLI runtime logs, retained temp files, and cache entries with:

```bash
basectl clean --older-than 30d --dry-run
basectl clean --older-than 30d
basectl clean --keep-last 20
basectl clean --older-than 30d --keep-last 20
```

Cleanup only targets runtime artifacts under the Base cache root, which defaults
to `~/Library/Caches/base` on macOS. Set `BASE_CACHE_DIR` to override it.
Durable state such as `~/.base.d/config.yaml`, Base's own venv, and project
virtual environments are outside this scope.

Show recent Base CLI logs with:

```bash
basectl logs
basectl logs --command setup,check
basectl logs --latest
basectl logs --open
basectl logs --tail
basectl logs -v
```

`basectl logs` is read-only. It lists the newest runtime logs under the Base
cache root so failed Python-layer runs can be inspected without rerunning with
debug output enabled. It supports `-v`/`--debug` for its own diagnostics without
creating a new default log entry for the inspection run.

Show recent structured Base command history with:

```bash
basectl history
basectl history --project base
basectl history --command check --status error
basectl history --format json
basectl history --report
basectl history --report --format json
basectl history --oldest-first
basectl history --last 2h --oldest-first
basectl history --since 2026-07-17 --until 2026-07-18
basectl history --local-time
```

`basectl history` reads the local Base history index at
`<base-cache-root>/base/history/runs.jsonl`. Each invocation also has a
run-oriented bundle under `<base-cache-root>/base/runs/<run-id>/`, while
project-native commands use `<base-cache-root>/projects/<project>/<checkout>/`.
The default view shows one row per public `basectl` command. Delegated Python
and resolver steps share that invocation's run ID and `logs/primary.log`; they
are not separate history records. History records point to raw logs instead of
replacing them, and malformed or legacy internal rows are ignored while listing
recent runs. `--report` prints a privacy-conscious local activity
summary with recent commands, failure counts, common failing command families,
and log file locations. Use `--oldest-first` for chronological display,
`--last 2h` for a relative window, or `--since`/`--until` for explicit bounds.
Text and Markdown timestamps use UTC by default;
`--local-time` renders those views in the host's local timezone. JSON retains
canonical UTC timestamps. Reports do not include raw log contents, compact home
paths to `~`, and redact secret-looking arguments and URL credentials. The
broader local diagnostic report model is described in
[docs/observability.md](observability.md).

Inspect machine-local Base config with:

```bash
basectl config path
basectl config show
basectl config doctor
```

Base creates `~/.base.d/config.yaml` with a small first-run default when the file
is missing, then leaves user edits and symlinks alone. Base owns the meaning of
that file, but users own how it is edited, backed up, or synced. `config show`
prints redacted JSON for routine inspection; Base config is not a secret store.
See [docs/local-config.md](local-config.md).

Inspect release readiness for a Base-managed repository with:

```bash
basectl release check --version 1.8.0
basectl release check --version 1.8.0 --format json
basectl release plan --version 1.8.0
basectl release notes --version 1.8.0
basectl release publish --version 1.8.0 --dry-run
basectl release publish --version 1.8.0 --yes
```

`basectl release check|plan|notes` are read-only. They validate the manifest
release contract, version file, changelog section, Git worktree state, GitHub
CLI authentication, local and remote tag availability, and planned downstream
handoffs. `basectl release publish` reuses those checks, requires confirmation
unless `--yes` is supplied, creates an annotated tag, pushes the tag, and
creates the GitHub Release from the matching changelog section. Homebrew tap
updates remain a manual handoff printed by the command.

Use `--keep-last <count>` to retain the newest completed run bundles per owner
namespace. `--older-than` removes completed bundles and persistent component
caches by age; active bundles and durable `~/.base.d` state are never removed.

Use `basectl doctor` when you want a human-oriented diagnosis with suggested
fixes. Each finding includes a stable identifier that automation can use
instead of matching on human-readable messages; see
[docs/doctor-findings.md](doctor-findings.md).
`basectl check` and `basectl doctor` validate virtual environment integrity,
not just path existence, and recommend `--recreate-venv` when a Base-managed
venv is broken.

```bash
basectl doctor
basectl doctor --profile dev
basectl doctor --profile sre
```

`basectl check <project>` and `basectl doctor <project>` extend those checks to
a project's `base_manifest.yaml` artifacts after verifying the Base bootstrap
environment:

```bash
basectl check example
basectl doctor example
```

`basectl onboard [project]` provides a guided checklist for technically-adjacent
users who want a first Base setup flow around check, setup, profile refresh,
doctor, and project discovery. It defaults to `base`, and can target another
Base-managed project for the check/setup/doctor steps. Product-specific
onboarding should still live in project installers that call Base internally. See
[docs/basectl-onboard.md](basectl-onboard.md).

Today, `basectl workspace agent-brief`, onboarding output, stable diagnostics,
`basectl history --report`, and `basectl export-context` provide local evidence
for a manual handoff. The separate issue-oriented handoff bundle remains
planned in [#1562](https://github.com/basefoundry/base/issues/1562); Base does
not yet package branch, issue, history, diagnostics, and context exports into a
single artifact.

Base can also bootstrap supported IDEs for participating projects through the
optional `ide:` manifest section. It currently supports VS Code and Cursor app
installation, extension installation, additive user settings, and check/doctor
diagnostics. See [docs/ide-bootstrapping.md](ide-bootstrapping.md).

### 2. Enabling Execution Contract: Shell Environment

Base should manage shell environments at two levels:

- global environment shared across the whole workspace
- project-specific environment layered on top for an individual repo

That includes things like:

- common shell initialization
- PATH management
- shared environment variables
- host and OS detection
- project-local activation hooks
- predictable loading order

The goal is to make shell behavior explicit, inspectable, and repeatable instead
of depending on a fragile mix of ad hoc dotfiles and one-off scripts.

### 3. Enabling Execution Contract: Libraries And Wrappers

Base should provide a stable foundation for controlled CLI execution.

That includes:

- shell libraries for logging, errors, files, Git, networking, and standard
  helpers
- Python wrappers for running Python-based tooling with the right environment
- shell wrappers for sourcing shared libraries and normalizing execution context
- a consistent convention for passing arguments, setting environment variables,
  and reporting failures

The wrapper model matters because it keeps command behavior predictable. A CLI
should run inside a known environment instead of relying on whoever happened to
invoke it from whatever shell state they already had.
