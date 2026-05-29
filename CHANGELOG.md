# Changelog

All notable changes to Base will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Base versions are tracked in the repo-root `VERSION` file.

## [Unreleased]

### Added

- Added this changelog so adopting teams can see what changed between Base
  versions.

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
