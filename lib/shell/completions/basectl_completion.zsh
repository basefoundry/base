#
# Zsh completion for basectl.
#

typeset -g _BASE_BASECTL_COMPLETION_PROJECT_NAMES=''
typeset -gi _BASE_BASECTL_COMPLETION_PROJECT_NAMES_SET=0
typeset -gi _BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT=0
typeset -g _BASE_BASECTL_COMPLETION_DECODED_VALUE=''

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

_base_basectl_completion_validate_utf8_hex() {
    local encoded="$1"
    local pair
    integer byte continuation continuation_count continuation_max continuation_min first
    integer index=0 length=${#encoded}

    while ((index < length)); do
        pair="${encoded:$index:2}"
        byte=$((16#$pair))
        ((index += 2))
        if ((byte <= 0x7f)); then
            continue
        elif ((byte >= 0xc2 && byte <= 0xdf)); then
            continuation_count=1
            continuation_min=0x80
            continuation_max=0xbf
        elif ((byte >= 0xe0 && byte <= 0xef)); then
            continuation_count=2
            if ((byte == 0xe0)); then
                continuation_min=0xa0
                continuation_max=0xbf
            elif ((byte == 0xed)); then
                continuation_min=0x80
                continuation_max=0x9f
            else
                continuation_min=0x80
                continuation_max=0xbf
            fi
        elif ((byte >= 0xf0 && byte <= 0xf4)); then
            continuation_count=3
            if ((byte == 0xf0)); then
                continuation_min=0x90
                continuation_max=0xbf
            elif ((byte == 0xf4)); then
                continuation_min=0x80
                continuation_max=0x8f
            else
                continuation_min=0x80
                continuation_max=0xbf
            fi
        else
            return 1
        fi

        ((index + continuation_count * 2 <= length)) || return 1
        pair="${encoded:$index:2}"
        first=$((16#$pair))
        ((first >= continuation_min && first <= continuation_max)) || return 1
        ((index += 2))
        for ((continuation = 1; continuation < continuation_count; continuation += 1)); do
            pair="${encoded:$index:2}"
            byte=$((16#$pair))
            ((byte >= 0x80 && byte <= 0xbf)) || return 1
            ((index += 2))
        done
    done
}

_base_basectl_completion_decode_hex() {
    local encoded="$1"
    local byte decoded='' pair
    integer index

    if (( ${#encoded} % 2 != 0 )) || [[ "$encoded" == *[^0-9a-f]* ]]; then
        return 1
    fi
    _base_basectl_completion_validate_utf8_hex "$encoded" || return 1

    for ((index = 0; index < ${#encoded}; index += 2)); do
        pair="${encoded:$index:2}"
        [[ "$pair" != 00 ]] || return 1
        printf -v byte '%b' "\\x$pair"
        decoded+="$byte"
    done
    _BASE_BASECTL_COMPLETION_DECODED_VALUE="$decoded"
}

_base_basectl_completion_project_names_from_protocol() {
    # Completion loads independently of the Bash runtime, so keep a narrow,
    # strict reader for the versioned project-list-entry schema here.
    local payload="$1"
    local count_text='' encoded line names='' project_name
    integer ended=0 in_record=0 line_number=0 max_record_count=1000000
    integer next_record=0 phase=0 record_count=0

    while IFS= read -r line || [[ -n "$line" ]]; do
        ((line_number += 1))
        case "$line_number" in
            1)
                [[ "$line" == BASE_COMMAND_PROTOCOL_V1 ]] || return 1
                continue
                ;;
            2)
                [[ "$line" == record_type=project-list-entry ]] || return 1
                continue
                ;;
            3)
                [[ "$line" == record_count=* ]] || return 1
                count_text="${line#record_count=}"
                case "$count_text" in
                    ''|*[!0-9]*|0?*) return 1 ;;
                esac
                ((${#count_text} <= ${#max_record_count})) || return 1
                record_count=$((10#$count_text))
                ((record_count <= max_record_count)) || return 1
                continue
                ;;
        esac

        ((ended == 0)) || return 1
        if ((in_record == 0)); then
            if [[ "$line" == "record=$next_record" && next_record -lt record_count ]]; then
                in_record=1
                phase=1
                continue
            fi
            if [[ "$line" == end_protocol= && next_record -eq record_count ]]; then
                ended=1
                continue
            fi
            return 1
        fi

        case "$phase" in
            1)
                [[ "$line" == field.project_name:string=* ]] || return 1
                encoded="${line#field.project_name:string=}"
                _base_basectl_completion_decode_hex "$encoded" || return 1
                project_name="$_BASE_BASECTL_COMPLETION_DECODED_VALUE"
                phase=2
                ;;
            2)
                [[ "$line" == field.project_root:string=* ]] || return 1
                encoded="${line#field.project_root:string=}"
                _base_basectl_completion_decode_hex "$encoded" || return 1
                phase=3
                ;;
            3)
                [[ "$line" == "end_record=$next_record" ]] || return 1
                [[ -z "$names" ]] || names+=$'\n'
                names+="$project_name"
                ((next_record += 1))
                in_record=0
                phase=0
                ;;
            *)
                return 1
                ;;
        esac
    done <<<"$payload"

    ((line_number >= 3 && in_record == 0 && ended == 1)) || return 1
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

    project_list="$("$wrapper" --project base base_projects list --format command-protocol 2>/dev/null || true)"
    if ! names="$(_base_basectl_completion_project_names_from_protocol "$project_list")"; then
        names=''
    fi
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
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--no-cd[Preserve the caller current directory]' \
                '-v[Enable DEBUG logging]' \
                '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        projects)
            _arguments '2:projects command:(list)' \
                '--workspace[Workspace directory to scan]:path:_files' \
                '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        trust)
            case "${words[3]:-}" in
                status)
                    _arguments '2:trust command:(status allow revoke)' \
                        '3::Base project:->projects' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '--format[Output format]:format:(text json)' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                allow)
                    _arguments '2:trust command:(status allow revoke)' \
                        '3:Base project:->projects' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '--manifest-sha256[Expected manifest SHA-256]:sha256:' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                revoke)
                    _arguments '2:trust command:(status allow revoke)' \
                        '3:Base project:->projects' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '2:trust command:(status allow revoke)'
                    ;;
            esac
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        workspace)
            case "${words[3]:-}" in
                status|check|doctor|onboarding|agent-brief)
                    _arguments '2:workspace command:(status check doctor onboarding agent-brief clone pull init configure)' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '--manifest[Local workspace manifest]:path:_files' \
                        '--format[Output format]:format:(text json)' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                clone)
                    _arguments '2:workspace command:(status check doctor onboarding agent-brief clone pull init configure)' \
                        '--workspace[Workspace directory to scan]:path:_files' \
                        '--manifest[Local workspace manifest]:path:_files' \
                        '--include-optional[Include optional manifest repositories when cloning]' \
                        '--dry-run[Show planned workspace clone work without writing]' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                pull)
                    _arguments '2:workspace command:(status check doctor onboarding agent-brief clone pull init configure)' \
                        '--source[Canonical workspace manifest source]:url-or-path:' \
                        '--manifest[Local workspace manifest]:path:_files' \
                        '--dry-run[Show planned workspace pull work without writing]' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                init)
                    _arguments '2:workspace command:(status check doctor onboarding agent-brief clone pull init configure)' \
                        '3:workspace source:' \
                        '--owner[GitHub owner for short workspace repository names]:owner:' \
                        '--path[Workspace configuration repository checkout path]:path:_files' \
                        '--workspace[Workspace directory for member repositories]:path:_files' \
                        '--manifest[Workspace manifest path or name]:path:_files' \
                        '--include-optional[Include optional manifest repositories when cloning]' \
                        '--dry-run[Show planned workspace initialization without writing]' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                configure)
                    _arguments '2:workspace command:(status check doctor onboarding agent-brief clone pull init configure)' \
                        '--workspace[Workspace directory to configure]:path:_files' \
                        '--manifest[Local workspace manifest]:path:_files' \
                        '--dry-run[Show planned workspace configuration without applying repo changes]' \
                        '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '2:workspace command:(status check doctor onboarding agent-brief clone pull init configure)'
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
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        check)
            _arguments '--ci[Run checks with CI-safe defaults]' \
                '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                '--format[Output format]:format:(text json)' \
                '--manifest[Use a specific manifest]:path:_files' \
                '--remote-network[Opt in to bounded project Git origin reachability checks]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        test)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved test command without running it]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects'
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
                '2:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        devcontainer)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--format[Output format]:format:(text json)' \
                '--write[Write .devcontainer/devcontainer.json]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        devenv-report)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--format[Output format]:format:(text json)' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        build)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print resolved build commands without running them]' \
                '--list[List build targets]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects' '*:Build target:'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        demo)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved demo script without running it]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        run)
            _arguments '--workspace[Workspace directory to scan]:path:_files' \
                '--dry-run[Print the resolved command without running it]' \
                '--list[List runnable project commands]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]' \
                '2:Base project:->projects' '3:Project command:'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        prompt)
            case "${words[3]:-}" in
                list)
                    _arguments '2:prompt:(list product-self-review)' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '2:prompt:(list product-self-review)' \
                        '--output[Write rendered prompt Markdown to this path]:path:_files' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
            esac
            ;;
        docs)
            _arguments '--show-url[Print the documentation URL without opening a browser]' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        repo)
            case "${words[3]:-}" in
                init)
                    _arguments '2:repo command:(init clone check configure agent-guidance installer-template)' \
                        '3:repository name:' \
                        '--path[Target path]:path:_files' \
                        '--repo[GitHub repository]:repo:' \
                        '--issue[Issue number for pull request]:number:' \
                        '--category[Issue category for pull request dry-run]:category:(bug enhancement documentation ci security)' \
                        '--pr[Commit the generated baseline on a branch and open a pull request]' \
                        '--agent-ready[Also seed repo-local agent guidance files]' \
                        '--release[Seed the generic release contract and process documentation]' \
                        '--language[Add project language metadata; may be repeated]:csv:' \
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
                    _arguments '2:repo command:(init clone check configure agent-guidance installer-template)' \
                        '3:repository name or owner/name:' \
                        '--owner[GitHub owner for short repository names]:owner:' \
                        '--path[Clone destination]:path:_files' \
                        '--dry-run[Print planned clone without modifying the filesystem]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                check)
                    _arguments '2:repo command:(init clone check configure agent-guidance installer-template)' \
                        '3:path:_files' \
                        '--agent-guidance[Include optional agent guidance files]' \
                        '--agent-ready[Include the agent-ready repo guidance contract]' \
                        '--release[Include the release contract and process document]' \
                        '--format[Output format]:format:(text json)' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                configure)
                    _arguments '2:repo command:(init clone check configure agent-guidance installer-template)' \
                        '3:path:_files' \
                        '--repo[GitHub repository]:repo:' \
                        '--no-protect-default-branch[Skip Base-managed default branch protection]' \
                        '--project[GitHub Project title]:title:' \
                        '--project-owner[GitHub Project owner]:owner:' \
                        '--project-schema[Project metadata schema]:schema:(base-project)' \
                        '--initiative-option[Initiative option to seed]:name:' \
                        '--copy-project-fields-from[Copy missing Project item field values from another Project]:title:' \
                        '--replace-project[Replace a nonstandard existing Project from base-project-template]' \
                        '--no-project[Skip GitHub Project metadata configuration]' \
                        '--release[Seed the generic release contract and process documentation]' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                agent-guidance)
                    _arguments '2:repo command:(init clone check configure agent-guidance installer-template)' \
                        '3:path:_files' \
                        '--repo[GitHub repository for pull request]:repo:' \
                        '--issue[Issue number for pull request]:number:' \
                        '--category[Issue category for pull request dry-run]:category:(bug enhancement documentation ci security)' \
                        '--repo-name[Repository name for generated guidance]:name:' \
                        '--default-branch[Default branch for generated guidance]:branch:' \
                        '--validation-command[Validation command for generated guidance]:command:' \
                        '--pr[Commit generated guidance files and open a draft pull request]' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                installer-template)
                    _arguments '2:repo command:(init clone check configure agent-guidance installer-template)' \
                        '3:path:_files' \
                        '--print[Print the maintained template to stdout instead of writing a file]' \
                        '--stdout[Alias for --print]' \
                        '--repo[GitHub repository for pull request]:repo:' \
                        '--issue[Issue number for pull request]:number:' \
                        '--category[Issue category for pull request dry-run]:category:(bug enhancement documentation ci security)' \
                        '--pr[Commit generated installer template and open a draft pull request]' \
                        '--dry-run[Print planned changes]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '2:repo command:(init clone check configure agent-guidance installer-template)'
                    ;;
            esac
            ;;
        ci)
            case "${words[3]:-}" in
                setup)
                    _arguments '2:ci command:(setup check doctor)' \
                        '--ci[Run setup with CI-safe defaults]' \
                        '--format[Output format]:format:(text json)' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                        '--dry-run[Log without making changes]' \
                        '--notify[Force a setup completion notification]' \
                        '--no-notify[Disable setup completion notification]' \
                        '--recreate-venv[Recreate the project virtual environment]' \
                        '--yes[Apply setup changes that require explicit confirmation]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '3:Base project:->projects'
                    ;;
                check)
                    _arguments '2:ci command:(setup check doctor)' \
                        '--ci[Run checks with CI-safe defaults]' \
                        '--format[Output format]:format:(text json)' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                        '--remote-network[Opt in to bounded project Git origin reachability checks]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '3:Base project:->projects'
                    ;;
                doctor)
                    _arguments '2:ci command:(setup check doctor)' \
                        '--ci[Run diagnostics with CI-safe defaults]' \
                        '--format[Output format]:format:(text json)' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                        '--remote-network[Opt in to bounded project Git origin reachability diagnostics]' \
                        '--no-color[Disable doctor status colors and symbols in text output]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '3:Base project:->projects'
                    ;;
                *)
                    _arguments '2:ci command:(setup check doctor)'
                    ;;
            esac
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        release)
            case "${words[3]:-}" in
                check)
                    _arguments '2:release command:(check plan notes publish)' \
                        '--version[Release version]:version:' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--format[Output format]:format:(text json)' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                plan|notes)
                    _arguments '2:release command:(check plan notes publish)' \
                        '--version[Release version]:version:' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                publish)
                    _arguments '2:release command:(check plan notes publish)' \
                        '--version[Release version]:version:' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--dry-run[Print publish actions without creating tags or releases]' \
                        '--yes[Publish without an interactive confirmation prompt]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                *)
                    _arguments '2:release command:(check plan notes publish)'
                    ;;
            esac
            ;;
        clean)
            _arguments '--older-than[Artifact age]:age:' \
                '--keep-last[Keep newest log files per CLI log directory]:count:' \
                '--dry-run[Log without removing files]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        logs)
            if [[ "${words[3]:-}" == last ]]; then
                _arguments '2:logs command:(last)' \
                    '--command[Filter by command]:command:' \
                    '--lines[Maximum log-tail lines]:count:' \
                    '--format[Output format]:format:(text json)' \
                    '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            else
                _arguments '2:logs command:(last)' \
                    '--command[Filter by command]:command:' \
                    '--limit[Number of entries]:count:' \
                    '--path[Print most recent log path]' \
                    '--tail[Tail and follow most recent log]' \
                    '--open[Open most recent log]' \
                    '--lines[Lines to show before following]:count:' \
                    '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            fi
            ;;
        history)
            _arguments '--project[Filter by Base project]:project:' \
                '--command[Filter by command]:command:' \
                '--status[Filter by status]:status:(ok warn error)' \
                '--limit[Number of records]:count:' \
                '--format[Output format]:format:(text json)' \
                '--report[Print a privacy-conscious Markdown or JSON activity report]' \
                '-v[Enable DEBUG logging]' '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        config)
            _arguments '2:config command:(path show doctor)' \
                '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        doctor)
            case "${words[3]:-}" in
                explain)
                    _arguments '--format[Output format]:format:(text json)' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '3:finding id:'
                    ;;
                *)
                    _arguments '--ci[Run diagnostics with CI-safe defaults]' \
                        '--profile[Include prerequisite profiles]:profile:(dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab)' \
                        '--format[Output format]:format:(text json)' \
                        '--manifest[Use a specific manifest]:path:_files' \
                        '--remote-network[Opt in to bounded project Git origin reachability diagnostics]' \
                        '--no-color[Disable doctor status colors and symbols in text output]' \
                        '-v[Enable DEBUG logging]' \
                        '(-h --help)'{-h,--help}'[Show help text]' \
                        '2:doctor command or project:->doctor_targets'
                    if [[ "$state" == doctor_targets ]]; then
                        _alternative \
                            'commands:doctor command:(explain)' \
                            'projects:Base project:_base_basectl_completion_describe_projects'
                    fi
                    ;;
            esac
            ;;
        gh)
            case "${words[3]:-}" in
                issue)
                    case "${words[4]:-}" in
                        list)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:issue command:(list create start readiness)' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        create)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:issue command:(list create start readiness)' \
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
                        start)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:issue command:(list create start readiness)' \
                                '4:issue number:' \
                                '--category[Issue category]:category:(bug enhancement documentation ci security)' \
                                '--title[Issue title]:title:' \
                                '(-R --repo)'{-R,--repo}'[Repository containing the issue]:repo:' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        readiness)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:issue command:(list create start readiness)' \
                                '4:issue number:' \
                                '--repo[GitHub repository]:repo:' \
                                '--project-owner[GitHub Project owner]:owner:' \
                                '--project-number[GitHub Project number]:number:' \
                                '--format[Output format]:format:(text json)' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        *)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:issue command:(list create start readiness)' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                    esac
                    ;;
                pr)
                    if [[ "${words[4]:-}" == create ]]; then
                        _arguments '2:gh area:(issue pr branch worktree project)' \
                            '3:pr command:(create status checks ready merge)' \
                            '--no-fixes[Do not add an issue-closing line derived from the branch]' \
                            '(-h --help)'{-h,--help}'[Show help text]'
                    else
                        _arguments '2:gh area:(issue pr branch worktree project)' \
                            '3:pr command:(create status checks ready merge)' \
                            '(-h --help)'{-h,--help}'[Show help text]'
                    fi
                    ;;
                branch)
                    if [[ "${words[4]:-}" == stale ]]; then
                        _arguments '2:gh area:(issue pr branch worktree project)' \
                            '3:branch command:(stale prune)' \
                            '--days[Stale threshold in days]:days:' \
                            '--format[Output format]:format:(text json)' \
                            '(-h --help)'{-h,--help}'[Show help text]'
                    elif [[ "${words[4]:-}" == prune ]]; then
                        _arguments '2:gh area:(issue pr branch worktree project)' \
                            '3:branch command:(stale prune)' \
                            '--dry-run[Show planned deletions]' \
                            '--yes[Apply branch pruning]' \
                            '--remote[Prune stale remote tracking refs]' \
                            '(-h --help)'{-h,--help}'[Show help text]'
                    else
                        _arguments '2:gh area:(issue pr branch worktree project)' \
                            '3:branch command:(stale prune)'
                    fi
                    ;;
                worktree)
                    _arguments '2:gh area:(issue pr branch worktree project)' \
                        '3:worktree command:(prune)' \
                        '--dry-run[Show planned removals]' \
                        '--yes[Apply worktree pruning]' \
                        '(-h --help)'{-h,--help}'[Show help text]'
                    ;;
                project)
                    case "${words[4]:-}" in
                        doctor)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:project command:(doctor configure issue)' \
                                '--project[GitHub Project title]:title:' \
                                '--owner[GitHub Project owner]:owner:' \
                                '--schema[Project metadata schema]:schema:(base-project)' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        configure)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:project command:(doctor configure issue)' \
                                '--project[GitHub Project title]:title:' \
                                '--owner[GitHub Project owner]:owner:' \
                                '--schema[Project metadata schema]:schema:(base-project)' \
                                '--config[Project intake config]:path:_files' \
                                '--copy-fields-from[Copy missing field values from another Project]:title:' \
                                '--initiative-option[Initiative option to seed]:name:' \
                                '--repo[GitHub repository]:repo:' \
                                '--replace-project[Replace a nonstandard existing Project from base-project-template]' \
                                '--dry-run[Print planned changes]' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        issue)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:project command:(doctor configure issue)' \
                                '4:issue command:(set-fields)' \
                                '5:issue number:' \
                                '--repo[GitHub repository]:repo:' \
                                '--project[GitHub Project title]:title:' \
                                '--owner[GitHub Project owner]:owner:' \
                                '--config[Project intake config]:path:_files' \
                                '--status[Status option]:status:' \
                                '--priority[Priority option]:priority:' \
                                '--area[Area option]:area:' \
                                '--initiative[Initiative option]:initiative:' \
                                '--size[Size option]:size:' \
                                '--dry-run[Print planned changes]' \
                                '(-h --help)'{-h,--help}'[Show help text]'
                            ;;
                        *)
                            _arguments '2:gh area:(issue pr branch worktree project)' \
                                '3:project command:(doctor configure issue)'
                            ;;
                    esac
                    ;;
                *)
                    _arguments '2:gh area:(issue pr branch worktree project)'
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
                '2:Base project:->projects'
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
                '2:Base project:->projects'
            if [[ "$state" == projects ]]; then
                _base_basectl_completion_describe_projects
            fi
            ;;
        version)
            _arguments '(-h --help)'{-h,--help}'[Show help text]'
            ;;
        help)
            local -a help_words
            local help_current="$CURRENT"

            help_words=("${words[@]}")
            words=("$help_words[1]" "${help_words[@]:2}")
            CURRENT=$((help_current - 1))
            _base_basectl_completion
            words=("${help_words[@]}")
            CURRENT="$help_current"
            ;;
    esac
}

if ! whence -w compdef >/dev/null 2>&1; then
    autoload -Uz compinit
    compinit -i
fi

compdef _base_basectl_completion basectl
