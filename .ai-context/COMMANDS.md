# Base Command Context

`basectl` is the public Base control-plane command. Run `basectl --help` for
the canonical current command list.

Long options with values use space-separated syntax, such as `--format json`.
Base rejects `--option=value` before command delegation. Arguments after `--`
belong to the delegated project command and may use that command's native
syntax.

`basectl` exposes `-v` as the command-level debug switch. Direct `base_cli`
package standard options such as `--debug`, `--quiet`, `--log-file`,
`--config`, `--environment`, and `--keep-temp` are not public `basectl`
options.

## Current Public Commands

- `basectl activate <project>` - start an interactive Base Bash runtime shell
  for a project.
- `basectl setup [project]` - install and bootstrap the local Base CLI
  environment and optional project artifacts.
- `basectl check [project]` - verify local Base and optional project artifacts
  without making changes, warning on non-blocking readiness issues.
- `basectl doctor [project]` - diagnose Base or project readiness and explain
  fixes.
- `basectl test [project]` - run a project's declared test command.
- `basectl build <project> [target...]` - run declared build targets.
- `basectl demo [project]` - run a declared interactive demo script.
- `basectl run <project> <command>` - run a declared project command.
- `basectl export-context [project]` - export `.ai-context/` as a Markdown or
  Zip bundle for manual upload or copy/paste into AI tools.
- `basectl trust <status|allow|revoke> <project>` - inspect, allow, or
  remove local approval for manifest-declared project commands.
- `basectl prompt <list|name>` - list and render repo-owned Markdown prompts
  for AI-assisted Base workflows. `product-self-review` prints the periodic
  product assessment prompt with current Base metadata, and `--output <path>`
  writes the rendered Markdown; Base does not send the prompt to an AI provider.
- `basectl docs` - open the Base documentation home page on GitHub.
- `basectl projects list` - list Base-managed projects discovered in the
  workspace.
- `basectl workspace <status|check|doctor|clone|pull|init|configure>` - inspect
  workspace status, checks, and diagnostics; explicitly clone expected
  repositories from a manifest; initialize a workspace from a workspace
  configuration repo; explicitly sync a local manifest from a configured
  canonical source; or apply repo configuration across a workspace.
  - `workspace status`, `workspace check`, and `workspace doctor` support
    `--format json`; `workspace clone`, `workspace pull`, `workspace init`, and
    `workspace configure` use text output.
  - `workspace clone` mutates repository checkouts only when invoked directly;
    `workspace pull` mutates only the local workspace manifest after validating
    the source; `workspace init` can clone the workspace configuration repo,
    update `~/.base.d/config.yaml`, and materialize manifest repositories.
  - `workspace configure --dry-run` previews delegated `repo configure` calls;
    without `--dry-run`, it skips missing or non-Base-managed repos, continues
    after per-repo failures, and reports configured/skipped/failed counts.
- `basectl repo <init|clone|check|configure|agent-guidance|installer-template>` -
  create repository baselines, clone GitHub repositories into the configured
  workspace, configure GitHub repository settings and default branch protection,
  repair missing Project intake support files, configure standard GitHub Project
  metadata, replace nonstandard Project layouts from `base-project-template`,
  seed agent guidance, and write installer templates. `repo init` defaults new
  repositories to the configured workspace root; use `--path .` for the current
  checkout. Plain `repo init` writes local baseline files without committing or
  pushing them; `repo init --agent-ready` also seeds `AGENTS.md` and `skills.md`;
  `repo check --agent-ready` verifies that baseline-integrated agent guidance
  contract; `repo init --pr` commits baseline changes on a branch, pushes to
  `origin`, and opens a PR.
- `basectl <setup|check|doctor> --ci <project>` - run Base setup/check/doctor
  with CI-safe defaults. It does not run project tests or create CI runners/VMs.
  `setup --ci --format json` uses `output` for the compact final status and
  adds `output_lines` on failures for intermediate context. `basectl ci`
  remains a compatibility alias.
- `basectl release <check|plan|notes|publish>` - inspect release readiness,
  print plans/notes, and publish guarded GitHub-side release artifacts.
- `basectl gh <area> <command>` - manage GitHub issues, PRs, branches, repo
  hygiene, and Project metadata using Base conventions.
  - `basectl gh issue create` defaults to category `enhancement` when
    `--category` is omitted and prints that default in command output. Pass
    `--assignee <login>` to assign an issue, or set
    `project.issue_defaults.assignee` in `.github/base-project.yml` for a
    repo-local default. Pass `--no-assignee` to ignore that default for one
    issue. Pass `--size <T|S|M|L>` when the issue scope is clear; otherwise
    Project metadata defaults to `Size=S`.
  - `basectl gh pr create` auto-injects `Fixes #<issue>` from Base branch
    names; pass `--no-fixes` to suppress that body injection. When
    `base_manifest.yaml` declares `github.pr`, it renders the PR body from
    that project policy.
  - `basectl gh project doctor --project <title>` - inspect Project metadata
    fields against the Base Project schema.
  - `basectl gh project configure --project <title>` - create or repair the
    standard Project metadata schema; pass `--replace-project` with `--repo`
    to archive and recreate a repo Project whose views are nonstandard; Projects
    that already have standard Base views are left intact.
  - `basectl gh project issue set-fields <number>` - add an issue to the
    Project if needed and update its metadata fields.
- `basectl clean` - remove old Base runtime logs, temp files, and cache entries.
- `basectl logs` - list, print, open, or tail recent Base CLI runtime logs.
- `basectl history` - list recent structured Base command runs from the local
  history index, with `--format json` for scripts.
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
- `base_dev` - prerequisite profile setup/check/doctor/onboard support,
  including dev, sre, ai, and linux-lab.
- `base_export_context` - deterministic local Markdown and Zip exports from a
  project's `.ai-context/` directory. Provider uploads are intentionally out of
  scope.
- `base_prompt` - repo-owned prompt listing and rendering. AI execution and
  provider integration are intentionally out of scope.
- `base_github_projects` - GitHub Project V2 schema inspection, configuration,
  and issue field updates for Base roadmap metadata.
