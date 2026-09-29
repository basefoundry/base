# shellcheck shell=bash
[[ -n "${_base_activate_subcommand_sourced:-}" ]] && return 0
_base_activate_subcommand_sourced=1
readonly _base_activate_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

import_base_lib arg/lib_arg.sh

base_activate_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl activate <project> [options]

Options:
  --project <name>    Explicitly select a project, including one named "help".
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --no-cd             Preserve the caller's current directory in the project shell.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Start an interactive Base Bash runtime shell for a project.
EOF
}

base_activate_usage_error() {
    base_activate_subcommand_usage >&2
    base_std_print_error "$*"
    return 2
}

base_activate_resolve_project() {
    local wrapper="$1"
    shift

    env -u BASE_PROJECT_VENV_DIR \
        "$wrapper" --project base base_projects resolve "$@" --format command-protocol
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
    local parse_args=() args=()

    while (($# > 0)); do
        case "$1" in
            --no-cd)
                preserve_cwd=1
                shift
                ;;
            *)
                parse_args+=("$1")
                shift
                ;;
        esac
    done

    base_project_command_parse_args \
        activate base_activate_subcommand_usage base_activate_usage_error \
        "The 'activate' command accepts exactly one project name." "${parse_args[@]}" || return $?
    [[ "$BASE_PROJECT_COMMAND_HELP_SHOWN" == 1 ]] && return 0
    project="$BASE_PROJECT_COMMAND_SELECTED_PROJECT"
    args=("${BASE_PROJECT_COMMAND_ARGUMENTS[@]}")

    [[ -n "$project" ]] || {
        base_activate_usage_error "Project name is required."
        return $?
    }

    wrapper="$BASE_HOME/bin/base-wrapper"
    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    resolve_output="$(base_activate_resolve_project "$wrapper" \
        "${BASE_PROJECT_COMMAND_SELECTION_ARGS[@]}" "${args[@]}")" || return $?
    base_command_protocol_decode_one project-route "$resolve_output" || {
        base_std_fatal_error "Unable to resolve project '$project'."
    }
    resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    project_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    manifest_path="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
    route_venv_dir="${BASE_COMMAND_PROTOCOL_FIELDS[project_venv_dir]}"
    uses_uv_manager="${BASE_COMMAND_PROTOCOL_FIELDS[uses_uv_manager]}"
    trust_required="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_command_trust_required]}"
    base_project_set_history_context "$resolved_name" "$project_root" "$manifest_path"

    [[ -n "$resolved_name" && -n "$project_root" && -n "$manifest_path" ]] || {
        base_std_fatal_error "Unable to resolve project '$project'."
    }

    base_project_require_manifest_command_trust "$resolved_name" "$manifest_path" "$trust_required" || return $?

    venv_dir="$(base_activate_project_venv_dir "$resolved_name" "$project_root" "$route_venv_dir")"
    venv_fix="$(base_project_venv_fix "$resolved_name" "$project_root" "$venv_dir" "$uses_uv_manager")"
    if [[ ! -x "$venv_dir/bin/python" ]]; then
        base_std_log_error "Project virtual environment Python was not found at '$venv_dir/bin/python'. $venv_fix"
        return 1
    fi

    shell_rc="$BASE_HOME/lib/bash/runtime/bashrc"
    [[ -f "$shell_rc" ]] || base_std_fatal_error "Base runtime shell rcfile '$shell_rc' was not found."

    export BASE_PROJECT="$resolved_name"
    export BASE_PROJECT_ROOT="$project_root"
    export BASE_PROJECT_MANIFEST="$manifest_path"
    export BASE_PROJECT_VENV_DIR="$venv_dir"
    export BASE_HOME

    if [[ "$preserve_cwd" != "1" ]]; then
        cd "$project_root" || base_std_fatal_error "Unable to enter project root '$project_root'."
    fi
    activate_shell="${BASE_ACTIVATE_SHELL:-${BASH:-bash}}"
    if ! base_activate_shell_is_bash "$activate_shell"; then
        base_std_fatal_error "basectl activate requires Bash. BASE_ACTIVATE_SHELL='$activate_shell' is not supported. Unset BASE_ACTIVATE_SHELL to use the default Bash runtime shell."
    fi
    "$activate_shell" --rcfile "$shell_rc"
}
