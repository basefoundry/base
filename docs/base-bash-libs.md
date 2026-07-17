# Base Bash Libraries

Base's reusable Bash libraries live in the standalone
[`basefoundry/base-bash-libs`](https://github.com/basefoundry/base-bash-libs)
repository. That repository lets scripts use Base's Bash logging, argument
parsing, command execution, filesystem, Git, GitHub CLI, list, and string helper
conventions without adopting the full Base workspace control plane.

This page documents the Base-side consumption and post-migration contract. Library
APIs and standalone examples live in the `base-bash-libs` repository.

## Current Boundary

The standalone reusable library package owns:

- `lib/bash/std`
- `lib/bash/arg`
- `lib/bash/file`
- `lib/bash/gh`
- `lib/bash/git`
- `lib/bash/list`
- `lib/bash/str`
- shared BATS helpers needed by those library test suites

Base still owns Base-specific runtime files, including:

- `lib/bash/runtime`
- `lib/bash/version`
- Base runtime bootstrap through `base_init.sh`
- Base command dispatch and project activation

Base no longer bundles those reusable libraries. Base commands consume them from
`base-bash-libs`.

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
helper. For example:

```bash
import "$base_bash_libs_prefix/libexec/lib/bash/arg/lib_arg.sh"
import "$base_bash_libs_prefix/libexec/lib/bash/file/lib_file.sh"
import "$base_bash_libs_prefix/libexec/lib/bash/gh/lib_gh.sh"
import "$base_bash_libs_prefix/libexec/lib/bash/git/lib_git.sh"
import "$base_bash_libs_prefix/libexec/lib/bash/list/lib_list.sh"
import "$base_bash_libs_prefix/libexec/lib/bash/str/lib_str.sh"
```

For source checkout development, clone the repository next to Base or source it
directly from the checkout path:

```bash
git clone https://github.com/basefoundry/base-bash-libs.git ~/work/base-bash-libs
source "$HOME/work/base-bash-libs/lib/bash/std/lib_std.sh"
```

## Homebrew/Core Readiness

The current public package lives in the `basefoundry/homebrew-base` tap as
`Formula/base-bash-libs.rb`. That formula is intentionally shaped so it can be
prepared for Homebrew/core without changing the Base runtime contract:

- it installs from the stable `basefoundry/base-bash-libs` release archive;
- it declares SPDX license metadata with `license "Apache-2.0"`;
- it keeps the Homebrew package name `base-bash-libs`;
- it depends only on Homebrew `bash`;
- it installs reusable libraries under `libexec/lib/bash`;
- it includes README, changelog, license, notice, and examples under
  `pkgshare`; and
- its formula test sources `lib_std.sh`, imports representative companion
  libraries, and verifies expected public functions through Homebrew Bash.

Before submitting or refreshing a Homebrew/core proposal, validate the tap
formula by name, not by local formula path:

```bash
brew test basefoundry/base/base-bash-libs
brew audit --new --formula basefoundry/base/base-bash-libs
```

The future Homebrew/core path should keep `base-bash-libs` available as its own
formula so the eventual Base formula can depend on it directly:

```ruby
depends_on "base-bash-libs"
```

That lets the intended user-facing Base install remain:

```bash
brew install basefoundry
```

Until Homebrew/core accepts those formulae, users should continue installing
Base and the standalone libraries from the existing tap with the explicit
`basefoundry/base/...` formula names documented above.

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

An explicit `BASE_BASH_LIBS_DIR` must contain `std/lib_std.sh`, and the loaded
package must be from the corrected 1.x release line at version 1.3.0 or newer.
Base rejects stale 1.x checkouts and incompatible major-version checkouts during
runtime bootstrap with a direct diagnostic. If no explicit, sibling, or
Homebrew source is available, Base fails during runtime bootstrap with an
actionable install or checkout message. The variable is intended for tests and
nonstandard source worktree development. Users should not set it in `~/.baserc`,
shell dotfiles, or project activation scripts.

Base command implementations should not source these files by absolute path.
They should rely on `basectl` to establish the runtime and then import reusable
libraries by convention:

```bash
import_base_lib arg/lib_arg.sh
import_base_lib file/lib_file.sh
import_base_lib gh/lib_gh.sh
import_base_lib git/lib_git.sh
import_base_lib list/lib_list.sh
import_base_lib str/lib_str.sh
```

`import_base_lib` checks only the resolved reusable library root. Base-specific
runtime and version helpers remain in `basefoundry/base` under `lib/bash`, but
the reusable libraries come from `base-bash-libs`.

The stdlib `import` helper is for standalone scripts that have already sourced
`lib_std.sh`. Inside Base, do not treat `import` as a blanket replacement for
Bash `source`: `base_init.sh` still sources the stdlib, and Base-owned command
modules, shell startup files, virtual environment activation scripts, OS
metadata files, and project activation scripts should continue to use
purpose-specific `source` calls.

## Post-Migration Contract

The Base contract is external-required:

- Base consumes `base-bash-libs` from a sibling checkout during source
  development.
- Nonstandard worktrees can set `BASE_BASH_LIBS_DIR` to a compatible 1.x
  `base-bash-libs/lib/bash` directory at version 1.3.0 or newer before runtime
  bootstrap.
- Homebrew Base consumes the Homebrew `base-bash-libs` package declared by the
  tap formula.
- Base CI pins the source checkout to the immutable `base-bash-libs` v1.3.0
  release commit; runtime compatibility remains a 1.x minimum-version contract.
- `basectl check` and `basectl doctor` emit `BASE-D007` as ok when the external
  source is explicit, sibling, or Homebrew.
- CI checks out `base-bash-libs` and validates Base without bundled reusable
  directories.

The Python `base_cli` extraction is a separate effort and is not part of this
Bash library migration.
