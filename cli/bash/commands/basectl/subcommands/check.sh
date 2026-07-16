#!/usr/bin/env bash

[[ -n "${_base_check_subcommand_sourced:-}" ]] && return 0
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
  --ci                  Run checks with CI-safe defaults.
  --profile <list>      Include named prerequisite profiles. Known profiles: dev, sre, ai, linux-lab.
  --format <text|json>  Select output format. Defaults to text.
  --manifest <path>     Use a specific base_manifest.yaml path for project checks.
  --remote-network      Opt in to bounded project Git origin reachability checks.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.

Profiles:
  Profile lists are comma-separated, for example: --profile dev,sre.
  dev       - Base development tooling for this repository.
  sre       - production/SRE prerequisite tooling.
  ai        - AI coding assistant tooling.
  linux-lab - Multipass tooling for local Ubuntu lab VMs on macOS hosts.

Purpose:
  Verify the local Base CLI environment and, when provided, project artifacts on supported platforms without making changes.
  Use check for a quick pass/fail result; use doctor for finding IDs and fix hints.

See also:
  basectl doctor [project] [options]
  basectl ci check [project] [options]  Compatibility alias for check --ci.

Check does:
  1. Verify platform-specific runtime prerequisites.
  2. On macOS, verify Homebrew, Xcode Command Line Tools, and Homebrew Python.
  3. On Ubuntu/Debian Linux, verify system python3 is available.
  4. Verify ~/.base.d/base/.venv is healthy.
  5. Verify prerequisite profiles when --profile is passed.
  6. Verify project manifest artifacts when a project name is passed.
  7. Record the latest project check result under ~/.base.d/<project>/checks/last.json.
EOF
}

base_check_usage_error() {
    print_error "$*"
    printf "Run 'basectl check --help' for usage.\n" >&2
    return 2
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
            --ci)
                setup_enable_ci_mode
                ;;
            --format)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_check_usage_error "Option '--format' requires an argument."
                    return $?
                fi
                case "$1" in
                    text|json)
                        output_format="$1"
                        ;;
                    *)
                        base_check_usage_error "Unsupported check output format '$1'."
                        return $?
                        ;;
                esac
                ;;
            --profile)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_check_usage_error "Option '--profile' requires an argument."
                    return $?
                fi
                if ! setup_enable_profile_argument "$1"; then
                    base_check_usage_error "$BASE_SETUP_PROFILE_ERROR"
                    return $?
                fi
                ;;
            --manifest)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_check_usage_error "Option '--manifest' requires an argument."
                    return $?
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
                    base_check_usage_error "Unknown option '$1'."
                    return $?
                fi
                if [[ -n "$project" ]]; then
                    base_check_usage_error "The 'check' command accepts at most one project name."
                    return $?
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
        BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_run_check_json "$remote_network"
    else
        setup_print_runtime_chain_summary
        BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_run_check
    fi
}
