# CLAUDE.md — AI Assistant Guide for Base

Base is a macOS-first workspace control plane (v0.2.0) for multi-project
development. It provides an umbrella CLI (`basectl`), shared Bash and Python
libraries, manifest-driven project setup, IDE bootstrapping, and shell
environment management across Bash and Zsh.

---

## Repository Layout

```
base/
├── bin/                        # Public command launchers (thin; added to PATH)
│   ├── basectl                 # Main entry point for all Base commands
│   ├── base-wrapper            # Python venv/command wrapper
│   ├── base-test               # Test runner for Base itself
│   ├── caff                    # Delegates to `basectl caff`
│   └── sort-in-place           # Delegates to `basectl sort-in-place`
├── cli/
│   ├── bash/commands/          # Bash command implementations
│   │   └── basectl/            # Umbrella command + subcommands/
│   │       ├── basectl.sh
│   │       ├── subcommands/    # activate, check, clean, config, doctor,
│   │       │                   #   gh, onboard, projects, setup, test,
│   │       │                   #   update, update_profile
│   │       └── tests/          # BATS tests colocated with the command
│   └── python/                 # Python CLI command packages
│       ├── base_clean/
│       ├── base_config/
│       ├── base_dev/
│       ├── base_projects/
│       └── base_setup/         # Setup engine + artifact registry
├── lib/
│   ├── bash/                   # Shared Bash libraries
│   │   ├── file/lib_file.sh
│   │   ├── git/lib_git.sh
│   │   ├── runtime/bashrc      # Interactive shell support
│   │   ├── std/lib_std.sh      # Logging, error helpers, PATH management
│   │   └── version/lib_version.sh
│   ├── python/base_cli/        # Shared Python CLI framework (Click wrapper)
│   │   ├── app.py              # App class, decorator API
│   │   ├── config.py           # Config loading with precedence
│   │   ├── context.py          # Command context object
│   │   ├── logging.py          # Structured logging
│   │   ├── paths.py            # Path discovery
│   │   ├── redaction.py        # Sensitive param redaction
│   │   └── testing.py          # CLI test helpers
│   ├── shell/                  # Shell startup files and completions
│   │   ├── bash_profile / zprofile
│   │   ├── bashrc / zshrc
│   │   ├── base_defaults.sh
│   │   └── completions/        # basectl_completion.sh / .zsh
│   └── base/                   # Manifests
│       ├── default_manifest.yaml
│       └── dev_manifest.yaml
├── docs/                       # Architecture and design documents
├── tests/                      # Cross-module tests (install.bats)
├── base_init.sh                # Runtime bootstrap (sourced by basectl)
├── base_manifest.yaml          # Base's own project manifest
├── install.sh                  # Standalone installer
├── skills.md                   # AI-assisted development workflows
├── STANDARDS.md                # Coding standards (shell + Python)
├── CONTRIBUTING.md             # Contribution guide
├── CHANGELOG.md                # Keep-a-Changelog format
└── VERSION                     # Current version string
```

---

## Development Commands

### Running Tests

```bash
# Run all tests for Base
basectl test base

# Python tests only
env PYTHONPATH=lib/python:cli/python python -m pytest

# Specific BATS test files
bats cli/bash/commands/basectl/tests/basectl.bats
bats cli/bash/commands/basectl/tests/setup.bats
bats lib/bash/std/tests/lib_std.bats
bats lib/bash/git/tests/lib_git.bats
bats lib/bash/runtime/tests/runtime_bashrc.bats
bats tests/install.bats

# Direct test runner
bin/base-test
```

### Linting and Static Analysis

```bash
# Python lint (multi-version matrix in CI)
env PYTHONPATH=lib/python:cli/python pylint cli/python lib/python

# Shell security scan
shellcheck -S error bin/basectl base_init.sh install.sh \
  cli/bash/commands/**/*.sh lib/bash/**/*.sh

# Python security scan
bandit -r cli/python lib/python

# Check for whitespace/formatting issues
git diff --check
```

### Setup and Diagnostics

```bash
basectl setup --dev          # Install developer prerequisites (BATS, gh)
basectl check --dev          # Check developer tool availability
basectl doctor --dev         # Diagnose missing developer tools
bin/basectl check            # Run Base's own check suite
bin/basectl setup --dry-run  # Preview setup without mutations
```

---

## Bash Code Conventions

All Bash standards are documented in `STANDARDS.md`. Key rules:

- **Indentation**: 4 spaces, no tabs.
- **Naming**:
  - Local variables and functions: `snake_case`
  - Exported environment variables and constants: `UPPER_CASE`
  - Private names in libraries: leading underscore `_name`
  - No `camelCase`
- **Quoting**: double-quote all variable expansions, except inside `[[ ]]` or
  `(( ))`, or when word splitting is intentional.
- **Error handling**: never use `set -e`. Use `run`, `exit_if_error`, and
  `fatal_error` from `lib/bash/std/lib_std.sh`. Check return codes explicitly.
- **Script structure**: define a `main()` function; call `main "$@"` at the
  bottom. Keep all logic inside functions.
- **Library guard**: every sourced library must guard against double-sourcing:

  ```bash
  [[ $__mylib_sourced__ ]] && return
  __mylib_sourced__=1
  ```

- **Library loading**: use `import_base_lib path/to/lib.sh` in runtime scripts;
  never reconstruct `BASE_*` paths locally.
- **Conditionals**: use `[[ $var ]]` (not `[[ -n $var ]]`) to test non-empty.
- **ShellCheck**: all shell files must pass `shellcheck -S error`.
- **Compact style**:

  ```bash
  if condition; then
      ...
  fi
  ```

---

## Python Code Conventions

- Python 3.10+ (`from __future__ import annotations` at the top of every file).
- All commands use the `base_cli.App` pattern — wrap Click via the framework:

  ```python
  import base_cli

  app = base_cli.App(name="my_command")

  @app.command()
  @base_cli.option("--foo", help="...")
  def run(ctx: base_cli.Context, foo: str | None) -> None:
      ...
  ```

- Use dataclasses for structured data, type hints everywhere.
- Max line length: 120 characters (`.pylintrc`).
- `PYTHONPATH` must include `lib/python:cli/python` when running or testing.
- Tests live under `<package>/tests/` next to the package they validate. Small
  packages can use `test_engine.py`; larger packages should split focused
  `test_*.py` modules by feature area.
- Standard CLI options (provided by `base_cli`): `--debug`, `--environment`,
  `--config`, `--keep-temp`, `--log-file`.

---

## Repository Structure Rules

### Commands

- Public launchers in `bin/` are thin; they delegate to `basectl`:

  ```bash
  #!/usr/bin/env bash
  exec "$(dirname "$0")/basectl" my-command "$@"
  ```

- Command implementation lives under
  `cli/bash/commands/<command>/<command>.sh`.
- Tests colocated under `cli/bash/commands/<command>/tests/`.
- Python commands live in `cli/python/<command>/`.

### Libraries

- Bash libraries: `lib/bash/<name>/lib_<name>.sh` with a `README.md` and
  `tests/` subdirectory.
- Python library/framework: `lib/python/base_cli/`.

### Shell Startup

- Managed startup snippets live in `lib/shell/`.
- Startup files must **not** source `base_init.sh` — runtime setup belongs to
  the `basectl` command path only.
- `~/.baserc` is user-managed; it must not set `BASE_*` runtime variables.

---

## Adding New Features (Workflow Patterns)

### New `basectl` Subcommand

1. Add implementation to `cli/bash/commands/basectl/subcommands/<name>.sh`.
2. Wire it into `cli/bash/commands/basectl/basectl.sh`.
3. Update completions in `lib/shell/completions/basectl_completion.sh` and
   `lib/shell/completions/basectl_completion.zsh`.
4. Add tests to `cli/bash/commands/basectl/tests/`.

### New Bash Library

1. Create `lib/bash/<name>/lib_<name>.sh`, `README.md`, and `tests/`.
2. Load via `import_base_lib lib/bash/<name>/lib_<name>.sh`.
3. No `set -e`; use explicit error handling throughout.

### New Python CLI Command

1. Create a package under `cli/python/<command>/` with `engine.py` (or
   equivalent) and a focused `tests/test_*.py` module.
2. Follow the `base_cli.App` pattern.
3. Run with `PYTHONPATH=lib/python:cli/python python -m <command>`.

### New Artifact in the Registry

1. Edit `cli/python/base_setup/registry.py`.
2. Add lookup and setup/check tests.
3. Prefer Homebrew delegation over expanding Base-owned setup logic.

---

## GitHub / Git Workflow

### Branch Names

```
<category>/<issue>-<YYYYMMDD>-<slug>
```

Examples:

```
bug/245-20260529-fix-profile-project-prompt
enhancement/222-20260529-add-changelog
documentation/241-20260529-document-github-workflow
ci/246-20260529-pin-shellcheck-version
security/247-20260529-restrict-log-permissions
```

### Labels

Use only these labels (no `type:*` prefixes):

- `bug` — defects and regressions
- `enhancement` — features, refactors, maintenance
- `documentation` — docs-only changes
- `ci` — GitHub Actions, test automation
- `security` — hardening, dependency pinning

### Worktrees

All PR implementation work happens in a dedicated worktree:

```bash
git fetch origin master
git worktree add -b <branch> ~/work/base-worktrees/<slug> origin/master
```

### Pull Requests

- One issue per PR; link with `Fixes #<issue>` or `Closes #<issue>`.
- PR body: short summary + validation commands run.
- Prefer `basectl gh` commands for GitHub operations; fall back to the GitHub
  MCP tools or `gh` CLI when `basectl gh` doesn't cover the operation.
- Issues created by automation should be assigned to `codeforester`.

### After Merge

```bash
git -C ~/work/base pull --ff-only origin master
git -C ~/work/base worktree remove ~/work/base-worktrees/<slug>
git -C ~/work/base branch -d <branch>
git -C ~/work/base push origin --delete <branch>
```

---

## CI Overview (`.github/workflows/`)

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `tests.yml` | push / PR | pytest (Python 3.13), BATS (11 files), Bandit, ShellCheck |
| `pylint.yml` | push / PR | pylint matrix across Python 3.10–3.13 |
| `skills.yml` | (see file) | AI-assisted workflow validation |

All checks must pass before merging. The narrowest relevant tests should be
run locally first (single BATS file or single pytest module) before running
the full suite.

---

## Configuration

### Project Manifest (`base_manifest.yaml`)

Declares a project's name, test command, Brewfile, artifacts, and IDE
configuration. Base reads this at setup and check time.

### User Config (`~/.base.d/config.yaml`)

Machine-local user configuration managed by Base. Not edited by hand.

### User Preferences (`~/.baserc`)

User-managed simple preferences (e.g. `BASE_DEBUG=1`). Must not contain
`BASE_HOME`, `BASE_BIN_DIR`, or other Base-owned runtime variables.

### Runtime Variables Set by `base_init.sh`

| Variable | Description |
|----------|-------------|
| `BASE_HOME` | Root of the Base installation |
| `BASE_BIN_DIR` | `$BASE_HOME/bin` |
| `BASE_BASH_LIB_DIR` | `$BASE_HOME/lib/bash` |
| `BASE_BASH_COMMANDS_DIR` | `$BASE_HOME/cli/bash/commands` |
| `BASE_OS` | `macos` or `linux` |
| `BASE_HOST` | Hostname |
| `BASE_SHELL` | `bash` or `zsh` |

---

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `bin/basectl` | Public entry point; dispatches to command implementations |
| `base_init.sh` | Runtime bootstrap; sets all `BASE_*` paths and metadata |
| `lib/bash/std/lib_std.sh` | Core Bash helpers: `run`, `fatal_error`, logging, PATH |
| `lib/python/base_cli/app.py` | Python CLI framework; wraps Click |
| `cli/python/base_setup/registry.py` | Curated artifact registry |
| `lib/base/default_manifest.yaml` | Default artifacts applied to all projects |
| `lib/shell/completions/` | Shell completions for `basectl` |
| `STANDARDS.md` | Authoritative coding standards |
| `skills.md` | AI-assisted development workflow patterns |
| `docs/architecture.md` | Product direction and system architecture |
| `docs/execution-model.md` | Runtime and dispatch details |
| `docs/github-workflow.md` | Full GitHub issue/PR/worktree policy |
