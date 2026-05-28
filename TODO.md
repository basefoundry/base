# TODO

Action items from the May 2026 Base product reviews.

Use this as a commit-by-commit work queue. Completed items are removed after
they are merged.

## P0 — Security And Correctness

## P1 — Product Core And Composability

- [ ] Add first-class `mise` integration.
  - Goal: let Base orchestrate project tool versions and tasks without becoming
    a version manager.
  - Expected behavior: `basectl setup <project>` can run `mise install` when a
    project opts in, and future `basectl test <project>` can delegate to
    `mise run test` when declared.

- [ ] Implement `basectl test [project]`.
  - Goal: make Base the umbrella entry point for project test execution.
  - Expected behavior: delegate to the project's declared test command, `mise`
    task, or conventional runner while preserving Base logging and exit status.

- [ ] Consider a structured `python:` manifest section.
  - Goal: make Base-managed Python environments clearer than encoding every
    package as an artifact entry.
  - Expected design topics: default project venv location, optional venv path
    override, package requirement syntax, relationship to `requirements.txt`,
    and migration from existing `python-package` artifacts.

- [ ] Decide whether setup hooks belong in the manifest.
  - Goal: preserve Base's safety stance while allowing real projects to perform
    necessary post-setup work when delegation targets are not enough.
  - Expected behavior: either define a constrained hook contract with explicit
    timing, dry-run, interactivity, and diagnostics semantics, or document why
    project-owned installers remain the right layer for hooks.

- [ ] Implement `basectl onboard`.
  - Goal: provide the guided checklist-style Base setup experience described in
    `docs/basectl-onboard.md`.
  - Expected behavior: orchestrate existing setup, check, doctor, profile, and
    project-discovery primitives without duplicating their logic.
  - Starting point: implement the v1 Bash subcommand with dry-run, prompted,
    `--yes`, `--dev`, and `--no-profile` flows.

- [ ] Decide whether `basectl onboard <project>` belongs in Base or project installers.
  - Goal: revisit the Round 5 recommendation for project-oriented onboarding
    against Base's current boundary that project installers own
    product-specific onboarding.
  - Expected behavior: either extend the onboard design for project targets or
    explicitly document why `<project>/install.sh` remains the preferred layer.

- [ ] Implement future `docker-service` artifact support when a real project needs it.
  - Goal: let Base orchestrate Docker Compose services without replacing Docker,
    Docker Compose, or project-owned Compose files.
  - Starting point: `docs/tool-boundaries.md` has the intended boundary and a
    possible future manifest shape.
  - Manifest design:
    - Add a `docker-service` artifact type only after field names are finalized
      against a real project.
    - Require `compose-file` paths to be relative to the project root and to
      stay inside that root.
    - Start with one named `service` per artifact; add service groups later only
      if needed.
    - Decide whether `version` should be accepted for schema consistency or
      omitted for this artifact type.
  - Setup behavior:
    - Validate Docker CLI availability and daemon reachability.
    - Run `docker compose -f <file> pull <service>` when enabled.
    - Run `docker compose -f <file> build <service>` when enabled.
    - Keep setup idempotent and avoid starting long-lived services during setup.
  - Check/doctor behavior:
    - Report missing Docker, missing daemon, missing Compose file, and missing
      service definitions as actionable findings.
    - Give Colima-specific recovery guidance such as `colima start` when useful.
    - Surface image/service status without hiding the underlying Docker command.
  - Activate behavior:
    - Optionally start opted-in services during `basectl activate <project>`.
    - Keep startup visible in logs and make health-check failures easy to
      understand.
  - Tests:
    - Cover manifest validation, dry-run command planning, daemon-check
      failures, Compose command failures, and activate-time startup behavior.

## P2 — Operational Excellence

- [ ] Package Base as a Homebrew formula or tap.
  - Goal: make Base installation feel native on macOS.
  - Expected behavior: support an install path such as
    `brew install codeforester/base/basectl`.

- [ ] Add initial Linux support plan.
  - Goal: define the first supported Linux target, likely Ubuntu/Debian.
  - Expected design topics: `/etc/os-release` detection, `apt` equivalents for
    Homebrew-managed bootstrap dependencies, shell startup differences, and CI
    implications.

- [ ] Design `basectl ci`.
  - Goal: make Base useful in non-interactive CI environments once Linux support
    exists.
  - Expected behavior: skip UI-only setup paths, avoid interactive prompts, and
    emit structured output suitable for automation.

- [ ] Add a real Base-managed project demonstration.
  - Goal: use a project such as Banyanlabs to prove the complete workflow:
    workspace discovery, `basectl setup <project>`, `basectl check <project>`,
    `basectl doctor <project>`, `basectl activate <project>`, and future
    `basectl test <project>`.

## P3 — Performance And CI Hardening

- [ ] Evaluate parallelizing independent `basectl check` probes.
  - Goal: reduce check wall time by running independent probes concurrently.
  - Expected behavior: preserve deterministic output order while collecting
    Homebrew, Xcode, Python, venv, and package results in parallel.

- [ ] Harden GitHub Actions Python file discovery.
  - Problem: the pylint workflow uses unquoted command substitution with
    `git ls-files '*.py'`.
  - Goal: avoid word splitting issues in CI.
  - Expected behavior: use a null-delimited or `xargs`-based invocation.

- [ ] Pin CI development dependencies and add security scanners.
  - Goal: make CI more reproducible and catch security issues earlier.
  - Expected behavior: add a pinned dev requirements flow for CI and evaluate
    adding Bandit for Python plus ShellCheck for Bash.
