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
  basectl setup [options] [project]

Options:
  --dev             Install developer/test dependencies such as BATS and GitHub CLI.
  --dry-run          Log what would happen without making changes.
  --manifest <path>  Use a specific base_manifest.yaml path.
  --recreate-venv    Back up and recreate the project virtual environment.
  -v                 Enable DEBUG logging for this subcommand.
  -h, --help         Show this help text.

Purpose:
  Prepare the local Base CLI environment on macOS.

Setup does:
  1. Install Homebrew if needed.
  2. Install Xcode Command Line Tools if needed.
  3. Install Python 3.13 via Homebrew if needed.
  4. Install BATS and GitHub CLI via Homebrew if --dev is passed.
  5. Create ~/.base.d/base/.venv if it does not already exist.
  6. Install Base Python bootstrap packages into the Base virtual environment.
  7. Invoke the Python project setup layer for base_manifest.yaml artifacts.

Notes:
  - This command is intentionally idempotent.
  - The optional project argument validates project.name in base_manifest.yaml.
  - Use `basectl check` to verify the same requirements without making changes.
EOF
}

base_setup_subcommand_main() {
    local project_name=""

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
            --dev)
                setup_enable_dev_dependencies
                ;;
            --manifest)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--manifest' requires an argument."
                    base_setup_subcommand_usage >&2
                    return 1
                fi
                BASE_SETUP_MANIFEST="$1"
                export BASE_SETUP_MANIFEST
                ;;
            --recreate-venv)
                setup_enable_recreate_venv
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            --*)
                print_error "Unknown option '$1'."
                base_setup_subcommand_usage >&2
                return 1
                ;;
            *)
                if [[ -n "$project_name" ]]; then
                    print_error "Only one project argument is supported."
                    base_setup_subcommand_usage >&2
                    return 1
                fi
                project_name="$1"
                ;;
        esac
        shift
    done

    BASE_SETUP_PROJECT_NAME="$project_name"
    export BASE_SETUP_PROJECT_NAME
    log_debug "Running 'basectl setup' (DRY_RUN=$(setup_is_dry_run && printf true || printf false))."
    setup_run_install
}
