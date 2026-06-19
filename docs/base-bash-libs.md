# Base Bash Libraries

Base's reusable Bash libraries live in the standalone
[`basefoundry/base-bash-libs`](https://github.com/basefoundry/base-bash-libs)
repository. That repository lets scripts use Base's Bash logging, command
execution, filesystem, and Git helper conventions without adopting the full
Base workspace control plane.

This page documents the Base-side consumption and post-migration contract. Library
APIs and standalone examples live in the `base-bash-libs` repository.

## Current Boundary

The standalone reusable library package owns:

- `lib/bash/std`
- `lib/bash/file`
- `lib/bash/git`
- shared BATS helpers needed by those library test suites

Base still owns Base-specific runtime files, including:

- `lib/bash/runtime`
- `lib/bash/version`
- Base runtime bootstrap through `base_init.sh`
- Base command dispatch and project activation

Base no longer bundles the reusable `std`, `file`, or `git` libraries. Base
commands consume those libraries from `base-bash-libs`.

## Standalone Installation

Users who want only the Bash libraries can install them from the existing
Homebrew tap:

```bash
brew trust basefoundry/base
brew install basefoundry/base/base-bash-libs
```

The trust step is required on Homebrew versions that block formulae from
non-official taps until the tap is trusted. It is safe to run again on machines
that already trust `basefoundry/base`.

Standalone scripts can then source the stdlib from the installed prefix:

```bash
base_bash_libs_prefix="$(brew --prefix basefoundry/base/base-bash-libs)"
source "$base_bash_libs_prefix/libexec/lib/bash/std/lib_std.sh"
```

Companion libraries should be loaded through the stdlib's absolute import
helper:

```bash
import "$base_bash_libs_prefix/libexec/lib/bash/file/lib_file.sh"
import "$base_bash_libs_prefix/libexec/lib/bash/git/lib_git.sh"
```

For source checkout development, clone the repository next to Base or source it
directly from the checkout path:

```bash
git clone https://github.com/basefoundry/base-bash-libs.git ~/work/base-bash-libs
source "$HOME/work/base-bash-libs/lib/bash/std/lib_std.sh"
```

## How Base Resolves Libraries

When `basectl` loads `base_init.sh`, Base resolves `BASE_BASH_LIBS_DIR` before
it sources the Bash stdlib. Base also exports `BASE_BASH_LIBS_SOURCE` so
diagnostics can report which external path won: `explicit`, `sibling`, or
`homebrew`. The resolution order is:

1. An explicit `BASE_BASH_LIBS_DIR` provided before runtime bootstrap.
2. A sibling source checkout at `$BASE_HOME/../base-bash-libs/lib/bash`.
3. A Homebrew package at
   `<homebrew-prefix>/opt/base-bash-libs/libexec/lib/bash` when `BASE_HOME`
   looks like a Homebrew Base install.

An explicit `BASE_BASH_LIBS_DIR` must contain `std/lib_std.sh`; otherwise Base
fails early with a direct error. If no explicit, sibling, or Homebrew source is
available, Base fails during runtime bootstrap with an actionable install or
checkout message. The variable is intended for tests and nonstandard source
worktree development. Users should not set it in `~/.baserc`, shell dotfiles,
or project activation scripts.

Base command implementations should not source these files by absolute path.
They should rely on `basectl` to establish the runtime and then import reusable
libraries by convention:

```bash
import_base_lib file/lib_file.sh
import_base_lib git/lib_git.sh
```

`import_base_lib` checks only the resolved reusable library root. Base-specific
runtime and version helpers remain in `basefoundry/base` under `lib/bash`, but
the reusable libraries come from `base-bash-libs`.

## Post-Migration Contract

The Base contract is external-required:

- Base consumes `base-bash-libs` from a sibling checkout during source
  development.
- Nonstandard worktrees can set `BASE_BASH_LIBS_DIR` to a compatible
  `base-bash-libs/lib/bash` directory before runtime bootstrap.
- Homebrew Base consumes the Homebrew `base-bash-libs` package declared by the
  tap formula.
- `basectl check` and `basectl doctor` emit `BASE-D007` as ok when the external
  source is explicit, sibling, or Homebrew.
- CI checks out `base-bash-libs` and validates Base without bundled reusable
  directories.

The Python `base_cli` extraction is a separate effort and is not part of this
Bash library migration.
