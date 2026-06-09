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
  basectl check [project] [options]

Options:
  --profile <list>      Include named prerequisite profiles. Known profiles: dev, sre, ai.
  --format <text|json>  Select output format. Defaults to text.
  --manifest <path>     Use a specific base_manifest.yaml path for project checks.
  --remote-network      Opt in to bounded project Git origin reachability checks.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.

Purpose:
  Verify the local Base CLI environment and, when provided, project artifacts on macOS without making changes.

Check does:
  1. Verify Homebrew is installed.
  2. Verify Xcode Command Line Tools are installed.
  3. Verify Python 3.13 is installed via Homebrew.
  4. Verify ~/.base.d/base/.venv is healthy.
  5. Verify prerequisite profiles when --profile is passed.
  6. Verify project manifest artifacts when a project name is passed.
EOF
}

base_check_subcommand_main() {
    local output_format="text"
    local project=""
    local remote_network=false

    setup_clear_run_state

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_check_subcommand_usage
                return 0
                ;;
            --format)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--format' requires an argument."
                    base_check_subcommand_usage >&2
                    return 1
                fi
                case "$1" in
                    text|json)
                        output_format="$1"
                        ;;
                    *)
                        print_error "Unsupported check output format '$1'."
                        base_check_subcommand_usage >&2
                        return 1
                        ;;
                esac
                ;;
            --profile)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--profile' requires an argument."
                    base_check_subcommand_usage >&2
                    return 1
                fi
                if ! setup_enable_profile_argument "$1"; then
                    print_error "$BASE_SETUP_PROFILE_ERROR"
                    base_check_subcommand_usage >&2
                    return 1
                fi
                ;;
            --manifest)
                shift
                if [[ -z "${1:-}" ]]; then
                    print_error "Option '--manifest' requires an argument."
                    base_check_subcommand_usage >&2
                    return 1
                fi
                BASE_SETUP_MANIFEST="$1"
                export BASE_SETUP_MANIFEST
                ;;
            --remote-network)
                remote_network=true
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            *)
                if [[ "$1" == -* ]]; then
                    print_error "Unknown option '$1'."
                    base_check_subcommand_usage >&2
                    return 1
                fi
                if [[ -n "$project" ]]; then
                    print_error "The 'check' command accepts at most one project name."
                    base_check_subcommand_usage >&2
                    return 1
                fi
                project="$1"
                ;;
        esac
        shift
    done

    BASE_SETUP_PROJECT_NAME="$project"
    BASE_SETUP_REMOTE_NETWORK="$remote_network"
    export BASE_SETUP_PROJECT_NAME
    export BASE_SETUP_REMOTE_NETWORK
    log_debug "Running 'basectl check'."
    if [[ "$output_format" == json ]]; then
        setup_run_check_json "$remote_network"
    else
        setup_run_check
    fi
}
