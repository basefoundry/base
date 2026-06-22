# `lib/`

Top-level library namespace for Base.

## Layout

- `lib/base/`
  Base-owned internal manifests such as the default manifest and built-in
  prerequisite profiles.
- `lib/bash/`
  Base Bash runtime libraries such as `std`, `git`, `file`, and runtime shell
  startup files.
- `lib/python/`
  Python package source for Base-owned Python libraries, including `base_cli`.
- `lib/shell/`
  Base-managed Bash/Zsh startup files and optional shared interactive defaults.

This keeps `cli/` focused on entrypoints, commands, and runtime bootstrap,
while `lib/` holds reusable sourceable modules.
