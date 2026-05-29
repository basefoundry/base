#!/usr/bin/env bash

#
# setup_common.sh
#     Shared implementation for Base CLI environment bootstrap subcommands.
#
# This file houses the reusable setup/check helpers that back:
#   - `basectl setup`
#   - `basectl check`
#   - `basectl update-profile`
#
# It is meant to be sourced by the umbrella `basectl` command, not invoked
# directly.
#

[[ -n "${_base_setup_common_sourced:-}" ]] && return
_base_setup_common_sourced=1
readonly _base_setup_common_sourced

_BASE_SETUP_VENV_DIR_CACHE=""
_BASE_SETUP_PYTHONPATH_CACHE=""

setup_refresh_cached_paths() {
    local base_pythonpath old_pythonpath

    _BASE_SETUP_VENV_DIR_CACHE="${BASE_SETUP_VENV_DIR:-$HOME/.base.d/base/.venv}"

    base_pythonpath="$BASE_HOME/lib/python:$BASE_HOME/cli/python"
    old_pythonpath="${PYTHONPATH-}"
    if [[ -n "$old_pythonpath" ]]; then
        base_pythonpath="$base_pythonpath:$old_pythonpath"
    fi
    _BASE_SETUP_PYTHONPATH_CACHE="$base_pythonpath"
}

setup_ensure_cached_paths() {
    if [[ -z "${_BASE_SETUP_VENV_DIR_CACHE:-}" || -z "${_BASE_SETUP_PYTHONPATH_CACHE:-}" ]]; then
        setup_refresh_cached_paths
    fi
}

setup_clear_run_state() {
    # Clear legacy lowercase state too so inherited environments cannot trigger
    # lib_std.sh dry-run behavior unless this command explicitly enables it.
    unset dry_run DRY_RUN BASE_SETUP_DEV BASE_SETUP_PROJECT_NAME BASE_SETUP_MANIFEST BASE_SETUP_RECREATE_VENV BASE_PROJECT
    setup_refresh_cached_paths
}

setup_enable_dry_run() {
    export DRY_RUN=true
}

setup_enable_debug_logging() {
    set_log_level DEBUG
    export LOG_DEBUG=1
}

setup_enable_dev_dependencies() {
    export BASE_SETUP_DEV=true
}

setup_dev_dependencies_enabled() {
    [[ "${BASE_SETUP_DEV:-false}" == true ]]
}

setup_is_dry_run() {
    [[ "${DRY_RUN-}" == true ]]
}

setup_enable_recreate_venv() {
    export BASE_SETUP_RECREATE_VENV=true
}

setup_enable_notifications() {
    export BASE_SETUP_NOTIFY=true
    export BASE_SETUP_NOTIFY_FORCE=true
}

setup_disable_notifications() {
    export BASE_SETUP_NOTIFY=false
}

setup_notify_min_seconds() {
    printf '%s\n' "${BASE_SETUP_NOTIFY_MIN_SECONDS:-30}"
}

setup_recreate_venv_enabled() {
    [[ "${BASE_SETUP_RECREATE_VENV:-false}" == true ]]
}

setup_notifications_enabled() {
    [[ "${BASE_SETUP_NOTIFY:-true}" == true ]]
}

setup_notifications_forced() {
    [[ "${BASE_SETUP_NOTIFY_FORCE:-false}" == true ]]
}

setup_virtualenv_exists() {
    local venv_dir

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    [[ -f "$venv_dir/bin/activate" || -f "$venv_dir/pyvenv.cfg" ]]
}

setup_venv_dir() {
    setup_ensure_cached_paths
    printf '%s\n' "$_BASE_SETUP_VENV_DIR_CACHE"
}

setup_backup_existing_venv_path() {
    local backup_path description timestamp venv_dir

    description="${1:-existing path}"
    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    [[ -e "$venv_dir" ]] || return 0

    timestamp="$(date +%Y%m%dT%H%M%S)"
    backup_path="${venv_dir}.backup.${timestamp}"
    [[ ! -e "$backup_path" ]] || fatal_error "Virtual environment backup path already exists at '$backup_path'."

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would move $description '$venv_dir' to '$backup_path'."
        return 0
    fi

    log_info "Moving $description '$venv_dir' to '$backup_path'."
    run mv "$venv_dir" "$backup_path"
}

setup_python_formula() {
    printf '%s\n' "${BASE_SETUP_PYTHON_FORMULA:-python@3.13}"
}

setup_pyyaml_package() {
    printf '%s\n' "${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
}

setup_click_package() {
    printf '%s\n' "${BASE_SETUP_CLICK_PACKAGE:-click}"
}

setup_xcode_tools_dir() {
    printf '%s\n' "${BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR:-/Library/Developer/CommandLineTools}"
}

setup_xcode_wait_timeout_seconds() {
    printf '%s\n' "${BASE_SETUP_XCODE_WAIT_TIMEOUT_SECONDS:-1800}"
}

setup_xcode_wait_interval_seconds() {
    printf '%s\n' "${BASE_SETUP_XCODE_WAIT_INTERVAL_SECONDS:-5}"
}

setup_allow_noninteractive_xcode_install() {
    [[ "${BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL:-false}" == true ]]
}

setup_allow_system_python() {
    [[ "${BASE_SETUP_ALLOW_SYSTEM_PYTHON:-false}" == true ]]
}

setup_allow_test_hooks() {
    [[ "${BASE_TEST_MODE:-false}" == true || "${CI:-false}" == true ]]
}

setup_reject_test_hook_if_disallowed() {
    local variable_name="$1"

    setup_allow_test_hooks && return 0
    fatal_error "$variable_name is a test-only setup override. Set BASE_TEST_MODE=true or CI=true to use it."
}

setup_recovery_homebrew() {
    printf "%s\n" "Run 'basectl setup' to install Homebrew, or install it manually from https://brew.sh/."
}

setup_recovery_brew_path() {
    printf "%s\n" "Check your Homebrew installation and make sure its bin directory is on PATH, then rerun 'basectl setup'."
}

setup_recovery_xcode_tools() {
    printf "%s\n" "Run 'xcode-select --install' in an interactive terminal, complete the installer, then rerun 'basectl setup'."
}

setup_recovery_python() {
    printf "Run 'basectl setup' to install Homebrew Python, or run 'brew install %s'.\n" "$(setup_python_formula)"
}

setup_recovery_venv() {
    printf "%s\n" "Run 'basectl setup --recreate-venv' to back up and recreate the Base virtual environment."
}

setup_recovery_base_python_package() {
    printf "%s\n" "Run 'basectl setup' to install Base Python bootstrap packages."
}

setup_recovery_project_layer() {
    printf "%s\n" "Review the Python error above, then rerun 'basectl setup -v' for more detail."
}

setup_notify_completion() {
    local exit_code="$1"
    local elapsed_seconds=0
    local message title
    local min_seconds

    setup_notifications_enabled || return 0
    setup_is_dry_run && return 0
    [[ "$OSTYPE" == darwin* ]] || return 0
    if ! command -v osascript >/dev/null 2>&1; then
        if setup_notifications_forced; then
            log_warn "Setup notification was requested, but 'osascript' is not available on this Mac."
        fi
        return 0
    fi

    min_seconds="$(setup_notify_min_seconds)"
    if ! [[ "$min_seconds" =~ ^[0-9]+$ ]]; then
        min_seconds=30
    fi
    if [[ -n "${BASE_SETUP_START_TIME:-}" && "$BASE_SETUP_START_TIME" =~ ^[0-9]+$ ]]; then
        elapsed_seconds=$(($(date +%s) - BASE_SETUP_START_TIME))
    fi
    if ! setup_notifications_forced && ((elapsed_seconds < min_seconds)); then
        return 0
    fi

    if ((exit_code == 0)); then
        title="Base setup complete"
        message="Base CLI setup completed successfully."
    else
        title="Base setup failed"
        message="Base CLI setup failed. Check the terminal for details."
    fi

    osascript -e 'on run argv
display notification (item 2 of argv) with title (item 1 of argv)
end run' "$title" "$message" >/dev/null 2>&1 || true
}

setup_find_brew_bin() {
    local candidate

    if [[ -n "${BASE_SETUP_BREW_BIN+x}" ]]; then
        if [[ -x "${BASE_SETUP_BREW_BIN}" ]]; then
            printf '%s\n' "${BASE_SETUP_BREW_BIN}"
            return 0
        fi
        return 1
    fi

    if command -v brew >/dev/null 2>&1; then
        command -v brew
        return 0
    fi

    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        [[ -x "$candidate" ]] || continue
        printf '%s\n' "$candidate"
        return 0
    done

    return 1
}

setup_refresh_brew_path() {
    local brew_bin

    brew_bin="$(setup_find_brew_bin)" || return 1
    add_to_path -p "$(dirname "$brew_bin")"
    return 0
}

setup_install_homebrew() {
    # Trust decision: Base follows Homebrew's official install command, which
    # intentionally fetches the installer from the mutable HEAD ref. Pinning a
    # reviewed commit would reduce mutability risk, but would also make Base own
    # installer refreshes and drift from Homebrew's supported bootstrap path.
    local installer_url="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
    local exit_code

    if setup_find_brew_bin >/dev/null 2>&1; then
        setup_refresh_brew_path || fatal_error "Homebrew is installed, but its bin directory could not be added to PATH. $(setup_recovery_brew_path)"
        log_info "Homebrew is already installed."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install Homebrew using the official installer."
        return 0
    fi

    log_info "Installing Homebrew."

    if [[ -n "${BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT:-}" ]]; then
        setup_reject_test_hook_if_disallowed BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT
        run "$BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT"
    else
        command -v curl >/dev/null 2>&1 || fatal_error "curl is required to install Homebrew. Install curl or install Homebrew manually from https://brew.sh/, then rerun 'basectl setup'."
        /bin/bash -c "$(curl -fsSL "$installer_url")"
        exit_code=$?
        if ((exit_code)); then
            log_error "$(setup_recovery_homebrew)"
        fi
        exit_if_error "$exit_code" "Homebrew installation failed."
    fi

    setup_refresh_brew_path || fatal_error "Homebrew installation finished, but 'brew' was not found on PATH. $(setup_recovery_brew_path)"
}

setup_require_macos() {
    [[ "$OSTYPE" == darwin* ]] || fatal_error "The setup command currently supports macOS only (OSTYPE='$OSTYPE')."
}

setup_xcode_tools_installed() {
    local tools_dir

    tools_dir="$(setup_xcode_tools_dir)"
    xcode-select -p >/dev/null 2>&1 &&
        [[ -d "$tools_dir" ]] &&
        [[ -f "$tools_dir/usr/bin/clang" ]]
}

setup_install_xcode_tools() {
    local timeout interval start_time current_time

    if setup_xcode_tools_installed; then
        log_info "Xcode Command Line Tools are already installed."
        return 0
    fi

    if ! is_interactive && ! setup_allow_noninteractive_xcode_install && ! setup_is_dry_run; then
        fatal_error "Xcode Command Line Tools installation requires an interactive terminal. $(setup_recovery_xcode_tools)"
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install Xcode Command Line Tools and wait for installation to complete."
        return 0
    fi

    log_info "Installing Xcode Command Line Tools."
    run --no-exit xcode-select --install

    timeout="$(setup_xcode_wait_timeout_seconds)"
    interval="$(setup_xcode_wait_interval_seconds)"
    start_time="$(date +%s)"

    until setup_xcode_tools_installed; do
        current_time="$(date +%s)"
        if ((current_time - start_time >= timeout)); then
            fatal_error "Timed out waiting for Xcode Command Line Tools installation to complete. If the installer is still open, finish it. Otherwise $(setup_recovery_xcode_tools)"
        fi
        sleep "$interval"
    done

    log_info "Xcode Command Line Tools installation detected."
}

setup_python_installed() {
    local formula

    formula="$(setup_python_formula)"
    command -v brew >/dev/null 2>&1 && brew list "$formula" >/dev/null 2>&1
}

setup_install_python() {
    local formula

    formula="$(setup_python_formula)"

    if setup_python_installed; then
        log_info "Python formula '$formula' is already installed via Homebrew."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install Python formula '$formula' via Homebrew."
        return 0
    fi

    command -v brew >/dev/null 2>&1 || fatal_error "Homebrew is required to install Python formula '$formula'. $(setup_recovery_homebrew)"

    log_info "Installing Python formula '$formula' via Homebrew."
    run brew install "$formula"
}

setup_find_python_bin() {
    local formula prefix candidate
    local candidates=()

    if [[ -n "${BASE_SETUP_PYTHON_BIN:-}" ]]; then
        setup_reject_test_hook_if_disallowed BASE_SETUP_PYTHON_BIN
        [[ -x "${BASE_SETUP_PYTHON_BIN}" ]] || return 1
        printf '%s\n' "${BASE_SETUP_PYTHON_BIN}"
        return 0
    fi

    formula="$(setup_python_formula)"
    candidates+=("/opt/homebrew/opt/$formula/bin/python3")
    candidates+=("/usr/local/opt/$formula/bin/python3")

    for candidate in "${candidates[@]}"; do
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    candidates=()
    if command -v brew >/dev/null 2>&1; then
        prefix="$(brew --prefix "$formula" 2>/dev/null || true)"
        if [[ -n "$prefix" ]]; then
            candidates+=("$prefix/bin/python3")
            candidates+=("$prefix/libexec/bin/python3")
            if [[ "$formula" == python@* ]]; then
                candidates+=("$prefix/bin/python${formula#python@}")
                candidates+=("$prefix/libexec/bin/python${formula#python@}")
            fi
            for candidate in "${candidates[@]}"; do
                if [[ -x "$candidate" ]]; then
                    printf '%s\n' "$candidate"
                    return 0
                fi
            done
        fi
    fi

    if setup_allow_system_python && command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi

    return 1
}

setup_create_virtualenv() {
    local venv_dir python_bin

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"

    if setup_virtualenv_exists && ! setup_recreate_venv_enabled; then
        log_info "Virtual environment already exists at '$venv_dir'."
        return 0
    fi

    if setup_virtualenv_exists; then
        setup_backup_existing_venv_path "existing virtual environment"
    else
        setup_backup_existing_venv_path "existing non-venv path"
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would create Python virtual environment at '$venv_dir'."
        return 0
    fi

    python_bin="$(setup_find_python_bin)" || fatal_error "Unable to locate a python3 executable after installation. $(setup_recovery_python)"

    safe_mkdir -p "$(dirname "$venv_dir")"
    log_info "Creating Python virtual environment at '$venv_dir'."
    run "$python_bin" -m venv "$venv_dir"
}

setup_base_venv_python_bin() {
    local venv_dir="$1"
    local python_bin="$venv_dir/bin/python"

    [[ -x "$python_bin" ]] || return 1
    printf '%s\n' "$python_bin"
}

setup_base_python_package_installed() {
    local package="$1"
    local venv_dir python_bin

    if setup_is_dry_run && setup_recreate_venv_enabled; then
        return 1
    fi

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    python_bin="$(setup_base_venv_python_bin "$venv_dir")" || return 1
    "$python_bin" -m pip show "$package" >/dev/null 2>&1
}

setup_install_base_python_package() {
    local package="$1"
    local venv_dir python_bin

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"

    if setup_base_python_package_installed "$package"; then
        log_info "Python package '$package' is already installed in the Base virtual environment."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install Python package '$package' in the Base virtual environment."
        return 0
    fi

    python_bin="$(setup_base_venv_python_bin "$venv_dir")" || fatal_error "Base virtual environment Python was not found at '$venv_dir/bin/python'. $(setup_recovery_venv)"

    log_info "Installing Python package '$package' in the Base virtual environment."
    run "$python_bin" -m pip install "$package"
}

setup_install_pyyaml() {
    setup_install_base_python_package "$(setup_pyyaml_package)"
}

setup_install_click() {
    setup_install_base_python_package "$(setup_click_package)"
}

setup_base_python_package_check_message() {
    local package="$1"
    local installed="$2"

    if [[ "$installed" == true ]]; then
        printf "Python package '%s' is installed in the Base virtual environment.\n" "$package"
    else
        printf "Python package '%s' is not installed in the Base virtual environment.\n" "$package"
    fi
}

setup_pythonpath() {
    setup_ensure_cached_paths
    printf '%s\n' "$_BASE_SETUP_PYTHONPATH_CACHE"
}

setup_resolve_project_manifest() {
    local project="$1"
    local python_bin="$2"
    local resolve_output resolved_manifest resolved_name resolved_root

    if [[ -n "${BASE_SETUP_MANIFEST:-}" ]]; then
        if [[ -z "$project" ]]; then
            setup_ensure_cached_paths
            env BASE_HOME="$BASE_HOME" BASE_PROJECT=base PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
                "$python_bin" -m base_projects manifest "$BASE_SETUP_MANIFEST"
            return $?
        fi
        printf '%s\n' "$BASE_SETUP_MANIFEST"
        return 0
    fi

    if [[ -z "$project" ]]; then
        project=base
    fi

    if [[ "$project" == base ]]; then
        printf '%s\n' "$BASE_HOME/base_manifest.yaml"
        return 0
    fi

    setup_ensure_cached_paths
    resolve_output="$(
        env BASE_HOME="$BASE_HOME" BASE_PROJECT=base PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
            "$python_bin" -m base_projects resolve "$project"
    )" || return 1

    IFS=$'\t' read -r resolved_name resolved_root resolved_manifest <<<"$resolve_output"
    [[ "$resolved_name" == "$project" && -n "$resolved_root" && -n "$resolved_manifest" ]] || return 1

    printf '%s\t%s\t%s\n' "$resolved_name" "$resolved_root" "$resolved_manifest"
}

setup_project_venv_dir() {
    local project="$1"

    if [[ -n "${BASE_PROJECT_VENV_DIR:-}" ]]; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi
    printf '%s\n' "$HOME/.base.d/$project/.venv"
}

setup_project_venv_python_bin() {
    local project="$1"
    local venv_dir

    venv_dir="$(setup_project_venv_dir "$project")"
    [[ -x "$venv_dir/bin/python" ]] || return 1
    printf '%s\n' "$venv_dir/bin/python"
}

setup_run_project_artifact_setup() {
    setup_run_project_artifact_layer setup text
}

setup_run_project_bootstrap_layer() {
    local manifest_path="$1"
    local project="$2"
    local output_format="$3"
    local python_bin venv_dir
    local args=()

    if setup_is_dry_run && ! setup_base_python_package_installed "$(setup_pyyaml_package)"; then
        log_info "[DRY-RUN] Would bootstrap project Python runtime after PyYAML is installed."
        return 0
    fi

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    python_bin="$(setup_base_venv_python_bin "$venv_dir")" || fatal_error "Base virtual environment Python was not found at '$venv_dir/bin/python'. $(setup_recovery_venv)"

    if setup_is_dry_run; then
        args+=(--dry-run)
    fi
    args+=(--manifest "$manifest_path" --action bootstrap "$project")

    if [[ "$output_format" != json ]]; then
        log_info "Bootstrapping Python runtime for project '$project'."
    fi

    setup_ensure_cached_paths
    env BASE_HOME="$BASE_HOME" BASE_PROJECT="$project" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" "$python_bin" -m base_setup "${args[@]}"
}

setup_run_project_artifact_layer() {
    local action="$1"
    local output_format="$2"
    local exit_code manifest_path project python_bin resolved_name resolved_root resolve_output venv_dir
    local args=()

    if setup_is_dry_run && ! setup_base_python_package_installed "$(setup_pyyaml_package)"; then
        log_info "[DRY-RUN] Would run Python project setup layer after PyYAML is installed."
        return 0
    fi

    project="${BASE_SETUP_PROJECT_NAME:-}"
    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    python_bin="$(setup_base_venv_python_bin "$venv_dir")" || fatal_error "Base virtual environment Python was not found at '$venv_dir/bin/python'. $(setup_recovery_venv)"
    resolve_output="$(setup_resolve_project_manifest "$project" "$python_bin")" || {
        log_error "Unable to resolve Base project '$project'."
        log_error "Run 'basectl projects list' to see projects Base can discover."
        return 1
    }
    if [[ "$resolve_output" == *$'\t'* ]]; then
        IFS=$'\t' read -r resolved_name resolved_root manifest_path <<<"$resolve_output"
        project="$resolved_name"
        if [[ "$output_format" != json ]]; then
            log_info "Resolved project '$project' at '$resolved_root'."
        fi
    else
        if [[ -z "$project" ]]; then
            project=base
        fi
        manifest_path="$resolve_output"
    fi

    if setup_is_dry_run; then
        args+=(--dry-run)
    fi
    args+=(--manifest "$manifest_path")
    args+=(--action "$action")
    if [[ "$action" == check || "$action" == doctor ]]; then
        args+=(--format "$output_format")
    fi
    args+=("$project")

    if [[ "$output_format" != json ]]; then
        log_info "Running Python project $action layer."
    fi

    if [[ "$action" == setup ]]; then
        setup_run_project_bootstrap_layer "$manifest_path" "$project" "$output_format"
        exit_code=$?
        if ((exit_code)); then
            log_error "$(setup_recovery_project_layer)"
            log_error "Python project $action layer failed."
            return "$exit_code"
        fi
    fi

    if ! setup_project_venv_python_bin "$project" >/dev/null 2>&1; then
        if setup_is_dry_run && [[ "$action" == setup ]]; then
            log_info "[DRY-RUN] Would run Python project setup layer through base-wrapper for project '$project'."
            return 0
        fi
        if [[ "$output_format" != json ]]; then
            log_warn "Project virtual environment Python was not found at '$(setup_project_venv_dir "$project")/bin/python'."
            log_warn "Run 'basectl setup $project' to bootstrap the project virtual environment."
        fi
        return 1
    fi

    "$BASE_HOME/bin/base-wrapper" --project "$project" base_setup "${args[@]}"
    exit_code=$?

    if ((exit_code)) && [[ "$action" == setup ]]; then
        log_error "$(setup_recovery_project_layer)"
        log_error "Python project $action layer failed."
        return "$exit_code"
    fi
    if ((exit_code)) && [[ "$action" == check ]]; then
        log_warn "Python project check layer found missing requirements."
        return "$exit_code"
    fi
    if ((exit_code)); then
        return "$exit_code"
    fi
}

setup_run_project_artifact_check() {
    setup_run_project_artifact_layer check text
}

setup_run_project_artifact_check_json() {
    setup_run_project_artifact_layer check json
}

setup_run_project_artifact_doctor() {
    setup_run_project_artifact_layer doctor text
}

setup_run_project_artifact_doctor_json() {
    setup_run_project_artifact_layer doctor json
}

setup_run_base_dev_layer() {
    local args=("$@")
    local venv_dir

    if setup_is_dry_run &&
        { ! setup_base_python_package_installed "$(setup_pyyaml_package)" ||
            ! setup_base_python_package_installed "$(setup_click_package)"; }; then
        log_info "[DRY-RUN] Would run Python developer prerequisite layer after Base Python bootstrap dependencies are installed."
        return 0
    fi

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    if ! setup_base_venv_python_bin "$venv_dir" >/dev/null 2>&1; then
        log_warn "Python developer prerequisite layer cannot run because Base virtual environment Python was not found at '$venv_dir/bin/python'."
        log_warn "$(setup_recovery_venv)"
        return 1
    fi

    "$BASE_HOME/bin/base-wrapper" --project base base_dev "${args[@]}"
}

setup_run_check() {
    local brew_bin="" click_package pyyaml_package venv_dir missing=0
    local project="${BASE_SETUP_PROJECT_NAME:-}"

    setup_require_macos
    click_package="$(setup_click_package)"
    pyyaml_package="$(setup_pyyaml_package)"
    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"

    if brew_bin="$(setup_find_brew_bin)"; then
        setup_refresh_brew_path || fatal_error "Homebrew is installed, but its bin directory could not be added to PATH. $(setup_recovery_brew_path)"
        log_info "Homebrew is installed."
        log_debug "Resolved Homebrew binary: $brew_bin"
    else
        log_warn "Homebrew is not installed."
        log_warn "$(setup_recovery_homebrew)"
        missing=1
    fi

    if setup_xcode_tools_installed; then
        log_info "Xcode Command Line Tools are installed."
    else
        log_warn "Xcode Command Line Tools are not installed."
        log_warn "$(setup_recovery_xcode_tools)"
        missing=1
    fi

    if setup_python_installed; then
        log_info "Python formula '$(setup_python_formula)' is installed via Homebrew."
    else
        log_warn "Python formula '$(setup_python_formula)' is not installed via Homebrew."
        log_warn "$(setup_recovery_python)"
        missing=1
    fi

    if setup_virtualenv_exists; then
        log_info "Virtual environment exists at '$venv_dir'."
    else
        log_warn "Virtual environment is missing at '$venv_dir'."
        log_warn "$(setup_recovery_venv)"
        missing=1
    fi

    if setup_base_python_package_installed "$pyyaml_package"; then
        log_info "$(setup_base_python_package_check_message "$pyyaml_package" true)"
    else
        log_warn "$(setup_base_python_package_check_message "$pyyaml_package" false)"
        log_warn "$(setup_recovery_base_python_package)"
        missing=1
    fi

    if setup_base_python_package_installed "$click_package"; then
        log_info "$(setup_base_python_package_check_message "$click_package" true)"
    else
        log_warn "$(setup_base_python_package_check_message "$click_package" false)"
        log_warn "$(setup_recovery_base_python_package)"
        missing=1
    fi

    if setup_dev_dependencies_enabled; then
        setup_run_base_dev_layer check || missing=1
    fi

    if [[ -n "$project" ]]; then
        setup_run_project_artifact_check || missing=1
    fi

    if ((missing == 0)); then
        if [[ -n "$project" ]]; then
            log_info "Base CLI environment and project '$project' check passed."
        else
            log_info "Base CLI environment check passed."
        fi
        return 0
    fi

    if [[ -n "$project" ]]; then
        log_warn "Base CLI environment or project '$project' check found missing requirements."
        log_warn "Run 'basectl setup $project' to reconcile the missing requirements."
    else
        log_warn "Base CLI environment check found missing requirements."
        log_warn "Run 'basectl setup' to reconcile the missing requirements."
    fi
    return 1
}

setup_json_escape() {
    local value="${1:-}"
    local char code escaped i
    local output=""
    local LC_ALL=C

    for ((i = 0; i < ${#value}; i++)); do
        char="${value:i:1}"
        case "$char" in
            '"')
                output+='\"'
                ;;
            '\')
                output+='\\'
                ;;
            $'\b')
                output+='\b'
                ;;
            $'\f')
                output+='\f'
                ;;
            $'\n')
                output+='\n'
                ;;
            $'\r')
                output+='\r'
                ;;
            $'\t')
                output+='\t'
                ;;
            *)
                printf -v code '%d' "'$char"
                if ((code < 32)); then
                    printf -v escaped '\\u%04x' "$code"
                    output+="$escaped"
                else
                    output+="$char"
                fi
                ;;
        esac
    done

    printf '%s' "$output"
}

setup_print_check_json_item() {
    local trailing_comma="$1"
    local name="$2"
    local ok="$3"
    local message="$4"

    printf '    {"name":"%s","ok":%s,"message":"%s"}%s\n' \
        "$(setup_json_escape "$name")" \
        "$ok" \
        "$(setup_json_escape "$message")" \
        "$trailing_comma"
}

setup_print_json_property_value() {
    local first_line=true
    local key="$1"
    local line
    local value="$2"

    printf '  "%s": ' "$(setup_json_escape "$key")"
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$first_line" == true ]]; then
            printf '%s\n' "$line"
            first_line=false
        else
            printf '  %s\n' "$line"
        fi
    done <<<"$value"
}

setup_run_check_json() {
    local brew_bin homebrew_message homebrew_ok=false
    local click_message click_ok=false click_package
    local dev_json="[]"
    local missing=0
    local project="${BASE_SETUP_PROJECT_NAME:-}"
    local project_json="[]"
    local pyyaml_message pyyaml_ok=false pyyaml_package
    local python_message python_ok=false
    local venv_dir venv_message venv_ok=false
    local xcode_message xcode_ok=false

    setup_require_macos
    click_package="$(setup_click_package)"
    pyyaml_package="$(setup_pyyaml_package)"
    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"

    if brew_bin="$(setup_find_brew_bin)"; then
        if setup_refresh_brew_path; then
            homebrew_ok=true
            homebrew_message="Homebrew is installed."
        else
            homebrew_message="Homebrew is installed, but its bin directory could not be added to PATH."
            missing=1
        fi
    else
        homebrew_message="Homebrew is not installed."
        missing=1
    fi

    if setup_xcode_tools_installed; then
        xcode_ok=true
        xcode_message="Xcode Command Line Tools are installed."
    else
        xcode_message="Xcode Command Line Tools are not installed."
        missing=1
    fi

    if setup_python_installed; then
        python_ok=true
        python_message="Python formula '$(setup_python_formula)' is installed via Homebrew."
    else
        python_message="Python formula '$(setup_python_formula)' is not installed via Homebrew."
        missing=1
    fi

    if setup_virtualenv_exists; then
        venv_ok=true
        venv_message="Virtual environment exists at '$venv_dir'."
    else
        venv_message="Virtual environment is missing at '$venv_dir'."
        missing=1
    fi

    if setup_base_python_package_installed "$pyyaml_package"; then
        pyyaml_ok=true
    else
        missing=1
    fi
    pyyaml_message="$(setup_base_python_package_check_message "$pyyaml_package" "$pyyaml_ok")"

    if setup_base_python_package_installed "$click_package"; then
        click_ok=true
    else
        missing=1
    fi
    click_message="$(setup_base_python_package_check_message "$click_package" "$click_ok")"

    if setup_dev_dependencies_enabled; then
        if ! dev_json="$(setup_run_base_dev_layer check --format json)"; then
            missing=1
            [[ -n "$dev_json" ]] || dev_json="[]"
        fi
    fi

    if [[ -n "$project" ]]; then
        if ! project_json="$(setup_run_project_artifact_check_json)"; then
            missing=1
            [[ -n "$project_json" ]] || project_json="[]"
        fi
    fi

    printf '{\n'
    printf '  "ok": %s,\n' "$([[ "$missing" -eq 0 ]] && printf true || printf false)"
    if [[ -n "$project" ]]; then
        printf '  "project": "%s",\n' "$(setup_json_escape "$project")"
    fi
    printf '  "checks": [\n'
    setup_print_check_json_item "," "homebrew" "$homebrew_ok" "$homebrew_message"
    setup_print_check_json_item "," "xcode_command_line_tools" "$xcode_ok" "$xcode_message"
    setup_print_check_json_item "," "python" "$python_ok" "$python_message"
    setup_print_check_json_item "," "base_virtualenv" "$venv_ok" "$venv_message"
    setup_print_check_json_item "," "pyyaml" "$pyyaml_ok" "$pyyaml_message"
    setup_print_check_json_item "" "click" "$click_ok" "$click_message"
    printf '  ]'
    if setup_dev_dependencies_enabled || [[ -n "$project" ]]; then
        printf ',\n'
    else
        printf '\n'
    fi
    if setup_dev_dependencies_enabled; then
        setup_print_json_property_value "dev_checks" "$dev_json"
        if [[ -n "$project" ]]; then
            printf ',\n'
        else
            printf '\n'
        fi
    fi
    if [[ -n "$project" ]]; then
        setup_print_json_property_value "project_checks" "$project_json"
    else
        :
    fi
    printf '}\n'

    [[ "$missing" -eq 0 ]]
}

setup_run_install() {
    setup_require_macos
    setup_install_homebrew
    setup_install_xcode_tools
    setup_install_python
    setup_create_virtualenv
    setup_install_pyyaml
    setup_install_click
    if setup_dev_dependencies_enabled; then
        if setup_is_dry_run; then
            setup_run_base_dev_layer setup --dry-run || fatal_error "Python developer prerequisite layer failed."
        else
            setup_run_base_dev_layer setup || fatal_error "Python developer prerequisite layer failed."
        fi
    fi
    setup_run_project_artifact_setup || return $?

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Base CLI setup check is complete."
    else
        log_info "Base CLI setup is complete."
    fi
}
