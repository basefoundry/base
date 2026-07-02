# Base Status Context

## Current Release

Base `1.5.0` is the current release. The repo-root `VERSION` file is updated
only during release-prep PRs, not on every ordinary PR.

## Current Implemented Areas

The current command surface covers:

- setup and first-mile bootstrap
- checks and doctor diagnostics
- project discovery
- project activation
- declared project test, build, run, and demo commands, including explicit
  `runner: uv` delegation
- advisory check/doctor lint warnings for missing manifest command executables
  and project script paths
- mise integration
- bundled declarative artifact registry for Base-managed built-in artifacts
- explicit uv-managed Python project setup through `python.manager: uv`
- project Python runtime requirements through `python.requires_python`
- cleanup, logs, and local command history
- local config inspection
- onboarding
- repository baseline creation and checks
- GitHub issue, PR, branch, and worktree helpers
- workspace status/check/doctor/init/clone/pull/configure flows
- release readiness inspection and guarded GitHub release publishing
- local AI context export bundles
- repo-owned prompt rendering through `basectl prompt`
- documentation entrypoint opening through `basectl docs`
- explicit `ai` prerequisite profile for Codex CLI and Claude Code
- Ubuntu/Debian runtime checks, diagnostics, and source-checkout validation

## Active Development Direction

The `v1.5.0` release is complete. Future work is tracked in GitHub Issues,
with Linux bootstrap polish, GitHub CLI install/auth polish for Ubuntu,
Docker/service artifacts, broader prompt ergonomics, and broader setup policy
work remaining outside the 1.5 release contract.

The Homebrew bottle and consumer upgrade contract has passed the #526 rehearsal.
Supported macOS installs should continue to use bottled Homebrew packages, with
source builds treated as fallback validation rather than the normal user path.

Recent released work includes:

- Ubuntu/Debian runtime support through `BASE_PLATFORM=linux-debian`,
  platform-aware setup/check/doctor dispatch, source-checkout CI coverage, and
  apt-backed setup behind explicit `--dry-run` / `--yes` confirmation
- `basectl docs` for opening the GitHub README documentation entrypoint
- standardized `basectl` help, option, logging, and usage-error behavior
- Python-backed CI setup JSON rendering and Project issue-default handling
- release-publish recovery guidance and release title validation
- optional pinned Homebrew installer support for verified bootstrap sources
- shell and completion performance improvements for project-name and Git prompt
  rendering
- redaction hardening for config display and setup command logs
- normalized Bash source guards and explicit `base-test` error handling
- local command-history index with future report surfaces still deferred
- project Python version requirements for Base-managed virtualenv creation
- workspace manifest status/check/doctor reporting plus explicit init, clone,
  and pull support
- guarded `basectl release publish`
- release check, plan, and notes commands
- local `.ai-context/` export bundles through `basectl export-context`
- newcomer orientation presentation docs
- optional project Git remote reachability diagnostics
- explicit `ai` prerequisite profile
- portable project Git workflow guidance from `basectl repo init`
- Homebrew upgrade path preservation for explicit `BASE_HOME` and shell startup
  snippets
- stale readonly `BASE_HOME` recovery guidance after Homebrew upgrades
- Homebrew Command Line Tools staleness warnings in `basectl check`
- Homebrew `basectl update` handoff and package-aware `basectl test base`
- Base `1.0.1` AGPL license cleanup and release artifacts
- explicit uv-managed Python setup and command runner support
- bundled `lib/base/artifact-registry.yaml` support for built-in artifacts
- workspace-aware repo clone, manifest-driven workspace clone, Project intake
  workflow generation, and resilient `basectl gh` command execution
- external `base-bash-libs` consumption for reusable Bash libraries, with Base
  retaining only Bash runtime and version helpers
- documented `base-bash-libs` Homebrew/core readiness as the future standalone
  dependency for a non-conflicting `basefoundry` core formula
- documented that `basectl setup` should stay serial for mutating installers
  until a deterministic setup-plan/preflight layer exists

## Recent Merged Changes

Recent commits on `main` include:

- public evaluator documentation through `docs/why-base.md`
- AGPL license cleanup and generated-license correction for `basectl repo init`
- Homebrew and source checkout install-path clarification
- uv ecosystem boundary documentation and explicit uv-managed project support
- repo Project metadata handoff and command-specific `basectl repo` help
- shell stdlib dry-run safety fixes from BankBuddy dogfooding
- Homebrew bottle and upgrade-path release process hardening
- external reusable Bash library resolution from `base-bash-libs`
- documented `base-bash-libs` consumption and post-migration contract
- formula-name Homebrew audit guidance for Base and `base-bash-libs`
- setup parallelism evaluation with a conservative setup-plan-first decision

## Useful Orientation Links

- Product front door: `README.md`
- Documentation map: `docs/README.md`
- Architecture: `docs/architecture.md`
- Execution model: `docs/execution-model.md`
- GitHub workflow: `docs/github-workflow.md`
- Testing: `docs/testing.md`
- Release process: `docs/release-process.md`
- Changelog: `CHANGELOG.md`
