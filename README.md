# Base

![Tests](https://github.com/codeforester/base/actions/workflows/tests.yml/badge.svg)
![Lint](https://github.com/codeforester/base/actions/workflows/pylint.yml/badge.svg)
![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey)
![Version](https://img.shields.io/badge/version-0.1.0-blue)

Base is a foundational developer tooling repo for a multi-project workspace.

Its job is not to be a product repo, a service repo, or a monorepo. Its job is
to provide the common layer that sits above individual project repositories and
makes them easier to set up, run, and test in a consistent way.

This repository already existed as a shell-focused project. The next version of
Base is a deliberate refactor of that idea into a broader workspace bootstrap
and execution layer.

## Why Base Exists

Most real engineering environments are not a single repository.

A developer may need:

- one repo for shared tooling
- several project repos checked out side by side
- a consistent shell environment across machines
- common shell and Python helper libraries
- a clean way to run project commands through wrappers instead of directly

Base exists to provide that missing common layer.

Contributions should follow [CONTRIBUTING.md](CONTRIBUTING.md).

## Top Goals

Base is being refactored around three primary goals.

### 1. Umbrella Interface for Multi-Project Setup and Test

Base should give the user one entry point for setting up and validating a
workspace that contains multiple project repositories.

Current implemented commands include:

- `basectl setup [project]`
- `basectl test [project]`
- `basectl check`
- `basectl doctor`
- `basectl clean --older-than <age>`
- `basectl clean --keep-last <count>`
- `basectl config path`
- `basectl config show`
- `basectl config doctor`
- `basectl onboard`
- `basectl update-profile`
- `basectl update`
- `basectl projects list`
- `basectl activate <project>`
- `basectl version`

The important idea is that the user should not need to memorize a different
bootstrap story for every repository in the workspace.

Base should be able to discover participating project repositories checked out
next to it under a shared parent directory, for example:

```text
~/work/
  base/
  banyanlabs/
  bankbuddy/
  blend/
  brew/
```

Over time, each project repo can declare how Base should interact with it,
likely through a small project manifest or well-defined conventions.

The first version of that manifest is `base_manifest.yaml` at a project repo
root. It declares the project name and the project contracts Base should
orchestrate:

```yaml
project:
  name: example

brewfile: Brewfile

mise: .mise.toml

artifacts:
  - type: python-package
    name: requests
    version: latest

test:
  command: pytest tests/
```

The manifest intentionally describes what the project needs, not arbitrary
commands to execute. Base's direction is delegation-first: use mature tools for
the domains they already own, and keep Base responsible for workspace
orchestration, project discovery, the project virtual environment, and
diagnostics.

The optional top-level `brewfile` field points to a Homebrew `Brewfile` relative
to the project root. When present, `basectl setup` runs
`brew bundle --file=<project-root>/<brewfile>` before reconciling artifacts. Use
this for ordinary Homebrew formulae and casks instead of adding every Homebrew
package to Base's hand-curated artifact registry.

Future manifest fields should follow the same rule. A `mise` field causes Base
to run `mise install` from the project root when a project chooses that
substrate. A `test` field gives `basectl test` a single project-owned command
to run from the project root:

```yaml
test:
  command: pytest tests/
```

Projects that keep tasks in `mise` can declare a mise task instead:

```yaml
test:
  mise: test
```

Base should not run arbitrary setup hooks until there is an explicit,
reviewable contract for when they run, where they run, whether they are
interactive, and how dry-run/check/doctor report them.

The curated tool artifact registry lives in `cli/python/base_setup/registry.py`.
It should stay small and Base-aware. `python-package` artifacts are pass-through
PyPI package names and install into the project virtual environment at
`~/.base.d/<project>/.venv`. Homebrew-managed `tool` artifacts currently support
`version: latest`, but ordinary Homebrew tools should move toward Brewfile
delegation. Pinned Homebrew versions fail clearly until Base grows explicit
versioned tool support.

Artifacts may include `bootstrap: true` when they are part of the minimum Python
runtime contract needed before Base can reconcile a project's remaining
artifacts. Base currently uses this marker in `lib/base/default_manifest.yaml`
for `click` and `PyYAML`.

You can inspect the projects Base can see with:

```bash
basectl projects list
basectl projects list --format json
```

By default this scans the parent directory of `BASE_HOME`, which matches the
recommended sibling-repo workspace layout. Use `--workspace <path>` to inspect a
different workspace root. Output is tab-separated as `<project-name><TAB><path>`.
Use `--format json` for machine-readable output.

Once a project is discoverable, activate it with:

```bash
basectl activate example
```

Activation spawns a project-specific subshell, changes to the project root, sets
`BASE_PROJECT` and related project variables, adds project-owned commands from
`$PROJECT_ROOT/bin` when that directory exists, and activates the project
virtual environment at `~/.base.d/<project>/.venv`. Exit that shell to return to
the original environment.

Use `basectl activate example --no-cd` to keep the caller's current directory
while still loading the selected project's Base runtime environment.

Invoking `basectl` with no arguments in a terminal starts the default
interactive Base shell. It uses the nearest `base_manifest.yaml` above the
current directory to choose the active project, then preserves the current
directory. If no project manifest is found, it falls back to the `base` project.

Clean old Base CLI runtime logs, retained temp files, and cache entries with:

```bash
basectl clean --older-than 30d --dry-run
basectl clean --older-than 30d
basectl clean --keep-last 20
basectl clean --older-than 30d --keep-last 20
```

Cleanup only targets runtime artifacts under the Base cache root, which defaults
to `~/Library/Caches/base` on macOS. Set `BASE_CACHE_DIR` to override it. Durable
state such as `~/.base.d/config.yaml` and project virtual environments under
`~/.base.d/<project>/.venv` are outside this scope.

Inspect machine-local Base config with:

```bash
basectl config path
basectl config show
basectl config doctor
```

Base owns the meaning of `~/.base.d/config.yaml`, but users own how that file is
edited, backed up, or synced. See [docs/local-config.md](docs/local-config.md).

Use `--keep-last <count>` to retain the newest log files per CLI log directory
while pruning older logs. This retention mode applies only to `*.log` files;
temp and cache artifacts continue to use `--older-than`.

Use `basectl doctor` when you want a human-oriented diagnosis with suggested
fixes:

```bash
basectl doctor
basectl doctor --dev
```

`basectl check <project>` and `basectl doctor <project>` extend those checks to
a project's `base_manifest.yaml` artifacts after verifying the Base bootstrap
environment:

```bash
basectl check example
basectl doctor example
```

`basectl onboard` provides a guided checklist for technically-adjacent users who
want a first Base setup flow around check, setup, profile refresh, doctor, and
project discovery. Product-specific onboarding should still live in project
installers that call Base internally. See
[docs/basectl-onboard.md](docs/basectl-onboard.md).

Base can also bootstrap supported IDEs for participating projects through the
optional `ide:` manifest section. It currently supports VS Code and Cursor app
installation, extension installation, additive user settings, and check/doctor
diagnostics. See [docs/ide-bootstrapping.md](docs/ide-bootstrapping.md).

### 2. Shell Environment Management

Base should manage shell environments at two levels:

- global environment shared across the whole workspace
- project-specific environment layered on top for an individual repo

That includes things like:

- common shell initialization
- PATH management
- shared environment variables
- host and OS detection
- project-local activation hooks
- predictable loading order

The goal is to make shell behavior explicit, inspectable, and repeatable instead
of depending on a fragile mix of ad hoc dotfiles and one-off scripts.

### 3. Common Shell and Python Libraries and Wrappers

Base should provide a stable foundation for controlled CLI execution.

That includes:

- shell libraries for logging, errors, files, Git, networking, and standard
  helpers
- Python wrappers for running Python-based tooling with the right environment
- shell wrappers for sourcing shared libraries and normalizing execution context
- a consistent convention for passing arguments, setting environment variables,
  and reporting failures

The wrapper model matters because it keeps command behavior predictable. A CLI
should run inside a known environment instead of relying on whoever happened to
invoke it from whatever shell state they already had.

## Public Command Surface

Base exposes its own commands through `$BASE_HOME/bin`. That directory is added
to `PATH` by Base's managed shell startup snippets.

`bin/basectl` is the control-plane command. Additional public commands, when
needed, are tiny real launcher files in `bin/` that delegate to `basectl`; their
implementation remains under `cli/bash/commands/<command>/` or, in the future,
`cli/python/commands/<command>/`.

Example launcher:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/basectl" caff "$@"
```

Projects expose their own commands through `$PROJECT_ROOT/bin`. When
`basectl activate <project>` starts a project runtime shell, Base adds that
directory to `PATH` if it exists, behind `$BASE_HOME/bin`. Project Python command
packages should be treated as implementation details unless a project-owned
launcher exposes them from `bin/`.

Project launchers that need to run Python packages should delegate through
`base-wrapper` so they use the selected project virtual environment and Base's
Python library roots:

```bash
#!/usr/bin/env bash
exec "$BASE_HOME/bin/base-wrapper" --project "${BASE_PROJECT:-example}" example_cli "$@"
```

`basectl setup` deliberately pins its default Homebrew Python formula so setup is
reproducible across machines. The current default is `python@3.13`. Override it
with `BASE_SETUP_PYTHON_FORMULA` when a workspace needs a different formula.
After this Bash bootstrap layer creates Base's own Python environment, setup
installs Base bootstrap Python packages into that environment. For project
artifact setup, Base first seeds the target project venv with `bootstrap: true`
default artifacts and then invokes the Python project setup layer through
`base-wrapper --project <project>`.
Developer prerequisites such as BATS and the GitHub CLI are opt-in and
manifest-driven through `lib/base/dev_manifest.yaml`; use `basectl setup --dev`
to install them and `basectl check --dev` or `basectl doctor --dev` to verify
them.

If Homebrew is missing, `basectl setup` uses Homebrew's official installer URL
at `https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh`. This is
a deliberate trust decision: Base stays aligned with Homebrew's supported
bootstrap command instead of pinning and maintaining a reviewed installer
commit. Teams that require stricter supply-chain controls should install
Homebrew through their managed device process before running Base.

On macOS, `basectl setup` sends a best-effort notification when setup completes
or fails after running for at least 30 seconds. Notifications are skipped during
`--dry-run` and never change the setup exit status. Use `basectl setup --notify`
to force a notification for quick runs, `basectl setup --no-notify` or
`BASE_SETUP_NOTIFY=false` to disable notifications, and
`BASE_SETUP_NOTIFY_MIN_SECONDS` to tune the default threshold. When `--notify`
is requested on macOS, Base warns if `osascript` is not available.

## Quick Start

Base can be installed through its Homebrew tap:

```bash
brew install codeforester/base/base
basectl setup
basectl update-profile
exec "$SHELL" -l
```

Homebrew installs the Base files. `basectl setup` still prepares the local Base
runtime under `~/.base.d/base/.venv`, and `basectl update-profile` adds Base to
your shell startup path. When installed through Homebrew, update Base with:

```bash
brew upgrade codeforester/base/base
```

The standalone installer is also available:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/install.sh | bash
exec "$SHELL" -l
```

This runs a shell script from GitHub, so review the script first if you do not
already trust this repository:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/install.sh
```

By default, the installer clones or updates Base at `~/work/base`, runs
`~/work/base/bin/basectl setup`, and then runs
`~/work/base/bin/basectl update-profile`. Set `BASE_INSTALL_DIR` or pass
`--dir <path>` to install somewhere else. When using the piped form, pass
installer options with `bash -s --`, for example:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/install.sh | bash -s -- --dir ~/work/base --no-profile
```

Use `--no-profile` to skip shell startup integration and `--dry-run` to print
planned actions.

The explicit manual bootstrap path is:

```bash
git clone https://github.com/codeforester/base.git ~/work/base
~/work/base/bin/basectl setup
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

After the shell restarts, Base's managed startup section adds `~/work/base/bin`
to `PATH`, so `basectl` can be run without spelling out the full path. Use
`basectl version` or `basectl --version` to report the installed Base version.

Project-specific onboarding should live in project installers that call Base
internally. See [Project Installers](docs/project-installers.md) for the
recommended boundary between Base and scripts such as `banyanlabs/install.sh`.

## Documentation

The top-level README is the product overview and first-run guide. The
[docs README](docs/README.md) is the map for architecture, runtime behavior,
feature designs, and ecosystem boundary decisions.

Key starting points:

- [Architecture](docs/architecture.md)
- [Execution Model](docs/execution-model.md)
- [Tool Boundaries](docs/tool-boundaries.md)
- [IDE Bootstrapping](docs/ide-bootstrapping.md)
- [Local Config](docs/local-config.md)

## Compatibility

Base is currently macOS-first. The implemented and tested support contract is
macOS with Homebrew, Xcode Command Line Tools, a Homebrew-managed Bash, Git, and
Python installed through Base setup.

Intended supported platforms are:

- macOS on Apple Silicon
- macOS on Intel Macs
- at least one Linux variant in the future, with the first target still to be decided

The supported macOS version floor is still TBD. Linux support is a design target,
but not yet an implemented or tested support contract. Windows is out of scope.

OS-specific behavior should stay isolated behind small helpers instead of being
scattered through command code. For example, the Base runtime prompt can prefer
macOS `scutil` names while still falling back to generic `hostname`.

## Shell Startup Files

Base integrates with Bash and Zsh through small managed sections in the user's
real dotfiles. Base does not take over whole dotfiles.

The command that installs or refreshes those sections is:

```bash
basectl update-profile
```

By default it updates all four startup files:

- `~/.bash_profile`
- `~/.bashrc`
- `~/.zprofile`
- `~/.zshrc`

Missing files are created. Existing files keep their non-Base content; Base only
adds or replaces its marked section.

`basectl update-profile` also creates `~/.base.d/profile.conf`, which records
whether the user has opted into Base's optional shell defaults. The managed
dotfile sections stay minimal and defer PATH/default handling to the sourced
Base snippets. The same sourced snippets also register `basectl` shell
completions, so future completion improvements arrive when Base is updated
without rewriting user dotfiles.

Run `basectl update-profile --defaults` to enable those optional defaults, and
run `basectl update-profile --no-defaults` to disable them again. Plain
`basectl update-profile` preserves the existing preference.

`BASE_PROFILE_VERSION` records the schema version of this Base-managed file. It
is reserved for future migrations and is not intended to be edited by users.

Update Base itself from the checked-out repository with:

```bash
basectl update
```

This command is intentionally conservative: it only runs from a clean `master`
worktree, pulls the latest changes through Git, and then runs `basectl setup`.

Base also reads `~/.baserc` when it exists. Unlike `profile.conf`, `~/.baserc`
is user-managed and may be hand-edited. It is intended for simple,
shell-startup-safe Base preferences such as `BASE_DEBUG=1`; it should not become
a second `.bashrc` with arbitrary setup logic.

`~/.baserc` must not set Base-owned runtime or profile variables such as
`BASE_HOME`, `BASE_BIN_DIR`, `BASE_LIB_DIR`, `BASE_OS`, `BASE_SHELL`,
`BASE_PROFILE_VERSION`, `BASE_ENABLE_BASH_DEFAULTS`, or
`BASE_ENABLE_ZSH_DEFAULTS`. Base startup snippets reject and restore those
variables if `~/.baserc` tries to change them.

Base-managed sections use explicit markers such as:

```bash
# --- BEGIN base bashrc MANAGED SECTION - DO NOT EDIT ---
# ... Base-managed content ...
# --- END base bashrc MANAGED SECTION - DO NOT EDIT ---
```

### Base Snippets

The managed sections source matching snippets under `lib/shell/`:

- `lib/shell/bash_profile` for `~/.bash_profile`
- `lib/shell/bashrc` for `~/.bashrc`
- `lib/shell/zprofile` for `~/.zprofile`
- `lib/shell/zshrc` for `~/.zshrc`

The names intentionally mirror the dotfiles they support, without leading dots
inside the repository.

Bash snippets and the Bash runtime rcfile share `lib/shell/baserc_guard.sh` for
safe `~/.baserc` loading. Zsh snippets keep their own guard logic for now.

### Login Profiles

`bash_profile` and `zprofile` stay thin.

For Bash, Base makes the login-shell bridge explicit: the Bash profile snippet
sources `~/.bashrc` with a guardrail. Bash needs this because login Bash shells
do not automatically read `~/.bashrc`.

For Zsh, Base does not source `~/.zshrc` from `zprofile`. Zsh already reads
`~/.zshrc` for interactive shells.

### Interactive RC Files

`bashrc` and `zshrc` are where interactive shell behavior belongs.

They are responsible for:

- guarding against non-interactive execution
- guarding against repeated sourcing
- deriving and exporting `BASE_HOME` from the sourced Base snippet
- adding Base's `bin/` directory to `PATH` so `basectl` is available after login
- keeping dotfile integration separate from the full Base runtime bootstrap
- optionally enabling shared shell defaults when `basectl update-profile --defaults` is used

They do not source `base_init.sh`. Base runtime setup happens only when the
`basectl` command runs a Base command, runs an explicit script path, or starts a
Base-enabled Bash shell.

When `basectl activate <project>` starts an interactive Bash runtime shell, it
uses Base's runtime rcfile rather than making Bash read `~/.bashrc` directly.
That runtime rcfile loads `base_init.sh`, sources the user's `~/.bashrc` once
with guardrails, activates the project virtual environment, and finally sets the
Base runtime prompt. This keeps user aliases and normal interactive Bash
behavior available while making Base stdlib functions such as `import_base_lib`
available during user Bash startup.

### Debugging Shell Startup

Set `BASE_DEBUG=1` to make Base-managed shell startup snippets print diagnostic
messages while they run. This is intentionally independent of `base_init.sh` and
stdlib logging, because dotfile debugging can happen before the Base runtime is
loaded.

For normal terminal startup, put this in `~/.baserc`:

```bash
BASE_DEBUG=1
```

For one-off checks, use an environment variable:

```bash
BASE_DEBUG=1 bash --rcfile ~/.bashrc -i
BASE_DEBUG=1 zsh -i
BASE_DEBUG=1 basectl
```

Diagnostics are printed to stderr and show which Base snippet loaded, how
`BASE_HOME` was derived, whether `$BASE_HOME/bin` was added to `PATH`, whether
optional shell defaults were enabled, and how the Base runtime shell was layered.

For command debugging, `basectl -v <command>` enables DEBUG logs after the Base
runtime is loaded and the selected command is dispatched. For earlier startup
debugging, use wrapper options that are consumed by `bin/basectl` before
`base_init.sh` is sourced:

- `--debug-wrapper` and `--verbose-wrapper` enable `LOG_DEBUG=1` before runtime
  initialization.
- `--utc-wrapper` enables UTC log timestamps before runtime initialization.
- `--color` preserves color-aware wrapper argument handling while keeping the flag
  out of command arguments.

Prefer `-v` unless the problem happens before the command implementation starts.

### Standard Shell Defaults

Base can provide optional, opinionated shell defaults, but they are not enabled
by plain `basectl update-profile`.

Current default-setting scripts are:

- `lib/shell/base_defaults.sh` for shell-neutral defaults shared by Bash and Zsh
- `lib/shell/bash_defaults.sh` for Bash-specific defaults
- `lib/shell/zsh_defaults.sh` for Zsh-specific defaults

Users can opt in during profile updates with:

```bash
basectl update-profile --defaults
```

Users can opt out again with:

```bash
basectl update-profile --no-defaults
```

Those defaults are intended to stay conservative:

- aliases like `rm -i`, `cp -i`, `mv -i`
- vi-style command editing
- editor defaults
- prompt defaults
- history behavior

## Bonus Utilities

Base currently exposes a small number of convenience utilities through
`$BASE_HOME/bin`, including `caff` and `sort-in-place`. These are useful helper
commands that share Base's command conventions, but they are not the core
workspace orchestration surface.

As Base matures, bonus utilities may stay documented as extras or move behind a
clearer namespace. The control-plane surface remains `basectl`.

## What Base Is Responsible For

Base owns the shared developer-platform layer of the workspace.

That means Base should be responsible for:

- bootstrapping the developer environment
- discovering participating project repos
- orchestrating setup and test flows across repos
- managing shared shell initialization
- providing common shell and Python helper libraries
- providing wrappers and execution conventions for CLIs

## What Base Is Not Responsible For

Base should not absorb project-specific logic that belongs inside individual
repositories.

Each project repo should still own:

- its own source code
- its own business logic
- its own build details
- its own runtime details
- its own tests
- its own project-specific setup steps

Base should orchestrate those things, not replace them.

## Mental Model

Think of Base as the workspace control plane for local development.

Each project repo remains independent. Base sits beside those repos and offers:

- one place to bootstrap the workspace
- one place to manage shared environments
- one place to host common execution libraries and wrappers

That gives a multi-repo setup some of the ergonomic benefits people often reach
for in a monorepo, without forcing unrelated codebases into a single repository.

## Likely Workspace Shape

The target shape looks roughly like this:

```text
work/
  base/
    README.md
    cli/
      bash/
      python/
    lib/
    manifests/
  project-a/
  project-b/
  infra/
```

Projects should be able to opt into Base with minimal coupling. The exact
mechanism is still being designed, but the intent is clear:

- Base discovers projects in the shared workspace
- projects expose a small contract to Base
- Base provides common orchestration on top

## Design Principles

The refactor should follow a few simple principles.

1. Keep project repos independent.
2. Prefer explicit conventions over hidden shell magic.
3. Keep wrappers thin but reliable.
4. Make setup and test flows idempotent where possible.
5. Let Base provide the common layer without turning into a dumping ground for
   project-specific behavior.

## Status

This repository is being repositioned and refactored.

The current contents include useful shell-oriented building blocks from the
older version of Base. The goal now is to evolve those foundations into a more
general multi-project workspace tool.

For the documentation map and naming convention, see
[docs/README.md](docs/README.md). For the evolving architecture and
product-direction notes behind that refactor, see
[docs/architecture.md](docs/architecture.md). For the current `basectl` runtime
and dispatch contract, see [docs/execution-model.md](docs/execution-model.md).
For ecosystem boundary and integration decisions, see
[docs/tool-boundaries.md](docs/tool-boundaries.md).

The first migration pass has already started: the Base CLI, runtime bootstrap,
setup command, and Bash libraries formerly living in the `banyanlabs` repo now
live under this repository.

## Short Version

Base is the repo you check out once per workspace so that all the other repos
in that workspace become easier to set up, easier to test, and easier to run in
a controlled shell environment.
