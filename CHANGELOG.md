# Changelog

All notable changes to Base will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Base versions are tracked in the repo-root `VERSION` file.

## [Unreleased]

### Added

- Added `basectl repo init/check/configure` to create, validate, and configure
  a standard Base-managed repository baseline.

### Fixed

- Updated the README status section to match the current `0.2.0` release.
- Fixed `basectl repo init` to create new repositories under the configured
  workspace root instead of the caller's current directory.

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
