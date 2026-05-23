#!/usr/bin/env bash

[[ -n "${_base_setup_subcommand_sourced:-}" ]] && return
_base_setup_subcommand_sourced=1
readonly _base_setup_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_setup_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl setup [options]

Options:
  --dry-run   Log what would happen without making changes.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Prepare the local Base CLI environment on macOS.

Setup does:
  1. Install Homebrew if needed.
  2. Install Xcode Command Line Tools if needed.
  3. Install Python 3.13 via Homebrew if needed.
  4. Install BATS via Homebrew if needed.
  5. Create ~/.base.d/.venv if it does not already exist.

Notes:
  - This command is intentionally idempotent.
  - Use `basectl check` to verify the same requirements without making changes.
EOF
}

base_setup_subcommand_main() {
    setup_clear_run_state

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_setup_subcommand_usage
                return 0
                ;;
            --dry-run)
                setup_enable_dry_run
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            *)
                print_error "Unknown option '$1'."
                base_setup_subcommand_usage >&2
                return 1
                ;;
        esac
        shift
    done

    log_debug "Running 'basectl setup' (dry_run=${dry_run:-false})."
    setup_run_install
}
