#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
    [[ -n "${_basectl_dispatcher_sourced:-}" ]] && return 0
    _basectl_dispatcher_sourced=1
    readonly _basectl_dispatcher_sourced
fi

BASECTL_REQUIRED_HOME_FILES=(
    VERSION
    base_init.sh
    lib/shell/bash_profile
    lib/shell/bashrc
    lib/shell/baserc_guard.sh
    lib/bash/runtime/bashrc
    lib/bash/runtime/command_protocol.sh
    lib/bash/version/lib_version.sh
    bin/basectl
    bin/base-wrapper
    cli/bash/commands/basectl/basectl.sh
)
readonly BASECTL_REQUIRED_HOME_FILES

if ! declare -F base_command_protocol_decode_one >/dev/null 2>&1 &&
    [[ -n "${BASE_HOME:-}" && -f "$BASE_HOME/lib/bash/runtime/command_protocol.sh" ]]; then
    # shellcheck source=/dev/null
    source "$BASE_HOME/lib/bash/runtime/command_protocol.sh"
fi

basectl_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

basectl_show_help() {
    cat <<'EOF'
Usage: basectl [options] <command> [args...]

Commands:

Getting started:
  onboard [project] [options]
    Guide a user through the first Base setup checklist.
  setup [options] [project]
    Install and bootstrap the local Base CLI environment on macOS or Ubuntu/Debian.
  check [project] [options]
    Verify the local Base CLI environment and optional project artifacts without making changes.
  doctor [project] [options]
    Diagnose the local Base CLI environment and optional project artifacts.

Daily project loop:
  projects list [options]
    List Base-managed projects discovered in the workspace.
  activate <project> [options]
    Start an interactive Base runtime subshell for a project.
  test [project] [options]
    Run a project's declared test command.
  build [project] [target...] [options]
    Run a project's declared build targets.
  demo [project] [options]
    Run a project's declared interactive demo.
  run [project] <command> [options]
    Run a project's declared command.
  trust <status|allow|revoke> [project] [options]
    Inspect trust across projects, or manage one project's local approval.

Workspace and repositories:
  workspace <status|check|doctor|onboarding|agent-brief|clone|pull|init|configure> [options]
    Show workspace status, onboarding, agent readiness, checks, or explicit workspace mutations.
  repo <init|clone|check|configure|agent-guidance|installer-template> [options]
    Create, clone, check, and configure repository baselines and guidance.
  gh <area> <command> [options]
    Manage GitHub issues, PRs, branches, and repository hygiene.

Release and sharing:
  release <check|plan|notes|publish> --version <version> [options]
    Inspect release readiness, plan, notes, and guarded GitHub publishing.
  export-context [project] [options]
    Export a project's .ai-context directory as Markdown or Zip.
  devcontainer [project] [options]
    Preview or write .devcontainer/devcontainer.json from a Base manifest.
  devenv-report [project] [options]
    Report Nix/devenv compatibility for a Base manifest.
  prompt <list|name> [options]
    Print repo-owned Markdown prompts for AI-assisted Base workflows.
  docs [options]
    Open the Base documentation home page on GitHub.

Diagnostics and maintenance:
  config <path|show|doctor>
    Inspect Base's machine-local user config.
  logs [options]
    List and open recent Base CLI runtime logs.
  history [options]
    List recent Base command history records.
  clean [--older-than <age>] [--keep-last <count>] [options]
    Remove old Base CLI runtime logs, temp files, and cache entries.
  update-profile [options]
    Create or update Base-managed sections in Bash and Zsh startup files.
  update [project] [options]
    Update Base from Git and run setup.

Compatibility:
  ci <setup|check|doctor> [project] [options]
    Compatibility alias for setup, check, and doctor --ci.

Other:
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
  Advanced startup diagnostics; normal command flags are documented by leaf help.
  --debug-wrapper    Enable DEBUG logging before the Base runtime is loaded.
  --verbose-wrapper  Enable verbose runtime argument handling before dispatch.
  --utc-wrapper      Print wrapper/runtime log timestamps in UTC.
  --color            Preserve color-aware wrapper argument handling.

Notes:
  - `basectl setup` is the preferred entrypoint for machine bootstrap.
  - `basectl check` verifies the same local requirements without making changes.
    Pass a project name to include that project's manifest artifacts.
  - Use space-separated values for long options, for example `--format json`.
    Base rejects `--option=value` syntax before command delegation. Arguments
    after `--` belong to the delegated project command.
  - Use `-v` for command-level debug logs. Python package standard options such
    as `--debug`, `--quiet`, `--log-file`, `--config`, `--environment`, and
    `--keep-temp` are not public `basectl` options.
  - Invoking `basectl` with no command starts a Base runtime shell for the
    nearest project manifest above the current directory, preserving that
    directory. If no manifest is found, it falls back to project `base`. In
    non-interactive shells it prints this help text.
  - Use `--debug-wrapper` when debugging startup before command dispatch or
    Base runtime initialization.
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

basectl_bare_script_usage_error() {
    local candidate="$1"
    local explicit_path

    printf -v explicit_path '%q' "./$candidate"
    printf "ERROR: Bare script name '%s' is not executed implicitly.\n" "$candidate" >&2
    printf 'Use an explicit path instead:\n' >&2
    printf '  basectl %s\n' "$explicit_path" >&2
    return 2
}

basectl_equals_option_usage_error() {
    local argument="$1"
    local option="${argument%%=*}"
    local value="${argument#*=}"

    if [[ -n "$value" ]]; then
        basectl_usage_error "Option '$option' uses unsupported equals syntax. Use '$option $value' instead."
    else
        basectl_usage_error "Option '$option' uses unsupported equals syntax. Pass its value as the next argument."
    fi
}

basectl_reject_equals_option_values() {
    local argument

    for argument in "$@"; do
        [[ "$argument" == "--" ]] && return 0
        case "$argument" in
            --?*=*)
                basectl_equals_option_usage_error "$argument"
                return $?
                ;;
        esac
    done

    return 0
}

basectl_private_standard_option_usage_error() {
    local option="$1"

    case "$option" in
        --debug)
            basectl_usage_error "Option '--debug' is not supported by basectl. Use '-v' for command-level debug logs or '--debug-wrapper' for wrapper startup logging."
            ;;
        *)
            basectl_usage_error "Option '$option' is not supported by basectl. Use command-specific options shown by 'basectl <command> --help'."
            ;;
    esac
}

basectl_reject_private_standard_options() {
    local argument

    for argument in "$@"; do
        [[ "$argument" == "--" ]] && return 0
        case "$argument" in
            --debug|--quiet|--log-file|--config|--environment|--keep-temp)
                basectl_private_standard_option_usage_error "$argument"
                return $?
                ;;
        esac
    done

    return 0
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
        # shellcheck disable=SC2034 # Read by the caller after this helper returns non-zero.
        BASE_CLI_ERROR_MESSAGE="Base home '$base_home' is not a directory."
        return 1
    fi

    for file in "${BASECTL_REQUIRED_HOME_FILES[@]}"; do
        if [[ ! -f "$base_home/$file" ]]; then
            missing+=("$file")
        fi
    done

    if (( ${#missing[@]} > 0 )); then
        # shellcheck disable=SC2034 # Read by the caller after this helper returns non-zero.
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

basectl_do_export_context() {
    basectl_source_subcommand_module export_context || return 1
    base_export_context_subcommand_main "$@"
}

basectl_do_devcontainer() {
    basectl_source_subcommand_module devcontainer || return 1
    base_devcontainer_subcommand_main "$@"
}

basectl_do_devenv_report() {
    basectl_source_subcommand_module devenv_report || return 1
    base_devenv_report_subcommand_main "$@"
}

basectl_do_build() {
    basectl_source_subcommand_module build || return 1
    base_build_subcommand_main "$@"
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

basectl_do_ci() {
    basectl_source_subcommand_module ci || return 1
    base_ci_subcommand_main "$@"
}

basectl_do_release() {
    basectl_source_subcommand_module release || return 1
    base_release_subcommand_main "$@"
}

basectl_do_prompt() {
    basectl_source_subcommand_module prompt || return 1
    base_prompt_subcommand_main "$@"
}

basectl_do_docs() {
    basectl_source_subcommand_module docs || return 1
    base_docs_subcommand_main "$@"
}

basectl_do_clean() {
    basectl_source_subcommand_module clean || return 1
    base_clean_subcommand_main "$@"
}

basectl_do_logs() {
    basectl_source_subcommand_module logs || return 1
    base_logs_subcommand_main "$@"
}

basectl_do_history() {
    basectl_source_subcommand_module history || return 1
    base_history_subcommand_main "$@"
}

basectl_do_config() {
    basectl_source_subcommand_module config || return 1
    base_config_subcommand_main "$@"
}

basectl_do_trust() {
    basectl_source_subcommand_module trust || return 1
    base_trust_subcommand_main "$@"
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

basectl_do_workspace() {
    basectl_source_subcommand_module workspace || return 1
    base_workspace_subcommand_main "$@"
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
    case "${1:-}" in
        "")
            ;;
        -h|--help|help)
            (($# == 1)) || {
                basectl_error "version does not accept arguments."
                printf "Run 'basectl version --help' for usage.\n" >&2
                return 2
            }
            cat <<'EOF'
Usage:
  basectl version

Purpose:
  Show the installed Base version.

Options:
  -h, --help  Show this help text.
EOF
            return 0
            ;;
        *)
            basectl_error "version does not accept arguments."
            printf "Run 'basectl version --help' for usage.\n" >&2
            return 2
            ;;
    esac

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
        if resolve_output="$("$wrapper" --project base base_projects current --format command-protocol 2>/dev/null)" &&
            base_command_protocol_decode_one project-reference "$resolve_output" 2>/dev/null; then
            project_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
            if [[ -n "$project_name" ]]; then
                printf '%s\n' "$project_name"
                return 0
            fi
        fi
    fi

    printf '%s\n' base
}

basectl_history_recordable_command() {
    case "$1" in
        ""|help|history|logs|version)
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

basectl_args_request_help() {
    local argument
    for argument in "$@"; do
        [[ "$argument" == "-h" || "$argument" == "--help" ]] && return 0
    done
    return 1
}

basectl_cache_root() {
    if [[ -n "${BASE_CACHE_DIR:-}" ]]; then
        printf '%s\n' "${BASE_CACHE_DIR%/}"
        return 0
    fi
    if [[ "$(uname -s 2>/dev/null || true)" == Darwin ]]; then
        printf '%s\n' "$HOME/Library/Caches/base"
    else
        printf '%s\n' "$HOME/.cache/base"
    fi
}

basectl_initialize_run_bundle() {
    local cache_root run_id run_root

    if [[ -n "${BASE_CLI_RUN_ROOT:-}" ]]; then
        export BASE_CLI_RUNTIME_OWNER=base
        export BASE_CLI_RUN_ID="${BASE_CLI_RUN_ID:-$(basename -- "$BASE_CLI_RUN_ROOT")}"
        export BASE_CLI_PRIMARY_LOG="${BASE_CLI_PRIMARY_LOG:-$BASE_CLI_RUN_ROOT/logs/primary.log}"
        export BASE_CLI_HISTORY_PARENT_RUN_ID="${BASE_CLI_HISTORY_PARENT_RUN_ID:-$BASE_CLI_RUN_ID}"
        return 0
    fi

    cache_root="$(basectl_cache_root)"
    run_id="$(date -u +%Y%m%dT%H%M%S 2>/dev/null || true)_${BASHPID:-$$}_${RANDOM}"
    run_root="$cache_root/base/runs/$run_id"
    mkdir -p "$run_root/logs" "$run_root/tmp" || {
        basectl_error "Unable to create Base run bundle '$run_root'. Check BASE_CACHE_DIR permissions."
        return 1
    }

    export BASE_CLI_RUNTIME_OWNER=base
    export BASE_CLI_RUN_ID="$run_id"
    export BASE_CLI_RUN_ROOT="$run_root"
    export BASE_CLI_PRIMARY_LOG="$run_root/logs/primary.log"
    export BASE_CLI_HISTORY_PARENT_RUN_ID="$run_id"
    printf '{"run_id":"%s","owner":"base","status":"running","started_at":"%s"}\n' \
        "$run_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || true)" >"$run_root/run.json"
    printf '%s basectl start run_id=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || true)" "$run_id" >>"$BASE_CLI_PRIMARY_LOG"
}

basectl_finalize_run_bundle() {
    local exit_code="$1" run_root tmp_file

    run_root="${BASE_CLI_RUN_ROOT:-}"
    [[ -n "$run_root" && -d "$run_root" ]] || return 0
    printf '%s basectl finish status=%s exit_code=%s\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || true)" \
        "$([[ "$exit_code" == 0 ]] && printf ok || printf error)" "$exit_code" >>"${BASE_CLI_PRIMARY_LOG:-$run_root/logs/primary.log}"
    tmp_file="$run_root/run.json.tmp"
    printf '{"run_id":"%s","owner":"base","status":"%s","exit_code":%s,"started_at":"%s","ended_at":"%s"}\n' \
        "${BASE_CLI_RUN_ID:-$(basename -- "$run_root")}" \
        "$([[ "$exit_code" == 0 ]] && printf ok || printf error)" "$exit_code" \
        "${BASE_CLI_HISTORY_STARTED_AT:-}" \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || true)" >"$tmp_file" && mv -f "$tmp_file" "$run_root/run.json"
}

basectl_history_record() {
    local command="$1"
    local exit_code="$2"
    local scope="$3"
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local args=()
    shift 3

    basectl_history_recordable_command "$command" || return 0
    [[ -x "$wrapper" ]] || return 0

    args+=(--command "$command")
    args+=(--run-id "${BASE_CLI_HISTORY_PARENT_RUN_ID:-}")
    args+=(--exit-code "$exit_code")
    args+=(--scope "$scope")
    args+=(--owner "${BASE_CLI_RUNTIME_OWNER:-base}")
    if [[ -n "${BASE_CLI_RUN_ROOT:-}" ]]; then
        args+=(--bundle-path "$BASE_CLI_RUN_ROOT")
    fi
    if [[ -n "${BASE_CLI_HISTORY_STARTED_AT:-}" ]]; then
        args+=(--started-at "$BASE_CLI_HISTORY_STARTED_AT")
    fi
    if [[ -n "${BASE_CLI_HISTORY_PROJECT:-}" ]]; then
        args+=(--project "$BASE_CLI_HISTORY_PROJECT")
    fi
    if [[ -n "${BASE_CLI_HISTORY_PROJECT_ROOT:-}" ]]; then
        args+=(--project-root "$BASE_CLI_HISTORY_PROJECT_ROOT")
    fi
    if [[ -n "${BASE_CLI_HISTORY_MANIFEST:-}" ]]; then
        args+=(--manifest "$BASE_CLI_HISTORY_MANIFEST")
    fi

    "$wrapper" --project base base_history.record "${args[@]}" -- basectl "$command" "$@" >/dev/null 2>&1 || true
}


basectl_main() {
    local base_debug=0 command="" command_status run_bundle_enabled=1
    local history_args=() history_scope="${BASE_CLI_HISTORY_SCOPE:-primary}"
    local opt

    if [[ "${1:-}" == "help" ]]; then
        shift
        if [[ $# -eq 0 || "${1:-}" == "help" ]]; then
            basectl_show_help
            return 0
        fi
        set -- "$@" --help
    fi

    if [[ "${1:-}" =~ ^(-h|--help|-help)$ ]]; then
        basectl_show_help
        return 0
    fi

    if [[ "${1:-}" == "--version" ]]; then
        if (($# != 1)); then
            basectl_usage_error "Option '--version' does not accept arguments."
            return $?
        fi
        basectl_get_base_home || return 1
        basectl_do_version
        return 0
    fi

    if [[ "${1:-}" == "--describe" ]]; then
        basectl_describe
        return 0
    fi

    case "${1:-}" in
        --?*=*)
            basectl_equals_option_usage_error "$1"
            return $?
            ;;
        --debug|--quiet|--log-file|--config|--environment|--keep-temp)
            basectl_private_standard_option_usage_error "$1"
            return $?
            ;;
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
    history_args=("$@")

    basectl_reject_equals_option_values "$@" || return $?
    basectl_reject_private_standard_options "$@" || return $?
    basectl_args_request_help "$@" && run_bundle_enabled=0
    basectl_history_recordable_command "$command" || run_bundle_enabled=0

    basectl_get_base_home || return 1
    if ((run_bundle_enabled)); then
        basectl_initialize_run_bundle || return 1
    fi
    export BASE_CLI_HISTORY_SCOPE=internal
    BASE_CLI_HISTORY_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || true)"
    export BASE_CLI_HISTORY_STARTED_AT
    ((base_debug)) && basectl_enable_debug_logging
    log_debug "Running basectl command '${command:-<none>}' with args: $*"

    case "$command" in
        activate)         basectl_do_activate "$@"; command_status=$? ;;
        check)            basectl_do_check "$@"; command_status=$? ;;
        test)             basectl_do_test "$@"; command_status=$? ;;
        export-context)   basectl_do_export_context "$@"; command_status=$? ;;
        devcontainer)     basectl_do_devcontainer "$@"; command_status=$? ;;
        devenv-report)    basectl_do_devenv_report "$@"; command_status=$? ;;
        build)            basectl_do_build "$@"; command_status=$? ;;
        demo)             basectl_do_demo "$@"; command_status=$? ;;
        run)              basectl_do_run "$@"; command_status=$? ;;
        repo)             basectl_do_repo "$@"; command_status=$? ;;
        ci)               basectl_do_ci "$@"; command_status=$? ;;
        release)          basectl_do_release "$@"; command_status=$? ;;
        prompt)           basectl_do_prompt "$@"; command_status=$? ;;
        docs)             basectl_do_docs "$@"; command_status=$? ;;
        clean)            basectl_do_clean "$@"; command_status=$? ;;
        logs)             basectl_do_logs "$@"; command_status=$? ;;
        history)          basectl_do_history "$@"; command_status=$? ;;
        config)           basectl_do_config "$@"; command_status=$? ;;
        trust)            basectl_do_trust "$@"; command_status=$? ;;
        doctor)           basectl_do_doctor "$@"; command_status=$? ;;
        gh)               basectl_do_gh "$@"; command_status=$? ;;
        onboard)          basectl_do_onboard "$@"; command_status=$? ;;
        setup)            basectl_do_setup "$@"; command_status=$? ;;
        help)             basectl_show_help; command_status=$? ;;
        projects)         basectl_do_projects "$@"; command_status=$? ;;
        workspace)        basectl_do_workspace "$@"; command_status=$? ;;
        update)           basectl_do_update "$@"; command_status=$? ;;
        update-profile)   basectl_do_update_profile "$@"; command_status=$? ;;
        version)          basectl_do_version "$@"; command_status=$? ;;
        "")
            if basectl_should_start_shell; then
                BASE_ACTIVATE_PRESERVE_CWD=1 basectl_do_activate "$(basectl_default_activate_project)"
                command_status=$?
            else
                basectl_show_help
                command_status=$?
            fi
            ;;
        *)
            if [[ -f "$command" ]]; then
                basectl_bare_script_usage_error "$command"
            else
                basectl_usage_error "Unrecognized command: $command"
            fi
            command_status=$?
            ;;
    esac

    if ((run_bundle_enabled)); then
        basectl_finalize_run_bundle "$command_status"
        basectl_history_record "$command" "$command_status" "$history_scope" "${history_args[@]}"
    fi
    return "$command_status"
}

main() {
    basectl_main "$@"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
