# `lib/`

Top-level library namespace for Base.

## Layout

- `lib/base/`
  Shared Base shell libraries used by `base_init.sh`, `base.sh`, and other
  repo-level shell code.
- `lib/bash/`
  Base Bash CLI libraries such as `std`, `git`, and `file`.
- `lib/shell/`
  Base-managed Bash/Zsh startup files and optional shared interactive defaults.

This keeps `cli/` focused on entrypoints, commands, and environment bootstrap,
while `lib/` holds reusable sourceable modules.
