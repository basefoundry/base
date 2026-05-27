#
# Zsh completion for basectl.
#

_base_basectl_completion_project_names() {
    local wrapper="${BASE_HOME:-}/bin/base-wrapper"

    [[ -x "$wrapper" ]] || return 0
    "$wrapper" --project base base_projects list 2>/dev/null | awk -F '\t' '{print $1}'
}

_base_basectl_completion() {
    local -a commands project_names

    commands=(
        'activate:Start an interactive Base runtime subshell for a project'
        'setup:Install and bootstrap the local Base CLI environment'
        'check:Verify the local Base CLI environment'
        'clean:Remove old Base CLI runtime artifacts'
        'doctor:Diagnose the local Base environment'
        'update-profile:Refresh Base-managed shell startup sections'
        'update:Update Base and rerun setup'
        'projects:List Base-managed projects'
        'version:Show the installed Base version'
        'help:Show help text'
    )

    if ((CURRENT == 2)); then
        _describe -t commands 'basectl command' commands
        return
    fi

    case "${words[2]:-}" in
        activate)
            if ((CURRENT == 3)); then
                project_names=("${(@f)$(_base_basectl_completion_project_names)}")
                _describe -t projects 'Base project' project_names
            else
                _arguments '--workspace[Workspace directory to scan]:path:_files' '-v[Enable DEBUG logging]' \
                    '(-h --help)'{-h,--help}'[Show help text]'
            fi
            ;;
        projects)
            _arguments '1:projects command:(list)'
            ;;
        setup)
            _arguments '--dev[Install developer prerequisites]' '--dry-run[Log without making changes]' \
                '--manifest[Use a specific manifest]:path:_files' '--recreate-venv[Recreate the Base venv]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        check)
            _arguments '--dev[Include developer prerequisite checks]' '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        clean)
            _arguments '--older-than[Artifact age]:age:' '--dry-run[Log without removing files]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        doctor)
            _arguments '--dev[Include developer prerequisite checks]' '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        update-profile)
            _arguments '--defaults[Enable shell defaults]' '--no-defaults[Disable shell defaults]' \
                '--dry-run[Log without changing files]' '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        update)
            _arguments '--dry-run[Log without pulling or running setup]' '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
    esac
}

if ! whence -w compdef >/dev/null 2>&1; then
    autoload -Uz compinit
    compinit -i
fi

compdef _base_basectl_completion basectl
