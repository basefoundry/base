# `lib/`

Top-level library namespace for Base.

## Layout

- `lib/base/`
  Shared Base shell libraries used by `base_init.sh`, the `basectl` CLI, and other
  repo-level shell code.
- `lib/bash/`
  Base Bash CLI libraries such as `std`, `git`, and `file`.
- `lib/shell/`
  Base-managed Bash/Zsh startup files and optional shared interactive defaults.

This keeps `cli/` focused on entrypoints, commands, and runtime bootstrap,
while `lib/` holds reusable sourceable modules.
