#!/usr/bin/env bash

#
# setup_profiles.sh
#     Base setup/check profile parsing and dispatch helpers for setup_common.sh.
#
# This file is sourced by setup_common.sh. It intentionally preserves the
# existing setup_* function names so setup/check/doctor call sites remain
# behavior-compatible while profile ownership moves out of the shared file.
#

[[ -n "${_base_setup_profiles_sourced:-}" ]] && return 0
_base_setup_profiles_sourced=1
readonly _base_setup_profiles_sourced

setup_supported_profiles() {
    printf '%s\n' "dev sre ai linux-lab"
}

setup_supported_profiles_display() {
    printf '%s\n' "dev, sre, ai, linux-lab"
}

setup_profile_supported() {
    local profile="$1"

    case "$profile" in
        dev|sre|ai|linux-lab)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

setup_normalize_profile_name() {
    local profile="$1"

    profile="${profile//[[:space:]]/}"
    printf '%s' "${profile,,}"
}

setup_profile_enabled() {
    local enabled_profile
    local profile="$1"

    for enabled_profile in ${BASE_SETUP_PROFILES:-}; do
        [[ "$enabled_profile" == "$profile" ]] && return 0
    done
    return 1
}

setup_enable_profile() {
    local profile="$1"

    setup_profile_supported "$profile" || return 1
    if setup_profile_enabled "$profile"; then
        return 0
    fi
    BASE_SETUP_PROFILES="${BASE_SETUP_PROFILES:+$BASE_SETUP_PROFILES }$profile"
    export BASE_SETUP_PROFILES
}

setup_enable_profile_argument() {
    local compact profile profile_arg="$1"
    local profiles=()

    BASE_SETUP_PROFILE_ERROR=""
    compact="${profile_arg//[[:space:]]/}"
    if [[ -z "$compact" || "$compact" == ,* || "$compact" == *, || "$compact" == *,,* ]]; then
        BASE_SETUP_PROFILE_ERROR="Profile list must not contain empty entries."
        return 1
    fi

    str_split profiles "$compact" ","
    for profile in "${profiles[@]}"; do
        profile="$(setup_normalize_profile_name "$profile")"
        if ! setup_profile_supported "$profile"; then
            # shellcheck disable=SC2034 # Consumed by setup.sh after this helper returns.
            BASE_SETUP_PROFILE_ERROR="Unsupported profile '$profile'. Expected one of: $(setup_supported_profiles_display)."
            return 1
        fi
        setup_enable_profile "$profile"
    done
}

setup_profiles_enabled() {
    [[ -n "${BASE_SETUP_PROFILES:-}" ]]
}

setup_profile_json_key() {
    local suffix="$1"

    printf 'profile_%s\n' "$suffix"
}

setup_profiles_csv() {
    local first=true profile

    for profile in ${BASE_SETUP_PROFILES:-}; do
        if [[ "$first" == true ]]; then
            printf '%s' "$profile"
            first=false
        else
            printf ',%s' "$profile"
        fi
    done
    printf '\n'
}

setup_run_base_dev_layer() {
    local args=("$@")
    local platform
    local profile_args=()
    local venv_dir

    if setup_is_dry_run &&
        { ! setup_base_python_package_installed "$(setup_pyyaml_package)" ||
            ! setup_base_python_package_installed "$(setup_click_package)"; }; then
        log_info "[DRY-RUN] Would run Python prerequisite profile layer after Base Python bootstrap dependencies are installed."
        return 0
    fi

    setup_ensure_cached_paths
    venv_dir="$_BASE_SETUP_VENV_DIR_CACHE"
    if ! setup_base_venv_python_bin "$venv_dir" >/dev/null 2>&1; then
        log_warn "Python prerequisite profile layer cannot run because Base virtual environment Python was not found at '$venv_dir/bin/python'."
        log_warn "$(setup_recovery_venv)"
        return 1
    fi

    profile_args=(--profile "$(setup_profiles_csv)")
    platform="$(setup_current_platform)" || return 1

    env BASE_PLATFORM="$platform" "$BASE_HOME/bin/base-wrapper" --project base base_dev "${args[@]}" "${profile_args[@]}"
}
