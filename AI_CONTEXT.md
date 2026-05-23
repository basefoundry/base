# AI Context

This file is the shared working memory for future AI-assisted development in this repository. Keep it current when project direction, recent fixes, or useful debugging context changes.

## Current State

- Branch: `hpr/fix-claude-findings2`.
- Current work is moving through `TODO.md`, which tracks Claude's code-analysis findings item by item.
- Most recent uncommitted change consolidates `basectl setup` dry-run state on exported `DRY_RUN` while still clearing legacy inherited `dry_run`.
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
- Current uncommitted TODO item: consolidate setup dry-run state on `DRY_RUN`.
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

- Latest verification in this session: full BATS suite passed, 134 tests with the existing pseudo-tty `wait_for_enter` case skipped.
