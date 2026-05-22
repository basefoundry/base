# `lib_std.sh`

Shared foundation library for Bash code under `cli/bash`.

## What It Provides

- Bash version checking and one-time initialization when sourced
- Shared globals for callers: `__SCRIPT_ARGS__` and `__SCRIPT_DIR__`
- Library importing with `import`
- PATH helpers: `add_to_path`, `dedupe_path`, `print_path`
- Structured logging with `set_log_level`, `log_*`, and `print_*`
- Failure helpers: `exit_if_error`, `fatal_error`, `dump_trace`
- Safe command execution via `run`
- Filesystem helpers such as `safe_mkdir`, `safe_touch`, `safe_truncate`, `safe_cd`
- Validation helpers such as `assert_not_null`, `assert_integer`, `assert_integer_range`, `assert_arg_count`
- Small interactive helpers such as `ask_yes_no` and `wait_for_enter`

## Usage

Standalone script usage:

```bash
source "/absolute/path/to/lib/bash/std/lib_std.sh"

add_to_path -p "/opt/my-tools/bin"
set_log_level DEBUG
run echo "hello"
```

## Notes

- Requires Bash 4.0 or newer.
- Sourcing the file runs `__stdlib_init__`.
- `base_init.sh` preloads this library for Base-run scripts so commands do not need per-command stdlib sourcing boilerplate.
- `bin/basectl` sets `BASE_BASH_BOOTSTRAP_SOURCE` before runtime bootstrap so `__SCRIPT_DIR__` still points at the command script rather than the Base entrypoint.
- Runtime flags such as `--debug-wrapper` and `--verbose-wrapper` are consumed during initialization for compatibility.
- Other Bash libraries in this tree rely on this file for logging and error handling.

## Tests

BATS coverage lives in `tests/lib_std.bats`.
