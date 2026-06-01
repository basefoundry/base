# `basectl`

Umbrella CLI for Base.

## Purpose

`basectl` is the primary user-facing command for workspace-level Base behavior.

It is invoked through:

```bash
basectl <subcommand> [args...]
```

The public entrypoint lives at `bin/basectl`. It establishes the Base runtime
for command implementations, then sources this command implementation and calls
`main`.

`basectl` also dispatches direct command names by convention. For example,
`basectl caff` loads `cli/bash/commands/caff/caff.sh`. Public convenience
commands in `$BASE_HOME/bin`, such as `bin/caff`, should remain tiny launchers
that delegate to `basectl`.

## Current subcommands

- `activate`
- `setup`
- `check`
- `clean`
- `config`
- `doctor`
- `gh`
- `onboard`
- `repo init/check/configure`
- `test`
- `update-profile`
- `update`
- `projects list`
- `version`
- `help`

## Planned subcommands

- Additional `test` backends beyond manifest commands and `mise run`.

## Notes

- `basectl setup` is the default local bootstrap path.
- `basectl activate <project>` starts a project-specific runtime subshell with
  the project virtual environment active and `$PROJECT_ROOT/bin` on `PATH` when
  that directory exists.
- `basectl setup [project]` runs the Bash bootstrap layer first, then invokes the
  Python project setup layer for `base_manifest.yaml` artifacts. The optional
  project argument validates `project.name`.
- `basectl check [project]` verifies the same local requirements without making
  changes and can include project manifest artifacts.
- `basectl setup --dev`, `basectl check --dev`, and `basectl doctor --dev`
  manage developer prerequisites through `lib/base/dev_manifest.yaml`.
- `basectl clean --older-than <age>` removes old runtime artifacts from the Base cache root.
- `basectl clean --keep-last <count>` keeps the newest log files per CLI log directory.
- `basectl logs` lists recent Base CLI runtime logs and can print, open, or tail
  the newest matching log file.
- `basectl config path/show/doctor` inspects Base's machine-local user config at `~/.base.d/config.yaml`.
- `basectl doctor [project]` diagnoses the local Base environment and, when
  provided, project manifest artifacts with suggested fixes.
- `basectl gh` manages GitHub issues, pull requests, branch naming, and
  repository hygiene using Base's opinionated workflow. It uses standard
  GitHub-style issue categories such as `bug`, `enhancement`, `documentation`,
  `ci`, and `security`, and derives branch names from those categories. Prefer
  this command for Base repository GitHub workflows when it supports the task.
- `basectl onboard` guides first-run setup around existing setup, check,
  doctor, profile, and project-discovery primitives. See
  `docs/basectl-onboard.md`.
- `basectl repo init <name>` creates the standard local repository baseline and
  creates and configures the GitHub repository when `--repo <owner/name>` is
  provided or an existing `origin` remote can be inferred. Without `--path`, it
  creates the repository under `workspace.root` from `~/.base.d/config.yaml`,
  then falls back to the parent directory of `BASE_HOME`.
  `basectl repo check [path]` verifies the local baseline, and
  `basectl repo configure [path]` reapplies the GitHub settings and labels.
- `basectl test [project]` runs the project's manifest `test.command` or
  `test.mise` from the project root with Base project environment variables
  exported. Use `basectl test <project> -- <args...>` to pass extra arguments
  to the delegated test command.
- `basectl run <project> <command>` runs a named command from the project's
  manifest `commands` map with the same project root, environment variables,
  virtual environment, dry-run, and extra-argument contract as `basectl test`.
  `basectl run <project> test` delegates to the top-level manifest `test`
  contract. Use `basectl run <project> --list` to inspect available commands.
- `basectl update-profile` creates or refreshes managed sections in Bash and Zsh dotfiles.
- `basectl update` updates the Base repository from Git and then runs `basectl setup`.
- `basectl projects list` scans `workspace.root` from `~/.base.d/config.yaml`
  when configured, otherwise `$BASE_HOME`'s parent, and prints discovered
  project names and paths.
- `basectl version` prints the installed Base version from the repo-root `VERSION` file.
- basectl-specific bootstrap subcommands live under `cli/bash/commands/basectl/subcommands/`.
- basectl tests live under `cli/bash/commands/basectl/tests/`.
