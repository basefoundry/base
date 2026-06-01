#!/usr/bin/env bash

basectl_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

basectl_show_help() {
    cat <<'EOF'
Usage: basectl [options] <command> [args...]

Commands:
  activate <project> [options]
    Start an interactive Base runtime subshell for a project.
  setup [options]
    Install and bootstrap the local Base CLI environment on macOS.
  check [project] [options]
    Verify the local Base CLI environment and optional project artifacts without making changes.
  test [project] [options]
    Run a project's declared test command.
  demo <project> [options]
    Run a project's declared interactive demo.
  run <project> <command> [options]
    Run a project's declared command.
  repo <init|check|configure> [options]
    Create, check, and configure a standard Base-managed repository baseline.
  clean [--older-than <age>] [--keep-last <count>] [options]
    Remove old Base CLI runtime logs, temp files, and cache entries.
  config <path|show|doctor>
    Inspect Base's machine-local user config.
  doctor [project] [options]
    Diagnose the local Base CLI environment and optional project artifacts.
  gh <area> <command> [options]
    Manage GitHub issues, PRs, branches, and repository hygiene.
  onboard [options]
    Guide a user through the first Base setup checklist.
  update-profile [options]
    Create or update Base-managed sections in Bash and Zsh startup files.
  update [options]
    Update Base from Git and run setup.
  projects list [options]
    List Base-managed projects discovered in the workspace.
  version
    Show the installed Base version.
  help
    Show this help text.

Options:
  -v       Enable DEBUG logging for the selected command.
  -x       Enable Bash xtrace before running the command.
  -h       Show this help text.
  --version
           Show the installed Base version.

Wrapper options:
  --debug-wrapper    Enable DEBUG logging before the Base runtime is loaded.
  --verbose-wrapper  Enable verbose runtime argument handling before dispatch.
  --utc-wrapper      Print wrapper/runtime log timestamps in UTC.
  --color            Preserve color-aware wrapper argument handling.

Notes:
  - `basectl setup` is the preferred entrypoint for machine bootstrap.
  - `basectl check` verifies the same local requirements without making changes.
    Pass a project name to include that project's manifest artifacts.
  - Invoking `basectl` with no command starts a Base runtime shell for the
    nearest project manifest above the current directory, preserving that
    directory. If no manifest is found, it falls back to project `base`. In
    non-interactive shells it prints this help text.
  - Use `-v` for command-level debug logs. Use `--debug-wrapper` when debugging
    startup before command dispatch or Base runtime initialization.
EOF
}

basectl_describe() {
    printf '%s\n' "basectl umbrella CLI"
}

basectl_usage_error() {
    basectl_error "$*"
    basectl_show_help >&2
    return 2
}

basectl_get_base_home() {
    [[ -n "${HOME:-}" ]] || {
        basectl_error "Environment variable 'HOME' is not set."
        return 1
    }
    [[ -d "$HOME" ]] || {
        basectl_error "\$HOME '$HOME' is not a directory."
        return 1
    }

    [[ -n "${BASE_HOME:-}" ]] || {
        basectl_error "BASE_HOME is not set. Run this command through bin/basectl."
        return 1
    }
    [[ -d "$BASE_HOME" ]] || {
        basectl_error "BASE_HOME '$BASE_HOME' is not a directory."
        return 1
    }
    export BASE_HOME
}

basectl_verify_home() {
    local base_home="$1"
    local file missing=()

    if [[ ! -d "$base_home" ]]; then
        BASE_CLI_ERROR_MESSAGE="Base home '$base_home' is not a directory."
        return 1
    fi

    for file in VERSION base_init.sh lib/shell/bash_profile lib/shell/bashrc lib/shell/baserc_guard.sh lib/bash/runtime/bashrc lib/bash/version/lib_version.sh bin/basectl bin/base-wrapper cli/bash/commands/basectl/basectl.sh; do
        if [[ ! -f "$base_home/$file" ]]; then
            missing+=("$file")
        fi
    done

    if (( ${#missing[@]} > 0 )); then
        BASE_CLI_ERROR_MESSAGE="Files missing in Base home '$base_home': ${missing[*]}"
        return 1
    fi

    return 0
}

basectl_runtime_base_home() {
    if basectl_verify_home "$BASE_HOME"; then
        printf '%s\n' "$BASE_HOME"
        return 0
    fi

    return 1
}

basectl_enable_debug_logging() {
    set_log_level DEBUG
    export LOG_DEBUG=1
}

basectl_source_subcommand_module() {
    local module_name="$1"
    local subcommand_script="$__SCRIPT_DIR__/subcommands/${module_name}.sh"

    [[ -f "$subcommand_script" ]] || {
        basectl_error "Subcommand module '$subcommand_script' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$subcommand_script"
}

basectl_do_setup() {
    basectl_source_subcommand_module setup || return 1
    base_setup_subcommand_main "$@"
}

basectl_do_activate() {
    basectl_source_subcommand_module activate || return 1
    base_activate_subcommand_main "$@"
}

basectl_do_check() {
    basectl_source_subcommand_module check || return 1
    base_check_subcommand_main "$@"
}

basectl_do_test() {
    basectl_source_subcommand_module test || return 1
    base_test_subcommand_main "$@"
}

basectl_do_demo() {
    basectl_source_subcommand_module demo || return 1
    base_demo_subcommand_main "$@"
}

basectl_do_run() {
    basectl_source_subcommand_module run || return 1
    base_run_subcommand_main "$@"
}

basectl_do_repo() {
    basectl_source_subcommand_module repo || return 1
    base_repo_subcommand_main "$@"
}

basectl_do_clean() {
    basectl_source_subcommand_module clean || return 1
    base_clean_subcommand_main "$@"
}

basectl_do_config() {
    basectl_source_subcommand_module config || return 1
    base_config_subcommand_main "$@"
}

basectl_do_doctor() {
    basectl_source_subcommand_module doctor || return 1
    base_doctor_subcommand_main "$@"
}

basectl_do_gh() {
    basectl_source_subcommand_module gh || return 1
    base_gh_subcommand_main "$@"
}

basectl_do_onboard() {
    basectl_source_subcommand_module onboard || return 1
    base_onboard_subcommand_main "$@"
}

basectl_do_update_profile() {
    basectl_source_subcommand_module update_profile || return 1
    base_update_profile_subcommand_main "$@"
}

basectl_do_update() {
    basectl_source_subcommand_module update || return 1
    base_update_subcommand_main "$@"
}

basectl_do_projects() {
    basectl_source_subcommand_module projects || return 1
    base_projects_subcommand_main "$@"
}

basectl_source_version_library() {
    local version_lib="$BASE_HOME/lib/bash/version/lib_version.sh"

    [[ -f "$version_lib" ]] || {
        basectl_error "Base version library '$version_lib' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$version_lib"
}

basectl_do_version() {
    basectl_source_version_library || return 1
    printf 'basectl %s\n' "$(base_read_version "$BASE_HOME")"
}

basectl_should_start_shell() {
    [[ -t 0 && -t 1 ]]
}

basectl_default_activate_project() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local resolve_output project_name

    if [[ -x "$wrapper" ]]; then
        if resolve_output="$("$wrapper" --project base base_projects current 2>/dev/null)"; then
            IFS=$'\t' read -r project_name _ <<<"$resolve_output"
            if [[ -n "$project_name" ]]; then
                printf '%s\n' "$project_name"
                return 0
            fi
        fi
    fi

    printf '%s\n' base
}


basectl_main() {
    local base_debug=0 command=""
    local opt

    if [[ "${1:-}" =~ ^(-h|--help|-help|help)$ ]]; then
        basectl_show_help
        return 0
    fi

    if [[ "${1:-}" == "--version" ]]; then
        basectl_get_base_home || return 1
        basectl_do_version
        return 0
    fi

    if [[ "${1:-}" == "--describe" ]]; then
        basectl_describe
        return 0
    fi

    case "${1:-}" in
        --*)
            basectl_usage_error "Unknown option '$1'"
            return $?
            ;;
    esac

    OPTIND=1
    OPTERR=0
    while getopts ":hvx" opt; do
        case "$opt" in
            v) base_debug=1 ;;
            x) set -x ;;
            h)
                basectl_show_help
                return 0
                ;;
            \?)
                basectl_usage_error "Unknown option '-$OPTARG'"
                return $?
                ;;
            :)
                basectl_usage_error "Option '-$OPTARG' requires an argument."
                return $?
                ;;
        esac
    done
    shift $((OPTIND - 1))

    command="${1:-}"
    [[ -n "$command" ]] && shift

    basectl_get_base_home || return 1
    ((base_debug)) && basectl_enable_debug_logging
    log_debug "Running basectl command '${command:-<none>}' with args: $*"

    case "$command" in
        activate)         basectl_do_activate "$@" ;;
        check)            basectl_do_check "$@" ;;
        test)             basectl_do_test "$@" ;;
        demo)             basectl_do_demo "$@" ;;
        run)              basectl_do_run "$@" ;;
        repo)             basectl_do_repo "$@" ;;
        clean)            basectl_do_clean "$@" ;;
        config)           basectl_do_config "$@" ;;
        doctor)           basectl_do_doctor "$@" ;;
        gh)               basectl_do_gh "$@" ;;
        onboard)          basectl_do_onboard "$@" ;;
        setup)            basectl_do_setup "$@" ;;
        help)             basectl_show_help ;;
        projects)         basectl_do_projects "$@" ;;
        update)           basectl_do_update "$@" ;;
        update-profile)   basectl_do_update_profile "$@" ;;
        version)          basectl_do_version ;;
        "")
            if basectl_should_start_shell; then
                BASE_ACTIVATE_PRESERVE_CWD=1 basectl_do_activate "$(basectl_default_activate_project)"
            else
                basectl_show_help
            fi
            ;;
        *)
            basectl_usage_error "Unrecognized command: $command"
            ;;
    esac
}

main() {
    basectl_main "$@"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
