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
            if (($#)); then
                base_config_usage_error "config path does not accept arguments."
                return $?
            fi
            base_config_path
            ;;
        show|doctor)
            shift
            [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
            BASE_CLI_DISPLAY_COMMAND="basectl config" "$wrapper" --project base base_config "$config_command" "$@"
            ;;
        *)
            base_config_usage_error "Unknown config command '$config_command'."
            return $?
            ;;
    esac
}
