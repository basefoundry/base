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
    local output_lines=()
    local index

    shift 2
    output_lines=("$@")

    if ((exit_code)); then
        status="error"
    fi

    printf '{\n'
    printf '  "schema_version": 1,\n'
    printf '  "command": "setup",\n'
    printf '  "status": "%s",\n' "$status"
    printf '  "project": "%s",\n' "$(setup_json_escape "$BASE_CI_PROJECT")"
    printf '  "output": "%s"' "$(setup_json_escape "$command_output")"
    if ((exit_code)) && ((${#output_lines[@]})); then
        printf ',\n'
        printf '  "output_lines": [\n'
        for index in "${!output_lines[@]}"; do
            printf '    "%s"' "$(setup_json_escape "${output_lines[$index]}")"
            if ((index < ${#output_lines[@]} - 1)); then
                printf ','
            fi
            printf '\n'
        done
        printf '  ]\n'
    else
        printf '\n'
    fi
    printf '}\n'
}

base_ci_compact_setup_output_lines() {
    local output_file="$1"
    local line
    local message

    [[ -f "$output_file" ]] || return 0
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -n "$line" ]] || continue
        if [[ "$line" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]][0-9]{2}:[0-9]{2}:[0-9]{2}[[:space:]][A-Z]+[[:space:]]+[^[:space:]]+[[:space:]]+(.*)$ ]]; then
            message="${BASH_REMATCH[1]}"
        else
            message="$line"
        fi
        printf '%s\n' "$message"
    done < "$output_file"
}

base_ci_compact_setup_output() {
    local output_file="$1"
    local line
    local message=""

    while IFS= read -r line || [[ -n "$line" ]]; do
        message="$line"
    done < <(base_ci_compact_setup_output_lines "$output_file")

    printf '%s\n' "$message"
}

base_ci_run_setup_json() {
    local args=("$@")
    local stdout_file
    local stderr_file
    local command_output
    local exit_code
    local output_lines=()
    local output_source_file

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

    command_output="$(base_ci_compact_setup_output "$stderr_file")"
    output_source_file="$stderr_file"
    if [[ -z "$command_output" ]]; then
        command_output="$(base_ci_compact_setup_output "$stdout_file")"
        output_source_file="$stdout_file"
    fi
    if ((exit_code)); then
        mapfile -t output_lines < <(base_ci_compact_setup_output_lines "$output_source_file")
    fi

    rm -f "$stdout_file" "$stderr_file"
    base_ci_print_setup_json "$command_output" "$exit_code" "${output_lines[@]}"
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
