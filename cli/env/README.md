# `cli/env`

This directory holds the shared CLI environment bootstrap.

## Purpose

`baseenv.sh` defines the common shell environment used by:

- `cli/bash/bin/base-wrapper`
- interactive shells that source it from `~/.bashrc` or `~/.zshrc`
- future Bash and Python CLIs that want a single, shared environment contract

## Usage

Source it from a shell startup file or from another script:

```bash
source /path/to/base/cli/env/baseenv.sh
```

It must be sourced rather than executed.

## Stable Exports

- `BASE_REPO_ROOT`
- `BASE_CLI_ROOT`
- `BASE_CLI_ENV_SCRIPT`
- `BASE_BASH_ROOT`
- `BASE_PYTHON_ROOT`

These are the environment variables that Base treats as the public cross-process contract.

## Additional Shell Variables

`baseenv.sh` also defines a few derived shell variables for the current shell session:

- `BASE_CLI_ENV_DIR`
- `BASE_BASH_BIN_DIR`
- `BASE_BASH_LIB_DIR`
- `BASE_BASH_COMMANDS_DIR`

These are intentionally not exported to child processes by default. They are easy to derive from the stable roots and are mainly convenience values for sourced scripts and interactive inspection.

`baseenv.sh` also prepends `cli/bash/bin` to `PATH` when that directory exists, without duplicating the entry on repeated sourcing.

## Compatibility

`baseenv.sh` is designed to work in both Bash and zsh.

## Tests

Run the environment bootstrap test suite with:

```bash
bats cli/env/tests/baseenv.bats
```
