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

Description:
  Check whether the local Base CLI environment is ready. With no project or
  --manifest, the command checks only the Base environment. Pass a project or
  --manifest to also check that project's manifest-declared requirements.

  Check does not install or repair prerequisites, modify project files, or run
  project tests. Project runtime checks remain unverified by default.

Arguments:
  project               Select a Base project by name. Omit it for a Base-only
                        check; --manifest can select the project instead.

Options:
  --ci                  Use noninteractive CI-safe checks. Does not select JSON
                        output or run project tests.
  --profile <list>      Also check the named prerequisite profiles.
  --format <text|json>  Print human-readable text or structured JSON.
                        Defaults to text.
  --manifest <path>     Use this base_manifest.yaml for project checks. When
                        project is omitted, infer it from manifest project.name.
  --verify-project-runtime
                        Authorize execution of reviewed project runtimes and tool
                        configuration for this invocation.
  --remote-network      Also run a bounded Git origin reachability check.
                        Off by default; requires project or --manifest.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.

Profiles:
  Profile lists are comma-separated, for example: --profile dev,sre.
  dev       - Base development tooling for this repository.
  sre       - production/SRE prerequisite tooling.
  ai        - AI coding assistant tooling.
  linux-lab - Multipass tooling for local Ubuntu lab VMs on macOS hosts.

Examples:
  # Check only the Base CLI environment.
  basectl check

  # Also check a project and its manifest-declared requirements.
  basectl check base-demo

  # Include multiple prerequisite profiles.
  basectl check --profile dev,sre

  # Produce structured output with CI-safe defaults.
  basectl check --ci base-demo --format json

  # Select a project directly from its manifest.
  basectl check --manifest ./base_manifest.yaml

  # Opt in to bounded Git origin reachability.
  basectl check base-demo --remote-network

Results:
  Text output is human-readable. JSON output includes the aggregate status and
  stable finding IDs for automation.

  Clean and warning-only results exit 0. Blocking findings exit 1. Invalid
  command usage exits 2.

  Normal runs write Base runtime logs and command history to the local cache.
  Project checks also record their latest result under
  ~/.base.d/<project>/checks/last.json.

See also:
  basectl setup [options] [project]   Install or repair prerequisites.
  basectl doctor [project] [options]  Explain findings and provide fix guidance.
  basectl test [project] [options]    Run the project-declared test command.
EOF
}

base_check_usage_error() {
    base_std_print_error "$*"
    printf "Run 'basectl check --help' for usage.\n" >&2
    return 2
}

base_check_subcommand_main() {
    local output_format="text"
    local project=""
    local remote_network=false verify_project_runtime=false

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
            --verify-project-runtime)
                verify_project_runtime=true
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

    if [[ "$remote_network" == true && -z "$project" && -z "${BASE_SETUP_MANIFEST:-}" ]]; then
        base_check_usage_error "Option '--remote-network' requires a project or '--manifest <path>'."
        return $?
    fi
    if [[ "$verify_project_runtime" == true && -z "$project" && -z "${BASE_SETUP_MANIFEST:-}" ]]; then
        base_check_usage_error "Option '--verify-project-runtime' requires a project or '--manifest <path>'."
        return $?
    fi
    BASE_SETUP_VERIFY_PROJECT_RUNTIME="$verify_project_runtime"
    export BASE_SETUP_VERIFY_PROJECT_RUNTIME
    BASE_SETUP_PROJECT_NAME="$project"
    BASE_SETUP_REMOTE_NETWORK="$remote_network"
    export BASE_SETUP_PROJECT_NAME
    export BASE_SETUP_REMOTE_NETWORK
    base_std_log_debug "Running 'basectl check'."
    if [[ "$output_format" == json ]]; then
        BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_run_check_json "$remote_network"
    else
        setup_print_runtime_chain_summary
        BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS=true setup_run_check
    fi
}
