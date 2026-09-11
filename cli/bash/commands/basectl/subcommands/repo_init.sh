#!/usr/bin/env bash

[[ -n "${_base_repo_init_sourced:-}" ]] && return 0
_base_repo_init_sourced=1
readonly _base_repo_init_sourced

base_repo_init_reset() {
    agent_default_branch="main"
    agent_ready=0
    configure=1
    baseline_change_status=0
    finish_pr_done=0
    category=""
    create_pr=0
    default_branch=""
    description=""
    dry_run=0
    github_repo=""
    github_visibility="private"
    github_visibility_explicit=0
    issue=""
    license_id="Apache-2.0"
    name=""
    path=""
    project_owner=""
    project_schema="base-project"
    project_title=""
    copy_project_fields_from=""
    protect_default_branch=1
    pr_branch=""
    pr_category=""
    pr_rerun_command=""
    requested_visibility=""
    issue_category=""
    root=""
    configure_project=1
    configure_release=0
    initiative_options=()
    language_fields=()
    language_options=()
    language_option=""
    language_field=""
    language=""
    normalized_language=""
    language_seen=""
    help_requested=0
}

base_repo_init_parse_args() {
    local -a parser_args=() positionals=() language_values=() initiative_option_values=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "path|value|--path"
        "repo|value|--repo"
        "issue|value|--issue"
        "category|value|--category"
        "pr|flag|--pr"
        "agent_ready|flag|--agent-ready"
        "release|flag|--release"
        "language_values|repeatable|--language"
        "description|value|--description"
        "license|value|--license"
        "private|flag|--private"
        "public|flag|--public"
        "no_configure|flag|--no-configure"
        "no_protect_default_branch|flag|--no-protect-default-branch"
        "project|value|--project"
        "project_owner|value|--project-owner"
        "project_schema|value|--project-schema"
        "initiative_option_values|repeatable|--initiative-option"
        "copy_project_fields_from|value|--copy-project-fields-from"
        "no_project|flag|--no-project"
        "dry_run|flag|--dry-run"
        "verbose|flag|-v"
    )
    local -A parsed_options=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_init_usage
                help_requested=1
                return 0
                ;;
            --path)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--path' requires an argument."
                    return $?
                }
                parser_args+=("--path=$2")
                shift 2
                ;;
            --path=*)
                parser_args+=("$1")
                shift
                ;;
            --repo)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--repo' requires an argument."
                    return $?
                }
                parser_args+=("--repo=$2")
                shift 2
                ;;
            --repo=*)
                parser_args+=("$1")
                shift
                ;;
            --issue)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--issue' requires a positive integer argument."
                    return $?
                }
                parser_args+=("--issue=$2")
                shift 2
                ;;
            --issue=*)
                [[ -n "${1#--issue=}" ]] || {
                    base_repo_init_usage_error "Option '--issue' requires a positive integer argument."
                    return $?
                }
                parser_args+=("$1")
                shift
                ;;
            --category)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--category' requires an argument."
                    return $?
                }
                parser_args+=("--category=$2")
                shift 2
                ;;
            --category=*)
                [[ -n "${1#--category=}" ]] || {
                    base_repo_init_usage_error "Option '--category' requires an argument."
                    return $?
                }
                parser_args+=("$1")
                shift
                ;;
            --pr)
                parser_args+=("$1")
                shift
                ;;
            --agent-ready)
                parser_args+=("$1")
                shift
                ;;
            --release)
                parser_args+=("$1")
                shift
                ;;
            --language)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--language' requires a comma-separated language list."
                    return $?
                }
                parser_args+=("--language=$2")
                shift 2
                ;;
            --language=*)
                if [[ -z "${1#--language=}" ]]; then
                    base_repo_init_usage_error "Option '--language' requires a comma-separated language list."
                    return $?
                fi
                parser_args+=("$1")
                shift
                ;;
            --description)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--description' requires an argument."
                    return $?
                }
                parser_args+=("--description=$2")
                shift 2
                ;;
            --license)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--license' requires an SPDX identifier."
                    return $?
                }
                parser_args+=("--license=$2")
                shift 2
                ;;
            --license=*)
                [[ -n "${1#--license=}" ]] || {
                    base_repo_init_usage_error "Option '--license' requires an SPDX identifier."
                    return $?
                }
                parser_args+=("$1")
                shift
                ;;
            --private|--public)
                parser_args+=("$1")
                shift
                ;;
            --no-configure)
                parser_args+=("$1")
                shift
                ;;
            --no-protect-default-branch)
                parser_args+=("$1")
                shift
                ;;
            --project)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--project' requires an argument."
                    return $?
                }
                parser_args+=("--project=$2")
                shift 2
                ;;
            --project=*)
                parser_args+=("$1")
                shift
                ;;
            --project-owner)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--project-owner' requires an argument."
                    return $?
                }
                parser_args+=("--project-owner=$2")
                shift 2
                ;;
            --project-owner=*)
                parser_args+=("$1")
                shift
                ;;
            --project-schema)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--project-schema' requires an argument."
                    return $?
                }
                parser_args+=("--project-schema=$2")
                shift 2
                ;;
            --project-schema=*)
                parser_args+=("$1")
                shift
                ;;
            --initiative-option)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--initiative-option' requires an argument."
                    return $?
                }
                parser_args+=("--initiative-option=$2")
                shift 2
                ;;
            --initiative-option=*)
                parser_args+=("$1")
                shift
                ;;
            --copy-project-fields-from)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--copy-project-fields-from' requires an argument."
                    return $?
                }
                parser_args+=("--copy-project-fields-from=$2")
                shift 2
                ;;
            --copy-project-fields-from=*)
                parser_args+=("$1")
                shift
                ;;
            --no-project)
                parser_args+=("$1")
                shift
                ;;
            --dry-run)
                parser_args+=("$1")
                shift
                ;;
            -v)
                parser_args+=("$1")
                base_std_set_log_level DEBUG
                export BASE_BASH_LIBS_LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_init_usage_error "Unknown repo init option '$1'."
                return $?
                ;;
            *)
                parser_args+=("$1")
                shift
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_repo_init_usage_error "Could not parse repo init arguments."
        return $?
    fi
    if ((${#positionals[@]} > 1)); then
        base_repo_init_usage_error "The 'repo init' command accepts exactly one repository name."
        return $?
    fi

    path="${parsed_options[path]:-}"
    github_repo="${parsed_options[repo]:-}"
    issue="${parsed_options[issue]:-}"
    category="${parsed_options[category]:-}"
    create_pr="${parsed_options[pr]:-0}"
    agent_ready="${parsed_options[agent_ready]:-0}"
    configure_release="${parsed_options[release]:-0}"
    description="${parsed_options[description]:-}"
    license_id="${parsed_options[license]:-Apache-2.0}"
    configure=$((1 - ${parsed_options[no_configure]:-0}))
    protect_default_branch=$((1 - ${parsed_options[no_protect_default_branch]:-0}))
    project_title="${parsed_options[project]:-}"
    project_owner="${parsed_options[project_owner]:-}"
    project_schema="${parsed_options[project_schema]:-base-project}"
    copy_project_fields_from="${parsed_options[copy_project_fields_from]:-}"
    configure_project=$((1 - ${parsed_options[no_project]:-0}))
    dry_run="${parsed_options[dry_run]:-0}"
    requested_visibility=""
    if [[ "${parsed_options[private]:-0}" == "1" ]]; then
        requested_visibility=private
    fi
    if [[ "${parsed_options[public]:-0}" == "1" ]]; then
        [[ -z "$requested_visibility" ]] || {
            base_repo_init_usage_error "Options '--private' and '--public' cannot be used together."
            return $?
        }
        requested_visibility=public
    fi
    if [[ -n "$requested_visibility" ]]; then
        github_visibility="$requested_visibility"
        github_visibility_explicit=1
    fi
    initiative_options=("${initiative_option_values[@]}")
    language_options=()
    for language_option in "${language_values[@]}"; do
        language_option="${language_option//[[:space:]]/}"
        if [[ -z "$language_option" || "$language_option" == ,* || "$language_option" == *, || "$language_option" == *,,* ]]; then
            base_repo_init_usage_error "Option '--language' must not contain empty entries."
            return $?
        fi
        base_str_split language_fields "$language_option" ","
        for language_field in "${language_fields[@]}"; do
            normalized_language="$(base_repo_normalize_language "$language_field" || true)"
            if [[ -z "$normalized_language" ]]; then
                base_repo_init_usage_error "Unsupported language '$language_field'. Expected one of: $(base_repo_supported_languages_display)."
                return $?
            fi
            language_seen=0
            for language in "${language_options[@]}"; do
                if [[ "$language" == "$normalized_language" ]]; then
                    language_seen=1
                    break
                fi
            done
            ((language_seen)) || language_options+=("$normalized_language")
        done
    done
    if ((${#positionals[@]} == 1)); then
        name="${positionals[0]}"
    fi
}

base_repo_init_validate() {
    [[ -n "$name" ]] || {
        base_repo_init_usage_error "Repository name is required."
        return $?
    }
    base_repo_validate_name "$name" || return 2
    if ! base_repo_license_is_supported "$license_id"; then
        base_repo_init_usage_error "Unsupported repository license '$license_id'. Expected: $(base_repo_license_display)"
        return 2
    fi
    if [[ -z "$path" ]]; then
        path="$(base_repo_default_target_path "$name")" || return $?
        [[ -n "$path" ]] || {
            base_std_log_error "Unable to resolve a non-empty default repository target for '$name'."
            return 2
        }
    fi
    [[ -n "$description" ]] || description="$(base_repo_default_description "$name")"
    root="$(base_repo_target_path "$path")" || return $?
    [[ -n "$root" ]] || {
        base_std_log_error "Unable to resolve a non-empty repository target for '$name'."
        return 2
    }
    if [[ -n "$issue" ]] && ! base_github_issue_number_is_valid "$issue"; then
        base_repo_init_usage_error "Option '--issue' must be a positive integer."
        return $?
    fi
    if [[ -n "$category" ]] && ! base_github_branch_category_is_valid "$category"; then
        base_repo_init_usage_error "Option '--category' must be one of: bug, enhancement, documentation, ci, security."
        return $?
    fi
}

base_repo_init_plan_pr() {
    if ((create_pr)); then
        [[ -n "$issue" ]] || {
            base_repo_init_usage_error "Option '--pr' requires --issue <positive integer>."
            return $?
        }
        if [[ -z "$github_repo" ]]; then
            github_repo="$(base_repo_infer_github_repo "$root" || true)"
        fi
        [[ -n "$github_repo" ]] || {
            base_repo_init_usage_error "Option '--pr' requires --repo <owner/name> or an inferable GitHub origin remote."
            return $?
        }
        if ((github_visibility_explicit)); then
            base_repo_init_usage_error "Options '--private' and '--public' cannot be used with '--pr'."
            return $?
        fi

        if [[ "$dry_run" == "1" ]]; then
            [[ -n "$category" ]] || {
                base_repo_init_usage_error "Options '--pr --dry-run' require --category <name>."
                return $?
            }
            pr_category="$category"
        else
            base_repo_require_pr_worktree "$root" || return 1
            issue_category="$(base_repo_pr_issue_category "$github_repo" "$issue")" || return 1
            if [[ -n "$category" && "$category" != "$issue_category" ]]; then
                base_repo_init_usage_error "Option '--category $category' does not match issue #$issue category '$issue_category'."
                return $?
            fi
            pr_category="$issue_category"
        fi
        pr_branch="$(base_repo_pr_branch_name "$pr_category" "$issue" "repo-baseline" "$name")" || {
            base_std_log_error "Unable to generate the canonical issue branch for repo init --pr."
            return 1
        }
        if [[ "$dry_run" == "1" ]]; then
            default_branch="<default branch>"
        else
            default_branch="$(base_repo_default_branch_for_pr "$github_repo")" || return 1
        fi
        pr_rerun_command="$(
            base_repo_init_pr_rerun_command \
                "$name" \
                "$root" \
                "$github_repo" \
                "$configure" \
                "$protect_default_branch" \
                "$configure_project" \
                "$project_title" \
                "$project_owner" \
                "$project_schema" \
                "$copy_project_fields_from" \
                "$agent_ready" \
                "$(base_repo_languages_csv "${language_options[@]}")" \
                "$issue" \
                "$pr_category" \
                "$configure_release" \
                "${initiative_options[@]}"
        )"
        base_repo_prepare_pr_branch "$dry_run" "$root" "$pr_branch" "$default_branch" || return 1
    fi
}

base_repo_init_write_baseline() {
    if ((configure_release)) && [[ -z "$github_repo" ]]; then
        github_repo="$(base_repo_infer_github_repo "$root" || true)"
    fi
    if ((configure_release)) && [[ -z "$github_repo" ]]; then
        base_repo_init_usage_error "Option '--release' requires --repo <owner/name> or an existing GitHub origin remote."
        return $?
    fi

    base_repo_write_baseline "$dry_run" "$name" "$description" "$root" "$license_id" "${language_options[@]}" || return 1
    if ((configure_release)); then
        base_repo_configure_release "$dry_run" "$github_repo" "$root" || return 1
    fi
    if ((agent_ready)); then
        if [[ -n "$default_branch" && "$default_branch" != "<default branch>" ]]; then
            agent_default_branch="$default_branch"
        elif [[ "$dry_run" != "1" ]]; then
            agent_default_branch="$(base_repo_detect_default_branch "$root" 2>/dev/null || true)"
            [[ -n "$agent_default_branch" ]] || agent_default_branch="main"
        fi
        base_repo_write_init_agent_guidance "$dry_run" "$name" "$agent_default_branch" "./tests/validate.sh" "$root" || return 1
    fi
}

base_repo_init_finish_pr() {
    if ((create_pr)); then
        if [[ "$dry_run" == "1" ]]; then
            base_repo_finish_pr_baseline "$dry_run" "$name" "$root" "$github_repo" "$pr_branch" "$default_branch" "$pr_rerun_command" "$agent_ready" "$issue" "$configure_release"
            local finish_status=$?
            finish_pr_done=1
            return "$finish_status"
        fi
        if base_repo_pr_baseline_has_changes "$root" "$agent_ready" "$configure_release"; then
            base_repo_finish_pr_baseline "$dry_run" "$name" "$root" "$github_repo" "$pr_branch" "$default_branch" "$pr_rerun_command" "$agent_ready" "$issue" "$configure_release"
            local finish_status=$?
            finish_pr_done=1
            return "$finish_status"
        else
            baseline_change_status=$?
            case "$baseline_change_status" in
                1)
                    if ((configure)); then
                        base_std_log_info "No repository baseline changes to commit; continuing with GitHub repository configuration."
                    else
                        base_std_log_info "No repository baseline changes to commit; GitHub repository configuration skipped by --no-configure."
                    fi
                    ;;
                *)
                    return 1
                    ;;
            esac
        fi
    fi
}

base_repo_init_configure_github() {
    if ((configure)); then
        if [[ -z "$github_repo" ]]; then
            github_repo="$(base_repo_infer_github_repo "$root" || true)"
        fi
        if [[ -n "$github_repo" ]]; then
            base_repo_load_github_settings || return 1
            base_repo_ensure_github_repo "$dry_run" "$github_repo" "$description" "$github_visibility" || return 1
            if [[ "${BASE_REPO_GITHUB_REPO_CREATED:-0}" == "1" ]]; then
                base_repo_bootstrap_github_checkout "$dry_run" "$github_repo" "$root" || return 1
            fi
            base_repo_configure_github "$dry_run" "$github_repo" "$protect_default_branch" "$root" || return 1
            if ((configure_project)); then
                [[ -n "$project_title" ]] || project_title="$(base_repo_default_project_title "$github_repo")"
                [[ -n "$project_owner" ]] || project_owner="$(base_repo_project_owner_from_repo "$github_repo")"
                base_repo_configure_project_metadata \
                    "$dry_run" \
                    "$github_repo" \
                    "$project_title" \
                    "$project_owner" \
                    "$project_schema" \
                    "$(base_repo_project_config_path "$root")" \
                    "$copy_project_fields_from" \
                    0 \
                    "${initiative_options[@]}" || return 1
            fi
        else
            base_repo_print_init_github_skip_notice "$dry_run" "$name" "$root"
        fi
    fi
}

base_repo_init() {
    local agent_default_branch="main"
    local agent_ready=0
    local configure=1
    local baseline_change_status=0
    local finish_pr_done=0
    local category=""
    local create_pr=0
    local default_branch=""
    local description=""
    local dry_run=0
    local github_repo=""
    local github_visibility="private"
    local github_visibility_explicit=0
    local issue=""
    local license_id="Apache-2.0"
    local name=""
    local path=""
    local project_owner=""
    local project_schema="base-project"
    local project_title=""
    local copy_project_fields_from=""
    local protect_default_branch=1
    local pr_branch=""
    local pr_category=""
    local pr_rerun_command=""
    local requested_visibility=""
    local issue_category=""
    local root=""
    local configure_project=1
    local configure_release=0
    local initiative_options=()
    local language_fields=()
    local language_options=()
    local language_option=""
    local language_field=""
    local language=""
    local normalized_language=""
    local language_seen=""
    local help_requested=0

    base_repo_init_reset
    base_repo_init_parse_args "$@" || return $?
    ((help_requested)) && return 0
    base_repo_init_validate || return $?
    base_repo_init_plan_pr || return $?
    base_repo_init_write_baseline || return $?
    base_repo_init_finish_pr || return $?
    ((finish_pr_done)) && return 0
    base_repo_init_configure_github
}
