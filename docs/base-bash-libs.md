# Base Bash Libraries

Base's reusable Bash libraries are being extracted into the standalone
[`codeforester/base-bash-libs`](https://github.com/codeforester/base-bash-libs)
repository. That repository lets scripts use Base's Bash logging, command
execution, filesystem, and Git helper conventions without adopting the full
Base workspace control plane.

This page documents the Base-side consumption and migration contract. Library
APIs and standalone examples live in the `base-bash-libs` repository.

## Current Boundary

The standalone reusable library package owns:

- `lib/bash/std`
- `lib/bash/file`
- `lib/bash/git`
- shared BATS helpers needed by those library test suites

Base still owns Base-specific runtime files, including:

- `lib/bash/runtime`
- Base runtime bootstrap through `base_init.sh`
- Base command dispatch and project activation

During the migration window, Base also keeps bundled copies of the reusable
library directories. Those copies are a compatibility fallback, not the
long-term source of truth.

## Standalone Installation

Users who want only the Bash libraries can install them from the existing
Homebrew tap:

```bash
brew trust codeforester/base
brew install codeforester/base/base-bash-libs
```

The trust step is required on Homebrew versions that block formulae from
non-official taps until the tap is trusted. It is safe to run again on machines
that already trust `codeforester/base`.

Standalone scripts can then source the stdlib from the installed prefix:

```bash
base_bash_libs_prefix="$(brew --prefix codeforester/base/base-bash-libs)"
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
git clone https://github.com/codeforester/base-bash-libs.git ~/work/base-bash-libs
source "$HOME/work/base-bash-libs/lib/bash/std/lib_std.sh"
```

## How Base Resolves Libraries

When `basectl` loads `base_init.sh`, Base resolves `BASE_BASH_LIBS_DIR` before
it sources the Bash stdlib. Base also exports `BASE_BASH_LIBS_SOURCE` so
diagnostics can report which path won: `explicit`, `sibling`, `homebrew`, or
`bundled`. The resolution order is:

1. An explicit `BASE_BASH_LIBS_DIR` provided before runtime bootstrap.
2. A sibling source checkout at `$BASE_HOME/../base-bash-libs/lib/bash`.
3. A Homebrew package at
   `<homebrew-prefix>/opt/base-bash-libs/libexec/lib/bash` when `BASE_HOME`
   looks like a Homebrew Base install.
4. Base's bundled fallback at `$BASE_HOME/lib/bash`.

An explicit `BASE_BASH_LIBS_DIR` must contain `std/lib_std.sh`; otherwise Base
fails early with a direct error. The variable is intended for tests, source
checkout development, and controlled migration checks. Users should not set it
in `~/.baserc`, shell dotfiles, or project activation scripts.

Base command implementations should not source these files by absolute path.
They should rely on `basectl` to establish the runtime and then import reusable
libraries by convention:

```bash
import_base_lib file/lib_file.sh
import_base_lib git/lib_git.sh
```

`import_base_lib` checks the resolved reusable library root first. If a
requested companion library is not present there and the resolved reusable root
is not the bundled Base root, it falls back to `$BASE_BASH_LIB_DIR`. That keeps
Base working while the external package and Base-owned runtime files are still
being separated.

## Migration Contract

The current Base contract is external-first, bundled-fallback:

- Base can consume `base-bash-libs` from a sibling checkout.
- Base can consume `base-bash-libs` from Homebrew when the formula is installed.
- Base still works without the external package because the bundled reusable
  libraries remain in `codeforester/base`.
- `basectl check` and `basectl doctor` emit `BASE-D007` as a warning when Base
  is still using the bundled fallback, and as ok when the external source is
  explicit, sibling, or Homebrew.

The bundled reusable libraries should not be removed from Base until the
external path is normal, validated, and diagnosable for both Homebrew users and
source checkout contributors. The practical removal gate is:

1. `base-bash-libs` has a released version and installable Homebrew formula.
2. Homebrew Base declares `base-bash-libs` as a dependency, or an equivalent
   install path makes the external package present by default.
3. Source checkout setup documents or installs the sibling `base-bash-libs`
   checkout clearly enough that raw `git clone` development is not fragile.
4. Base setup, check, or doctor paths report missing external Bash libraries
   clearly where that state can affect users. `BASE-D007` now covers the
   check and doctor side of this gate.
5. CI validates Base without relying on the bundled reusable directories. The
   `base_init` BATS suite now includes a temporary Base home with bundled
   reusable `std`, `file`, and `git` directories removed and external
   `base-bash-libs` provided through the sibling checkout path.
6. A Base release cycle has passed with the external package as the normal path
   and without needing the fallback for ordinary installs.

Only after those gates are satisfied should Base remove the bundled reusable
directories. If Base intentionally keeps the fallback long term, that decision
should be recorded explicitly and the extraction tracker should close only
after that policy is clear.

The Python `base_cli` extraction is a separate effort and is not part of this
Bash library migration.
