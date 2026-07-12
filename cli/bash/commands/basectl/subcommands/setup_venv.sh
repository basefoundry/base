#!/usr/bin/env bash

#
# setup_venv.sh
#     Base runtime virtualenv and Python bootstrap helpers for setup_common.sh.
#
# This file is sourced by setup_common.sh. It intentionally preserves the
# existing setup_* function names so setup/check/doctor call sites remain
# behavior-compatible while Base runtime ownership moves out of the shared file.
#

[[ -n "${_base_setup_venv_sourced:-}" ]] && return 0
_base_setup_venv_sourced=1
readonly _base_setup_venv_sourced

_BASE_SETUP_VENV_HEALTH_MESSAGE=""

setup_recreate_venv_enabled() {
    [[ "${BASE_SETUP_RECREATE_VENV:-false}" == true ]]
}

setup_base_recreate_venv_enabled() {
    setup_recreate_venv_enabled || return 1
    [[ -z "${BASE_SETUP_PROJECT_NAME:-}" || "${BASE_SETUP_PROJECT_NAME:-}" == base ]]
}

setup_project_recreate_venv_enabled() {
    local project="$1"

    setup_recreate_venv_enabled || return 1
    [[ -n "$project" && "$project" != base ]]
}

setup_virtualenv_exists() {
    local venv_dir

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    [[ -f "$venv_dir/bin/activate" || -f "$venv_dir/pyvenv.cfg" ]]
}

setup_pyvenv_cfg_value() {
    local key="$1"
    local pyvenv_cfg="$2"
    local line value

    [[ -f "$pyvenv_cfg" ]] || return 1
    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in
            "$key = "*)
                value="${line#"$key = "}"
                printf '%s\n' "$value"
                return 0
                ;;
        esac
    done <"$pyvenv_cfg"
    return 1
}

setup_virtualenv_home_has_python() {
    local candidate home_path="$1"

    [[ -d "$home_path" ]] || return 1
    for candidate in "$home_path"/python*; do
        [[ -x "$candidate" && ! -d "$candidate" ]] && return 0
    done
    return 1
}

setup_python_machine() {
    local machine python_bin="$1"

    [[ -x "$python_bin" ]] || return 1
    machine="$("$python_bin" -c 'import platform; print(platform.machine() or "unknown")' 2>/dev/null || true)"
    [[ -n "$machine" ]] || return 1
    printf '%s\n' "$machine"
}

setup_virtualenv_homebrew_architecture_compatible() {
    local executable_path home_path homebrew_prefix pyvenv_cfg python_bin python_machine venv_dir="$1"

    [[ "$(setup_current_platform)" == macos ]] || return 0

    homebrew_prefix="$(setup_homebrew_prefix 2>/dev/null || true)"
    [[ "$homebrew_prefix" == "/opt/homebrew" ]] || return 0

    pyvenv_cfg="$venv_dir/pyvenv.cfg"
    python_bin="$venv_dir/bin/python"
    python_machine="$(setup_python_machine "$python_bin" || true)"
    executable_path="$(setup_pyvenv_cfg_value executable "$pyvenv_cfg" || true)"
    home_path="$(setup_pyvenv_cfg_value home "$pyvenv_cfg" || true)"

    if [[ "$python_machine" == "x86_64" ]]; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Base virtual environment Python is x86_64 but Homebrew prefix is '$homebrew_prefix'."
        return 1
    fi

    if [[ "$executable_path" == /usr/local/* ]]; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Base virtual environment Python executable '$executable_path' is under /usr/local but Homebrew prefix is '$homebrew_prefix'."
        return 1
    fi

    if [[ "$home_path" == /usr/local/* ]]; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Base virtual environment Python home '$home_path' is under /usr/local but Homebrew prefix is '$homebrew_prefix'."
        return 1
    fi

    return 0
}

setup_virtualenv_healthy_path() {
    local executable_path home_path pyvenv_cfg python_bin venv_dir="$1"

    pyvenv_cfg="$venv_dir/pyvenv.cfg"
    python_bin="$venv_dir/bin/python"
    if [[ ! -d "$venv_dir" ]]; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Virtual environment is missing at '$venv_dir'."
        return 1
    fi
    if [[ ! -f "$pyvenv_cfg" ]]; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Virtual environment is missing pyvenv.cfg at '$pyvenv_cfg'."
        return 1
    fi
    if [[ ! -x "$python_bin" ]]; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Virtual environment Python is missing or not executable at '$python_bin'."
        return 1
    fi
    if ! "$python_bin" --version >/dev/null 2>&1; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Virtual environment Python failed to run at '$python_bin'."
        return 1
    fi

    executable_path="$(setup_pyvenv_cfg_value executable "$pyvenv_cfg" || true)"
    if [[ -n "$executable_path" && ! -x "$executable_path" ]]; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Virtual environment Python is broken because '$executable_path' no longer exists."
        return 1
    fi

    home_path="$(setup_pyvenv_cfg_value home "$pyvenv_cfg" || true)"
    if [[ -n "$home_path" ]] && ! setup_virtualenv_home_has_python "$home_path"; then
        _BASE_SETUP_VENV_HEALTH_MESSAGE="Virtual environment Python is broken because home path '$home_path' no longer provides Python."
        return 1
    fi

    setup_virtualenv_homebrew_architecture_compatible "$venv_dir" || return 1

    _BASE_SETUP_VENV_HEALTH_MESSAGE="Virtual environment is healthy at '$venv_dir'."
    return 0
}

setup_virtualenv_healthy() {
    setup_ensure_cached_paths
    setup_virtualenv_healthy_path "$_BASE_SETUP_VENV_DIR_CACHE"
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

    timestamp="$(setup_backup_timestamp)" || fatal_error "Unable to generate virtual environment backup timestamp."
    backup_path="${venv_dir}.backup.${timestamp}"
    [[ ! -e "$backup_path" ]] || fatal_error "Virtual environment backup path already exists at '$backup_path'."

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would move $description '$venv_dir' to '$backup_path'."
        return 0
    fi

    log_info "Moving $description '$venv_dir' to '$backup_path'."
    mv "$venv_dir" "$backup_path" || fatal_error "Unable to move $description '$venv_dir' to '$backup_path'."
}

setup_pyyaml_package() {
    printf '%s\n' "${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
}

setup_click_package() {
    printf '%s\n' "${BASE_SETUP_CLICK_PACKAGE:-click}"
}

setup_recovery_venv() {
    printf "%s\n" "Run 'basectl setup --recreate-venv' to back up and recreate the Base virtual environment."
}

setup_recovery_base_python_package() {
    printf "%s\n" "Run 'basectl setup' to install Base Python bootstrap packages."
}

setup_recovery_ci_python() {
    printf "%s\n" "Install Python 3.13 or set BASE_SETUP_PYTHON_BIN, then rerun with '--ci'."
}

setup_find_platform_python_bin() {
    local platform

    platform="$(setup_current_platform)" || return 1
    case "$platform" in
        linux-debian)
            setup_find_linux_python_bin
            ;;
        *)
            setup_find_python_bin
            ;;
    esac
}

setup_recovery_platform_python() {
    local platform

    platform="$(setup_current_platform)" || return 1
    case "$platform" in
        linux-debian)
            setup_recovery_linux_python
            ;;
        *)
            setup_recovery_python
            ;;
    esac
}

setup_create_virtualenv() {
    local venv_dir python_bin

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"

    if setup_virtualenv_exists && ! setup_base_recreate_venv_enabled; then
        setup_virtualenv_healthy ||
            fatal_error "$_BASE_SETUP_VENV_HEALTH_MESSAGE $(setup_recovery_venv)"
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

    python_bin="$(setup_find_platform_python_bin)" || fatal_error "Unable to locate a python3 executable after installation. $(setup_recovery_platform_python)"

    safe_mkdir -p "$(dirname "$venv_dir")"
    log_info "Creating Python virtual environment at '$venv_dir'."
    "$python_bin" -m venv "$venv_dir"
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

    if setup_is_dry_run && setup_base_recreate_venv_enabled; then
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
    "$python_bin" -m pip install --disable-pip-version-check "$package" ||
        fatal_error "Unable to install Python package '$package' in the Base virtual environment."
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

setup_write_virtualenv_check_probe() {
    local result_file="$1"

    if setup_virtualenv_healthy; then
        setup_write_check_result_file \
            "$result_file" \
            "base_virtualenv" \
            true \
            "$_BASE_SETUP_VENV_HEALTH_MESSAGE"
    else
        setup_write_check_result_file \
            "$result_file" \
            "base_virtualenv" \
            false \
            "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
            "$(setup_recovery_venv)"
    fi
}

setup_write_python_package_check_probe() {
    local ok=false
    local package="$3"
    local result_file="$1"
    local result_name="$2"

    if setup_base_python_package_installed "$package"; then
        ok=true
    fi

    setup_write_check_result_file \
        "$result_file" \
        "$result_name" \
        "$ok" \
        "$(setup_base_python_package_check_message "$package" "$ok")" \
        "$(setup_recovery_base_python_package)"
}

setup_collect_ci_runtime_check_results() {
    local click_package
    local missing=0
    local pyyaml_package
    local python_bin

    setup_clear_check_results
    click_package="$(setup_click_package)"
    pyyaml_package="$(setup_pyyaml_package)"
    setup_ensure_cached_paths

    if python_bin="$(setup_find_platform_python_bin)"; then
        setup_add_check_result \
            "python" \
            true \
            "Python is available for CI runtime checks." \
            "" \
            "Resolved Python binary: $python_bin"
    else
        setup_add_check_result \
            "python" \
            false \
            "Python is not available for CI runtime checks." \
            "$(setup_recovery_ci_python)"
        missing=1
    fi

    if setup_virtualenv_healthy; then
        setup_add_check_result "base_virtualenv" true "$_BASE_SETUP_VENV_HEALTH_MESSAGE"
    else
        setup_add_check_result \
            "base_virtualenv" \
            false \
            "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
            "$(setup_recovery_venv)"
        missing=1
    fi

    if setup_base_python_package_installed "$pyyaml_package"; then
        setup_add_check_result "pyyaml" true "$(setup_base_python_package_check_message "$pyyaml_package" true)"
    else
        setup_add_check_result \
            "pyyaml" \
            false \
            "$(setup_base_python_package_check_message "$pyyaml_package" false)" \
            "$(setup_recovery_base_python_package)"
        missing=1
    fi

    if setup_base_python_package_installed "$click_package"; then
        setup_add_check_result "click" true "$(setup_base_python_package_check_message "$click_package" true)"
    else
        setup_add_check_result \
            "click" \
            false \
            "$(setup_base_python_package_check_message "$click_package" false)" \
            "$(setup_recovery_base_python_package)"
        missing=1
    fi

    return "$missing"
}

setup_run_ci_runtime_install() {
    setup_create_virtualenv
    setup_install_pyyaml
    setup_install_click
    if setup_profiles_enabled; then
        if setup_is_dry_run; then
            setup_run_base_dev_layer setup --dry-run || fatal_error "Python prerequisite profile layer failed."
        else
            setup_run_base_dev_layer setup || fatal_error "Python prerequisite profile layer failed."
        fi
    fi
    setup_run_project_artifact_setup || return $?

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Base CI setup check is complete."
    else
        log_info "Base CI setup is complete."
    fi
}
