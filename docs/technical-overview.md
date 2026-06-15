# Base — Technical and Product Overview

## What It Is

**Base** is a macOS-first workspace control plane for developers who keep multiple
Git repositories checked out side by side under a shared directory (typically
`~/work/`). Rather than forcing unrelated codebases into a monorepo, Base provides
a single CLI — `basectl` — that orchestrates setup, diagnostics, project discovery,
shell activation, test execution, and releases across all of them.

> The repo you check out once per workspace so all other repos become easier to
> set up, test, and run.

## Why It Exists

Multi-repo development has a recurring problem: every project has a different
bootstrap story, and the glue between projects — shared env vars, shared tools,
consistent shell environments — lives in fragile ad-hoc dotfiles or one-off
scripts. Base formalizes that glue without absorbing project-specific logic.

It solves exactly three things:

1. **Umbrella setup and test** — one command to set up or test any project
2. **Shell environment management** — one managed, inspectable shell layer across
   the whole workspace
3. **Shared Bash/Python libraries** — consistent CLI execution patterns for all
   project scripts

## Target Workspace Shape

```
~/work/
  base/           ← Base itself (source checkout or Homebrew install)
  project-a/      ← has base_manifest.yaml
  project-b/      ← has base_manifest.yaml
  infra/          ← another peer repo opted into Base
```

Projects opt in by placing a `base_manifest.yaml` at their root. Base discovers
them by scanning the workspace root.

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | Bash 4.2+ |
| Data / artifacts | Python 3.10+ |
| CLI framework | Click (wrapped by `base_cli`) |
| Manifest format | YAML (`base_manifest.yaml`) |
| Package management | Homebrew (tools), pip/venv (Python) |
| Runtime versioning | `mise` (optional, per-project) |
| Testing | BATS (Bash), pytest (Python) |
| Static analysis | ShellCheck, Pylint, Bandit |
| CI | GitHub Actions (tests, lint, skills) |

## Architecture: Three Layers

**Layer 1 — Dotfile integration** (`basectl update-profile`)

Manages small marked sections in `~/.bash_profile`, `~/.bashrc`, `~/.zprofile`,
and `~/.zshrc`. Adds `$BASE_HOME/bin` to `PATH`. Never takes over whole dotfiles.
Markers look like:

```bash
# >>> base: bashrc managed >>>
# ... Base-managed content ...
# <<< base: bashrc managed <<<
```

**Layer 2 — Base runtime** (`base_init.sh`, sourced on every `basectl` invocation)

Exports `BASE_HOME`, `BASE_BIN_DIR`, `BASE_BASH_LIB_DIR`, `BASE_OS`, `BASE_HOST`,
and `BASE_SHELL`. Loads the Bash standard library. Sets up `import_base_lib` for
convention-based library imports.

**Layer 3 — Project environment** (`basectl activate <project>`)

Spawns a Bash runtime shell, sets `BASE_PROJECT`, activates the project venv at
`~/.base.d/<project>/.venv`, runs `activate.source` scripts declared in the
manifest, and updates the prompt to `[project: branch] ~/path $`. Exit that
shell to return to the original environment - no deactivation logic needed.

**Design choice — no `cd`-triggered activation:** switching directories does not
change environment. Users explicitly activate projects with `basectl activate`.
This is deliberate; auto-activation on `cd` is ambiguous and error-prone.

## Project Manifest Contract

Each project opts into Base with a small declarative YAML file at its root. All
fields are optional:

```yaml
schema_version: 1

project:
  name: example

brewfile: Brewfile          # delegates to brew bundle
mise: .mise.toml            # delegates to mise install

artifacts:                  # Python packages → project venv
  - type: python-package
    name: requests
    version: latest

health:
  required_env: [DATABASE_URL]
  required_ports:
    - { name: postgres, port: 5432, state: listening }

activate:
  source: [.base/activate.sh]

test:
  command: pytest tests/    # or: mise: test

commands:
  dev: uvicorn app:app --reload
  lint: ruff check .

build:
  default: [api]
  targets:
    api:
      command: go build ./cmd/api
      working_dir: services/api

ide:
  vs-code:
    extensions: [ms-python.python]

release:
  version_file: VERSION
  changelog: CHANGELOG.md
```

**Design principle:** manifests describe *what* the project needs, not *how* to do
arbitrary setup. There are no setup hooks. Projects delegate to Homebrew, `mise`,
and their own build systems. See [Setup Hooks Boundary](setup-hooks.md).

## Key Commands

### Install and Bootstrap

| Command | What it does |
|---|---|
| `basectl setup [project] [--profile dev\|sre\|ai]` | Install / reconcile prerequisites |
| `basectl update-profile [--defaults]` | Wire shell startup files |
| `basectl update [--dry-run]` | Upgrade Base (git pull or brew upgrade) |
| `basectl onboard` | Guided first-run checklist |

### Daily Loop

| Command | What it does |
|---|---|
| `basectl projects list [--format json]` | Discover all Base-managed projects |
| `basectl activate <project> [--no-cd]` | Spawn project subshell |
| `basectl test <project> [-- args]` | Run declared test command |
| `basectl run <project> <cmd> [-- args]` | Run named manifest command |
| `basectl build <project> [targets] [--list\|--dry-run]` | Run build targets |
| `basectl demo [project] [--non-interactive]` | Run project demo script |
| `basectl export-context [project]` | Generate AI context pack from `.ai-context/` |

### Diagnostics

| Command | What it does |
|---|---|
| `basectl check [project] [--profile]` | Quick pass/fail readiness check |
| `basectl doctor [project] [--profile]` | Human-readable findings + fix commands |
| `basectl logs [--tail\|--command\|--path\|--open]` | Inspect runtime logs |
| `basectl config path\|show\|doctor` | Machine-local config |
| `basectl clean [--older-than\|--keep-last]` | Prune cache/logs |

### Workspace

| Command | What it does |
|---|---|
| `basectl workspace status [--manifest]` | Cross-project manifest and venv state |
| `basectl workspace check [--manifest]` | Cross-project readiness check |
| `basectl workspace doctor [--manifest]` | Cross-project diagnostic findings |

### Repository and Release

| Command | What it does |
|---|---|
| `basectl repo init <name> [--repo owner/name]` | Create new Base-managed GitHub repo |
| `basectl repo check [path]` | Validate repo baseline |
| `basectl repo configure [path]` | Repair / standardize repo settings |
| `basectl repo agent-guidance [path]` | Seed AI guidance for a repo |
| `basectl release check\|plan\|notes\|publish` | Release readiness + guarded publishing |

### CI

| Command | What it does |
|---|---|
| `basectl ci setup\|check\|doctor [--format json]` | Non-interactive CI entry point |

**Prerequisite profiles** (compose with commas: `--profile dev,ai`):

| Profile | Installs |
|---|---|
| `dev` | BATS, GitHub CLI, ShellCheck |
| `sre` | kubectl, helm, k9s, jq, yq, httpie, nmap, mtr |
| `ai` | Codex CLI, Claude Code |

## Installation Paths

| Method | Best for |
|---|---|
| `curl … bootstrap.sh \| bash` | Blank macOS machine; installs Homebrew, Git, Bash, then Base |
| `brew install codeforester/base/base` | Users wanting Base installed as a managed tool |
| `git clone` + `basectl setup` | Contributors / Base developers |
| `curl … install.sh \| bash` | Source-install shortcut |

All paths converge on the same daily command surface. After any install, finish
with:

```bash
basectl setup
basectl update-profile
exec "$SHELL" -l
```

## Key File Locations

| Path | Purpose |
|---|---|
| `~/.base.d/config.yaml` | Machine-local config (workspace root, log level) |
| `~/.base.d/<project>/.venv` | Per-project Python virtual environment |
| `~/Library/Caches/base/` | Runtime logs, temp files, project discovery cache |
| `~/.baserc` | User preferences (e.g., `BASE_DEBUG=1`) |
| `~/.base.d/profile.conf` | Shell defaults opt-in state |

## Testing

| Layer | Tool | Where |
|---|---|---|
| Bash unit tests | BATS | `cli/bash/commands/basectl/tests/`, `lib/bash/*/tests/` |
| Python unit tests | pytest | `cli/python/*/tests/`, `lib/python/*/tests/` |
| Integration tests | BATS | `tests/integration/base_workflows.bats` |
| Shell static analysis | ShellCheck | All `*.sh` files |
| Python lint | Pylint | `cli/python/`, `lib/python/` (3.10–3.13 matrix) |
| Python security scan | Bandit | `cli/python/`, `lib/python/` |

Run everything locally with `basectl test base` or `bin/base-test`.

## Current Status

Base **0.4.4** (June 2026) covers: setup, check, doctor, project discovery,
workspace status, project activation (subshell), test execution, build targets,
named commands, demo scripts, repository baseline creation, guarded GitHub release
publishing, AI context export, `basectl ci` for non-interactive CI, IDE
bootstrapping (VS Code/Cursor), and release readiness inspection.

Linux support is a design target but not yet an implemented or tested contract.
Windows is out of scope.

## Where to Go Next

- [README](../README.md) — first-run guide and full command documentation
- [FAQ](../FAQ.md) — common installation and configuration questions
- [Base Newcomer Orientation](presentations/base-newcomer-orientation.md) — slide
  walkthrough for live or async onboarding
- [Architecture](architecture.md) — design decisions and product direction
- [Execution Model](execution-model.md) — `basectl` runtime and dispatch contract
- [Tool Boundaries](tool-boundaries.md) — what Base owns vs. what it delegates
- [Doctor Finding IDs](doctor-findings.md) — stable IDs for automation
