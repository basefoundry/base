# Base Status Context

## Current Release

Base `0.3.0` is the current published release. The repo-root `VERSION` file is
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
- explicit `ai` prerequisite profile for Codex CLI and Claude Code

## Active Development Direction

The `v0.4.0` milestone is focused on CI and Linux foundation work while also
hardening the release, workflow, workspace, and AI-assisted development
surfaces needed before `1.0.0`.

Recent unreleased work includes:

- local observability model for future command history and report surfaces
- read-only workspace manifest support
- guarded `basectl release publish`
- release check, plan, and notes commands
- newcomer orientation presentation docs
- optional project Git remote reachability diagnostics
- explicit `ai` prerequisite profile
- portable project Git workflow guidance from `basectl repo init`

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

## Useful Orientation Links

- Product front door: `README.md`
- Documentation map: `docs/README.md`
- Architecture: `docs/architecture.md`
- Execution model: `docs/execution-model.md`
- GitHub workflow: `docs/github-workflow.md`
- Testing: `docs/testing.md`
- Release process: `docs/release-process.md`
- Changelog: `CHANGELOG.md`
