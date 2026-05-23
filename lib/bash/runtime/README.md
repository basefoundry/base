# Runtime Bash Rcfile

`lib/bash/runtime/bashrc` is the rcfile used by `basectl` and `basectl shell`
when they start a Base-enabled interactive Bash shell.

## What It Does

- validates `BASE_HOME`
- sources `lib/shell/baserc_guard.sh`
- sources user-managed `~/.baserc` when present
- sources `base_init.sh`
- sources the user's `~/.bashrc` with guardrails
- owns the final runtime prompt

## Behavior Notes

- This file is passed to Bash with `bash --rcfile`.
- It is not installed into user dotfiles by `basectl update-profile`.
- It intentionally runs `base_init.sh`; normal shell startup snippets under
  `lib/shell/` must not.

## Tests

BATS coverage lives in `tests/runtime_bashrc.bats`. Additional integration
coverage for `basectl shell` and command startup lives in
`cli/bash/commands/basectl/tests/basectl.bats`.
