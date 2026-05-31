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

---

## Repository Structure

Base is a public GitHub repository. All projects managed by Base are also GitHub
repositories, checked out as peers under a shared parent directory:

```
~/projects/          ← shared parent directory
  base/              ← the Base repository itself
  myproject-a/       ← peer project with a base manifest
  myproject-b/       ← peer project with a base manifest
  banyanlabs/        ← peer project with a base manifest
```

Base discovers peer repositories by scanning the parent directory for repos that contain
a base manifest file.

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
- `basectl activate`
- `basectl test`

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

The solution: **spawn a subshell** when activating a project. The project environment
lives inside the subshell. The user works in that subshell. When done, they `exit` (or
Ctrl-D) and return to their base shell. No deactivation logic required. No state
restoration complexity.

This does not require a distinct shell function. A normal `basectl activate <project>`
command can validate the target and launch the configured subshell.

### Activation Flow

```
basectl activate myproject
  ↓
1. Look up BASE_HOME, resolve the workspace root, and scan known projects
2. Validate myproject exists and has a valid manifest
3. Set BASE_PROJECT=myproject
4. Spawn a new subshell
5. In the subshell: load the Base runtime and user Bash startup with guardrails
6. In the subshell: activate the project's Python virtual environment
7. In the subshell: source manifest-declared activate.source scripts
8. Update the prompt to reflect the active project
9. User works in subshell
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
- exported Base path contract such as `BASE_HOME`, `BASE_BIN_DIR`, and `BASE_BASH_LIB_DIR`
- OS and host metadata such as `BASE_OS` and `BASE_HOST`
- Base's Bash standard library
- `import_base_lib` for convention-based Base Bash library imports
- PATH additions for Base's own executable entrypoints

This layer is established by `base_init.sh`, which is sourced only through the
`basectl` command path.

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
# --- BEGIN base bashrc MANAGED SECTION - DO NOT EDIT ---
# --- END base bashrc MANAGED SECTION - DO NOT EDIT ---
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
- Lives inside the project directory (e.g., `.venv/`)
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

activate:
  source:
    - .base/activate.sh

test:
  command: pytest tests/
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
- Use `health.required_env` for local environment contracts that `basectl check`
  and `basectl doctor` should validate without exposing secret values.
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

A structured `python:` manifest section is the preferred future shape when
projects need to express requirement files, package requirement strings, or venv
settings more clearly than artifact rows allow. That section is not part of the
current manifest contract. See [python-manifest.md](python-manifest.md) for the
design target and migration boundary.

Homebrew-managed `tool` artifacts currently support `version: latest`. If a
project requests a pinned Homebrew version, setup fails clearly instead of
silently installing a different version. New ordinary Homebrew tools should
prefer Brewfile delegation over registry growth. Richer version conflict
handling across projects is a later iteration, not part of the initial build.

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

## Mac Bootstrap Sequence

When `basectl setup` runs on a fresh Mac:

1. Check for Homebrew — install if missing
2. Check for Xcode CLI tools — install if missing
3. Install Python (target version) via Homebrew
4. Create Base's own virtual environment at `~/.base.d/base/.venv`
5. Install Base's Python bootstrap dependencies into `~/.base.d/base/.venv`
6. Prepare the managed shell startup model with `basectl update-profile`
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

- Base is a public GitHub repository
- Issues are the official communication channel for bug reports and feedback
- The README contains a clear "Issues and Feedback" section pointing users to GitHub
  Issues
- A stable release tag (e.g. `v0.9.0`) marks the last version of the old Base design
  before the current rewrite begins
- The README includes a notice that active development is happening on master and the
  API is changing significantly
- Users who want stability should pin to the stable release tag

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

## Open Questions (To Resolve Through Use)

- Exact manifest file name (`base.yaml`, `.base.yaml`, `base_manifest.yaml`)
- Version conflict resolution strategy across projects with different dependency versions
- Docker/dev container integration path for banyanlabs
- How Base handles projects that don't use Python at all
- Fish shell support — revisit if real demand emerges

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

*This document reflects design decisions made in May 2026. It is a living document —
update it as the design evolves through real implementation experience.*
