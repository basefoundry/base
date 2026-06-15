# basectl Quick Reference

This page is a compact lookup table for the current `basectl` command surface.
Run `basectl --help` or `basectl <command> --help` for full usage.

## Install And Bootstrap

| Command | What it does | Important flags |
|---|---|---|
| `basectl setup [project]` | Install or reconcile Base and optional project artifacts. | `--profile <dev,sre,ai>`, `--dry-run`, `--manifest <path>`, `--recreate-venv` |
| `basectl update-profile` | Create or update Base-managed Bash and Zsh startup snippets. | `--defaults`, `--no-defaults`, `--dry-run` |
| `basectl update [project]` | Update a Base-managed project checkout through Git, or update Base through Homebrew when Base is Homebrew-managed, then run setup for the selected project. | `--dry-run` |
| `basectl onboard` | Guide first-run setup by orchestrating setup, shell profile, doctor, and project discovery checks. | `--profile <list>`, `--dry-run`, `--yes`, `--no-profile` |
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

## Diagnostics And Logs

| Command | What it does | Important flags |
|---|---|---|
| `basectl check [project]` | Verify Base and optional project readiness without making changes. | `--profile <list>`, `--format <text\|json>`, `--manifest <path>`, `--remote-network` |
| `basectl doctor [project]` | Explain Base and optional project findings with stable finding IDs and fixes. | `--profile <list>`, `--format <text\|json>`, `--manifest <path>`, `--remote-network` |
| `basectl ci setup <project>` | Run setup in non-interactive CI mode. | `--format <text\|json>`, `--manifest <path>`, `--profile <list>`, `--recreate-venv` |
| `basectl ci check <project>` | Run readiness checks in non-interactive CI mode. | `--format <text\|json>`, `--manifest <path>`, `--profile <list>` |
| `basectl ci doctor <project>` | Run diagnostics in non-interactive CI mode. | `--format <text\|json>`, `--manifest <path>`, `--profile <list>` |
| `basectl logs` | List recent Base CLI runtime logs. | `--command <name>`, `--limit <count>` |
| `basectl logs --path` | Print the newest matching log path only. | `--command <name>` |
| `basectl logs --open` | Open the newest matching log in `PAGER` or `EDITOR`. | `--command <name>` |
| `basectl logs --tail` | Tail and follow the newest matching log. | `--command <name>`, `--lines <count>` |
| `basectl clean` | Remove old Base runtime logs, temp files, and cache entries. | `--older-than <age>`, `--keep-last <count>`, `--dry-run` |
| `basectl config path` | Print the local Base config path. | none |
| `basectl config show` | Show local Base config. | none |
| `basectl config doctor` | Diagnose local Base config. | none |

## Workspace

| Command | What it does | Important flags |
|---|---|---|
| `basectl workspace status` | Show read-only workspace project status. | `--workspace <path>`, `--manifest <path>`, `--format <text\|json>` |
| `basectl workspace check` | Run read-only checks across workspace projects. | `--workspace <path>`, `--manifest <path>`, `--format <text\|json>` |
| `basectl workspace doctor` | Run read-only diagnostics across workspace projects. | `--workspace <path>`, `--manifest <path>`, `--format <text\|json>` |
| `basectl workspace clone` | Clone or validate expected repositories from a workspace manifest. | `--workspace <path>`, `--manifest <path>`, `--include-optional`, `--dry-run` |

## Repository And GitHub Workflow

| Command | What it does | Important flags |
|---|---|---|
| `basectl repo init <name>` | Create a Base-managed repository baseline, including `.github/base-project.yml`, and optionally create/configure the GitHub repo. | `--path <path>`, `--repo <owner/name>`, `--public`, `--private`, `--pr`, `--copy-project-fields-from <title>`, `--no-project`, `--dry-run` |
| `basectl repo clone <name-or-owner/name>` | Clone one GitHub repository into the configured Base workspace, treating matching existing checkouts as already satisfied. | `--owner <owner>`, `--path <path>`, `--dry-run` |
| `basectl repo check [path]` | Verify the local repository baseline. | `--agent-guidance` |
| `basectl repo configure [path]` | Apply Base-managed GitHub repository settings, labels, branch protection, and repo Project metadata. Reads `.github/base-project.yml` to seed options and fill missing issue defaults when present. | `--repo <owner/name>`, `--project <title>`, `--project-owner <login>`, `--copy-project-fields-from <title>`, `--no-project`, `--no-protect-default-branch`, `--dry-run` |
| `basectl repo agent-guidance [path]` | Seed optional repo-local agent guidance files. | `--repo-name <name>`, `--default-branch <name>`, `--validation-command <cmd>`, `--dry-run` |
| `basectl repo installer-template [path]` | Print the maintained project installer starter script, or write it to a path. | `--dry-run` |
| `basectl gh issue list` | List GitHub issues through `gh`. | passes through `gh` options |
| `basectl gh issue create` | Create an issue with Base category conventions, assign it, and add repo Project metadata when the repo is known. | `--category <bug\|enhancement\|documentation\|ci\|security>`, `--title <title>`, `--body <body>`, `--repo <owner/name>`, `--project <title>`, `--project-owner <login>`, `--no-project` |
| `basectl gh issue start <number>` | Start issue-backed branch naming workflow. | `--category <category>`, `--title <title>` |
| `basectl gh pr create/status/checks/ready/merge` | Create and manage pull requests through Base's workflow wrapper. | passes through `gh` options |
| `basectl gh branch stale` | Report stale local branches. | `--days <days>` |
| `basectl gh branch prune` | Prune safe merged branches. | `--dry-run`, `--yes`, `--remote` |
| `basectl gh worktree prune` | Prune stale merged worktrees. | `--dry-run`, `--yes` |
| `basectl gh project doctor` | Inspect GitHub Project metadata against the Base roadmap schema. | `--project <title>`, `--owner <login>`, `--schema base-roadmap` |
| `basectl gh project configure` | Create or repair Base-managed Project metadata. | `--project <title>`, `--owner <login>`, `--repo <owner/name>`, `--config <path>`, `--copy-fields-from <title>`, `--dry-run` |
| `basectl gh project issue set-fields <number>` | Add an issue to the Project if needed and update metadata fields. | `--project <title>`, `--repo <owner/name>`, `--config <path>`, field options |
| `basectl gh todo import` | Preview migration of `TODO.md` items into GitHub Issues. | `--dry-run`, `--file <path>` |

## Release And Context

| Command | What it does | Important flags |
|---|---|---|
| `basectl release check --version <version>` | Inspect release readiness without publishing. | `--manifest <path>` |
| `basectl release plan --version <version>` | Print the release plan and downstream handoff details. | `--manifest <path>` |
| `basectl release notes --version <version>` | Extract release notes for the requested version. | `--manifest <path>` |
| `basectl release publish --version <version>` | Create the annotated Git tag and GitHub Release after checks pass. | `--manifest <path>`, `--dry-run`, `--yes` |
| `basectl export-context [project]` | Export a project's `.ai-context/` directory as Markdown or Zip. | `--workspace <path>`, `--format <markdown\|zip>`, `--output <path>`, `--print`, `--list-files` |
