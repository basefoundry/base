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

- `base setup`
- `base check`
- `base setup <project>`
- `base test`
- `base test <project>`
- `base doctor`
- `base projects list`

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

## Shell Startup Files

Base now ships managed startup files under `lib/shell/` for both Bash and Zsh:

- `lib/shell/bash_profile`
- `lib/shell/bashrc`
- `lib/shell/zprofile`
- `lib/shell/zshrc`

The division of responsibility is intentional.

### Login Profiles

`bash_profile` and `zprofile` should stay thin.

They are responsible for:

- one-time setup for a login shell
- handing off to the interactive rc file

They should not be the main place for aliases, prompt settings, shell editing
mode, completion, or project activation logic.

### Interactive RC Files

`bashrc` and `zshrc` are where interactive shell behavior belongs.

They are responsible for:

- guarding against non-interactive execution
- guarding against repeated sourcing
- locating `BASE_HOME`
- sourcing `~/.baserc` for machine-local overrides
- sourcing `base_init.sh`
- optionally enabling shared shell defaults

This is where Base becomes active for day-to-day terminal use.

### Standard Shell Defaults

Reusable, opinionated shell defaults should live outside the profile files
themselves.

Current default-setting scripts are:

- `lib/shell/base_defaults.sh` for Bash
- `lib/shell/zsh_defaults.sh` for Zsh

These are intentionally optional. Users can opt in by setting:

```bash
BASE_ENABLE_SHELL_DEFAULTS=true
```

in `~/.baserc`.

That keeps the startup files focused on shell bootstrap while letting Base also
house standard interactive settings such as:

- aliases like `rm -i`, `cp -i`, `mv -i`
- vi-style command editing
- editor defaults
- prompt defaults
- history behavior

### Machine-Local Overrides

`~/.baserc` is the right place for machine-local settings that should not be
hard-coded into the shared startup files, such as:

- `BASE_HOME`
- `BASE_ENABLE_SHELL_DEFAULTS`
- host-specific overrides
- local experimental toggles

### Adoption

The expected setup is to symlink your shell startup files to the Base-managed
versions:

```bash
ln -sf /path/to/base/lib/shell/bash_profile ~/.bash_profile
ln -sf /path/to/base/lib/shell/bashrc ~/.bashrc
ln -sf /path/to/base/lib/shell/zprofile ~/.zprofile
ln -sf /path/to/base/lib/shell/zshrc ~/.zshrc
```

When the files are symlinked, the rc files can infer `BASE_HOME` from their own
resolved path. When they are copied instead of symlinked, `~/.baserc` should
set `BASE_HOME` explicitly.

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
      env/
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

The first migration pass has already started: the shared Bash wrapper,
environment bootstrap, setup command, and Bash libraries formerly living in the
`banyanlabs` repo now live under `base/cli/`.

## Short Version

Base is the repo you check out once per workspace so that all the other repos
in that workspace become easier to set up, easier to test, and easier to run in
a controlled shell environment.
