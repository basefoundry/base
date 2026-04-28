#
# zsh_defaults.sh
#     Optional Zsh-specific interactive defaults for users who want Base to
#     provide a standard Zsh experience on top of the shared Base bootstrap.
#
# Purpose:
#     - define a conservative shared set of aliases, editor defaults,
#       keybindings, prompt settings, and history behavior for interactive Zsh
#       shells
#
# How it is loaded:
#     - sourced indirectly from lib/shell_startup.sh
#     - only when BASE_ENABLE_SHELL_DEFAULTS=true
#     - only for interactive Zsh shells
#
# What belongs here:
#     - aliases such as rm -i / cp -i / mv -i
#     - bindkey/editor preferences
#     - prompt defaults
#     - history-related zsh options
#
# What does not belong here:
#     - BASE_HOME discovery
#     - sourcing of base_init.sh
#     - login-shell orchestration
#     - machine-specific overrides (those belong in ~/.baserc)
#
# See also:
#     README.md section "Shell Startup Files"
#
[[ ! -o interactive ]] && return 0

alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

bindkey -v
export EDITOR="${EDITOR:-vi}"
export VISUAL="${VISUAL:-$EDITOR}"

export HISTSIZE="${HISTSIZE:-5000}"
export SAVEHIST="${SAVEHIST:-5000}"
setopt appendhistory
setopt hist_ignore_dups
setopt hist_ignore_all_dups
setopt share_history

PROMPT='%* %m %1~: '
