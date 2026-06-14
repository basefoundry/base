# `lib_std.sh`

`lib_std.sh` is Base's foundation library for Bash scripts.

Bash is excellent glue, but raw Bash makes it too easy for every script to
invent its own logging, path handling, argument conventions, dry-run behavior,
error reporting, and import rules. `lib_std.sh` gives Base Bash code one shared
toolbox so scripts can stay small, readable, and consistent.

## Why This Makes Bash Scripting Better

The library improves Bash-based scripting in a few practical ways:

- **Consistent logs**: every script can emit timestamped logs with level and
  source location.
- **Logs stay on stderr**: stdout remains available for real program output that
  another command may pipe or capture.
- **Readable failures**: fatal errors include a message and Bash stack trace
  instead of a mysterious non-zero exit.
- **Safe command execution**: `run` preserves argument boundaries, supports
  dry-run mode, and can either exit or return a status.
- **Shared dry-run behavior**: scripts do not need to reimplement "print what
  would happen" logic.
- **Simple library imports**: scripts can import helpers relative to their own
  source directory.
- **Predictable PATH edits**: PATH additions avoid duplicates and can prepend or
  append intentionally.
- **Batch validation**: required variables, files, directories, commands, and
  integer ranges can be checked with one helper call.
- **Safer filesystem helpers**: common operations report all failures in one
  clear error.
- **Base wrapper integration**: wrapper flags are recognized once and removed
  before command-specific argument parsing begins.

The goal is not to hide Bash. The goal is to make Base scripts look like they
belong to the same product and fail in ways a user or developer can understand.

## Loading The Library

Standalone scripts can source the library directly:

```bash
source "/absolute/path/to/lib/bash/std/lib_std.sh"
```

Most Base command scripts do not need to do this manually. `base_init.sh`
preloads `lib_std.sh` when commands run through `basectl`, which means Base-run
scripts already have functions such as `log_info`, `run`, and `fatal_error`
available.

Base entrypoints require Bash 4.2 or newer before sourcing this library. The
library has passive Bash version helpers, but sourcing it does not prompt,
install packages, or re-exec the caller.

## Initialization Contract

Sourcing `lib_std.sh` runs a small one-time initializer:

- initializes the logging level map
- records the original script arguments in `__SCRIPT_ARGS__`
- derives the caller's source directory in `__SCRIPT_DIR__`
- consumes Base wrapper flags such as `--debug-wrapper`, `--verbose-wrapper`,
  `--utc-wrapper`, and `--color`
- resets the caller's positional parameters to the filtered argument list

Caller-visible globals:

- `__SCRIPT_ARGS__`: original arguments before wrapper flags were stripped
- `__SCRIPT_DIR__`: absolute source directory for the script being bootstrapped

When a Base wrapper preloads the stdlib for another command, it can set
`BASE_BASH_BOOTSTRAP_SOURCE` so `__SCRIPT_DIR__` still points at the command
script rather than the wrapper.

## Logging

Use structured logging for operational messages:

```bash
log_info "Installing package '$name'."
log_warn "Cache directory does not exist: $cache_dir"
log_error "Unable to read manifest '$manifest_path'."
log_debug "resolved_home=$resolved_home"
log_verbose "raw_response=$response"
```

Available levels:

- `FATAL`
- `ERROR`
- `WARN`
- `INFO`
- `DEBUG`
- `VERBOSE`

Change the default logger's level with:

```bash
set_log_level DEBUG
```

Named loggers are also supported:

```bash
set_log_level -l artifact DEBUG
log_debug -l artifact "registry key: $key"
```

For user-facing messages that should not include timestamps or source
locations, use:

```bash
print_error "Invalid project name."
print_warn "Using default workspace."
print_info "Setup complete."
print_success "Done."
print_message "plain stdout message"
```

`log_*`, `print_error`, `print_warn`, `print_info`, and `print_success` write to
stderr. `print_message` writes to stdout.

## Error Handling

Use `fatal_error` when the script cannot continue:

```bash
[[ -f "$manifest_path" ]] || fatal_error "Manifest '$manifest_path' was not found."
```

Use `exit_if_error` when checking a command's explicit status:

```bash
some_command
exit_if_error $? "some_command failed."
```

Fatal failures log the message, dump a Bash stack trace, and exit with the
original failing status when possible.

Not every user mistake should be fatal. Command-line usage errors should usually
print usage and return `2` rather than calling `fatal_error`, because the command
itself is fine and the user simply gave invalid arguments.

## Running Commands Safely

`run` is the preferred helper for simple external command execution:

```bash
run git status --short
run touch "file with spaces.txt"
```

It improves on ad hoc command strings because it:

- executes commands as argument arrays, not through `eval`
- preserves spaces and special characters
- logs a copy-pastable command in dry-run mode
- exits through `exit_if_error` by default when a command fails

Dry-run mode:

```bash
DRY_RUN=true
run brew install jq
```

`DRY_RUN` and `dry_run` both accept `true`, `1`, `yes`, and `on`. Use
`is_dry_run` when a script needs to branch on the same normalized dry-run state
without executing a command through `run`.

Handle a failing command yourself with `--no-exit`:

```bash
if ! run --no-exit grep "needle" "$file"; then
    log_info "needle was not present; continuing"
fi
```

Use `run` for commands plus arguments. Keep shell features such as pipelines,
redirection, process substitution, and complex conditionals explicit in the
calling script so the code remains clear.

## Importing Other Bash Libraries

Use `import` to source helper libraries:

```bash
import file/lib_file.sh
import /absolute/path/to/another_lib.sh
```

Relative imports resolve from `__SCRIPT_DIR__`, which is the directory of the
script being bootstrapped.

Important Bash detail: imported files are sourced inside the `import` function.
If an imported library needs global variables, declare them with `-g`:

```bash
declare -gA MY_LOOKUP=()
```

Without `-g`, Bash may create locals scoped to the import function.

## PATH Helpers

Use `add_to_path` instead of hand-editing PATH:

```bash
add_to_path "/opt/tool/bin"
add_to_path -p "$HOME/.local/bin"
add_to_path -n "$maybe_created_later/bin"
```

Options:

- `-p`: prepend instead of append
- `-n`: do not require the directory to already exist

`add_to_path` de-duplicates PATH after adding entries. You can also call:

```bash
dedupe_path
print_path
```

## Filesystem Helpers

The safe filesystem helpers collect failures and report them clearly:

```bash
safe_mkdir -p "$state_dir" "$cache_dir"
safe_touch "$log_file"
safe_truncate "$log_file"
safe_cd "$project_root"
```

These helpers are useful in setup scripts where a partially completed operation
should fail loudly and explain which path could not be created, touched, or
entered.

## Validation Helpers

Use assertions near the top of functions to make assumptions explicit:

```bash
assert_arg_count "$#" 2
assert_not_null BASE_HOME project_name
assert_integer retry_count
assert_integer_range retry_count 0 5
assert_command_exists git brew
assert_file_exists "$manifest_path"
assert_dir_exists "$project_root"
```

`assert_not_null` takes variable names, not expanded values. Use
`assert_not_null TOKEN`, not `assert_not_null "$TOKEN"`. When an argument is not
a valid Bash variable name, `assert_not_null` reports likely misuse without
echoing the invalid value.

The assertions favor clear failure messages over scattered one-off tests. Some
helpers check all provided values and report all missing items together.

## Interactive Helpers

For interactive scripts:

```bash
if ask_yes_no "Continue?"; then
    log_info "Continuing."
fi

wait_for_enter "Press Enter after reviewing the output."
```

Use `is_interactive` before prompting from code paths that might run in CI,
cron, or another non-interactive environment:

```bash
if is_interactive; then
    ask_yes_no "Install optional tools?" || return 0
fi
```

## Suggested Script Pattern

A small Base-style Bash command should look like this:

```bash
#!/usr/bin/env bash

main() {
    local project="${1:-}"

    if [[ -z "$project" ]]; then
        print_error "Project name is required."
        return 2
    fi

    assert_command_exists git
    log_info "Checking project '$project'."
    run git status --short
}

main "$@"
```

When the script runs through `basectl`, the Base runtime provides the stdlib and
calls `main` with wrapper flags already filtered out.

For standalone scripts that source the library directly:

```bash
#!/usr/bin/env bash
source "/path/to/base/lib/bash/std/lib_std.sh"

main() {
    set_log_level DEBUG
    run echo "hello"
}

main "$@"
```

## What Belongs Here

`lib_std.sh` should contain small, broadly useful primitives for Bash code:

- logging
- error handling
- path manipulation
- command execution
- imports
- validation
- simple filesystem safety wrappers

Domain-specific behavior should live in other libraries or command modules. For
example, Git helpers belong in a Git library, file editing helpers belong in a
file library, and artifact setup behavior belongs in setup code.

## Tests

BATS coverage lives in:

```text
lib/bash/std/tests/lib_std.bats
```

When changing this library, run:

```bash
bats lib/bash/std/tests/lib_std.bats
```

For command-level changes that depend on stdlib behavior, also run the relevant
command BATS tests.
