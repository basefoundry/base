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
- `doctor`
- `update-profile`
- `update`
- `projects list`
- `version`
- `help`

## Planned subcommands

- `onboard`

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
- `basectl doctor [project]` diagnoses the local Base environment and, when
  provided, project manifest artifacts with suggested fixes.
- `basectl update-profile` creates or refreshes managed sections in Bash and Zsh dotfiles.
- `basectl update` updates the Base repository from Git and then runs `basectl setup`.
- `basectl projects list` scans a workspace for `base_manifest.yaml` files and prints discovered project names and paths.
- `basectl version` prints the installed Base version from the repo-root `VERSION` file.
- `basectl onboard` is planned as a guided first-run checklist around existing
  setup, check, doctor, profile, and project-discovery primitives. See
  `docs/basectl-onboard.md`.
- basectl-specific bootstrap subcommands live under `cli/bash/commands/basectl/subcommands/`.
- basectl tests live under `cli/bash/commands/basectl/tests/`.
