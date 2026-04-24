# `cli/bash/bin`

This directory holds the user-facing Bash entrypoints.

## Layout

- `bash-wrapper`
  The shared dispatcher used to launch Bash commands.
- `<command>.sh` symlinks
  Each command symlink points to `bash-wrapper`. The wrapper uses the invoked filename to decide which command to run.
- `tests/`
  Wrapper-specific BATS coverage for `bash-wrapper`.

## How `bash-wrapper` Works

The wrapper supports two invocation styles:

```bash
bash-wrapper <command>.sh [args...]
<command>.sh [args...]
```

Behavior:

- When invoked as `bash-wrapper`, the first argument is treated as the command name.
- Bash entrypoint symlinks are expected to end in `.sh`.
- When invoked through a symlink, the wrapper strips the `.sh` suffix and uses the remaining name as the command name.
- Commands are resolved under `../commands/<name>/<name>.sh`.

## What the Wrapper Provides

Before sourcing the command script, `bash-wrapper`:

- sources `../../env/banyanenv.sh` to initialize the shared CLI environment
- resolves the repository, CLI, and Bash root directories
- exports wrapper metadata:
  - `BANYAN_REPO_ROOT`
  - `BANYAN_CLI_ROOT`
  - `BANYAN_BASH_ROOT`
  - `BANYAN_BASH_BIN_DIR`
  - `BANYAN_CLI_ENV_SCRIPT`
  - `BANYAN_BASH_COMMAND_NAME`
  - `BANYAN_BASH_COMMAND_DIR`
  - `BANYAN_BASH_COMMAND_SCRIPT`
- preloads `../lib/std/lib_std.sh`

That means command scripts inherit both the shared environment and the stdlib helpers without having to source them directly.

The wrapper also sets `BANYAN_BASH_BOOTSTRAP_SOURCE` before loading the stdlib so stdlib path detection still treats the command script as the real caller.

`banyanenv.sh` is also meant to be sourced from a user's shell startup file:

```bash
source /path/to/base/cli/env/banyanenv.sh
```

That keeps interactive shells and wrapper-launched commands on the same environment contract.

## Examples

Direct dispatch:

```bash
cli/bash/bin/bash-wrapper my-command.sh --flag value
```

Symlink dispatch:

```bash
ln -s bash-wrapper cli/bash/bin/my-command.sh
cli/bash/bin/my-command.sh --flag value
```

## Tests

Run the wrapper test suite with:

```bash
cd cli/bash
bats bin/tests/bash-wrapper.bats
```
