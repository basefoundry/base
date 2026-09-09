# Base

![Tests](https://github.com/basefoundry/base/actions/workflows/tests.yml/badge.svg)
![Lint](https://github.com/basefoundry/base/actions/workflows/pylint.yml/badge.svg)
![Platform: macOS + Ubuntu/Debian](https://img.shields.io/badge/platform-macOS%20%2B%20Ubuntu%2FDebian-lightgrey)
![Version](https://img.shields.io/badge/version-1.9.0-blue)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> Base is an AI-ready Git-based, GitHub-primary workspace control plane for
> repository setup, local development, and verified pull requests.

Base is the local operating contract you add to a repository set so its readiness,
trusted execution, onboarding, and handoff stop depending on private maintainer
memory. It makes a project workspace explicit and repeatable. It gives developers
and platform engineers a shared way to prepare repositories, inspect readiness,
approve trusted project commands, and hand off work across one or more independent
Git repositories.

Use Base when you need to:

- create or configure a GitHub repository and its local workspace;
- make setup, readiness, tests, builds, and trusted execution inspectable before
  work starts;
- carry enough evidence from issue and implementation work to a verified,
  handoff-ready pull request.

Base owns workspace orchestration, policy, trust, readiness, and handoff. Your
repositories own their source code, tests, and project behavior; Git remains the
SCM boundary; GitHub remains Base's first-class forge automation target for
hosting and pull requests; environment managers and AI tools remain adapters.
That boundary lets Base coordinate the workflow without turning your projects
into a monorepo or moving project-specific logic into Base.

```text
inventory -> prepare -> verify -> trust -> onboard -> hand off
```

## Quickstart

For the canonical source-checkout install commands, see the
[source checkout install recipe](docs/bootstrap.md#source-checkout-install-recipe).
Then run the trust-conscious project proof:

```bash
# After completing the canonical source-checkout install recipe.
~/work/base/bin/basectl setup --dry-run
~/work/base/bin/basectl projects list --workspace ~/work
~/work/base/bin/basectl trust status base
```

Review the manifest identity and digest printed by `trust status` before
running the exact `basectl trust allow base --manifest-sha256 ...` command it
provides. This path lets you inspect and verify Base before adding it to shell
startup files. See [Start Here](#start-here) for the demo walkthrough and install
choices.

## See Base Run

The shortest proof is the real self-demo:

```bash
basectl demo base -- --non-interactive
```

This excerpt is from that manifest-declared run; local paths are shortened so
the workflow is easy to scan:

```text
$ basectl demo base -- --non-interactive

Base Self-Demo

== Step 1: Runtime Contract ==

BASE_PROJECT=base

== Step 2: Manifest Contract ==

11:demo:
12:  script: ./demo/demo.sh

== Step 4: Check And Doctor ==

Base CLI environment and project 'base' check passed.
Base doctor found no blocking issues for project 'base'.

== Step 6: Run And Test Delegation ==

[DRY-RUN] Would run command test for project base: ./bin/base-test
[DRY-RUN] Would run tests for project base: ./bin/base-test

Base self-demo complete.
```

[Play the full asciinema-compatible capture](docs/assets/base-self-demo.cast).

### Tool Comparison

| Tool | Primary responsibility | Base relationship |
|---|---|---|
| Base | Repository contracts, readiness, trust, onboarding, and handoff | Owns the local operating contract across participating repositories |
| [mise](docs/tool-boundaries.md) | Machine and project bootstrap, tool versions, environments, and tasks | Base delegates; choose mise when convergence is the primary outcome |
| [mani](docs/tool-boundaries.md) | Git repository inventory, synchronization, worktrees, filters, and tasks | Base coexists; choose mani when repository-set management is the primary need |

See [Tool Boundaries](docs/tool-boundaries.md) for the maintained comparison,
including where Base should delegate, integrate, or stay out of the way.

## Contents

- [Quickstart](#quickstart)
- [See Base Run](#see-base-run)
  - [Tool Comparison](#tool-comparison)
- [Why Base Exists](#why-base-exists)
- [What Base Is Responsible For](#what-base-is-responsible-for)
- [What Base Is Not Responsible For](#what-base-is-not-responsible-for)
- [Mental Model](#mental-model)
- [Likely Workspace Shape](#likely-workspace-shape)
- [Design Principles](#design-principles)
- [Source Control And Forge Support](#source-control-and-forge-support)
- [Start Here](#start-here)
  - [Trust-Conscious Proof, No Dotfile Changes](#trust-conscious-proof-no-dotfile-changes)
- [How Base Fits](#how-base-fits)
  - [Reusable Bash Libraries](#reusable-bash-libraries)
- [Product Layers And Shipped Commands](#product-layers-and-shipped-commands)
- [Public Command Surface](#public-command-surface)
- [Installation Details](#installation-details)
  - [First-Mile Bootstrap](#first-mile-bootstrap)
  - [Homebrew](#homebrew)
  - [Source Checkout](#source-checkout)
  - [After Installation](#after-installation)
- [Version Identity](#version-identity)
- [Documentation](#documentation)
- [Compatibility](#compatibility)
- [Shell Startup Files](#shell-startup-files)
- [Optional Utility Tools](#optional-utility-tools)
- [Current Status](#current-status)
- [License](#license)

## Why Base Exists

Every engineering project accumulates setup steps, readiness rules, trusted
commands, and handoff context that can become scattered across READMEs, shell
state, and maintainer memory. That problem exists within a single repository
and becomes more visible when work spans several repositories. Base gives a
project or participating repository set one explicit local contract for answering:
what belongs here, what is ready, what is missing, what may run, and what the
next person or agent needs to know.

In this product promise, **deterministic** is deliberately narrow. Base makes
declared inputs, inspection order, findings, and next actions explicit and
repeatable. It does not promise hermetic builds, byte-for-byte environments, or
transactional mutation across every repository and external tool.

For a concise evaluator view of where Base fits, what it gives a project or
multi-repo workspace, and how it compares with adjacent tools, see
[Why Base](docs/why-base.md).
For a candid maintained assessment of Base's originality, usefulness, adoption
potential, and engineering evidence, see
[Product Assessment](docs/product-assessment.md).

Common first-run and product questions are answered in [FAQ.md](FAQ.md).
Contributions should follow [CONTRIBUTING.md](CONTRIBUTING.md). Report security
issues and handle detected credentials according to [SECURITY.md](SECURITY.md).
Release notes are tracked in [CHANGELOG.md](CHANGELOG.md).

## What Base Is Responsible For

Base owns the local operating contract for participating repositories.

That means Base should be responsible for:

- inventorying participating repositories and their declared contracts
- preparing and verifying local readiness through explicit commands
- enforcing Base's local trust boundary for manifest-declared execution
- making onboarding state and handoff evidence inspectable
- providing the execution conventions and diagnostics that support that outcome

Repository/GitHub/release workflow packs and environment/IDE/container/AI
adapters support this contract, but they do not redefine the core product.

## What Base Is Not Responsible For

Base should not absorb project-specific logic that belongs inside individual
repositories.

Each project repo should still own:

- its own source code
- its own business logic
- its own build details
- its own runtime details
- its own tests
- its own project-specific setup steps

Base should orchestrate those things, not replace them.

## Mental Model

Think of Base as the local operating contract for a project, whether that
project is one repository or a set of independent Git repositories.

A single repository can use Base to make setup, readiness, trusted execution,
and handoff explicit. When a project spans several repositories, Base extends
the same contract across the repository set. Each project repo remains independent;
Base sits beside those repos and offers:

- one declared way to inventory, prepare, and verify local readiness
- one explicit trust boundary for project-owned commands
- one onboarding story and a growing set of local handoff evidence

That gives a multi-repo setup some of the ergonomic benefits people often reach
for in a monorepo, without forcing unrelated codebases into a single repository.

## Likely Workspace Shape

The target shape looks roughly like this:

```text
work/                          ← shared workspace root (`workspace.root`)
  base/                        ← Base repository (`BASE_HOME` for source installs)
  project-a/                   ← peer project with `base_manifest.yaml`
  project-b/                   ← peer project with `base_manifest.yaml`
  infra/                       ← another peer repo that can opt into Base
```

This directory shape does not prescribe one universal repository set. Each
project owns its own `base_manifest.yaml`; a team that wants a shared
repository inventory supplies a separate `workspace.yaml`, either as a local
file or through a dedicated workspace-config repository. Base Foundry's
maintainer inventory is kept in `base-workspace`, but normal Base installations
do not need that private workspace configuration.

Projects opt into Base with minimal coupling:

- Base discovers projects in the shared workspace
- projects expose a small contract through `base_manifest.yaml`
- Base provides common orchestration on top

See [Workspace Manifest](docs/workspace-manifest.md) for the ownership split,
manifest sources, and workspace command behavior.

## Design Principles

Base follows a few simple principles.

1. Keep project repos independent.
2. Prefer explicit conventions over hidden shell magic.
3. Keep wrappers thin but reliable.
4. Make setup and test flows idempotent where possible.
5. Make findings and next actions stable enough for human and automated handoff.
6. Let Base provide the common layer without turning into a dumping ground for
   project-specific behavior.

## Source Control And Forge Support

Base assumes Git. Mercurial, Perforce, Subversion, and other non-Git SCMs are
out of scope.

Base is GitHub-primary rather than forge-independent. GitHub is the only
first-class forge automation target today for repository creation,
configuration, Issues, pull requests, Projects, Actions intake, and release
publishing. A GitLab, Bitbucket, internal Git, or local Git repository can
still use Base's local project loop once it is checked out locally and declares
`base_manifest.yaml`.

See [Source Control And Forge Support](docs/source-control-and-forge-support.md)
for the command-by-command compatibility contract and non-GitHub Git workflow.

## Start Here

### Trust-Conscious Proof, No Dotfile Changes

The canonical no-dotfile proof is in [Quickstart](#quickstart). It runs
`basectl trust status base` before the final `basectl demo base -- --non-interactive`;
review the manifest identity and digest, then run the exact `basectl trust allow
base --manifest-sha256 ...` command it provides. This path
lets you inspect and verify Base before adding it to shell startup files.
Until shell-profile setup puts `basectl` on `PATH`, replace its leading
`basectl` with `~/work/base/bin/basectl`; keep the project and printed digest
unchanged.

To inspect a small, real Base-managed project, clone
[`basefoundry/base-demo`](https://github.com/basefoundry/base-demo) next to
Base and run its walkthrough:

```bash
git clone https://github.com/basefoundry/base-demo.git ~/work/base-demo
~/work/base/bin/basectl setup base-demo
~/work/base/bin/basectl trust status base-demo
```

Review the reported command surfaces, then run the exact command it prints:
`basectl trust allow base-demo --manifest-sha256 ...`. Only then launch the
demo:

```bash
~/work/base/bin/basectl demo base-demo
```

The demo sequence is separate from the canonical Quickstart proof; both keep
manifest trust review ahead of execution.

## How Base Fits

Base coordinates the systems that already own their domains:

- Homebrew still owns ordinary macOS packages and Brewfiles.
- mise owns its configuration model, including language/runtime management and
  its broader machine and project bootstrap behavior. When a Base manifest
  points to a mise config, Base checks mise's config trust and missing tools,
  runs `mise install`, and delegates `mise run`. On Debian-family Linux, Base
  can install a missing mise CLI after `--dry-run` review and `--yes` consent
  under its [remote-installer policy](docs/remote-installer-policy.md). Base
  does not invoke or interpret `mise bootstrap`.
- Project repositories still own their source code, tests, installers, service
  definitions, and product-specific onboarding.

Repository discovery, clone or synchronization, status, and command fan-out are
shared ecosystem primitives rather than Base's differentiation. See
[Tool Boundaries](docs/tool-boundaries.md) for the dated comparison, including
when to choose mise, `mani`, `gita`, `vcs2l`, Android Repo, or `west` instead.

### Reusable Bash Libraries

Base's reusable Bash libraries are also available as a standalone package for
scripts that want Base's Bash helper conventions without adopting the Base
local operating contract:

```bash
brew trust basefoundry/base
brew install basefoundry/base/base-bash-libs
```

Base consumes reusable Bash libraries from an external `base-bash-libs` checkout
or Homebrew package. The resolution order, standalone usage path, and
post-migration boundary are documented in
[Base Bash Libraries](docs/base-bash-libs.md).

## Product Layers And Shipped Commands

The full command and runtime reference lives in the focused documentation:

- [Command Quick Reference](docs/command-reference.md) — current commands,
  flags, output formats, and detailed command behavior.
- [Technical Overview](docs/technical-overview.md) — product model, workspace
  shape, manifest contract, architecture, and implementation boundaries.

This README keeps the product overview and first-run path above; use the focused
references when you need command or runtime detail.

The top-level public command inventory remains visible here:

- `basectl setup [project]`
- `basectl check`
- `basectl doctor`
- `basectl clean --older-than <age>`
- `basectl config <path|show|doctor>`
- `basectl update-profile`
- `basectl update`
- `basectl projects list`
- `basectl workspace <status|check|doctor|onboarding|agent-brief|clone|pull|update|init|configure|setup>`
- `basectl trust <status|allow|revoke>`
- `basectl repo <init|clone|check|configure|agent-guidance|installer-template>`
- `basectl gh <area> <command>`
- `basectl release <check|plan|notes|publish>`
- `basectl prompt <list|product-self-review>`
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

## Public Command Surface

Base exposes its own commands through `$BASE_HOME/bin`. That directory is added
to `PATH` by Base's managed shell startup snippets.

`bin/basectl` is the control-plane command. Additional Base-owned public
commands, when needed, are tiny real launcher files in `bin/` that delegate to
`basectl`; their implementation remains under
`cli/bash/commands/<command>/` or, in the future,
`cli/python/commands/<command>/`.

Example launcher for a hypothetical Base-owned Bash command:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/basectl" example "$@"
```

Projects expose their own commands through `$PROJECT_ROOT/bin`. When
`basectl activate <project>` starts a project runtime shell, Base adds that
directory to `PATH` if it exists, behind `$BASE_HOME/bin` and behind any
detected optional Base Platform Tools checkout. Project Python command packages
should be treated as implementation details unless a project-owned launcher
exposes them from `bin/`.

Optional utility commands live in
[`basefoundry/base-platform-tools`](https://github.com/basefoundry/base-platform-tools).
When that repository is checked out next to Base as `base-platform-tools`, Base
adds its `bin/` directory to `PATH` in new Bash/Zsh shells and Base runtime
shells. This is detected dynamically by the sourced shell snippets; users do not
need to rerun `basectl update-profile` after checking out the optional repo.

Project launchers that need to run Python packages should delegate through
`base-wrapper` so they use the selected project virtual environment and Base's
Python library roots:

```bash
#!/usr/bin/env bash
exec "$BASE_HOME/bin/base-wrapper" --project "${BASE_PROJECT:-example}" example_cli "$@"
```

## Installation Details

This is the canonical README summary of the supported installation paths.
Choose Homebrew when you want Base managed like an installed consumer tool, or a
source checkout when you want to contribute to or dogfood Base. For complete,
copy-pasteable recipes, safety disclosures, and edge cases, see [First-Mile
Bootstrap](docs/bootstrap.md).

For setup profiles, Python runtime policy, setup parallelism, and completion
notifications, see [Setup Profiles And Behavior](docs/command-reference.md#setup-profiles-and-behavior).

### First-Mile Bootstrap

Use `bootstrap.sh` on a blank or uncertain macOS machine. It can select an
existing Base install, install through Homebrew, or prepare a source checkout.
On Ubuntu/Debian it prints the manual source-checkout handoff instead of running
apt automatically. Review the `--dry-run` output before applying system or
remote-installer changes; use `--source`, `--brew`, or the narrower
`--ensure-bash` mode when needed.

When Homebrew, Git, or a supported Bash may be missing, the concise verified
handoff is:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

For a reviewed Homebrew installer, provide both checksum variables before
running that command:

```bash
BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL=file:///path/to/homebrew-install.sh \
BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256=<sha256> \
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

Use `--ensure-bash --dry-run` and `--ensure-bash --yes` for the narrower
Bash-repair path. Use `--source`, `--brew`, or `--source --dry-run` for explicit
mode selection and Ubuntu/Debian review. The same installer pin can use
`BASE_HOMEBREW_INSTALLER_URL` and `BASE_HOMEBREW_INSTALLER_SHA256`.

### Homebrew

Use the full formula name `basefoundry/base/base` for Homebrew installs and
upgrades. If Homebrew asks you to trust the tap, run `brew trust
basefoundry/base` before retrying. Homebrew owns the installed files while
Base's local runtime remains under `~/.base.d`; `basectl update` delegates
Base upgrades to Homebrew.

See the [Homebrew install recipe](docs/bootstrap.md#homebrew-install-recipe) and
[Remote Installer Policy](docs/remote-installer-policy.md) for the complete
trust and upgrade contract.

### Source Checkout

Use a source checkout for contribution or dogfooding. The canonical recipe
installs from `~/work/base` (or a chosen path) and keeps profile integration
opt-in. For a stable no-Homebrew install, pin the published release:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/v1.9.0/install.sh \
  | bash -s -- --branch v1.9.0
```

Contributor installs may explicitly follow `HEAD`/`main`. See the
[stable source install recipe](docs/bootstrap.md#stable-source-install-recipe),
[source checkout install recipe](docs/bootstrap.md#source-checkout-install-recipe),
and [First-Mile Bootstrap](docs/bootstrap.md) for the exact commands.

### After Installation

All installation paths prepare the local Base runtime under `~/.base.d` and
leave shell startup integration opt-in. Setup creates
`~/.base.d/config.yaml` with a default `workspace.root` of `~/work`; set it
to the shared directory that contains your repositories. Add Base to future
interactive shells only after reviewing the marked-section behavior of
`basectl update-profile`; see [Shell Startup Files](docs/shell-startup.md).

For team or security-conscious rollouts, review installer plans with `--dry-run`
and pin remote installer content when your workstation policy requires it. The
complete checksum, consent, Ubuntu/Debian, tap-trust, and project-installer
guidance lives in [First-Mile Bootstrap](docs/bootstrap.md) and [Remote
Installer Policy](docs/remote-installer-policy.md).

The common development loop after installation is:

```bash
basectl projects list
basectl setup <project>
basectl check <project>
basectl doctor <project>
basectl test <project>
basectl demo [project]
basectl run [project] <command>
basectl export-context <project>
basectl docs
basectl activate <project>
```

For Base itself, run the self-demo or the dogfood test contract:

```bash
basectl demo base -- --non-interactive
basectl test base
```

## Version Identity

`VERSION` is the latest published release identity. `DEVELOPMENT_VERSION` is
the numeric next development line. A clean tagged release or packaged install
reports the clean `VERSION`, while a mutable Git checkout—including a dirty
checkout based on a release tag—reports
`DEVELOPMENT_VERSION-dev+g<short-sha>` and appends `.dirty` when local changes
are present. For example, Base `1.9.0` and mutable development code targeting
`1.9.0` cannot report the same identity.

Project-specific onboarding should live in project installers that call Base
internally. `basectl onboard [project]` can run Base's setup/check/doctor flow
for a selected project, but product-specific setup still belongs in scripts such
as `banyanlabs/install.sh`. See [Project Installers](docs/project-installers.md)
for the recommended boundary.

## Documentation

The top-level README is the product overview and first-run guide. The
[docs README](docs/README.md) is the map for architecture, runtime behavior,
feature designs, and ecosystem boundary decisions.

Key starting points:

- [FAQ](FAQ.md)
- [Command Quick Reference](docs/command-reference.md)
- [Technical Overview](docs/technical-overview.md)
- [Base Newcomer Orientation](docs/presentations/base-newcomer-orientation.md)
- [Architecture](docs/architecture.md)
- [Clean macOS Install Validation](docs/macos-install-validation.md)
- [Execution Model](docs/execution-model.md)
- [Runtime Environment](docs/runtime-environment.md)
- [Tool Boundaries](docs/tool-boundaries.md)
- [Doctor Finding IDs](docs/doctor-findings.md)
- [IDE Bootstrapping](docs/ide-bootstrapping.md)
- [Local Config](docs/local-config.md)
- [Project Demo Workflow](docs/project-demo-workflow.md)

## Compatibility

Base is macOS-first, with Ubuntu/Debian runtime support now included in the
tested support contract.

Intended supported platforms are:

- macOS 14 Sonoma or newer on Apple Silicon
- macOS 14 Sonoma or newer on Intel Macs
- Ubuntu/Debian runtime environments with apt-backed Base setup

The supported macOS version floor is macOS 14 Sonoma. Support means Base is
tested and expected to work on macOS 14 or newer with Homebrew's supported
install contract, Xcode Command Line Tools, a Homebrew-managed Bash, Git, and
Python installed through Base setup. Older macOS releases may work from source,
but they are outside Base's tested support contract.

Ubuntu/Debian support currently covers runtime checks, project diagnostics,
source-checkout validation, and apt-backed setup for the simple prerequisites
Base owns. Linux setup remains narrower than macOS setup and should stay behind
the platform-policy boundary described in [docs/linux-support.md](docs/linux-support.md).
Windows is out of scope.

The macOS CI floor runs on GitHub's `macos-14` runner. Newer macOS runners may
be added for coverage, but the floor job should stay until Base intentionally
raises the support floor.

OS-specific behavior should stay isolated behind small helpers instead of being
scattered through command code. For example, the Base runtime prompt can prefer
macOS `scutil` names while still falling back to generic `hostname`.

## Shell Startup Files

Base integrates with Bash and Zsh through marked sections in your real dotfiles;
it never takes over whole files. `basectl update-profile` creates or refreshes
the managed sections, preserving unrelated content and writing a timestamped
sibling backup before changing an existing file.

Run `update-profile` only after you want `basectl` on `PATH`, shell completions,
and `basectl activate <project>` available in new interactive shells:

```bash
~/work/base/bin/basectl update-profile --dry-run
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

By default, it updates `~/.bash_profile`, `~/.bashrc`, `~/.zprofile`, and
`~/.zshrc`. Use `basectl update-profile --remove` to remove only Base-managed
sections, or `--dry-run` to preview changes. The detailed file-by-file contract,
debugging guidance, and optional defaults are in
[Shell Startup Files](docs/shell-startup.md).

## Optional Utility Tools

Base no longer owns general-purpose utility CLIs such as `caff` and
`sort-in-place`. Those tools live in
[`basefoundry/base-platform-tools`](https://github.com/basefoundry/base-platform-tools),
which is the optional platform/SRE utility layer for Base-managed workspaces.
Check it out next to Base to make its launchers available automatically in new
shells:

```bash
git clone https://github.com/basefoundry/base-platform-tools.git ~/work/base-platform-tools
exec "$SHELL" -l
```

The Base control-plane surface remains `basectl`.

## Current Status

Base `1.9.0` is the current release. The implemented command surface covers
setup, checks, diagnostics, project discovery, project activation, project test
execution, manifest-declared mise trust/missing-tool checks plus `mise install`
and `mise run` delegation, cleanup, updates, onboarding, repository baseline
creation, CI-safe setup/check/doctor entry points, release readiness inspection,
guarded GitHub release publishing, GitHub workflow helpers, workspace
status/check/doctor/onboarding/init/clone/pull/configure flows, privacy-conscious
history reports, local AI context exports, repo-owned prompt rendering, the
`basectl docs` documentation shortcut, external reusable Bash library
consumption, and explicit prerequisite profiles for developer, SRE, AI tooling,
and local Linux lab setup. The `basectl setup`, `basectl check`, and `basectl
doctor` flows are platform-aware for macOS and Ubuntu/Debian, including
apt-backed prerequisite handling on Ubuntu/Debian; macOS diagnostics also warn
when Homebrew reports outdated or incomplete Xcode Command Line Tools.

For the documentation map and naming convention, see
[docs/README.md](docs/README.md). For accepted product requirements, see
[docs/product-requirements.md](docs/product-requirements.md). For the
architecture and product direction, see
[docs/architecture.md](docs/architecture.md). For the current `basectl` runtime
and dispatch contract, see [docs/execution-model.md](docs/execution-model.md).
For ecosystem boundary and integration decisions, see
[docs/tool-boundaries.md](docs/tool-boundaries.md).

The Base 1.9.0 release also owns the cross-repository compatibility BOM for the
validated Base, base-cli, base-bash-libs, and base-demo combination on Ubuntu
24.04 and macOS 14. Release notes are tracked in [CHANGELOG.md](CHANGELOG.md), and upcoming work is
tracked in GitHub Issues using the workflow in
[docs/github-workflow.md](docs/github-workflow.md).

Published Base, base-cli, and base-bash-libs releases can also trigger the
issue-backed downstream pin workflow documented in
[docs/release-process.md](docs/release-process.md). It opens reviewable
base-demo bump PRs and leaves merging to the downstream checks and review.

## License

Base is licensed under Apache 2.0. See [LICENSE](LICENSE) for the license terms.
