# shellcheck shell=bash
#
# zsh_defaults.sh
#     Optional Zsh-specific interactive defaults for users who want Base to
#     provide a standard Zsh experience.
#
# Purpose:
#     - load Base's shared shell defaults
#     - define conservative Zsh-specific keybindings, prompt, and history
#       behavior for interactive Zsh shells
#
# How it is loaded:
#     - sourced from the Base-managed ~/.zshrc section
#     - only when the user runs `basectl update-profile --defaults`
#     - only for interactive Zsh shells
#
# What belongs here:
#     - Zsh bindkey/editor behavior
#     - Zsh prompt defaults
#     - Zsh history-related shell options
#
# What does not belong here:
#     - aliases and editor defaults shared with Bash; use base_defaults.sh
#     - BASE_HOME discovery
#     - sourcing of base_init.sh
#     - login-shell orchestration
#     - machine-specific overrides
#
[[ ! -o interactive ]] && return 0
[[ -n "${_base_zsh_defaults_sourced:-}" ]] && return 0

base_zsh_defaults_file="${BASE_HOME:-}/lib/shell/base_defaults.sh"
[[ -f "$base_zsh_defaults_file" ]] || {
    printf "ERROR: Base shared defaults file '%s' was not found.\n" "$base_zsh_defaults_file" >&2
    unset base_zsh_defaults_file
    return 1
}
# shellcheck source=/dev/null
source "$base_zsh_defaults_file" || {
    unset base_zsh_defaults_file
    return 1
}
unset base_zsh_defaults_file

_base_zsh_defaults_sourced=1
readonly _base_zsh_defaults_sourced

bindkey -v
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
zstyle ':completion:*' menu select

_base_zsh_defaults_git_prompt() {
    local branch
    local git_state
    local inside

    command -v git >/dev/null 2>&1 || return 0

    git_state="$(git rev-parse --is-inside-work-tree --abbrev-ref HEAD 2>/dev/null)" || return 0
    [[ "$git_state" == *$'\n'* ]] || return 0
    inside="${git_state%%$'\n'*}"
    branch="${git_state#*$'\n'}"
    branch="${branch%%$'\n'*}"
    [[ "$inside" == "true" ]] || return 0
    if [[ -z "$branch" || "$branch" == "HEAD" ]]; then
        branch="$(git rev-parse --short HEAD 2>/dev/null)" || return 0
    fi
    [[ -n "$branch" ]] || return 0

    printf '(%s) ' "$branch"
}

export HISTFILE="${HISTFILE:-$HOME/.zsh_history}"
if [[ "${HISTSIZE:-30}" == 30 ]]; then
    export HISTSIZE=10000
else
    export HISTSIZE
fi
if [[ "${SAVEHIST:-0}" == 0 ]]; then
    export SAVEHIST=10000
else
    export SAVEHIST
fi
setopt appendhistory
setopt extended_history
setopt hist_expire_dups_first
setopt hist_find_no_dups
setopt hist_ignore_dups
setopt hist_ignore_all_dups
setopt hist_ignore_space
setopt hist_reduce_blanks
setopt hist_save_no_dups
setopt hist_verify
setopt interactive_comments
setopt no_beep
setopt prompt_subst
setopt share_history

PROMPT='%* %m $(_base_zsh_defaults_git_prompt)%1~: '
