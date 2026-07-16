#!/usr/bin/env bash

[[ -n "${_base_config_subcommand_sourced:-}" ]] && return 0
_base_config_subcommand_sourced=1
readonly _base_config_subcommand_sourced

base_config_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl config path
  basectl config show
  basectl config doctor

Purpose:
  Inspect Base's machine-local user config.

Notes:
  - The default config path is ~/.base.d/config.yaml.
  - config show redacts secret-shaped keys and URL credentials.
  - Missing config is treated as an empty config.
  - Base does not edit or sync this file.
EOF
}

base_config_leaf_usage() {
    local config_command="$1"

    case "$config_command" in
        path)
            cat <<'EOF'
Usage:
  basectl config path

Purpose:
  Print Base's machine-local user config path.

Options:
  -h, --help  Show this help text.
EOF
            ;;
        show)
            cat <<'EOF'
Usage:
  basectl config show

Purpose:
  Show Base's machine-local user config as redacted JSON.

Options:
  -h, --help  Show this help text.
EOF
            ;;
        doctor)
            cat <<'EOF'
Usage:
  basectl config doctor

Purpose:
  Diagnose Base's machine-local user config.

Options:
  -h, --help  Show this help text.
EOF
            ;;
        *)
            return 1
            ;;
    esac
}

base_config_args_request_help() {
    local arg

    for arg in "$@"; do
        case "$arg" in
            -h|--help) return 0 ;;
        esac
    done
    return 1
}

base_config_path() {
    [[ -n "${HOME:-}" ]] || fatal_error "Environment variable 'HOME' is not set."
    printf '%s\n' "$HOME/.base.d/config.yaml"
}

base_config_usage_error() {
    print_error "$*"
    printf "Run 'basectl config --help' for usage.\n" >&2
    return 2
}

base_config_subcommand_main() {
    local config_command="${1:-}"
    local wrapper="$BASE_HOME/bin/base-wrapper"

    case "$config_command" in
        ""|-h|--help|help)
            base_config_subcommand_usage
            return 0
            ;;
        path)
            shift
            if base_config_args_request_help "$@"; then
                base_config_leaf_usage path
                return $?
            fi
            if (($#)); then
                base_config_usage_error "config path does not accept arguments."
                return $?
            fi
            base_config_path
            ;;
        show|doctor)
            shift
            if base_config_args_request_help "$@"; then
                base_config_leaf_usage "$config_command"
                return $?
            fi
            [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
            BASE_CLI_DISPLAY_COMMAND="basectl config" "$wrapper" --project base base_config "$config_command" "$@"
            ;;
        *)
            base_config_usage_error "Unknown config command '$config_command'."
            return $?
            ;;
    esac
}
