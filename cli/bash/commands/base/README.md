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
- `install`
- `embrace`
- `update`
- `run`
- `status`
- `shell`
- `set-team`
- `set-shared-teams`
- `version`
- `man`
- `help`

## Notes

- `base setup ...` currently delegates to the existing `setup` command.
- This command is the long-term home for the umbrella Base CLI surface.
- More modular per-subcommand organization can be introduced underneath this
  command as the CLI grows.
