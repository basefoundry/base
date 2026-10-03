#!/usr/bin/env bash

[[ -n "${_base_uninstall_subcommand_sourced:-}" ]] && return 0
_base_uninstall_subcommand_sourced=1
readonly _base_uninstall_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

import_base_lib arg/lib_arg.sh

base_uninstall_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl uninstall <project> [options]
  basectl uninstall --all [options]

Options:
  --project <name>  Explicitly select a project, including one named "help".
  --all       Remove all Base-managed local state and workspace settings.
  --workspace <path>
              Workspace directory used to resolve a project name.
  --dry-run   Preview removal without changing files.
  --yes       Apply the removal after reviewing the preview.
  --verify    Verify that the selected Base-managed state is absent.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Remove Base-managed trust, check state, external Base-managed project
  environments, and runtime caches. The project checkout and its manifest are
  never deleted. Use --all to also remove Base workspace settings and shell
  startup sections.

Notes:
  Removal previews by default. Apply changes only with --yes. After an
  applied --all removal, Base removes deferred runtime state and runs the
  verification check automatically.
EOF
}

base_uninstall_usage_error() {
    base_uninstall_subcommand_usage >&2
    base_std_print_error "$*"
    return 2
}

base_uninstall_run_python() {
    local wrapper="$BASE_HOME/bin/base-wrapper"

    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    BASE_CLI_DISPLAY_COMMAND="basectl uninstall" \
        "$wrapper" --project base base_uninstall "$@"
}

base_uninstall_subcommand_main() {
    local all_projects=0 verify=0 yes=0 project=""
    local parse_args=() python_args=()

    while (($# > 0)); do
        case "$1" in
            --all)
                all_projects=1
                ;;
            --yes)
                yes=1
                ;;
            --verify)
                verify=1
                ;;
            *)
                parse_args+=("$1")
                ;;
        esac
        shift
    done

    base_project_command_parse_args \
        uninstall base_uninstall_subcommand_usage base_uninstall_usage_error \
        "The 'uninstall' command accepts at most one project name." "${parse_args[@]}" || return $?
    [[ "$BASE_PROJECT_COMMAND_HELP_SHOWN" == 1 ]] && return 0

    local dry_run="$BASE_PROJECT_COMMAND_DRY_RUN"
    project="$BASE_PROJECT_COMMAND_SELECTED_PROJECT"
    python_args=("${BASE_PROJECT_COMMAND_ARGUMENTS[@]}")

    if ((all_projects && ${#project} > 0)); then
        base_uninstall_usage_error "Option '--all' cannot be combined with a project name."
        return $?
    fi
    if ((!all_projects && ${#project} == 0)); then
        base_uninstall_usage_error "Provide a project name or use '--all'."
        return $?
    fi
    if ((dry_run && yes)); then
        base_uninstall_usage_error "Options '--dry-run' and '--yes' cannot be used together."
        return $?
    fi
    if ((verify && (dry_run || yes))); then
        base_uninstall_usage_error "Option '--verify' cannot be combined with '--dry-run' or '--yes'."
        return $?
    fi
    ((all_projects)) && python_args+=(--all)
    ((dry_run)) && python_args+=(--dry-run)
    ((yes)) && python_args+=(--yes)
    ((verify)) && python_args+=(--verify)
    [[ -z "$project" ]] || python_args+=("$project")

    base_uninstall_run_python "${python_args[@]}"
    local status=$?
    ((status == 0)) || return "$status"

    if ((all_projects && !verify)); then
        if ((yes)); then
            if base_update_profile_subcommand_main --remove; then
                status=0
            else
                status=$?
            fi
        else
            if base_update_profile_subcommand_main --remove --dry-run; then
                status=0
            else
                status=$?
            fi
        fi
    fi

    if ((all_projects && yes)); then
        local finalize_status=0
        if base_uninstall_run_python --all --finalize; then
            finalize_status=0
        else
            finalize_status=$?
        fi
        ((status == 0)) || return "$status"
        ((finalize_status == 0)) || return "$finalize_status"
    fi
    return "$status"
}
