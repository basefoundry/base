#!/usr/bin/env bash

[[ -n "${_base_ci_subcommand_sourced:-}" ]] && return
_base_ci_subcommand_sourced=1
readonly _base_ci_subcommand_sourced

_base_ci_subcommand_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
_base_ci_setup_common_path="$_base_ci_subcommand_dir/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_ci_setup_common_path"

base_ci_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl ci setup <project> [options]
  basectl ci check <project> [options]
  basectl ci doctor <project> [options]

Options:
  --format <text|json>  Select output format. Defaults to text.
  --manifest <path>     Use a specific base_manifest.yaml path.
  --profile <list>      Include named prerequisite profiles. Known profiles: dev, sre, ai.
  --recreate-venv       Back up and recreate the project virtual environment during setup.
  -v                    Enable DEBUG logging for this subcommand.
  -h, --help            Show this help text.

Profiles:
  Profile lists are comma-separated, for example: --profile dev,sre.
  dev - Base development tooling for this repository.
  sre - production/SRE prerequisite tooling.
  ai  - AI coding assistant tooling.

Purpose:
  Run Base setup, checks, and diagnostics in a non-interactive CI environment.
  Sets BASE_CI=true so setup and diagnostic paths can choose CI-safe behavior.
EOF
}

base_ci_usage_error() {
    print_error "$*"
    base_ci_subcommand_usage >&2
    return 2
}

base_ci_apply_environment() {
    export BASE_CI=true
    export CI=true
    export BASE_SETUP_NOTIFY=false
    export BASE_SETUP_ALLOW_SYSTEM_PYTHON=true
    export BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=false
}

base_ci_source_subcommand_module() {
    local module_name="$1"
    local subcommand_script="$_base_ci_subcommand_dir/${module_name}.sh"

    [[ -f "$subcommand_script" ]] || {
        print_error "Subcommand module '$subcommand_script' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$subcommand_script"
}

base_ci_parse_args() {
    local command="$1"
    shift

    BASE_CI_FORMAT="text"
    BASE_CI_MANIFEST=""
    BASE_CI_PROFILE=""
    BASE_CI_PROJECT=""
    BASE_CI_RECREATE_VENV=0
    BASE_CI_VERBOSE=0
    BASE_CI_HELP_REQUESTED=0

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_ci_subcommand_usage
                BASE_CI_HELP_REQUESTED=1
                return 0
                ;;
            --format)
                shift
                [[ -n "${1:-}" ]] || {
                    base_ci_usage_error "Option '--format' requires an argument."
                    return $?
                }
                case "$1" in
                    text|json)
                        BASE_CI_FORMAT="$1"
                        ;;
                    *)
                        base_ci_usage_error "Unsupported ci output format '$1'."
                        return $?
                        ;;
                esac
                ;;
            --manifest)
                shift
                [[ -n "${1:-}" ]] || {
                    base_ci_usage_error "Option '--manifest' requires an argument."
                    return $?
                }
                BASE_CI_MANIFEST="$1"
                ;;
            --profile)
                shift
                [[ -n "${1:-}" ]] || {
                    base_ci_usage_error "Option '--profile' requires an argument."
                    return $?
                }
                BASE_CI_PROFILE="$1"
                ;;
            --recreate-venv)
                [[ "$command" == setup ]] || {
                    base_ci_usage_error "Option '--recreate-venv' is only supported for 'ci setup'."
                    return $?
                }
                BASE_CI_RECREATE_VENV=1
                ;;
            -v)
                BASE_CI_VERBOSE=1
                ;;
            -*)
                base_ci_usage_error "Unknown ci $command option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$BASE_CI_PROJECT" ]]; then
                    base_ci_usage_error "The 'ci $command' command accepts exactly one project name."
                    return $?
                fi
                BASE_CI_PROJECT="$1"
                ;;
        esac
        shift
    done

    [[ -n "$BASE_CI_PROJECT" ]] || {
        base_ci_usage_error "The 'ci $command' command requires a project name."
        return $?
    }
}

base_ci_common_delegate_args() {
    if [[ -n "$BASE_CI_PROFILE" ]]; then
        printf '%s\n' --profile "$BASE_CI_PROFILE"
    fi
    if [[ -n "$BASE_CI_MANIFEST" ]]; then
        printf '%s\n' --manifest "$BASE_CI_MANIFEST"
    fi
    if ((BASE_CI_VERBOSE)); then
        printf '%s\n' -v
    fi
}

base_ci_setup_delegate_args() {
    base_ci_common_delegate_args
    if ((BASE_CI_RECREATE_VENV)); then
        printf '%s\n' --recreate-venv
    fi
    printf '%s\n' "$BASE_CI_PROJECT"
}

base_ci_check_or_doctor_delegate_args() {
    base_ci_common_delegate_args
    printf '%s\n' "$BASE_CI_PROJECT" --format "$BASE_CI_FORMAT"
}

base_ci_print_setup_json() {
    local exit_code="$1"
    local stdout_file="$2"
    local stderr_file="$3"
    local python_bin

    python_bin="$(setup_diagnostics_python_bin)" ||
        fatal_error "Python is required to render Base CI setup JSON."
    setup_ensure_cached_paths
    env BASE_HOME="$BASE_HOME" PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
        "$python_bin" -m base_setup.ci_json setup-json \
        --project "$BASE_CI_PROJECT" \
        --exit-code "$exit_code" \
        --stdout-file "$stdout_file" \
        --stderr-file "$stderr_file"
}

base_ci_run_setup_json() {
    local args=("$@")
    local stdout_file
    local stderr_file
    local exit_code
    local render_status

    stdout_file="$(mktemp "${TMPDIR:-/tmp}/base-ci-setup-stdout.XXXXXX")" || return 1
    stderr_file="$(mktemp "${TMPDIR:-/tmp}/base-ci-setup-stderr.XXXXXX")" || {
        rm -f "$stdout_file"
        return 1
    }

    base_setup_subcommand_main "${args[@]}" > "$stdout_file" 2> "$stderr_file"
    exit_code=$?

    if [[ -s "$stdout_file" ]]; then
        cat "$stdout_file" >&2
    fi
    if [[ -s "$stderr_file" ]]; then
        cat "$stderr_file" >&2
    fi

    base_ci_print_setup_json "$exit_code" "$stdout_file" "$stderr_file"
    render_status=$?
    rm -f "$stdout_file" "$stderr_file"
    if ((render_status)); then
        return "$render_status"
    fi
    return "$exit_code"
}

base_ci_run_setup() {
    local args=()

    mapfile -t args < <(base_ci_setup_delegate_args)
    base_ci_source_subcommand_module setup || return 1

    if [[ "$BASE_CI_FORMAT" == json ]]; then
        base_ci_run_setup_json "${args[@]}"
        return $?
    fi

    base_setup_subcommand_main "${args[@]}"
}

base_ci_run_check() {
    local args=()

    mapfile -t args < <(base_ci_check_or_doctor_delegate_args)
    base_ci_source_subcommand_module check || return 1
    base_check_subcommand_main "${args[@]}"
}

base_ci_run_doctor() {
    local args=()

    mapfile -t args < <(base_ci_check_or_doctor_delegate_args)
    base_ci_source_subcommand_module doctor || return 1
    base_doctor_subcommand_main "${args[@]}"
}

base_ci_subcommand_main() {
    local command="${1:-}"
    local parse_status

    case "$command" in
        -h|--help|help)
            base_ci_subcommand_usage
            return 0
            ;;
        "")
            base_ci_usage_error "CI command is required."
            return $?
            ;;
        setup|check|doctor)
            shift
            base_ci_parse_args "$command" "$@"
            parse_status=$?
            if ((parse_status != 0)); then
                return "$parse_status"
            fi
            if ((BASE_CI_HELP_REQUESTED)); then
                    return 0
            fi
            ;;
        *)
            base_ci_usage_error "Unknown ci command '$command'."
            return $?
            ;;
    esac

    base_ci_apply_environment
    case "$command" in
        setup)
            base_ci_run_setup
            ;;
        check)
            base_ci_run_check
            ;;
        doctor)
            base_ci_run_doctor
            ;;
    esac
}
