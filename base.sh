#!/usr/bin/env bash

#
# base.sh
#
# This is a wrapper or a common entry point for Base. It helps in two main ways:
#
# 1. Install base or change Base settings  (install, embrace, set-team, set-shared-teams)
# 2. Do things with the installed version of Base (status, run, shell)
#
# In shell mode, we would create a Bash shell:
# a) using Base's bash_profile in case Base is installed
# b) using the in-line common bash_profile in case Base is not installed
#

error_exit()    { printf 'ERROR: %s\n' "$@" >&2; exit 1; }
exit_if_error() { local ec=$1; shift; (($ec)) && error_exit "$@"; }
cd_base()       { cd -- "$BASE_HOME" || exit_if_error 1 "Can't cd to BASE_HOME at '$BASE_HOME'"; }
usage_error() {
    printf '%s\n' "$@" >&2
    show_common_help >&2
    exit 2
}

show_common_help() {
    cat << EOF
Usage: base [-b DIR] [-t TEAM] [-x] [install|embrace|update|run|status|shell|set-team|set-shared-teams|version|help] ...
-b DIR     - use DIR as BASE_HOME directory
-t TEAM    - use TEAM as BASE_TEAM
-s TEAM    - use TEAM as BASE_SHARED_TEAMS [use space delimited strings for multiple teams]
-f         - ignore the existing installation and force install [relevant only for 'base install' command]
-v         - show the CLI version
-x         - turn on bash debug mode

install               - install Base
embrace               - override .bash_profile and .bashrc so that Base gets enabled upon login
update                - update Base by running 'git pull' in BASE_HOME directory
run                   - run the rest of the command line after initializing Base
shell                 - if Base is installed, create an interactive Bash shell with Base initialized
                        if Base is not installed, create an interactive Bash shell with default settings
status                - check if Base is installed or not
set-team TEAM         - set BASE_TEAM in $HOME/.baserc
set-shared-teams TEAM - set shared BASE_SHARED_TEAMS in $HOME/.baserc [use space delimited strings for multiple teams]
version               - show the CLI version
help                  - show this help message
man                  - print one line summary of all Base scripts, use '-t team' to filter by team

Invoking without any arguments would result in an interactive Bash shell with default settings.
EOF
}

base_init() {
    local base_init=$BASE_HOME/base_init.sh
    [[ -f $base_init ]] && source "$base_init"
}

get_base_home() {
    if [[ ! $HOME ]]; then
        error_exit "Environment variable 'HOME' is not set!"
    fi
    if [[ ! -d $HOME ]]; then
        error_exit "\$HOME '$HOME' is not a directory!"
    fi

    # if BASE_HOME is not already set, source .baserc to see it is defined there
    if [[ ! $BASE_HOME ]]; then
        local baserc=$HOME/.baserc
        [[ -f $baserc ]] && source "$baserc"
    fi

    # if BASE_HOME is still not set, go with the default value
    BASE_HOME=${BASE_HOME:-$HOME/base}
}

create_base_home() {
    # if set, BASE_HOME must hold a directory name
    if [[ -e $BASE_HOME && ! -d $BASE_HOME ]]; then
        error_exit "$BASE_HOME exists but it is not a directory!"
    else
        mkdir -- "$BASE_HOME"
        exit_if_error $? "Can't create directory '$BASE_HOME'"
    fi
}

verify_base() {
    # now make sure BASE_HOME directory is actually a git repo
    local git=$BASE_HOME/.git
    if [[ ! -d $git ]]; then
        glb_error_message="Directory '$BASE_HOME' isn't a git repo; check if Base is installed"
        return 1
    else
        local oldpwd=$PWD
        cd -- "$git" || { glb_error_message="Can't cd to '$git' directory"; return 1; }
        if ! git rev-parse --git-dir &>/dev/null; then
            glb_error_message="Directory '$git' isn't a git repo; check if Base is installed"
            return 1
        fi
        local file missing=()
        for file in base_init.sh lib/shell/bash_profile lib/shell/bashrc; do
            if [[ ! -f $BASE_HOME/$file ]]; then
                missing+=($file)
            fi
        done
        cd -- "$oldpwd"
        if (( ${#missing[@]} > 0)); then
            glb_error_message="Files missing in Base repo: ${missing[@]}"
            return 1
        fi
    fi
    return 0
}

patch_baserc() {
    local var value base_text_array=() grep_expr
    local marker="# BASE_MARKER, do not delete"
    local baserc=$HOME/.baserc baserc_temp=$HOME/.baserc.temp
    for var; do
        value=${!var}
        if [[ $value ]]; then
            base_text_array+=("export $var=\"$value\" $marker")
        fi
        if [[ $grep_expr ]]; then
            grep_expr="$grep_expr|$var=.*$marker"
        else
            grep_expr="$var=.*$marker"
        fi
    done
    if [[ ! -f $baserc ]]; then
        touch -- "$baserc"
        exit_if_error $? "Couldn't create '$baserc'"
    fi
    rm -f "$baserc_temp"
    if [[ $grep_expr ]]; then
        grep -Ev -- "$grep_expr" "$baserc" > "$baserc_temp"
    else
        touch -- "$baserc_temp"
    fi
    [[ -f $baserc_temp ]] || exit_if_error 1 "Couldn't create '$baserc_temp'"
    printf '%s\n' "${base_text_array[@]}" >> "$baserc_temp"
    exit_if_error $? "Couldn't append to '$baserc_temp'"
    mv -f -- "$baserc_temp" "$baserc"
    exit_if_error $? "Couldn't overwrite '$baserc'"
    return 0
}

do_install() {
    local repo="ssh://git@github.com:codeforester/base.git"
    if [[ -d $BASE_HOME ]]; then
        if ((force_install)); then
            local base_home_backup=$BASE_HOME.$current_time
            if mv -- "$BASE_HOME" "$base_home_backup"; then
                printf '%s\n' "Moved current base home directory '$BASE_HOME' to '$base_home_backup'"
            else
                exit_if_error 1 "Couldn't move current base home directory '$BASE_HOME' to '$base_home_backup'"
            fi
        else
            printf '%s\n' "Base is already installed at '$BASE_HOME'"
            exit 0
        fi
    fi

    git clone "$repo" "$BASE_HOME"
    exit_if_error $? "Couldn't install Base"
    printf '%s\n' "Installed Base at '$BASE_HOME'"

    #
    # patch .baserc
    # This is how we remember custom BASE_HOME path and BASE_TEAM values.
    # The user is free to put custom code into the .baserc file.
    # A marker is appended to the lines managed by base CLI.
    #
    BASE_TEAM=$base_team
    BASE_SHARED_TEAMS=$base_shared_teams
    patch_baserc BASE_HOME BASE_TEAM BASE_SHARED_TEAMS

    exit 0
}

do_embrace() {
    if ! verify_base; then
        error_exit "$glb_error_message"
    fi
    local base_bash_profile=$BASE_HOME/lib/shell/bash_profile
    local base_bashrc=$BASE_HOME/lib/shell/bashrc
    local bash_profile=$HOME/.bash_profile
    local bashrc=$HOME/.bashrc
    if [[ -L $bash_profile ]]; then
        local bash_profile_link=$(readlink "$bash_profile")
    fi
    if [[ -L $bashrc ]]; then
        local bashrc_link=$(readlink "$bashrc")
    fi
    if [[ $bash_profile_link = $base_bash_profile ]]; then
        printf '%s\n' "$bash_profile is already symlinked to $base_bash_profile"
    else
        if [[ -f $bash_profile ]]; then
            local bash_profile_backup=$HOME/.bash_profile.$current_time
            printf '%s\n' "Backing up $bash_profile to $bash_profile_backup and overriding it with $base_bash_profile"
            if ! cp -- "$bash_profile" "$bash_profile_backup"; then
                exit_if_error $? "ERROR: can't create a backup of $bash_profile"
            fi
        fi
        if ln -sf -- "$base_bash_profile" "$bash_profile"; then
            printf '%s\n' "Symlinked '$bash_profile' to '$base_bash_profile'"
        fi
    fi
    if [[ $bashrc_link = $base_bashrc ]]; then
        printf '%s\n' "$bashrc is already symlinked to $base_bashrc"
    else
        if [[ -f $bashrc ]]; then
            local bashrc_backup=$HOME/.bashrc.$current_time
            printf '%s\n' "Backing up $bashrc to $bashrc_backup and overriding it with $base_bashrc"
            if ! cp -- "$bashrc" "$bashrc_backup"; then
                exit_if_error $? "ERROR: can't create a backup of $bashrc"
            fi
        fi
        if ln -sf -- "$base_bashrc" "$bashrc"; then
            printf '%s\n' "Symlinked '$bash_profile' to '$base_bash_profile'"
        fi
    fi
}

do_update() {
    if [[ -d $BASE_HOME ]]; then
        cd -- "$BASE_HOME" || error_exit "Can't cd to BASE_HOME at '$BASE_HOME'"
        git pull
    else
        printf '%s\n' "ERROR: Base is not installed at BASE_HOME '$BASE_HOME'"
        exit 1
    fi
}

do_run() {
    if ! verify_base; then
        error_exit "$glb_error_message"
    fi
    base_init
    "$@"
}

do_status() {
    if [[ ! -d $BASE_HOME ]]; then
        printf '%s\n' "Base is not installed at '$BASE_HOME'"
        exit 1
    fi

    if ! verify_base; then
        error_exit "$glb_error_message"
    else
        printf '%s\n' "Base is installed at $BASE_HOME"
    fi
    exit 0
}

do_shell() {
    local base_bash_profile=$BASE_HOME/lib/shell/bash_profile
    if [[ -d $BASE_HOME && -f $base_bash_profile ]]; then
        export BASE_SHELL=1
        exec bash --rcfile "$base_bash_profile"
    else
        do_common_shell
    fi
}

do_common_shell() {
    local common_bash_profile=${0%/*}/bash_profile
    if [[ -f $common_bash_profile ]]; then
        exec bash --rcfile "$common_bash_profile"
    else
        error_exit "Common bash profile '$common_bash_profile' not found"
    fi
}

do_version() {
    printf '%s\n' "base version $BASE_VERSION"
}

do_man() {
    local dir bin desc dirs team
    local -A teams
    if ! verify_base; then
        error_exit "$glb_error_message"
    fi
	if ! command -v base-wrapper >/dev/null; then
		error_exit "base-wrapper needs to be in your \$PATH to be able to run this command."
	fi
    dirs=(bin company/bin)
    [[ $base_team ]] || base_team=$BASE_TEAM
    if [[ $base_team ]]; then
        dirs+=(team/$base_team/bin)
        teams[$base_team]=1
    fi
    # note: BASE_SHARED_TEAMS could be a space delimited string or an array
    for team in $BASE_SHARED_TEAMS "${BASE_SHARED_TEAMS[@]}"; do
        [[ ${teams[$team]} ]] && continue
        dirs+=(team/$team/bin)
        teams[$team]=1
    done
    for dir in "${dirs[@]}"; do
        dir=$BASE_HOME/$dir
        [[ -d $dir ]] || continue
        cd -- "$dir" || continue
        printf '%s\n' "${dir#$BASE_HOME/}:"
        for bin in *; do
            [[ -f $bin ]] || continue
            if head -1 "$bin" | grep -Eq '!/usr/bin/env[[:space:]]+base-wrapper[[:space:]]*'; then
                desc=$(./"$bin" --describe)
                printf '\t\t%s\n' "$bin: $desc"
            fi
        done
    done
}

do_set_team() {
    if (($# > 1)); then
        usage_error "Got too many arguments"
    else
        if [[ $1 ]]; then
            BASE_TEAM=$1
        else
            BASE_TEAM=$base_team
        fi
        if [[ ! $BASE_TEAM ]]; then
            usage_error "Usage: base set-team TEAM"
        fi
    fi

    patch_baserc BASE_TEAM
}

do_set_shared_teams() {
    if (($# > 0)); then
        BASE_SHARED_TEAMS=$*
    elif [[ $base_shared_teams ]]; then
        BASE_SHARED_TEAMS=$base_shared_teams
    else
        usage_error "Usage: base set-shared-teams TEAM ..."
    fi
    patch_baserc BASE_SHARED_TEAMS
}

assert_bash_version() {
    local curr_version=$1 min_needed_version=$2
    if ((curr_version < min_needed_version)); then
        error_exit "Need Bash version >= $min_needed_version; your version is $curr_version"
    fi
}

main() {
    local bash_version="${BASH_VERSINFO[0]}${BASH_VERSINFO[1]}" timefmt="%Y-%m-%d:%H:%M:%S"
    if [[ $1 =~ -h|--help|-help|help ]]; then
        show_common_help
        exit 0
    fi
    if [[ $1 =~ --version|-version|-v ]]; then
        do_version
        exit 0
    fi
    force_install=0
    if ((bash_version >= 42)); then
        printf -v current_time "%($timefmt)T" -1
    else
        current_time=$(date +"$timefmt")
    fi
    while getopts "fhb:s:t:vx" opt; do
        case $opt in
        b) export BASE_HOME=$OPTARG;;
        t) export base_team=$OPTARG;;
        s) export base_shared_teams=$OPTARG;;
        f) force_install=1;;
        v) do_version
           exit 0;;
        x) set -x;;
        *) show_common_help >&2
           exit 2;;
        esac
    done
    shift $((OPTIND-1))
    command=$1
    shift 2>/dev/null
    get_base_home
    case $command in
    embrace)          do_embrace;;
    help)             show_common_help;;
    install)          assert_bash_version "$bash_version" 42; do_install;;
    run)              do_run "$@";;
    set-shared-teams) do_set_shared_teams "$@";;
    set-team)         do_set_team "$@";;
    shell)            do_shell;;
    status)           do_status;;
    update)           do_update;;
    version)          do_version;;
    man)              do_man;;
    "")               do_common_shell;;
    *)                usage_error "Unrecognized command: $command";;
    esac
}

main "$@"
