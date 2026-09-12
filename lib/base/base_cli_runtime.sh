#!/usr/bin/env bash

# Resolve the Python base_cli provider for Base launchers and tests.
#
# The final extraction contract is:
#   1. BASE_CLI_SOURCE_DIR, when explicitly supplied;
#   2. a sibling base-cli checkout;
#   3. an installed base-cli distribution in the selected Python environment.
# The resolver functions accept an optional Base root for callers that need to
# locate a sibling checkout while BASE_HOME is intentionally unset.
#
base_cli_runtime_source_root() {
    local base_home="${1:-${BASE_HOME:-}}"
    local explicit_root="${BASE_CLI_SOURCE_DIR:-}"
    local sibling_repo="${base_home:+$base_home/../base-cli}"
    local sibling_root="$sibling_repo/lib/python"

    if [[ -n "$explicit_root" ]]; then
        [[ -f "$explicit_root/base_cli/__init__.py" ]] || {
            printf "ERROR: BASE_CLI_SOURCE_DIR '%s' does not contain base_cli/__init__.py.\n" "$explicit_root" >&2
            return 1
        }
        printf '%s\n' "$explicit_root"
        return 0
    fi

    if [[ -d "$sibling_repo" ]]; then
        [[ -f "$sibling_root/base_cli/__init__.py" ]] || {
            printf "ERROR: sibling base-cli checkout '%s' is missing lib/python/base_cli/__init__.py.\n" "$sibling_repo" >&2
            return 1
        }
        printf '%s\n' "$sibling_root"
        return 0
    fi

    # An empty result deliberately leaves base_cli to normal site-package
    # resolution in the selected Python environment.
    return 0
}

base_cli_runtime_source_kind() {
    local base_home="${1:-${BASE_HOME:-}}"
    local explicit_root="${BASE_CLI_SOURCE_DIR:-}"
    local sibling_repo="${base_home:+$base_home/../base-cli}"
    local sibling_root="$sibling_repo/lib/python"

    if [[ -n "$explicit_root" ]]; then
        [[ -f "$explicit_root/base_cli/__init__.py" ]] || return 1
        printf 'explicit\n'
    elif [[ -d "$sibling_repo" ]]; then
        [[ -f "$sibling_root/base_cli/__init__.py" ]] || return 1
        printf 'sibling\n'
    else
        printf 'pip\n'
    fi
}

base_cli_runtime_prepare() {
    local source_kind source_root

    source_kind="$(base_cli_runtime_source_kind "$@")" || return 1
    source_root="$(base_cli_runtime_source_root "$@")" || return 1
    export BASE_CLI_SOURCE="$source_kind"
    export BASE_CLI_RUNTIME_SOURCE_ROOT="$source_root"
}
