# Base

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

## Top Goals

Base is being refactored around three primary goals.

### 1. Umbrella Interface for Multi-Project Setup and Test

Base should give the user one entry point for setting up and validating a
workspace that contains multiple project repositories.

Examples of the kind of interface Base should provide:

- `basectl setup`
- `basectl check`
- `basectl setup <project>`
- `basectl test`
- `basectl test <project>`
- `basectl doctor`
- `basectl projects list`

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

Base exposes commands through a single public directory: `$BASE_HOME/bin`. That
directory is added to `PATH` by Base's managed shell startup snippets.

`bin/basectl` is the control-plane command. Additional public commands, when
needed, are tiny real launcher files in `bin/` that delegate to `basectl`; their
implementation remains under `cli/bash/commands/<command>/` or, in the future,
`cli/python/commands/<command>/`.

Example launcher:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/basectl" caff "$@"
```

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
Base snippets.

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

### Standard Shell Defaults

Base can provide optional, opinionated shell defaults, but they are not enabled
by plain `basectl update-profile`.

Current default-setting scripts are:

- `lib/shell/bash_defaults.sh` for Bash
- `lib/shell/zsh_defaults.sh` for Zsh

Users can opt in during profile updates with:

```bash
basectl update-profile --defaults
```

Those defaults are intended to stay conservative:

- aliases like `rm -i`, `cp -i`, `mv -i`
- vi-style command editing
- editor defaults
- prompt defaults
- history behavior

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

For the evolving architecture and product-direction notes behind that refactor,
see [docs/design.md](docs/design.md). For ecosystem boundary and integration
decisions, see [docs/tool-boundaries.md](docs/tool-boundaries.md).

The first migration pass has already started: the Base CLI, runtime bootstrap,
setup command, and Bash libraries formerly living in the `banyanlabs` repo now
live under this repository.

## Short Version

Base is the repo you check out once per workspace so that all the other repos
in that workspace become easier to set up, easier to test, and easier to run in
a controlled shell environment.
