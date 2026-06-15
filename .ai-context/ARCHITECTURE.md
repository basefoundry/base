# Base Architecture Context

## Product Boundaries

Base is strongest when it stays focused on:

- Mac-first workstation bootstrap.
- Shared shell startup and shell-environment layering.
- Peer-repo workspace discovery under a shared parent directory.
- Workspace-level orchestration across sibling repositories.
- Shared execution conventions through `basectl` and `base-wrapper`.
- A small project manifest and command contract for participating repos.

Base should not become a general tool version manager, automatic directory-based
environment loader, full dotfile manager, generic task runner, or reproducible
package/environment solver.

## Layer Model

Base keeps clear layer ownership:

- Public launchers live in `bin/` and stay thin.
- Bash owns runtime bootstrap, shell startup, setup/check/doctor orchestration,
  and command dispatch.
- Python owns manifest parsing, structured project discovery, artifact
  decisions, JSON output, and reusable CLI framework behavior.
- Project repositories own application code, tests, service definitions,
  project-specific setup, and product onboarding.
- Persistent local state lives under `~/.base.d`.
- Ephemeral logs, temp files, and caches live under Base's cache root.

## Runtime Entrypoints

`bin/basectl` is the public control-plane command. It derives `BASE_HOME` from
its own path, sources `base_init.sh`, and dispatches to either a Base command,
an explicit Bash script, or an interactive Base runtime shell.

`bin/base-wrapper` is the Python execution wrapper. It runs Base Python packages
with the selected project virtual environment and a `PYTHONPATH` that includes
Base's `lib/python` and `cli/python`.

## Environment Layers

Base separates shell startup from runtime activation:

1. Dotfile integration makes `basectl` available in Bash/Zsh startup without
   sourcing the full runtime.
2. Base runtime activation establishes Base-owned path variables, OS/host
   metadata, Bash libraries, and command dispatch support.
3. Project activation resolves a project, sets project runtime variables,
   activates the project virtual environment, sources manifest-declared
   activation files, and updates the prompt inside a subshell.

## Activation Model

Project activation uses a Bash runtime shell. `basectl activate <project>`
validates the project, sets project runtime variables, starts Bash with Base's
runtime rcfile, and applies the project environment inside that shell. Exiting
the shell returns to the previous environment, so Base does not need fragile
deactivate logic. `BASE_ACTIVATE_SHELL` may point to another Bash executable,
but not Zsh or another non-Bash shell.

## Tool Boundary Model

Base orchestrates mature tools instead of replacing them:

- Homebrew owns ordinary macOS packages and Brewfiles.
- `mise` owns language/runtime installation when a project declares a mise
  config.
- uv owns Python dependency resolution, lockfiles, and project-local `.venv`
  environments when a manifest declares `python.manager: uv`; individual
  commands can opt into `uv run` with `runner: uv`.
- IDEs own editor behavior; Base can install apps/extensions/settings
  additively.
- Docker, `just`, Taskfile, Devbox, Nix, and similar tools can be project-level
  substrates when a project chooses them.

Adapters should detect relevance, check health, invoke the underlying tool
without hiding it, report failures in Base-native diagnostics, and avoid taking
over the tool's full configuration model.
