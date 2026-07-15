# Base Ecosystem Boundaries

This document captures how Base should relate to other popular developer tools.
Its purpose is not to compete with everything in the ecosystem. Its purpose is
to help Base stay sharp about what it owns, what it can orchestrate, and what
it should leave alone.

Evidence checked: 2026-07-14

When we evaluate another tool, we record five separate decisions:

1. What Base must **own** to preserve its readiness and handoff contract.
2. What Base should **delegate** to the external tool.
3. Whether a narrow Base **integration** would improve the combined workflow.
4. Where the products honestly **overlap** today.
5. What Base should **not expand into**, even when the adjacent tool is useful.

The answers are often mixed. Coexistence does not imply that Base has or needs
an adapter, and overlap does not make a generic capability part of Base's
differentiation. Proposed integrations in this document are explicitly future
ideas unless the text identifies a shipped Base behavior.

## Base's Center of Gravity

Base is strongest as a local operating contract for deterministic readiness and
handoff across participating Git repositories. Its durable responsibilities are:

- the Base participation and project contract in `base_manifest.yaml`
- semantic readiness findings with stable identifiers and machine-readable
  output where supported
- explicit local trust before manifest-declared project commands execute
- lifecycle and next-action guidance across prepare, verify, onboard, and handoff
- portable local evidence that another person or coding agent can inspect
- transparent delegation through `basectl` and `base-wrapper` when a project
  chooses an external substrate

Base also owns the safety and behavior of the first-mile bootstrap, shell
startup, workspace, repository, and release commands it ships. Those supporting
surfaces are not evidence that generic machine convergence or multi-repository
management is unique to Base.

Base gets weaker when it drifts into becoming any of these:

- a general tool version manager
- an automatic directory-based environment loader
- a full dotfile manager
- a generic task runner
- a full reproducible package manager or environment solver
- a generic multi-repository inventory, synchronization, or command fan-out
  manager
- a multi-VCS client or revision-controlled source-tree materializer

## Adapter Quality Bar

Base should grow through adapters before it grows through replacements. For any
external tool integration, the adapter should answer:

- How does Base detect whether this tool is relevant to a project?
- How does Base check whether the tool is installed and healthy?
- How does Base invoke the tool without hiding the underlying command?
- How does Base report failures in Base-native check, doctor, and JSON output?
- How does Base avoid owning the tool's full configuration model?
- How does Base behave when the tool is absent?

The result should feel like one readiness and handoff story while leaving
mature tools in charge of their own domains.

## Quick Decision Matrix

| Tool | What it primarily owns | Base relationship | Choose the adjacent tool when |
|---|---|---|---|
| `mise` | machine and project bootstrap, tool versions, environment, tasks | Delegate; keep the shipped Base adapter narrow | Declarative package, repository, dotfile, service, shell, or tool convergence is the main outcome. |
| `mani` | declarative Git repository inventory, sync, worktrees, filtering, tasks, TUI | Coexist; any import must remain proposed and one-way | You need a Git multi-repo manager and cross-repo task surface. |
| `gita` | personal Git repository registry, status dashboard, batch Git and shell commands | Coexist; importing clone configuration emitted by `gita freeze` is only a low-priority proposal | You want a lightweight Git dashboard and command fan-out from any directory. |
| `vcs2l` | multi-VCS discovery, commands, and reproducible repository-set import/export | Delegate; a Git-only `.repos` reader is only proposed | You need Git plus Mercurial, Subversion, or Breezy/Bazaar, or exact ROS-style repository sets. |
| Android Repo | manifest-controlled Git source trees, revision sync, topic branches, Gerrit | Delegate; resolved-inventory observation is only proposed | You need a large revision-controlled source tree or Gerrit workflow. |
| `west` | manifest-controlled Git workspaces and extensible embedded workflows | Delegate; resolved `west list` observation is only proposed | Zephyr-style revisions, groups, imports, build, flash, or debug workflows are central. |
| `uv` | Python projects, dependencies, lockfiles, project venvs, Python versions, tools | Use the shipped explicit Python adapter | The project needs Python dependency or environment ownership. |
| `direnv` | automatic directory-based environment loading | Stay compatible; do not absorb | Automatic environment changes on `cd` are desired. |
| `asdf` | tool version management | Stay compatible; do not absorb | Existing `.tool-versions` workflows already solve the requirement. |
| `devbox` | reproducible project shells and packages | Coexist; any Base adapter remains a future proposal | An isolated project shell is the primary outcome. |
| `nix` / `devenv` | reproducible environments, shells, services, tasks | Coexist through project-owned contracts; do not replace | Reproducibility and environment solving are the primary outcome. |
| `chezmoi` / `dotbot` | broad dotfile management | Stay compatible; do not absorb | Personal configuration, templating, or dotfile linking is the requirement. |
| `Taskfile` / `just` / `mise` tasks | project-local task definition and execution | Delegate project task implementation | Rich task logic inside a repository is the requirement. |
| `Brewfile` / `brew bundle` | declarative Homebrew bootstrap | Orchestrate; do not replace | Homebrew packages and applications are the requirement. |
| Docker / Docker Compose / Colima | containers and Compose-defined services | Orchestrate; do not replace | Container runtime or service topology is the requirement. |
| VS Code / Cursor | editor, extensions, and user settings | Use Base only for explicit readiness integration | Editor behavior is the requirement. |
| AI agent harnesses | live sessions, providers, sandboxing, collaboration | Provide portable context; do not become a runtime | Live agent execution or hosted collaboration is the requirement. |

## Tool-by-Tool Decisions

### `mise`

What it does well:

- converges OS packages, Git repositories, dotfiles, shell activation, macOS
  defaults and LaunchAgents, Linux systemd user services, login shell, tools,
  hooks, and a final bootstrap task through
  [`mise bootstrap`](https://mise.jdx.dev/bootstrap.html)
- reports declarative bootstrap state through text, `--json`, and `--missing`
  via [`mise bootstrap status`](https://mise.jdx.dev/cli/bootstrap/status.html)
- declares path-keyed Git repositories and safely clones or updates clean
  matching checkouts without forcing resets, as documented in
  [Bootstrap Repositories](https://mise.jdx.dev/bootstrap/repos.html)
- installs and pins project tools, loads project environment variables, and
  runs named tasks

What Base should borrow:

- the idea that project setup can be declarative and checked into the repo
- the idea that project-local tasks can be discoverable and explicit

What Base should not do:

- reimplement mise's machine-bootstrap, repository-convergence, dotfile,
  service, tool-version, environment, or task domains
- imply that Base is broader because mise is only a version manager

How Base should coexist:

- allow a Base-managed project to declare that it uses `mise.toml`
- keep the current shipped adapter explicit: use `mise trust --show` to check
  trust, `mise ls --missing --json` to check missing tools, `mise install`
  during setup, and `mise run` for declared task delegation
- on Ubuntu/Debian, install a missing `mise` CLI during `basectl setup <project>`
  only after the manifest declares a mise config and the caller has reviewed
  `--dry-run` output and passed `--yes`, subject to Base's
  [remote-installer policy](remote-installer-policy.md)
- support Go, Java, and other language runtimes through project-owned
  `.mise.toml` files instead of adding Base-owned package types for each
  language ecosystem
- leave `mise bootstrap` configuration and convergence owned by mise; Base does
  not currently run or interpret it

A future opt-in, read-only adapter could translate the JSON output from
[`mise bootstrap status --json`](https://mise.jdx.dev/cli/bootstrap/status.html)
into Base-native readiness evidence. That is a proposed follow-up, not shipped
behavior, and it should not make Base responsible for applying or rewriting
mise bootstrap configuration.

Choose mise instead of Base when declarative machine or project convergence is
the complete requirement. Add Base only when its semantic readiness, trust,
lifecycle, onboarding, or handoff contract provides additional value.

Current stance: strong coexistence, narrow shipped tool/task delegation, no
bootstrap replacement.

### Multi-Repository Managers

Generic inventory, discovery, clone or synchronization, status, and command
fan-out are established multi-repository capabilities. They overlap with Base
commands, but they are not Base's unique position.

#### `mani`

The official [`mani` introduction](https://manicli.com/) and
[command reference](https://manicli.com/commands/) document a declarative
`mani.yaml`, local and forge-backed repository discovery, clone and sync,
status, worktrees, filtering, a TUI, named tasks, and arbitrary parallel
commands. Its [configuration model](https://manicli.com/config/) also owns
imports, targets, task output, project environment, and remote reconciliation.

- Choose `mani` when a Git repository inventory, synchronizer, task runner,
  filtering model, or TUI is the primary need.
- Base may add semantic readiness and handoff after `mani` materializes the
  repository set, but it should not duplicate `mani` tasks, filters, source
  discovery, TUI, or worktree reconciliation.
- A one-way reader for selected `mani.yaml` project fields could be considered
  separately. It is proposed, not shipped; `mani.yaml` must remain authoritative
  and Base must not claim lossless round-trip export.

#### `gita`

The official [`gita` repository](https://github.com/nosarthur/gita) documents a
personal repository registry, side-by-side Git status, recursive discovery,
groups and contexts, clone/freeze workflows, and arbitrary batch Git or shell
commands from any directory.

- Choose `gita` for a lightweight Git dashboard and batch Git command surface.
- Base overlaps on local discovery, status, clone, and execution, but adds a
  participating-project contract rather than a general personal Git registry.
- A one-time import of clone configuration emitted by `gita freeze` could be
  explored only after demonstrated demand. It is proposed, not shipped; Base
  should not reproduce `gita` groups, contexts, coloring, or customizable Git
  delegation.

#### `vcs2l`

The Open Source Robotics Foundation's
[`vcs2l` documentation](https://ros-infrastructure.github.io/vcs2l/) and
[official package description](https://pypi.org/project/vcs2l/) document
recursive discovery and command execution for Git, Mercurial, Subversion, and
Breezy/Bazaar, plus YAML import, export, validation, deletion, and exact revision
capture through `vcs export --exact`.

- Choose `vcs2l` for ROS-compatible `.repos` workflows, multiple VCS types, or
  reproducible repository revision sets.
- Base assumes Git and should not add non-Git client semantics or become a
  recursive multi-VCS executor.
- A read-only `.repos` adapter could expose Git entries as expected Base
  repositories while reporting other VCS types as unsupported. It is proposed,
  not shipped, and the `.repos` file must remain authoritative.

#### Android Repo

Android's official [source-control overview](https://source.android.com/docs/setup/download/source-control-tools)
and [Repo command reference](https://source.android.com/docs/setup/reference/repo)
document a manifest repository, `.repo` client state, revision-aware `init` and
`sync`, cross-project `status` and `forall`, topic branches, downloads, uploads,
and Gerrit integration.

- Choose Repo for a large manifest-controlled Git source tree, pinned revisions,
  known-good builds, or Gerrit/topic-branch workflows.
- Base must not reproduce Repo XML manifest resolution, synchronization,
  mirrors, revision checkout, topic branches, or Gerrit behavior.
- A future read-only integration could consume Repo's resolved project view and
  apply Base readiness only to repositories that independently opt into Base.
  This is proposed, not shipped; Base should not parse and reinterpret Repo's
  source manifest as a competing authority.

#### `west`

Zephyr's official [`west` overview](https://docs.zephyrproject.org/latest/develop/west/index.html),
[basics](https://docs.zephyrproject.org/latest/develop/west/basics.html),
[built-in commands](https://docs.zephyrproject.org/latest/develop/west/built-in.html),
and [manifest reference](https://docs.zephyrproject.org/latest/develop/west/manifest.html)
document manifest-driven workspaces, revision-aware init and update, groups,
imports, submodules, compare/diff/status/list/forall/grep, and pluggable commands
used by Zephyr for build, flash, and debug.

- Choose `west` for Zephyr or embedded workflows where manifest revisions,
  project groups, imports, or domain extension commands are central.
- Base must not reproduce west manifest resolution, detached-revision update,
  group/import semantics, extension APIs, or build/flash/debug behavior.
- A future read-only adapter could consume resolved `west list` output and
  apply Base semantics only to opted-in repositories. It is proposed, not
  shipped, and `west.yml` must remain authoritative.

### `uv`

What it does well:

- manages Python project dependencies, environments, lockfiles, and workspaces
- runs scripts and project commands through Python-aware environments
- installs and runs Python command-line tools
- installs and switches Python versions
- provides a pip-compatible interface for Python package workflows

What Base should borrow:

- the idea that Python project environments should be explicit, inspectable, and
  close to the project contract
- the steady-state preference for one active project Python environment when a
  project has clearly opted into uv
- the discipline that lockfile and sync state should be surfaced clearly before
  Base mutates anything

What Base should not do:

- reimplement Python dependency resolution, lockfile generation, tool
  installation, or Python version management
- treat any `pyproject.toml` as proof that Base owns Python setup for the
  project
- run `uv sync`, enforce `uv.lock`, or route `basectl run` and `basectl test`
  through `uv run` without an explicit Base contract
- maintain a parallel Base-managed project venv as the long-term state once a
  project has explicitly adopted uv-managed Python

How Base should coexist:

- continue observing same-directory `pyproject.toml` through read-only
  diagnostics
- use the repo-local `.venv` only when a project explicitly declares
  `python.manager: uv`
- allow individual commands to declare `runner: uv` without requiring the whole
  project to use `python.manager: uv`
- report missing uv, missing `.venv`, or needed `uv sync` steps through
  Base-native check and doctor output when the project has opted into that
  contract
- on Ubuntu/Debian, bootstrap the `uv` tool during `basectl setup <project>`
  only after the manifest has explicitly opted into uv and the caller has
  reviewed `--dry-run` output and passed `--yes`
- invoke uv transparently, so dry-run output, logs, and diagnostics show the
  underlying `uv sync` or `uv run -- ...` command instead of hiding it behind
  Base

Current stance: strong coexistence. Base supports explicit uv-managed Python
projects through `python.manager: uv` and command-level uv execution through
`runner: uv`. Base still does not infer uv ownership from `pyproject.toml` or
`uv.lock` alone. See [Python Manifest Section](python-manifest.md) for the
current boundary.

### `direnv`

What it does well:

- hooks into the shell and automatically loads or unloads exported variables
  based on the current directory

What Base should borrow:

- very little directly
- the useful lesson is that environment activation should be explicit and
  inspectable, even if the trigger model differs

What Base should not do:

- adopt `cd`-driven magic as its primary activation story
- assume that directory changes are the same as project-context changes

How Base should coexist:

- users who already like `direnv` can keep using it for local convenience
- Base should not require `direnv`
- if a project uses `direnv`, Base may document that relationship, but should
  not center its activation model around it

Current stance: optional coexistence, no feature cloning.

### `asdf`

What it does well:

- manages tool versions through `.tool-versions`

What Base should borrow:

- mainly the lesson that tool version declarations belong close to the project

What Base should not do:

- become another version manager

How Base should coexist:

- if a project already uses `asdf`, Base can detect that and guide the user
- Base may eventually surface checks such as "this project expects `.tool-versions`"
- Base should not make `asdf` a first-class foundation if `mise` or another
  tool is the preferred modern path

Current stance: light coexistence, no direct feature work.

### `devbox`

What it does well:

- provides per-project development environments with packages, scripts, and
  shells

What Base should borrow:

- the idea that a project environment can be entered explicitly and treated as
  a deliberate workspace context

What Base should not do:

- reimplement project package solving or isolated shell construction

How Base should coexist:

- a Base project can declare that its environment is provided by `devbox`
- `basectl activate <project>` can eventually delegate to `devbox shell`
- `basectl setup` and `basectl check` can validate that the expected `devbox`
  workflow is available

Current stance: strong coexistence, Base as orchestrator rather than shell
builder.

### `nix` / `devenv`

What they do well:

- create reproducible shells and development environments
- model packages, processes, services, and tasks declaratively

What Base should borrow:

- the idea that project environments should be explicit, reproducible, and
  inspectable

What Base should not do:

- become a package manager, solver, or reproducibility platform
- chase Nix-level flexibility inside Base itself

How Base should coexist:

- Base can treat `nix develop` or `devenv shell` as project-level backends
- a project manifest can eventually say, in effect, "this project's shell
  comes from Nix/devenv"
- Base remains responsible for its participating-project readiness, trust, and
  handoff contract around the delegated environment

Current stance: strong coexistence, no attempt to replace Nix.

### `chezmoi`

What it does well:

- manages dotfiles, templating, and host-specific personalization

What Base should borrow:

- very little directly
- the useful lesson is that machine-local differences deserve an intentional
  home instead of being mixed into shared files

What Base should not do:

- become a full dotfile management system
- absorb secret management, templating, or broad home-directory ownership

How Base should coexist:

- Base-managed startup files can be installed through `chezmoi`
- Base-managed profile state lives in `~/.base.d/profile.conf`
- user-managed Base preferences live in `~/.baserc`
- users who already use `chezmoi` should be able to adopt Base cleanly

Current stance: light coexistence, distinct responsibilities.

### `dotbot`

What it does well:

- bootstraps dotfiles, especially symlinks and simple setup actions

What Base should borrow:

- nothing substantial

What Base should not do:

- turn itself into a generic dotfile-bootstrap tool

How Base should coexist:

- users may use `dotbot` to install or link Base-managed shell startup files
- Base does not need native `dotbot` integration beyond staying compatible with
  ordinary dotfile management and marked sections

Current stance: light coexistence, otherwise not a major design influence.

### `Taskfile` / `just`

What they do well:

- define and run named project tasks in a concise, readable way

What Base should borrow:

- the idea that projects should expose explicit, named operations such as
  `setup`, `test`, `lint`, and `run`

What Base should not do:

- become a general task runner for arbitrary recipes
- compete with mature task syntaxes when a project already has one

How Base should coexist:

- a Base project can declare that testing is done through `task test` or
  `just test`
- `basectl test <project>` should eventually delegate rather than duplicate
- Base should provide its declared project-command and readiness contract, not
  a second general task language

Current stance: strong coexistence, borrow the explicit-command philosophy.

### VS Code / Cursor

What they do well:

- provide the main editing environment for project work
- install language/tooling extensions through a scriptable CLI
- store user-level settings in a known macOS location

What Base should borrow:

- the idea that project development ergonomics should be declared and checked
- the ability to install extensions through the IDE's own CLI

What Base should not do:

- become a general IDE preference manager
- overwrite personal user settings
- manage every editor or fork before a real project needs it
- pin extension versions without a deliberate VSIX strategy

How Base should coexist:

- let projects declare supported IDE requirements through `base_manifest.yaml`
- install VS Code/Cursor through Homebrew casks when opted in
- install declared extensions through `code` or `cursor`
- add missing user-level settings without overwriting user values
- report missing app, CLI, extension, and settings state through check/doctor

Current stance: strong coexistence, Base as IDE-readiness orchestrator rather
than IDE owner.

### AI Agent Harnesses

This category includes AI coding CLIs, IDE agents, and meta-harnesses such as
Codex CLI, Claude Code, Cursor agents, Omnigent, Pi-like tools, and future agent
session managers.

What they do well:

- run live agent sessions against local repositories or hosted workspaces
- manage provider interaction, model selection, credentials, sandboxing, and
  approvals
- compose multiple agents or expose collaborative session views
- consume files, prompts, and project context prepared by other tools

What Base should borrow:

- the idea that AI work benefits from portable context, explicit policy, and
  durable handoff artifacts
- the idea that one workspace may use several agent harnesses over time, so
  Base-owned context should stay provider-neutral
- the discipline of making opt-in AI tooling visible through health checks
  instead of implying that every developer workflow needs it

What Base should not do:

- become a live agent runtime, session server, or multi-agent scheduler
- manage model/provider accounts, credentials, billing, or organization policy
- own OS-level sandboxing, approvals, or cost-control enforcement for agent
  sessions
- make any agent harness a default developer prerequisite
- vendor a third-party harness methodology when a smaller Base-native rule is
  enough

How Base should coexist:

- keep `--profile ai` explicit for AI developer tools, with allowlisted
  installers and read-only check/doctor diagnostics
- use `.ai-context/`, `basectl export-context`, and repo-local `AGENTS.md` as
  the portable context and guidance surfaces that any harness can consume
- use `basectl prompt` for maintained, repo-visible prompts without sending them
  to a provider
- prefer local, redacted handoff/report artifacts over hosted session sharing as
  Base's own collaboration boundary
- treat a machine-readable `basectl export-context` descriptor as a separate
  context-pack enhancement, not as part of any one harness integration
- evaluate new harnesses through this adapter quality bar before adding install,
  check, or wrapper behavior
- split concrete `--profile ai`, `export-context`, and report/handoff work into
  separate follow-up issues once the desired behavior is clear

Current stance: optional coexistence. Base should support AI harnesses through
portable context, explicit profile checks, and local handoff artifacts, not by
becoming a harness itself.

### `Brewfile` / `brew bundle`

What they do well:

- declare macOS package and app dependencies through Homebrew's own mechanism

What Base should borrow:

- a lot, but through orchestration rather than reimplementation
- on macOS, `Brewfile` is close enough to Base's workstation-bootstrap problem
  that it deserves first-class respect

What Base should not do:

- invent a parallel macOS package manifest when `Brewfile` already fits the job
- replace Homebrew's own package management behavior
- require Linux users to install Homebrew just because a project has a Brewfile

How Base should coexist:

- `basectl setup` should be able to run `brew bundle` on macOS
- Base manifests can point to one or more `Brewfile`s instead of inventing a
  new package DSL too early
- `basectl check` can validate that declared Homebrew dependencies are satisfied
  where Homebrew is a supported platform delegate
- on Ubuntu/Debian, Base should skip Brewfile setup/check as a warning and let
  platform-native delegates such as uv continue

Current stance: first-class macOS integration candidate, but still as an
orchestrator on top of Homebrew.

### Docker, Docker Compose, And Colima

What they do well:

- run containers, networks, volumes, and images through a mature container
  runtime
- describe multi-container local services through Docker Compose files
- provide a common service substrate for databases, queues, app dependencies,
  and project-local infrastructure
- offer multiple macOS runtime choices, including Docker Desktop and Colima

What Base should borrow:

- the idea that a project can declare named local services needed for daily
  development
- the idea that service preparation and health can be checked separately from
  service startup
- the Compose file as the project-owned source of truth for containers,
  networks, volumes, ports, and environment variables

What Base should not do:

- replace Docker, Docker Compose, Docker Desktop, or Colima
- invent a parallel container manifest
- hide the underlying Docker commands so thoroughly that troubleshooting becomes
  harder
- own image architecture compatibility, licensing, registry auth, or container
  health semantics beyond reporting useful diagnostics

How Base should coexist:

- Base can manage Docker CLI and Colima installation through ordinary
  Homebrew-backed `tool` artifacts
- project repositories should own their `docker-compose.yml` or
  `compose.yaml` files
- a future Base `docker-service` artifact can point at a Compose file and a
  service name, then orchestrate common lifecycle operations
- `basectl setup` can prepare services by running `docker compose pull` and,
  when requested by the manifest, `docker compose build`
- `basectl check` or `basectl doctor` can verify that Docker is installed, the
  daemon is reachable, the Compose file exists, and declared images or services
  are available
- `basectl activate <project>` can optionally start declared services for the
  activated project when the manifest opts into that behavior

A future manifest shape could look like this:

```yaml
artifacts:
  - type: tool
    name: colima
    version: latest

  - type: tool
    name: docker
    version: latest

  - type: docker-service
    name: postgres
    version: latest
    compose-file: docker-compose.yml
    service: postgres
    setup:
      pull: true
      build: false
    activate:
      start: true
    health:
      command: docker compose exec -T postgres pg_isready
      timeout-seconds: 30
```

This is intentionally a future shape, not the current manifest contract. The
exact field names should be finalized when a real project needs the feature.
The key design choice is that Base should orchestrate Compose; Docker Compose
should remain the source of truth for how services actually run.

Implementation notes for later:

- start with one Compose file per `docker-service` artifact
- require Compose paths to be relative to the project root and to stay inside
  that root
- support a single named service first; multi-service groups can come later
- keep setup preparation idempotent: `pull` and `build` should be safe to rerun
- make daemon checks explicit and friendly, especially for Colima users who may
  need `colima start`
- avoid automatic service startup during setup; activation is the better place
  for long-lived local services
- expose the underlying Docker command in logs before running it

Current stance: support Docker and Colima as installable tools now; design
`docker-service` as future Base orchestration over Docker Compose, not a
container abstraction owned by Base.

## Practical Guardrails for Base

These are the lines worth defending as Base grows.

### Base should own

- the opt-in Base participation and project contract
- semantic readiness findings, stable identifiers, and Base-native diagnostics
- explicit local trust for manifest-declared execution
- lifecycle and next-action guidance across prepare, verify, onboard, and handoff
- portable local evidence for the next person or coding agent
- the safety, transparency, and compatibility of commands Base itself ships

### Base should orchestrate rather than replace

- Homebrew and `brew bundle`
- `mise`
- `uv`
- `asdf`
- `task`
- `just`
- `devbox`
- `nix develop`
- `devenv`
- authoritative repository materialization and synchronization through `mani`,
  `gita`, `vcs2l`, Android Repo, or `west` when a workspace chooses one
- optional AI agent harnesses through explicit profile checks and context
  artifacts

Base should be able to operate after an external repository manager has
materialized a workspace. It should not require users to migrate the manager's
configuration into a second Base-owned source of truth.

### Base may integrate narrowly

- preserve the shipped `mise` and uv project adapters
- detect an external substrate only when a project or workspace opts in
- prefer read-only resolved state over reimplementing another manifest engine
- translate relevant external state into Base-native readiness evidence
- leave external configuration authoritative and show the underlying command

No adapter or import path for `mani`, `gita`, `vcs2l`, Android Repo, or `west`
is shipped today. Every such idea in this document requires a separate issue,
contract, and validation before it becomes a product claim.

### Base honestly overlaps

- repository inventory and local discovery
- repository materialization and clone planning
- aggregate status and machine-readable reports
- cross-repository command selection and execution
- declarative project or workspace manifests
- dry-run and next-action output

These primitives are useful parts of Base's execution surface. They are not the
reason Base is distinct; the differentiating composition is semantic readiness,
trust, lifecycle guidance, onboarding, and portable handoff evidence.

### Base should stay compatible with, but not absorb

- `direnv`
- `chezmoi`
- `dotbot`
- live AI agent session managers and meta-harnesses

### Base should explicitly avoid becoming

- another polyglot version manager
- another `cd`-triggered environment tool
- another general task runner
- another broad dotfile manager
- another reproducible package manager or dependency solver
- another generic multi-repository inventory, sync, status, or command runner
- a multi-VCS client
- a revision-pinned source-tree materializer or manifest resolution engine
- a second authority for `mani.yaml`, `.repos`, Repo manifests, or `west.yml`
- an agent runtime, hosted session-sharing service, sandbox, or provider-policy
  engine

## What This Means for Future Base Design

A good default rule is:

- if a capability strengthens Base's semantic readiness, trust, lifecycle,
  onboarding, or handoff contract, Base may own it
- if a capability is generic multi-repository inventory, materialization,
  synchronization, status, or command fan-out, Base should first delegate or
  consume resolved state
- if a capability is project-local and already solved well by a mature tool,
  Base should probably orchestrate it
- if a capability is personal-machine preference management, Base should stay
  compatible with it but not absorb it

That suggests the next generation of Base should lean toward:

- a small Base project manifest
- first-class support for pointing at existing artifacts such as:
  - `Brewfile`
  - `mise.toml`
  - `pyproject.toml`
  - `uv.lock`
  - `.tool-versions`
  - `Taskfile.yml`
  - `justfile`
  - `devbox.json`
  - `devenv.nix`
- umbrella commands that understand those artifacts well enough to orchestrate
  them without taking ownership of their full configuration models

## Comparison Maintenance

This document is the canonical capability and boundary matrix. Evaluator-facing
pages should summarize and link here instead of copying detailed feature lists.

- Perform a quarterly fast scan of the high-change `mise` and `mani` official
  documentation and changelogs.
- Revalidate all six bootstrap and multi-repository comparisons at least every
  six months.
- Revalidate immediately when Base changes workspace, bootstrap, import/export,
  or adapter claims, or when an adjacent tool materially changes those areas.
- Record an `Evidence checked: YYYY-MM-DD` line and link every material claim to
  a primary source.
- Keep proposed adapters in separate follow-up issues; a documentation refresh
  must not silently turn a proposal into shipped behavior.

## Review Trigger

We should revisit this document whenever Base starts to grow a feature that
looks like any of these:

- project-local tool version installation
- automatic environment changes on `cd`
- generalized task execution unrelated to workspace orchestration
- user-home dotfile templating or secret management
- dependency solving or package-resolution logic
- project topology complexity such as manifest inheritance, project groups,
  or sub-repository manifests
- generic repository inventory, synchronization, revision checkout, or command
  fan-out
- import or export of `mani.yaml`, clone configuration emitted by `gita freeze`,
  `.repos`, Repo manifests, or `west.yml`
- live agent-session orchestration, sandboxing, provider credentials, or hosted
  collaboration

Those are the places where Base is most likely to drift away from its real
strength. For project topology specifically, the constraints and rationale are
recorded in the "Project Model Scope" section of
[architecture.md](architecture.md).

## References

Official references that informed this boundary note. Bootstrap and
multi-repository capabilities were checked on 2026-07-14.

- `mise` bootstrap: <https://mise.jdx.dev/bootstrap.html>
- `mise` bootstrap CLI: <https://mise.jdx.dev/cli/bootstrap.html>
- `mise` bootstrap status CLI: <https://mise.jdx.dev/cli/bootstrap/status.html>
- `mise` repositories: <https://mise.jdx.dev/bootstrap/repos.html>
- `mani` introduction: <https://manicli.com/>
- `mani` usage: <https://manicli.com/usage/>
- `mani` commands: <https://manicli.com/commands/>
- `mani` configuration: <https://manicli.com/config/>
- `mani` changelog: <https://manicli.com/changelog/>
- `gita`: <https://github.com/nosarthur/gita>
- `vcs2l` documentation: <https://ros-infrastructure.github.io/vcs2l/>
- `vcs2l` source: <https://github.com/ros-infrastructure/vcs2l>
- `vcs2l` package: <https://pypi.org/project/vcs2l/>
- Android source-control tools: <https://source.android.com/docs/setup/download/source-control-tools>
- Android Repo command reference: <https://source.android.com/docs/setup/reference/repo>
- `west` overview: <https://docs.zephyrproject.org/latest/develop/west/index.html>
- `west` basics: <https://docs.zephyrproject.org/latest/develop/west/basics.html>
- `west` built-in commands: <https://docs.zephyrproject.org/latest/develop/west/built-in.html>
- `west` manifests: <https://docs.zephyrproject.org/latest/develop/west/manifest.html>
- `uv`: <https://docs.astral.sh/uv/>
- `direnv`: <https://direnv.net/>
- `asdf`: <https://asdf-vm.com/guide/introduction.html>
- `devbox`: <https://www.jetify.com/docs/devbox>
- `nix`: <https://nix.dev/>
- `devenv`: <https://devenv.sh/>
- `chezmoi`: <https://www.chezmoi.io/>
- `dotbot`: <https://github.com/anishathalye/dotbot>
- `Task`: <https://taskfile.dev/docs/getting-started>
- `just`: <https://just.systems/man/en/introduction.html>
- `Brewfile` / `brew bundle`: <https://docs.brew.sh/Brew-Bundle-and-Brewfile>
- Docker Compose: <https://docs.docker.com/compose/>
- Colima: <https://github.com/abiosoft/colima>
- `mise` tasks: <https://mise.jdx.dev/tasks/>
- Omnigent: <https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents>
