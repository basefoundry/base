#!/usr/bin/env bash

[[ -n "${_base_test_subcommand_sourced:-}" ]] && return
_base_test_subcommand_sourced=1
readonly _base_test_subcommand_sourced

base_test_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl test <project> [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to BASE_HOME's parent.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a project's declared test command from its project root.
EOF
}

base_test_usage_error() {
    base_test_subcommand_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_test_project_venv_dir() {
    local project="$1"

    if [[ -n "${BASE_PROJECT_VENV_DIR:-}" ]]; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi

    printf '%s\n' "$HOME/.base.d/$project/.venv"
}

base_test_subcommand_main() {
    local project="" wrapper resolve_output resolved_name project_root manifest_path test_command venv_dir
    local args=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_test_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_test_usage_error "Option '--workspace' requires an argument."
                    return $?
                }
                args+=(--workspace "$2")
                shift 2
                ;;
            --workspace=*)
                args+=("$1")
                shift
                ;;
            -*)
                base_test_usage_error "Unknown test option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$project" ]]; then
                    base_test_usage_error "The 'test' command accepts exactly one project name."
                    return $?
                fi
                project="$1"
                shift
                ;;
        esac
    done

    [[ -n "$project" ]] || {
        base_test_usage_error "Project name is required."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    resolve_output="$("$wrapper" --project base base_projects test-command "$project" "${args[@]}")" || return $?
    IFS=$'\t' read -r resolved_name project_root manifest_path test_command <<<"$resolve_output"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" && -n "$test_command" ]] || {
        fatal_error "Unable to resolve test command for project '$project'."
    }

    venv_dir="$(base_test_project_venv_dir "$resolved_name")"
    export BASE_PROJECT="$resolved_name"
    export BASE_PROJECT_ROOT="$project_root"
    export BASE_PROJECT_MANIFEST="$manifest_path"
    export BASE_PROJECT_VENV_DIR="$venv_dir"

    if [[ -d "$venv_dir/bin" ]]; then
        PATH="$venv_dir/bin:$PATH"
        export PATH
    fi

    log_info "Running tests for project '$resolved_name': $test_command"
    (cd "$project_root" && bash -c "$test_command")
}
