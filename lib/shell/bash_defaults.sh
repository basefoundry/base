# shellcheck shell=bash
#
# bash_defaults.sh
#     Optional Bash-specific interactive defaults for users who want Base to
#     provide a standard shell experience.
#
# Purpose:
#     - load Base's shared shell defaults
#     - define conservative Bash-specific command-line editing, prompt, and
#       history behavior for interactive Bash shells
#
# How it is loaded:
#     - sourced from the Base-managed ~/.bashrc section
#     - only when the user runs `basectl update-profile --defaults`
#     - only for interactive Bash shells
#
# What belongs here:
#     - Bash command-line editing defaults
#     - Bash prompt defaults
#     - Bash history-related shell options
#
# What does not belong here:
#     - aliases and editor defaults shared with Zsh; use base_defaults.sh
#     - BASE_HOME discovery
#     - sourcing of base_init.sh
#     - login-shell orchestration
#     - machine-specific overrides
#
[[ $- != *i* ]] && return 0
[[ -n "${_base_bash_defaults_sourced:-}" ]] && return 0

base_bash_defaults_file="${BASE_HOME:-}/lib/shell/base_defaults.sh"
[[ -f "$base_bash_defaults_file" ]] || {
    printf "ERROR: Base shared defaults file '%s' was not found.\n" "$base_bash_defaults_file" >&2
    unset base_bash_defaults_file
    return 1
}
# shellcheck source=/dev/null
source "$base_bash_defaults_file" || {
    unset base_bash_defaults_file
    return 1
}
unset base_bash_defaults_file

_base_bash_defaults_sourced=1
readonly _base_bash_defaults_sourced

set -o vi

_base_bash_defaults_git_dir() {
    local current="${PWD:-}"
    local git_dir
    local git_file
    local parent

    while [[ -n "$current" ]]; do
        if [[ -d "$current/.git" ]]; then
            printf '%s\n' "$current/.git"
            return 0
        fi
        if [[ -f "$current/.git" ]]; then
            IFS= read -r git_file < "$current/.git" || return 1
            [[ "$git_file" == gitdir:\ * ]] || return 1
            git_dir="${git_file#gitdir: }"
            case "$git_dir" in
                /*) ;;
                *) git_dir="$current/$git_dir" ;;
            esac
            printf '%s\n' "$git_dir"
            return 0
        fi

        [[ "$current" == "/" ]] && return 1
        parent="${current%/*}"
        [[ -n "$parent" && "$parent" != "$current" ]] || parent="/"
        current="$parent"
    done

    return 1
}

_base_bash_defaults_git_prompt() {
    local branch
    local git_dir
    local head

    git_dir="$(_base_bash_defaults_git_dir)" || return 0
    IFS= read -r head < "$git_dir/HEAD" || return 0
    case "$head" in
        "ref: refs/heads/"*) branch="${head#ref: refs/heads/}" ;;
        "ref: "*) branch="${head#ref: }"; branch="${branch##*/}" ;;
        *) branch="$(printf '%.7s' "$head")" ;;
    esac
    [[ -n "$branch" ]] || return 0

    printf '(%s) ' "$branch"
}

export PS1='\[\033[0;35m\]\T \h\[\033[0;33m\] $(_base_bash_defaults_git_prompt)\w\[\033[00m\]: '

_base_bash_defaults_bind_set() {
    bind "set $1" 2>/dev/null || true
}

_base_bash_defaults_bind_set "completion-ignore-case on"
_base_bash_defaults_bind_set "show-all-if-ambiguous on"
_base_bash_defaults_bind_set "mark-symlinked-directories on"
unset -f _base_bash_defaults_bind_set

export HISTCONTROL="${HISTCONTROL:-ignoreboth:erasedups}"
if [[ "${HISTSIZE:-500}" == 500 ]]; then
    export HISTSIZE=10000
else
    export HISTSIZE
fi
if [[ "${HISTFILESIZE:-500}" == 500 ]]; then
    export HISTFILESIZE=20000
else
    export HISTFILESIZE
fi
export HISTTIMEFORMAT="[%F %T] "
shopt -s checkwinsize
shopt -s histappend
shopt -s cmdhist
shopt -s lithist
