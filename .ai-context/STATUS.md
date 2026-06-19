# Base Status Context

## Current Release

Base `1.0.5` is the current release. The repo-root `VERSION` file is updated
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
- explicit uv-managed Python project setup through `python.manager: uv`
- cleanup and logs
- local config inspection
- onboarding
- repository baseline creation and checks
- GitHub issue, PR, branch, and worktree helpers
- workspace status/check/doctor reports
- release readiness inspection and guarded GitHub release publishing
- local AI context export bundles
- explicit `ai` prerequisite profile for Codex CLI and Claude Code

## Active Development Direction

The `v1.0.0` milestone is complete. Post-1.0 work is tracked toward `v1.1.0`,
with Linux runtime support, Docker/service artifacts, and shell stdlib
hardening remaining outside the 1.0 release contract. uv-managed Python project
behavior is now implemented after 1.0 through the explicit
`python.manager: uv` contract.

The Homebrew bottle and consumer upgrade contract has passed the #526 rehearsal.
Supported macOS installs should continue to use bottled Homebrew packages, with
source builds treated as fallback validation rather than the normal user path.

Recent released work includes:

- local observability model for future command history and report surfaces
- workspace manifest status/check/doctor reporting plus explicit clone and pull
  support
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
- Homebrew `basectl update` handoff and package-aware `basectl test base`
- Base `1.0.1` AGPL license cleanup and release artifacts
- explicit uv-managed Python setup and command runner support
- workspace-aware repo clone, manifest-driven workspace clone, Project intake
  workflow generation, and resilient `basectl gh` command execution
- external `base-bash-libs` consumption for reusable Bash libraries, with Base
  retaining only Bash runtime and version helpers

## Recent Merged Changes

Recent commits on `master` include:

- public evaluator documentation through `docs/why-base.md`
- AGPL license cleanup and generated-license correction for `basectl repo init`
- Homebrew and source checkout install-path clarification
- uv ecosystem boundary documentation and explicit uv-managed project support
- repo Project metadata handoff and command-specific `basectl repo` help
- shell stdlib dry-run safety fixes from BankBuddy dogfooding
- Homebrew bottle and upgrade-path release process hardening
- external reusable Bash library resolution from `base-bash-libs`
- documented `base-bash-libs` consumption and post-migration contract

## Useful Orientation Links

- Product front door: `README.md`
- Documentation map: `docs/README.md`
- Architecture: `docs/architecture.md`
- Execution model: `docs/execution-model.md`
- GitHub workflow: `docs/github-workflow.md`
- Testing: `docs/testing.md`
- Release process: `docs/release-process.md`
- Changelog: `CHANGELOG.md`
