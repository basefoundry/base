# Changelog

All notable changes to Base will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Base versions are tracked in the repo-root `VERSION` file.

## [Unreleased]

### Added

- Added `base_cli.ExitCode` constants for Base's standard command return
  values.
- Added `cwd` support to `base_cli.testing.invoke()` so tests can run commands
  from an explicit project context without leaking the process working
  directory.
- Added `assert_executable` to `lib_std.sh` for explicit executable path checks.
- Added a test-local `BASE_CACHE_DIR` default to `base_cli.testing.invoke()`
  when `home` is supplied, with explicit environment overrides still honored.
- Added `run --quiet` to suppress expected `--no-exit` failure warnings in
  probe-style Bash checks.
- Added `ctx.dry_run` and `base_cli.option(..., dry_run=True)` so commands can
  explicitly connect nonstandard preview flags to Base's no-durable-write mode.
- Added `base_cli.App(max_log_files=...)` to let high-frequency CLIs prune old
  default log files during startup.
- Added `ctx.user_config` so Python commands can read typed user config without
  re-parsing `~/.base.d/config.yaml`.
- Added `base_cli.App.subcommand()` so one Python CLI can expose multiple
  Base-managed entry points.
- Added `docs/product-assessment.md` as a maintained review of Base's
  originality, usefulness, adoption potential, and engineering-skill evidence.

### Changed

- Aligned bootstrap and installer candidate-list splitting with the scoped
  `IFS=: read -ra` Bash pattern.
- Made `base_cli` log source paths prefer the active project root before
  falling back to the process working directory.

### Fixed

- Redacted compound secret-like command-output assignments such as
  `GITHUB_TOKEN=...`, `DB_PASSWORD=...`, and
  `AWS_SECRET_ACCESS_KEY=...` from setup failure summaries and debug logs.
- Removed `eval` from Bash `.baserc` guard variable snapshots while preserving
  Bash 4.2 compatibility.
- Replaced `install.sh` shell strict mode with explicit installer command
  failure handling.
- Corrected the `git_get_current_branch` usage message to name the current
  helper.
- Avoided subshell timestamp formatting in Bash `LOG_UTC` logging.
- Made `lib_std.sh` yes/no prompts read from the controlling terminal so
  redirected stdin stays available to the caller.
- Compared `lib_std.sh` Bash major and minor versions arithmetically so older
  major versions with two-digit minors cannot bypass the Bash 4.2 minimum.
- Resolved `lib_std.sh` relative imports without changing directories so
  failing imports cannot leave the caller on the script directory stack.
- Bounded `lib_std.sh` log caller stack walking so unusual stdlib-only frame
  chains cannot scan indefinitely while finding a source location.
- Made Bash `lib_std.sh` logging honor `LOG_UTC=1` so wrapper-driven Bash and
  Python logs use the same timestamp zone.
- Made `lib_std.sh` color initialization check stderr when deciding whether
  log colors can be rendered, so redirected stdout does not disable colored
  logs while stderr is still a terminal.
- Made `base_cli.App` reject duplicate command registrations instead of
  silently overwriting the first command.

## [1.0.0] - 2026-06-14

### Added

- Added `docs/why-base.md` as a concise evaluator page comparing Base with
  adjacent developer-environment tools.
- Documented Base's `uv` ecosystem boundary in `docs/tool-boundaries.md`.
- Clarified the Homebrew and source checkout install choices for users who
  already have Homebrew, Git, and Bash.
- Added a one-page command quick reference for the current `basectl` command
  surface.
- Added `.github/base-project.yml` to the standard `basectl repo init`
  baseline so repo Project taxonomy and issue defaults can move through the
  same review path as other repository files.
- Added repo Project metadata handoff to `basectl gh issue create` so new
  issues are added to the repo Project with defaults from
  `.github/base-project.yml` when the repository is known.

### Changed

- Changed `basectl repo` help to show command-specific options for each
  subcommand instead of one shared option list.
- Changed `basectl repo init --pr` to continue into GitHub-side configuration
  when the generated baseline is already present, while still stopping after
  opening a pull request when file changes are needed.
- Updated the Homebrew release process to require bottle publishing for
  supported macOS installs before accepting the 1.0 upgrade rehearsal.
- Removed the stale `CLAUDE.md` agent guide in favor of the canonical
  `AGENTS.md` guidance.

### Fixed

- Copied missing GitHub Project item field values into repo-specific Projects
  during `basectl repo configure` migrations, preserving existing target values.
- Made `assert_not_null` reject invalid variable-name arguments without logging
  the raw value, and clarified that callers must pass variable names.
- Made `lib_std.sh` dry-run handling treat `DRY_RUN` and `dry_run` values of
  `true`, `1`, `yes`, and `on` consistently, avoiding accidental live execution.
- Fixed documentation drift for `basectl logs` syntax, project virtual
  environment location, and README coverage of the `basectl ci` command.
- Made `basectl activate` prefer a uv project's repo-local `.venv` when
  `pyproject.toml` and `uv.lock` are present, avoiding a misleading
  Base-managed virtual environment in activated shells.

## [0.4.4] - 2026-06-12

### Added

- Protected default branches by default during `basectl repo configure`, with
  `--no-protect-default-branch` for repositories that intentionally skip the
  Base-managed ruleset.
- Added Base-managed GitHub Project metadata configuration through
  `basectl repo init`, `basectl repo configure`, and the lower-level
  `basectl gh project` surface.
- Added diagnostic workflow guidance for preserving failure evidence and
  routing follow-up fixes.

### Fixed

- Changed `basectl repo configure` to warn instead of fail when GitHub reports
  that default branch rulesets are unavailable for a private repository's plan.
- Made `basectl test base` package-aware so Homebrew-installed Base runs the
  packaged Python test layer and skips source-checkout-only BATS tests with
  clear guidance.

## [0.4.3] - 2026-06-11

### Added

- Added opt-in pull request creation for `basectl repo init --pr` so generated
  repository baselines can move through review before merge.

### Changed

- Changed `basectl update` to detect Homebrew-managed Base installs, hand off
  only to `brew upgrade codeforester/base/base`, preserve non-mutating dry-run
  output, and run setup with inherited Base environment variables cleared.

### Fixed

- Fixed `basectl repo agent-guidance` so it works from a repository directory
  without an explicit path and shows command-specific help.

## [0.4.2] - 2026-06-10

### Fixed

- Improved Bash startup recovery guidance when an existing shell still has a
  stale readonly `BASE_HOME` after a Homebrew upgrade.

## [0.4.1] - 2026-06-10

### Fixed

- Preserved explicit Homebrew `opt` symlink paths for `BASE_HOME` and
  Base-managed shell startup snippets after upgrades, avoiding stale versioned
  `Cellar` paths that can disappear after `brew cleanup`.

## [0.4.0] - 2026-06-10

### Added

- Added the local observability model for future command history, last-error
  explanation, and diagnostic report surfaces.
- Added read-only workspace manifest support for `basectl workspace status`,
  `check`, and `doctor` with `--manifest <path>`.
- Added guarded `basectl release publish` for annotated Git tags and GitHub
  Releases, including post-publish Homebrew handoff reporting.
- Added read-only `basectl release check|plan|notes` commands backed by
  manifest-owned release metadata.
- Added a text-first Base newcomer orientation deck and documented the optional
  PDF/PPTX export path.
- Added opt-in project Git `origin` reachability diagnostics with
  `basectl check|doctor <project> --remote-network`.
- Added an explicit `ai` prerequisite profile for Codex CLI and Claude Code
  setup, check, doctor, onboard, and shell completion flows.
- Added first-run seeding of `~/.base.d/config.yaml` with
  `workspace.root: ~/work` during `basectl setup`.
- Added `basectl export-context` for deterministic local Markdown and Zip
  bundles from a project's `.ai-context/` directory.

### Changed

- Expanded `basectl repo init` to seed portable project Git workflow guidance
  and a standard pull request template for Base-managed repositories.

### Fixed

- Replaced stale pre-1.0 rewrite guidance in the architecture repository
  conventions with current GitHub release and Homebrew tap ownership.
- Removed a hardcoded issue number from the 1.0 Homebrew upgrade reminder in
  `basectl release`.
- Kept `basectl ci setup --format json` output focused on a clean setup summary
  instead of embedding the delegated setup log stream.
- Validated workspace manifest repo URLs when a `repos[].url` value is provided.
- Removed forbidden shell strict mode from the project installer template.

## [0.3.0] - 2026-06-06

### Added

- Added a first-mile bootstrap documentation page and contributor setup guidance
  for source-based Base development.
- Added the workspace manifest design document to define the future team-shared
  repo-set contract and its relationship to discovered local projects.
- Added `basectl workspace check` and `basectl workspace doctor` for read-only
  project diagnostics across discovered workspace projects.
- Added named prerequisite profiles for `basectl setup/check/doctor/onboard`,
  using `--profile <list>` as the single profile selection surface and adding an
  initial local-only `sre` profile.
- Expanded `STANDARDS.md` into a broader Base contributor standard covering
  architecture layering, Bash, Python CLIs, `base-wrapper`, manifests, testing,
  documentation, and GitHub workflow.
- Added Go CLI guidance to `STANDARDS.md`, including Cobra as the default
  framework recommendation and Base's orchestration boundary for Go commands.
- Added `basectl repo init/check/configure` to create, validate, and configure
  a standard Base-managed repository baseline.
- Added GitHub remote branch cleanup to `basectl gh branch prune --remote` so
  safe merged branches can be deleted from GitHub before stale `origin/*` refs
  are pruned locally.
- Added `basectl gh worktree prune` for dry-run-by-default cleanup of stale,
  merged Git worktrees from PR trains.
- Added `basectl logs` to list, print, open, and tail recent Base CLI runtime
  logs.
- Added `basectl workspace status` as the first read-only workspace-level
  project health summary.
- Added `bootstrap.sh` as a first-mile macOS bootstrapper for installing
  Homebrew, Git, Bash, and Base before handing off to `basectl`.
- Added a top-level FAQ for common first-run and product questions.
- Added optional shell startup integration for sibling
  `base-platform-tools` checkouts.

### Changed

- Extracted shared `basectl run`, `basectl test`, and `basectl demo` project
  command helpers into one Bash helper module.
- Changed `base_logs` to use `base_cli.App` without default persistent log
  creation, so `basectl logs -v` enables debug diagnostics without adding a
  self-log entry.
- Changed `basectl demo` to infer the current project from the nearest
  `base_manifest.yaml` when the project argument is omitted.
- Changed `basectl repo init --repo` to create private GitHub repositories by
  default, with explicit `--public` and `--private` visibility flags.
- Updated Base-managed shell profile sections to use shorter `>>> base: ...`
  markers, clearer overwrite guidance, and quoted source paths.
- Moved the optional `caff` and `sort-in-place` utility CLIs out of Base and
  into `codeforester/base-platform-tools`.

### Fixed

- Pretty-printed workspace JSON output for `basectl workspace status`, `check`,
  and `doctor`.
- Fixed `basectl gh` authentication diagnostics to include the underlying
  `gh auth status` output when GitHub access fails.
- Converted `bootstrap.sh` away from shell strict mode to explicit command
  failure checks that match Base shell standards.
- Clarified `BASE-H001` required-environment findings as repeated rule
  instances keyed by `(id, name)` and report empty required variables as empty.
- Removed the placeholder `BASE-P000` default from `ArtifactCheck` so project
  doctor findings must declare explicit stable IDs.
- Updated the README status section to match the current `0.4.0` release.
- Fixed `basectl repo init` to create new repositories under the configured
  workspace root instead of the caller's current directory.
- Fixed `basectl repo init --dry-run` to explicitly report planned GitHub
  repository creation or explain why GitHub creation is skipped.
- Fixed `basectl repo` dry-run output to print readable quoted GitHub command
  arguments instead of backslash-escaped words.
- Fixed `basectl update` to allow harmless untracked files while still blocking
  tracked local changes.
- Fixed `basectl gh branch prune` output to report worktree-attached and
  upstream-protected branches as clear skips instead of raw Git errors.
- Fixed `basectl gh branch prune` and `basectl gh worktree prune` to recognize
  squash-merged PR branches through GitHub when Git ancestry is not enough.
- Fixed `bin/base-test` to stop invoking migrated utility CLI test suites.

## [0.2.0] - 2026-05-30

### Added

- Added documentation for the no-hooks manifest boundary and future setup hook
  criteria.
- Added the design target for a future structured `python:` manifest section.
- Added the user-local IDE preference design for `~/.base.d/config.yaml`.
- Added documentation guidance for using `mise` with Go and Java projects.
- Added documentation for the boundary between `basectl onboard` and
  project-owned installers.
- Added a repo-owned `bin/base-test` runner and declared it through
  `base_manifest.yaml` so Base can dogfood `basectl test base`.
- Added GitHub CLI authentication diagnostics to developer prerequisite checks.
- Added `basectl test <project> -- <args...>` passthrough for delegated test
  command arguments.

### Changed

- Updated `basectl test` to warn when a project virtual environment is missing
  before running a project's test command.
- Changed the mise manifest check to report a warning instead of a full pass
  when Base has verified only the config file and `mise` CLI availability.
- Updated contributor test documentation to use `pytest` and the Base dogfood
  test command.

### Fixed

- Fixed `basectl gh issue` shell completions to use `--category` and the
  current GitHub workflow labels.
- Replaced an optimized-away Python `assert` in project test command resolution
  with an explicit invariant error.
- Isolated `base_cli` tests from ambient `BASE_CACHE_DIR` overrides.

## [0.1.0] - 2026-05-29

### Added

- Added `basectl` as the umbrella command for Base workspace operations.
- Added project setup through `basectl setup [project]`, including the Bash
  bootstrap layer and Python manifest reconciliation layer.
- Added project health checks through `basectl check [project]` and deeper
  diagnostics through `basectl doctor [project]`.
- Added `basectl activate <project>` for project-specific runtime subshells.
- Added `basectl projects list` for workspace project discovery.
- Added `basectl test <project>` for manifest-declared project test commands.
- Added `basectl onboard` for guided first-run Base setup.
- Added `basectl clean` for pruning Base runtime artifacts from the cache root.
- Added `basectl update` and `basectl update-profile` for repo updates and
  shell profile wiring.
- Added Bash and Zsh completions for `basectl`.
- Added Base manifests with support for curated artifacts, default artifacts,
  developer prerequisite manifests, Brewfile delegation, mise installation, and
  project test commands.
- Added Base-owned Python and Bash helper libraries for writing project CLIs and
  scripts consistently.
- Added macOS-oriented cache separation under `~/Library/Caches/base`.
- Added Homebrew tap packaging support for installing Base through Homebrew.

### Changed

- Standardized project virtual environments under `~/.base.d/<project>/.venv`.
- Standardized Base logs on stderr so command stdout can remain scriptable.
- Moved public product backlog tracking from `TODO.md` into GitHub Issues.

### Security

- Restricted Base Python CLI log files to user-only permissions.
- Hardened setup and CI behavior around environment escape hatches, JSON output,
  shell quoting, and pinned CI Python dependencies.
