# `lib/`

Top-level library namespace for Base.

## Layout

- `lib/base/`
  Base-owned internal manifests such as the default manifest and built-in
  prerequisite profiles.
- `lib/bash/`
  Base-specific runtime, command protocol, version adapters, and shell startup
  files. Reusable libraries such as `std`, `git`, and `file` come from the
  standalone `base-bash-libs` repository.
- `lib/shell/`
  Base-managed Bash/Zsh startup files and optional shared interactive defaults.

Base-owned Python packages and integration helpers live under `cli/python/`;
there is no local `lib/python/` source tree. The reusable `base_cli` framework
is maintained in the standalone `base-cli` repository. See
[Python Package Ownership](../docs/python-package-ownership.md).
