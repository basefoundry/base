# Skills

This file documents repeatable AI-assisted development workflows for Base.
Coding standards live in `STANDARDS.md`.

## Add a basectl subcommand

Use this workflow when adding or changing a `basectl <command>` feature.

- Public entrypoint: `bin/basectl`
- Command implementation: `cli/bash/commands/basectl/`
- Subcommands: `cli/bash/commands/basectl/subcommands/`
- Tests: `cli/bash/commands/basectl/tests/`
- Update completions: `lib/shell/completions/basectl_completion.sh` and
  `lib/shell/completions/basectl_completion.zsh` — add the new command to the
  top-level command list and add a case block for its options.
- Follow shell standards in `STANDARDS.md`.
- Validate focused command behavior with:

```bash
bats cli/bash/commands/basectl/tests/basectl.bats
bats cli/bash/commands/basectl/tests/setup.bats
```

## Add a Bash command

Use this workflow when adding a public Base-owned Bash command.

- Add the public launcher under `bin/`.
- Put implementation code under `cli/bash/commands/<command>/`.
- Keep command tests under `cli/bash/commands/<command>/tests/`.
- Prefer a launcher that delegates through `basectl` so the Base runtime owns
  path setup and library loading.
- Add or update the command README when user-facing behavior changes.

## Add a Bash library

Use this workflow when adding shared Bash behavior.

- Library path: `lib/bash/<name>/lib_<name>.sh`
- Module README: `lib/bash/<name>/README.md`
- Tests: `lib/bash/<name>/tests/`
- Use `import_base_lib` from Base runtime scripts.
- Do not use `set -e`; use explicit error handling.
- Validate the module's BATS tests directly before running the broader suite.

## Add a Python CLI feature

Use this workflow when adding or changing Python-backed Base behavior.

- Shared framework: `lib/python/base_cli/`
- Command packages: `cli/python/`
- Command execution wrapper: `bin/base-wrapper`
- Keep package tests next to the package under `tests/`.
- Run Python commands with `PYTHONPATH=lib/python:cli/python`.
- Validate with:

```bash
env PYTHONPATH=lib/python:cli/python python -m pytest
```

## Add or change artifact setup

Use this workflow when changing `base_manifest.yaml`, default artifacts, or
setup behavior.

- Project manifest: `base_manifest.yaml`
- Default artifacts: `lib/base/default_manifest.yaml`
- Development artifacts: `lib/base/dev_manifest.yaml`
- Artifact registry: `cli/python/base_setup/registry.py`
- Prefer delegation to mature tools over expanding Base-owned setup logic.
- Keep `basectl check` and `basectl doctor` non-mutating.
- Include `tests/install.bats` when installer behavior or setup bootstrap
  behavior changes.

## Change shell startup behavior

Use this workflow when changing profile, rc, completion, or activation behavior.

- Startup snippets: `lib/shell/`
- Runtime shell entrypoint: `lib/bash/runtime/bashrc`
- Profile updater: `cli/bash/commands/basectl/subcommands/update_profile.sh`
- Managed login and interactive snippets must not source `base_init.sh`.
- Validate startup behavior with:

```bash
bats lib/bash/runtime/tests/runtime_bashrc.bats
bats cli/bash/commands/basectl/tests/setup.bats
```

## Release or Homebrew-facing changes

Use this workflow when changing installation, update, or public package
behavior.

- Standalone installer: `install.sh`
- User-facing install test coverage: `tests/install.bats`
- Homebrew tap repository: `https://github.com/codeforester/homebrew-base`
- User-facing Homebrew install command: `brew install codeforester/base/base`
- Keep Homebrew users on `brew upgrade codeforester/base/base` rather than
  `basectl update`.
- Validate with:

```bash
bats tests/install.bats
bin/basectl check
bin/basectl setup --dry-run
```
