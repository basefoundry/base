#
# Zsh completion for basectl.
#

typeset -g _BASE_BASECTL_COMPLETION_PROJECT_NAMES=''
typeset -gi _BASE_BASECTL_COMPLETION_PROJECT_NAMES_SET=0
typeset -gi _BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT=0

_base_basectl_completion_project_cache_ttl() {
    local ttl="${BASE_COMPLETION_PROJECT_CACHE_TTL:-5}"

    case "$ttl" in
        ''|*[!0-9]*) ttl=5 ;;
    esac
    printf '%s\n' "$ttl"
}

_base_basectl_completion_now() {
    printf '%s\n' "${SECONDS:-0}"
}

_base_basectl_completion_project_names_from_list() {
    local line name names=''

    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        name="${line%%$'\t'*}"
        [[ -n "$name" ]] || continue
        names+="${names:+$'\n'}$name"
    done

    print -r -- "$names"
}

_base_basectl_completion_refresh_project_cache() {
    local names now ttl project_list
    local wrapper="${BASE_HOME:-}/bin/base-wrapper"

    if [[ ! -x "$wrapper" ]]; then
        _BASE_BASECTL_COMPLETION_PROJECT_NAMES=''
        _BASE_BASECTL_COMPLETION_PROJECT_NAMES_SET=1
        _BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT=0
        return 0
    fi

    ttl="$(_base_basectl_completion_project_cache_ttl)"
    now="$(_base_basectl_completion_now)"
    if ((ttl > 0)) &&
        ((_BASE_BASECTL_COMPLETION_PROJECT_NAMES_SET)) &&
        ((_BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT > now)); then
        return 0
    fi

    project_list="$("$wrapper" --project base base_projects list 2>/dev/null || true)"
    names="$(_base_basectl_completion_project_names_from_list <<<"$project_list")"
    _BASE_BASECTL_COMPLETION_PROJECT_NAMES="$names"
    _BASE_BASECTL_COMPLETION_PROJECT_NAMES_SET=1
    if ((ttl > 0)); then
        _BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT=$((now + ttl))
    else
        _BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT=0
    fi
}

_base_basectl_completion_project_names() {
    _base_basectl_completion_refresh_project_cache || return 0
    printf '%s\n' "$_BASE_BASECTL_COMPLETION_PROJECT_NAMES"
}

_base_basectl_completion_describe_projects() {
    local -a project_names

    _base_basectl_completion_refresh_project_cache || return 0
    project_names=("${(@f)_BASE_BASECTL_COMPLETION_PROJECT_NAMES}")
    _describe -t projects 'Base project' project_names
}

_base_basectl_completion() {
    local -a commands project_names
    local state

    commands=(
        'activate:Start an interactive Base runtime subshell for a project'
        'setup:Install and bootstrap the local Base CLI environment'
        'check:Verify the local Base CLI environment'
        'test:Run a project test command'
        'export-context:Export a project AI context bundle'
        'devcontainer:Preview or write a Dev Containers configuration'
        'devenv-report:Report Nix/devenv compatibility for a Base manifest'
        'build:Run project build targets'
        'demo:Run a project interactive demo'
        'run:Run a project command'
        'repo:Create, check, and configure repository baseline'
        'ci:Run Base setup, checks, and diagnostics in CI'
        'release:Inspect release readiness, notes, and publishing'
        'prompt:Print repo-owned Markdown prompts'
        'docs:Open the Base documentation home page on GitHub'
        'clean:Remove old Base CLI runtime artifacts'
        'logs:List and open recent Base CLI runtime logs'
        'history:List recent Base command history records'
        'config:Inspect Base machine-local user config'
        'trust:Manage manifest command trust approvals'
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
                _base_basectl_completion_describe_projects
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
        trust)
            case "${words[3]:-}" in
                status)
                    _arguments '1:trust command:(status allow revoke)' \
                        '2:Base project:->projects' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '--format[Output format]:format:(text json)' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                allow)
                    _arguments '1:trust command:(status allow revoke)' \
                        '2:Base project:->projects' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '--manifest-sha256[Expected manifest SHA-256]:sha256:' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                revoke)
                    _arguments '1:trust command:(status allow revoke)' \
                        '2:Base project:->projects' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '1:trust command:(status allow revoke)'
                    ;;
            esac
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        workspace)
            case "${words[3]:-}" in
                status|check|doctor)
                    _arguments '1:workspace command:(status check doctor onboarding clone pull init configure)' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '--manifest[Local workspace manifest]:path:_files' \
                        '--format[Output format]:format:(text json)' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                clone)
                    _arguments '1:workspace command:(status check doctor onboarding clone pull init configure)' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '--manifest[Local workspace manifest]:path:_files' \
                        '--include-optional[Include optional manifest repositories when cloning]' \
                        '--dry-run[Show planned workspace clone work without writing]' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                pull)
                    _arguments '1:workspace command:(status check doctor onboarding clone pull init configure)' \
                        '--source[Canonical workspace manifest source]:url-or-path:' \
                        '--manifest[Local workspace manifest]:path:_files' \
                        '--dry-run[Show planned workspace pull work without writing]' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                init)
                    _arguments '1:workspace command:(status check doctor onboarding clone pull init configure)' \
                        '2:workspace source:' \
                        '--owner[GitHub owner for short workspace repository names]:owner:' \
                        '--path[Workspace configuration repository checkout path]:path:_files' \
                        '--workspace[Workspace directory for member repositories]:path:_files' \
                        '--manifest[Workspace manifest path or name]:path:_files' \
                        '--include-optional[Include optional manifest repositories when cloning]' \
                        '--dry-run[Show planned workspace initialization without writing]' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                configure)
                    _arguments '1:workspace command:(status check doctor onboarding clone pull init configure)' \
                        '--workspace[Workspace directory to configure]:path:_files' \
                        '--manifest[Local workspace manifest]:path:_files' \
                        '--dry-run[Show planned workspace configuration without applying repo changes]' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '1:workspace command:(status check doctor onboarding clone pull init configure)'
                    ;;
            esac
            ;;
        setup)
            _arguments '--ci[Run setup with CI-safe defaults]' \
                '--format[Output format for --ci]:format:(text json)' \
                '--profile[Install prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                '--dry-run[Log without making changes]' \
                '--manifest[Use a specific manifest]:path:_files' \
                '--notify[Force a setup completion notification]' \
                '--no-notify[Disable setup completion notification]' \
                '--recreate-venv[Recreate the Base venv]' \
                '--yes[Apply setup changes that require explicit confirmation]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        check)
            _arguments '--ci[Run checks with CI-safe defaults]' \
                '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                '--format[Output format]:format:(text json)' \
                '--manifest[Use a specific manifest]:path:_files' \
                '--remote-network[Opt in to bounded project Git origin reachability checks]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        test)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved test command without running it]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        export-context)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--format[Export format]:format:(markdown zip)' \
                '--output[Output path]:path:_files' \
                '--print[Print the Markdown export to stdout]' \
                '--list-files[List files in export order]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        devcontainer)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--format[Output format]:format:(text json)' \
                '--write[Write .devcontainer/devcontainer.json]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        devenv-report)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        build)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print resolved build commands without running them]' \
                '--list[List build targets]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects' '*:Build target:'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        demo)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved demo script without running it]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        run)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved command without running it]' \
                '--list[List runnable project commands]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects' '2:Project command:'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        prompt)
            _arguments '1:prompt:(list product-self-review)' \
                '--output[Write rendered prompt Markdown to this path]:path:_files' \
                '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        docs)
            _arguments '--show-url[Print the documentation URL without opening a browser]' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        repo)
            case "${words[3]:-}" in
                init)
                    _arguments '1:repo command:(init clone check configure agent-guidance installer-template)' \
                        '2:repository name:' \
                        '--path[Target path]:path:_files' \
                        '--repo[GitHub repository]:repo:' \
                        '--pr[Commit the generated baseline on a branch and open a pull request]' \
                        '--description[Repository description]:description:' \
                        '--copyright-holder[Copyright holder]:name:' \
                        '--private[Create a private GitHub repository when needed]' \
                        '--public[Create a public GitHub repository when needed]' \
                        '--no-configure[Skip GitHub configuration]' \
                        '--no-protect-default-branch[Skip Base-managed default branch protection]' \
                        '--project[GitHub Project title]:title:' \
                        '--project-owner[GitHub Project owner]:owner:' \
                        '--project-schema[Project metadata schema]:schema:(base-project)' \
                        '--initiative-option[Initiative option to seed]:name:' \
                        '--copy-project-fields-from[Copy missing Project item field values from another Project]:title:' \
                        '--no-project[Skip GitHub Project metadata configuration]' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                clone)
                    _arguments '1:repo command:(init clone check configure agent-guidance installer-template)' \
                        '2:repository name or owner/name:' \
                        '--owner[GitHub owner for short repository names]:owner:' \
                        '--path[Clone destination]:path:_files' \
                        '--dry-run[Print planned clone without modifying the filesystem]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                check)
                    _arguments '1:repo command:(init clone check configure agent-guidance installer-template)' \
                        '2:path:_files' \
                        '--agent-guidance[Include optional agent guidance files]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                configure)
                    _arguments '1:repo command:(init clone check configure agent-guidance installer-template)' \
                        '2:path:_files' \
                        '--repo[GitHub repository]:repo:' \
                        '--no-protect-default-branch[Skip Base-managed default branch protection]' \
                        '--project[GitHub Project title]:title:' \
                        '--project-owner[GitHub Project owner]:owner:' \
                        '--project-schema[Project metadata schema]:schema:(base-project)' \
                        '--initiative-option[Initiative option to seed]:name:' \
                        '--copy-project-fields-from[Copy missing Project item field values from another Project]:title:' \
                        '--replace-project[Replace a nonstandard existing Project from base-project-template]' \
                        '--no-project[Skip GitHub Project metadata configuration]' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                agent-guidance)
                    _arguments '1:repo command:(init clone check configure agent-guidance installer-template)' \
                        '2:path:_files' \
                        '--repo[GitHub repository for pull request]:repo:' \
                        '--repo-name[Repository name for generated guidance]:name:' \
                        '--default-branch[Default branch for generated guidance]:branch:' \
                        '--validation-command[Validation command for generated guidance]:command:' \
                        '--pr[Commit generated guidance files and open a draft pull request]' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                installer-template)
                    _arguments '1:repo command:(init clone check configure agent-guidance installer-template)' \
                        '2:path:_files' \
                        '--print[Print the maintained template to stdout instead of writing a file]' \
                        '--stdout[Alias for --print]' \
                        '--repo[GitHub repository for pull request]:repo:' \
                        '--pr[Commit generated installer template and open a draft pull request]' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '1:repo command:(init clone check configure agent-guidance installer-template)'
                    ;;
            esac
            ;;
        ci)
            case "${words[3]:-}" in
                setup)
                    _arguments '1:ci command:(setup check doctor)' \
                        '--format[Output format]:format:(text json)' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                        '--recreate-venv[Recreate the project virtual environment]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '2:Base project:->projects'
                    ;;
                check|doctor)
                    _arguments '1:ci command:(setup check doctor)' \
                        '--format[Output format]:format:(text json)' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '2:Base project:->projects'
                    ;;
                *)
                    _arguments '1:ci command:(setup check doctor)'
                    ;;
            esac
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
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
        history)
            _arguments '--project[Filter by Base project]:project:' \
                '--command[Filter by command]:command:' \
                '--status[Filter by status]:status:(ok warn error)' \
                '--limit[Number of records]:count:' \
                '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        config)
            _arguments '1:config command:(path show doctor)'
            ;;
        doctor)
            _arguments '--ci[Run diagnostics with CI-safe defaults]' \
                '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                '--format[Output format]:format:(text json)' \
                '--manifest[Use a specific manifest]:path:_files' \
                '--remote-network[Opt in to bounded project Git origin reachability diagnostics]' \
                '--no-color[Disable doctor status colors and symbols in text output]' \
                '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        gh)
            case "${words[3]:-}" in
                issue)
                    _arguments '1:gh area:(issue pr branch worktree project)' \
                        '2:issue command:(list create start)' \
                        '--category[Issue category]:category:(bug enhancement documentation ci security)' \
                        '--title[Issue title]:title:' \
                        '--body[Issue body]:body:' \
                        '--repo[GitHub repository]:repo:' \
                        '--assignee[Issue assignee]:login:' \
                        '--no-assignee[Do not assign the issue]' \
                        '--project[GitHub Project title]:title:' \
                        '--project-owner[GitHub Project owner]:owner:' \
                        '--size[Project size option]:size:(T S M L)' \
                        '--no-project[Skip Project metadata updates]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                pr)
                    _arguments '1:gh area:(issue pr branch worktree project)' \
                        '2:pr command:(create status checks ready merge)'
                    ;;
                branch)
                    _arguments '1:gh area:(issue pr branch worktree project)' \
                        '2:branch command:(stale prune)' \
                        '--days[Stale threshold in days]:days:' \
                        '--dry-run[Show planned deletions]' \
                        '--yes[Apply branch pruning]' \
                        '--remote[Prune stale remote tracking refs]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                worktree)
                    _arguments '1:gh area:(issue pr branch worktree project)' \
                        '2:worktree command:(prune)' \
                        '--dry-run[Show planned removals]' \
                        '--yes[Apply worktree pruning]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                project)
                    case "${words[4]:-}" in
                        doctor)
                            _arguments '1:gh area:(issue pr branch worktree project)' \
                                '2:project command:(doctor configure issue)' \
                                '--project[GitHub Project title]:title:' \
                                '--owner[GitHub Project owner]:owner:' \
                                '--schema[Project metadata schema]:schema:(base-project)' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        configure)
                            _arguments '1:gh area:(issue pr branch worktree project)' \
                                '2:project command:(doctor configure issue)' \
                                '--project[GitHub Project title]:title:' \
                                '--owner[GitHub Project owner]:owner:' \
                                '--schema[Project metadata schema]:schema:(base-project)' \
                                '--initiative-option[Initiative option to seed]:name:' \
                                '--repo[GitHub repository]:repo:' \
                                '--replace-project[Replace a nonstandard existing Project from base-project-template]' \
                                '--dry-run[Print planned changes]' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        issue)
                            _arguments '1:gh area:(issue pr branch worktree project)' \
                                '2:project command:(doctor configure issue)' \
                                '3:issue command:(set-fields)' \
                                '4:issue number:' \
                                '--repo[GitHub repository]:repo:' \
                                '--project[GitHub Project title]:title:' \
                                '--owner[GitHub Project owner]:owner:' \
                                '--status[Status option]:status:' \
                                '--priority[Priority option]:priority:' \
                                '--area[Area option]:area:' \
                                '--initiative[Initiative option]:initiative:' \
                                '--size[Size option]:size:' \
                                '--dry-run[Print planned changes]' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        *)
                            _arguments '1:gh area:(issue pr branch worktree project)' \
                                '2:project command:(doctor configure issue)'
                            ;;
                    esac
                    ;;
                *)
                    _arguments '1:gh area:(issue pr branch worktree project)'
                    ;;
            esac
            ;;
        onboard)
            _arguments '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                '--dry-run[Explain planned onboarding steps without making changes]' \
                '--yes[Accept default answers for setup and shell profile prompts]' \
                '--no-profile[Skip shell profile updates]' \
                '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        update-profile)
            _arguments '--defaults[Enable shell defaults]' '--no-defaults[Disable shell defaults]' \
                '--remove[Remove Base-managed shell startup sections]' \
                '--dry-run[Log without changing files]' '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        update)
            _arguments '--dry-run[Log without pulling or running setup]' '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]' \
                '1:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
    esac
}

if ! whence -w compdef >/dev/null 2>&1; then
    autoload -Uz compinit
    compinit -i
fi

compdef _base_basectl_completion basectl
