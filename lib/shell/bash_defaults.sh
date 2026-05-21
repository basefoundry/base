#
# bash_defaults.sh
#     Optional Bash-specific interactive defaults for users who want Base to
#     provide a standard shell experience in addition to the core bootstrap.
#
# Purpose:
#     - define a conservative shared set of aliases, editor defaults, prompt
#       settings, and history behavior for interactive Bash shells
#
# How it is loaded:
#     - sourced indirectly from lib/shell/shell_startup.sh
#     - only when BASE_ENABLE_SHELL_DEFAULTS=true
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
#     - machine-specific overrides (those belong in ~/.baserc)
#
# See also:
#     README.md section "Shell Startup Files"
#
[[ $- != *i* ]] && return 0

###
### Aliases
###
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

###
### Command editing
###
set -o vi
export EDITOR="${EDITOR:-vi}"
export VISUAL="${VISUAL:-$EDITOR}"

###
### vi/vim
###
export EXINIT="set ts=4 sw=4 ai nows nosm expandtab"

###
### Prompt
###
export PS1='\[\033[0;35m\]\T \h\[\033[0;33m\] \w\[\033[00m\]: '

###
### Bash history
###
export HISTCONTROL=ignoredups:erasedups
export HISTTIMEFORMAT="[%F %T] "
shopt -s histappend
