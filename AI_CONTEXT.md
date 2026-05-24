# AI Context

This file is the shared working memory for future AI-assisted development in this repository. Keep it current when project direction, recent fixes, or useful debugging context changes.

## Current State

- Branch: `hpr/fix-claude-findings2`.
- Current work is moving through `TODO.md`, which tracks Claude's code-analysis findings item by item.
- New in-progress feature work adds the first artifact setup layer: root
  `base_manifest.yaml`, a Python `base_setup` package under `cli/python/`, and
  a Bash setup handoff after Base bootstrap.
- The Bash setup layer seeds Base's own project virtual environment at
  `~/.base.d/base/.venv` with PyYAML and Click before invoking Python setup.
- Current in-progress work rewrites `docs/base-cli-design.md` around explicit
  `base_cli.App`/`Context` initialization and starts v1 under `lib/python/base_cli/`.
  Click is a Base Python bootstrap dependency installed into `~/.base.d/base/.venv`.
- Most recent local work dogfoods `base_cli` in `base_setup`: the Python setup
  engine now uses `base_cli.App`, `base_cli.argument`, `base_cli.option`, and
  `Context` logging while preserving the existing module CLI shape.
- `bin/base-wrapper` is the single Python command wrapper, uses
  `~/.base.d/<project>/.venv`, and invokes package commands such as
  `base_setup`. Base itself uses project name `base`.
- Default project artifacts are declared in `lib/base/default_manifest.yaml`
  using the same manifest shape as project manifests; the Python setup layer
  merges defaults with the project manifest before reconciling artifacts.
- Artifact manifests declare `project.name` and `artifacts` with `type`, `name`,
  and `version`; users do not specify managers. The Python registry maps known
  `(type, name)` pairs to managers and errors on unknown artifacts.
- Most recent uncommitted change dogfoods the new Base project venv bootstrap:
  `basectl setup` creates/uses `~/.base.d/base/.venv`, seeds PyYAML and Click
  there, and invokes Python setup through `base-wrapper`. If the target `.venv`
  path exists but is not a valid venv, setup moves it to
  `.venv.backup.<timestamp>` before creating a clean venv. `basectl setup
  --recreate-venv` intentionally backs up and rebuilds even a valid venv. This
  was verified with real non-dry setup locally.
- The previous change makes `basectl shell` reject unexpected arguments with a usage error instead of silently ignoring them.
- The previous change added the supported `--version` flag to `basectl --help`.
- The previous change consolidated `basectl setup` dry-run state on exported `DRY_RUN` while still clearing legacy inherited `dry_run`.
- The previous change consolidated Base version reading in `lib/bash/version/lib_version.sh`, shared by early `basectl --version` handling and the runtime `basectl version` command.
- `lib/bash/version` and `lib/bash/runtime` now have local README files and colocated BATS coverage, in addition to existing basectl integration coverage.
- Confirmed there are no symlinked snippets in the repo; `basectl update-profile` writes direct `source $BASE_HOME/lib/shell/<snippet>` lines into managed dotfile sections.
- The recent extension cleanup is considered complete.
- The broader development thread remains improving focused tests and startup/public utility coverage while closing TODO items in small commits.

## Project Shape

- Base is a macOS-first developer tooling foundation for a multi-repo workspace.
- Public commands live in `bin/`; `bin/basectl` is the control-plane command.
- Command implementations live under `cli/bash/commands/<command>/`.
- Shared Bash libraries live under `lib/bash/`.
- Shell startup snippets live under `lib/shell/`.
- `basectl update-profile` manages marked sections in `~/.bash_profile`, `~/.bashrc`, `~/.zprofile`, and `~/.zshrc`.
- `~/.base.d/profile.conf` records whether optional Bash/Zsh defaults are enabled.
- `~/.baserc` is user-managed and may set startup-safe preferences such as `BASE_DEBUG=1`, but must not set Base-owned variables like `BASE_HOME` or `BASE_ENABLE_BASH_DEFAULTS`.

## Shell Startup Model

- Managed login/interactive snippets must not source `base_init.sh`.
- `lib/shell/bash_profile` only bridges Bash login shells into `~/.bashrc`.
- `lib/shell/bashrc` derives `BASE_HOME`, prepends `$BASE_HOME/bin` to `PATH`, reads optional defaults from `profile.conf`, and sources `lib/shell/bash_defaults.sh` only when defaults are enabled.
- `lib/shell/zshrc` mirrors the same integration model for Zsh.
- `lib/bash/runtime/bashrc` is separate from managed dotfiles and is used by `basectl shell`; it sources `base_init.sh`, then user `~/.bashrc`, then owns the final runtime prompt.

## Recent Bug Context

- Previously observed bug: after `basectl update-profile` and `exec bash`, the prompt inside `/Users/rameshhp/work/base` did not show the git branch.
- `basectl shell` did show the branch because it uses `lib/bash/runtime/bashrc`, whose prompt calls `_base_runtime_git_prompt`.
- Root cause: normal Bash shells with optional Base defaults use `lib/shell/bash_defaults.sh`, whose prompt only showed time, host, and cwd.
- Fix: keep ordinary shell startup separate from runtime bootstrap, but make `bash_defaults.sh` include a small dynamic git prompt helper so normal interactive Bash defaults show the active repo branch.

## Current TODO Progress

- Completed and committed: Claude findings TODO list, `_git_only_path_dirty` directory matching, `sort-in-place` flag quoting, `update_file_section` temp cleanup, wrapper runtime flag documentation, simplified shell snippet path discovery, and shared version reading.
- Current uncommitted TODO item: add a CLI path to disable profile defaults.
- Next likely TODO item after that commit: remove interactive Bash upgrade behavior from `lib_std.sh`.

## Testing Notes

- Tests are BATS-based.
- Shared BATS helper: `lib/bash/tests/test_helper.sh`.
- Main basectl startup/profile coverage: `cli/bash/commands/basectl/tests/setup.bats`.
- Runtime shell prompt coverage: `cli/bash/commands/basectl/tests/basectl.bats`.
- Good focused verification after startup changes:

```bash
bats cli/bash/commands/basectl/tests/setup.bats
bats cli/bash/commands/basectl/tests/basectl.bats
```

- Latest verification in this session: full BATS suite passed, 137 tests with the existing pseudo-tty `wait_for_enter` case skipped.
