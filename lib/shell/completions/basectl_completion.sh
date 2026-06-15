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

_base_basectl_completion_profiles() {
    printf '%s\n' "dev sre ai dev,sre dev,ai sre,ai dev,sre,ai"
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

_base_basectl_completion_profiles_or_options() {
    local current="$1"
    local options="$2"
    local previous="${COMP_WORDS[COMP_CWORD - 1]:-}"

    if [[ "$previous" == "--profile" ]]; then
        _base_basectl_completion_compgen "$(_base_basectl_completion_profiles)" "$current"
    else
        _base_basectl_completion_compgen "$options" "$current"
    fi
}

_base_basectl_completion_project_profiles_or_options() {
    local current="$1"
    local options="$2"
    local previous="${COMP_WORDS[COMP_CWORD - 1]:-}"

    if [[ "$previous" == "--profile" ]]; then
        _base_basectl_completion_compgen "$(_base_basectl_completion_profiles)" "$current"
    else
        _base_basectl_completion_project_or_options "$options" "$current"
    fi
}

_base_basectl_completion() {
    local command cur
    local commands="activate setup check test export-context build demo run repo ci release clean logs config doctor gh onboard update-profile update projects workspace version help"

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
        workspace)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "status check doctor" "$cur"
            else
                _base_basectl_completion_compgen "--workspace --manifest --format -v -h --help" "$cur"
            fi
            ;;
        setup)
            _base_basectl_completion_profiles_or_options \
                "$cur" \
                "--profile --dry-run --manifest --notify --no-notify --recreate-venv -v -h --help"
            ;;
        check)
            _base_basectl_completion_project_profiles_or_options "$cur" "--profile --format -v -h --help"
            ;;
        test)
            _base_basectl_completion_project_or_options "--workspace --dry-run -v -h --help" "$cur"
            ;;
        export-context)
            _base_basectl_completion_project_or_options "--workspace --format --output --print --list-files -v -h --help" "$cur"
            ;;
        build)
            _base_basectl_completion_project_or_options "--workspace --dry-run --list -v -h --help" "$cur"
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
                    _base_basectl_completion_compgen "init clone check configure agent-guidance installer-template" "$cur"
                    ;;
                init)
                    _base_basectl_completion_compgen "--path --repo --description --copyright-holder --private --public --no-configure --no-protect-default-branch --project --project-owner --project-schema --initiative-option --no-project --dry-run -v -h --help" "$cur"
                    ;;
                clone)
                    _base_basectl_completion_compgen "--owner --path --dry-run -v -h --help" "$cur"
                    ;;
                check)
                    _base_basectl_completion_compgen "--agent-guidance -v -h --help" "$cur"
                    ;;
                configure)
                    _base_basectl_completion_compgen "--repo --no-protect-default-branch --project --project-owner --project-schema --initiative-option --no-project --dry-run -v -h --help" "$cur"
                    ;;
                agent-guidance)
                    _base_basectl_completion_compgen "--repo-name --default-branch --validation-command --dry-run -v -h --help" "$cur"
                    ;;
                installer-template)
                    _base_basectl_completion_compgen "--dry-run -v -h --help" "$cur"
                    ;;
            esac
            ;;
        ci)
            case "${COMP_WORDS[2]:-}" in
                "")
                    _base_basectl_completion_compgen "setup check doctor" "$cur"
                    ;;
                setup)
                    _base_basectl_completion_project_profiles_or_options "$cur" "--format --manifest --profile --recreate-venv -v -h --help"
                    ;;
                check|doctor)
                    _base_basectl_completion_project_profiles_or_options "$cur" "--format --manifest --profile -v -h --help"
                    ;;
            esac
            ;;
        release)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "check plan notes publish" "$cur"
            else
                _base_basectl_completion_compgen "--version --manifest --dry-run --yes -h --help" "$cur"
            fi
            ;;
        clean)
            _base_basectl_completion_compgen "--older-than --keep-last --dry-run -v -h --help" "$cur"
            ;;
        logs)
            _base_basectl_completion_compgen "--command --limit --path --tail --open --lines -v -h --help" "$cur"
            ;;
        config)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "path show doctor" "$cur"
            fi
            ;;
        doctor)
            _base_basectl_completion_project_profiles_or_options "$cur" "--profile --format -v -h --help"
            ;;
        gh)
            case "${COMP_WORDS[2]:-}" in
                "")
                    _base_basectl_completion_compgen "issue pr branch worktree todo project" "$cur"
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
                worktree)
                    if ((COMP_CWORD == 3)); then
                        _base_basectl_completion_compgen "prune" "$cur"
                    else
                        _base_basectl_completion_compgen "--dry-run --yes -h --help" "$cur"
                    fi
                    ;;
                todo)
                    if ((COMP_CWORD == 3)); then
                        _base_basectl_completion_compgen "import" "$cur"
                    else
                        _base_basectl_completion_compgen "--dry-run --file -h --help" "$cur"
                    fi
                    ;;
                project)
                    case "${COMP_WORDS[3]:-}" in
                        "")
                            _base_basectl_completion_compgen "doctor configure issue" "$cur"
                            ;;
                        doctor)
                            _base_basectl_completion_compgen "--project --owner --schema -h --help" "$cur"
                            ;;
                        configure)
                            _base_basectl_completion_compgen "--project --owner --schema --initiative-option --repo --dry-run -h --help" "$cur"
                            ;;
                        issue)
                            if ((COMP_CWORD == 4)); then
                                _base_basectl_completion_compgen "set-fields" "$cur"
                            else
                                _base_basectl_completion_compgen "--repo --project --owner --status --priority --area --initiative --size --dry-run -h --help" "$cur"
                            fi
                            ;;
                    esac
                    ;;
            esac
            ;;
        onboard)
            _base_basectl_completion_profiles_or_options \
                "$cur" \
                "--profile --dry-run --yes --no-profile -v -h --help"
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
