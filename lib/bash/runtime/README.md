# Runtime Bash Rcfile

`lib/bash/runtime/bashrc` is the rcfile used by `basectl activate <project>`
when it starts a Base-enabled interactive Bash shell. Invoking `basectl` with no
arguments in a terminal activates the nearest Base project for the caller
directory, preserves that directory, and falls back to project `base` when no
project manifest is found.

## What It Does

- validates `BASE_HOME`
- sources `lib/shell/baserc_guard.sh`
- sources user-managed `~/.baserc` when present
- sources `base_init.sh`
- adds `$BASE_PROJECT_ROOT/bin` to `PATH` when it exists, keeping `$BASE_HOME/bin` first
- sources the user's `~/.bashrc` with guardrails
- activates the project virtual environment
- sources manifest-declared `activate.source` scripts
- owns the final runtime prompt

## Behavior Notes

- This file is passed to Bash with `bash --rcfile`.
- It is not installed into user dotfiles by `basectl update-profile`.
- It intentionally runs `base_init.sh`; normal shell startup snippets under
  `lib/shell/` must not.

## Tests

BATS coverage lives in `tests/runtime_bashrc.bats`. Additional integration
coverage for project activation and command startup lives in
`cli/bash/commands/basectl/tests/basectl.bats`.
