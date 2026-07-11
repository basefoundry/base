# `setup_common.sh` Ownership Reduction

Status: preliminary implementation slice for #1570, refreshed against the
current 2,906-line `setup_common.sh` implementation.

`cli/bash/commands/basectl/subcommands/setup_common.sh` is intentionally shared
by `basectl setup`, `basectl check`, `basectl doctor`, and
`basectl update-profile`. It owns first-mile host bootstrap, Base runtime
readiness, platform dispatch, project-layer dispatch, and check/doctor
orchestration. Its size is now the maintenance problem; the safe response is a
staged ownership split with behavior-preserving PRs, not a line-count driven
rewrite.

This note maps the current responsibilities and records the strategy for
breaking up the file into domain-scoped helpers or Python-owned surfaces.

## Guardrails

- Preserve the top-level setup contract: `basectl check` inspects,
  `basectl setup` applies, `basectl setup --dry-run` previews, and
  `basectl setup --yes` is consent for prompts, not an automatic "fix
  everything" mode.
- Preserve public function names and call sites during shell extraction. Move
  code first; rename only in later, separately reviewed cleanup.
- Keep Bash responsible for host bootstrap, shell process orchestration, prompt
  consent, environment activation, and command dispatch.
- Keep Python responsible for manifest parsing, structured project data,
  artifact decisions, workspace data, and stable JSON serialization.
- Move one ownership boundary per PR. Each PR must be reviewable as a no-op for
  setup/check/doctor/update behavior on macOS and Ubuntu/Debian.
- Add source guards and sourcing-order tests before introducing any new sourced
  shell helper.
- Coordinate Linux/Debian helper movement with #1564 before moving broader
  platform code.

## Current Responsibility Map

Line spans are approximate navigation aids for the current source shape. The
entry-point functions are the stable anchors for future edits.

| Span | Current responsibility | Entry-point anchors | Target owner |
| --- | --- | --- | --- |
| 1-252 | Source guard, shared cached paths, run state, profile flags, dry-run/debug/yes/CI toggles, and Ubuntu/Debian consent prompts. | `setup_refresh_cached_paths()`, `setup_enable_profile_argument()`, `setup_require_linux_debian_system_consent()` | Keep in shared shell orchestration until profile parsing can move independently. |
| 260-435 | Base virtualenv health checks, pyvenv inspection, architecture compatibility, backup path handling, and package/config defaults. | `setup_virtualenv_healthy_path()`, `setup_backup_existing_venv_path()`, `setup_python_formula()` | Candidate `setup_venv.sh` only after platform Python finders and project-venv fallback dependencies are separated. |
| 436-636 | Platform/host-env detection helpers, test-hook gates, recovery text, and GitHub CLI Debian/Ubuntu install guidance constants. | `setup_current_platform()`, `setup_current_host_env()`, `setup_recovery_linux_github_cli()` | Split platform policy only with #1564 or a later platform-boundary issue. |
| 636-676 | macOS completion notification behavior. | `setup_notify_completion()` | Candidate `setup_notifications.sh`; low risk but low value unless used as a source-guard pilot. |
| 678-1027 | Homebrew discovery, Rosetta/runtime summary, pinned installer policy, Homebrew install, and macOS command-line-tool prerequisites. | `setup_find_brew_bin()`, `setup_print_runtime_chain_summary()`, `setup_install_homebrew()`, `setup_install_xcode_tools()` | Candidate `setup_homebrew.sh` or `setup_macos.sh` after Linux/Debian boundary decisions settle the helper pattern. |
| 1031-1319 | macOS/Linux Python discovery, Linux runtime predicates, Base virtualenv creation, and Base bootstrap package install. | `setup_find_platform_python_bin()`, `setup_create_virtualenv()`, `setup_install_base_python_package()` | Candidate `setup_venv.sh`; keep the platform Python finder seam explicit. |
| 1320-1513 | Base check finding metadata, base-bash-libs status, PYTHONPATH, and the diagnostics JSON bridge. | `setup_base_check_finding_id()`, `setup_diagnostics_python_bin()`, `setup_run_diagnostics_json()` | Finding metadata should eventually move to Python; the diagnostics bridge remains shared shell until check JSON assembly moves. |
| 1523-1671 | Project manifest resolution, project route dispatch, check-result recording, user config seeding, and legacy project-venv fallback helpers. | `setup_resolve_project_manifest()`, `setup_resolve_project_route()`, `setup_record_project_check_result()` | Continue moving structured route policy to Python; keep shell dispatch thin. |
| 1677-1779 | Doctor visual status and project virtualenv JSON snippets for pre-venv failure handling. | `setup_print_doctor_finding()`, `setup_print_project_venv_check_json()`, `setup_print_project_venv_doctor_json()` | Move structured JSON assembly to Python before considering command-local doctor formatting. |
| 1779-2067 | Project pre-venv, bootstrap, artifact setup/check/doctor, uv-manager, wrapper, and remote-network dispatch. | `setup_run_project_pre_venv_layer()`, `setup_run_project_bootstrap_layer()`, `setup_run_project_artifact_layer()` | Keep as shell dispatch; reduce by moving project policy and payload shape to Python. |
| 2075-2099 | `base_dev` prerequisite profile dispatch. | `setup_run_base_dev_layer()` | Candidate `setup_profiles.sh` once profile parsing, profile JSON keys, and profile dispatch can move together. |
| 2102-2479 | macOS parallel host probes, Linux check-result collectors, platform-specific check dispatch, and CI runtime check collectors. | `setup_collect_macos_base_check_results()`, `setup_collect_linux_debian_base_check_results()`, `setup_collect_platform_base_check_results()` | Linux collector belongs with #1564; macOS probes can later move with Homebrew/macOS helpers. |
| 2488-2699 | Base check text rendering, project check result status handling, top-level check orchestration, and check JSON argument assembly. | `setup_run_check()`, `setup_run_check_json()`, `setup_print_check_text_results()` | Move check JSON assembly to Python; keep human text rendering and exit orchestration in shell. |
| 2704-2906 | CI install, macOS install, Ubuntu/Debian apt prerequisites, GitHub CLI apt repository setup, platform install dispatch, and top-level setup dispatch. | `setup_run_ci_runtime_install()`, `setup_run_macos_install()`, `setup_run_linux_debian_install()`, `setup_run_install()` | Split Linux install with #1564 first, then consider macOS install and shared venv helpers. |

## Decomposition Strategy

The split should proceed in phases that reduce ownership, preserve behavior, and
avoid circular shell dependencies.

### Phase 0: Ownership Map And Guard

This issue slice refreshes the map and adds a documentation guard. It does not
move runtime code. That keeps the first PR review focused on whether the
planned boundaries are coherent.

### Phase 1: Linux/Debian Platform Boundary

Use #1564 as the input for the first sourced-shell extraction. The likely helper
is `setup_linux_debian.sh` or `setup_apt.sh`, but the name should follow the
actual ownership being moved.

The first Linux slice should include:

- apt package list and dry-run command helpers:
  `setup_linux_debian_apt_packages()`,
  `setup_linux_debian_apt_update_command()`, and
  `setup_linux_debian_apt_prerequisite_command()`;
- apt package presence and install flow:
  `setup_linux_debian_apt_prerequisites_installed()` and
  `setup_run_linux_debian_apt_prerequisites()`;
- GitHub CLI repository setup helpers:
  `setup_linux_debian_github_cli_source_line()` and
  `setup_run_linux_debian_github_cli_prerequisite()`;
- Linux check collectors only if the PR can keep the review small:
  `setup_collect_linux_debian_base_check_results()`.

This is important because Linux support is now product-visible, and keeping
Ubuntu/Debian policy buried inside the cross-platform common file increases the
risk of macOS-specific edits breaking Linux behavior.

### Phase 2: Homebrew And macOS Host Bootstrap

After the Linux helper pattern is proven, move the Homebrew/Xcode surface to a
macOS-specific helper such as `setup_homebrew.sh` or `setup_macos.sh`.

Candidate functions include `setup_find_brew_bin()`,
`setup_homebrew_installer_url()`, `setup_install_homebrew()`,
`setup_xcode_tools_installed()`, and `setup_install_xcode_tools()`.

This matters because the Homebrew installer policy, Rosetta diagnostics, and
Xcode behavior change at a different cadence from Ubuntu/Debian setup. A
macOS-specific helper lets platform reviewers reason about one host family at a
time.

### Phase 3: Base Runtime Virtualenv And Python Bootstrap

Move the Base virtualenv and Python bootstrap surface only after platform Python
finder boundaries are explicit. The candidate helper is `setup_venv.sh`.

Candidate functions include `setup_virtualenv_healthy_path()`,
`setup_find_platform_python_bin()`, `setup_create_virtualenv()`,
`setup_base_venv_python_bin()`, and `setup_install_base_python_package()`.

This matters because setup, check, CI runtime, and project dispatch all depend
on Base runtime health. Extracting this too early would create hidden coupling;
doing it after platform helpers are stable gives the venv helper a clean API.

### Phase 4: Profile Dispatch And Notifications

Move smaller orchestration surfaces only after the platform and venv layers have
settled.

Candidate helpers:

- `setup_profiles.sh` for profile parsing and `setup_run_base_dev_layer()`;
- `setup_notifications.sh` for `setup_notify_completion()`.

These are cleanup slices, not product enablers. They are useful only when they
reduce the common file without creating extra source-order complexity.

### Phase 5: Python-Owned Payloads

Do not move structured payload work into new shell helpers. Move it into Python
instead.

Candidates for Python ownership:

- check JSON assembly currently coordinated by `setup_run_check_json()`;
- project virtualenv JSON snippets currently emitted through
  `setup_print_project_venv_check_json()` and
  `setup_print_project_venv_doctor_json()`;
- base finding metadata currently in `setup_base_check_finding_id()` and
  `setup_base_check_display_name()`.

This matters because JSON schema stability is easier to test and preserve in
Python than in shell argument assembly.

## Source-Guard Protocol

Each sourced helper PR should follow this protocol:

1. Add the helper under `cli/bash/commands/basectl/subcommands/` with a private
   guard variable such as `_base_setup_linux_debian_sourced`.
2. Source it from `setup_common.sh` in dependency order, near the existing
   `setup_check_results.sh` source.
3. Preserve existing public `setup_*` function names.
4. Keep helper dependencies explicit. A helper may call functions sourced before
   it; it must not rely on functions sourced later.
5. Add BATS coverage that sources `setup_common.sh` twice, verifies moved
   functions are declared, and exercises at least one behavior path from the
   moved domain.
6. Run syntax checks for `setup_common.sh` and every new helper.
7. Update this map in the same PR so the ownership document remains current.

## Non-Goals

- Do not split by line count alone.
- Do not rewrite setup orchestration in Python.
- Do not change user-visible setup/check/doctor text, JSON shape, dry-run
  behavior, prompt consent behavior, or platform support in extraction PRs.
- Do not remove `setup_common.sh` as the shared command surface until each
  command has a proven replacement boundary.

## Recommended PR Sequence

1. Finish this preliminary #1570 slice: refreshed map, strategy, and doc guard.
2. Resolve or explicitly scope #1564, then move the first Linux/Debian helper
   boundary.
3. Move macOS/Homebrew bootstrap helpers using the same source-guard pattern.
4. Move Base runtime virtualenv/Python bootstrap helpers after both platform
   helpers are stable.
5. Move profile and notification helpers if they still reduce ownership.
6. Move structured check/doctor JSON assembly into Python-owned code, not into
   another shell helper.
