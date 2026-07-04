# Changelog

All notable changes to Base will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Base versions are tracked in the repo-root `VERSION` file.

## [Unreleased]

## [1.6.0] - 2026-07-04

### Added

- Added an explicit `linux-lab` prerequisite profile that checks and installs
  Multipass via Homebrew cask for local Ubuntu lab VMs without creating VM
  instances during Base setup.

### Changed

- Bound Base CI source-checkout jobs to the published `base-bash-libs` v1.1.0
  release commit.

### Fixed

- Stopped `basectl` from continuing under Rosetta when it resolves native
  Apple Silicon Homebrew at `/opt/homebrew`, so setup fails early with Bash
  recovery guidance instead of breaking during a later `brew install`.
- Replaced stray shell `run` calls in setup's virtualenv and apt install paths
  with direct command execution so spawned `basectl setup` runs do not depend on
  a test-harness helper.
- Stopped default project checks from failing Ubuntu/Linux acceptance solely
  because manifest-declared IDE extension CLIs such as `code` are not on `PATH`;
  IDE extension diagnostics now run with the developer profile.
- Made the `tool:bats-core` project artifact platform-aware on Ubuntu/Debian,
  mapping it to the system `bats` package instead of planning a Homebrew
  `brew install bats-core` command.
- Preflighted `mise` trust before `basectl setup` runs `mise install`, so
  untrusted project configs fail with a Base recovery message instead of raw
  lower-level `mise install` output.
- Bootstrapped `mise` during Ubuntu/Debian project setup when a manifest
  declares a project-owned mise config, while keeping the mutation guarded by
  `--dry-run` review and `--yes`.
- Bootstrapped `uv` during Ubuntu/Debian project setup when a manifest
  explicitly opts into `python.manager: uv` or `runner: uv`, while keeping the
  mutation guarded by `--dry-run` review and `--yes`.
- Allowed repeated Ubuntu/Debian `basectl setup` runs without `--yes` when all
  apt prerequisites are already installed, while still requiring `--yes` before
  Base mutates apt-managed system packages.
- Made `basectl setup --profile dev`, `check --profile dev`, and
  `doctor --profile dev` use apt-backed BATS, GitHub CLI, and ShellCheck
  handling on Ubuntu/Debian instead of requiring Homebrew.
- Made explicit project setup/check routing ignore active-project virtualenv
  overrides from a different shell project, so commands such as
  `basectl setup base-demo` cannot accidentally reuse the `base` venv.
- Made project Brewfile delegates platform-aware: macOS still runs Homebrew
  `brew bundle`, while Ubuntu/Debian skips Brewfile setup/check as a warning so
  uv-managed projects can proceed through `uv sync`.

## [1.5.0] - 2026-07-02

### Added

- Added `BASE_PLATFORM` runtime metadata so Linux distribution-family support
  can be represented without overloading the coarse `BASE_OS=linux` contract.
- Added Ubuntu/Debian source-checkout CI validation and documented the
  accepted Ubuntu 24.04 ARM64 Parallels validation path.
- Added Linux-aware `basectl check` and `basectl doctor` prerequisite
  diagnostics for Python venv support, Git, GitHub CLI, BATS, ShellCheck, jq,
  and Go on Ubuntu/Debian.

### Changed

- Centralized setup/check platform dispatch so macOS, Ubuntu/Debian, unknown
  Linux, and unsupported platforms are routed through explicit platform-policy
  helpers instead of scattered command conditionals.
- Changed Ubuntu/Debian setup behavior to fail conservatively with manual
  prerequisite guidance until full apt-backed bootstrap support is implemented.
- Updated compatibility, Linux-support, IDE-boundary, and forge-boundary docs
  to reflect Ubuntu/Debian runtime support and the remaining non-goals.

### Fixed

- Scrubbed activate override variables in the source-checkout test harness so
  local shell state does not leak into BATS validation on Ubuntu or macOS.

## [1.4.0] - 2026-07-01

### Added

- Added a contract registry and contract check runner, then wired those checks
  into the default local and CI validation path.
- Broadened CI coverage for high-level workflows, supported Python minors,
  macOS shell surfaces, Project Intake behavior, and safe portions of macOS
  install validation.

### Changed

- Consolidated shared command helpers for project execution, GitHub repository
  parsing, workspace clone handling, command history, and log display.
- Reduced subprocess usage in shell prompts, GitHub helpers, update-profile
  newline checks, setup profile normalization, and timestamp formatting.
- Continued splitting large Python command surfaces into focused modules while
  adopting shared `ExitCode` handling across production engines.

### Fixed

- Made `basectl check` warn when Homebrew reports installed Xcode Command Line
  Tools are outdated or incomplete, matching the existing `basectl doctor`
  finding while keeping the check non-blocking.
- Fixed `basectl export-context --format zip --output <directory>` so directory
  outputs resolve to the default archive filename instead of leaking filesystem
  exceptions.
- Fixed redirected-stdin prompt handling for onboarding and the self-demo, and
  made BATS reusable-library fixture resolution portable across source
  checkouts.
- Replaced remaining runtime `assert` guards and implicit failures in Python
  paths with explicit runtime errors, exit codes, or documented policies.
- Added timeouts to subprocess-heavy release, workspace, setup, Project Intake,
  and diagnostic paths so failures stay bounded.
- Aligned setup, doctor, and Python-backed subcommand output streams with the
  documented stdout/stderr contract.

### Security

- Pinned GitHub Actions and the `base-bash-libs` CI dependency, declared
  minimal workflow permissions, and hardened generated repository workflows
  against drift from Base CI policy.
- Added project installer template integrity verification and surfaced skipped
  checksum verification clearly.
- Avoided shell-interpolated AI installer URLs and rejected or warned on
  cleartext HTTP workspace repository URLs.
- Created Python CLI log files with restrictive permissions atomically.

### Documentation

- Refreshed command reference, architecture, execution model, bootstrap,
  contributor setup, GitHub workflow, Project metadata, doctor findings,
  observability, and Linux-support posture documentation to match the shipped
  command surface.
- Documented the future `base_cli` extraction boundary, production
  `AssertionError` policy, CI setup JSON stderr replay contract, and intentional
  blocking behavior in `basectl logs`.

## [1.3.0] - 2026-06-28

### Added

- Added `basectl docs` as a convenience shortcut to open the Base GitHub README
  documentation entrypoint, with `--show-url` for non-browser contexts.
- Added CI setup JSON rendering and a documented CI supply-chain hardening
  policy for Base-managed bootstrap paths.
- Added project Python runtime diagnostics and release title placeholder
  validation.
- Added optional pinned Homebrew installer support for first-mile bootstrap
  environments that need a verified installer source.
- Added direct coverage for Base command helpers, source guards, completions,
  bootstrap, install, and command-dispatch lifecycle behavior.

### Changed

- Standardized the `basectl` public command lifecycle around space-separated
  long options, compact usage errors, consistent help routing, and explicit
  command-level logging options.
- Routed Python command packages through the shared `base_cli` lifecycle and
  moved project command metadata, CI JSON rendering, and GitHub Project issue
  defaults into Python-backed helpers.
- Improved shell and completion performance by caching project-name completion
  results, reducing Git prompt subprocess work, and reducing setup/profile
  subprocess use.
- Split repository helper ownership into focused `repo installer-template` and
  `repo agent-guidance` modules, and centralized project command execution
  helpers for `test`, `build`, `run`, and `demo`.
- Hardened GitHub and Homebrew workflow handling with structured Homebrew trust
  parsing, bounded GitHub authentication diagnostics, release-publish recovery
  guidance, and portable GitHub Bash helper documentation.
- Improved Base maintainability by normalizing Bash source guards, making the
  Base home verification contract explicit, enforcing Python future annotation
  standards, and using explicit error handling in `base-test`.

### Fixed

- Fixed nested and top-level completion parity gaps across Bash and Zsh.
- Fixed inherited `basectl update` source-guard state so repeated sourced
  command execution does not leak between invocations.
- Fixed interactive prompt handling so redirected stdin does not block
  onboarding and self-demo prompts from reading the terminal.
- Fixed diagnostic probe duplication and bounded subprocess probes for Base
  diagnostics.
- Fixed sensitive value exposure in `basectl config show` and setup command
  argument logging.
- Fixed `base_cli` history records to use the effective argv for displayed
  command history.

## [1.2.0] - 2026-06-24

### Added

- Added `basectl workspace init` to clone a workspace repository, read its
  workspace configuration, and clone the repositories declared by that
  workspace.
- Added `basectl prompt list` and `basectl prompt product-self-review` to render
  repo-owned Markdown prompts for periodic AI-assisted Base workflow reviews.
- Added a local command-history index for Python-backed Base command runs.
- Added manifest-declared PR policy support for Base-managed GitHub PR helpers.
- Added project Python version requirements and declarative artifact registry
  support for Base-managed artifacts.

### Changed

- Added `ctx.workspace_root` to `base_cli.Context` so workspace-aware commands
  can use the configured workspace root without reaching through user config.
- Improved `basectl repo clone`, `repo check`, `repo configure`, and
  `gh issue create|start` diagnostics so repository workflow failures include
  clearer update, chmod, origin, Project-field, and worktree-command guidance.
- Made `basectl repo configure` warn when Homebrew reports the local GitHub CLI
  package is outdated, pointing users to `basectl setup --profile dev`.
- Made lifecycle command usage errors compact and consistent, returning exit
  code `2` for `setup`, `check`, `doctor`, `onboard`, and `update-profile`.
- Made idempotent `basectl setup` reconciliation quieter when no action is
  required.
- Added `base_cli.testing.invoke(..., manifest={...})` for project-aware tests
  that need a fixture `base_manifest.yaml`.
- Added optional stream and formatter overrides to `base_cli.configure_logger`
  for tests and CI wrappers that need to capture or reshape user-facing logs.
- Added `base_cli.App(help=...)` support for subcommand group help text.
- Added standard `--quiet` / `-q` support to `base_cli.App` to suppress INFO
  output on the user-facing stream while preserving warnings, errors, and
  persistent DEBUG log detail.
- Documented the `base-bash-libs` Homebrew/core readiness path, including the
  formula-name audit command and future `basefoundry` dependency plan.
- Documented the `basectl setup` parallelism evaluation and the decision to
  keep mutating setup serial until a setup-plan/preflight layer exists.
- Corrected 1.1.0 documentation status, source-checkout `base-bash-libs`
  prerequisites, future-design banners, and CI bootstrap package guidance.

### Fixed

- Fixed `basectl prompt -v <name>` so the verbose flag no longer counts as a
  second prompt argument.
- Added actionable recovery guidance when `basectl update-profile` detects a
  runtime `BASE_HOME` mismatch.
- Fixed workspace reports for uv-managed project virtual environments and
  broken project virtualenv detection.
- Fixed project `--recreate-venv` repair and fail-fast runtime directory
  handling for check diagnostics.
- Allowed standard `base_cli.App` options such as `--debug` and
  `--environment` before subcommand names.
- Made `base_cli.option(..., dry_run=True)` reject duplicate dry-run markers on
  the same command function.
- Made default `base_cli.App(max_log_files=...)` log retention prune by
  timestamp-prefixed run-id filename instead of filesystem modification time.

## [1.1.0] - 2026-06-21

### Changed

- Suppressed pip self-upgrade notices during Base-managed pip installs so
  setup output stays focused on Base actions and real install failures.
- Made live workflow docs and installer examples main-ready, using default-branch
  URLs for raw GitHub install scripts and `main` for contributor branch
  examples.
- Documented the boundary for optional personal shell defaults such as color
  aliases, navigation shortcuts, signing helpers, and strict shell modes.
- Improved opt-in Bash and Zsh completion ergonomics for interactive shell
  defaults.
- Added conservative pager and terminal usability behavior to opt-in shell
  defaults.
- Enriched opt-in shell history defaults for `basectl update-profile --defaults`.
- Made Homebrew-managed `version: latest` profile and project artifacts report
  outdated installed packages during `check`/`doctor` and upgrade them during
  `setup`.
- Renamed the Base-managed GitHub Project metadata schema from `base-roadmap`
  to `base-project`.
- Made `basectl repo configure` report missing `BASE_PROJECT_TOKEN` Project
  intake secrets and improved generated workflow diagnostics when the Actions
  token cannot see repo Projects.
- Made Homebrew-managed `basectl update` preflight tap trust before upgrading
  Base when Homebrew requires trust for the tap-owned `base-bash-libs`
  dependency.
- Removed Base's bundled reusable Bash `std`, `file`, and `git` libraries;
  Base now requires external `base-bash-libs` through an explicit override,
  sibling checkout, or Homebrew package.

### Fixed

- Made Homebrew artifact dry-run tests independent of the developer machine's
  installed or outdated Homebrew formulae.

## [1.0.5] - 2026-06-18

### Added

- Added `BASE_BASH_LIBS_SOURCE` and `BASE-D007` diagnostics so `basectl check`
  and `basectl doctor` report whether Base is using external reusable Bash
  libraries or the bundled fallback.
- Added BATS coverage proving Base can bootstrap from external
  `base-bash-libs` when bundled reusable Bash library directories are absent.

### Changed

- Documented Homebrew tap trust for Base and standalone `base-bash-libs`
  installs, and updated direct Base upgrade examples to use
  `brew upgrade --no-ask basefoundry/base/base`.

### Fixed

- Fixed Bash library readiness BATS assertions so they pass both with a sibling
  `base-bash-libs` checkout and with bundled fallback.

## [1.0.4] - 2026-06-17

### Changed

- Made Base resolve reusable Bash libraries from an external `base-bash-libs`
  checkout or Homebrew package when available, while keeping the bundled
  `lib/bash` tree as a fallback.
- Documented the standalone `base-bash-libs` install path, Base's consumption
  contract, and the migration gate for eventually removing bundled reusable
  Bash libraries.

## [1.0.3] - 2026-06-17

### Changed

- Made `basectl repo init` print visible next steps when GitHub setup is skipped
  because no repository was provided or inferred.
- Made `basectl repo clone` print the Base baseline check hint only when the
  cloned repository contains `base_manifest.yaml`.
- Made `basectl repo agent-guidance` detect the target repository default
  branch before falling back to `main`.
- Made `basectl repo agent-guidance` print a visible created/unchanged summary
  when existing guidance files are left untouched.
- Made `basectl repo installer-template` write `./install.sh` by default and
  added `--print`/`--stdout` for the stdout template view.
- Added dirty-worktree and repository-root fix hints for `basectl repo`
  subcommands that create pull requests.
- Clarified `basectl repo init` and `repo configure` help to say Base-managed
  GitHub settings are safe to re-run and do not remove outside settings.
- Made live `basectl repo configure` runs print a structured action summary for
  repository settings, labels, branch protection, and Project metadata.
- Made `basectl repo check` print visible success/failure summaries with counts
  and repair commands when files are missing.
- Made `basectl repo init --pr` print next steps after opening a baseline pull
  request, including the command to rerun after merge.
- Clarified `basectl repo init` and `repo configure` help to distinguish local
  baseline updates, optional GitHub repo creation, and GitHub-side repair.
- Made `basectl ci setup --format json` include compact `output_lines` on
  setup failures so CI consumers keep intermediate diagnostic context.
- Standardized Bash CLI usage errors on `print_error` and changed unknown
  config, projects, release, and workspace commands to return usage status
  without fatal stack traces.

## [1.0.2] - 2026-06-16

### Added

- Added `basectl repo clone` for workspace-aware cloning of one GitHub
  repository into the configured Base workspace.
- Added `--pr` support to `basectl repo agent-guidance` and
  `basectl repo installer-template` so optional generated helper files can be
  committed on predictable branches and opened as draft pull requests.
- Added `basectl workspace clone --manifest <path>` for manifest-driven
  workspace checkout, with dry-run support and optional repositories gated by
  `--include-optional`.
- Added a generated Project intake workflow so Base-managed repos can
  idempotently add externally-created issues to their repo Project and apply
  default Project fields.
- Added explicit uv-managed Python project support with `python.manager: uv`,
  delegated `uv sync` setup, uv diagnostics, and command-level `runner: uv`
  support for test, run, demo, and build commands.

### Changed

- Changed `basectl update` to accept an optional project name, so
  `basectl update <project>` updates that project checkout and then runs
  `basectl setup <project>`, while omitting the project keeps the existing
  Base update behavior.

### Fixed

- Fixed `basectl gh` to run the requested GitHub command before using
  `gh auth status` diagnostics, avoiding false failures when the status probe
  is transiently unavailable.

## [1.0.1] - 2026-06-15

### Added

- Added Base's own `.github/base-project.yml` so Base issues get repo Project
  defaults through the same reviewed config file as other Base-managed repos.
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

- Moved the README license notice out of the opening product summary and made
  the MIT-to-AGPL version boundary explicit.
- Made `basectl repo init` generate AGPL-3.0-or-later licenses for new
  repositories.
- Relicensed Base prospectively from MIT to AGPL-3.0-or-later.
- Aligned bootstrap and installer candidate-list splitting with the scoped
  `IFS=: read -ra` Bash pattern.
- Clarified that `basectl activate` starts a Bash runtime shell and that
  `BASE_ACTIVATE_SHELL` must point to Bash.
- Normalized Base's built-in default, developer, and SRE profile manifest
  names to the same safe project-name syntax enforced for project manifests.
- Made `base_cli` log source paths prefer the active project root before
  falling back to the process working directory.

### Fixed

- Made `basectl repo configure` create missing Project intake support files for
  older Base-managed repositories.
- Made `basectl repo init` generate repo-specific AGPL license files without
  copying Base's own application notice into new repositories.
- Made `basectl repo configure` apply `.github/base-project.yml`
  `issue_defaults` to existing repo Project issue items that are missing those
  values.
- Reported a clear error when `BASE_ACTIVATE_SHELL` points to a non-Bash shell.
- Made setup BATS command helpers run with noninteractive stdin so PTY-backed
  test runs exercise recovery guidance consistently.
- Redacted compound secret-like command-output assignments such as
  `GITHUB_TOKEN=...`, `DB_PASSWORD=...`, and
  `AWS_SECRET_ACCESS_KEY=...` from setup failure summaries and debug logs.
- Rejected path-unsafe `project.name` values in `base_manifest.yaml` before
  they can be used in Base-managed state paths.
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
- Made `basectl doctor` warn when Homebrew reports installed Xcode Command Line
  Tools are outdated or incomplete.

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
  only to `brew upgrade basefoundry/base/base`, preserve non-mutating dry-run
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
  into `basefoundry/base-platform-tools`.

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
