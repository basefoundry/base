# `setup`

Bootstrap the local Base CLI environment on macOS.

## What It Does

The command is intentionally small and idempotent.

## Commands

- `install`
  Installs Homebrew, Xcode Command Line Tools, Python 3.13, BATS, and creates `$HOME/.base.d/.venv`.
- `check`
  Verifies the required local CLI setup without making changes. Exits non-zero if anything is missing.
- `update-profile`
  Reserved for future shell profile updates. This subcommand is not implemented yet.

## Install Behavior

The `install` command performs these steps:

1. install Homebrew if it is not already installed
2. install Xcode Command Line Tools if they are not already installed
3. install Python 3.13 via Homebrew if it is not already installed
4. install BATS via Homebrew if it is not already installed
5. create `$HOME/.base.d/.venv` if it does not already exist

## Check Behavior

The `check` command verifies the same base requirements as `install`:

1. Homebrew is installed
2. Xcode Command Line Tools are installed
3. Python 3.13 is installed via Homebrew
4. BATS is installed via Homebrew
5. `$HOME/.base.d/.venv` exists

It exits with status `0` when everything is present and `1` when any required item is missing.

## What It Does Not Do Yet

- update shell profiles such as `~/.bashrc` or `~/.zshrc`
- uninstall previously installed tools
- manage application-specific Python packages inside the virtual environment

## Usage

Preferred umbrella CLI usage:

```bash
base setup install
```

Via the wrapper:

```bash
base-wrapper setup.sh install
```

Via the symlinked entrypoint:

```bash
cli/bash/bin/setup.sh install
```

Check:

```bash
cli/bash/bin/setup.sh check
```

Help:

```bash
cli/bash/bin/setup.sh --help
```

Dry run:

```bash
cli/bash/bin/setup.sh install --dry-run
```

Verbose/debug logging:

```bash
cli/bash/bin/setup.sh -v install
```

## Configuration

The command supports a few environment-variable overrides, mainly for automation and tests:

- `BASE_SETUP_VENV_DIR`
- `BASE_SETUP_PYTHON_FORMULA`
- `BASE_SETUP_BATS_FORMULA`
- `BASE_SETUP_PYTHON_BIN`
- `BASE_SETUP_BREW_BIN`
- `BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT`
- `BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR`

## Tests

Run the command test suite with:

```bash
bats cli/bash/commands/setup/tests/setup.bats
```
