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
    local state

    commands=(
        'activate:Start an interactive Base runtime subshell for a project'
        'setup:Install and bootstrap the local Base CLI environment'
        'check:Verify the local Base CLI environment'
        'test:Run a project test command'
        'build:Run project build targets'
        'demo:Run a project interactive demo'
        'run:Run a project command'
        'repo:Create, check, and configure repository baseline'
        'ci:Run Base setup, checks, and diagnostics in CI'
        'release:Inspect release readiness, notes, and publishing'
        'clean:Remove old Base CLI runtime artifacts'
        'logs:List and open recent Base CLI runtime logs'
        'config:Inspect Base machine-local user config'
        'doctor:Diagnose the local Base environment'
        'gh:Manage GitHub issues, pull requests, branches, and hygiene'
        'onboard:Guide a user through first Base setup'
        'update-profile:Refresh Base-managed shell startup sections'
        'update:Update Base and rerun setup'
        'projects:List Base-managed projects'
        'workspace:Show workspace-level project status, checks, and diagnostics'
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
                _arguments '--workspace[Workspace directory to scan]:path:_files' \
                    '--no-cd[Preserve the caller current directory]' \
                    '-v[Enable DEBUG logging]' \
                    '(-h --help)'{-h,--help}'[Show help text]'
            fi
            ;;
        projects)
            _arguments '1:projects command:(list)' \
                '--workspace[Workspace directory to scan]:path:_files' \
                '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        workspace)
            _arguments '1:workspace command:(status check doctor)' \
                '--workspace[Workspace directory to scan]:path:_files' \
                '--manifest[Local workspace manifest]:path:_files' \
                '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        setup)
            _arguments '--profile[Install prerequisite profiles]:profile:(dev sre ai dev,sre dev,ai sre,ai dev,sre,ai)' \
                '--dry-run[Log without making changes]' \
                '--manifest[Use a specific manifest]:path:_files' \
                '--notify[Force a setup completion notification]' \
                '--no-notify[Disable setup completion notification]' \
                '--recreate-venv[Recreate the Base venv]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        check)
            _arguments '--profile[Include prerequisite profiles]:profile:(dev sre ai dev,sre dev,ai sre,ai dev,sre,ai)' \
                '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                project_names=("${(@f)$(_base_basectl_completion_project_names)}")
                _describe -t projects 'Base project' project_names
            fi
            ;;
        test)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved test command without running it]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                project_names=("${(@f)$(_base_basectl_completion_project_names)}")
                _describe -t projects 'Base project' project_names
            fi
            ;;
        build)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print resolved build commands without running them]' \
                '--list[List build targets]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects' '*:Build target:'
            if [[ "$state" == projects ]]; then
                project_names=("${(@f)$(_base_basectl_completion_project_names)}")
                _describe -t projects 'Base project' project_names
            fi
            ;;
        demo)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved demo script without running it]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                project_names=("${(@f)$(_base_basectl_completion_project_names)}")
                _describe -t projects 'Base project' project_names
            fi
            ;;
        run)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved command without running it]' \
                '--list[List runnable project commands]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects' '2:Project command:'
            if [[ "$state" == projects ]]; then
                project_names=("${(@f)$(_base_basectl_completion_project_names)}")
                _describe -t projects 'Base project' project_names
            fi
            ;;
        repo)
            case "${words[3]:-}" in
                init)
                    _arguments '1:repo command:(init check configure agent-guidance installer-template)' \
                        '2:repository name:' \
                        '--path[Target path]:path:_files' \
                        '--repo[GitHub repository]:repo:' \
                        '--description[Repository description]:description:' \
                        '--copyright-holder[Copyright holder]:name:' \
                        '--private[Create a private GitHub repository when needed]' \
                        '--public[Create a public GitHub repository when needed]' \
                        '--no-configure[Skip GitHub configuration]' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                check)
                    _arguments '1:repo command:(init check configure agent-guidance installer-template)' \
                        '2:path:_files' \
                        '--agent-guidance[Include optional agent guidance files]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                configure)
                    _arguments '1:repo command:(init check configure agent-guidance installer-template)' \
                        '2:path:_files' \
                        '--repo[GitHub repository]:repo:' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                agent-guidance)
                    _arguments '1:repo command:(init check configure agent-guidance installer-template)' \
                        '2:path:_files' \
                        '--repo-name[Repository name for generated guidance]:name:' \
                        '--default-branch[Default branch for generated guidance]:branch:' \
                        '--validation-command[Validation command for generated guidance]:command:' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                installer-template)
                    _arguments '1:repo command:(init check configure agent-guidance installer-template)' \
                        '2:path:_files' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '1:repo command:(init check configure agent-guidance installer-template)'
                    ;;
            esac
            ;;
        ci)
            case "${words[3]:-}" in
                setup)
                    _arguments '1:ci command:(setup check doctor)' \
                        '--format[Output format]:format:(text json)' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--profile[Include prerequisite profiles]:profile:(dev sre ai dev,sre dev,ai sre,ai dev,sre,ai)' \
                        '--recreate-venv[Recreate the project virtual environment]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '2:Base project:->projects'
                    ;;
                check|doctor)
                    _arguments '1:ci command:(setup check doctor)' \
                        '--format[Output format]:format:(text json)' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--profile[Include prerequisite profiles]:profile:(dev sre ai dev,sre dev,ai sre,ai dev,sre,ai)' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '2:Base project:->projects'
                    ;;
                *)
                    _arguments '1:ci command:(setup check doctor)'
                    ;;
            esac
            if [[ "$state" == projects ]]; then
                project_names=("${(@f)$(_base_basectl_completion_project_names)}")
                _describe -t projects 'Base project' project_names
            fi
            ;;
        release)
            _arguments '1:release command:(check plan notes publish)' \
                '--version[Release version]:version:' \
                '--manifest[Use a specific manifest]:path:_files' \
                '--dry-run[Print publish actions without creating tags or releases]' \
                '--yes[Publish without an interactive confirmation prompt]' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        clean)
            _arguments '--older-than[Artifact age]:age:' \
                '--keep-last[Keep newest log files per CLI log directory]:count:' \
                '--dry-run[Log without removing files]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        logs)
            _arguments '--command[Filter by command]:command:' \
                '--limit[Number of entries]:count:' \
                '--path[Print most recent log path]' \
                '--tail[Tail and follow most recent log]' \
                '--open[Open most recent log]' \
                '--lines[Lines to show before following]:count:' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        config)
            _arguments '1:config command:(path show doctor)'
            ;;
        doctor)
            _arguments '--profile[Include prerequisite profiles]:profile:(dev sre ai dev,sre dev,ai sre,ai dev,sre,ai)' \
                '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                project_names=("${(@f)$(_base_basectl_completion_project_names)}")
                _describe -t projects 'Base project' project_names
            fi
            ;;
        gh)
            case "${words[3]:-}" in
                issue)
                    _arguments '1:gh area:(issue pr branch worktree todo)' \
                        '2:issue command:(list create start)' \
                        '--category[Issue category]:category:(bug enhancement documentation ci security)' \
                        '--title[Issue title]:title:' \
                        '--body[Issue body]:body:' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                pr)
                    _arguments '1:gh area:(issue pr branch worktree todo)' \
                        '2:pr command:(create status checks ready merge)'
                    ;;
                branch)
                    _arguments '1:gh area:(issue pr branch worktree todo)' \
                        '2:branch command:(stale prune)' \
                        '--days[Stale threshold in days]:days:' \
                        '--dry-run[Show planned deletions]' \
                        '--yes[Apply branch pruning]' \
                        '--remote[Prune stale remote tracking refs]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                worktree)
                    _arguments '1:gh area:(issue pr branch worktree todo)' \
                        '2:worktree command:(prune)' \
                        '--dry-run[Show planned removals]' \
                        '--yes[Apply worktree pruning]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                todo)
                    _arguments '1:gh area:(issue pr branch worktree todo)' \
                        '2:todo command:(import)' \
                        '--dry-run[Show planned issues]' \
                        '--file[TODO file]:path:_files' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '1:gh area:(issue pr branch worktree todo)'
                    ;;
            esac
            ;;
        onboard)
            _arguments '--profile[Include prerequisite profiles]:profile:(dev sre ai dev,sre dev,ai sre,ai dev,sre,ai)' \
                '--dry-run[Explain planned onboarding steps without making changes]' \
                '--yes[Accept default answers for setup and shell profile prompts]' \
                '--no-profile[Skip shell profile updates]' \
                '-v[Enable DEBUG logging]' \
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
