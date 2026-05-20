# Base — Design Document

## Overview

Base is an opinionated Mac development orchestrator. It provides a unified, declarative
foundation for bootstrapping a Mac development environment and managing multiple projects
through a single CLI interface. Base is Mac-only by deliberate design choice. Windows
support is not in scope.

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

## Command Surface — `base` First

The most important command-surface decision in Base: **one canonical public command**.

### `base` — The Primary CLI

`base` is the public entrypoint. It is a normal executable command that runs through the
Base wrapper/bootstrap path. This keeps the product surface simple:

- `base setup`
- `base check`
- `base install`
- `base embrace`
- `base shell`
- future commands such as `base projects list`, `base test`, and `base activate`

For now, Base does **not** introduce a separate `basectl` command. A second top-level
name adds conceptual weight before we have a real need for it.

### Why a Separate `basectl` Is Not Needed Yet

Most orchestration work does not need to mutate the current shell, so a normal CLI is
sufficient. Even project activation can still be initiated from the `base` executable if
it works by validating the target project and spawning a subshell with the desired
project environment.

That means the important split is not between two product names. The important split is
between:

- commands that perform orchestration and exit normally
- commands that may launch a subshell for interactive project work

Both can still live under the same `base` command surface.

### Optional Future Shell Function

If Base later needs functionality that truly must mutate the current shell process, an
optional shell function can be added. If that happens, it should be a thin wrapper around
`base`, not a separate conceptual tool with a different name.

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

This does not require a distinct shell function. A normal `base activate <project>`
command can validate the target and launch the configured subshell.

### Activation Flow

```
base activate myproject
  ↓
1. Look up BASE_HOME, scan known projects
2. Validate myproject exists and has a valid manifest
3. Set BASE_PROJECT=myproject
4. Spawn a new subshell
5. In the subshell: source the project's shell environment script
6. In the subshell: activate the project's Python virtual environment
7. Update the prompt to reflect the active project
8. User works in subshell
9. User exits → returns to base shell, prompt resets
```

### `base activate` — Intelligence

- Takes a project name as argument (not a directory path)
- Works from any current directory — the user does not need to be in the project folder
- Base looks in `$BASE_HOME` to locate and validate the project
- Validates that the target is a recognized Base project with a valid manifest

---

## Shell Environment Layers

There are two layers of shell environment, clearly separated:

### Layer 1 — Base Global Environment

Applied once when the shell starts, using Base-managed startup files and machine-local overrides.
Contains:
- Shell prompt (PS1) defaults
- History settings (size, format, file location)
- Default aliases and utility functions
- PATH additions for Base's own tools
- Shell options appropriate for bash or zsh
- `BASE_PROJECT` set to `"base"` by default
- `BASE_HOME` pointing to the base project root

This layer is currently installed by adopting the Base-managed startup files under `lib/shell/`, typically through symlinks or a helper such as `base embrace`. Machine-local overrides belong in `~/.baserc`.

### Layer 2 — Project-Specific Environment

Applied inside the project subshell when `base activate <project>` is run.
Contains:
- Project-specific PATH additions
- Project-specific environment variables
- Project-specific aliases and functions
- Project-specific Python virtual environment activation
- `BASE_PROJECT` updated to the project name

Project-specific settings layer on top of the base global environment. Settings not
overridden by the project inherit from the base global layer. When the subshell exits,
the project layer disappears naturally — no explicit deactivation needed.

### Dotfile Management

Base currently ships managed shell startup files instead of injecting a large managed block into user dotfiles. The preferred adoption model is:

| File | Purpose |
|---|---|
| `lib/shell/bashrc` | Interactive bash shell settings |
| `lib/shell/bash_profile` | Login bash shell settings |
| `lib/shell/zshrc` | Interactive zsh shell settings |
| `lib/shell/zprofile` | Login zsh shell settings |

Users can symlink these into place, and Base can provide helper commands such as `base embrace` to make that easier. `~/.baserc` remains the machine-local override file for settings such as `BASE_HOME`.

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

Everything else stays stable until the user explicitly runs `base activate <project>`.

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

`BASE_PROJECT` is set by `base activate`. Default value is `"base"`. It does not change
based on directory. Once you activate a project, the project name shows consistently
regardless of where you `cd` inside the subshell.

### Git Branch in Prompt

The git branch is **not stored in a variable**. It is queried dynamically each time the
prompt renders. This ensures the prompt reflects reality when the user runs `git
checkout` to switch branches inside the subshell.

Implementation in PS1:

```bash
_base_git_branch() {
  git -C "$BASE_PROJECT_ROOT" symbolic-ref --short HEAD 2>/dev/null || echo "detached"
}

PS1='[${BASE_PROJECT}: $(_base_git_branch)] \w $ '
```

Key decision: the branch is always queried against `$BASE_PROJECT_ROOT` (the project's
root directory), not the current working directory. This means even if you `cd /tmp`,
the prompt shows the project's branch, not whatever git repo happens to be at `/tmp`.

### Why Not Show Python Venv in Prompt

The project name in the prompt implies the Python virtual environment — if a project is
active, its venv is active. Showing both would be redundant. The prompt stays clean.

---

## Python Virtual Environments

### Base Venv

- Created once during `base setup`
- Lives at `~/.base.d/.venv`
- Used to run Base's own Python orchestration code (manifest parsing, project discovery,
  etc.)
- Not activated in the user's interactive shell by default — it runs internally when
  Base needs it

### Project Venv

- Created per project during `base setup <project>` or `base setup` when scanning
  all projects
- Lives inside the project directory (e.g., `.venv/`)
- Activated automatically when `base activate <project>` spawns the project subshell
- Deactivated automatically when the subshell exits

### Key Distinction

Only one Python venv can be active at a time. Base venv runs quietly in the background
for Base's own tools. Project venv is what the user interacts with. The two never
conflict because Base venv is not surfaced in the interactive shell.

---

## Project Manifest

Each Base-managed project declares its dependencies in a YAML manifest file at the
project root. Base reads this manifest to know what to install and configure.

File: `base.yaml` (name TBD)

Conceptual structure:

```yaml
project:
  name: myproject
  description: A short description

dependencies:
  system:
    - kubernetes
    - terraform
    - docker
  python:
    - version: "3.12"
      packages:
        - requests
        - rich
  go:
    - version: "1.22"

shell:
  env:
    MY_PROJECT_ENV: production
  path:
    - ./bin
```

The Python layer interprets this declarative manifest and translates each item into
concrete installation actions. Base knows how to install system tools via Homebrew,
manage Python versions and packages, and handle language-specific package managers.

Version conflicts across projects are a known complexity — addressed in a later
iteration, not in the initial build.

---

## Mac Bootstrap Sequence

When `base setup` runs on a fresh Mac:

1. Check for Homebrew — install if missing
2. Check for Xcode CLI tools — install if missing
3. Install Python (target version) via Homebrew
4. Create Base's own virtual environment at `~/.base.d/.venv`
5. Install Base's Python dependencies into `~/.base.d/.venv`
6. Prepare the managed shell startup model (currently via Base-managed startup files and shell adoption helpers)
7. Scan the parent directory for peer repos with base manifests
8. For each discovered project, run project-level setup (install declared dependencies,
   create project venv)

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
- Not cross-platform — Windows is explicitly out of scope.
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
Banyanlabs handles the learning environment. Base must ship first.

---

*This document reflects design decisions made in May 2026. It is a living document —
update it as the design evolves through real implementation experience.*
