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

Purpose:
  Run Base setup, checks, and diagnostics in a non-interactive CI environment.
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

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_ci_subcommand_usage
                return 10
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
    local command_output="$1"
    local exit_code="$2"
    local status="ok"

    if ((exit_code)); then
        status="error"
    fi

    printf '{\n'
    printf '  "schema_version": 1,\n'
    printf '  "command": "setup",\n'
    printf '  "status": "%s",\n' "$status"
    printf '  "project": "%s",\n' "$(setup_json_escape "$BASE_CI_PROJECT")"
    printf '  "output": "%s"\n' "$(setup_json_escape "$command_output")"
    printf '}\n'
}

base_ci_run_setup() {
    local args=()
    local command_output
    local exit_code

    mapfile -t args < <(base_ci_setup_delegate_args)
    base_ci_source_subcommand_module setup || return 1

    if [[ "$BASE_CI_FORMAT" == json ]]; then
        command_output="$(base_setup_subcommand_main "${args[@]}" 2>&1)"
        exit_code=$?
        base_ci_print_setup_json "$command_output" "$exit_code"
        return "$exit_code"
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
            case "$parse_status" in
                0)
                    ;;
                10)
                    return 0
                    ;;
                *)
                    return "$parse_status"
                    ;;
            esac
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
