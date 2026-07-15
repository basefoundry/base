# Base Architecture Context

## Product Boundaries

Base is strongest when it stays focused on a local operating contract for:

- Inventorying participating and expected independent Git repositories.
- Preparing and verifying declared local readiness.
- Keeping project-owned execution behind an explicit trust boundary.
- Making onboarding and handoff evidence inspectable.

The small project manifest, `basectl`, `base-wrapper`, activation model, and
declared project commands are the enabling execution contract. Repository,
GitHub, and release conventions are supporting workflow packs.
Environment-manager, IDE, container, Nix/devenv, and AI behavior stays in
adapter or export lanes.

Deterministic means explicit ordering, stable findings or machine-readable
structures, and clear next actions from declared inputs and inspectable local
state. It does not mean hermetic builds or transactional multi-repository
updates.

Base should not become a general tool version manager, automatic directory-based
environment loader, full dotfile manager, generic task runner, or reproducible
package/environment solver. It should also not become a generic repo sync/
fan-out manager or a hosted agent runtime.

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

The `setup_common.sh` ownership-reduction path is documented in
`docs/setup-common-ownership.md`: reduce Bash ownership by moving project
routing and JSON formatting to Python before considering any new shell
boundary. Do not split `setup_common.sh` into sourced fragments by topic.

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
- Base owns the supported Python runtime window for `python.requires_python`
  and uses that declaration when creating Base-managed project virtualenvs.
- IDEs own editor behavior; Base can install apps/extensions/settings
  additively.
- Docker, `just`, Taskfile, Devbox, Nix, and similar tools can be project-level
  substrates when a project chooses them.
- AI agent harnesses own live agent sessions, provider interaction, credentials,
  sandboxing, approvals, collaboration UI, and multi-agent scheduling. Base
  should support them only through provider-neutral context packs, repo-local
  guidance, maintained prompts, current local evidence, planned handoff/report
  artifacts, and explicit opt-in health checks. Unified handoff artifacts remain
  open work in #1561 and #1562.

Adapters should detect relevance, check health, invoke the underlying tool
without hiding it, report failures in Base-native diagnostics, and avoid taking
over the tool's full configuration model.
