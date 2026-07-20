# shellcheck shell=bash
[[ -n "${_base_projects_subcommand_sourced:-}" ]] && return 0
_base_projects_subcommand_sourced=1
readonly _base_projects_subcommand_sourced

base_projects_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl projects list [options]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --format <format>   Output format for list: text, csv, tsv, yaml, or json.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

List Base-managed projects discovered through base_manifest.yaml files.
EOF
}

base_projects_usage_error() {
    base_projects_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_projects_base_venv_python() {
    local venv_dir="${BASE_PROJECT_VENV_DIR:-$HOME/.base.d/base/.venv}"

    printf '%s\n' "$venv_dir/bin/python"
}

base_projects_source_checkout_available() {
    [[ -f "$BASE_HOME/cli/python/base_projects/__main__.py" ]] &&
        [[ -f "$BASE_HOME/lib/python/base_cli/__init__.py" ]]
}

base_projects_source_pythonpath() {
    local base_pythonpath="$BASE_HOME/lib/python:$BASE_HOME/cli/python"

    if [[ -n "${PYTHONPATH:-}" ]]; then
        printf '%s:%s\n' "$base_pythonpath" "$PYTHONPATH"
    else
        printf '%s\n' "$base_pythonpath"
    fi
}

base_projects_source_python() {
    local python_bin
    local base_pythonpath

    python_bin="$(command -v python3 2>/dev/null || true)"
    [[ -n "$python_bin" ]] || return 1

    base_pythonpath="$(base_projects_source_pythonpath)"
    env BASE_HOME="$BASE_HOME" BASE_PROJECT=base PYTHONPATH="$base_pythonpath" \
        "$python_bin" -c 'import click; import yaml; import base_projects' >/dev/null 2>&1 || return 1

    printf '%s\n' "$python_bin"
}

base_projects_list_pre_setup_error() {
    print_error "basectl projects list needs either the Base project virtualenv or a Python 3 with Click and PyYAML available."
    print_error "Run 'basectl setup' to create the Base project virtualenv."
    return 1
}

base_projects_run_list() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local venv_python
    local python_bin
    local base_pythonpath

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."

    venv_python="$(base_projects_base_venv_python)"
    if [[ -x "$venv_python" ]]; then
        "$wrapper" --project base base_projects list "$@"
        return $?
    fi

    if base_projects_source_checkout_available && python_bin="$(base_projects_source_python)"; then
        base_pythonpath="$(base_projects_source_pythonpath)"
        env BASE_HOME="$BASE_HOME" BASE_PROJECT=base PYTHONPATH="$base_pythonpath" \
            "$python_bin" -m base_projects list "$@"
        return $?
    fi

    base_projects_list_pre_setup_error
}

base_projects_subcommand_main() {
    local project_command="${1:-}"
    local args=()

    case "$project_command" in
        ""|-h|--help)
            base_projects_subcommand_usage
            return 0
            ;;
        list)
            shift
            ;;
        *)
            base_projects_usage_error "Unknown projects command '$project_command'."
            return $?
            ;;
    esac

    while (($# > 0)); do
        case "$1" in
            -v)
                args+=(--debug)
                shift
                ;;
            -h|--help)
                base_projects_subcommand_usage
                return 0
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    base_projects_run_list "${args[@]}"
}
