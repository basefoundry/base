# `basectl`

Umbrella CLI for Base.

## Purpose

`basectl` is the primary user-facing command for workspace-level Base behavior.

It is invoked through:

```bash
basectl <subcommand> [args...]
```

Long options with values use the space-separated form, for example
`--format json`. The umbrella command rejects `--option=value` before command
delegation. Arguments after a `--` separator belong to the delegated project
command and may use that command's native syntax.

`basectl` exposes `-v` as the public command-level debug switch. Direct
`base_cli` package standard options such as `--debug`, `--quiet`, `--log-file`,
`--config`, `--environment`, and `--keep-temp` are not public `basectl`
options.

The public entrypoint lives at `bin/basectl`. It establishes the Base runtime
for command implementations, then sources this command implementation and calls
`main`.

`basectl` also dispatches direct Base-owned command names by convention when
such command directories exist. Optional utility CLIs such as `caff` and
`sort-in-place` live in `basefoundry/base-platform-tools` instead of Base core.

## Current subcommands

- `activate`
- `setup`
- `check`
- `ci setup/check/doctor`
- `clean`
- `config`
- `doctor`
- `docs`
- `devcontainer`
- `export-context`
- `gh`
- `onboard`
- `prompt`
- `repo init/clone/check/configure/agent-guidance/installer-template`
- `trust status/allow/revoke`
- `test`
- `build`
- `update-profile`
- `update`
- `projects list`
- `workspace status/check/doctor/clone/pull/init/configure`
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
- `basectl ci setup/check/doctor <project>` runs Base setup, readiness checks,
  and diagnostics with CI-safe defaults and text or JSON output. It does not
  run project tests or launch CI runners/VMs.
- `basectl setup/check/doctor --profile <list>` manage opt-in prerequisite
  profiles. `sre` is the first additional built-in profile, and profiles compose
  as comma-separated lists such as `--profile dev,sre`.
- `basectl clean --older-than <age>` removes old runtime artifacts from the Base cache root.
- `basectl clean --keep-last <count>` keeps the newest log files per CLI log directory.
- `basectl logs` lists recent Base CLI runtime logs and can print, open, or tail
  the newest matching log file.
- `basectl history` lists recent structured Base command runs from the local
  history index and supports JSON output for scripts.
- `basectl config path/show/doctor` inspects Base's machine-local user config at `~/.base.d/config.yaml`.
- `basectl trust status/allow/revoke <project>` manages local approval for
  manifest-declared project commands under `~/.base.d/trust/manifest-commands/`.
- `basectl doctor [project]` diagnoses the local Base environment and, when
  provided, project manifest artifacts with suggested fixes.
- `basectl gh` manages GitHub issues, pull requests, branch naming, repository
  hygiene, and GitHub Project metadata using Base's opinionated workflow. It
  uses standard GitHub-style issue categories such as `bug`, `enhancement`,
  `documentation`, `ci`, and `security`, and derives branch names from those
  categories. Issue creation is unassigned by default unless `--assignee` is
  passed or `.github/base-project.yml` sets `project.issue_defaults.assignee`.
  Prefer this command for Base repository GitHub workflows when it supports the
  task.
- `basectl onboard` guides first-run setup around existing setup, check,
  doctor, profile, and project-discovery primitives. See
  `docs/basectl-onboard.md`.
- `basectl repo init <name>` ensures the standard local repository baseline.
  It is safe to run on an existing checkout: existing files are left alone and
  missing Base-managed files are added. When `--repo <owner/name>` is provided,
  it creates the GitHub repository only if it is missing, then applies the same
  GitHub-side configuration handled by `repo configure`. Without `--path`, it
  creates the repository under `workspace.root` from `~/.base.d/config.yaml`,
  then falls back to the parent directory of `BASE_HOME`. For the current
  checkout, pass the repository name plus `--path .`; plain `repo init` does not
  commit or push local files. Use `--pr` on an existing clean Git worktree to
  commit baseline changes on a branch, push that branch to `origin`, and open a
  pull request.
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
  repo-named Project when `BASE_PROJECT_TOKEN` has Project write access.
  `repo configure` reports when that secret is missing so the workflow does not
  silently fall back to the default Actions token. Use `--no-project` to skip
  Project setup, `--project <title>` to override the
  Project title, or
  `--initiative-option <name>` to seed repository-specific Initiative values.
  Use `--copy-project-fields-from <title>` during migration to copy missing
  issue item field values from an existing Project before config defaults fill
  remaining blanks in the repo Project. Use `--replace-project` when an
  existing repo Project has nonstandard views; Base archives the old Project,
  recreates it from `base-project-template`, backfills repository issues, and
  preserves missing item field values where possible. Already-standard Projects
  are left intact.
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
- `basectl devcontainer [project]` previews a generated
  `.devcontainer/devcontainer.json` from the resolved Base manifest. It is
  dry-run by default, supports `--format json`, and writes only with `--write`,
  refusing to replace an existing project-owned Dev Containers file.
- `basectl docs` opens the Base documentation home page on GitHub. Use
  `--show-url` to print the URL without opening a browser.
- `basectl prompt list` lists repo-owned Markdown prompts that Base can render
  for AI-assisted workflows. `basectl prompt product-self-review` prints the
  periodic Base product self-review prompt with current Base metadata, or writes
  the rendered Markdown with `--output <path>`. Base renders the prompt only;
  an AI tool performs the review.
- `basectl update-profile` creates, refreshes, or removes managed sections in
  Bash and Zsh dotfiles, backing up existing dotfiles before changes.
- `basectl update [project]` updates the selected project checkout through Git
  and then runs `basectl setup <project>`. Omitting the project selects `base`;
  Homebrew-managed Base installs still hand off only the Base package to
  `brew upgrade basefoundry/base/base`.
- `basectl projects list` scans `workspace.root` from `~/.base.d/config.yaml`
  when configured, otherwise `$BASE_HOME`'s parent, and prints discovered
  project names and paths. Source checkouts can run this read-only command
  before `basectl setup` when ambient `python3` has Base's bootstrap Python
  dependencies available; otherwise the command prints a targeted setup
  diagnostic.
- `basectl workspace status` reports a read-only workspace summary across
  discovered projects, or across expected repositories when
  `workspace.manifest` is configured or `--manifest <path>` is supplied. When
  `basectl check <project>` has run, status reports the latest recorded project
  check date from `~/.base.d/<project>/checks/last.json`.
- `basectl workspace check` and `basectl workspace doctor` run read-only
  project checks and diagnostics across discovered projects. With a configured
  workspace manifest or `--manifest <path>`, they also report missing expected
  repositories and discovered Base-managed projects outside the manifest.
- `basectl workspace clone` materializes missing required repositories from a
  configured or explicit workspace manifest by delegating to `basectl repo clone`.
  Optional repositories are reported but skipped unless `--include-optional` is
  supplied, `--dry-run` previews the delegated clone work, and explicit
  `--manifest <path>` takes precedence over `workspace.manifest`.
- `basectl workspace init <workspace-source>` bootstraps a workspace from a
  workspace configuration repository. The source may be a local path, GitHub URL,
  `owner/repo`, or a short repository name resolved by `--owner <owner>` or
  `github.default_owner`. `--path <path>` controls the configuration repo
  checkout, while `--workspace <path>` controls member repository destinations.
- `basectl workspace pull` explicitly fetches and validates a canonical
  workspace manifest source from `workspace.manifest_source` in
  `~/.base.d/config.yaml`, or from an explicit `--source <url-or-path>`, and
  writes the result to `workspace.manifest` or `--manifest <path>` before the
  next workspace status, check, doctor, or clone operation.
- `basectl workspace configure` applies the existing `basectl repo configure`
  repair path across discovered Base-managed projects, or across present
  Base-managed repositories from a configured or explicit workspace manifest.
  It supports `--dry-run`, skips missing or non-Base-managed repositories, and
  continues after per-repo failures.
- `basectl version` prints the installed Base version from the repo-root `VERSION` file.
- basectl-specific bootstrap subcommands live under `cli/bash/commands/basectl/subcommands/`.
- basectl tests live under `cli/bash/commands/basectl/tests/`.
