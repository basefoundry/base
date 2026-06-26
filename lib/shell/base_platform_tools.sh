# shellcheck shell=bash

# Shared Base Platform Tools detection and PATH helpers for shell startup.
#
# This file is intentionally compatible with both Bash and Zsh startup snippets.
# Do not source base_init.sh from here; ordinary dotfile startup must stay light.

[[ -n "${_base_platform_tools_sourced:-}" ]] && return 0
_base_platform_tools_sourced=1
readonly _base_platform_tools_sourced

base_platform_tools_clear() {
    unset BASE_PLATFORM_TOOLS_HOME BASE_PLATFORM_TOOLS_BIN_DIR
}

base_platform_tools_detect() {
    local base_home="${1:-${BASE_HOME:-}}"
    local workspace_dir
    local candidate_home
    local candidate_bin

    [[ -n "$base_home" ]] || {
        base_platform_tools_clear
        return 1
    }

    workspace_dir="$(cd -- "$base_home/.." && pwd -P)" || {
        base_platform_tools_clear
        return 1
    }
    candidate_home="$workspace_dir/base-platform-tools"
    candidate_bin="$candidate_home/bin"

    [[ -f "$candidate_home/base_manifest.yaml" && -d "$candidate_bin" ]] || {
        base_platform_tools_clear
        return 1
    }

    candidate_home="$(cd -- "$candidate_home" && pwd -P)" || {
        base_platform_tools_clear
        return 1
    }
    candidate_bin="$(cd -- "$candidate_home/bin" && pwd -P)" || {
        base_platform_tools_clear
        return 1
    }

    BASE_PLATFORM_TOOLS_HOME="$candidate_home"
    BASE_PLATFORM_TOOLS_BIN_DIR="$candidate_bin"
    export BASE_PLATFORM_TOOLS_HOME BASE_PLATFORM_TOOLS_BIN_DIR
}

base_platform_tools_path_without_entries() {
    local skip_first="${1:-}"
    local skip_second="${2:-}"
    local skip_third="${3:-}"
    local path_value="${4:-${PATH:-}}"
    local entry
    local remaining="$path_value"
    local new_path=""

    while :; do
        case "$remaining" in
            *:*)
                entry="${remaining%%:*}"
                remaining="${remaining#*:}"
                ;;
            *)
                entry="$remaining"
                remaining=""
                ;;
        esac

        if [[ -n "$entry" && "$entry" != "$skip_first" && "$entry" != "$skip_second" && "$entry" != "$skip_third" ]]; then
            if [[ -n "$new_path" ]]; then
                new_path="$new_path:$entry"
            else
                new_path="$entry"
            fi
        fi

        [[ -n "$remaining" ]] || break
    done

    printf '%s\n' "$new_path"
}

base_platform_tools_set_ordered_path() {
    local base_bin="${1:-}"
    local platform_tools_bin="${2:-}"
    local project_bin="${3:-}"
    local rest_path

    rest_path="$(base_platform_tools_path_without_entries "$base_bin" "$platform_tools_bin" "$project_bin" "${PATH:-}")"

    PATH=""
    if [[ -n "$base_bin" && -d "$base_bin" ]]; then
        PATH="$base_bin"
    fi
    if [[ -n "$platform_tools_bin" && -d "$platform_tools_bin" ]]; then
        PATH="${PATH:+$PATH:}$platform_tools_bin"
    fi
    if [[ -n "$project_bin" && -d "$project_bin" ]]; then
        PATH="${PATH:+$PATH:}$project_bin"
    fi
    if [[ -n "$rest_path" ]]; then
        PATH="${PATH:+$PATH:}$rest_path"
    fi
    export PATH
}
