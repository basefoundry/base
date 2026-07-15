# shellcheck shell=bash
[[ -n "${_base_activate_subcommand_sourced:-}" ]] && return 0
_base_activate_subcommand_sourced=1
readonly _base_activate_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

base_activate_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl activate <project> [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --no-cd             Preserve the caller's current directory in the project shell.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Start an interactive Base Bash runtime shell for a project.
EOF
}

base_activate_usage_error() {
    base_activate_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_activate_resolve_project() {
    local project="$1"
    local wrapper="$2"
    shift 2

    env -u BASE_PROJECT_VENV_DIR \
        "$wrapper" --project base base_projects resolve "$project" "$@" --format command-protocol
}

base_activate_project_venv_dir() {
    local project="$1"
    local project_root="${2:-}"
    local route_venv_dir="${3:-}"

    base_project_venv_dir "$project" "$project_root" "$route_venv_dir"
}

base_activate_shell_is_bash() {
    local shell_path="$1"
    local shell_name="${shell_path##*/}"

    [[ "$shell_name" == "bash" || "$shell_name" == bash-* || "$shell_name" == *-bash ]]
}

base_activate_subcommand_main() {
    local project="" wrapper resolve_output activate_shell venv_fix
    local resolved_name project_root manifest_path venv_dir shell_rc route_venv_dir uses_uv_manager trust_required
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
    base_command_protocol_decode_one project-route "$resolve_output" || {
        fatal_error "Unable to resolve project '$project'."
    }
    resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    project_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
    route_venv_dir="${BASE_COMMAND_PROTOCOL_FIELDS[project_venv_dir]}"
    uses_uv_manager="${BASE_COMMAND_PROTOCOL_FIELDS[uses_uv_manager]}"
    trust_required="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_command_trust_required]}"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" ]] || {
        fatal_error "Unable to resolve project '$project'."
    }

    base_project_require_manifest_command_trust "$resolved_name" "$manifest_path" "$trust_required" || return $?

    venv_dir="$(base_activate_project_venv_dir "$resolved_name" "$project_root" "$route_venv_dir")"
    venv_fix="$(base_project_venv_fix "$resolved_name" "$project_root" "$venv_dir" "$uses_uv_manager")"
    [[ -x "$venv_dir/bin/python" ]] || {
        fatal_error "Project virtual environment Python was not found at '$venv_dir/bin/python'. $venv_fix"
    }

    shell_rc="$BASE_HOME/lib/bash/runtime/bashrc"
    [[ -f "$shell_rc" ]] || fatal_error "Base runtime shell rcfile '$shell_rc' was not found."

    export BASE_PROJECT="$resolved_name"
    export BASE_PROJECT_ROOT="$project_root"
    export BASE_PROJECT_MANIFEST="$manifest_path"
    export BASE_PROJECT_VENV_DIR="$venv_dir"
    export BASE_HOME

    if [[ "$preserve_cwd" != "1" ]]; then
        cd "$project_root" || fatal_error "Unable to enter project root '$project_root'."
    fi
    activate_shell="${BASE_ACTIVATE_SHELL:-${BASH:-bash}}"
    if ! base_activate_shell_is_bash "$activate_shell"; then
        fatal_error "basectl activate requires Bash. BASE_ACTIVATE_SHELL='$activate_shell' is not supported. Unset BASE_ACTIVATE_SHELL to use the default Bash runtime shell."
    fi
    exec "$activate_shell" --rcfile "$shell_rc"
}
