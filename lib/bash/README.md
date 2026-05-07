# `lib/bash`

Reusable Bash libraries for Base-owned command wrappers and other Bash tooling.

## Layout

- `std/`
  Foundation library with logging, error handling, PATH helpers, and other
  shared Bash primitives.
- `git/`
  Git-related helpers built on top of the stdlib.
- `file/`
  File-editing helpers built on top of the stdlib.
- `tests/`
  Common BATS helpers for Bash library test suites.

These libraries are separate from `cli/bash/commands/`, which holds runnable
commands rather than sourceable modules.
