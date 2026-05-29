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

[[ -n "${__base_defaults_sourced__:-}" ]] && return 0
readonly __base_defaults_sourced__=1

alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

export EDITOR="${EDITOR:-vi}"
export VISUAL="${VISUAL:-$EDITOR}"
export EXINIT="${EXINIT:-set ts=4 sw=4 ai nows nosm expandtab}"
