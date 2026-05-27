# shellcheck shell=bash

#
# Bash completion for basectl.
#

_base_basectl_completion_project_names() {
    local wrapper="${BASE_HOME:-}/bin/base-wrapper"

    [[ -x "$wrapper" ]] || return 0
    "$wrapper" --project base base_projects list 2>/dev/null | awk -F '\t' '{print $1}'
}

_base_basectl_completion_compgen() {
    local candidate
    local words="$1"
    local current="$2"

    COMPREPLY=()
    while IFS= read -r candidate; do
        COMPREPLY+=("$candidate")
    done < <(compgen -W "$words" -- "$current")
}

_base_basectl_completion() {
    local command cur
    local commands="activate setup check clean doctor update-profile update projects version help"

    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]:-}"

    if ((COMP_CWORD == 1)); then
        _base_basectl_completion_compgen "$commands" "$cur"
        return 0
    fi

    command="${COMP_WORDS[1]:-}"
    case "$command" in
        activate)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "$(_base_basectl_completion_project_names)" "$cur"
            else
                _base_basectl_completion_compgen "--workspace -v -h --help" "$cur"
            fi
            ;;
        projects)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "list" "$cur"
            fi
            ;;
        setup)
            _base_basectl_completion_compgen "--dev --dry-run --manifest --recreate-venv -v -h --help" "$cur"
            ;;
        check)
            _base_basectl_completion_compgen "--dev --format -v -h --help" "$cur"
            ;;
        clean)
            _base_basectl_completion_compgen "--older-than --dry-run -v -h --help" "$cur"
            ;;
        doctor)
            _base_basectl_completion_compgen "--dev -v -h --help" "$cur"
            ;;
        update-profile)
            _base_basectl_completion_compgen "--defaults --no-defaults --dry-run -v -h --help" "$cur"
            ;;
        update)
            _base_basectl_completion_compgen "--dry-run -v -h --help" "$cur"
            ;;
    esac
}

complete -F _base_basectl_completion basectl 2>/dev/null || true
