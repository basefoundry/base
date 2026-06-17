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

`basectl` also dispatches direct Base-owned command names by convention when
such command directories exist. Optional utility CLIs such as `caff` and
`sort-in-place` live in `codeforester/base-platform-tools` instead of Base core.

## Current subcommands

- `activate`
- `setup`
- `check`
- `ci setup/check/doctor`
- `clean`
- `config`
- `doctor`
- `export-context`
- `gh`
- `onboard`
- `repo init/clone/check/configure/agent-guidance/installer-template`
- `test`
- `build`
- `update-profile`
- `update`
- `projects list`
- `workspace status/check/doctor/clone`
- `version`
- `help`

## Planned subcommands

- Additional `test` backends beyond manifest commands and `mise run`.

## Notes

- `basectl setup` is the default local bootstrap path.
- `basectl activate <project>` starts a project-specific Bash runtime shell
  with the project virtual environment active and `$PROJECT_ROOT/bin` on `PATH`
  when that directory exists.
- `basectl setup [project]` runs the Bash bootstrap layer first, then invokes the
  Python project setup layer for `base_manifest.yaml` artifacts. The optional
  project argument validates `project.name`.
- `basectl check [project]` verifies the same local requirements without making
  changes and can include project manifest artifacts.
- `basectl ci setup/check/doctor <project>` runs Base in non-interactive CI
  mode, sets CI-safe defaults, and supports text or JSON output.
- `basectl setup/check/doctor --profile <list>` manage opt-in prerequisite
  profiles. `sre` is the first additional built-in profile, and profiles compose
  as comma-separated lists such as `--profile dev,sre`.
- `basectl clean --older-than <age>` removes old runtime artifacts from the Base cache root.
- `basectl clean --keep-last <count>` keeps the newest log files per CLI log directory.
- `basectl logs` lists recent Base CLI runtime logs and can print, open, or tail
  the newest matching log file.
- `basectl config path/show/doctor` inspects Base's machine-local user config at `~/.base.d/config.yaml`.
- `basectl doctor [project]` diagnoses the local Base environment and, when
  provided, project manifest artifacts with suggested fixes.
- `basectl gh` manages GitHub issues, pull requests, branch naming, repository
  hygiene, and GitHub Project metadata using Base's opinionated workflow. It
  uses standard GitHub-style issue categories such as `bug`, `enhancement`,
  `documentation`, `ci`, and `security`, and derives branch names from those
  categories. Prefer this command for Base repository GitHub workflows when it
  supports the task.
- `basectl onboard` guides first-run setup around existing setup, check,
  doctor, profile, and project-discovery primitives. See
  `docs/basectl-onboard.md`.
- `basectl repo init <name>` ensures the standard local repository baseline.
  It is safe to run on an existing checkout: existing files are left alone and
  missing Base-managed files are added. When `--repo <owner/name>` is provided,
  it creates the GitHub repository only if it is missing, then applies the same
  GitHub-side configuration handled by `repo configure`. Without `--path`, it
  creates the repository under `workspace.root` from `~/.base.d/config.yaml`,
  then falls back to the parent directory of `BASE_HOME`.
  `basectl repo clone <name-or-owner/name>` clones one existing GitHub
  repository into the configured workspace, supports `--owner <owner>` for
  short names, and treats matching existing checkouts as already satisfied.
  `basectl repo check [path]` verifies the local baseline, and
  `basectl repo configure [path]` applies or repairs the GitHub settings,
  labels, default branch protection, and standard repo Project setup after the
  baseline exists. By default, the
  Project title matches the repository name; missing Projects are copied from
  `base-project-template`, linked to the repository, and backfilled with
  repository issues. When `.github/base-project.yml` exists, repo-specific
  `Area` and `Initiative` options are added from that file and `issue_defaults`
  are applied to missing Project item field values. `repo init` also seeds a
  Project intake workflow that can add externally-created issues to the
  repo-named Project when `BASE_PROJECT_TOKEN` has Project write access. Use
  `--no-project` to skip Project setup, `--project <title>` to override the
  Project title, or
  `--initiative-option <name>` to seed repository-specific Initiative values.
  Use `--copy-project-fields-from <title>` during migration to copy missing
  issue item field values from an existing Project before config defaults fill
  remaining blanks in the repo Project.
  `basectl repo agent-guidance [path]` seeds optional repo-local agent guidance
  files and `basectl repo check [path] --agent-guidance` verifies that optional
  layer for repos that opt in. Use `--pr` when generated guidance should land
  through a draft pull request instead of direct file generation.
  `basectl repo installer-template [path]` prints or writes the maintained
  project installer starter script. Use `--pr` with a path to open the
  generated installer template as a draft pull request.
- `basectl test [project]` runs the project's manifest `test.command` or
  `test.mise` from the project root with Base project environment variables
  exported. Use `basectl test <project> -- <args...>` to pass extra arguments
  to the delegated test command.
- `basectl build <project> [target...]` runs manifest `build.targets` from
  each target's `working_dir`. With no targets, it runs `build.default`
  sequentially. Use `basectl build <project> --list` to inspect targets and
  `--dry-run` to preview commands without running them.
- `basectl run <project> <command>` runs a named command from the project's
  manifest `commands` map with the same project root, environment variables,
  virtual environment, dry-run, and extra-argument contract as `basectl test`.
  `basectl run <project> test` delegates to the top-level manifest `test`
  contract. Use `basectl run <project> --list` to inspect available commands.
- `basectl export-context [project]` exports a project's `.ai-context`
  directory for manual AI tool upload or copy/paste. Markdown exports include
  stable file headings and use `INDEX.md` ordering when available. Zip exports
  contain only files from `.ai-context`.
- `basectl update-profile` creates or refreshes managed sections in Bash and Zsh dotfiles.
- `basectl update [project]` updates the selected project checkout through Git
  and then runs `basectl setup <project>`. Omitting the project selects `base`;
  Homebrew-managed Base installs still hand off only the Base package to
  `brew upgrade codeforester/base/base`.
- `basectl projects list` scans `workspace.root` from `~/.base.d/config.yaml`
  when configured, otherwise `$BASE_HOME`'s parent, and prints discovered
  project names and paths.
- `basectl workspace status` reports a read-only workspace summary across
  discovered projects, or across expected repositories when
  `workspace.manifest` is configured or `--manifest <path>` is supplied.
- `basectl workspace check` and `basectl workspace doctor` run read-only
  project checks and diagnostics across discovered projects. With a configured
  workspace manifest or `--manifest <path>`, they also report missing expected
  repositories and discovered Base-managed projects outside the manifest.
- `basectl workspace clone` materializes missing required repositories from a
  configured or explicit workspace manifest by delegating to `basectl repo clone`.
  Optional repositories are reported but skipped unless `--include-optional` is
  supplied, `--dry-run` previews the delegated clone work, and explicit
  `--manifest <path>` takes precedence over `workspace.manifest`.
- `basectl version` prints the installed Base version from the repo-root `VERSION` file.
- basectl-specific bootstrap subcommands live under `cli/bash/commands/basectl/subcommands/`.
- basectl tests live under `cli/bash/commands/basectl/tests/`.
