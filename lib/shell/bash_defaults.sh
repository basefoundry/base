#
# bash_defaults.sh
#     Optional Bash-specific interactive defaults for users who want Base to
#     provide a standard shell experience.
#
# Purpose:
#     - define a conservative shared set of aliases, editor defaults, prompt
#       settings, and history behavior for interactive Bash shells
#
# How it is loaded:
#     - sourced from the Base-managed ~/.bashrc section
#     - only when the user runs `basectl update-profile --defaults`
#     - only for interactive Bash shells
#
# What belongs here:
#     - aliases such as rm -i / cp -i / mv -i
#     - editor and command-line editing defaults
#     - prompt defaults
#     - history-related shell options
#
# What does not belong here:
#     - BASE_HOME discovery
#     - sourcing of base_init.sh
#     - login-shell orchestration
#     - machine-specific overrides
#
[[ $- != *i* ]] && return 0

alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

set -o vi
export EDITOR="${EDITOR:-vi}"
export VISUAL="${VISUAL:-$EDITOR}"

export EXINIT="set ts=4 sw=4 ai nows nosm expandtab"

export PS1='\[\033[0;35m\]\T \h\[\033[0;33m\] \w\[\033[00m\]: '

export HISTCONTROL=ignoredups:erasedups
export HISTTIMEFORMAT="[%F %T] "
shopt -s histappend
