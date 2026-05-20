#!/usr/bin/env bash

[[ -n "${_base_update_profile_subcommand_sourced:-}" ]] && return
_base_update_profile_subcommand_sourced=1
readonly _base_update_profile_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_update_profile_subcommand_usage() {
    cat <<'EOF'
Usage:
  base update-profile [options]

Options:
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Reserved for future shell profile updates managed by Base.
EOF
}

base_update_profile_subcommand_main() {
    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_update_profile_subcommand_usage
                return 0
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            *)
                print_error "Unknown option '$1'."
                base_update_profile_subcommand_usage >&2
                return 1
                ;;
        esac
        shift
    done

    log_debug "Running 'base update-profile'."
    setup_run_update_profile
}
