# Base Command Context

`basectl` is the public Base control-plane command. Run `basectl --help` for
the journey-oriented command map. Run `basectl help <nested path>` or append
`--help` to that path for the same leaf-specific usage.

Long options with values use space-separated syntax, such as `--format json`.
Base rejects `--option=value` before command delegation. Arguments after `--`
belong to the delegated project command and may use that command's native
syntax.

`basectl` exposes `-v` as the command-level debug switch. Direct `base_cli`
package standard options such as `--debug`, `--quiet`, `--log-file`,
`--config`, `--environment`, and `--keep-temp` are not public `basectl`
options. Pre-runtime diagnostics use `--debug-wrapper`, and
`--utc-wrapper` switches wrapper/runtime log presentation to UTC.
`--verbose-wrapper` remains a deprecated alias for `--debug-wrapper` through
the v1.x compatibility window; new automation should use `--debug-wrapper`.

## Current Public Commands

- `bootstrap.sh` - first-mile installer/repair script used before `basectl`
  may be available. `bootstrap.sh --ensure-bash --dry-run` previews the
  supported Bash 4.2+ repair path, and `bootstrap.sh --ensure-bash --yes`
  applies only that Bash prerequisite: Homebrew `bash` on macOS, or
  `sudo apt-get update` plus `sudo apt-get install -y bash` on Ubuntu/Debian.
  It does not clone Base, install Python, create virtualenvs, install developer
  tools, or run project setup.
- `basectl activate <project>` - start an interactive Base Bash runtime shell
  for a project.
- `basectl setup [project]` - install and bootstrap the local Base CLI
  environment and optional project artifacts.
- `basectl check [project]` - check Base readiness only by default; pass a
  project name or `--manifest` to also check manifest-declared project
  requirements. It does not install or repair prerequisites, modify project
  files, or run project tests. Warning-only results exit successfully, while
  `--format json` provides stable finding IDs for automation.
- `basectl doctor [project]` - diagnose Base or project readiness and explain
  fixes.
- `basectl test [project]` - run a project's declared test command.
- `basectl build [project] [target...]` - run declared build targets for the positional, explicit, or nearest project.
- `basectl demo [project]` - run a declared interactive demo script.
- `basectl run [project] <command>` - run a declared command for the positional, explicit, or nearest project.
- `basectl export-context [project]` - export `.ai-context/` as a Markdown or
  Zip bundle for manual upload or copy/paste into AI tools.
- `basectl trust status [project]` - inspect one project's manifest command
  trust or all discovered command-bearing projects.
- `basectl trust <allow|revoke> <project>` - add or remove local approval for
  manifest-declared project commands.
- `basectl prompt <list|name>` - list and render repo-owned Markdown prompts
  for AI-assisted Base workflows. `product-self-review` prints the periodic
  product assessment prompt with current Base metadata, and `--output <path>`
  writes the rendered Markdown; Base does not send the prompt to an AI provider.
- `basectl docs` - open the Base documentation home page on GitHub.
- `basectl projects list` - list Base-managed projects discovered in the
  workspace.
- `basectl workspace <status|check|doctor|onboarding|agent-brief|clone|pull|update|init|configure|setup>` -
  inspect workspace status, checks, diagnostics, read-only first-day
  onboarding, and local agent-handoff readiness; explicitly clone expected
  repositories from a manifest; initialize a workspace from a workspace
  configuration repo; explicitly sync a local manifest from a configured
  canonical source; apply repo configuration across a workspace; or run local
  project setup across eligible repositories.
  - `workspace status`, `workspace check`, `workspace doctor`,
    `workspace onboarding`, and `workspace agent-brief` support `--format json`;
    `workspace clone`, `workspace pull`, `workspace update`, `workspace init`, `workspace configure`,
    and `workspace setup` use text output.
  - `workspace check` presents check-oriented readiness messages; `workspace doctor`
    presents actionable findings with stable IDs and fix guidance. Workspace
    check-record persistence is optional: failures are reported per project in
    text and through JSON/YAML `record_warnings` without changing health status
    or exit semantics.
  - `workspace onboarding` summarizes ready, needs-setup, invalid-manifest,
    missing-required, and missing-optional repository state without cloning
    repositories or running setup.
  - `workspace agent-brief` reports baseline, agent-guidance, AI-context,
    environment, and validation evidence for expected and extra Base-managed
    repositories. It is local and read-only; manifest-declared test execution
    stays behind a recommended `basectl test` command.
  - `workspace clone` mutates repository checkouts only when invoked directly;
    `workspace pull` mutates only the local workspace manifest after validating
    the source; `workspace init` can clone the workspace configuration repo,
    update `~/.base.d/config.yaml`, and materialize manifest repositories;
    init and pull share one local `file://` parser that percent-decodes once,
    accepts empty or `localhost` authority, and rejects remote authorities;
    `workspace update` runs `git pull --ff-only` across present repositories in
    manifest order, including the active Base checkout when it is the
    manifest's `base` target;
    `workspace setup` delegates local project setup serially in manifest order.
  - `workspace configure` previews delegated `repo configure` calls by default;
    `--apply` authorizes changes and prompts unless `--yes` is supplied. `--yes`
    alone is rejected. Applied runs skip missing or non-Base-managed repos,
    continue after per-repo failures, and report configured/skipped/failed counts.
  - `workspace setup --dry-run` previews delegated `basectl setup` calls;
    without `--dry-run`, it skips ineligible repositories, continues after
    per-repo failures, and reports setup/skipped/failed counts. `--yes` forwards
    confirmation to each delegated setup command.
  - `workspace update --dry-run` previews the ordered Git pull plan; without
    `--dry-run`, it continues after per-repo failures and reports
    updated/unchanged/skipped/failed counts.
- `basectl repo <init|clone|check|configure|agent-guidance|installer-template>` -
  create repository baselines, clone GitHub repositories into the configured
  workspace, configure GitHub repository settings, default branch protection,
  non-default branch naming enforcement, and the trusted issue/category branch
  policy status, repair missing Project intake support files, configure standard
  GitHub Project metadata, replace nonstandard
  Project layouts from `base-project-template`, seed agent guidance, and write
  installer templates. `repo init` defaults new
  repositories to the configured workspace root; use `--path .` for the current
  checkout. Plain `repo init` writes local baseline files without committing or
  pushing them; `repo init --agent-ready` also seeds `AGENTS.md` and `skills.md`;
  `repo check` follows the manifest-declared `./bin/base-test` validation path
  for Base itself while generated repositories retain `tests/validate.sh`;
  `repo check --agent-ready` verifies that baseline-integrated agent guidance
  contract; `repo init --pr --issue <number>` commits baseline changes on a
  canonical issue-backed branch, pushes to `origin`, and opens a PR. Offline
  `--pr --dry-run` previews also require `--category <name>`.
  `repo init --language <csv>` may be repeated for explicit, normalized
  language metadata; selecting `python` adds the explicit
  `python.manager: uv` profile while other initial language values are metadata
  only.
- `basectl <setup|check|doctor> --ci [project]` - run Base setup/check/doctor
  with CI-safe defaults. It does not run project tests or create CI runners/VMs.
  `setup --ci --format json` uses `output` for the compact final status and
  adds `output_lines` on failures for intermediate context. The former
  `basectl ci setup|check|doctor` remains a deprecated compatibility alias for
  the canonical lifecycle command with `--ci`.
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
    Project metadata defaults to `Size=S`. Project updates must target a
    Project linked to the issue repository unless `--allow-cross-repo` is
    supplied for an intentional cross-repository maintenance operation.
  - `basectl gh issue readiness <number>` checks required implementation issue
    body sections and reports labels and assignees. Pass `--project-owner` and
    `--project-number` with `--repo` to validate Base Project fields; without
    Project coordinates it reports a partial result.
  - `basectl gh issue start <number>` resolves issue metadata from an explicit
    `--repo`/`-R` selector, then `GH_REPO`, then the origin remote.
  - `basectl gh auth status` inspects stored GitHub authentication state
    without displaying token values; `basectl gh auth refresh` refreshes the
    stored credential and can request repeatable OAuth scopes.
  - `basectl gh pr create` auto-injects `Fixes #<issue>` from Base branch
    names and fails before PR creation when the prefix disagrees with the
    issue's single category label; pass `--no-fixes` to suppress only that body injection. When
    `base_manifest.yaml` declares `github.pr`, it renders the PR body from
    that project policy.
  - `basectl gh branch prune` previews safe merged-branch cleanup by default;
    pass `--closed-unmerged` to include branches whose pull requests were
    closed without merging.
  - `basectl gh worktree prune` previews safe merged-worktree cleanup by
    default; pass `--closed-unmerged` to include clean worktrees tied to
    closed, unmerged pull requests.
  - `basectl gh project doctor --project <title>` - inspect Project metadata
    fields against the Base Project schema.
  - `basectl gh project configure --project <title>` - create or repair the
    standard Project metadata schema; pass `--replace-project` with `--repo`
    to archive and recreate a repo Project whose views are nonstandard; Projects
    that already have standard Base views are left intact.
  - `basectl gh project issue set-fields <number>` - add an issue to the
    Project if needed and update its metadata fields. The command rejects
    repository/Project mismatches by default; pass `--allow-cross-repo` only
    when that mismatch is deliberate.

Stable read-only inspection JSON uses one schema-versioned envelope across
`repo check`, `release check`, `gh issue readiness`, and `gh branch stale`.
Pass `--format json`; text remains the default. Completed inspections keep
findings in `data` with `error: null`, while controlled usage or upstream
failures use an `error` object. The canonical field contract and exit semantics
are documented in `docs/inspection-json.md`.
- `basectl clean` - preview old completed Base run bundles and component caches;
  it requires `--yes` for deletion, reports and retains active runs, rejects
  symlinked paths below the resolved Base cache root, and never follows them
  during deletion.
- `basectl logs` - list, print, open, or tail recent Base CLI runtime logs.
- `basectl history` - list recent structured Base command runs from the local
  history index, with comma-separated OR filters such as
  `--command check,doctor`, `--format json` for scripts, and `--report` for a
  privacy-conscious Markdown or JSON activity report. Rejected usage
  invocations (status `2`), including an explicitly named nonexistent project,
  leave no persistent run bundle, log, or history row. Failures after command
  usage is accepted remain observable.
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

Base Python commands use the Base-owned `base_cli_app()` adapter. It passes
`base_cli_profile()` to newer `base_cli.App` releases and preserves the
historical constructor path for older installed releases. The generic framework
adds standard options, logging, temp/cache directories, cleanup hooks, and a
command context; the adapter supplies Base configuration, manifest discovery,
runtime placement, and history policies.

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
