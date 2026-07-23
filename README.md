# Base

![Tests](https://github.com/basefoundry/base/actions/workflows/tests.yml/badge.svg)
![Lint](https://github.com/basefoundry/base/actions/workflows/pylint.yml/badge.svg)
![Platform: macOS + Ubuntu/Debian](https://img.shields.io/badge/platform-macOS%20%2B%20Ubuntu%2FDebian-lightgrey)
![Version](https://img.shields.io/badge/version-1.7.0-blue)

Base is a local operating contract for developers and platform engineers who
work across multiple independent Git repositories.

It makes that repo set easier to inventory, prepare, verify, trust, onboard,
and hand off without turning it into a monorepo or moving project-specific
logic into Base.

```text
inventory -> prepare -> verify -> trust -> onboard -> hand off
```

## Why Base Exists

Most real engineering environments are not a single repository. Their setup
steps, readiness rules, trusted commands, and handoff context are often spread
across READMEs, shell state, and maintainer memory. Base gives participating
repositories one explicit local contract for answering: what belongs here,
what is ready, what is missing, what may run, and what the next person or agent
needs to know.

In this product promise, **deterministic** is deliberately narrow. Base makes
declared inputs, inspection order, findings, and next actions explicit and
repeatable. It does not promise hermetic builds, byte-for-byte environments, or
transactional mutation across every repository and external tool.

For a concise evaluator view of where Base fits, what it gives a multi-repo
workspace, and how it compares with adjacent tools, see
[Why Base](docs/why-base.md).
For a candid maintained assessment of Base's originality, usefulness, adoption
potential, and engineering evidence, see
[Product Assessment](docs/product-assessment.md).

Common first-run and product questions are answered in [FAQ.md](FAQ.md).
Contributions should follow [CONTRIBUTING.md](CONTRIBUTING.md). Release notes
are tracked in [CHANGELOG.md](CHANGELOG.md).

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

### 90-Second Proof, No Dotfile Changes

The fastest trust-conscious evaluation path is a source checkout. It lets you
inspect the code, run setup explicitly, and prove the local project loop before
Base touches shell startup files:

```bash
git clone https://github.com/basefoundry/base.git ~/work/base
~/work/base/bin/basectl setup --dry-run
~/work/base/bin/basectl setup
~/work/base/bin/basectl projects list --workspace ~/work
~/work/base/bin/basectl trust status base
```

Review the manifest identity, digest, and read-only inspection commands, then
run the exact `basectl trust allow base --manifest-sha256 ...` command printed
by `trust status`. Until shell-profile setup puts `basectl` on `PATH`, replace
its leading `basectl` with `~/work/base/bin/basectl`; keep the project and
printed digest unchanged. The digest-bound approval is never inferred from
setup or an unattended flag. After approving the reviewed manifest, finish the
proof:

```bash
~/work/base/bin/basectl demo base -- --non-interactive
```

That sequence creates Base's local runtime state under `~/.base.d`, but it does
not edit `~/.bash_profile`, `~/.bashrc`, `~/.zprofile`, or `~/.zshrc`. Use the
same explicit path, `~/work/base/bin/basectl`, until you decide to add Base to
future interactive shells.

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

Success looks like a workspace where each participating project has a
`base_manifest.yaml`, appears in `basectl projects list`, can be checked with
`basectl check <project>`, and can run its declared test command through
`basectl test <project>` or named project commands through
`basectl run [project] <command>`.

### Shell Startup Is Explicit

Run `update-profile` only after you want `basectl` on `PATH`, shell
completions, and `basectl activate <project>` available in new interactive
shells:

```bash
~/work/base/bin/basectl update-profile --dry-run
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

`update-profile` manages only marked Base sections in Bash and Zsh startup
files and preserves non-Base content. See [Shell Startup Files](#shell-startup-files)
for the full dotfile boundary.

### Choose An Install Path

If your Mac already has Homebrew, Git, and a supported Bash, choose one of the
normal Base install paths:

- Use Homebrew when you want Base managed like an ordinary installed tool.
- Use a source checkout when you want to inspect, contribute to, or dogfood Base
  from the repository.

```bash
# Homebrew-managed install
brew trust basefoundry/base
brew install basefoundry/base/base
basectl setup
```

```bash
# Source checkout install
git clone https://github.com/basefoundry/base.git ~/work/base
~/work/base/bin/basectl setup
```

For Homebrew installs, Base itself lives under Homebrew's prefix rather than in
your project workspace. For source checkout installs, Base lives at the clone
path you choose, usually `~/work/base`. In both modes, first setup creates
`~/.base.d/config.yaml` with the default workspace root:

```yaml
workspace:
  root: ~/work
```

Edit `workspace.root` if your repositories live under a different shared
directory. You may also add an optional workspace manifest:

```yaml
workspace:
  root: ~/work
  manifest: ~/work/base-workspace/workspace.yaml
  manifest_source: https://raw.githubusercontent.com/<org>/<repo>/main/workspace.yaml
```

When `workspace.manifest` is set, workspace status, check, doctor, onboarding,
agent-brief, clone, and configure commands use it unless `--manifest <path>` is
supplied for a single command. `basectl workspace pull` treats it as the local
destination for an explicitly requested refresh. When
`workspace.manifest_source` is set, pull can refresh that local manifest from
the canonical source.

### New Or Uncertain Machine?

On a new macOS machine, or any machine where Homebrew, Git, or a supported Bash
may be missing, start with the first-mile bootstrap script:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

For a verified first run, pin reviewed Homebrew installer content before
executing the bootstrapper. Use the bootstrap-specific variables for this
script, or the `BASE_HOMEBREW_INSTALLER_URL` and
`BASE_HOMEBREW_INSTALLER_SHA256` pair when the same pin should apply to all
Base Homebrew entry points:

```bash
BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL=file:///path/to/homebrew-install.sh \
BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256=<sha256> \
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

The bootstrapper installs Homebrew, Git, and a supported Bash when needed,
chooses an existing Base install when one is present, otherwise defaults to a
source checkout at `~/work/base`, and prints the exact `basectl setup` and
`basectl update-profile` commands to finish the installation. It does not edit
shell startup files automatically.

If Base is already installed but `basectl` cannot start because Bash is too
old, repair only that prerequisite:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --ensure-bash --dry-run
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --ensure-bash --yes
```

Choose an install mode explicitly when needed:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --brew
```

For mode selection, dry-run behavior, and contributor setup details, see
[First-Mile Bootstrap](docs/bootstrap.md).

On Ubuntu/Debian Linux, the same bootstrap script prints the manual
source-checkout path instead of running apt itself:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source --dry-run
```

Review the printed apt, clone, `basectl setup --yes`, and `update-profile`
commands, then run them in the Ubuntu shell. The printed `--yes` handoff is for
unattended pasted commands; interactive `basectl setup` still applies setup
after prompting for Ubuntu/Debian system changes.

### Team Or Security-Conscious Rollout

Use `--dry-run` before first-mile setup when you need to review planned
installer actions. Managed workstations can pin or mirror Homebrew installer
content by setting `BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL` and
`BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256`; Base fails closed if either half of
that pair is missing or the digest does not match.

Project-owned installers should pin `BASE_INSTALL_URL` to a tag, commit, or
owned copy and set `BASE_INSTALL_SHA256` before executing Base's installer. See
[Remote Installer Policy](docs/remote-installer-policy.md) and
[Project Installers](docs/project-installers.md) for the maintained trust
contracts.

After Base is installed, the common development loop is:

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

## How Base Fits

Base's product responsibilities have four layers:

- **Core outcome:** deterministic local readiness and handoff across independent
  Git repositories.
- **Enabling execution contract:** `base_manifest.yaml`, `basectl`,
  `base-wrapper`, explicit activation, and declared project commands.
- **Supporting workflow packs:** repository baselines plus GitHub and release
  conventions. These support the outcome; they are not Base's primary product
  category.
- **Adapters:** environment managers, IDEs, containers, Nix/devenv, and AI
  tools remain external systems that Base detects, checks, invokes, or exports
  context for without taking over their domains.

These are responsibility layers, not separately installed packages. Base
orchestrates tools that already own their domains:

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
- Base owns the local contract that makes participation, readiness, trusted
  execution, and handoff explicit across projects.

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

Base's primary product outcome is readiness and handoff. The command and runtime
details below preserve discovery of the shipped execution contract, workflow
packs, and adapters that support that outcome.

### 1. Core Outcome And Enabling Execution Contract

Base should give the user one entry point for setting up and validating a
workspace that contains multiple project repositories.

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
- `basectl workspace <status|check|doctor|onboarding|agent-brief|clone|pull|init|configure>`
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
non-interactive behavior and JSON-capable output. The legacy `basectl ci`
wrapper remains as a compatibility alias. Neither surface runs project tests,
launches GitHub Actions locally, or creates Ubuntu/Multipass VMs. Use
`basectl test` for a project's declared test command and `bin/base-test` for
Base's full source-checkout validation suite. See
[CI-safe mode](docs/basectl-ci.md) for the CI contract, and
[Command Quick Reference](docs/command-reference.md) for a scannable command
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
[Manifest Command Trust](docs/manifest-command-trust.md) for the local allow
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
[Setup Hooks Boundary](docs/setup-hooks.md).

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
captured in [Artifact Adapter Registry](docs/artifact-adapter-registry.md).

The optional structured `python:` manifest section supports uv-managed Python
projects:

```yaml
python:
  manager: uv
```

For uv-managed projects, Base delegates setup to `uv sync`, uses the
project-local `.venv` for activation and project commands, and skips
Base-managed `python-package` reconciliation. See
[Python Manifest Section](docs/python-manifest.md).
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
basectl workspace configure --dry-run
```

By default this scans `workspace.root` from `~/.base.d/config.yaml` when that
value is configured. If it is not configured, Base falls back to the parent
directory of `BASE_HOME`, which matches the source-checkout sibling-repo layout.
Use `--workspace <path>` to inspect a different workspace root for one command.
Project list output is tab-separated as `<project-name><TAB><path>`.
In a source checkout, `basectl projects list` can run before `basectl setup`
when the ambient `python3` has Base's bootstrap Python dependencies available;
otherwise it reports a targeted setup diagnostic.
`basectl projects list` and the read-only workspace status, check, doctor,
onboarding, and agent-brief commands support `--format json` for
machine-readable output.
Workspace clone, pull, init, and configure use text output only. Status reports
each discovered project's manifest validity, whether the Base-managed project
virtual environment is present, and the latest recorded `basectl check
<project>` date when one exists. Check records live under
`~/.base.d/<project>/checks/last.json`; status JSON includes the full timestamp
and recorded check status.
Check and doctor run project diagnostics across discovered projects and keep
invalid project manifests visible as per-project findings.

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
a no-write preview. Optional repositories are reported but skipped unless
`--include-optional` is supplied. Workspace manifests may list non-GitHub Git
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

Use `basectl workspace configure --dry-run` to preview applying
`basectl repo configure` across Base-managed repositories in the workspace, then
run `basectl workspace configure` to apply the repair path. With
`--manifest <path>`, Base walks the expected repository set, skips missing or
non-Base-managed repositories, and continues after per-repo failures. Without a
manifest, Base scans discovered local Base-managed projects under the workspace
root. This is the fastest way to roll out shared repo or Project schema repairs
across a local repo family while keeping each repository's `repo configure`
behavior idempotent.

Start a new Base-managed repository with:

```bash
basectl repo init example --repo basefoundry/example
```

This creates the local repository baseline: README, version, changelog,
contributing guide, AGPL-3.0-or-later license, `.gitignore`, `base_manifest.yaml`, a
`tests/validate.sh` contract, and a GitHub Actions workflow that runs it.
By default, `repo init` creates the repository under `workspace.root` from
`~/.base.d/config.yaml`; if that is not configured, it falls back to the parent
directory of `BASE_HOME`. Use `--path <path>` for an explicit location.
When refreshing the current checkout, pass the repository name plus `--path .`;
`.` is a path value, not the `repo init` name. `repo init` also creates the
GitHub repository when needed and then standardizes its settings when
`--repo <owner/name>` is provided or when an existing `origin` remote can be
inferred. Newly created GitHub repositories are private by default; pass
`--public` when a public repository is intentional. Plain `repo init` writes the
local baseline but does not commit or push local files. Use `--pr --issue
<number>` on an existing clean Git worktree to commit baseline changes on a
canonical issue-backed branch, push that branch to `origin`, and open a pull
request. Use `--no-configure` to skip the GitHub step, or rerun it later with
`basectl repo configure`. Real PR runs derive and verify the issue category;
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
inspection; see [Inspection JSON](docs/inspection-json.md).

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
documented in [Repository Baseline](docs/repo-baseline.md). Once that workflow
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
[docs/observability.md](docs/observability.md).

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
See [docs/local-config.md](docs/local-config.md).

Inspect release readiness for a Base-managed repository with:

```bash
basectl release check --version 1.7.0
basectl release check --version 1.7.0 --format json
basectl release plan --version 1.7.0
basectl release notes --version 1.7.0
basectl release publish --version 1.7.0 --dry-run
basectl release publish --version 1.7.0 --yes
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
[docs/doctor-findings.md](docs/doctor-findings.md).
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
[docs/basectl-onboard.md](docs/basectl-onboard.md).

Today, `basectl workspace agent-brief`, onboarding output, stable diagnostics,
`basectl history --report`, and `basectl export-context` provide local evidence
for a manual handoff. The separate issue-oriented handoff bundle remains
planned in [#1562](https://github.com/basefoundry/base/issues/1562); Base does
not yet package branch, issue, history, diagnostics, and context exports into a
single artifact.

Base can also bootstrap supported IDEs for participating projects through the
optional `ide:` manifest section. It currently supports VS Code and Cursor app
installation, extension installation, additive user settings, and check/doctor
diagnostics. See [docs/ide-bootstrapping.md](docs/ide-bootstrapping.md).

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
[Remote Installer Policy](docs/remote-installer-policy.md).

Setup intentionally stays serial for mutating installers and state writes until
Base has a setup-plan/preflight layer that can prove safe concurrency boundaries.
See [`basectl setup` parallelism](docs/setup-parallelism.md).

On macOS, `basectl setup` sends a best-effort notification when setup completes
or fails after running for at least 30 seconds. Notifications are skipped during
`--dry-run` and never change the setup exit status. Use `basectl setup --notify`
to force a notification for quick runs, `basectl setup --no-notify` or
`BASE_SETUP_NOTIFY=false` to disable notifications, and
`BASE_SETUP_NOTIFY_MIN_SECONDS` to tune the default threshold. When `--notify`
is requested on macOS, Base warns if `osascript` is not available.

## Installation Details

For a blank macOS machine, use `bootstrap.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

The bootstrapper is intentionally small. It verifies macOS, installs Homebrew
when missing, installs Git and Bash through Homebrew when needed, then installs
Base through either a source checkout or Homebrew. It does not edit shell startup
files automatically. Instead, it prints the exact follow-up commands, typically:

```bash
~/work/base/bin/basectl setup
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

Pass `--source` or `--brew` with `bash -s --` to choose the route explicitly.
Without an explicit choice, the bootstrapper preserves an existing Homebrew Base
install, then an existing source checkout, and otherwise defaults to source mode.
See [First-Mile Bootstrap](docs/bootstrap.md) for the full bootstrap contract.

On Ubuntu/Debian Linux, `bootstrap.sh` does not run `sudo apt` automatically.
It prints the manual source-checkout path, including the supported apt
prerequisites, a sibling `base-bash-libs` checkout, `basectl setup --dry-run`,
`basectl setup --yes`, and `basectl update-profile`.

The focused `bootstrap.sh --ensure-bash --yes` path is intentionally narrower:
it installs only Bash after a dry-run review.

Base can be installed through its Homebrew tap:

```bash
brew trust basefoundry/base
brew install basefoundry/base/base
basectl setup
basectl update-profile
exec "$SHELL" -l
```

Use the full formula name `basefoundry/base/base` for Homebrew installs and
upgrades. `basefoundry/base` is the tap name, not the formula, and bare `base`
can resolve to unrelated Homebrew formulae or casks.

Base is not yet in Homebrew/core. Until that changes, use the tap commands
above. The planned core path keeps the reusable Bash libraries as a separate
`base-bash-libs` dependency so a future non-conflicting Base formula, expected
to be named `basefoundry`, can install with:

```bash
brew install basefoundry
```

The trust step is required on Homebrew versions that block formulae from
non-official taps until the tap is trusted. It is safe to run again on machines
that already trust `basefoundry/base`. Existing installs that predate this
trust step can fail during upgrade while Homebrew loads Base's tap-owned
`base-bash-libs` dependency. If that happens, run:

```bash
brew trust basefoundry/base
brew upgrade --no-ask basefoundry/base/base
```

Homebrew installs the Base files. `basectl setup` still prepares the local Base
runtime under `~/.base.d/base/.venv`, and `basectl update-profile` adds Base to
your shell startup path. When installed through Homebrew, `basectl update` for
Base hands off to Homebrew and runs setup afterward. This is equivalent to:

```bash
brew upgrade --no-ask basefoundry/base/base
```

For a Base development machine, prefer the source checkout as the active
`basectl`. Homebrew-installed Base and source-cloned Base can coexist, but the
active command is whichever executable wins on `PATH`, and both normally share
state under `~/.base.d`. Use Homebrew-managed Base for consumer install or
upgrade validation in a test account, separate machine, isolated `HOME`, or with
explicit paths such as `/opt/homebrew/bin/basectl` or `~/work/base/bin/basectl`.

When Base is installed through Homebrew, `BASE_HOME` points to the stable
Homebrew install location, such as `/usr/local/opt/base/libexec` or
`/opt/homebrew/opt/base/libexec`. It does not point to your project workspace.
Configure `workspace.root` in `~/.base.d/config.yaml` so commands such as
`basectl projects list`, `basectl activate <project>`, and
`basectl test <project>` can find your repositories:

```yaml
workspace:
  root: ~/work
```

The standalone installer is also available:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/install.sh | bash
exec "$SHELL" -l
```

This runs a shell script from GitHub, so review the script first if you do not
already trust this repository:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/install.sh
```

By default, the installer clones or updates Base at `~/work/base`, runs
`~/work/base/bin/basectl setup`, and then runs
`~/work/base/bin/basectl update-profile`. Set `BASE_INSTALL_DIR` or pass
`--dir <path>` to install somewhere else. When using the piped form, pass
installer options with `bash -s --`, for example:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/install.sh | bash -s -- --dir ~/work/base --no-profile
```

Use `--no-profile` to skip shell startup integration and `--dry-run` to print
planned actions.

The explicit manual bootstrap path is:

```bash
git clone https://github.com/basefoundry/base.git ~/work/base
~/work/base/bin/basectl setup
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

After the shell restarts, Base's managed startup section adds `~/work/base/bin`
to `PATH`, so `basectl` can be run without spelling out the full path. Use
`basectl version` or `basectl --version` to report the installed Base version.

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

Base integrates with Bash and Zsh through small managed sections in the user's
real dotfiles. Base does not take over whole dotfiles.

The command that installs or refreshes those sections is:

```bash
basectl update-profile
```

By default it updates all four startup files:

- `~/.bash_profile`
- `~/.bashrc`
- `~/.zprofile`
- `~/.zshrc`

Missing files are created. Existing files keep their non-Base content; Base only
adds or replaces its marked section. Before changing an existing startup file,
`basectl update-profile` writes a timestamped sibling backup such as
`~/.bashrc.backup.YYYYMMDDTHHMMSS`.

To remove Base from shell startup files without hand-editing dotfiles, run:

```bash
basectl update-profile --remove
```

This removes only Base-managed marked sections from Bash and Zsh startup files.
Use `basectl update-profile --remove --dry-run` to preview the planned backups
and removals.

`basectl update-profile` also creates `~/.base.d/profile.conf`, which records
whether the user has opted into Base's optional shell defaults. The managed
dotfile sections stay minimal and defer PATH/default handling to the sourced
Base snippets. The same sourced snippets also register `basectl` shell
completions, so future completion improvements arrive when Base is updated
without rewriting user dotfiles.

Run `basectl update-profile --defaults` to enable those optional defaults, and
run `basectl update-profile --no-defaults` to disable them again. Plain
`basectl update-profile` preserves the existing preference.

`BASE_PROFILE_VERSION` records the schema version of this Base-managed file. It
is reserved for future migrations and is not intended to be edited by users.

Update Base or a Base-managed project checkout with:

```bash
basectl update
basectl update bankbuddy
```

Omitting the project is equivalent to `basectl update base`. This command is
intentionally conservative. In a source checkout, it only runs from the selected
project repository's default branch, requires tracked project files to be clean,
pulls the latest changes through Git, and runs `basectl setup <project>` only
when the pull changes the checked-out revision. Untracked files do not block the
update; Git still stops the pull if an incoming tracked file would overwrite
them.

In a Homebrew-managed install, the Base update path remains Base-only:
`basectl update` runs the Base package upgrade,
`brew upgrade basefoundry/base/base`, and then runs `basectl setup base` with
inherited Base environment variables cleared. `basectl update --dry-run` prints
the Git or Homebrew handoff it would perform without changing files or packages.
For manual Homebrew upgrades outside `basectl update`, prefer
`brew upgrade --no-ask basefoundry/base/base` so Homebrew skips the preview
prompt path on already-current installs. If Homebrew refuses to load
`basefoundry/base/base-bash-libs` from an untrusted tap, run
`brew trust basefoundry/base` once and retry the upgrade.

Base also reads `~/.baserc` when it exists. Unlike `profile.conf`, `~/.baserc`
is user-managed and may be hand-edited. It is intended for simple,
shell-startup-safe Base preferences such as `BASE_DEBUG=1`; it should not become
a second `.bashrc` with arbitrary setup logic. See
[Runtime Environment](docs/runtime-environment.md) for the full variable
contract and mutability policy.

`~/.baserc` must not set Base-owned runtime or profile variables such as
`BASE_HOME`, `BASE_BIN_DIR`, `BASE_LIB_DIR`, `BASE_BASH_LIBS_DIR`,
`BASE_BASH_LIBS_SOURCE`, `BASE_OS`, `BASE_PLATFORM`, `BASE_HOST_ENV`, `BASE_SHELL`,
`BASE_PLATFORM_TOOLS_HOME`, `BASE_PLATFORM_TOOLS_BIN_DIR`,
`BASE_PROFILE_VERSION`, `BASE_ENABLE_BASH_DEFAULTS`, or
`BASE_ENABLE_ZSH_DEFAULTS`. Base startup snippets reject and restore those
variables if `~/.baserc` tries to change them.

Base-managed sections use explicit markers such as:

```bash
# >>> base: bashrc managed >>>
# ... Base-managed content ...
# <<< base: bashrc managed <<<
```

### Base Snippets

The managed sections source matching snippets under `lib/shell/`:

- `lib/shell/bash_profile` for `~/.bash_profile`
- `lib/shell/bashrc` for `~/.bashrc`
- `lib/shell/zprofile` for `~/.zprofile`
- `lib/shell/zshrc` for `~/.zshrc`

The names intentionally mirror the dotfiles they support, without leading dots
inside the repository.

Bash snippets and the Bash runtime rcfile share `lib/shell/baserc_guard.sh` for
safe `~/.baserc` loading. Zsh snippets keep their own guard logic for now.

### Login Profiles

`bash_profile` and `zprofile` stay thin.

For Bash, Base makes the login-shell bridge explicit: the Bash profile snippet
sources `~/.bashrc` with a guardrail. Bash needs this because login Bash shells
do not automatically read `~/.bashrc`.

For Zsh, Base does not source `~/.zshrc` from `zprofile`. Zsh already reads
`~/.zshrc` for interactive shells.

### Interactive RC Files

`bashrc` and `zshrc` are where interactive shell behavior belongs.

They are responsible for:

- guarding against non-interactive execution
- guarding against repeated sourcing
- deriving and exporting `BASE_HOME` from the sourced Base snippet
- adding Base's `bin/` directory to `PATH` so `basectl` is available after login
- adding an optional sibling `base-platform-tools/bin` directory to `PATH` when
  that repo is present
- keeping dotfile integration separate from the full Base runtime bootstrap
- optionally enabling shared shell defaults when `basectl update-profile --defaults` is used

They do not source `base_init.sh`. Base runtime setup happens only when the
`basectl` command runs a Base command, runs an explicit script path, or starts a
Base-enabled Bash shell.

When `basectl activate <project>` starts an interactive Bash runtime shell, it
uses Base's runtime rcfile rather than making Bash read `~/.bashrc` directly.
That runtime rcfile loads `base_init.sh`, sources the user's `~/.bashrc` once
with guardrails, activates the project virtual environment, and finally sets the
Base runtime prompt. This keeps user aliases and normal interactive Bash
behavior available while making Base stdlib functions such as `import_base_lib`
available during user Bash startup.

### Debugging Shell Startup

Set `BASE_DEBUG=1` to make Base-managed shell startup snippets print diagnostic
messages while they run. This is intentionally independent of `base_init.sh` and
stdlib logging, because dotfile debugging can happen before the Base runtime is
loaded.

For normal terminal startup, put this in `~/.baserc`:

```bash
BASE_DEBUG=1
```

For one-off checks, use an environment variable:

```bash
BASE_DEBUG=1 bash --rcfile ~/.bashrc -i
BASE_DEBUG=1 zsh -i
BASE_DEBUG=1 basectl
```

Diagnostics are printed to stderr and show which Base snippet loaded, how
`BASE_HOME` was derived, whether `$BASE_HOME/bin` was added to `PATH`, whether
optional shell defaults were enabled, and how the Base runtime shell was layered.

For command debugging, `basectl -v <command>` enables DEBUG logs after the Base
runtime is loaded and the selected command is dispatched. For earlier startup
debugging, use wrapper options that are consumed by `bin/basectl` before
`base_init.sh` is sourced:

- `--debug-wrapper` and `--verbose-wrapper` enable `LOG_DEBUG=1` before runtime
  initialization.
- `--utc-wrapper` enables UTC log timestamps before runtime initialization.
- `--color` preserves color-aware wrapper argument handling while keeping the flag
  out of command arguments.

Prefer `-v` unless the problem happens before the command implementation starts.

### Standard Shell Defaults

Base can provide optional, opinionated shell defaults, but they are not enabled
by plain `basectl update-profile`.

Current default-setting scripts are:

- `lib/shell/base_defaults.sh` for shell-neutral defaults shared by Bash and Zsh
- `lib/shell/bash_defaults.sh` for Bash-specific defaults
- `lib/shell/zsh_defaults.sh` for Zsh-specific defaults

Users can opt in during profile updates with:

```bash
basectl update-profile --defaults
```

Users can opt out again with:

```bash
basectl update-profile --no-defaults
```

Those defaults are intended to stay conservative:

- aliases like `rm -i`, `cp -i`, `mv -i`
- vi-style command editing
- completion ergonomics
- editor defaults
- pager defaults
- prompt defaults
- terminal usability behavior
- history behavior, including duplicate suppression, timestamped history, and
  multi-line command preservation

The defaults should not become a personal dotfile bundle. The following remain
outside `basectl update-profile --defaults` unless Base adds a separate,
explicit opt-in:

- color or listing aliases for tools such as `ls`, `grep`, or `diff`
- navigation shortcuts, `CDPATH`, auto-directory changes, or spelling
  correction
- signing and agent helpers such as `GPG_TTY`
- strict shell modes such as global `errexit`, `nounset`, or `pipefail`
- prompt features that run expensive checks, such as dirty Git status

Those settings are platform-sensitive, workflow-specific, or more likely to
change command behavior in surprising ways. Keep personal aliases and functions
in normal shell dotfiles, and keep simple Base preferences in `~/.baserc`.

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

Think of Base as the local operating contract beside a set of independent Git
repositories.

Each project repo remains independent. Base sits beside those repos and offers:

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

Projects opt into Base with minimal coupling:

- Base discovers projects in the shared workspace
- projects expose a small contract through `base_manifest.yaml`
- Base provides common orchestration on top

## Design Principles

Base follows a few simple principles.

1. Keep project repos independent.
2. Prefer explicit conventions over hidden shell magic.
3. Keep wrappers thin but reliable.
4. Make setup and test flows idempotent where possible.
5. Make findings and next actions stable enough for human and automated handoff.
6. Let Base provide the common layer without turning into a dumping ground for
   project-specific behavior.

## Current Status

Base `1.7.0` is the current release. The implemented command surface covers
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

Release notes are tracked in [CHANGELOG.md](CHANGELOG.md), and upcoming work is
tracked in GitHub Issues using the workflow in
[docs/github-workflow.md](docs/github-workflow.md).

## Short Version

Base is the local operating contract you add to a repo set so its readiness,
trusted execution, onboarding, and handoff stop depending on private maintainer
memory.

## License

Base is licensed under AGPL-3.0-or-later starting with v1.0.1.

Versions through v1.0.0 remain available under the MIT License as originally
published. See [LICENSE](LICENSE) for the current license terms.
