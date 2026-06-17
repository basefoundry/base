# Base Command Context

`basectl` is the public Base control-plane command. Run `basectl --help` for
the canonical current command list.

## Current Public Commands

- `basectl activate <project>` - start an interactive Base Bash runtime shell
  for a project.
- `basectl setup [project]` - install and bootstrap the local Base CLI
  environment and optional project artifacts.
- `basectl check [project]` - verify local Base and optional project artifacts
  without making changes.
- `basectl doctor [project]` - diagnose Base or project readiness and explain
  fixes.
- `basectl test [project]` - run a project's declared test command.
- `basectl build <project> [target...]` - run declared build targets.
- `basectl demo [project]` - run a declared interactive demo script.
- `basectl run <project> <command>` - run a declared project command.
- `basectl export-context [project]` - export `.ai-context/` as a Markdown or
  Zip bundle for manual upload or copy/paste into AI tools.
- `basectl projects list` - list Base-managed projects discovered in the
  workspace.
- `basectl workspace <status|check|doctor|clone>` - show read-only workspace project
  status, checks, diagnostics, or clone expected repositories from a manifest.
- `basectl repo <init|clone|check|configure|agent-guidance|installer-template>` -
  create repository baselines, clone GitHub repositories into the configured
  workspace, configure GitHub repository settings and default branch protection,
  repair missing Project intake support files, configure standard GitHub Project
  metadata, seed agent guidance, and write installer templates.
- `basectl ci <setup|check|doctor> <project>` - run Base setup/check/doctor in
  non-interactive CI. `ci setup --format json` uses `output` for the compact
  final status and adds `output_lines` on failures for intermediate context.
- `basectl release <check|plan|notes|publish>` - inspect release readiness,
  print plans/notes, and publish guarded GitHub-side release artifacts.
- `basectl gh <area> <command>` - manage GitHub issues, PRs, branches, repo
  hygiene, and Project metadata using Base conventions.
  - `basectl gh issue create` defaults to category `enhancement` when
    `--category` is omitted and prints that default in command output.
  - `basectl gh pr create` auto-injects `Fixes #<issue>` from Base branch
    names; pass `--no-fixes` to suppress that body injection.
  - `basectl gh project doctor --project <title>` - inspect Project metadata
    fields against the Base roadmap schema.
  - `basectl gh project configure --project <title>` - create or repair the
    standard Project metadata schema.
  - `basectl gh project issue set-fields <number>` - add an issue to the
    Project if needed and update its metadata fields.
- `basectl clean` - remove old Base runtime logs, temp files, and cache entries.
- `basectl logs` - list, print, open, or tail recent Base CLI runtime logs.
- `basectl config <path|show|doctor>` - inspect Base's machine-local user
  config.
- `basectl onboard` - guide a user through the first Base setup checklist.
- `basectl update-profile` - create or update Base-managed Bash/Zsh startup
  snippets.
- `basectl update [project]` - update Base or a named project using the
  configured Git checkout or Homebrew-managed Base handoff, then run setup for
  the selected project.
- `basectl version` - show the installed Base version.
- `basectl help` - show command help.

## Command Implementation Pattern

The umbrella command implementation lives at:

```text
cli/bash/commands/basectl/basectl.sh
```

Umbrella subcommand modules live under:

```text
cli/bash/commands/basectl/subcommands/
```

Bash command modules handle user-facing dispatch and shell/runtime behavior.
When structured project data is needed, Bash delegates through `base-wrapper`
to Python packages under `cli/python/`.

## Python CLI Pattern

Base Python commands use `base_cli.App`. The framework adds standard options,
logging, config loading, project discovery, temp/cache directories, cleanup
hooks, and a command context.

Important Python packages include:

- `base_setup` - setup, checks, doctor, manifest parsing, artifacts, delegates,
  demo resolution, and project health.
- `base_projects` - project discovery, workspace reports, project command
  resolution, test command resolution, and build target resolution.
- `base_config` - local config path/show/doctor behavior.
- `base_logs` - runtime log inspection.
- `base_clean` - runtime cache/log/temp cleanup.
- `base_release` - release check/plan/notes/publish support.
- `base_dev` - developer profile setup/check/doctor/onboard support.
- `base_export_context` - deterministic local Markdown and Zip exports from a
  project's `.ai-context/` directory. Provider uploads are intentionally out of
  scope.
- `base_github_projects` - GitHub Project V2 schema inspection, configuration,
  and issue field updates for Base roadmap metadata.
