# AI Context

This file is shared working memory for future AI-assisted development in this
repository. Keep it current when project direction, execution model, or useful
debugging context changes.

## Current State

- Base is a macOS-first developer tooling foundation for multi-repo workspaces.
- Current work is moving through `TODO.md`, which tracks May 2026 product-review
  follow-ups by priority.
- Base has a public Homebrew tap at `codeforester/homebrew-base`, exposed to
  users as `brew install codeforester/base/basectl`.
- Public commands live in `bin/`; `bin/basectl` is the control-plane command.
- Command implementations live under `cli/bash/commands/<command>/`.
- Shared Bash libraries live under `lib/bash/`.
- Shared Python libraries live under `lib/python/`.
- Python command packages live under `cli/python/`.
- Shell startup snippets live under `lib/shell/`.
- Durable Base state lives under `~/.base.d`; project virtual environments live
  at `~/.base.d/<project>/.venv`.
- Runtime cache/log/temp data lives under the Base cache root, which defaults to
  `~/Library/Caches/base` on macOS and can be overridden with `BASE_CACHE_DIR`.

## Standalone Installer Model

- `install.sh` is the user-facing installer for installing Base itself from a
  fresh machine.
- By default it installs into `~/work/base` from
  `https://github.com/codeforester/base.git`.
- Supported installer options are `--dir`, `--repo-url`, `--branch`,
  `--no-profile`, and `--dry-run`.
- The installer clones Base when the target directory is absent, updates it when
  the target is an existing git checkout, rejects an existing non-git target, and
  then runs `bin/basectl setup`.
- Unless `--no-profile` is used, the installer also runs
  `bin/basectl update-profile`.
- Installer behavior is covered by `tests/install.bats`; include that file in
  branch validation when touching installer logic.

## Homebrew Tap Model

- The Homebrew tap repository is `https://github.com/codeforester/homebrew-base`.
- The formula lives at `Formula/basectl.rb` in that repository.
- The user-facing install command is:

```bash
brew install codeforester/base/basectl
```

- The formula installs Base files and users still finish setup with
  `basectl setup` and `basectl update-profile`.
- When installed through Homebrew, Base should be updated with
  `brew upgrade basectl` rather than `basectl update`.
- The initial formula follows Base's `master` branch. Once Base publishes
  release tarballs, the formula should move to a versioned URL plus SHA256.

## Artifact Setup Model

- Projects declare `base_manifest.yaml` at the repo root.
- `base_manifest.yaml` declares `project.name`, optional `brewfile`, and
  `artifacts` with `type`, `name`, `version`, and optional `bootstrap`.
- Users do not specify artifact managers. The Python registry maps supported
  `(type, name)` pairs to managers and errors on unknown artifacts.
- Default project artifacts are declared in `lib/base/default_manifest.yaml`
  using the same manifest shape as project manifests.
- Development-only Base artifacts are declared in `lib/base/dev_manifest.yaml`.
- `click` and `PyYAML` are marked `bootstrap: true` in
  `lib/base/default_manifest.yaml`; they are the minimum Python packages needed
  before Base can run its Python CLI layer inside a project venv.
- `basectl setup` first ensures Base's own venv exists at
  `~/.base.d/base/.venv` and installs Base bootstrap packages there from Bash.
- For project artifact setup, Bash resolves the project manifest using Base's
  venv, runs `base_setup --action bootstrap` from Base's venv to seed the
  project's venv with `bootstrap: true` default artifacts, then invokes:

```bash
base-wrapper --project <project> base_setup ...
```

- `basectl check <project>` and `basectl doctor <project>` also run the project
  artifact layer through `base-wrapper`, but remain non-mutating. If the project
  venv is missing, they report the missing project runtime instead of creating
  it.
- `python-package` artifacts install into the project virtual environment at
  `~/.base.d/<project>/.venv`.
- Homebrew `tool` artifacts currently support `version: latest`; ordinary
  Homebrew packages should move toward Brewfile delegation instead of registry
  growth.

## Python CLI Model

- `lib/python/base_cli` provides the standard Python CLI framework:
  `base_cli.App`, decorators, `Context`, logging, and runtime directories.
- `bin/base-wrapper` is the authoritative Python command wrapper. It selects
  `~/.base.d/<project>/.venv`, sets `BASE_HOME` and `BASE_PROJECT`, adds
  `lib/python` and `cli/python` to `PYTHONPATH`, and executes package commands
  with `python -m <package>`.
- Base itself uses project name `base`.
- End users normally invoke `basectl` or project `bin/` launchers rather than
  calling Python packages directly.

## Shell Startup Model

- `basectl update-profile` manages marked sections in `~/.bash_profile`,
  `~/.bashrc`, `~/.zprofile`, and `~/.zshrc`.
- Managed login/interactive snippets must not source `base_init.sh`.
- `lib/shell/bash_profile` only bridges Bash login shells into `~/.bashrc`.
- `lib/shell/bashrc` derives `BASE_HOME`, prepends `$BASE_HOME/bin` to `PATH`,
  reads optional defaults from `~/.base.d/profile.conf`, and sources
  `lib/shell/bash_defaults.sh` only when defaults are enabled.
- `lib/shell/zshrc` mirrors the same integration model for Zsh.
- Shell completions live under `lib/shell/completions/`.
- `~/.baserc` is user-managed and may set startup-safe preferences such as
  `BASE_DEBUG=1`, but must not set Base-owned variables like `BASE_HOME` or
  `BASE_ENABLE_BASH_DEFAULTS`.
- `basectl activate <project>` starts a runtime shell using
  `lib/bash/runtime/bashrc`; that runtime sources `base_init.sh`, loads the user
  shell config, activates the project venv, and owns the final runtime prompt.
- Invoking `basectl` with no command in an interactive terminal is equivalent to
  `basectl activate base`.

## Useful Validation

- Full Bash test suite:

```bash
bats lib/bash/git/tests/lib_git.bats \
  lib/bash/version/tests/lib_version.bats \
  lib/bash/std/tests/lib_std.bats \
  lib/bash/runtime/tests/runtime_bashrc.bats \
  lib/bash/file/tests/lib_file.bats \
  cli/bash/commands/sort-in-place/tests/sort-in-place.bats \
  cli/bash/commands/basectl/tests/setup.bats \
  cli/bash/commands/basectl/tests/basectl.bats \
  cli/bash/commands/caff/tests/caff.bats \
  tests/install.bats
```

- Focused setup/control-plane validation:

```bash
bats cli/bash/commands/basectl/tests/setup.bats
bats cli/bash/commands/basectl/tests/basectl.bats
```

- Python setup validation:

```bash
env PYTHONPATH=lib/python:cli/python \
  ~/.base.d/base/.venv/bin/python -m unittest cli.python.base_setup.tests.test_engine

env PYTHONPATH=lib/python:cli/python \
  ~/.base.d/base/.venv/bin/python -m pylint --rcfile=.pylintrc \
  cli/python/base_setup/engine.py cli/python/base_setup/tests/test_engine.py
```

- Broader Python validation:

```bash
env PYTHONPATH=lib/python:cli/python \
  ~/.base.d/base/.venv/bin/python -m unittest discover -s lib/python -p 'test*.py'

env PYTHONPATH=lib/python:cli/python \
  ~/.base.d/base/.venv/bin/python -m unittest discover -s cli/python -p 'test*.py'
```

- Smoke validation:

```bash
bin/basectl check
bin/basectl setup --dry-run
```

## Open Design Notes

- `docs/ide-bootstrapping.md` currently captures planned IDE support for
  manifest-driven VS Code/Cursor extension and settings bootstrapping. If that
  design is intended to move forward, commit it intentionally and keep this
  context updated as the manifest shape becomes real.
