# shellcheck shell=bash
[[ -n "${_base_activate_subcommand_sourced:-}" ]] && return
_base_activate_subcommand_sourced=1
readonly _base_activate_subcommand_sourced

base_activate_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl activate <project> [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to BASE_HOME's parent.
  --no-cd             Preserve the caller's current directory in the project shell.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Start an interactive Base runtime subshell for a project.
EOF
}

base_activate_usage_error() {
    base_activate_subcommand_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_activate_resolve_project() {
    local project="$1"
    local wrapper="$2"
    shift 2

    env -u BASE_PROJECT_VENV_DIR "$wrapper" --project base base_projects resolve "$project" "$@"
}

base_activate_project_venv_dir() {
    local project="$1"

    if [[ -n "${BASE_PROJECT_VENV_DIR:-}" ]]; then
        printf '%s\n' "$BASE_PROJECT_VENV_DIR"
        return 0
    fi

    printf '%s\n' "$HOME/.base.d/$project/.venv"
}

base_activate_subcommand_main() {
    local project="" wrapper resolve_output activate_shell
    local resolved_name project_root manifest_path venv_dir shell_rc
    local preserve_cwd="${BASE_ACTIVATE_PRESERVE_CWD:-0}"
    local args=()

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                base_activate_subcommand_usage
                return 0
                ;;
            -v)
                args+=(--debug)
                shift
                ;;
            --workspace)
                [[ -n "${2:-}" ]] || {
                    base_activate_usage_error "Option '--workspace' requires an argument."
                    return $?
                }
                args+=(--workspace "$2")
                shift 2
                ;;
            --workspace=*)
                args+=("$1")
                shift
                ;;
            --no-cd)
                preserve_cwd=1
                shift
                ;;
            -*)
                base_activate_usage_error "Unknown activate option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$project" ]]; then
                    base_activate_usage_error "The 'activate' command accepts exactly one project name."
                    return $?
                fi
                project="$1"
                shift
                ;;
        esac
    done

    [[ -n "$project" ]] || {
        base_activate_usage_error "Project name is required."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    resolve_output="$(base_activate_resolve_project "$project" "$wrapper" "${args[@]}")" || return $?
    IFS=$'\t' read -r resolved_name project_root manifest_path <<<"$resolve_output"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" ]] || {
        fatal_error "Unable to resolve project '$project'."
    }

    venv_dir="$(base_activate_project_venv_dir "$resolved_name")"
    [[ -x "$venv_dir/bin/python" ]] || {
        fatal_error "Project virtual environment Python was not found at '$venv_dir/bin/python'. Run 'basectl setup $resolved_name' first."
    }

    shell_rc="$BASE_HOME/lib/bash/runtime/bashrc"
    [[ -f "$shell_rc" ]] || fatal_error "Base runtime shell rcfile '$shell_rc' was not found."

    export BASE_PROJECT="$resolved_name"
    export BASE_PROJECT_ROOT="$project_root"
    export BASE_PROJECT_MANIFEST="$manifest_path"
    export BASE_PROJECT_VENV_DIR="$venv_dir"
    export BASE_HOME
    export BASE_SHELL=1

    if [[ "$preserve_cwd" != "1" ]]; then
        cd "$project_root" || fatal_error "Unable to enter project root '$project_root'."
    fi
    activate_shell="${BASE_ACTIVATE_SHELL:-${BASH:-bash}}"
    exec "$activate_shell" --rcfile "$shell_rc"
}
