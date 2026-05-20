# `base`

Umbrella CLI for Base.

## Purpose

`base` is the primary user-facing command for workspace-level Base behavior.

It is invoked through:

```bash
base <subcommand> [args...]
```

The public entrypoint lives at `bin/base` and delegates through `base-wrapper`,
so Base command execution still goes through the same environment bootstrap and
Bash stdlib loading path as other wrapped commands.

## Current subcommands

- `setup`
- `check`
- `update-profile`
- `install`
- `embrace`
- `shell`
- `version`
- `help`

## Notes

- `base setup` is the default local bootstrap path.
- `base check` verifies the same local requirements without making changes.
- `embrace` and `shell` are the remaining shell-management entrypoints.
- Base-specific bootstrap subcommands live under `cli/bash/commands/base/subcommands/`.
- Shared tests for Base subcommands live under `cli/bash/commands/tests/`.
