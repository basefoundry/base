# shellcheck shell=bash
#
# base_defaults.sh
#     Optional shell-neutral interactive defaults shared by Bash and Zsh.
#
# Purpose:
#     - define conservative defaults that mean the same thing in Bash and Zsh
#     - keep duplicated alias/editor setup out of shell-specific defaults files
#
# How it is loaded:
#     - sourced by bash_defaults.sh and zsh_defaults.sh
#     - only when the user runs `basectl update-profile --defaults`
#     - only for interactive shells
#
# What belongs here:
#     - shell-neutral aliases
#     - editor environment defaults
#     - other simple defaults that are valid in both Bash and Zsh
#
# What does not belong here:
#     - BASE_HOME discovery
#     - sourcing of base_init.sh
#     - shell-specific options such as shopt, setopt, bindkey, or PROMPT/PS1
#     - machine-specific overrides
#
[[ $- != *i* ]] && return 0

[[ -n "${_base_defaults_sourced:-}" ]] && return 0
_base_defaults_sourced=1
readonly _base_defaults_sourced

alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

export EDITOR="${EDITOR:-vi}"
export VISUAL="${VISUAL:-$EDITOR}"
export EXINIT="${EXINIT:-set ts=4 sw=4 ai nows nosm expandtab}"

export PAGER="${PAGER:-less}"
export LESS="${LESS:--FRX}"
export MANPAGER="${MANPAGER:-less -R}"
export GIT_PAGER="${GIT_PAGER:-less -FRX}"

_base_defaults_git_dir() {
    local current="${PWD:-}"
    local git_dir
    local git_file
    local parent

    while [[ -n "$current" ]]; do
        if [[ -d "$current/.git" ]]; then
            git_dir="$current/.git"
            [[ -r "$git_dir/HEAD" ]] || return 1
            printf '%s\n' "$git_dir"
            return 0
        fi
        if [[ -f "$current/.git" ]]; then
            [[ -r "$current/.git" ]] || return 1
            IFS= read -r git_file 2>/dev/null < "$current/.git" || return 1
            [[ "$git_file" == gitdir:\ * ]] || return 1
            git_dir="${git_file#gitdir: }"
            [[ -n "$git_dir" ]] || return 1
            case "$git_dir" in
                /*) ;;
                *) git_dir="$current/$git_dir" ;;
            esac
            [[ -d "$git_dir" && -r "$git_dir/HEAD" ]] || return 1
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

_base_defaults_git_prompt() {
    local branch
    local git_dir
    local head

    git_dir="$(_base_defaults_git_dir)" || return 0
    [[ -r "$git_dir/HEAD" ]] || return 0
    IFS= read -r head 2>/dev/null < "$git_dir/HEAD" || return 0
    case "$head" in
        "ref: refs/heads/"*) branch="${head#ref: refs/heads/}" ;;
        "ref: "*) branch="${head#ref: }"; branch="${branch##*/}" ;;
        *)
            [[ ${#head} -ge 7 && "$head" != *[![:xdigit:]]* ]] || return 0
            branch="${head:0:7}"
            ;;
    esac
    [[ -n "$branch" ]] || return 0

    printf '(%s) ' "$branch"
}
