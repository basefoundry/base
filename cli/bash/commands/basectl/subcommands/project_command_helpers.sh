#!/usr/bin/env bash

[[ -n "${_base_project_command_helpers_sourced:-}" ]] && return 0
_base_project_command_helpers_sourced=1
readonly _base_project_command_helpers_sourced

base_project_venv_override_applies() {
    local project="$1"

    [[ -n "${BASE_PROJECT_VENV_DIR:-}" ]] || return 1
    [[ -z "${BASE_PROJECT:-}" || "${BASE_PROJECT:-}" == "$project" ]]
}

base_project_venv_dir() {
    local project="$1"
    local project_root="${2:-}"
    local route_venv_dir="${3:-}"

    if base_project_venv_override_applies "$project"; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi

    if [[ -n "$route_venv_dir" ]]; then
        printf '%s\n' "$route_venv_dir"
        return 0
    fi

    if [[ "$project" != base && -n "$project_root" ]]; then
        printf '%s\n' "$project_root/.venv"
        return 0
    fi

    printf '%s\n' "$HOME/.base.d/$project/.venv"
}

base_project_set_history_context() {
    export BASE_CLI_HISTORY_PROJECT="$1"
    export BASE_CLI_HISTORY_PROJECT_ROOT="$2"
    export BASE_CLI_HISTORY_MANIFEST="$3"
}

base_project_venv_uses_project_local_default() {
    local project="$1"
    local project_root="${2:-}"
    local venv_dir="${3:-}"

    [[ "$project" != base && -n "$project_root" && "$venv_dir" == "$project_root/.venv" ]]
}

base_project_venv_fix() {
    local project="$1"
    local project_root="${2:-}"
    local venv_dir="${3:-}"
    local uses_uv_manager="${4:-false}"

    if ! base_project_venv_override_applies "$project" && [[ "$uses_uv_manager" == true ]]; then
        printf "Run 'uv sync' in '%s' first." "$project_root"
        return 0
    fi
    if ! base_project_venv_override_applies "$project" && base_project_venv_uses_project_local_default "$project" "$project_root" "$venv_dir"; then
        printf "Run 'basectl setup %s' first. To keep using an external Base-managed virtual environment, set python.venv_location: external in base_manifest.yaml or export BASE_PROJECT_VENV_DIR." "$project"
        return 0
    fi
    printf "Run 'basectl setup %s' first." "$project"
}

base_project_require_manifest_command_trust() {
    local project="$1"
    local manifest_path="$2"
    local trust_required="${3:-false}"
    local wrapper="$BASE_HOME/bin/base-wrapper"

    [[ "$trust_required" == true ]] || return 0
    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    "$wrapper" --project base base_trust require "$project" --manifest "$manifest_path"
}

base_project_command_parse_args() {
    local command_name="$1"
    local usage_function="$2"
    local usage_error_function="$3"
    local positional_error="$4"
    shift 4

    local project="" explicit_project="" dry_run=0
    local positional_count=0
    local args=() extra_args=() parser_args=() positionals=()
    # shellcheck disable=SC2034 # base_arg_parse reads the caller-owned option specification by name.
    local -a option_specs=(
        "debug|flag|-v"
        "workspace|value|--workspace"
        "project|value|--project"
        "dry_run|flag|--dry-run"
    )
    local -A parsed_options=()

    # shellcheck disable=SC2034 # The selected project is consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_PROJECT=""
    # shellcheck disable=SC2034 # These shared parse outputs are consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_DRY_RUN=0
    # shellcheck disable=SC2034 # The parser returns help to its caller without resolving a project.
    BASE_PROJECT_COMMAND_HELP_SHOWN=0
    BASE_PROJECT_COMMAND_ARGUMENTS=()
    # shellcheck disable=SC2034 # Passthrough arguments are consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_EXTRA_ARGS=()
    BASE_PROJECT_COMMAND_SELECTION_ARGS=()

    while (($#)); do
        case "$1" in
            --)
                shift
                extra_args=("$@")
                break
                ;;
            -h|--help|help)
                # shellcheck disable=SC2034 # The caller must skip resolution after help is printed.
                BASE_PROJECT_COMMAND_HELP_SHOWN=1
                "$usage_function"
                return 0
                ;;
            -v)
                parser_args+=("$1")
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    "$usage_error_function" "Option '--workspace' requires an argument."
                    return $?
                }
                parser_args+=("--workspace=$2")
                args+=(--workspace "$2")
                shift 2
                ;;
            --workspace=*)
                parser_args+=("$1")
                args+=("$1")
                shift
                ;;
            --project)
                [[ -n "${2:-}" ]] || {
                    "$usage_error_function" "Option '--project' requires an argument."
                    return $?
                }
                [[ -z "$explicit_project" ]] || {
                    "$usage_error_function" "Option '--project' may be specified only once."
                    return $?
                }
                explicit_project="$2"
                parser_args+=("--project=$2")
                shift 2
                ;;
            --dry-run)
                parser_args+=("$1")
                shift
                ;;
            -*)
                "$usage_error_function" "Unknown $command_name option '$1'."
                return $?
                ;;
            *)
                positional_count=$((positional_count + 1))
                if ((positional_count > 1)); then
                    "$usage_error_function" "$positional_error"
                    return $?
                fi
                parser_args+=("$1")
                shift
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        "$usage_error_function" "Could not parse $command_name arguments."
        return $?
    fi

    if ((${#positionals[@]} > 1)); then
        "$usage_error_function" "$positional_error"
        return $?
    fi
    if ((${#positionals[@]} == 1)); then
        project="${positionals[0]}"
    fi

    explicit_project="${parsed_options[project]:-}"
    dry_run="${parsed_options[dry_run]:-0}"
    [[ -z "$explicit_project" || -z "$project" ]] || {
        "$usage_error_function" "The '$command_name' command does not accept a positional project with --project."
        return $?
    }

    # shellcheck disable=SC2034 # The selected project is consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_PROJECT="$project"
    # shellcheck disable=SC2034 # Dry-run mode is consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_DRY_RUN="$dry_run"
    BASE_PROJECT_COMMAND_ARGUMENTS=("${args[@]}")
    # shellcheck disable=SC2034 # Passthrough arguments are consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_EXTRA_ARGS=("${extra_args[@]}")
    if [[ -n "$explicit_project" ]]; then
        BASE_PROJECT_COMMAND_SELECTION_ARGS=(--project "$explicit_project")
    elif [[ -n "$project" ]]; then
        BASE_PROJECT_COMMAND_SELECTION_ARGS=("$project")
    fi
    return 0
}

base_project_command_resolve_context() {
    local resolver_command="$1"
    local protocol_type="$2"
    local command_field="$3"
    local command_description="$4"
    local display_project="$5"
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local resolve_output

    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    resolve_output="$("$wrapper" --project base base_projects "$resolver_command" \
        "${BASE_PROJECT_COMMAND_SELECTION_ARGS[@]}" "${BASE_PROJECT_COMMAND_ARGUMENTS[@]}" \
        --format command-protocol)" || return $?
    base_command_protocol_decode_one "$protocol_type" "$resolve_output" || {
        base_std_fatal_error "Unable to resolve $command_description for project '$display_project'."
    }

    BASE_PROJECT_COMMAND_RESOLVED_NAME="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    BASE_PROJECT_COMMAND_RESOLVED_ROOT="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    BASE_PROJECT_COMMAND_RESOLVED_MANIFEST="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
    # shellcheck disable=SC2034 # Venv route metadata is consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_ROUTE_VENV="${BASE_COMMAND_PROTOCOL_FIELDS[project_venv_dir]}"
    # shellcheck disable=SC2034 # Manager route metadata is consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_USES_UV="${BASE_COMMAND_PROTOCOL_FIELDS[uses_uv_manager]}"
    # shellcheck disable=SC2034 # Trust metadata is consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_TRUST_REQUIRED="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_command_trust_required]}"
    BASE_PROJECT_COMMAND_RESOLVED_ACTION="${BASE_COMMAND_PROTOCOL_FIELDS[$command_field]}"
    # shellcheck disable=SC2034 # The runner is consumed by test.sh and demo.sh.
    BASE_PROJECT_COMMAND_RUNNER="${BASE_COMMAND_PROTOCOL_FIELDS[runner]}"

    [[ -n "$BASE_PROJECT_COMMAND_RESOLVED_NAME" && \
        -n "$BASE_PROJECT_COMMAND_RESOLVED_ROOT" && \
        -n "$BASE_PROJECT_COMMAND_RESOLVED_MANIFEST" && \
        -n "$BASE_PROJECT_COMMAND_RESOLVED_ACTION" ]] || {
        base_std_fatal_error "Unable to resolve $command_description for project '$display_project'."
    }

    base_project_set_history_context \
        "$BASE_PROJECT_COMMAND_RESOLVED_NAME" \
        "$BASE_PROJECT_COMMAND_RESOLVED_ROOT" \
        "$BASE_PROJECT_COMMAND_RESOLVED_MANIFEST"
}

base_project_activate_environment() {
    local project="$1"
    local project_root="$2"
    local manifest_path="$3"
    local dry_run="${4:-0}"
    local route_venv_dir="${5:-}"
    local uses_uv_manager="${6:-false}"
    local venv_dir venv_fix

    venv_dir="$(base_project_venv_dir "$project" "$project_root" "$route_venv_dir")"
    venv_fix="$(base_project_venv_fix "$project" "$project_root" "$venv_dir" "$uses_uv_manager")"
    export BASE_PROJECT="$project"
    export BASE_PROJECT_ROOT="$project_root"
    export BASE_PROJECT_MANIFEST="$manifest_path"
    export BASE_PROJECT_VENV_DIR="$venv_dir"
    export BASE_CLI_PROJECT_NAME="$project"
    export BASE_CLI_PROJECT_ROOT="$project_root"
    export BASE_CLI_PROJECT_MANIFEST="$manifest_path"

    if [[ -d "$venv_dir/bin" ]]; then
        PATH="$venv_dir/bin:$PATH"
        export PATH
    elif [[ "$dry_run" != "1" ]]; then
        base_std_log_warn "Project virtual environment was not found at '$venv_dir'. $venv_fix"
    fi

    printf '%s\n' "$venv_dir"
}

base_format_extra_args() {
    local arg quoted output=""

    for arg in "$@"; do
        printf -v quoted '%q' "$arg"
        output+=" $quoted"
    done
    printf '%s\n' "$output"
}

base_command_with_extra_args() {
    local command="$1"
    shift

    if (($# == 0)); then
        printf '%s\n' "$command"
        return 0
    fi

    if [[ "$command" == mise\ run\ * ]]; then
        printf '%s -- "$@"\n' "$command"
    else
        printf '%s "$@"\n' "$command"
    fi
}

base_command_with_runner() {
    local runner="$1" command="$2" command_with_args
    shift 2

    command_with_args="$(base_command_with_extra_args "$command" "$@")"
    case "$runner" in
        "")
            printf '%s\n' "$command_with_args"
            ;;
        uv)
            printf 'uv run -- %s\n' "$command_with_args"
            ;;
        *)
            printf 'Unsupported command runner %q.\n' "$runner" >&2
            return 2
            ;;
    esac
}

base_project_run_shell_command() {
    local working_dir="$1"
    local command_to_run="$2"
    local command_name="$3"
    shift 3

    # Bash assigns the word after `bash -c <command>` to `$0`; use a stable
    # sentinel so delegated extra args start at `$1` and populate `$@`.
    (
        export BASE_CLI_RUNTIME_OWNER=project
        export BASE_CLI_PROJECT_ROOT="${BASE_PROJECT_ROOT:-$working_dir}"
        export BASE_CLI_PROJECT_NAME="${BASE_PROJECT:-$(basename -- "$working_dir")}"
        export BASE_CLI_PROJECT_MANIFEST="${BASE_PROJECT_MANIFEST:-}"
        # A project command gets its own owner-scoped bundle. Keep the parent
        # history ID, but do not let it write raw logs into Base's bundle.
        unset BASE_CLI_RUN_ROOT BASE_CLI_RUN_ID BASE_BASH_LIBS_PRIMARY_LOG
        # setup and diagnostics also recognize user-local tool installs. Keep
        # the project environment first, then make $HOME/.local/bin available
        # for runners such as uv and mise.
        if [[ -n "${HOME:-}" ]]; then
            PATH="${PATH:+$PATH:}$HOME/.local/bin"
            export PATH
        fi
        cd "$working_dir" && bash -c "$command_to_run" "$command_name" "$@"
    )
}

base_validate_command_runner() {
    local runner="$1"
    local uv_path

    case "$runner" in
        "")
            return 0
            ;;
        uv)
            if base_std_command_path uv_path uv && [[ -n "$uv_path" ]]; then
                return 0
            fi
            if [[ -n "${HOME:-}" && -x "$HOME/.local/bin/uv" ]]; then
                return 0
            fi
            base_std_fatal_error "Command runner 'uv' is not available. Install uv or remove runner: uv from the project manifest."
            ;;
        *)
            base_std_fatal_error "Unsupported command runner '$runner'."
            ;;
    esac
}

base_display_command() {
    local command="$1"
    shift

    if (($# == 0)); then
        printf '%s\n' "$command"
        return 0
    fi

    if [[ "$command" == mise\ run\ * ]]; then
        printf '%s --%s\n' "$command" "$(base_format_extra_args "$@")"
    else
        printf '%s%s\n' "$command" "$(base_format_extra_args "$@")"
    fi
}

base_display_command_with_runner() {
    local runner="$1" command="$2" display_command
    shift 2

    display_command="$(base_display_command "$command" "$@")"
    case "$runner" in
        "")
            printf '%s\n' "$display_command"
            ;;
        uv)
            printf 'uv run -- %s\n' "$display_command"
            ;;
        *)
            printf 'Unsupported command runner %q.\n' "$runner" >&2
            return 2
            ;;
    esac
}
