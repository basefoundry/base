# basectl Quick Reference

This page is a compact lookup table for the current `basectl` command surface.
Run `basectl --help` or `basectl <command> --help` for full usage.

Use space-separated values for long options, for example `--format json`.
Base rejects `--option=value` syntax before command delegation. Arguments after
`--` belong to the delegated project command and may use that command's native
syntax.

`basectl` exposes `-v` as the public command-level debug switch. Direct
`base_cli` package standard options such as `--debug`, `--quiet`, `--log-file`,
`--config`, `--environment`, and `--keep-temp` are private to Python package
execution and are rejected by `basectl`.

## Source Control And Forge Boundary

Base assumes Git as the source-control system. Non-Git SCMs such as Mercurial,
Perforce, and Subversion are out of scope.

Base is GitHub-primary today. Local project commands work for non-GitHub Git
repositories once they are checked out locally and declare `base_manifest.yaml`.
Repository creation, cloning, configuration, issue, pull-request, Project, and
release automation are GitHub-specific unless a command explicitly says
otherwise. See
[Source Control And Forge Support](source-control-and-forge-support.md) for the
full compatibility contract.

## Install And Bootstrap

| Command | What it does | Important flags |
|---|---|---|
| `basectl setup [project]` | Install or reconcile Base and optional project artifacts. | `--profile <dev,sre,ai>`, `--dry-run`, `--manifest <path>`, `--recreate-venv`, `--notify`, `--no-notify` |
| `basectl update-profile` | Create, refresh, or remove Base-managed Bash and Zsh startup snippets, backing up existing dotfiles before changes. | `--defaults`, `--no-defaults`, `--remove`, `--dry-run` |
| `basectl update [project]` | Update a Base-managed project checkout through Git, or update Base through Homebrew when Base is Homebrew-managed, then run setup for the selected project. | `--dry-run` |
| `basectl onboard [project]` | Guide first-run setup by orchestrating check, setup, shell profile, doctor, and project discovery. Defaults to `base`. | `--profile <list>`, `--dry-run`, `--yes`, `--no-profile` |
| `basectl version` | Show the installed Base version. | none |

## Daily Project Loop

| Command | What it does | Important flags |
|---|---|---|
| `basectl projects list` | Discover Base-managed projects under the workspace root. | `--workspace <path>`, `--format <text\|json>` |
| `basectl activate <project>` | Start an interactive Base Bash runtime shell for a project. | `--workspace <path>`, `--no-cd` |
| `basectl test [project]` | Run the project's declared test command from the project root. | `--workspace <path>`, `--dry-run`, `-- <args>` |
| `basectl run <project> <command>` | Run a named manifest command from the project root. | `--workspace <path>`, `--dry-run`, `-- <args>` |
| `basectl run [project] --list` | List runnable commands declared by a project manifest. | `--workspace <path>` |
| `basectl build <project> [target...]` | Run declared build targets, or `build.default` when no target is provided. | `--workspace <path>`, `--dry-run`, `-- <args>` |
| `basectl build <project> --list` | List build targets declared by a project manifest. | `--workspace <path>` |
| `basectl demo [project]` | Run a project-owned demo script. | `--workspace <path>`, `--dry-run`, `-- <args>` |

Manifest-declared `test`, `run`, and `build` commands are project-owned shell
command strings executed from the project root. Review manifests from
unfamiliar repositories before running them; use `--dry-run` or `--list` to
inspect the resolved command contract first.

## Diagnostics And Logs

| Command | What it does | Important flags |
|---|---|---|
| `basectl check [project]` | Verify Base and optional project readiness without making changes. Project checks record the latest result under `~/.base.d/<project>/checks/last.json`. | `--profile <list>`, `--format <text\|json>`, `--manifest <path>`, `--remote-network` |
| `basectl doctor [project]` | Explain Base and optional project findings with stable finding IDs and fixes. | `--profile <list>`, `--format <text\|json>`, `--manifest <path>`, `--remote-network` |
| `basectl ci setup <project>` | Run setup in non-interactive CI mode. | `--format <text\|json>`, `--manifest <path>`, `--profile <list>`, `--recreate-venv` |
| `basectl ci check <project>` | Run readiness checks in non-interactive CI mode. | `--format <text\|json>`, `--manifest <path>`, `--profile <list>` |
| `basectl ci doctor <project>` | Run diagnostics in non-interactive CI mode. | `--format <text\|json>`, `--manifest <path>`, `--profile <list>` |
| `basectl logs` | List recent Base CLI runtime logs. | `--command <name>`, `--limit <count>` |
| `basectl logs --path` | Print the newest matching log path only. | `--command <name>` |
| `basectl logs --open` | Open the newest matching log in `PAGER` or `EDITOR`. | `--command <name>` |
| `basectl logs --tail` | Tail and follow the newest matching log. | `--command <name>`, `--lines <count>` |
| `basectl history` | List recent structured Base command runs. | `--project <name>`, `--command <name>`, `--status <ok\|warn\|error>`, `--format <text\|json>` |
| `basectl clean` | Remove old Base runtime logs, temp files, and cache entries. | `--older-than <age>`, `--keep-last <count>`, `--dry-run` |
| `basectl config path` | Print the local Base config path. | none |
| `basectl config show` | Show local Base config as redacted JSON. | none |
| `basectl config doctor` | Diagnose local Base config. | none |

## Workspace

| Command | What it does | Important flags |
|---|---|---|
| `basectl workspace status` | Show read-only workspace project status and latest recorded project check dates. Uses `workspace.manifest` from user config unless `--manifest` is supplied. | `--workspace <path>`, `--manifest <path>`, `--format <text\|json>` |
| `basectl workspace check` | Run read-only checks across workspace projects. Uses `workspace.manifest` from user config unless `--manifest` is supplied. | `--workspace <path>`, `--manifest <path>`, `--format <text\|json>` |
| `basectl workspace doctor` | Run read-only diagnostics across workspace projects. Uses `workspace.manifest` from user config unless `--manifest` is supplied. | `--workspace <path>`, `--manifest <path>`, `--format <text\|json>` |
| `basectl workspace clone` | Clone or validate expected repositories from a workspace manifest. Missing-repository materialization is GitHub-only today because this path delegates to `repo clone`. Uses `workspace.manifest` from user config unless `--manifest` is supplied. | `--workspace <path>`, `--manifest <path>`, `--include-optional`, `--dry-run` |
| `basectl workspace pull` | Explicitly fetch and validate a canonical workspace manifest source before updating the local workspace manifest. Uses `workspace.manifest_source` and `workspace.manifest` from user config unless flags are supplied. | `--source <url-or-path>`, `--manifest <path>`, `--dry-run` |
| `basectl workspace init <workspace-source>` | Initialize a workspace from a workspace configuration repository, update local workspace config, and optionally materialize member repositories. | `--owner <owner>`, `--path <path>`, `--workspace <path>`, `--manifest <path>`, `--include-optional`, `--dry-run` |
| `basectl workspace configure` | Apply the existing `repo configure` repair path across discovered Base-managed workspace repositories or an explicit workspace manifest. Skips missing, non-Base-managed, or non-GitHub repos and continues after per-repo failures. | `--workspace <path>`, `--manifest <path>`, `--dry-run` |

## Repository And GitHub Workflow

This section is intentionally GitHub-specific except for local baseline
inspection. Use ordinary Git to clone non-GitHub repositories, then use the
daily project loop commands from the local checkout.

| Command | What it does | Important flags |
|---|---|---|
| `basectl repo init <name>` | Create a Base-managed repository baseline, including `.github/base-project.yml`, and optionally create/configure the GitHub repo. | `--path <path>`, `--repo <owner/name>`, `--description <text>`, `--copyright-holder <name>`, `--public`, `--private`, `--pr`, `--project <title>`, `--project-owner <login>`, `--project-schema <schema>`, `--copy-project-fields-from <title>`, `--initiative-option <name>`, `--no-configure`, `--no-project`, `--no-protect-default-branch`, `--dry-run` |
| `basectl repo clone <name-or-owner/name>` | Clone one GitHub repository into the configured Base workspace, treating matching existing checkouts as already satisfied. | `--owner <owner>`, `--path <path>`, `--dry-run` |
| `basectl repo check [path]` | Verify the local repository baseline. | `--agent-guidance` |
| `basectl repo configure [path]` | Apply Base-managed GitHub repository settings, labels, branch protection, and repo Project metadata. Reads `.github/base-project.yml` to seed options and fill missing issue defaults when present. | `--repo <owner/name>`, `--project <title>`, `--project-owner <login>`, `--project-schema <schema>`, `--copy-project-fields-from <title>`, `--initiative-option <name>`, `--replace-project`, `--no-project`, `--no-protect-default-branch`, `--dry-run` |
| `basectl repo agent-guidance [path]` | Seed optional repo-local agent guidance files, optionally through a draft PR. | `--repo <owner/name>`, `--repo-name <name>`, `--default-branch <name>`, `--validation-command <cmd>`, `--pr`, `--dry-run` |
| `basectl repo installer-template [path]` | Write the maintained project installer starter script to a path, defaulting to `./install.sh`, optionally through a draft PR. | `--print`, `--repo <owner/name>`, `--pr`, `--dry-run` |
| `basectl gh issue list` | List GitHub issues through `gh`. | passes through `gh` options |
| `basectl gh issue create` | Create an issue with Base category conventions, assign it, and add repo Project metadata when the repo is known. Defaults to `--category enhancement` and Project `Size=S` when omitted. | `--category <bug\|enhancement\|documentation\|ci\|security>`, `--title <title>`, `--body <body>`, `--repo <owner/name>`, `--project <title>`, `--project-owner <login>`, `--size <T\|S\|M\|L>`, `--no-project` |
| `basectl gh issue start <number>` | Start issue-backed branch naming workflow. | `--category <category>`, `--title <title>` |
| `basectl gh pr create/status/checks/ready/merge` | Create and manage pull requests through Base's workflow wrapper. `pr create` auto-injects `Fixes #<issue>` from Base branch names unless `--no-fixes` is passed, and uses `github.pr` from `base_manifest.yaml` when present. | passes through `gh` options; `pr create` also accepts `--no-fixes` |
| `basectl gh branch stale` | Report stale local branches. | `--days <days>` |
| `basectl gh branch prune` | Prune safe merged branches. | `--dry-run`, `--yes`, `--remote` |
| `basectl gh worktree prune` | Prune stale merged worktrees. | `--dry-run`, `--yes` |
| `basectl gh project doctor` | Inspect GitHub Project metadata against the Base Project schema. | `--project <title>`, `--owner <login>`, `--schema base-project` |
| `basectl gh project configure` | Create or repair Base-managed Project metadata. | `--project <title>`, `--owner <login>`, `--repo <owner/name>`, `--schema base-project`, `--config <path>`, `--copy-fields-from <title>`, `--replace-project`, `--initiative-option <name>`, `--dry-run` |
| `basectl gh project issue set-fields <number>` | Add an issue to the Project if needed and update metadata fields. | `--project <title>`, `--repo <owner/name>`, `--config <path>`, field options |

## Release And Context

| Command | What it does | Important flags |
|---|---|---|
| `basectl release check --version <version>` | Inspect release readiness without publishing. | `--manifest <path>` |
| `basectl release plan --version <version>` | Print the release plan and downstream handoff details. | `--manifest <path>` |
| `basectl release notes --version <version>` | Extract release notes for the requested version. | `--manifest <path>` |
| `basectl release publish --version <version>` | Create the annotated Git tag and GitHub Release after checks pass. | `--manifest <path>`, `--dry-run`, `--yes` |
| `basectl docs` | Open the Base documentation home page on GitHub. | `--show-url` |
| `basectl export-context [project]` | Export a project's `.ai-context/` directory as Markdown or Zip. | `--workspace <path>`, `--format <markdown\|zip>`, `--output <path>`, `--print`, `--list-files` |
| `basectl prompt list` | List repo-owned Markdown prompts that Base can render for AI-assisted workflows. | none |
| `basectl prompt product-self-review` | Print the periodic Base product self-review prompt with current Base metadata. | none |
