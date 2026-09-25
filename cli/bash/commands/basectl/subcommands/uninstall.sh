#!/usr/bin/env bash

[[ -n "${_base_uninstall_subcommand_sourced:-}" ]] && return 0
_base_uninstall_subcommand_sourced=1
readonly _base_uninstall_subcommand_sourced

base_uninstall_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl uninstall <project> [options]
  basectl uninstall --all [options]

Options:
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
  applied --all removal, Base runs the verification check automatically.
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
    local all_projects=0 dry_run=0 verify=0 yes=0 debug=0 workspace="" project="" arg
    local -a python_args=()

    while (($# > 0)); do
        arg="$1"
        case "$arg" in
            -h|--help|help)
                base_uninstall_subcommand_usage
                return 0
                ;;
            --all)
                all_projects=1
                ;;
            --dry-run)
                dry_run=1
                ;;
            --yes)
                yes=1
                ;;
            --verify)
                verify=1
                ;;
            -v)
                debug=1
                ;;
            --workspace)
                shift
                [[ -n "${1:-}" ]] || {
                    base_uninstall_usage_error "Option '--workspace' requires an argument."
                    return $?
                }
                workspace="$1"
                ;;
            *)
                if [[ "$arg" == -* ]]; then
                    base_uninstall_usage_error "Unknown option '$arg'."
                    return $?
                fi
                [[ -z "$project" ]] || {
                    base_uninstall_usage_error "The 'uninstall' command accepts at most one project name."
                    return $?
                }
                project="$arg"
                ;;
        esac
        shift
    done

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
    if ((debug)); then
        python_args+=(--debug)
    fi
    ((all_projects)) && python_args+=(--all)
    [[ -z "$workspace" ]] || python_args+=(--workspace "$workspace")
    ((dry_run)) && python_args+=(--dry-run)
    ((yes)) && python_args+=(--yes)
    ((verify)) && python_args+=(--verify)
    [[ -z "$project" ]] || python_args+=("$project")

    base_uninstall_run_python "${python_args[@]}"
    local status=$?
    ((status == 0)) || return "$status"

    if ((all_projects && !verify)); then
        if ((yes)); then
            base_update_profile_subcommand_main --remove
        else
            base_update_profile_subcommand_main --remove --dry-run
        fi
        status=$?
        ((status == 0)) || return "$status"
    fi

    if ((all_projects && yes)); then
        base_uninstall_run_python --all --verify
        status=$?
        ((status == 0)) || return "$status"
    fi
    return 0
}
