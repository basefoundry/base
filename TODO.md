# TODO

Action items from the May 2026 Base product reviews.

Use this as a commit-by-commit work queue. Completed items are removed after
they are merged.

## P0 — Security And Correctness

- [ ] Restrict setup test-only environment escape hatches.
  - Problem: `BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT` and `BASE_SETUP_PYTHON_BIN`
    can redirect setup to arbitrary executables when present in the environment.
  - Goal: keep test hooks available without honoring them in normal user runs.
  - Expected behavior: require an explicit test/CI guard such as
    `BASE_TEST_MODE=true` before these overrides are accepted; otherwise ignore
    or fail with a clear error.

- [ ] Remove implicit system `python3` fallback from Base venv creation.
  - Problem: `setup_find_python_bin` can fall back to the first `python3` on
    `PATH` if Homebrew Python cannot be resolved, potentially creating Base's
    venv with the wrong interpreter.
  - Goal: use the configured Homebrew Python formula unless the user explicitly
    opts into a system Python fallback.
  - Expected behavior: remove the fallback or gate it behind a clearly named
    opt-in such as `BASE_SETUP_ALLOW_SYSTEM_PYTHON=true`.

- [ ] Clear inherited setup state in `basectl check`.
  - Problem: `basectl setup` calls `setup_clear_run_state`, but `basectl check`
    does not, so inherited variables such as `DRY_RUN` or
    `BASE_SETUP_RECREATE_VENV` can affect check behavior.
  - Goal: make `check` deterministic and insulated from ambient setup state.
  - Expected behavior: call `setup_clear_run_state` at the start of
    `base_check_subcommand_main`, then preserve only flags explicitly passed to
    `check`.

- [ ] Support non-`master` default branches in `basectl update`.
  - Problem: `basectl update` currently refuses to run unless the checked-out
    branch is exactly `master`, which blocks repositories whose default branch
    is `main` or another remote default.
  - Goal: make self-update work with modern GitHub default branch conventions.
  - Expected behavior: accept both `master` and `main`, or discover the remote
    default branch from `origin/HEAD` and use that consistently.

- [ ] Make Bash JSON escaping strict for all control characters.
  - Problem: `setup_json_escape` handles `"`, `\`, newline, carriage return, and
    tab, but not the rest of U+0000 through U+001F.
  - Goal: ensure `basectl check --format json` always emits structurally valid
    JSON.
  - Expected behavior: either use a trusted JSON encoder when available or add a
    complete control-character escape path with regression tests.

- [ ] Put `base_virtualenv` before Python packages in check JSON.
  - Problem: JSON output currently reports PyYAML and click before the venv even
    though the venv is their prerequisite.
  - Goal: make JSON check ordering communicate dependency order.
  - Expected behavior: emit Homebrew, Xcode, Python, Base virtualenv, PyYAML,
    click, then optional dev/project checks.

- [ ] Add JSON output to `basectl doctor`.
  - Problem: `basectl check` supports `--format text|json`, but
    `basectl doctor` is text-only even though project artifact checks already
    have structured data internally.
  - Goal: make doctor usable in automation, CI health checks, and dashboards.
  - Expected behavior: support `basectl doctor --format json` and
    `basectl doctor <project> --format json` with stable `ok`, `warn`, and
    `error` finding objects.

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
