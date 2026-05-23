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

bindkey -v

export HISTSIZE="${HISTSIZE:-5000}"
export SAVEHIST="${SAVEHIST:-5000}"
setopt appendhistory
setopt hist_ignore_dups
setopt hist_ignore_all_dups
setopt share_history

PROMPT='%* %m %1~: '
