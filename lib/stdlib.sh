###
### stdlib.sh - foundation library for Bash scripts
###             Need Bash version 4.3 or above - see http://tiswww.case.edu/php/chet/bash/NEWS
###
### Areas covered:
###     - PATH manipulation
###     - logging
###     - error handling
###

################################################# INITIALIZATION #######################################################

#
# make sure we do nothing in case the library is sourced more than once in the same shell
#
[[ $__stdlib_sourced__ ]] && return
__stdlib_sourced__=1

#
# The only code that executes when the library is sourced
#
__stdlib_init__() {
    __log_init__

    # call future init functions here
}

################################################# LIBRARY IMPORTER #####################################################

#
# import: source a library from $BASE_HOME
# Example:
#     import lib/assertions.sh company/lib/xyz.sh ...
#
# IMPORTANT NOTE: If your library has global variables declared with 'declare' statement, you need to add -g flag to those.
#                 Since the library gets sourced inside the `import` function, globals declared without the -g option would
#                 be local to the function and hence be unavailable to other functions.
import() {
    local lib rc=0
    [[ $BASE_HOME ]] || { printf '%s\n' "ERROR: BASE_HOME not set; import functionality needs it" >&2; return 1; }
    for lib; do
        lib=$BASE_HOME/$lib
        if [[ -f "$lib" ]]; then
            source "$lib"
        else
            printf 'ERROR: %s\n' "Library '$lib' does not exist" >&2
            rc=1
        fi
    done
    return $rc
}

################################################# PATH MANIPULATION ####################################################

# add a new directory to $PATH
add_to_path() {
    local dir re prepend=0 opt strict=1
    OPTIND=1
    while getopts sp opt; do
        case "$opt" in
            n)  strict=0  ;;  # don't care if directory exists or not before adding it to PATH
            p)  prepend=1 ;;  # prepend the directory to PATH instead of appending
            *)  log_error "add_to_path - invalid option '$opt'"
                return
                ;;
        esac
    done

    shift $((OPTIND-1))
    for dir; do
        ((strict)) && [[ ! -d $dir ]] && continue
        re="(^$dir:|:$dir:|:$dir$)"
        if ! [[ $PATH =~ $re ]]; then
            ((prepend)) && PATH="$dir:$PATH" || PATH="$PATH:$dir"
        fi
    done
}

# remove duplicates in $PATH
dedupe_path() { PATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PATH}))')"; }

# print directories in $PATH, one per line
print_path() {
    local -a dirs; local dir
    IFS=: read -ra dirs <<< "$PATH"
    for dir in "${dirs[@]}"; do printf '%s\n' "$dir"; done
}

#################################################### LOGGING ###########################################################

__log_init__() {
    if [[ -t 1 ]]; then
        # colors for logging in interactive mode
        [[ $COLOR_BOLD ]]   || COLOR_BOLD="\033[1m"
        [[ $COLOR_RED ]]    || COLOR_RED="\033[0;31m"
        [[ $COLOR_GREEN ]]  || COLOR_GREEN="\033[0;32m"
        [[ $COLOR_YELLOW ]] || COLOR_YELLOW="\033[0;33m"
        [[ $COLOR_BLUE ]]   || COLOR_BLUE="\033[0;34m"
        [[ $COLOR_OFF ]]    || COLOR_OFF="\033[0m"
    else
        # no colors to be used if non-interactive
        COLOR_RED= COLOR_GREEN= COLOR_YELLOW= COLOR_BLUE= COLOR_OFF=
    fi
    readonly COLOR_RED COLOR_GREEN COLOR_YELLOW COLOR_BLUE COLOR_OFF

    #
    # map log level strings (FATAL, ERROR, etc.) to numeric values
    #
    # Note the '-g' option passed to declare - it is essential
    #
    unset _log_levels _loggers_level_map
    declare -gA _log_levels _loggers_level_map
    _log_levels=([FATAL]=0 [ERROR]=1 [WARN]=2 [INFO]=3 [DEBUG]=4 [VERBOSE]=5)

    #
    # hash to map loggers to their log levels
    # the default logger "default" has INFO as its default log level
    #
    _loggers_level_map["default"]=3  # the log level for the default logger is INFO
}

#
# set_log_level
#
set_log_level() {
    local logger=default in_level l
    [[ $1 = "-l" ]] && { logger=$2; shift 2 2>/dev/null; }
    in_level="${1:-INFO}"
    if [[ $logger ]]; then
        l="${_log_levels[$in_level]}"
        if [[ $l ]]; then
            _loggers_level_map[$logger]=$l
        else
            printf '%(%Y-%m-%d:%H:%M:%S)T %-7s %s\n' -1 WARN \
                "${BASH_SOURCE[2]}:${BASH_LINENO[1]} Unknown log level '$in_level' for logger '$logger'; setting to INFO"
            _loggers_level_map[$logger]=3
        fi
    else
        printf '%(%Y-%m-%d:%H:%M:%S)T %-7s %s\n' -1 WARN \
            "${BASH_SOURCE[2]}:${BASH_LINENO[1]} Option '-l' needs an argument" >&2
    fi
}

#
# Core and private log printing logic to be called by all logging functions.
# Note that we don't make use of any external commands like 'date' and hence we don't fork at all.
# We use the Bash's printf builtin instead.
#
_print_log() {
    local in_level=$1; shift
    local logger=default log_level_set log_level
    [[ $1 = "-l" ]] && { logger=$2; shift 2; }
    log_level="${_log_levels[$in_level]}"
    log_level_set="${_loggers_level_map[$logger]}"
    if [[ $log_level_set ]]; then
        ((log_level_set >= log_level)) && {
            printf '%(%Y-%m-%d:%H:%M:%S)T %-7s %s ' -1 "$in_level" "${BASH_SOURCE[2]}:${BASH_LINENO[1]}"
            printf '%s\n' "$@"
        }
    else
        printf '%(%Y-%m-%d:%H:%M:%S)T %-7s %s\n' -1 WARN "${BASH_SOURCE[2]}:${BASH_LINENO[1]} Unknown logger '$logger'"
    fi
}

#
# core function for logging contents of a file
#
_print_log_file()   {
    local in_level=$1; shift
    local logger=default log_level_set log_level file
    [[ $1 = "-l" ]] && { logger=$2; shift 2; }
    file=$1
    log_level="${_log_levels[$in_level]}"
    log_level_set="${_loggers_level_map[$logger]}"
    if [[ $log_level_set ]]; then
        if ((log_level_set >= log_level)) && [[ -f $file ]]; then
            log_debug "Contents of file '$1':" 
            cat -- "$1"
        fi
    else
        printf '%(%Y-%m-%d:%H:%M:%S)T %s\n' -1 "WARN ${BASH_SOURCE[2]}:${BASH_LINENO[1]} Unknown logger '$logger'"
    fi
}

#
# main logging functions
#
log_fatal()   { _print_log FATAL   "$@"; }
log_error()   { _print_log ERROR   "$@"; }
log_warn()    { _print_log WARN    "$@"; }
log_info()    { _print_log INFO    "$@"; }
log_debug()   { _print_log DEBUG   "$@"; }
log_verbose() { _print_log VERBOSE "$@"; }
#
# logging file content
#
log_info_file()    { _print_log_file INFO    "$@"; }
log_debug_file()   { _print_log_file DEBUG   "$@"; }
log_verbose_file() { _print_log_file VERBOSE "$@"; }
#
# logging for function entry and exit
#
log_info_enter()    { _print_log INFO    "Entering function ${FUNCNAME[1]}"; }
log_debug_enter()   { _print_log DEBUG   "Entering function ${FUNCNAME[1]}"; }
log_verbose_enter() { _print_log VERBOSE "Entering function ${FUNCNAME[1]}"; }
log_info_leave()    { _print_log INFO    "Leaving function ${FUNCNAME[1]}";  }
log_debug_leave()   { _print_log DEBUG   "Leaving function ${FUNCNAME[1]}";  }
log_verbose_leave() { _print_log VERBOSE "Leaving function ${FUNCNAME[1]}";  }

#
# THe print routines don't prefix the messages with the timestamp
#

print_error() {
    {
        printf "${COLOR_RED}ERROR: "
        printf '%s\n' "$@"
        printf "$COLOR_OFF"
    } >&2
}

print_warn() {
    printf "${COLOR_YELLOW}WARN: "
    printf '%s\n' "$@"
    printf "$COLOR_OFF"
}

print_info() {
    printf "$COLOR_BLUE"
    printf '%s\n' "$@"
    printf "$COLOR_OFF"
}

print_success() {
    printf "${COLOR_GREEN}SUCCESS: "
    printf '%s\n' "$@"
    printf "$COLOR_OFF"
}

print_bold() {
    printf '%b\n' "$COLOR_BOLD$@$COLOR_OFF"
}

print_message() {
    printf '%s\n' "$@"
}

# print only if output is going to terminal
print_tty() {
    if [[ -t 1 ]]; then
        printf '%s\n' "$@"
    fi
}

################################################## ERROR HANDLING ######################################################

dump_trace() {
    local frame=0 line func source n=0
    while caller "$frame"; do
        ((frame++))
    done | while read line func source; do
        ((n++ == 0)) && {
            printf 'Encountered a fatal error\n'
        }
        printf '%4s at %s\n' " " "$func ($source:$line)"
    done
}

exit_if_error() {
    (($#)) || return
    local num_re='^[0-9]+'
    local rc=$1; shift
    local message="${@:-No message specified}"
    if ! [[ $rc =~ $num_re ]]; then
        log_error "'$rc' is not a valid exit code; it needs to be a number greater than zero. Treating it as 1."
        rc=1
    fi
    ((rc)) && {
        log_fatal "$message"
        dump_trace "$@"
        exit $rc
    }
    return 0
}

fatal_error() {
    local ec=$?                # grab the current exit code
    ((ec == 0)) && ec=1        # if it is zero, set exit code to 1
    exit_if_error "$ec" "$@"
}

#
# run a simple command (no compound statements or pipelines) and exit if it exits with non-zero 
#
run_simple() {
    log_debug "Running command: $*"
    "$@"
    exit_if_error $? "run failed: $@"
}

#
# safe cd
#
base_cd() {
    local dir=$1
    [[ $dir ]]   || fatal_error "No arguments or an empty string passed to base_cd"
    cd -- "$dir" || fatal_error "Can't cd to '$dir'"
}

base_cd_nonfatal() {
    local dir=$1
    [[ $dir ]] || return 1
    cd -- "$dir" || return 1
    return 0
}

#
# safe_unalias
#
safe_unalias() {
    # Ref: https://stackoverflow.com/a/61471333/6862601
    local alias_name
    for alias_name; do
        [[ ${BASH_ALIASES[$alias_name]} ]] && unalias "$alias_name"
    done
    return 0
}

################################################# MISC FUNCTIONS #######################################################
#
# For functions that need to return a single value, we use the global variable OUTPUT.
# For functions that need to return multiple values, we use the global variable OUTPUT_ARRAY.
# These global variables eliminate the need for a subshell when the caller wants to retrieve the
# returned values.
#
# Each function that makes use of these global variables would call __clear_output__ as the very first step.
#
__clear_output__() { unset OUTPUT OUTPUT_ARRAY; }

#
# return path to parent script's source directory
#
get_my_source_dir() {
    __clear_output__

    # Reference: https://stackoverflow.com/a/246128/6862601
    OUTPUT="$(cd "$(dirname "${BASH_SOURCE[1]}")" >/dev/null 2>&1 && pwd -P)"
}

#
# wait for user to hit Enter key
#
wait_for_enter() {
    local prompt=${1:-"Press Enter to continue"}
    read -r -n1 -s -p "Press Enter to continue" </dev/tty
}

#################################################### END OF FUNCTIONS ##################################################

__stdlib_init__
