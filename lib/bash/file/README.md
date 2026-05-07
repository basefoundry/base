# `lib_file.sh`

File-oriented Bash helpers shared by CLI commands.

## Dependency

Source `lib/bash/std/lib_std.sh` before this library so logging and error helpers are available.

## Public API

- `update_file_section`
  Idempotently add, replace, or remove a marker-delimited block inside a file.

## Usage

```bash
source "/absolute/path/to/lib/bash/std/lib_std.sh"
source "/absolute/path/to/lib/bash/file/lib_file.sh"

update_file_section ~/.bash_profile "# BEGIN APP" "# END APP" \
    "export APP_HOME=/opt/app" \
    "alias appctl='app status'"
```

## Behavior Notes

- Returns success when the target file does not exist and there is nothing to remove.
- Replaces only the first matching marked section when markers already exist.
- Appends the marked block when markers are not present.

## Tests

BATS coverage lives in `tests/lib_file.bats`.
