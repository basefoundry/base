# Base Architecture

## Overview

Base is an opinionated Mac-first development orchestrator. It provides a unified,
declarative foundation for bootstrapping a Mac development environment and managing
multiple projects through a single CLI interface. The current implementation support
contract is macOS. Linux is a future design target, while Windows support is not in
scope.

The governing philosophy: **solve your own problem elegantly first**. Base is built for
a specific workflow — multiple peer GitHub repositories under a shared parent directory,
each declaring their dependencies through a simple manifest, all managed through a
unified interface. If it works well for its author, it will work well for others with
similar constraints.

---

## Product Direction

Base's long-term product shape is a Mac-first control plane for multi-repo
developer workspaces. It should make a folder of sibling repositories
understandable, repeatable, diagnosable, and easy to onboard without becoming a
replacement for Homebrew, `mise`, Docker, GitHub CLI, IDEs, or project-owned
build systems.

The coherent product loop is:

```text
discover -> setup -> activate -> run -> test -> doctor -> fix -> onboard
```

Major features should strengthen that loop at the project or workspace level.
Unrelated commands belong outside the core product unless real use proves they
need Base's orchestration model.

---

## Core Principles

- **Opinionated over flexible** — Base makes decisions for you. Fewer choices means
  less complexity and easier maintenance. If you disagree with the decisions, use a
  different tool.
- **Problem-first** — technology choices follow real problems encountered during
  development, not the other way around.
- **Ship incrementally** — start minimal, use it yourself, let the tool grow organically
  through real use.
- **Idempotent by design** — running any setup command multiple times should produce
  the same result safely.
- **Orchestrate, do not replace** — Base should discover, sequence, validate,
  and explain mature tools rather than absorb their full configuration models.
- **Observable and diagnosable** — Base commands should make local state and
  failures understandable through clear output, stable finding IDs, JSON where
  useful, and inspectable logs.

---

## Repository Structure

Base is a public GitHub repository. All projects managed by Base are also GitHub
repositories, checked out as peers under a shared parent directory:

```
~/work/              ← shared workspace root
  base/              ← the Base repository itself
  myproject-a/       ← peer project with base_manifest.yaml
  myproject-b/       ← peer project with base_manifest.yaml
  banyanlabs/        ← peer project with base_manifest.yaml
```

Base discovers peer repositories by scanning the workspace root for repositories
that contain `base_manifest.yaml`.

---

## Shell Support

Base supports two shells:

- **bash** — primary scripting shell. All orchestration scripts run in bash. Default for
  all base internals.
- **zsh** — supported for interactive use. Power users who prefer zsh for their
  interactive shell are accommodated.

Fish, tcsh, ksh, and other shells are explicitly out of scope for now. If real demand
emerges, support can be added later.

---

## Command Surface — `basectl` as Control Plane

The most important command-surface decision in Base: **the product is Base, the
control-plane command is `basectl`**.

`basectl` is the public entrypoint. It is a normal executable command that
establishes the Base runtime before dispatching to Bash scripts or future Python
layers. This keeps the product name and the control-plane action separate:

- `basectl setup`
- `basectl check`
- `basectl doctor`
- `basectl update-profile`
- `basectl projects list`
- `basectl workspace status`
- `basectl activate`
- `basectl run`
- `basectl test`
- `basectl build`
- `basectl demo`
- `basectl release`
- `basectl logs`

Shebang-based Bash scripts can also use:

```bash
#!/usr/bin/env basectl
```

In that mode, `basectl` wraps the script in the Base environment, sources it,
and calls its `main` function.

The current dispatch and runtime contract is documented in
[execution-model.md](execution-model.md).

---

## Project Activation Model — Subshell Design

### Why Subshells

Activating a project environment means setting shell variables, aliases, functions, and
activating a Python virtual environment. The naive approach of activate/deactivate
(like Python venv) does not scale to the full richness of a shell environment. Tracking
and restoring arbitrary shell state on deactivation is complex and error-prone.

The solution: **spawn a Bash runtime shell** when activating a project. The
project environment lives inside that shell. The user works in that shell. When
done, they `exit` (or Ctrl-D) and return to their base shell. No deactivation
logic required. No state restoration complexity.

This does not require a distinct shell function. A normal `basectl activate <project>`
command can validate the target and launch the Bash runtime shell.

### Activation Flow

```
basectl activate myproject
  ↓
1. Look up BASE_HOME, resolve the workspace root, and scan known projects
2. Validate myproject exists and has a valid manifest
3. Set BASE_PROJECT=myproject
4. Spawn a new Bash runtime shell
5. In that shell: load the Base runtime and user Bash startup with guardrails
6. In that shell: activate the project's Python virtual environment
7. In that shell: source manifest-declared activate.source scripts
8. Update the prompt to reflect the active project
9. User works in the Bash runtime shell
10. User exits → returns to base shell, prompt resets
```

### `basectl activate` — Intelligence

- Takes a project name as argument (not a directory path)
- Works from any current directory — the user does not need to be in the project folder
- Base locates projects from explicit `--workspace`, configured `workspace.root`,
  or the parent of `$BASE_HOME` as a source-checkout fallback
- Validates that the target is a recognized Base project with a valid manifest

---

## Shell Environment Layers

Base separates ordinary shell startup from Base runtime activation.

### Layer 1 — Dotfile Integration

Applied by the user's normal Bash/Zsh startup files after running
`basectl update-profile`.

Contains:
- login-shell handoff for Bash (`~/.bash_profile` sources `~/.bashrc` with guardrails)
- interactive Bash/Zsh guardrails
- `BASE_HOME` derived from the sourced Base snippet
- Base `bin/` added to `PATH` so `basectl` is available after login
- optional sibling `base-platform-tools/bin` added to `PATH` when present
- optional shell defaults when the user runs `basectl update-profile --defaults`

This layer must not source `base_init.sh` and must not establish the full Base
runtime contract. It is only about Bash/Zsh startup behavior plus launcher
availability.

### Layer 2 — Base Runtime Environment

Applied when the user invokes `basectl`, `basectl activate <project>`, or
`basectl /path/to/script.sh`. Invoking `basectl` with no arguments in a terminal
starts the Base project runtime while preserving the caller's current
directory.

Contains:
- exported Base path contract such as `BASE_HOME`, `BASE_BIN_DIR`,
  `BASE_BASH_LIB_DIR`, `BASE_BASH_LIBS_DIR`, and `BASE_BASH_LIBS_SOURCE`
- OS and host metadata such as `BASE_OS`, `BASE_PLATFORM`, and `BASE_HOST`
- Base's Bash standard library
- `import_base_lib` for convention-based Base Bash library imports from the
  resolved reusable Bash library root
- PATH additions for Base's own executable entrypoints
- optional PATH additions for the local Base Platform Tools companion repo

This layer is established by `base_init.sh`, which is sourced only through the
`basectl` command path. The canonical variable reference and mutability policy
live in [Runtime Environment](runtime-environment.md). The standalone
`base-bash-libs` install path and post-migration contract live in
[Base Bash Libraries](base-bash-libs.md).

### Layer 3 — Project-Specific Environment

Applied inside the project subshell when `basectl activate <project>` is run.

Contains:
- Project-specific PATH additions
- Project-specific environment variables
- Project-specific aliases and functions
- Project-specific Python virtual environment activation
- Manifest-declared `activate.source` scripts
- `BASE_PROJECT` updated to the project name

Project-specific settings layer on top of the Base runtime environment. Settings
not overridden by the project inherit from Base. When the subshell exits, the
project layer disappears naturally — no explicit deactivation needed.

### Dotfile Management

Base updates the user's real dotfiles by managing small marked sections. The preferred adoption model is:

```bash
basectl update-profile
```

By default, Base updates all four files:

| Dotfile | Base snippet | Purpose |
|---|---|---|
| `~/.bash_profile` | `lib/shell/bash_profile` | Login Bash bridge into `~/.bashrc` |
| `~/.bashrc` | `lib/shell/bashrc` | Interactive Bash startup |
| `~/.zprofile` | `lib/shell/zprofile` | Thin Zsh login startup |
| `~/.zshrc` | `lib/shell/zshrc` | Interactive Zsh startup |

Base does not symlink over the user's dotfiles and does not own content outside its clearly marked managed sections. The markers are intentionally explicit, for example:

```bash
# >>> base: bashrc managed >>>
# <<< base: bashrc managed <<<
```

Optional Base shell defaults are enabled explicitly with `basectl update-profile --defaults`.

---

## Directory Change Behavior

**Changing directory does not trigger environment changes.**

This is a deliberate design decision. Auto-activating environments on `cd` is confusing
because the intent behind a `cd` is ambiguous — the user may be casually navigating,
not intending to switch project context. Background logic running on every `cd` also
slows the shell and is error-prone.

The only things that change on `cd`:
- `$PWD` updates (built-in shell behavior)
- The directory portion of the prompt updates
- The git branch portion of the prompt updates dynamically (see Prompt section)

Everything else stays stable until the user explicitly runs `basectl activate <project>`.

---

## Prompt Design

The prompt shows three things, always:

```
[myproject: main] ~/projects/myproject/src $
```

| Element | Source | Behavior |
|---|---|---|
| Project name | `$BASE_PROJECT` | Static — set at activation, stays until subshell exits |
| Git branch | Dynamic query | Updates on every prompt render |
| Current directory | `$PWD` | Updates on every `cd` |

### Project Name in Prompt

`BASE_PROJECT` is set by `basectl activate`. When the user invokes `basectl`
with no arguments in an interactive terminal, Base discovers the nearest
`base_manifest.yaml` above the current directory and activates that project
while preserving the current directory. If no manifest is found, it falls back
to the `base` project.

Once the subshell starts, `BASE_PROJECT` stays fixed until the shell exits. It
does not change dynamically when the user later runs `cd`.

### Git Branch in Prompt

The git branch is **not stored in a variable**. It is queried dynamically each time the
prompt renders. This ensures the prompt reflects reality when the user runs `git
checkout` to switch branches inside the subshell.

Implementation in PS1:

```bash
_base_git_branch() {
  git symbolic-ref --quiet --short HEAD 2>/dev/null ||
    git rev-parse --short HEAD 2>/dev/null
}

PS1='[${BASE_PROJECT}: $(_base_git_branch)] \w $ '
```

Key decision: the branch is queried from the current directory at prompt render
time. This keeps the prompt honest when a Base runtime shell is started from a
nested project directory or when the user moves between repositories inside the
same shell.

### Why Not Show Python Venv in Prompt

The project name in the prompt implies the Python virtual environment — if a project is
active, its venv is active. Showing both would be redundant. The prompt stays clean.

---

## Python Virtual Environments

### Base Venv

- Created once during `basectl setup`
- Lives at `~/.base.d/base/.venv`
- Used to run Base's own Python orchestration code (manifest parsing, project discovery,
  etc.)
- Not activated in the user's interactive shell by default — it runs internally when
  Base needs it

### Project Venv

- Created per project during `basectl setup <project>` or `basectl setup` when scanning
  all projects
- Lives at `~/.base.d/<project>/.venv`
- Activated automatically when `basectl activate <project>` spawns the project subshell
- Deactivated automatically when the subshell exits

### Key Distinction

Only one Python venv can be active at a time. Base venv runs quietly in the background
for Base's own tools. Project venv is what the user interacts with. The two never
conflict because Base venv is not surfaced in the interactive shell.

---

## Project Manifest

Each Base-managed project declares its dependencies in a YAML manifest file at the
project root. Base reads this manifest to know what to install and configure.

File: `base_manifest.yaml`

Current and planned structure:

```yaml
schema_version: 1

project:
  name: myproject

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

`schema_version` is a manifest compatibility marker. Missing values are treated
as schema version `1`, which keeps existing project manifests valid. Base rejects
manifests with a schema version newer than the installed Base understands so
future team-facing manifest expansion can fail with a clear upgrade message
instead of ambiguous parser behavior.

The Python layer interprets this declarative manifest and translates it into
orchestration actions. The design rule is delegation-first:

- Use Homebrew's own `Brewfile`/`brew bundle` flow for ordinary macOS packages.
- Use `mise` for tool versions, language runtimes, environment variables, and
  future tasks when a project opts into it. Base runs `mise install` during
  setup and does not reimplement mise's version management.
- For Go and Java projects, put runtime pins such as `go = "1.22"` and
  `java = "temurin-21"` in `.mise.toml`. Keep system tools in `Brewfile`, Go
  dependencies in `go.mod`/`go.sum`, and Java dependencies in Maven or Gradle
  project files. Base should orchestrate those contracts rather than add
  generic language package artifact types.
- Use a project-owned `test` contract for `basectl test <project>` delegation.
  Projects can declare either `test.command` for a shell command or `test.mise`
  for a `mise run <task>` delegation. Extra arguments after `basectl test
  <project> --` are passed through to the delegated command.
- Use a project-owned `commands` map for additional named commands that
  `basectl run <project> <command>` can execute from the project root. These
  commands use the same Base project environment and virtual environment
  contract as `basectl test`; the command name `test` is reserved for the
  top-level `test` contract.
- Use `health.required_env` for local environment contracts that `basectl check`
  and `basectl doctor` should validate without exposing secret values.
- Use `health.required_ports` for local TCP port contracts that should be
  explicitly `listening` or `free`. Base checks connection state only; it does
  not mutate local services, inspect process ownership, or replace future
  Docker Compose health checks.
- Use `activate.source` for explicit project activation scripts that need to
  affect the interactive runtime shell, such as local environment loading,
  aliases, or functions. Source paths must be relative to the project root and
  must resolve inside that root.
- Let Base own the project virtual environment and Base-aware package
  reconciliation.
- Do not run arbitrary project setup hooks until Base has a clear safety
  contract for dry-run behavior, interactivity, setup diagnostics, and broader
  side effects. See [setup-hooks.md](setup-hooks.md) for the setup no-hooks
  decision and future reconsideration criteria.

Base owns the curated tool artifact registry only for things it must manage
directly. The current registry is `cli/python/base_setup/registry.py`.

The optional top-level `brewfile` field delegates ordinary Homebrew dependencies
to Homebrew's native `brew bundle` flow. The path is relative to the project root
and must stay inside the project. Base runs `brew bundle --file=<path>` during
setup before reconciling Base-managed artifacts.

`python-package` artifacts are pass-through PyPI package names and install into
the project virtual environment at `~/.base.d/<project>/.venv`. Base's own
project venv is therefore
`~/.base.d/base/.venv`. The wrapper `bin/base-wrapper` runs Python packages
through that project-scoped venv.

A structured `python:` manifest section owns Python project runtime policy.
`python.manager: uv` delegates environment setup to uv. `python.requires_python`
lets a project select a supported Python 3.10 through 3.13 minor for
Base-managed virtualenv creation, while check/doctor distinguish unsupported
requests from supported-but-unavailable interpreters. See
[python-manifest.md](python-manifest.md) for the current contract and migration
boundary.

Homebrew-managed `tool` artifacts currently support `version: latest`. If a
project requests a pinned Homebrew version, setup fails clearly instead of
silently installing a different version. For `version: latest`, check and doctor
report installed-but-outdated Homebrew packages, and setup upgrades them. New
ordinary Homebrew tools should prefer Brewfile delegation over registry growth.
Richer version conflict handling across projects is a later iteration, not part
of the initial build.

Default artifacts can be marked with `bootstrap: true` when they are required to
run Base's Python CLI layer inside a project virtual environment before the rest
of that project's artifacts are reconciled. In the current default manifest,
`click` and `PyYAML` carry this marker.

Artifact install commands keep stdout attached to the terminal so long-running
tools such as `brew` and `pip` remain live and readable while setup runs. Base's
persistent log records the command intent and captures stderr on failures. If
Base later needs full install transcripts, it should add tee-style streaming so
users still see progress while stdout is also preserved in the log.

---

## Project Model Scope

Base's project model is deliberately flat and simple: **one repository equals one
project, and all projects are peer siblings under a shared parent directory.**

This constraint is a feature, not a limitation. It keeps the manifest readable,
the discovery logic fast, and the activation model unambiguous. The four most
common requests to extend this model — and why each is out of scope:

### Parent-child manifest inheritance

A child project that inherits its parent's manifest looks attractive for sharing
common artifacts across related projects. Base already has two manifest layers
that address this need: `lib/base/default_manifest.yaml` for shared bootstrap
defaults and each project's own `base_manifest.yaml`. A third layer creates an
inheritance chain where diagnosing "why is this artifact installed?" requires
tracing provenance across files rather than reading one manifest. It also
introduces discovery-order coupling — a child is broken in a non-obvious way
when its parent is not checked out.

The right escalation path: if the need is for shared Homebrew tools, use
Brewfile delegation. If the need is for shared Python packages, declare them in
each project's manifest. If Base ever needs an org-level layer, introduce a
workspace-level manifest at the parent directory rather than reaching for
inheritance.

### Project groups sharing a manifest

If two projects share a manifest they are probably not two separate projects —
they are one project with two source trees. A group concept introduces a new
entity (group vs. project vs. member) with no clear semantics for which project
gets activated when the user runs `basectl activate`. Closely coupled components
should either be treated as one project or kept as independent projects that
happen to declare the same artifacts.

### Multiple projects within a single repository

Scanning a repository tree for nested `base_manifest.yaml` files makes
`basectl projects list` traverse potentially thousands of directories. It also
conflicts with the activation model — `basectl activate <project>` assumes a
project root is a repository root, so one active context maps cleanly to one
directory. Sub-repo manifests blur that mapping in ways that affect the prompt,
PATH manipulation, and virtual environment selection.

What already works: `discover_manifest` in `lib/python/base_cli/paths.py` walks
upward from the current directory, so a manifest anywhere in a repository subtree
is found when `basectl` is invoked from that directory. The gap is only in
`basectl projects list`, which enumerates workspace siblings rather than trees.
If a specific monorepo layout genuinely needs enumeration, the least-invasive
path is to scan exactly one additional level and require explicit opt-in from a
parent manifest rather than auto-discovering everything.

### Workspace manifest

A workspace manifest is a team-shared repo-set contract. It is distinct from
each project's `base_manifest.yaml`: the workspace manifest says which
repositories should belong together, while project manifests say how each
repository participates in Base.

Workspace commands operate on discovered local projects by default. Configuring
`workspace.manifest` or supplying `--manifest <path>` adds expected-repository
awareness without changing the default discovered-project behavior. The
command-line manifest takes precedence over user config. See
[Workspace Manifest](workspace-manifest.md).

### Caching project definitions

Base keeps project discovery flat: it scans direct children of the workspace
root for `base_manifest.yaml` files instead of traversing repository trees. That
keeps discovery predictable, but repeated YAML parsing still shows up in
project-aware commands and shell completion.

The implemented cache is intentionally narrow. Base stores discovered project
metadata under the runtime cache root in `projects/`, keyed by the resolved
workspace path. On each discovery run it still checks the immediate workspace
children, but it reuses cached project names and paths when the manifest path,
mtime, and size set is unchanged. A new checkout, manifest edit, or manifest
removal changes that key data and forces a fresh parse.

This cache is an optimization, not an authority. The manifest files remain the
source of truth, and corrupt or unwritable cache files are ignored.

---

## Workspace Operations

Base's larger value is managing a full workspace, not just one repository. The
workspace command surface should make local state visible before it mutates many
projects.

Current workspace-oriented commands include:

```bash
basectl projects list
basectl workspace status
basectl workspace check
basectl workspace doctor
basectl workspace clone
basectl workspace pull
basectl workspace init
basectl workspace configure
```

Workspace commands are read-first and mutate only through explicit init, clone,
pull, or configure commands. `basectl workspace status` reports project manifest state,
virtual environment state, and Git state across discovered projects, including
invalid manifests without stopping the whole scan. With `workspace.manifest` or
`--manifest <path>`, workspace commands also report missing required
repositories, missing optional repositories, and discovered Base-managed
projects outside the expected repo set. `basectl workspace check` and `basectl
workspace doctor` run project checks and diagnostics across discovered
projects. `basectl workspace clone` materializes missing expected repositories
only when invoked directly. `basectl workspace pull` updates only the local
workspace manifest after validating an explicit or configured source. `basectl
workspace init` bootstraps a workspace from a workspace configuration repository
and can materialize member repositories. `basectl workspace configure` applies
the existing `repo configure` repair path across discovered Base-managed
workspace repositories. JSON output is part of the status/check/doctor contract
so automation and future CI smoke checks can use the same data.

Future workspace commands should follow the same principles:

- start with read-only status, check, and doctor behavior
- require explicit commands and dry-run paths before mutating many repositories
  or local workspace metadata
- treat partial failure as normal in multi-repo workspaces
- keep sibling repositories under a shared workspace root as the default
  discovery model
- report machine-readable summaries early

---

## Doctor And Observability

`basectl doctor` is a core trust-building feature. It should explain what is
wrong, why it matters, whether Base can fix it, and the safest next command.
Doctor output must stay non-mutating unless a future explicit fix command is
designed with dry-run behavior.

Doctor findings use stable identifiers documented in
[Doctor Finding IDs](doctor-findings.md). Automation and runbooks should match
on those IDs instead of human-readable messages.

Base should also remain locally observable. `basectl logs` exposes recent Base
CLI runtime logs from the Base cache root, and `basectl history` lists the
structured local command-history index without sending telemetry anywhere.
Useful command metadata includes the command, target project or workspace,
start and end time, exit code, manifest version where relevant, external tools
invoked, and log file paths.

The goal is explainability, not surveillance. Base should help users understand
what happened on their own machine.

---

## Mac Bootstrap Sequence

On a fresh Mac, installation and first-run setup use this sequence:

1. Check for Homebrew — install if missing
2. Check for Xcode CLI tools — install if missing
3. Install Python (target version) via Homebrew
4. Create Base's own virtual environment at `~/.base.d/base/.venv`
5. Install Base's Python bootstrap dependencies into `~/.base.d/base/.venv`
6. After `basectl setup` finishes, explicitly run `basectl update-profile` as a
   separate one-time shell-profile step; run it again only when updating
   Base-managed shell dotfiles
7. Scan the parent directory for peer repos with base manifests
8. For each project setup target, seed the project venv with `bootstrap: true`
   default artifacts, then run project artifact reconciliation through
   `base-wrapper --project <project>`

Homebrew installation follows Homebrew's official `install/HEAD/install.sh`
bootstrap command. That means Base intentionally trusts Homebrew's mutable
installer entry point instead of pinning a commit SHA. Pinning would reduce
installer mutability, but would also make Base responsible for tracking
Homebrew installer updates and could diverge from Homebrew's documented support
path. Environments with stricter supply-chain policy should preinstall Homebrew
through managed workstation provisioning before invoking `basectl setup`.

---

## GitHub and Repository Conventions

- Base uses a public GitHub repository at `basefoundry/base`.
- GitHub Issues are the official product backlog for bugs, feature requests,
  release work, maintenance, and documentation follow-up.
- `basectl release` manages annotated tags and GitHub Releases for Base using
  the manifest-owned release metadata in `base_manifest.yaml`.
- The Homebrew tap at `basefoundry/homebrew-base` owns the formula that installs
  published Base releases.
- Homebrew tap updates happen after each GitHub Release and remain a manual
  handoff. `basectl release` prints the required tap follow-up when the project
  manifest declares Homebrew metadata.

---

## Adoption Signals

Base should measure product readiness through concrete local workflows:

- one-command install works on a clean supported macOS machine
- a public demo project can be cloned, set up, checked, tested, diagnosed, and
  demonstrated by Base
- a technically adjacent user can complete guided onboarding without reading
  private internal notes
- multiple project types are supported through adapters instead of
  special-case code
- `doctor` identifies and explains the most common local failure modes
- JSON output is stable enough for automation and CI smoke checks

These are not analytics goals. They are acceptance signals for whether Base is
becoming useful beyond one personal machine.

---

## Utility Scripts and Extras

Base ships with a small collection of utility scripts useful for day-to-day Mac
development:

- Shell helper functions for common operations
- Python library utilities for unified CLI development (shared across Base-managed
  projects)
- Git convenience helpers (branch management, PR workflows)
- Potentially: a base-provided Python CLI framework so that projects built within the
  Base ecosystem share a consistent CLI style

These extras emerge organically from real needs — they are not designed upfront.

---

## What Base Is Not

- Not a replacement for Docker or dev containers — those solve a different problem
  (containerization). Base is Mac-native and lightweight.
- Not broadly cross-platform today — macOS is the current support contract, Linux is a future target, and Windows is explicitly out of scope.
- Not a universal package manager — Homebrew handles that. Base orchestrates on top
  of Homebrew.
- Not trying to solve every edge case — version conflict handling across projects,
  language runtimes beyond Python, and container integration are future considerations.

---

## Settled Design References

Several questions from the early architecture pass now have dedicated reference
documents:

- Workspace manifest location, trust, clone, pull, and team-onboarding policy
  are covered by [Workspace Manifest](workspace-manifest.md).
- Non-Python projects stay inside the Base manifest command contract and use
  project-owned tools through `basectl run`, `basectl test`, `mise`, or direct
  shell commands. See [Tool Boundaries](tool-boundaries.md) and
  [Python Manifest Section](python-manifest.md).
- Docker and dev container integration remain coexistence and orchestration
  topics rather than Base-owned container management. See
  [Tool Boundaries](tool-boundaries.md).

Remaining questions should be tracked as GitHub Issues when they become concrete
enough to affect a project or release.

---

## Relationship to Banyanlabs

Base is the prerequisite for banyanlabs. Banyanlabs (a multi-cloud, polyglot DevOps
learning environment) will be a Base-managed project — it will have a base manifest
declaring all its infrastructure tool dependencies. Base handles the bootstrapping.
Banyanlabs handles the learning environment. A Banyanlabs-specific installer can
bootstrap or locate Base, clone the project, and call `basectl setup` with
friendlier product-specific messaging. See [Project Installers](project-installers.md)
for that boundary. Base must ship first.

---

*This is a living document. See [CHANGELOG.md](../CHANGELOG.md) for the dated
history of architecture and command-surface changes.*
