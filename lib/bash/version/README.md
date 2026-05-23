# `lib_version.sh`

Base version helpers that are safe to source before the full Base runtime is
loaded.

## Public API

- `base_read_version`
  Read the first line of `$BASE_HOME/VERSION` for a caller-provided Base home,
  returning `unknown` when the version file is missing or empty.

## Usage

```bash
source "/absolute/path/to/lib/bash/version/lib_version.sh"

printf 'basectl %s\n' "$(base_read_version "$BASE_HOME")"
```

## Behavior Notes

- This library intentionally does not depend on `lib_std.sh`.
- `bin/basectl` uses it before `base_init.sh` is sourced so `basectl --version`
  stays available early in startup.
- The runtime `basectl version` command uses the same helper after Base home has
  been validated.

## Tests

BATS coverage lives in `tests/lib_version.bats`.
