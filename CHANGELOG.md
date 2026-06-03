# Changelog

All notable changes to Base will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Base versions are tracked in the repo-root `VERSION` file.

## [Unreleased]

### Added

- Added the workspace manifest design document to define the future team-shared
  repo-set contract and its relationship to discovered local projects.
- Added `basectl workspace check` and `basectl workspace doctor` for read-only
  project diagnostics across discovered workspace projects.
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

### Changed

- Changed `basectl demo` to infer the current project from the nearest
  `base_manifest.yaml` when the project argument is omitted.
- Changed `basectl repo init --repo` to create private GitHub repositories by
  default, with explicit `--public` and `--private` visibility flags.
- Updated Base-managed shell profile sections to use shorter `>>> base: ...`
  markers, clearer overwrite guidance, and quoted source paths.

### Fixed

- Updated the README status section to match the current `0.2.0` release.
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
