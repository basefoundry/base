#!/usr/bin/env bash

base_cli_error() {
    printf 'ERROR: %s\n' "$*" >&2
}

base_cli_show_help() {
    cat <<'EOF'
Usage: base [options] <command> [args...]

Commands:
  setup [options]
    Install and bootstrap the local Base CLI environment on macOS.
  check [options]
    Verify the local Base CLI environment without making changes.
  update-profile [options]
    Reserved for future shell profile updates.
  install
    Install Base into BASE_HOME.
  embrace
    Symlink shell startup files from Base into the user's home directory.
  update
    Run git pull in BASE_HOME.
  run <command> [args...]
    Initialize Base and run the given command.
  status
    Check whether Base is installed at BASE_HOME.
  shell
    Start an interactive Bash shell using Base's managed startup files.
  set-team TEAM
    Set BASE_TEAM in ~/.baserc.
  set-shared-teams TEAM...
    Set BASE_SHARED_TEAMS in ~/.baserc.
  version
    Show the Base CLI version.
  man
    Print one-line summaries for wrapped Base scripts.
  help
    Show this help text.

Options:
  -b DIR   Use DIR as BASE_HOME.
  -t TEAM  Use TEAM as BASE_TEAM.
  -s TEAM  Use TEAM as BASE_SHARED_TEAMS (space-delimited for multiple teams).
  -f       Force install by moving aside an existing BASE_HOME directory.
  -v       Enable DEBUG logging for the selected command.
  -V       Show the CLI version.
  -x       Enable Bash xtrace before running the command.
  -h       Show this help text.

Notes:
  - `base setup` is the preferred entrypoint for machine bootstrap.
  - `base check` verifies the same local requirements without making changes.
  - Invoking `base` with no command opens an interactive shell when attached to
    a terminal; otherwise it prints this help text.
EOF
}

base_cli_describe() {
    printf '%s\n' "Base umbrella CLI"
}

base_cli_usage_error() {
    base_cli_error "$*"
    base_cli_show_help >&2
    return 2
}

base_cli_source_user_baserc() {
    [[ -f "$HOME/.baserc" ]] || return 0
    [[ -n "${__base_cli_user_baserc_sourced__:-}" ]] && return 0

    # shellcheck source=/dev/null
    source "$HOME/.baserc"
    readonly __base_cli_user_baserc_sourced__=1
}

base_cli_get_base_home() {
    [[ -n "${HOME:-}" ]] || {
        base_cli_error "Environment variable 'HOME' is not set."
        return 1
    }
    [[ -d "$HOME" ]] || {
        base_cli_error "\$HOME '$HOME' is not a directory."
        return 1
    }

    base_cli_source_user_baserc || return 1
    BASE_HOME="${BASE_HOME:-$HOME/base}"
    export BASE_HOME
}

base_cli_verify_repo() {
    local repo_root="$1"
    local file missing=()

    if [[ ! -d "$repo_root" ]]; then
        BASE_CLI_ERROR_MESSAGE="Base is not installed at '$repo_root'"
        return 1
    fi

    if ! git -C "$repo_root" rev-parse --git-dir >/dev/null 2>&1; then
        BASE_CLI_ERROR_MESSAGE="Directory '$repo_root' is not a git repo; check if Base is installed."
        return 1
    fi

    for file in base_init.sh lib/shell/bash_profile lib/shell/bashrc bin/base-wrapper; do
        if [[ ! -f "$repo_root/$file" ]]; then
            missing+=("$file")
        fi
    done

    if (( ${#missing[@]} > 0 )); then
        BASE_CLI_ERROR_MESSAGE="Files missing in Base repo: ${missing[*]}"
        return 1
    fi

    return 0
}

base_cli_runtime_repo_root() {
    if base_cli_verify_repo "$BASE_HOME"; then
        printf '%s\n' "$BASE_HOME"
        return 0
    fi

    if base_cli_verify_repo "$BASE_REPO_ROOT"; then
        printf '%s\n' "$BASE_REPO_ROOT"
        return 0
    fi

    return 1
}

base_cli_shell_profile_path() {
    local repo_root

    repo_root="$(base_cli_runtime_repo_root)" || return 1
    printf '%s\n' "$repo_root/lib/shell/bash_profile"
}

base_cli_patch_baserc() {
    local var value marker baserc baserc_temp grep_expr=""
    local base_text_array=()

    marker="# BASE_MARKER, do not delete"
    baserc="$HOME/.baserc"
    baserc_temp="$HOME/.baserc.temp"

    for var in "$@"; do
        value="${!var:-}"
        if [[ -n "$value" ]]; then
            base_text_array+=("export $var=\"$value\" $marker")
        fi
        if [[ -n "$grep_expr" ]]; then
            grep_expr="$grep_expr|$var=.*$marker"
        else
            grep_expr="$var=.*$marker"
        fi
    done

    [[ -f "$baserc" ]] || safe_touch "$baserc"

    rm -f -- "$baserc_temp"
    if [[ -n "$grep_expr" ]]; then
        grep -Ev -- "$grep_expr" "$baserc" > "$baserc_temp"
    else
        safe_touch "$baserc_temp"
    fi
    [[ -f "$baserc_temp" ]] || {
        base_cli_error "Couldn't create '$baserc_temp'."
        return 1
    }

    if (( ${#base_text_array[@]} > 0 )); then
        printf '%s\n' "${base_text_array[@]}" >> "$baserc_temp" || {
            base_cli_error "Couldn't append to '$baserc_temp'."
            return 1
        }
    fi

    mv -f -- "$baserc_temp" "$baserc" || {
        base_cli_error "Couldn't overwrite '$baserc'."
        return 1
    }

    return 0
}

base_cli_version_value() {
    if [[ -n "${BASE_VERSION:-}" ]]; then
        printf '%s\n' "$BASE_VERSION"
        return 0
    fi

    if git -C "$BASE_REPO_ROOT" rev-parse --short HEAD >/dev/null 2>&1; then
        git -C "$BASE_REPO_ROOT" rev-parse --short HEAD
        return 0
    fi

    printf '%s\n' "dev"
}

base_cli_do_version() {
    printf 'base version %s\n' "$(base_cli_version_value)"
}

base_cli_enable_debug_logging() {
    set_log_level DEBUG
    export LOG_DEBUG=1
}

base_cli_source_subcommand_module() {
    local module_name="$1"
    local subcommand_script="$__SCRIPT_DIR__/subcommands/${module_name}.sh"

    [[ -f "$subcommand_script" ]] || {
        base_cli_error "Subcommand module '$subcommand_script' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$subcommand_script"
}

base_cli_do_setup() {
    base_cli_source_subcommand_module setup || return 1
    base_setup_subcommand_main "$@"
}

base_cli_do_check() {
    base_cli_source_subcommand_module check || return 1
    base_check_subcommand_main "$@"
}

base_cli_do_update_profile() {
    base_cli_source_subcommand_module update_profile || return 1
    base_update_profile_subcommand_main "$@"
}

base_cli_do_install() {
    local repo_url="ssh://git@github.com:codeforester/base.git"
    local base_home_backup=""

    if [[ -d "$BASE_HOME" ]]; then
        if (( force_install )); then
            base_home_backup="$BASE_HOME.$current_time"
            mv -- "$BASE_HOME" "$base_home_backup" || {
                base_cli_error "Couldn't move current Base home directory '$BASE_HOME' to '$base_home_backup'."
                return 1
            }
            printf "Moved current Base home directory '%s' to '%s'\n" "$BASE_HOME" "$base_home_backup"
        else
            printf "Base is already installed at '%s'\n" "$BASE_HOME"
            return 0
        fi
    fi

    git clone "$repo_url" "$BASE_HOME" || {
        base_cli_error "Couldn't install Base."
        return 1
    }
    printf "Installed Base at '%s'\n" "$BASE_HOME"

    BASE_TEAM="${base_team:-${BASE_TEAM:-}}"
    BASE_SHARED_TEAMS="${base_shared_teams:-${BASE_SHARED_TEAMS:-}}"
    base_cli_patch_baserc BASE_HOME BASE_TEAM BASE_SHARED_TEAMS || return 1

    return 0
}

base_cli_do_embrace() {
    local base_bash_profile base_bashrc
    local bash_profile bashrc
    local bash_profile_link="" bashrc_link=""
    local bash_profile_backup="" bashrc_backup=""

    if ! base_cli_verify_repo "$BASE_HOME"; then
        if base_cli_verify_repo "$BASE_REPO_ROOT"; then
            BASE_HOME="$BASE_REPO_ROOT"
            export BASE_HOME
        else
            base_cli_error "$BASE_CLI_ERROR_MESSAGE"
            return 1
        fi
    fi

    base_bash_profile="$BASE_HOME/lib/shell/bash_profile"
    base_bashrc="$BASE_HOME/lib/shell/bashrc"
    bash_profile="$HOME/.bash_profile"
    bashrc="$HOME/.bashrc"

    [[ -L "$bash_profile" ]] && bash_profile_link="$(readlink "$bash_profile")"
    [[ -L "$bashrc" ]] && bashrc_link="$(readlink "$bashrc")"

    if [[ "$bash_profile_link" == "$base_bash_profile" ]]; then
        printf '%s\n' "$bash_profile is already symlinked to $base_bash_profile"
    else
        if [[ -f "$bash_profile" ]]; then
            bash_profile_backup="$HOME/.bash_profile.$current_time"
            printf "Backing up %s to %s and overriding it with %s\n" "$bash_profile" "$bash_profile_backup" "$base_bash_profile"
            cp -- "$bash_profile" "$bash_profile_backup" || {
                base_cli_error "Can't create a backup of $bash_profile."
                return 1
            }
        fi
        ln -sf -- "$base_bash_profile" "$bash_profile" || {
            base_cli_error "Couldn't symlink '$bash_profile' to '$base_bash_profile'."
            return 1
        }
        printf "Symlinked '%s' to '%s'\n" "$bash_profile" "$base_bash_profile"
    fi

    if [[ "$bashrc_link" == "$base_bashrc" ]]; then
        printf '%s\n' "$bashrc is already symlinked to $base_bashrc"
    else
        if [[ -f "$bashrc" ]]; then
            bashrc_backup="$HOME/.bashrc.$current_time"
            printf "Backing up %s to %s and overriding it with %s\n" "$bashrc" "$bashrc_backup" "$base_bashrc"
            cp -- "$bashrc" "$bashrc_backup" || {
                base_cli_error "Can't create a backup of $bashrc."
                return 1
            }
        fi
        ln -sf -- "$base_bashrc" "$bashrc" || {
            base_cli_error "Couldn't symlink '$bashrc' to '$base_bashrc'."
            return 1
        }
        printf "Symlinked '%s' to '%s'\n" "$bashrc" "$base_bashrc"
    fi

    return 0
}

base_cli_do_update() {
    if ! base_cli_verify_repo "$BASE_HOME"; then
        if base_cli_verify_repo "$BASE_REPO_ROOT"; then
            BASE_HOME="$BASE_REPO_ROOT"
            export BASE_HOME
        else
            base_cli_error "$BASE_CLI_ERROR_MESSAGE"
            return 1
        fi
    fi

    git -C "$BASE_HOME" pull
}

base_cli_do_run() {
    local repo_root

    (($# > 0)) || {
        base_cli_usage_error "Usage: base run COMMAND [ARGS ...]"
        return $?
    }

    repo_root="$(base_cli_runtime_repo_root)" || {
        base_cli_error "$BASE_CLI_ERROR_MESSAGE"
        return 1
    }

    BASE_HOME="$repo_root"
    export BASE_HOME

    # shellcheck source=/dev/null
    source "$repo_root/base_init.sh" || return 1
    "$@"
}

base_cli_do_status() {
    if [[ ! -d "$BASE_HOME" ]]; then
        printf "Base is not installed at '%s'\n" "$BASE_HOME"
        return 1
    fi

    if ! base_cli_verify_repo "$BASE_HOME"; then
        base_cli_error "$BASE_CLI_ERROR_MESSAGE"
        return 1
    fi

    printf 'Base is installed at %s\n' "$BASE_HOME"
    return 0
}

base_cli_do_shell() {
    local shell_profile

    shell_profile="$(base_cli_shell_profile_path)" || {
        base_cli_error "$BASE_CLI_ERROR_MESSAGE"
        return 1
    }

    BASE_HOME="$(cd -- "$(dirname -- "$shell_profile")/../.." && pwd -P)"
    export BASE_HOME
    export BASE_SHELL=1
    exec bash --rcfile "$shell_profile"
}

base_cli_do_man() {
    local repo_root dir bin desc team
    local -a dirs
    local -A teams=()

    repo_root="$(base_cli_runtime_repo_root)" || {
        base_cli_error "$BASE_CLI_ERROR_MESSAGE"
        return 1
    }

    add_to_path -p "$repo_root/bin"
    if ! command -v base-wrapper >/dev/null 2>&1; then
        base_cli_error "base-wrapper needs to be in your PATH to run this command."
        return 1
    fi

    dirs=(bin company/bin)
    [[ -n "${base_team:-}" ]] || base_team="${BASE_TEAM:-}"
    if [[ -n "${base_team:-}" ]]; then
        dirs+=(team/"$base_team"/bin)
        teams["$base_team"]=1
    fi

    for team in ${BASE_SHARED_TEAMS:-} "${BASE_SHARED_TEAMS[@]:-}"; do
        [[ -n "$team" ]] || continue
        [[ -n "${teams[$team]:-}" ]] && continue
        dirs+=(team/"$team"/bin)
        teams["$team"]=1
    done

    for dir in "${dirs[@]}"; do
        dir="$repo_root/$dir"
        [[ -d "$dir" ]] || continue
        cd -- "$dir" || continue
        printf '%s\n' "${dir#$repo_root/}:"
        for bin in *; do
            [[ -f "$bin" ]] || continue
            if head -1 "$bin" | grep -Eq '!/usr/bin/env[[:space:]]+base-wrapper[[:space:]]*'; then
                desc="$(./"$bin" --describe 2>/dev/null || true)"
                printf '\t\t%s\n' "$bin: $desc"
            fi
        done
    done
}

base_cli_do_set_team() {
    if (($# > 1)); then
        base_cli_usage_error "Got too many arguments for set-team."
        return $?
    fi

    if (($# == 1)); then
        BASE_TEAM="$1"
    else
        BASE_TEAM="${base_team:-}"
    fi

    [[ -n "${BASE_TEAM:-}" ]] || {
        base_cli_usage_error "Usage: base set-team TEAM"
        return $?
    }

    base_cli_patch_baserc BASE_TEAM
}

base_cli_do_set_shared_teams() {
    if (($# > 0)); then
        BASE_SHARED_TEAMS="$*"
    elif [[ -n "${base_shared_teams:-}" ]]; then
        BASE_SHARED_TEAMS="$base_shared_teams"
    else
        base_cli_usage_error "Usage: base set-shared-teams TEAM ..."
        return $?
    fi

    base_cli_patch_baserc BASE_SHARED_TEAMS
}

base_cli_main() {
    local base_debug=0 bash_version current_time_fmt command=""
    local opt

    if [[ "${1:-}" =~ ^(-h|--help|-help|help)$ ]]; then
        base_cli_show_help
        return 0
    fi

    if [[ "${1:-}" =~ ^(--version|-version|-V)$ ]]; then
        base_cli_do_version
        return 0
    fi

    if [[ "${1:-}" == "--describe" ]]; then
        base_cli_describe
        return 0
    fi

    force_install=0
    bash_version="${BASH_VERSINFO[0]}${BASH_VERSINFO[1]}"
    current_time_fmt="%Y-%m-%d:%H:%M:%S"
    if (( bash_version >= 42 )); then
        printf -v current_time "%($current_time_fmt)T" -1
    else
        current_time="$(date +"$current_time_fmt")"
    fi

    OPTIND=1
    while getopts "fhb:s:t:vVx" opt; do
        case "$opt" in
            b) export BASE_HOME="$OPTARG" ;;
            t) export base_team="$OPTARG" ;;
            s) export base_shared_teams="$OPTARG" ;;
            f) force_install=1 ;;
            v) base_debug=1 ;;
            V)
                base_cli_do_version
                return 0
                ;;
            x) set -x ;;
            h)
                base_cli_show_help
                return 0
                ;;
            *)
                base_cli_show_help >&2
                return 2
                ;;
        esac
    done
    shift $((OPTIND - 1))

    command="${1:-}"
    [[ -n "$command" ]] && shift

    base_cli_get_base_home || return 1
    ((base_debug)) && base_cli_enable_debug_logging
    log_debug "Running base command '${command:-<none>}' with args: $*"

    case "$command" in
        check)            base_cli_do_check "$@" ;;
        setup)            base_cli_do_setup "$@" ;;
        embrace)          base_cli_do_embrace ;;
        help)             base_cli_show_help ;;
        install)          base_cli_do_install ;;
        man)              base_cli_do_man ;;
        run)              base_cli_do_run "$@" ;;
        set-shared-teams) base_cli_do_set_shared_teams "$@" ;;
        set-team)         base_cli_do_set_team "$@" ;;
        shell)            base_cli_do_shell ;;
        status)           base_cli_do_status ;;
        update)           base_cli_do_update ;;
        update-profile)   base_cli_do_update_profile "$@" ;;
        version)          base_cli_do_version ;;
        "")
            if is_interactive; then
                base_cli_do_shell
            else
                base_cli_show_help
            fi
            ;;
        *)
            base_cli_usage_error "Unrecognized command: $command"
            ;;
    esac
}

base_cli_main "$@"
