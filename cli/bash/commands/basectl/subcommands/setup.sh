#!/usr/bin/env bash

[[ -n "${_base_setup_subcommand_sourced:-}" ]] && return 0
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
  --ci              Run setup with CI-safe defaults.
  --format <text|json>
                    Select setup output format when --ci is used. Defaults to text.
  --profile <list>  Install named prerequisite profiles. Known profiles: dev, sre, ai, linux-lab.
  --dry-run          Log what would happen without making changes.
  --manifest <path>  Use a specific base_manifest.yaml path.
  --notify           Force a best-effort macOS notification when setup ends.
  --no-notify        Disable the default best-effort macOS completion notification.
  --recreate-venv    Back up and recreate the project virtual environment.
  --yes              Apply setup changes that require explicit confirmation.
  -v                 Enable DEBUG logging for this subcommand.
  -h, --help         Show this help text.

Profiles:
  Profile lists are comma-separated, for example: --profile dev,sre.
  dev       - Base development tooling for this repository.
  sre       - production/SRE prerequisite tooling.
  ai        - AI coding assistant tooling.
  linux-lab - Multipass tooling for local Ubuntu lab VMs on macOS hosts.

Purpose:
  Prepare the local Base CLI environment on supported setup platforms.

Setup does:
  1. Install or verify macOS prerequisites on macOS.
  2. Install or verify apt prerequisites on Ubuntu/Debian Linux with interactive consent or --yes.
  3. Install prerequisite profiles when --profile is passed.
  4. Create ~/.base.d/base/.venv if it does not already exist.
  5. Install Base Python bootstrap packages into the Base virtual environment.
  6. Invoke the Python project setup layer for base_manifest.yaml artifacts.
  7. Create ~/.base.d/config.yaml with workspace.root: ~/work if missing.

Notes:
  - This command is intentionally idempotent.
  - Use --ci for non-interactive CI-safe setup. The legacy
    `basectl ci setup` command remains as a compatibility alias.
  - On Ubuntu/Debian Linux, setup can install apt prerequisites with
    interactive consent or --yes.
  - The optional project argument resolves a Base project from the workspace
    unless --manifest is provided explicitly.
  - Use `basectl check` to verify the same requirements without making changes.
EOF
}

base_setup_usage_error() {
    print_error "$*"
    printf "Run 'basectl setup --help' for usage.\n" >&2
    return 2
}

base_setup_print_ci_json() {
    local exit_code="$1"
    local stdout_file="$2"
    local stderr_file="$3"
    local python_bin

    python_bin="$(setup_diagnostics_python_bin)" ||
        fatal_error "Python is required to render Base CI setup JSON."
    setup_ensure_cached_paths
    env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
        "$python_bin" -m base_setup.ci_json setup-json \
        --project "${BASE_SETUP_PROJECT_NAME:-}" \
        --exit-code "$exit_code" \
        --stdout-file "$stdout_file" \
        --stderr-file "$stderr_file"
}

base_setup_run_text() {
    local exit_code

    BASE_SETUP_START_TIME="$(setup_epoch_seconds)" || BASE_SETUP_START_TIME=0
    export BASE_SETUP_START_TIME
    log_debug "Running 'basectl setup' (DRY_RUN=$(setup_is_dry_run && printf true || printf false))."
    if setup_notifications_enabled; then
        trap 'setup_notify_completion "$?"' EXIT
    fi
    setup_print_runtime_chain_summary
    setup_run_install
    exit_code=$?
    if setup_notifications_enabled; then
        trap - EXIT
        setup_notify_completion "$exit_code"
    fi
    return "$exit_code"
}

base_setup_run_ci_json() {
    local stdout_file
    local stderr_file
    local exit_code
    local render_status

    std_make_temp_file stdout_file base-ci-setup-stdout || return 1
    std_make_temp_file stderr_file base-ci-setup-stderr || return 1

    base_setup_run_text > "$stdout_file" 2> "$stderr_file"
    exit_code=$?

    # Keep JSON as stdout-only; replay setup logs to stderr for CI visibility.
    if [[ -s "$stdout_file" ]]; then
        cat "$stdout_file" >&2
    fi
    if [[ -s "$stderr_file" ]]; then
        cat "$stderr_file" >&2
    fi

    base_setup_print_ci_json "$exit_code" "$stdout_file" "$stderr_file"
    render_status=$?
    rm -f "$stdout_file" "$stderr_file"
    if ((render_status)); then
        return "$render_status"
    fi
    return "$exit_code"
}

base_setup_subcommand_main() {
    local ci_mode=false format_requested=false output_format="text"
    local project_name=""

    setup_clear_run_state

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_setup_subcommand_usage
                return 0
                ;;
            --ci)
                ci_mode=true
                setup_enable_ci_mode
                ;;
            --format)
                format_requested=true
                shift
                if [[ -z "${1:-}" ]]; then
                    base_setup_usage_error "Option '--format' requires an argument."
                    return $?
                fi
                case "$1" in
                    text|json)
                        output_format="$1"
                        ;;
                    *)
                        base_setup_usage_error "Unsupported setup output format '$1'."
                        return $?
                        ;;
                esac
                ;;
            --dry-run)
                setup_enable_dry_run
                ;;
            --yes)
                setup_enable_yes
                ;;
            --profile)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_setup_usage_error "Option '--profile' requires an argument."
                    return $?
                fi
                if ! setup_enable_profile_argument "$1"; then
                    base_setup_usage_error "$BASE_SETUP_PROFILE_ERROR"
                    return $?
                fi
                ;;
            --manifest)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_setup_usage_error "Option '--manifest' requires an argument."
                    return $?
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
                base_setup_usage_error "Unknown option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$project_name" ]]; then
                    base_setup_usage_error "Only one project argument is supported."
                    return $?
                fi
                project_name="$1"
                ;;
        esac
        shift
    done

    if [[ "$format_requested" == true && "$ci_mode" != true ]]; then
        base_setup_usage_error "Option '--format' is only supported when '--ci' is passed."
        return $?
    fi

    BASE_SETUP_PROJECT_NAME="$project_name"
    export BASE_SETUP_PROJECT_NAME
    if [[ "$ci_mode" == true && "$output_format" == json ]]; then
        base_setup_run_ci_json
        return $?
    fi
    base_setup_run_text
}
