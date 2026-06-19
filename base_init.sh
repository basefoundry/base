#!/usr/bin/env bash

#
# base_init.sh
#     Base runtime bootstrap for Bash commands and Base-enabled Bash shells.
#
# Loaded by:
#     - bin/basectl before it sources a Base command implementation
#     - bin/basectl before it sources an explicit Base-enabled Bash script
#     - lib/bash/runtime/bashrc for `basectl` and `basectl shell` sessions
#
# Not loaded by:
#     - normal Bash/Zsh dotfile startup managed by lib/shell/*
#
# Runtime contract:
#     - validate that the runtime is Bash 4.2 or newer
#     - derive or validate BASE_HOME
#     - export the BASE_* paths that downstream scripts may rely on
#     - export BASE_OS and BASE_HOST runtime metadata
#     - resolve and source the reusable Bash standard library
#     - add BASE_BIN_DIR to PATH
#     - provide import_base_lib for convention-based Base Bash library imports
#
# Downstream scripts should not rediscover Base's directory layout on their own.
# They should use the exported BASE_* variables and import libraries with:
#
#     import_base_lib file/lib_file.sh
#
# import_base_lib loads reusable libraries from base-bash-libs. It reports
# missing or invalid libraries through Base stdlib error handling and fails
# immediately, so callers do not need duplicate checks.
#

[[ -n "${__base_init_sourced__:-}" ]] && return 0
readonly __base_init_sourced__=1

base_init_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

base_init_resolve_path() {
    local source_path="${1:-}"
    local link_dir
    local target

    [[ -n "$source_path" ]] || return 1

    while [[ -L "$source_path" ]]; do
        link_dir="$(cd -- "$(dirname -- "$source_path")" && pwd -P)" || return 1
        target="$(readlink "$source_path")" || return 1
        if [[ "$target" == /* ]]; then
            source_path="$target"
        else
            source_path="$link_dir/$target"
        fi
    done

    link_dir="$(cd -- "$(dirname -- "$source_path")" && pwd -P)" || return 1
    printf '%s/%s\n' "$link_dir" "$(basename -- "$source_path")"
}

base_init_require_bash() {
    local current_version

    if [[ -z "${BASH_VERSION:-}" ]]; then
        base_init_error "Base runtime requires Bash."
        return 1
    fi

    current_version="${BASH_VERSINFO[0]}${BASH_VERSINFO[1]}"
    if ((current_version < 42)); then
        base_init_error "Base runtime requires Bash 4.2 or newer; current version is ${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}."
        return 1
    fi
}

base_init_resolve_home() {
    local source_path
    local source_dir

    if [[ -n "${BASE_HOME:-}" ]]; then
        [[ -d "$BASE_HOME" ]] || {
            base_init_error "BASE_HOME '$BASE_HOME' is not a directory or is not accessible."
            return 1
        }
        (cd -L -- "$BASE_HOME" && pwd -L)
        return $?
    fi

    source_path="$(base_init_resolve_path "${BASH_SOURCE[0]}")" || return 1
    source_dir="$(cd -- "$(dirname -- "$source_path")" && pwd -P)" || return 1
    printf '%s\n' "$source_dir"
}

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

base_init_export_contract() {
    local base_home base_os base_host uname_os

    base_home="$(base_init_resolve_home)" || return 1
    uname_os="$(uname -s)" || {
        base_init_error "Unable to determine BASE_OS with uname."
        return 1
    }
    [[ -n "$uname_os" ]] || {
        base_init_error "Unable to determine BASE_OS with uname."
        return 1
    }
    case "$uname_os" in
        Darwin)
            base_os=macos
            ;;
        Linux)
            base_os=linux
            ;;
        *)
            base_os="$(printf '%s\n' "$uname_os" | tr '[:upper:]' '[:lower:]')"
            ;;
    esac
    base_host="$(hostname -s)" || {
        base_init_error "Unable to determine BASE_HOST with hostname."
        return 1
    }
    [[ -n "$base_host" ]] || {
        base_init_error "Unable to determine BASE_HOST with hostname."
        return 1
    }

    BASE_HOME="$base_home"
    BASE_BIN_DIR="$BASE_HOME/bin"
    BASE_CLI_DIR="$BASE_HOME/cli"
    BASE_BASH_DIR="$BASE_CLI_DIR/bash"
    BASE_BASH_COMMANDS_DIR="$BASE_BASH_DIR/commands"
    BASE_LIB_DIR="$BASE_HOME/lib"
    BASE_BASH_LIB_DIR="$BASE_LIB_DIR/bash"
    base_init_set_bash_libs_contract || return 1
    BASE_SHELL_DIR="$BASE_LIB_DIR/shell"
    BASE_OS="$base_os"
    BASE_HOST="$base_host"
    BASE_SHELL="${BASE_SHELL:-bash}"
    export BASE_HOME BASE_BIN_DIR BASE_CLI_DIR BASE_BASH_DIR BASE_BASH_COMMANDS_DIR
    export BASE_LIB_DIR BASE_BASH_LIB_DIR BASE_BASH_LIBS_DIR BASE_BASH_LIBS_SOURCE BASE_SHELL_DIR BASE_OS BASE_HOST BASE_SHELL
    readonly BASE_HOME BASE_BIN_DIR BASE_CLI_DIR BASE_BASH_DIR BASE_BASH_COMMANDS_DIR
    readonly BASE_LIB_DIR BASE_BASH_LIB_DIR BASE_BASH_LIBS_DIR BASE_BASH_LIBS_SOURCE BASE_SHELL_DIR BASE_OS BASE_HOST BASE_SHELL
}

base_init_source_stdlib() {
    local stdlib_path="$BASE_BASH_LIBS_DIR/std/lib_std.sh"

    [[ -f "$stdlib_path" ]] || {
        base_init_error "Base Bash stdlib '$stdlib_path' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$stdlib_path"
}

import_base_lib() {
    local relative_path="${1:-}"
    local lib_path

    [[ -n "$relative_path" ]] || fatal_error "import_base_lib: no library path provided."
    [[ "$relative_path" != /* ]] || fatal_error "import_base_lib: expected a path relative to '$BASE_BASH_LIBS_DIR', got '$relative_path'."

    case "$relative_path" in
        ..|../*|*/..|*/../*)
            fatal_error "import_base_lib: refusing path outside Base Bash library root: '$relative_path'."
            ;;
    esac

    lib_path="$BASE_BASH_LIBS_DIR/$relative_path"
    [[ -f "$lib_path" ]] || fatal_error "Base reusable library '$relative_path' was not found at '$lib_path'."

    # shellcheck source=/dev/null
    source "$lib_path" || fatal_error "Failed to import Base library '$lib_path'."
}

base_init_main() {
    base_init_require_bash || return 1
    base_init_export_contract || return 1
    base_init_source_stdlib "$@" || return 1

    add_to_path -p "$BASE_BIN_DIR"
    export PATH
}

base_init_main "$@" || return $?
