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
  --profile <list>  Install named prerequisite profiles. Known profiles: dev, sre, ai.
  --dry-run          Log what would happen without making changes.
  --manifest <path>  Use a specific base_manifest.yaml path.
  --notify           Force a best-effort macOS notification when setup ends.
  --no-notify        Disable the default best-effort macOS completion notification.
  --recreate-venv    Back up and recreate the project virtual environment.
  -v                 Enable DEBUG logging for this subcommand.
  -h, --help         Show this help text.

Profiles:
  Profile lists are comma-separated, for example: --profile dev,sre.
  dev - Base development tooling for this repository.
  sre - production/SRE prerequisite tooling.
  ai  - AI coding assistant tooling.

Purpose:
  Prepare the local Base CLI environment on macOS.

Setup does:
  1. Install Homebrew if needed.
  2. Install Xcode Command Line Tools if needed.
  3. Install Python 3.13 via Homebrew if needed.
  4. Install prerequisite profiles when --profile is passed.
  5. Create ~/.base.d/base/.venv if it does not already exist.
  6. Install Base Python bootstrap packages into the Base virtual environment.
  7. Invoke the Python project setup layer for base_manifest.yaml artifacts.
  8. Create ~/.base.d/config.yaml with workspace.root: ~/work if missing.

Notes:
  - This command is intentionally idempotent.
  - The optional project argument resolves a Base project from the workspace
    unless --manifest is provided explicitly.
  - Use `basectl check` to verify the same requirements without making changes.
EOF
}

base_setup_subcommand_main() {
    local exit_code
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
            --profile)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--profile' requires an argument."
                    base_setup_subcommand_usage >&2
                    return 2
                fi
                if ! setup_enable_profile_argument "$1"; then
                    print_error "$BASE_SETUP_PROFILE_ERROR"
                    base_setup_subcommand_usage >&2
                    return 2
                fi
                ;;
            --manifest)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--manifest' requires an argument."
                    base_setup_subcommand_usage >&2
                    return 2
                fi
                BASE_SETUP_MANIFEST="$1"
                export BASE_SETUP_MANIFEST
                ;;
            --notify)
                setup_enable_notifications
                ;;
            --no-notify)
                setup_disable_notifications
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
                return 2
                ;;
            *)
                if [[ -n "$project_name" ]]; then
                    print_error "Only one project argument is supported."
                    base_setup_subcommand_usage >&2
                    return 2
                fi
                project_name="$1"
                ;;
        esac
        shift
    done

    BASE_SETUP_PROJECT_NAME="$project_name"
    BASE_SETUP_START_TIME="$(date +%s)"
    export BASE_SETUP_START_TIME
    export BASE_SETUP_PROJECT_NAME
    log_debug "Running 'basectl setup' (DRY_RUN=$(setup_is_dry_run && printf true || printf false))."
    if setup_notifications_enabled; then
        trap 'setup_notify_completion "$?"' EXIT
    fi
    setup_run_install
    exit_code=$?
    if setup_notifications_enabled; then
        trap - EXIT
        setup_notify_completion "$exit_code"
    fi
    return "$exit_code"
}
