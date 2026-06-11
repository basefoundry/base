# Base Status Context

## Current Release

Base `0.4.1` is the current published release. The repo-root `VERSION` file is
updated only during release-prep PRs, not on every ordinary PR.

## Current Implemented Areas

The current command surface covers:

- setup and first-mile bootstrap
- checks and doctor diagnostics
- project discovery
- project activation
- declared project test, build, run, and demo commands
- mise integration
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

Current pre-1.0 work is tracked toward `v1.0.0`. The `0.4.1` patch release
preserves Homebrew `opt` paths after Base upgrades so shell startup snippets do
not point at cleaned-up versioned `Cellar` paths.

Recent released work includes:

- local observability model for future command history and report surfaces
- read-only workspace manifest support
- guarded `basectl release publish`
- release check, plan, and notes commands
- local `.ai-context/` export bundles through `basectl export-context`
- newcomer orientation presentation docs
- optional project Git remote reachability diagnostics
- explicit `ai` prerequisite profile
- portable project Git workflow guidance from `basectl repo init`
- Homebrew upgrade path preservation for explicit `BASE_HOME` and shell startup
  snippets

## Recent Merged Changes

Recent commits on `master` include:

- Homebrew link conflict guidance.
- `BASE_SHELL` readonly warning fix during activation.
- Architecture GitHub convention updates.
- Base newcomer presentation docs.
- Claude-reported Base issue fixes.
- Local observability model documentation.
- Guarded `basectl release publish`.
- Pretty-printed workspace JSON output.
- Homebrew `opt` path preservation after upgrades.

## Useful Orientation Links

- Product front door: `README.md`
- Documentation map: `docs/README.md`
- Architecture: `docs/architecture.md`
- Execution model: `docs/execution-model.md`
- GitHub workflow: `docs/github-workflow.md`
- Testing: `docs/testing.md`
- Release process: `docs/release-process.md`
- Changelog: `CHANGELOG.md`
