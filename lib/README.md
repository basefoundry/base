# `lib/`

Top-level library namespace for Base.

## Layout

- `lib/bash/`
  Base Bash runtime libraries such as `std`, `git`, `file`, and runtime shell
  startup files.
- `lib/shell/`
  Base-managed Bash/Zsh startup files and optional shared interactive defaults.

This keeps `cli/` focused on entrypoints, commands, and runtime bootstrap,
while `lib/` holds reusable sourceable modules.
