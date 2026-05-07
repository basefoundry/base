# `cli/env`

This directory holds the shared CLI environment bootstrap.

The script currently keeps its historical name, `banyanenv.sh`, during the
migration from the old `banyanlabs` repo into `base`.

## Purpose

`banyanenv.sh` defines the common shell environment used by:

- `cli/bash/bin/base-wrapper`
- interactive shells that source it from `~/.bashrc` or `~/.zshrc`
- future Bash and Python CLIs that want a single, shared environment contract

## Usage

Source it from a shell startup file or from another script:

```bash
source /path/to/base/cli/env/banyanenv.sh
```

It must be sourced rather than executed.

## What It Exports

- `BANYAN_REPO_ROOT`
- `BANYAN_CLI_ROOT`
- `BANYAN_CLI_ENV_DIR`
- `BANYAN_CLI_ENV_SCRIPT`
- `BANYAN_BASH_ROOT`
- `BANYAN_BASH_BIN_DIR`
- `BANYAN_BASH_LIB_DIR`
- `BANYAN_BASH_COMMANDS_DIR`
- `BANYAN_PYTHON_ROOT`

It also prepends `cli/bash/bin` to `PATH` when that directory exists, without duplicating the entry on repeated sourcing.

## Compatibility

`banyanenv.sh` is designed to work in both Bash and zsh.

## Tests

Run the environment bootstrap test suite with:

```bash
bats cli/env/tests/banyanenv.bats
```
