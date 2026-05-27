# TODO

Action items from the May 2026 Base product reviews.

Use this as a commit-by-commit work queue. Completed items are removed after
they are merged.

## P0 — Security And Correctness

- [ ] Add warning severity to doctor findings.
  - Problem: doctor findings are currently effectively binary `ok` or `error`.
  - Goal: distinguish optional or non-blocking recommendations from setup
    failures.
  - Expected behavior: support `warn` findings in Base, dev, and project doctor
    output; reserve non-zero exit status for blocking `error` findings.

- [ ] Document or harden the Homebrew installer trust decision.
  - Problem: Base follows Homebrew's official mutable `HEAD` installer pattern,
    which executes downloaded code.
  - Goal: make the trust model explicit and decide whether Base should pin and
    verify the installer.
  - Expected behavior: either pin to a reviewed installer commit with SHA
    verification, or document in code and docs why Base intentionally follows
    Homebrew's official installer command.

## P1 — Product Core And Composability

- [ ] Redesign project manifests around delegation-first orchestration.
  - Goal: reduce the hand-curated artifact registry and make Base easier for
    real projects to adopt.
  - Expected design topics:
    - Keep `brewfile: Brewfile` as the primary path for ordinary Homebrew
      formulae and casks.
    - Add first-class `mise` delegation when a project declares `.mise.toml` or
      `mise.toml`.
    - Consider a structured `python:` section for Base-managed venvs and Python
      package requirements.
    - Define a `test:` contract for future `basectl test <project>`.
    - Decide whether setup hooks belong in the manifest and what guardrails they
      need.
  - Constraint: preserve Base's safety stance; do not silently run arbitrary
    project commands without a clear contract.

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

- [ ] Route project artifact setup/check/doctor through `base-wrapper`.
  - Problem: `setup_run_base_dev_layer` uses `base-wrapper`, but the project
    artifact layer still invokes Python directly with a hand-built `PYTHONPATH`.
  - Goal: make `base-wrapper` the single authoritative Python invocation path.
  - Expected behavior: use `"$BASE_HOME/bin/base-wrapper" --project <project>
    base_setup ...` while preserving manifest resolution and JSON stdout
    cleanliness.

- [ ] Add successful command debug logging in the Python setup engine.
  - Problem: `run_command` logs failures but has no `ctx`, so successful command
    completion is silent beyond the caller's "installing..." message.
  - Goal: make setup logs more useful without noisy terminal output.
  - Expected behavior: pass `ctx` or a logger into command execution helpers and
    log successful commands at DEBUG with `format_command(command)`.

- [ ] Add log rotation or retention policy.
  - Goal: prevent Base CLI logs from growing indefinitely.
  - Expected behavior: keep a fixed number of recent log files per CLI, or add a
    retention mode to `basectl clean` such as `--keep-last 20`.

- [ ] Add a standalone installer script.
  - Goal: make first-time Base adoption easier than manually cloning the repo.
  - Expected behavior: provide an install path such as
    `curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/install.sh | bash`
    that clones or updates Base, runs `basectl setup`, and optionally runs
    `basectl update-profile`.
  - Security note: document the trust implications of `curl | bash` and align
    with the Homebrew installer trust decision.

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

- [ ] Speed up Homebrew Python discovery.
  - Problem: `brew --prefix <formula>` adds noticeable startup cost to setup and
    check runs.
  - Goal: check known Homebrew opt paths before invoking `brew --prefix`.
  - Expected behavior: try `/opt/homebrew/opt/<formula>/bin/python3` and
    `/usr/local/opt/<formula>/bin/python3` first, then fall back to Homebrew.

- [ ] Speed up Xcode Command Line Tools detection.
  - Problem: `xcrun -f clang` can be slow because it validates the active
    toolchain.
  - Goal: replace the slow probe with direct filesystem checks when reliable.
  - Expected behavior: after `xcode-select -p` and the configured tools
    directory exist, check for `usr/bin/clang` under the tools directory.

- [ ] Optimize Bash log caller detection.
  - Problem: `_print_log` walks the caller stack on every log call.
  - Goal: use `BASH_SOURCE` and `BASH_LINENO` fast paths for common direct
    callers and keep the stack walk only as a rare fallback.

- [ ] Reduce repeated subshell calls for setup paths.
  - Problem: helpers such as `setup_venv_dir` and `setup_pythonpath` are often
    called through command substitution even though they build deterministic
    strings.
  - Goal: cache or initialize these values once per command run.

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
