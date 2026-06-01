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

_base_basectl_completion_project_or_options() {
    local options="$1"
    local current="$2"

    if ((COMP_CWORD == 2)) && [[ "$current" != -* ]]; then
        _base_basectl_completion_compgen "$(_base_basectl_completion_project_names)" "$current"
    else
        _base_basectl_completion_compgen "$options" "$current"
    fi
}

_base_basectl_completion() {
    local command cur
    local commands="activate setup check test demo run repo clean config doctor gh onboard update-profile update projects version help"

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
                _base_basectl_completion_compgen "--workspace --no-cd -v -h --help" "$cur"
            fi
            ;;
        projects)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "list" "$cur"
            else
                _base_basectl_completion_compgen "--workspace --format -v -h --help" "$cur"
            fi
            ;;
        setup)
            _base_basectl_completion_compgen "--dev --dry-run --manifest --notify --no-notify --recreate-venv -v -h --help" "$cur"
            ;;
        check)
            _base_basectl_completion_project_or_options "--dev --format -v -h --help" "$cur"
            ;;
        test)
            _base_basectl_completion_project_or_options "--workspace --dry-run -v -h --help" "$cur"
            ;;
        demo)
            _base_basectl_completion_project_or_options "--workspace --dry-run -v -h --help" "$cur"
            ;;
        run)
            _base_basectl_completion_project_or_options "--workspace --dry-run --list -v -h --help" "$cur"
            ;;
        repo)
            case "${COMP_WORDS[2]:-}" in
                "")
                    _base_basectl_completion_compgen "init check configure" "$cur"
                    ;;
                init)
                    _base_basectl_completion_compgen "--path --repo --description --copyright-holder --no-configure --dry-run -v -h --help" "$cur"
                    ;;
                check)
                    _base_basectl_completion_compgen "-v -h --help" "$cur"
                    ;;
                configure)
                    _base_basectl_completion_compgen "--repo --dry-run -v -h --help" "$cur"
                    ;;
            esac
            ;;
        clean)
            _base_basectl_completion_compgen "--older-than --keep-last --dry-run -v -h --help" "$cur"
            ;;
        config)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "path show doctor" "$cur"
            fi
            ;;
        doctor)
            _base_basectl_completion_project_or_options "--dev -v -h --help" "$cur"
            ;;
        gh)
            case "${COMP_WORDS[2]:-}" in
                "")
                    _base_basectl_completion_compgen "issue pr branch todo" "$cur"
                    ;;
                issue)
                    if ((COMP_CWORD == 3)); then
                        _base_basectl_completion_compgen "list create start" "$cur"
                    else
                        _base_basectl_completion_compgen "--category --title --body -h --help" "$cur"
                    fi
                    ;;
                pr)
                    if ((COMP_CWORD == 3)); then
                        _base_basectl_completion_compgen "create status checks ready merge" "$cur"
                    fi
                    ;;
                branch)
                    if ((COMP_CWORD == 3)); then
                        _base_basectl_completion_compgen "stale prune" "$cur"
                    else
                        _base_basectl_completion_compgen "--days --dry-run --yes --remote -h --help" "$cur"
                    fi
                    ;;
                todo)
                    if ((COMP_CWORD == 3)); then
                        _base_basectl_completion_compgen "import" "$cur"
                    else
                        _base_basectl_completion_compgen "--dry-run --file -h --help" "$cur"
                    fi
                    ;;
            esac
            ;;
        onboard)
            _base_basectl_completion_compgen "--dev --dry-run --yes --no-profile -v -h --help" "$cur"
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
