# Base — Design Document

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
- `basectl update-profile`
- `basectl shell`
- future commands such as `basectl projects list`, `basectl test`, and
  `basectl activate`

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

### `basectl activate` — Intelligence

- Takes a project name as argument (not a directory path)
- Works from any current directory — the user does not need to be in the project folder
- Base looks in `$BASE_HOME` to locate and validate the project
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

Applied when the user invokes `basectl`, `basectl shell`, or `basectl /path/to/script.sh`.

Contains:
- exported Base path contract such as `BASE_HOME`, `BASE_BIN_DIR`, and `BASE_BASH_LIB_DIR`
- OS and host metadata such as `BASE_OS` and `BASE_HOST`
- Base's Bash standard library
- `import_base_lib` for convention-based Base Bash library imports
- PATH additions for Base's own executable entrypoints

This layer is established by `base_init.sh`, which is sourced only through the
`basectl` command path.

### Layer 3 — Project-Specific Environment

Applied inside the project subshell when a future `basectl activate <project>` flow
is run.

Contains:
- Project-specific PATH additions
- Project-specific environment variables
- Project-specific aliases and functions
- Project-specific Python virtual environment activation
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

`BASE_PROJECT` is set by `basectl activate`. Default value is `"base"`. It does not change
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

When `basectl setup` runs on a fresh Mac:

1. Check for Homebrew — install if missing
2. Check for Xcode CLI tools — install if missing
3. Install Python (target version) via Homebrew
4. Create Base's own virtual environment at `~/.base.d/base/.venv`
5. Install Base's Python dependencies into `~/.base.d/base/.venv`
6. Prepare the managed shell startup model with `basectl update-profile`
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
Banyanlabs handles the learning environment. Base must ship first.

---

*This document reflects design decisions made in May 2026. It is a living document —
update it as the design evolves through real implementation experience.*
