# Base Execution Model

This document describes the current `basectl` execution contract. It is about
what happens after a user invokes Base, not the future project-discovery or
Python orchestration layers.

## Public Entrypoint

`bin/basectl` is the public control-plane command for Base. Base exposes one
public executable directory: `$BASE_HOME/bin`.

`basectl` is responsible for deciding what kind of invocation the user asked
for. It then delegates runtime setup to `base_init.sh`.

At a high level, `basectl` can:

- start a Base-enabled interactive Bash shell
- run the umbrella Base command dispatcher
- run a Base command implementation by convention
- run an explicit Bash script path inside the Base runtime

## Base Home Discovery

`basectl` derives `BASE_HOME` from its own location. In the normal layout,
`bin/basectl` lives directly under `$BASE_HOME/bin`, so the parent of `bin/` is
Base home.

This is intentionally a filesystem-layout contract, not a Git contract. Base
does not require `$BASE_HOME` to be the root of a Git repository. That keeps the
same runtime model usable when Base is checked out as its own repo or embedded
inside a larger repository.

The Base home check validates the expected Base files instead of checking for a
`.git` directory.

## Dispatch Order

When `basectl` starts, it uses this dispatch order:

1. If no arguments are provided and stdin/stdout are attached to a terminal,
   start a Base-enabled interactive Bash shell.
2. If the first argument is path-like or names an existing file, treat it as a
   Bash script path and run that script inside the Base runtime.
3. If the first argument matches a Base command implementation by convention,
   run that command implementation.
4. Otherwise, run the umbrella Base command dispatcher.

This ordering lets explicit script paths win over command names.

## Script Arguments

A first argument is treated as a script when either condition is true:

- it contains `/`, such as `./script.sh`, `scripts/deploy`, or
  `/tmp/base-task.sh`
- it is an existing file in the current directory, such as `deploy.sh` or
  `deploy`

Script files do not need a `.sh` extension. The script is sourced as Bash and
must define a `main` function. After sourcing the script, `basectl` calls
`main "$@"` with the remaining arguments.

For command naming, a trailing `.sh` is stripped from
`BASE_BASH_COMMAND_NAME`. Other extensions are left intact.

Examples:

```bash
basectl ./scripts/deploy.sh prod
basectl scripts/deploy prod
basectl deploy.sh prod      # works if deploy.sh exists in the current directory
```

A script can also opt into Base with a shebang:

```bash
#!/usr/bin/env basectl

main() {
    # script body
}
```

## Command Implementations

Base command implementations are found by convention:

```text
$BASE_HOME/cli/bash/commands/<command>/<command>.sh
```

For example:

```bash
basectl caff
```

loads:

```text
$BASE_HOME/cli/bash/commands/caff/caff.sh
```

A command implementation is sourced as Bash and must define `main`.

## Umbrella Base Command

The umbrella command implementation lives at:

```text
$BASE_HOME/cli/bash/commands/basectl/basectl.sh
```

It owns the current Base subcommands:

- `setup`
- `check`
- `update-profile`
- `shell`
- `help`

Subcommand modules for the umbrella command live under:

```text
$BASE_HOME/cli/bash/commands/basectl/subcommands/
```

## Public Command Launchers

Convenience commands in `$BASE_HOME/bin` should be tiny real launcher files,
not symlinks. They delegate to `basectl` and keep the public command surface in
one place.

Some launchers may expose bonus utilities such as `caff` or `sort-in-place`.
Those utilities follow the same command-layout convention, but they are extras,
not the core workspace control plane.

Example:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/basectl" caff "$@"
```

The implementation still lives under `cli/bash/commands/<command>/` with its
local README and tests.

## Runtime Bootstrap

`base_init.sh` is the runtime bootstrap layer. It is sourced after `basectl`
has decided what should run.

`base_init.sh` establishes the Base runtime contract, including:

- exported Base environment variables such as `BASE_HOME`, `BASE_BIN_DIR`,
  `BASE_BASH_COMMANDS_DIR`, and `BASE_BASH_LIB_DIR`
- OS and host metadata such as `BASE_OS` and `BASE_HOST`
- Base's Bash standard library
- `import_base_lib`, the convention-based helper for sourcing Base Bash
  libraries
- PATH additions needed by Base runtime execution

Downstream Bash scripts should import Base Bash libraries with:

```bash
import_base_lib file/lib_file.sh
```

`import_base_lib` fails through Base standard error handling when the requested
library cannot be found, so callers do not need to duplicate that check.

## Runtime Shell

Running `basectl` with no arguments in a terminal, or running `basectl shell`,
starts an interactive Bash shell with the Base runtime loaded.

That shell uses Base's runtime rcfile:

```text
$BASE_HOME/lib/bash/runtime/bashrc
```

The runtime rcfile sources `base_init.sh`, sources the user's `~/.bashrc` once
with guardrails, and then sets the Base runtime prompt. This gives the user their
normal interactive Bash behavior while also making Base stdlib functions such as
`import_base_lib` available during user Bash startup. Base still owns the final
runtime prompt.

## Dotfile Boundary

The normal shell-startup snippets under `lib/shell/` do not source
`base_init.sh`. They only manage Bash/Zsh startup concerns, including:

- deriving `BASE_HOME` for the managed snippet
- adding `$BASE_HOME/bin` to `PATH`
- loading simple user preferences from `~/.baserc`
- enabling optional shell defaults when requested

The full Base runtime is loaded only through the `basectl` command path.

## Current Non-Goals

The current execution model does not yet define:

- Python command dispatch
- project discovery
- project activation
- version-number management
- Linux support beyond the current macOS implementation

Those features should build on this execution contract rather than bypass it.
