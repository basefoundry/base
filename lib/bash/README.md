# `lib/bash`

Base-specific Bash runtime and version helpers.

## Layout

- `version/`
  Base version helpers that can be sourced before the full runtime is loaded.
- `runtime/`
  Bash runtime startup files used only by `basectl` when it starts an
  interactive Base shell. These are passed with `bash --rcfile`, source the
  user's `~/.bashrc` with guardrails, load the Base runtime, and define the
  Base runtime prompt.

Reusable libraries such as `std`, `file`, and `git` live in the standalone
`base-bash-libs` repository and are resolved by `base_init.sh`.
