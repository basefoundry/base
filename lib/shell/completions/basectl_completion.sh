# shellcheck shell=bash

#
# Bash completion for basectl.
#

_BASE_BASECTL_COMPLETION_PROJECT_NAMES=""
_BASE_BASECTL_COMPLETION_PROJECT_NAMES_SET=0
_BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT=0

_base_basectl_completion_project_cache_ttl() {
    local ttl="${BASE_COMPLETION_PROJECT_CACHE_TTL:-5}"

    [[ "$ttl" =~ ^[0-9]+$ ]] || ttl=5
    printf '%s\n' "$((10#$ttl))"
}

_base_basectl_completion_now() {
    printf '%s\n' "${SECONDS:-0}"
}

_base_basectl_completion_validate_utf8_hex() {
    local encoded="$1"
    local byte continuation first index=0 length
    local continuation_count continuation_min continuation_max

    length=${#encoded}
    while ((index < length)); do
        byte=$((16#${encoded:index:2}))
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
        first=$((16#${encoded:index:2}))
        ((first >= continuation_min && first <= continuation_max)) || return 1
        ((index += 2))
        for ((continuation = 1; continuation < continuation_count; continuation += 1)); do
            byte=$((16#${encoded:index:2}))
            ((byte >= 0x80 && byte <= 0xbf)) || return 1
            ((index += 2))
        done
    done
}

_base_basectl_completion_decode_hex() {
    local encoded="$1"
    local byte decoded="" index pair

    if (( ${#encoded} % 2 != 0 )) || [[ "$encoded" == *[!0-9a-f]* ]]; then
        return 1
    fi
    _base_basectl_completion_validate_utf8_hex "$encoded" || return 1

    for ((index = 0; index < ${#encoded}; index += 2)); do
        pair="${encoded:index:2}"
        [[ "$pair" != 00 ]] || return 1
        printf -v byte '%b' "\\x$pair"
        decoded+="$byte"
    done
    _BASE_BASECTL_COMPLETION_DECODED_VALUE="$decoded"
}

_base_basectl_completion_project_names_from_protocol() {
    # Completion can load under macOS system Bash 3 before basectl establishes
    # its Bash 4.2+ runtime. Keep this strict reader narrow instead of sourcing
    # the associative-array runtime protocol decoder.
    local payload="$1"
    local count_text="" encoded ended=0 in_record=0 line line_number=0 names=""
    local max_record_count=1000000 next_record=0 phase=0 project_name record_count=0

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
                [[ "$count_text" =~ ^(0|[1-9][0-9]*)$ ]] || return 1
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
                names+="${names:+$'\n'}$project_name"
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
    _BASE_BASECTL_COMPLETION_PROJECT_NAMES_DECODED="$names"
}

_base_basectl_completion_refresh_project_cache() {
    local names="" now ttl project_list
    local wrapper="${BASE_HOME:-}/bin/base-wrapper"

    [[ -x "$wrapper" ]] || {
        _BASE_BASECTL_COMPLETION_PROJECT_NAMES=""
        _BASE_BASECTL_COMPLETION_PROJECT_NAMES_SET=1
        _BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT=0
        return 0
    }

    ttl="$(_base_basectl_completion_project_cache_ttl)"
    now="$(_base_basectl_completion_now)"
    if ((ttl > 0)) &&
        ((_BASE_BASECTL_COMPLETION_PROJECT_NAMES_SET)) &&
        ((_BASE_BASECTL_COMPLETION_PROJECT_NAMES_EXPIRES_AT > now)); then
        return 0
    fi

    project_list="$("$wrapper" --project base base_projects list --format command-protocol 2>/dev/null || true)"
    if _base_basectl_completion_project_names_from_protocol "$project_list"; then
        names="$_BASE_BASECTL_COMPLETION_PROJECT_NAMES_DECODED"
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

_base_basectl_completion_project_candidates() {
    local current="$1"
    local candidate

    _base_basectl_completion_refresh_project_cache || return 0
    COMPREPLY=()
    while IFS= read -r candidate; do
        [[ -n "$candidate" ]] || continue
        [[ "$candidate" == "$current"* ]] || continue
        COMPREPLY+=("$candidate")
    done <<<"$_BASE_BASECTL_COMPLETION_PROJECT_NAMES"
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
    printf '%s\n' "dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab"
}

_base_basectl_completion_project_or_options() {
    local options="$1"
    local current="$2"

    if ((COMP_CWORD == 2)) && [[ "$current" != -* ]]; then
        _base_basectl_completion_project_candidates "$current"
    else
        _base_basectl_completion_compgen "$options" "$current"
    fi
}

_base_basectl_completion_project_profiles_or_options() {
    local current="$1"
    local options="$2"
    local project_position="${3:-2}"
    local previous="${COMP_WORDS[COMP_CWORD - 1]:-}"

    if [[ "$previous" == "--profile" ]]; then
        _base_basectl_completion_compgen "$(_base_basectl_completion_profiles)" "$current"
    elif ((COMP_CWORD == project_position)) && [[ "$current" != -* ]]; then
        _base_basectl_completion_project_candidates "$current"
    else
        _base_basectl_completion_compgen "$options" "$current"
    fi
}

_base_basectl_completion() {
    local command cur
    local commands="activate setup check test export-context devcontainer devenv-report build demo run repo ci release prompt docs clean logs history config trust doctor gh onboard update-profile update projects workspace version help"
    local setup_options="--ci --format --profile --dry-run --manifest --notify --no-notify --recreate-venv --yes -v -h --help"
    local check_options="--ci --profile --format --manifest --remote-network -v -h --help"
    local doctor_options="--ci --profile --format --manifest --remote-network --no-color -v -h --help"

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
                _base_basectl_completion_project_candidates "$cur"
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
        trust)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "status allow revoke" "$cur"
            elif ((COMP_CWORD == 3)) && [[ "$cur" != -* ]]; then
                _base_basectl_completion_project_candidates "$cur"
            else
                case "${COMP_WORDS[2]:-}" in
                    status)
                        _base_basectl_completion_compgen "--workspace --format -v -h --help" "$cur"
                        ;;
                    allow)
                        _base_basectl_completion_compgen "--workspace --manifest-sha256 -v -h --help" "$cur"
                        ;;
                    revoke)
                        _base_basectl_completion_compgen "--workspace -v -h --help" "$cur"
                        ;;
                esac
            fi
            ;;
        workspace)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "status check doctor onboarding agent-brief clone pull init configure" "$cur"
            else
                case "${COMP_WORDS[2]:-}" in
                    status|check|doctor)
                        _base_basectl_completion_compgen "--workspace --manifest --format -v -h --help" "$cur"
                        ;;
                    onboarding|agent-brief)
                        _base_basectl_completion_compgen "--workspace --manifest --format -v -h --help" "$cur"
                        ;;
                    clone)
                        _base_basectl_completion_compgen "--workspace --manifest --include-optional --dry-run -v -h --help" "$cur"
                        ;;
                    pull)
                        _base_basectl_completion_compgen "--source --manifest --dry-run -v -h --help" "$cur"
                        ;;
                    init)
                        _base_basectl_completion_compgen "--owner --path --workspace --manifest --include-optional --dry-run -v -h --help" "$cur"
                        ;;
                    configure)
                        _base_basectl_completion_compgen "--workspace --manifest --dry-run -v -h --help" "$cur"
                        ;;
                esac
            fi
            ;;
        setup)
            _base_basectl_completion_project_profiles_or_options "$cur" "$setup_options"
            ;;
        check)
            _base_basectl_completion_project_profiles_or_options "$cur" "$check_options"
            ;;
        test)
            _base_basectl_completion_project_or_options "--workspace --dry-run -v -h --help" "$cur"
            ;;
        export-context)
            _base_basectl_completion_project_or_options "--workspace --format --output --print --list-files -v -h --help" "$cur"
            ;;
        devcontainer)
            _base_basectl_completion_project_or_options "--workspace --format --write -v -h --help" "$cur"
            ;;
        devenv-report)
            _base_basectl_completion_project_or_options "--workspace --format -v -h --help" "$cur"
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
                    _base_basectl_completion_compgen "--path --repo --issue --category --pr --agent-ready --release --language --description --copyright-holder --private --public --no-configure --no-protect-default-branch --project --project-owner --project-schema --initiative-option --copy-project-fields-from --no-project --dry-run -v -h --help" "$cur"
                    ;;
                clone)
                    _base_basectl_completion_compgen "--owner --path --dry-run -v -h --help" "$cur"
                    ;;
                check)
                    _base_basectl_completion_compgen "--agent-guidance --agent-ready -v -h --help" "$cur"
                    ;;
                configure)
                    _base_basectl_completion_compgen "--repo --no-protect-default-branch --project --project-owner --project-schema --initiative-option --copy-project-fields-from --replace-project --no-project --release --dry-run -v -h --help" "$cur"
                    ;;
                agent-guidance)
                    _base_basectl_completion_compgen "--repo --issue --category --repo-name --default-branch --validation-command --pr --dry-run -v -h --help" "$cur"
                    ;;
                installer-template)
                    _base_basectl_completion_compgen "--print --stdout --repo --issue --category --pr --dry-run -v -h --help" "$cur"
                    ;;
            esac
            ;;
        ci)
            case "${COMP_WORDS[2]:-}" in
                "")
                    _base_basectl_completion_compgen "setup check doctor" "$cur"
                    ;;
                setup)
                    _base_basectl_completion_project_profiles_or_options "$cur" "$setup_options" 3
                    ;;
                check)
                    _base_basectl_completion_project_profiles_or_options "$cur" "$check_options" 3
                    ;;
                doctor)
                    _base_basectl_completion_project_profiles_or_options "$cur" "$doctor_options" 3
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
        prompt)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "list product-self-review" "$cur"
            else
                _base_basectl_completion_compgen "--output -v -h --help" "$cur"
            fi
            ;;
        docs)
            _base_basectl_completion_compgen "--show-url -h --help" "$cur"
            ;;
        clean)
            _base_basectl_completion_compgen "--older-than --keep-last --dry-run -v -h --help" "$cur"
            ;;
        logs)
            if ((COMP_CWORD == 2)) && [[ "$cur" != -* ]]; then
                _base_basectl_completion_compgen "last" "$cur"
            else
                _base_basectl_completion_compgen "--command --limit --path --tail --open --lines --format -v -h --help" "$cur"
            fi
            ;;
        history)
            _base_basectl_completion_compgen "--project --command --status --limit --format --report -v -h --help" "$cur"
            ;;
        config)
            if ((COMP_CWORD == 2)); then
                _base_basectl_completion_compgen "path show doctor" "$cur"
            fi
            ;;
        doctor)
            if [[ "${COMP_WORDS[2]:-}" == explain ]]; then
                _base_basectl_completion_compgen "--format -h --help" "$cur"
            elif ((COMP_CWORD == 2)) && [[ "$cur" != -* ]]; then
                _base_basectl_completion_project_candidates "$cur"
                if [[ "explain" == "$cur"* ]]; then
                    COMPREPLY+=("explain")
                fi
            else
                _base_basectl_completion_project_profiles_or_options "$cur" "$doctor_options"
            fi
            ;;
        gh)
            case "${COMP_WORDS[2]:-}" in
                "")
                    _base_basectl_completion_compgen "issue pr branch worktree project" "$cur"
                    ;;
                issue)
                    if ((COMP_CWORD == 3)); then
                        _base_basectl_completion_compgen "list create start readiness" "$cur"
                    elif [[ "${COMP_WORDS[3]:-}" == "readiness" ]]; then
                        _base_basectl_completion_compgen "--repo --project-owner --project-number -h --help" "$cur"
                    elif [[ "${COMP_WORDS[3]:-}" == "start" ]]; then
                        _base_basectl_completion_compgen "--category --title --repo -R -h --help" "$cur"
                    else
                        _base_basectl_completion_compgen "--category --title --body --repo --assignee --no-assignee --project --project-owner --size --no-project -h --help" "$cur"
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
                project)
                    case "${COMP_WORDS[3]:-}" in
                        "")
                            _base_basectl_completion_compgen "doctor configure issue" "$cur"
                            ;;
                        doctor)
                            _base_basectl_completion_compgen "--project --owner --schema -h --help" "$cur"
                            ;;
                        configure)
                            _base_basectl_completion_compgen "--project --owner --schema --config --copy-fields-from --initiative-option --repo --replace-project --dry-run -h --help" "$cur"
                            ;;
                        issue)
                            if ((COMP_CWORD == 4)); then
                                _base_basectl_completion_compgen "set-fields" "$cur"
                            else
                                _base_basectl_completion_compgen "--repo --project --owner --config --status --priority --area --initiative --size --dry-run -h --help" "$cur"
                            fi
                            ;;
                    esac
                    ;;
            esac
            ;;
        onboard)
            _base_basectl_completion_project_profiles_or_options \
                "$cur" \
                "--profile --dry-run --yes --no-profile -v -h --help"
            ;;
        update-profile)
            _base_basectl_completion_compgen "--defaults --no-defaults --remove --dry-run -v -h --help" "$cur"
            ;;
        update)
            _base_basectl_completion_project_or_options "--dry-run -v -h --help" "$cur"
            ;;
    esac
}

complete -F _base_basectl_completion basectl 2>/dev/null || true
