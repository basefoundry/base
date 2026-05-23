# `basectl`

Umbrella CLI for Base.

## Purpose

`basectl` is the primary user-facing command for workspace-level Base behavior.

It is invoked through:

```bash
basectl <subcommand> [args...]
```

The public entrypoint lives at `bin/basectl`. It establishes the Base runtime
for command implementations, then sources this command implementation and calls
`main`.

`basectl` also dispatches direct command names by convention. For example,
`basectl caff` loads `cli/bash/commands/caff/caff.sh`. Public convenience
commands in `$BASE_HOME/bin`, such as `bin/caff`, should remain tiny launchers
that delegate to `basectl`.

## Current subcommands

- `setup`
- `check`
- `update-profile`
- `version`
- `shell`
- `help`

## Notes

- `basectl setup` is the default local bootstrap path.
- `basectl check` verifies the same local requirements without making changes.
- `basectl update-profile` creates or refreshes managed sections in Bash and Zsh dotfiles.
- `basectl version` prints the installed Base version from the repo-root `VERSION` file.
- basectl-specific bootstrap subcommands live under `cli/bash/commands/basectl/subcommands/`.
- basectl tests live under `cli/bash/commands/basectl/tests/`.
