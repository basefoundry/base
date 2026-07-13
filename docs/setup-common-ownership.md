# `setup_common.sh` Ownership Reduction

Status: #1570 close-out map. The first platform helpers,
`setup_linux_debian.sh` and `setup_macos_homebrew.sh`, the Base runtime helper
`setup_venv.sh`, and the profile helper `setup_profiles.sh` have been
extracted from the shared 2,906-line baseline; `setup_common.sh` is now the
shared orchestrator plus the few domains that still need a broader ownership
boundary before they should move.

`cli/bash/commands/basectl/subcommands/setup_common.sh` is intentionally shared
by `basectl setup`, `basectl check`, `basectl doctor`, and
`basectl update-profile`. It owns first-mile host bootstrap, Base runtime
readiness, platform dispatch, project-layer dispatch, and check/doctor
orchestration. The maintenance risk was mixed ownership, not raw file length;
the safe response was a staged ownership split with behavior-preserving PRs,
not a line-count driven rewrite.

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
- Move one ownership boundary per PR. Split only when the moved code owns a
  cohesive functional domain with a stable source boundary; do not split merely
  because a file has crossed a line-count threshold.
- Each PR must be reviewable as a no-op for setup/check/doctor/update behavior
  on macOS and Ubuntu/Debian.
- Add source guards and sourcing-order tests before introducing any new sourced
  shell helper.
- Coordinate Linux/Debian helper movement with #1564 before moving broader
  platform code.

## Current Responsibility Map

Line spans are approximate navigation aids for the current source shape. The
entry-point functions are the stable anchors for future edits.

| File / span | Current responsibility | Entry-point anchors | Target owner |
| --- | --- | --- | --- |
| `setup_common.sh` 1-179 | Source guard, helper sourcing, shared cached paths, run state, dry-run/debug/yes/CI toggles, Ubuntu/Debian consent prompts, notification toggles, and CI mode detection. | `setup_refresh_cached_paths()`, `setup_clear_run_state()`, `setup_require_linux_debian_system_consent()` | Keep in shared shell orchestration. |
| `setup_common.sh` 183-268 | Platform/host-env helpers, platform support messages, test-hook gates, and shared non-runtime recovery text. | `setup_current_platform()`, `setup_current_host_env()`, `setup_reject_test_hook_if_disallowed()` | Keep platform policy shared while OS-specific implementation remains in platform helpers. |
| `setup_common.sh` 272-310 | Completion notification behavior. | `setup_notify_completion()` | Keep in shared shell for now. Revisit `setup_notifications.sh` when notification policy grows beyond the current macOS-only surface into a cross-platform domain. |
| `setup_common.sh` 314-410 | Shared command-path probes, executable architecture, Rosetta state, GitHub CLI version display, and runtime-chain summary rendering. | `setup_command_path()`, `setup_rosetta_translation_state()`, `setup_print_runtime_chain_summary()` | Keep shared because the summary combines platform helper data with cross-platform runtime state. |
| `setup_common.sh` 414-632 | Base Bash library status, PYTHONPATH, diagnostics JSON bridge, and first-mile text fallback for Base check metadata. | `setup_base_check_metadata()`, `setup_diagnostics_python_bin()`, `setup_run_diagnostics_json()` | Base check metadata and structured diagnostics JSON are Python-primary; keep shell fallback only for pre-runtime text diagnostics. |
| `setup_common.sh` 636-784 | Project manifest resolution, project route dispatch, check-result recording, user config seeding, and legacy project-venv fallback helpers. | `setup_resolve_project_manifest()`, `setup_resolve_project_route()`, `setup_record_project_check_result()` | Continue moving structured route policy to Python; keep shell dispatch thin. |
| `setup_common.sh` 790-879 | Doctor visual status and project virtualenv JSON routing for pre-venv failure handling. | `setup_print_doctor_finding()`, `setup_print_project_venv_check_json()`, `setup_print_project_venv_doctor_json()` | Shell owns human doctor text and routes project virtualenv JSON to Python diagnostics. |
| `setup_common.sh` 892-1179 | Project pre-venv, bootstrap, artifact setup/check/doctor, uv-manager, wrapper, and remote-network dispatch. | `setup_run_project_pre_venv_layer()`, `setup_run_project_bootstrap_layer()`, `setup_run_project_artifact_layer()` | Keep as shell dispatch; reduce by moving project policy and payload shape to Python. |
| `setup_common.sh` 1188-1267 | Shared probe waiting plus platform/base check dispatch. | `setup_wait_for_base_check_probes()`, `setup_collect_platform_base_check_results()`, `setup_collect_base_check_results()` | Keep dispatch shared until check JSON assembly and probe orchestration have clearer Python boundaries. |
| `setup_common.sh` 1276-1389 | Base check text rendering, project check result status handling, top-level check orchestration, and raw check-result record routing for JSON. | `setup_run_check()`, `setup_run_check_json()`, `setup_print_check_text_results()` | Python owns JSON item assembly from raw shell result records; keep human text rendering and exit orchestration in shell. |
| `setup_common.sh` 1392-1416 | Platform install dispatch and top-level setup dispatch. | `setup_run_platform_install()`, `setup_run_install()` | Keep shared dispatch in `setup_common.sh`; install bodies belong in domain helpers. |
| `setup_linux_debian.sh` 1-422 | Ubuntu/Debian recovery text, Python finder, runtime tool probes, check collector, apt prerequisites, GitHub CLI apt-repo setup, and Linux install body. | `setup_find_linux_python_bin()`, `setup_collect_linux_debian_base_check_results()`, `setup_run_linux_debian_install()` | Extracted OS/platform helper; keep future Ubuntu/Debian policy here unless it is structured data better owned by Python. |
| `setup_macos_homebrew.sh` 1-601 | macOS/Homebrew recovery text, Homebrew discovery and installer policy, Xcode command-line tools, macOS Python finder, macOS host probes, and macOS install body. | `setup_find_brew_bin()`, `setup_install_homebrew()`, `setup_collect_macos_base_check_results()`, `setup_run_macos_install()` | Extracted OS/platform helper; keep future macOS/Homebrew policy here unless it is structured data better owned by Python. |
| `setup_venv.sh` 1-444 | Base runtime virtualenv health, pyvenv inspection, recreate behavior, platform Python dispatch, Base bootstrap package checks/install, venv check probes, CI-runtime checks, and CI-runtime install body. | `setup_virtualenv_healthy_path()`, `setup_create_virtualenv()`, `setup_collect_ci_runtime_check_results()`, `setup_run_ci_runtime_install()` | Extracted Base runtime helper; keep future runtime bootstrap policy here unless structured check output moves to Python. |
| `setup_profiles.sh` 1-137 | Setup/check profile parsing, profile state, profile JSON key naming, profile CSV rendering, and `base_dev` prerequisite profile dispatch. | `setup_enable_profile_argument()`, `setup_profiles_csv()`, `setup_run_base_dev_layer()` | Extracted profile helper; keep future profile parsing and dispatch policy here unless profile state moves to Python. |

## Decomposition Strategy

The split should proceed in phases that reduce ownership, preserve behavior, and
avoid circular shell dependencies.

### Phase 0: Ownership Map And Guard

This issue slice refreshes the map and adds a documentation guard. It does not
move runtime code. That keeps the first PR review focused on whether the
planned boundaries are coherent.

### Phase 1: Linux/Debian Platform Boundary

Implemented first as `setup_linux_debian.sh`, using the OS/platform name so the
helper's scope is explicit.

The Linux/Debian helper owns:

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

Implemented second as `setup_macos_homebrew.sh`, after the Linux helper pattern
was proven.

The macOS/Homebrew helper owns:

- Homebrew discovery and prefix recovery:
  `setup_find_brew_bin()`, `setup_homebrew_prefix()`, and
  `setup_refresh_brew_path()`;
- pinned and mutable Homebrew installer policy:
  `setup_homebrew_installer_url()`, `setup_homebrew_installer_sha256()`, and
  `setup_install_homebrew()`;
- Xcode command-line-tool checks and installation:
  `setup_xcode_tools_installed()` and `setup_install_xcode_tools()`;
- macOS Python discovery and installation:
  `setup_find_python_bin()` and `setup_install_python()`;
- macOS check collectors and install body:
  `setup_collect_macos_base_check_results()` and
  `setup_run_macos_install()`.

This matters because the Homebrew installer policy, Rosetta diagnostics, and
Xcode behavior change at a different cadence from Ubuntu/Debian setup. A
macOS-specific helper lets platform reviewers reason about one host family at a
time.

### Phase 3: Base Runtime Virtualenv And Python Bootstrap

Implemented third as `setup_venv.sh`, after the Linux/Debian and macOS/Homebrew
Python finder boundaries were explicit.

The Base runtime helper owns:

- virtualenv recreate and health policy:
  `setup_recreate_venv_enabled()`, `setup_virtualenv_healthy_path()`, and
  `setup_backup_existing_venv_path()`;
- platform Python dispatch for runtime creation:
  `setup_find_platform_python_bin()` and
  `setup_recovery_platform_python()`;
- Base bootstrap package checks and installs:
  `setup_base_python_package_installed()`,
  `setup_install_base_python_package()`, `setup_install_pyyaml()`, and
  `setup_install_click()`;
- venv and package probe writers:
  `setup_write_virtualenv_check_probe()` and
  `setup_write_python_package_check_probe()`;
- CI-runtime setup and check body:
  `setup_collect_ci_runtime_check_results()` and
  `setup_run_ci_runtime_install()`.

This matters because setup, check, CI runtime, and project dispatch all depend
on Base runtime health. Extracting this too early would create hidden coupling;
doing it after platform helpers are stable gives the venv helper a clean API.

### Phase 4: Profile Dispatch And Notifications

Move smaller orchestration surfaces only when they have a clear functional
boundary after the platform and venv layers have settled.

Implemented profile dispatch fourth as `setup_profiles.sh`.

The profile helper owns:

- supported profile names and display text:
  `setup_supported_profiles()` and `setup_supported_profiles_display()`;
- profile normalization and enablement:
  `setup_normalize_profile_name()`, `setup_enable_profile_argument()`, and
  `setup_profiles_enabled()`;
- profile payload keys and CSV rendering:
  `setup_profile_json_key()` and `setup_profiles_csv()`;
- `base_dev` prerequisite profile dispatch:
  `setup_run_base_dev_layer()`.

Deferred candidate:

- `setup_notifications.sh` for `setup_notify_completion()`.

The notification helper is intentionally deferred. Today it is a small
macOS-focused completion path, so extracting it would mostly reduce line count.
As Base adds more Linux flavors and eventually Windows support, notification
behavior may become a real cross-platform policy domain with platform-specific
implementations. That is the right time to extract it.

### Phase 5: Python-Owned Payloads

Do not move structured payload work into new shell helpers. Move it into Python
instead.

Implemented under #1591. The stable boundary is:

- check and doctor JSON assembly reads raw shell check-result records in
  Python;
- project virtualenv JSON is assembled by Python diagnostics, with shell
  wrappers routing pre-runtime failure details to that surface;
- base finding metadata is exposed to shell through the
  `setup_base_check_metadata()` bridge, with a pre-runtime text fallback.

This matters because JSON schema stability is easier to test and preserve in
Python than in shell argument assembly. The remaining shell ownership is
orchestration, fallback routing, and human text rendering, not schema
construction.

## Source-Guard Protocol

Each sourced helper PR should follow this protocol:

1. Add the helper under `cli/bash/commands/basectl/subcommands/` with a private
   guard variable such as `_base_setup_linux_debian_sourced`.
2. Source it from `setup_common.sh` in dependency order, near the existing
   `setup_check_results.sh` source.
3. Preserve existing public `setup_*` function names.
4. Keep helper dependencies explicit. A helper must not execute code at source
   time that depends on functions defined later; runtime calls may continue to
   use shared `setup_common.sh` orchestration helpers until those helpers move.
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

## Close-Out Decisions

1. Treat the Linux/Debian, macOS/Homebrew, Base runtime, and profile helper
   extractions as the completed shell-domain decomposition for #1570.
2. Keep notification behavior in `setup_common.sh` until it grows into a real
   cross-platform notification policy domain.
3. Structured check/doctor JSON assembly moved into Python-owned code under
   #1591, not into another shell helper.
4. Close #1570 after this ownership decision is documented and validated.
