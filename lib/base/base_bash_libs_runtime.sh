#!/usr/bin/env bash
# Shared provider selection for runtime bootstrap and dependency-independent inspection.
# shellcheck disable=SC2034
# Callers supply BASE_HOME and base_init_error; no provider code is sourced here.

[[ -n "${_base_bash_libs_runtime_sourced:-}" ]] && return 0
_base_bash_libs_runtime_sourced=1
readonly _base_bash_libs_runtime_sourced

base_init_homebrew_prefix() {
    case "$BASE_HOME" in
        */opt/base/libexec)
            printf '%s\n' "${BASE_HOME%/opt/base/libexec}"
            ;;
        */Cellar/base/*/libexec)
            printf '%s\n' "${BASE_HOME%%/Cellar/base/*}"
            ;;
    esac
}

base_init_bash_libs_dir_is_usable() {
    local candidate="${1:-}"

    [[ -n "$candidate" ]] || return 1
    [[ -f "$candidate/std/lib_std.sh" ]]
}

base_init_report_missing_bash_libs() {
    local candidate
    local homebrew_prefix

    base_init_error "Base reusable Bash libraries were not found."

    candidate="$BASE_HOME/../base-bash-libs/lib/bash"
    base_init_error "Tried sibling base-bash-libs checkout at '$candidate'."

    homebrew_prefix="$(base_init_homebrew_prefix || true)"
    if [[ -n "$homebrew_prefix" ]]; then
        candidate="$homebrew_prefix/opt/base-bash-libs/libexec/lib/bash"
        base_init_error "Tried Homebrew base-bash-libs package at '$candidate'."
    fi

    base_init_error "Clone basefoundry/base-bash-libs next to Base, install it with 'brew install basefoundry/base/base-bash-libs', or set BASE_BASH_LIBS_DIR to a compatible lib/bash directory."
}

base_init_set_bash_libs_contract() {
    local candidate
    local homebrew_prefix
    local explicit_dir="${BASE_BASH_LIBS_DIR:-}"

    if [[ -n "$explicit_dir" ]]; then
        base_init_bash_libs_dir_is_usable "$explicit_dir" || {
            base_init_error "BASE_BASH_LIBS_DIR '$explicit_dir' does not contain std/lib_std.sh."
            return 1
        }
        BASE_BASH_LIBS_DIR="$(cd -L -- "$explicit_dir" && pwd -L)" || return 1
        BASE_BASH_LIBS_SOURCE=explicit
        return $?
    fi

    candidate="$BASE_HOME/../base-bash-libs/lib/bash"
    if base_init_bash_libs_dir_is_usable "$candidate"; then
        BASE_BASH_LIBS_DIR="$(cd -L -- "$candidate" && pwd -L)" || return 1
        BASE_BASH_LIBS_SOURCE=sibling
        return $?
    fi

    homebrew_prefix="$(base_init_homebrew_prefix || true)"
    if [[ -n "$homebrew_prefix" ]]; then
        candidate="$homebrew_prefix/opt/base-bash-libs/libexec/lib/bash"
        if base_init_bash_libs_dir_is_usable "$candidate"; then
            BASE_BASH_LIBS_DIR="$(cd -L -- "$candidate" && pwd -L)" || return 1
            BASE_BASH_LIBS_SOURCE=homebrew
            return $?
        fi
    fi

    base_init_report_missing_bash_libs
    return 1
}
