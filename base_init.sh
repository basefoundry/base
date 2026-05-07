#!/usr/bin/env bash

#
# base_init.sh
#     Shared Base shell bootstrap loaded after the shell-specific startup files
#     have already decided that Base should be activated for the current shell.
#
# Purpose:
#     - validate the current shell/runtime expectations
#     - establish Base-wide environment variables such as BASE_HOME, BASE_OS,
#       BASE_HOST, and BASE_SOURCES
#     - extend PATH with Base-managed command directories
#
# Call chain:
#     lib/bashrc or lib/zshrc
#         -> lib/shell_startup.sh
#             -> base_init.sh
#
# What belongs here:
#     - shell-agnostic Base bootstrap logic
#     - shared environment and library loading
#     - Base-level path management and activation rules
#
# What does not belong here:
#     - aliases, prompts, keybindings, or other interactive shell cosmetics
#       (those belong in base_defaults.sh / zsh_defaults.sh or user-specific
#       startup files)
#
# See also:
#     README.md section "Shell Startup Files"
#

[[ $__base_init_sourced__ ]] && return
__base_init_sourced__=1

check_shell_version() {
    local major=${1:-4}
    local minor=${2:-2}
    local rc=0
    local num_re='^[0-9]+$'

    if [[ -n "${ZSH_VERSION:-}" ]]; then
        return 0
    fi

    if [[ -z "${BASH_VERSION:-}" ]]; then
        printf '%s\n' "ERROR: Unsupported shell - need Bash or zsh" >&2
        return 1
    fi

    if [[ ! $major =~ $num_re ]] || [[ ! $minor =~ $num_re ]]; then
        printf '%s\n' "ERROR: version numbers should be numeric"
        return 1
    fi

    local bv=${BASH_VERSINFO[0]}${BASH_VERSINFO[1]}
    local vstring=$major.$minor
    local vnum=$major$minor

    ((bv < vnum)) && {
        printf '%s\n' "ERROR: Base needs Bash version $vstring or above, your version is ${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}"
        rc=1
    }
    return $rc
}

do_init() {
    local rc=0
    [[ -f $HOME/.base_debug ]] && export BASE_DEBUG=1
    if [[ $BASH ]]; then
        # Bash
        base_debug() { [[ $BASE_DEBUG ]] && printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "DEBUG ${BASH_SOURCE[0]}:${BASH_LINENO[1]} $@" >&2; }
        base_error() {                      printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "ERROR ${BASH_SOURCE[0]}:${BASH_LINENO[1]} $@" >&2; }
    elif [[ $ZSH_VERSION ]]; then
        base_debug() { [[ $BASE_DEBUG ]] && printf '%s\n' "$(date) DEBUG base_init.sh $*" >&2; }
        base_error() {                      printf '%s\n' "$(date) ERROR base_init.sh $*" >&2; }
    else
        printf '%s\n' "ERROR: Unsupported shell - need Bash or zsh" >&2
        rc=1
    fi

    BASE_OS=$(uname -s)
    BASE_HOST=$(hostname -s)
    export BASE_SOURCES=() BASE_OS BASE_HOST

    return $rc
}

set_base_home() {
    script=$HOME/.baserc
    [[ -f $script ]] && [[ -z $_baserc_sourced ]] && {
        base_debug "Sourcing $script"
        # shellcheck source=/dev/null
        source "$script"
        _baserc_sourced=1
    }

    # set BASE_HOME to default in case it is not set
    [[ -z $BASE_HOME ]] && {
        local dir=$HOME/base
        base_debug "BASE_HOME not set; defaulting it to '$dir'"
        BASE_HOME=$dir
    }

    export BASE_HOME
}

#
# check for existence of the library, source it, add its name to BASE_SOURCES array
# Usage: source_it [-i] library_file
# -i - source only if the shell is interactive
#
source_it() {
    local lib iflag=0 sourced=0
    [[ $1 = "-i" ]] && { iflag=1; shift; }
    lib=$1
    if ((iflag)); then
        # shellcheck source=/dev/null
        ((_interactive)) && [[ -f $lib ]] && { base_debug "(interactive) Sourcing $lib"; source "$lib"; sourced=1; }
    else
        # shellcheck source=/dev/null
        [[ -f $lib ]] && { base_debug "Sourcing $lib"; source "$lib"; sourced=1; }
    fi
    ((sourced)) && BASE_SOURCES+=("$lib")
}

#
# source in libraries, starting from the top (lowest precedence) to the bottom (highest precedence)
#
import_libs_and_profiles() {
    local lib script team
    local -A teams

    source_it    "$BASE_HOME/lib/stdlib.sh"          # common library
    source_it -i "$HOME/.baserc-$USER"               # user specific bashrc outside the repo for interactive shells

    #
    # team specific actions
    #
    # Users choose teams by setting the "BASE_TEAM" variable in their user specific startup script
    # For example: BASE_TEAM=teamX
    #
    # Users can also set "BASE_SHARED_TEAMS" to more teams so as to share from those teams.
    # For example: BASE_SHARED_TEAMS="teamY teamZ" or
    #              BASE_SHARED_TEAMS=(teamY teamZ)
    #
    # We source the team specific startup script add the team bin directory to PATH, in the same order
    #
    teams=()
    for team in $BASE_TEAM $BASE_SHARED_TEAMS "${BASE_SHARED_TEAMS[@]}"; do
        [[ ${teams[$team]} ]] && continue                    # skip if team was seen already
        source_it    "$BASE_HOME/team/$team/lib/$team.sh"    # team specific library
        source_it -i "$BASE_HOME/team/$team/lib/bashrc"      # team specific bashrc for interactive shells
        add_to_path  "$BASE_HOME/team/$team/bin"             # add team bin to PATH (gets priority over company bin)
        teams[$team]=1
    done

    # add company bin to PATH; team bins, if any, take priority over company bin
    add_to_path  "$BASE_HOME/company/bin"
}

#
# A shortcut to refresh the base git repo; users can add it to user/<user>.sh file so that base is automatically
# updated upon login.
#
base_update() (
    [[ -d $BASE_HOME ]] && {
        cd "$BASE_HOME" && git pull --rebase
    }
)

base_main() {
    check_shell_version 4 2 || return $?
    do_init || return $?
    [[ $- = *i* ]] && _interactive=1 || _interactive=0
    set_base_home
    if [[ -d $BASE_HOME ]]; then
        import_libs_and_profiles
        add_to_path "$BASE_HOME/bin"
    else
        base_error "BASE_HOME '$BASE_HOME' is not a directory or is not accessible"
    fi

    #
    # these functions need to be available to user's subprocesses
    #
    if [[ -n "${BASH_VERSION:-}" ]]; then
        export -f base_update import
    fi
}

#
# start here
#
base_main
