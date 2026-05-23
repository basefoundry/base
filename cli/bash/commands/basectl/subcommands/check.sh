#!/usr/bin/env bash

[[ -n "${_base_check_subcommand_sourced:-}" ]] && return
_base_check_subcommand_sourced=1
readonly _base_check_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_check_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl check [options]

Options:
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Verify the local Base CLI environment on macOS without making changes.

Check does:
  1. Verify Homebrew is installed.
  2. Verify Xcode Command Line Tools are installed.
  3. Verify Python 3.13 is installed via Homebrew.
  4. Verify BATS is installed via Homebrew.
  5. Verify ~/.base.d/.venv exists.
EOF
}

base_check_subcommand_main() {
    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_check_subcommand_usage
                return 0
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            *)
                print_error "Unknown option '$1'."
                base_check_subcommand_usage >&2
                return 1
                ;;
        esac
        shift
    done

    log_debug "Running 'basectl check'."
    setup_run_check
}
