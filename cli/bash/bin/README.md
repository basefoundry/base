# `cli/bash/bin`

This directory holds the user-facing Bash entrypoints.

## Layout

- `base-wrapper`
  A symlink to the canonical wrapper at `../../../bin/base-wrapper`.
- `<command>.sh` symlinks
  Each command symlink points to `base-wrapper`. The wrapper uses the invoked filename to decide which command to run.
- `tests/`
  Wrapper-specific BATS coverage for `base-wrapper`.

## How `base-wrapper` Works

The wrapper supports two invocation styles:

```bash
base-wrapper <command>.sh [args...]
base-wrapper ./path/to/script.sh [args...]
<command>.sh [args...]
```

Behavior:

- When invoked as `base-wrapper`, the first argument is treated as either a Base-owned command name or an explicit script path.
- Bash entrypoint symlinks are expected to end in `.sh`.
- When invoked through a symlink, the wrapper strips the `.sh` suffix and uses the remaining name as the command name.
- Commands are resolved under `../commands/<name>/<name>.sh`.
- Script paths that contain `/` are executed directly after Base bootstraps the environment and stdlib.

## What the Wrapper Provides

Before sourcing the command script, `base-wrapper`:

- sources `../../env/baseenv.sh` to initialize the shared CLI environment
- resolves the repository, CLI, and Bash root directories
- makes wrapper metadata available to sourced command scripts:
  - `BASE_REPO_ROOT`
  - `BASE_CLI_ROOT`
  - `BASE_BASH_ROOT`
  - `BASE_BASH_BIN_DIR`
  - `BASE_CLI_ENV_SCRIPT`
  - `BASE_BASH_COMMAND_NAME`
  - `BASE_BASH_COMMAND_DIR`
  - `BASE_BASH_COMMAND_SCRIPT`
- preloads `../lib/std/lib_std.sh`

That means command scripts inherit both the shared environment and the stdlib helpers without having to source them directly. The wrapper metadata is available in the wrapper shell because Base commands are sourced, but it is not part of the stable exported environment contract for child processes.

The wrapper also sets `BASE_BASH_BOOTSTRAP_SOURCE` before loading the stdlib so stdlib path detection still treats the command script as the real caller.

`baseenv.sh` is also meant to be sourced from a user's shell startup file:

```bash
source /path/to/base/cli/env/baseenv.sh
```

That keeps interactive shells and wrapper-launched commands on the same environment contract.

## Examples

Direct dispatch:

```bash
base-wrapper my-command.sh --flag value
```

Symlink dispatch:

```bash
ln -s base-wrapper cli/bash/bin/my-command.sh
cli/bash/bin/my-command.sh --flag value
```

Explicit script-path dispatch:

```bash
base-wrapper ./tools/my-script.sh --flag value
```

## Tests

Run the wrapper test suite with:

```bash
cd cli/bash
bats bin/tests/base-wrapper.bats
```
