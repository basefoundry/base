# Base Ecosystem Boundaries

This document captures how Base should relate to other popular developer tools.
Its purpose is not to compete with everything in the ecosystem. Its purpose is
to help Base stay sharp about what it owns, what it can orchestrate, and what
it should leave alone.

When we evaluate another tool, we ask three questions:

1. Does Base need to borrow anything from this tool and build that capability
   directly into itself?
2. Can Base coexist with this tool so the combination is better than Base
   alone?
3. Is the tool far enough from Base's center of gravity that we do not need to
   bother about it?

The answers are often mixed. A tool may be worth learning from without being
something Base should reimplement. A tool may also be worth supporting without
becoming a hard dependency.

## Base's Center of Gravity

Base is strongest when it stays focused on these responsibilities:

- Mac-first workstation bootstrap
- shared shell startup and shell-environment layering
- peer-repo workspace discovery under a shared parent directory
- workspace-level orchestration across sibling repositories
- shared execution conventions through `basectl` and a future `base-python-wrapper`
- a small project manifest and command contract for participating repositories

Base gets weaker when it drifts into becoming any of these:

- a general tool version manager
- an automatic directory-based environment loader
- a full dotfile manager
- a generic task runner
- a full reproducible package manager or environment solver

## Quick Decision Matrix

| Tool | What it primarily owns | Build directly into Base? | Coexist with Base? | How much to care |
|---|---|---|---|---|
| `mise` | tool versions, env vars, tasks | Partially borrow ideas, do not reimplement wholesale | Yes, strongly | High |
| `direnv` | automatic directory-based env loading | No | Yes, optionally | Medium |
| `asdf` | tool version management | No | Yes, lightly | Medium |
| `devbox` | reproducible project shells and packages | No | Yes, strongly | High |
| `nix` / `devenv` | reproducible environments, shells, services, tasks | No | Yes, strongly | High |
| `chezmoi` | dotfile management | No | Yes, lightly | Medium |
| `dotbot` | dotfile bootstrap and symlinks | No | Yes, lightly | Low |
| `Taskfile` / `just` | task running | No | Yes, strongly | High |
| `Brewfile` / `brew bundle` | declarative Homebrew bootstrap | Yes, by orchestration rather than replacement | Yes, strongly | High |
| Docker / Docker Compose / Colima | containers, Compose-defined local services | Partially, as orchestration only | Yes, strongly | High |
| `mise` tasks | project-local task running inside `mise` | No | Yes, strongly | Medium |
| VS Code / Cursor | IDE app, extensions, and user editor settings | Partially, as workstation bootstrap only | Yes, strongly | High |

## Tool-by-Tool Decisions

### `mise`

What it does well:

- installs and pins tool versions per project
- loads project-specific environment variables
- runs named tasks from one CLI

What Base should borrow:

- the idea that project setup can be declarative and checked into the repo
- the idea that project-local tasks can be discoverable and explicit

What Base should not do:

- reimplement a broad tool version manager
- become a generic env-var loader plus task runner for every language stack

How Base should coexist:

- allow a Base-managed project to declare that it uses `mise.toml`
- let `basectl setup` or `basectl check` invoke `mise install`, `mise doctor`, or
  `mise run ...` when that is the project's chosen substrate
- keep Base at the workspace-orchestration layer, not the per-language tool
  installation layer

Current stance: strong coexistence, selective borrowing, no wholesale
reimplementation.

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
- Base remains responsible for workspace discovery and umbrella orchestration

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
- Base should provide the workspace-wide orchestration and selection layer

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

How Base should coexist:

- `basectl setup` should be able to run `brew bundle` where appropriate
- Base manifests can point to one or more `Brewfile`s instead of inventing a
  new package DSL too early
- `basectl check` can validate that declared Homebrew dependencies are satisfied

Current stance: first-class integration candidate, but still as an orchestrator
on top of Homebrew.

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

### `mise` tasks

What they do well:

- keep project tasks close to `mise`-managed tools and env vars

What Base should borrow:

- mostly the same lesson as Taskfile and `just`: explicit named tasks are good

What Base should not do:

- create a second parallel task system just because a project chose `mise`

How Base should coexist:

- if a project uses `mise run test`, Base should be happy to delegate to it
- Base should care about the workspace command contract, not whether the task
  backend is `mise`, `task`, `just`, shell, or Python

Current stance: strong coexistence, little direct feature work.

## Practical Guardrails for Base

These are the lines worth defending as Base grows.

### Base should own

- workspace discovery across peer repositories
- the shared project manifest and command contract
- umbrella commands such as `basectl setup`, `basectl check`, `basectl projects list`,
  `basectl test`, and future `basectl activate`
- shared shell startup and shell-environment layering
- shared execution conventions for Bash and Python wrappers
- workspace-level health checks and diagnostics

### Base should orchestrate rather than replace

- Homebrew and `brew bundle`
- `mise`
- `asdf`
- `task`
- `just`
- `devbox`
- `nix develop`
- `devenv`

### Base should stay compatible with, but not absorb

- `direnv`
- `chezmoi`
- `dotbot`

### Base should explicitly avoid becoming

- another polyglot version manager
- another `cd`-triggered environment tool
- another general task runner
- another broad dotfile manager
- another reproducible package manager or dependency solver

## What This Means for Future Base Design

A good default rule is:

- if a capability is workspace-level and cross-repo, Base should probably own it
- if a capability is project-local and already solved well by a mature tool,
  Base should probably orchestrate it
- if a capability is personal-machine preference management, Base should stay
  compatible with it but not absorb it

That suggests the next generation of Base should lean toward:

- a small Base project manifest
- first-class support for pointing at existing artifacts such as:
  - `Brewfile`
  - `mise.toml`
  - `.tool-versions`
  - `Taskfile.yml`
  - `justfile`
  - `devbox.json`
  - `devenv.nix`
- umbrella commands that understand those artifacts well enough to orchestrate
  them across a whole workspace

## Review Trigger

We should revisit this document whenever Base starts to grow a feature that
looks like any of these:

- project-local tool version installation
- automatic environment changes on `cd`
- generalized task execution unrelated to workspace orchestration
- user-home dotfile templating or secret management
- dependency solving or package-resolution logic

Those are the places where Base is most likely to drift away from its real
strength.

## References

Official references that informed this boundary note:

- `mise`: <https://mise.jdx.dev/>
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
