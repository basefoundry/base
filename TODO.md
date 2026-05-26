# TODO

Action items from the May 2026 Base product review.

Use this as a commit-by-commit work queue. Completed items are removed after
they are merged.

## P0 — Core Workspace Loop

- [ ] Implement `basectl activate <project>`.
  - Goal: make Base a daily workspace tool, not only a setup tool.
  - Expected behavior: discover the project, set `BASE_PROJECT` and project-root environment, activate `~/.base.d/<project>/.venv`, layer project shell behavior, and spawn a subshell that cleans up when it exits.
  - Notes: the activation model is already described in `docs/design.md`; implementation should follow that design before expanding scope.

- [ ] Implement `basectl projects list`.
  - Goal: make workspace discovery visible and inspectable.
  - Expected behavior: scan the workspace for repos with `base_manifest.yaml`, parse project names, and print a stable list of discovered projects.
  - Follow-up: later use the same discovery layer for completions, activation, setup, and project commands.

- [ ] Split runtime artifacts out of `~/.base.d`.
  - Files: `lib/python/base_cli/paths.py`, `lib/python/base_cli/app.py`, tests.
  - Problem: `~/.base.d` currently mixes durable config and project venvs with ephemeral CLI logs, temp files, and caches.
  - Expected behavior: keep durable state under `~/.base.d`, but move CLI runtime artifacts under a cache root such as `${BASE_CACHE_DIR:-~/.cache/base}`.
  - Notes: macOS `~/Library/Caches/base` is a later option; start with an overrideable default that is simple and testable.

- [ ] Add log cleanup with `basectl clean`.
  - Goal: prevent Base logs and retained temp/cache files from growing indefinitely.
  - Expected behavior: support at least `basectl clean --older-than 30d`, with dry-run output and clear scope.
  - Dependency: easiest after the runtime artifact cache root is split from `~/.base.d`.

## P1 — High-Value Product Capabilities

- [ ] Implement `basectl doctor`.
  - Goal: provide deeper diagnosis than `basectl check`.
  - Expected behavior: report findings as `ok`, `warn`, or `error`, and include suggested fix commands or next steps for each issue.
  - Notes: keep `basectl check` automation-friendly; make `doctor` human-oriented.

- [ ] Add Docker and Colima to the artifact registry.
  - File: `cli/python/base_setup/registry.py`
  - Expected behavior: support `type: tool`, `name: docker`, `version: latest` and `type: tool`, `name: colima`, `version: latest` through Homebrew.
  - Notes: do not build a docker-service reconciler in this task.

- [ ] Design future `docker-service` artifacts.
  - File: `docs/tool-boundaries.md`
  - Goal: document how Base should eventually orchestrate Docker Compose without replacing Docker.
  - Expected design topics: compose file path, `docker compose pull/build`, daemon checks, image existence checks, activation-time service startup, health checks, and Colima vs Docker Desktop tradeoffs.

- [ ] Add Brewfile integration for project setup.
  - Goal: support arbitrary Homebrew project dependencies without hand-curating every package in the Base registry.
  - Expected behavior: allow a project manifest to reference a `Brewfile` and have setup run `brew bundle --file=<path>`.
  - Notes: this should complement the registry, not replace Base-specific known artifacts.

- [ ] Add shell completions for `basectl`.
  - Goal: improve daily ergonomics for commands and project names.
  - Expected behavior: complete subcommands and, once project discovery exists, complete project names for commands such as `activate`.
  - Notes: wire completion setup through `basectl update-profile` if practical.

- [ ] Implement `basectl update`.
  - Goal: provide a simple self-update path until Base has a Homebrew formula.
  - Expected behavior: update the Base repo safely, then run `basectl setup`.
  - Notes: build on the existing Git update helpers and keep dirty-worktree handling explicit.

## P2 — Adoption And Expansion

- [ ] Improve setup recovery messages for technically-adjacent users.
  - Goal: keep `basectl setup` developer-oriented while making failures easier to recover from.
  - Expected behavior: plain-English errors with concrete commands or next steps for missing Homebrew, Xcode tools, Python, venv, and Python package issues.

- [ ] Design `basectl onboard`.
  - Goal: provide a guided checklist-style setup experience without making `basectl setup` itself interactive-heavy.
  - Expected behavior: explain each prerequisite, confirm before performing major steps, and call existing setup/check primitives internally.

- [ ] Define project-level installer guidance.
  - Goal: document that true end-user onboarding belongs in project-specific installers, not in `basectl` itself.
  - Expected output: guidance for scripts such as `banyanlabs/install.sh` that bootstrap Base and then call `basectl setup`.

- [ ] Add macOS notification on long setup completion.
  - Goal: make long-running setup friendlier.
  - Expected behavior: optionally display a macOS notification when `basectl setup` completes or fails.
  - Notes: keep this best-effort and non-fatal.

- [ ] Package Base as a Homebrew formula or tap.
  - Goal: make Base installation feel native on macOS.
  - Expected behavior: support an install path such as `brew install codeforester/base/basectl`.

- [ ] Add initial Linux support plan.
  - Goal: define the first supported Linux target, likely Ubuntu/Debian.
  - Expected design topics: `/etc/os-release` detection, `apt` equivalents for Homebrew-managed bootstrap dependencies, shell startup differences, and CI implications.
