#!/usr/bin/env bash

[[ -n "${_base_gh_issue_sourced:-}" ]] && return 0
_base_gh_issue_sourced=1
readonly _base_gh_issue_sourced

base_gh_issue_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue list [gh options...]
  basectl gh issue create [--category <bug|enhancement|documentation|ci|security>] --title <title> [--body <body>] [--repo <owner/name>] [--assignee <login>|--no-assignee] [--size <T|S|M|L>] [--allow-cross-repo] [project options...]
  basectl gh issue readiness <number> [--repo <owner/name>] [--project-owner <login> --project-number <number>] [--format <text|json>]
  basectl gh issue start <number> [--category <bug|enhancement|documentation|ci|security>] [--title <title>] [--repo <owner/name>|-R <owner/name>]

Purpose:
  List, create, validate, and start GitHub issues using Base's issue-first workflow.

Branch naming:
  <category>/<issue>-<YYYYMMDD>-<slug>

Issue create project options:
  --repo <owner/name>           Repository to create the issue in. Defaults to the origin remote.
  --category <category>         Issue label category. Defaults to enhancement.
  --assignee <login>            Assign the issue to a GitHub login.
  --no-assignee                 Do not assign the issue, even when repo config has a default.
  --project <title>             Project to update. Defaults to the repository name.
  --project-owner <login>       Project owner. Defaults to the repository owner.
  --size <T|S|M|L>              Project Size value. Defaults to .github/base-project.yml or S.
  --no-project                  Skip Project metadata updates.
  --allow-cross-repo            Allow an intentional update to a Project not linked to the issue repository.

Issue readiness options:
  --repo <owner/name>           Repository containing the issue. Defaults to the origin remote.
  --project-owner <login>       Project owner for Project field validation.
  --project-number <number>     Project number for Project field validation.
  --format <text|json>          Select human text or stable inspection JSON. Defaults to text.

Issue start options:
  --repo, -R <owner/name>       Repository containing the issue. Selection order is
                                the explicit option, GH_REPO, then the origin remote.
  --category <category>         Must match the issue's single category label.
  --title <title>               Override the issue title used to generate the slug.

Default category: enhancement.
Default assignee: none unless project.issue_defaults.assignee is set in .github/base-project.yml.
Categories: bug, enhancement, documentation, ci, security.
EOF
}

base_gh_issue_start_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue start <number> [options]

Purpose:
  Print the canonical issue-backed branch and worktree commands after verifying
  the issue's standard category label.

Options:
  --repo, -R <owner/name>  Repository containing the issue. Selection order is
                           the explicit option, GH_REPO, then the origin remote.
  --category <category>    Must match the issue's single category label.
  --title <title>          Override the issue title used to generate the slug.
  -h, --help               Show this help text.
EOF
}

base_gh_issue_list_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue list [gh options...]

Purpose:
  List GitHub issues through the GitHub CLI.

Options:
  -h, --help  Show this help text.

Additional options are passed through to `gh issue list`.
EOF
}

base_gh_issue_create_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue create --title <title> [options]

Purpose:
  Create an issue with Base category, assignment, and Project conventions.

Options:
  --category <category>    Issue category. Defaults to enhancement.
  --title <title>          Required issue title.
  --body <body>            Issue body.
  --repo <owner/name>      Target repository. Defaults to origin.
  --assignee <login>       Assign the issue to a GitHub login.
  --no-assignee            Ignore any repository assignee default.
  --project <title>        GitHub Project title.
  --project-owner <login>  GitHub Project owner.
  --size <T|S|M|L>         GitHub Project Size value.
  --no-project             Skip GitHub Project metadata updates.
  --allow-cross-repo       Allow an intentional update to a Project not linked to the issue repository.
  -h, --help               Show this help text.

Categories: bug, enhancement, documentation, ci, security.
EOF
}

base_gh_issue_readiness_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue readiness <number> [options]

Purpose:
  Check required issue sections and optional Base Project metadata before work.

Options:
  --repo <owner/name>        Repository containing the issue.
  --project-owner <login>    Project owner for field validation.
  --project-number <number>  Project number for field validation.
  --format <text|json>       Select human text or stable inspection JSON.
  -h, --help                 Show this help text.
EOF
}

base_gh_issue_main() {
    local command="${1:-}"
    shift || true

    case "$command" in
        list)
            if base_gh_args_request_help "$@"; then
                base_gh_issue_list_usage
                return 0
            fi
            base_cli_gh_run issue list "$@"
            ;;
        create)
            if base_gh_args_request_help "$@"; then
                base_gh_issue_create_usage
                return 0
            fi
            base_gh_issue_create "$@"
            ;;
        readiness)
            base_gh_load_issue_readiness || return 1
            base_gh_issue_readiness "$@"
            ;;
        start)
            if base_gh_args_request_help "$@"; then
                base_gh_issue_start_usage
                return 0
            fi
            base_gh_issue_start "$@"
            ;;
        -h|--help|help|"")
            base_gh_issue_usage
            ;;
        *)
            base_gh_usage_error base_gh_issue_usage "Unknown gh issue command '$command'."
            return $?
            ;;
    esac
}

base_gh_issue_create() {
    local assignee=""
    local assignee_explicit=0
    local body=""
    local category=""
    local configure_project=1
    local config_path=""
    local github_repo=""
    local allow_cross_repo=0
    local issue_args=()
    local issue_number=""
    local issue_output=""
    local no_assignee=0
    local project_owner=""
    local project_size=""
    local project_title=""
    local title=""
    local -a parser_args=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "category|value|--category"
        "repo|value|--repo"
        "title|value|--title"
        "assignee|value|--assignee"
        "no_assignee|flag|--no-assignee"
        "body|value|--body"
        "project|value|--project"
        "project_owner|value|--project-owner"
        "size|value|--size"
        "no_project|flag|--no-project"
        "allow_cross_repo|flag|--allow-cross-repo"
    )
    local -a positionals=()
    local -A parsed_options=()

    while (($#)); do
        case "$1" in
            --category|--repo|--title|--assignee|--body|--project|--project-owner|--size)
                [[ $# -ge 2 ]] || {
                    base_gh_usage_error base_gh_issue_usage "Option '$1' requires an argument."
                    return $?
                }
                parser_args+=("$1" "$2")
                shift 2
                ;;
            --no-assignee|--no-project|--allow-cross-repo)
                parser_args+=("$1")
                shift
                ;;
            -h|--help)
                base_gh_issue_create_usage
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_issue_usage "Unknown option '$1'."
                return $?
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_gh_usage_error base_gh_issue_usage "Could not parse issue create arguments."
        return $?
    fi
    if ((${#positionals[@]} > 0)); then
        base_gh_usage_error base_gh_issue_usage "Unknown option '${positionals[0]}'."
        return $?
    fi
    if [[ "${parsed_options[help]:-0}" == "1" ]]; then
        base_gh_issue_create_usage
        return 0
    fi
    category="${parsed_options[category]:-}"
    github_repo="${parsed_options[repo]:-}"
    title="${parsed_options[title]:-}"
    assignee="${parsed_options[assignee]:-}"
    assignee_explicit="${parsed_options[assignee]+1}"
    no_assignee="${parsed_options[no_assignee]:-0}"
    body="${parsed_options[body]:-}"
    project_title="${parsed_options[project]:-}"
    project_owner="${parsed_options[project_owner]:-}"
    project_size="${parsed_options[size]:-}"
    configure_project=$((1 - ${parsed_options[no_project]:-0}))
    allow_cross_repo="${parsed_options[allow_cross_repo]:-0}"

    [[ -n "$title" ]] || {
        base_gh_usage_error base_gh_issue_usage "Missing required --title."
        return $?
    }
    if [[ -z "$category" ]]; then
        category="enhancement"
        printf 'Using default --category: enhancement\n'
    fi
    base_gh_validate_category "$category" || {
        base_gh_issue_usage >&2
        return 2
    }
    if [[ -n "$project_size" ]]; then
        base_gh_validate_project_size "$project_size" || {
            base_gh_issue_usage >&2
            return 2
        }
    fi
    if ((assignee_explicit)) && ((no_assignee)); then
        base_gh_usage_error base_gh_issue_usage "Options '--assignee' and '--no-assignee' cannot be used together."
        return $?
    fi
    if ((assignee_explicit)) && [[ -z "$assignee" ]]; then
        base_gh_usage_error base_gh_issue_usage "Option '--assignee' requires an argument."
        return $?
    fi

    [[ -n "$github_repo" ]] || github_repo="$(base_gh_infer_github_repo || true)"
    config_path="$(base_gh_project_config_path || true)"
    if ((assignee_explicit)); then
        :
    elif ((no_assignee)); then
        assignee=""
    elif [[ -n "$config_path" ]]; then
        assignee="$(base_gh_issue_default_assignee_from_config "$config_path" || true)"
    fi

    issue_args=(issue create --title "$title")
    if [[ -n "$body" ]]; then
        issue_args+=(--body "$body")
    fi
    issue_args+=(--label "$category")
    if [[ -n "$assignee" ]]; then
        issue_args+=(--assignee "$assignee")
    fi
    if [[ -n "$github_repo" ]]; then
        issue_args+=(--repo "$github_repo")
    fi
    issue_output="$(base_cli_gh_run "${issue_args[@]}")" || return $?
    printf '%s\n' "$issue_output"

    if ((configure_project)) && [[ -n "$github_repo" ]]; then
        base_gh_auth_environment_warning github.com || true
        issue_number="$(base_gh_issue_number_from_output "$issue_output")" || {
            base_gh_error "Unable to determine created issue number from gh output."
            return 1
        }
        [[ -n "$project_title" ]] || project_title="$(base_gh_default_project_title "$github_repo")"
        [[ -n "$project_owner" ]] || project_owner="$(base_gh_project_owner_from_repo "$github_repo")"
        if [[ -n "$config_path" ]]; then
            local field_args=(
                "$issue_number"
                --project "$project_title"
                --owner "$project_owner"
                --repo "$github_repo"
                --config "$config_path"
            )
            if [[ -n "$project_size" ]]; then
                field_args+=(--size "$project_size")
            fi
            if ((allow_cross_repo)); then
                field_args+=(--allow-cross-repo)
            fi
            base_gh_apply_project_issue_fields "$project_title" "$config_path" "$project_size" "$issue_number" "${field_args[@]}" || return $?
        else
            [[ -n "$project_size" ]] || project_size="S"
            local field_args=(
                "$issue_number"
                --project "$project_title"
                --owner "$project_owner"
                --repo "$github_repo"
                --status Backlog
                --priority P2
                --size "$project_size"
            )
            if ((allow_cross_repo)); then
                field_args+=(--allow-cross-repo)
            fi
            base_gh_apply_project_issue_fields "$project_title" "" "$project_size" "$issue_number" "${field_args[@]}" || return $?
        fi
    fi
}

base_gh_issue_start() {
    local issue="${1:-}" category="" issue_category="" github_repo="" title="" slug branch default_branch worktree_path
    local option_value
    local repo_args=()
    local parser_args=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "category|value|--category"
        "title|value|--title"
        "repo|value|--repo"
    )
    local -a positionals=()
    local -A parsed_options=()
    local status

    [[ -n "$issue" ]] || {
        base_gh_usage_error base_gh_issue_usage "Missing issue number."
        return $?
    }
    shift

    while (($#)); do
        case "$1" in
            --category)
                if (($# > 1)); then
                    parser_args+=("--category=$2")
                    shift 2
                else
                    # Preserve the legacy empty-value behavior. The issue's
                    # category remains authoritative when no value is given.
                    parser_args+=("--category=")
                    shift
                fi
                continue
                ;;
            --category=*)
                base_gh_usage_error base_gh_issue_usage "Unknown option '$1'."
                return $?
                ;;
            --title)
                if (($# > 1)); then
                    parser_args+=("--title=$2")
                    shift 2
                else
                    # Preserve the legacy empty-value behavior so a missing
                    # title still falls back to the issue title.
                    parser_args+=("--title=")
                    shift
                fi
                continue
                ;;
            --title=*)
                base_gh_usage_error base_gh_issue_usage "Unknown option '$1'."
                return $?
                ;;
            --repo|-R)
                if (($# < 2)) || [[ -z "$2" || "$2" == -* ]]; then
                    base_gh_usage_error base_gh_issue_usage "Option '$1' requires a repository argument."
                    return $?
                fi
                parser_args+=("--repo=$2")
                shift 2
                continue
                ;;
            --repo=*|-R=*)
                option_value="${1#*=}"
                if [[ -z "$option_value" ]]; then
                    base_gh_usage_error base_gh_issue_usage "Option '${1%%=*}' requires a repository argument."
                    return $?
                fi
                parser_args+=("--repo=$option_value")
                shift
                continue
                ;;
            -h|--help)
                base_gh_issue_start_usage
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_issue_usage "Unknown option '$1'."
                return $?
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_gh_usage_error base_gh_issue_usage "Could not parse issue start arguments."
        return $?
    fi
    if ((${#positionals[@]} > 0)); then
        base_gh_usage_error base_gh_issue_usage "Unknown option '${positionals[0]}'."
        return $?
    fi

    category="${parsed_options[category]:-}"
    title="${parsed_options[title]:-}"
    github_repo="${parsed_options[repo]:-}"
    if [[ -n "$github_repo" ]]; then
        repo_args=(--repo "$github_repo")
    fi

    base_github_issue_number_is_valid "$issue" || {
        base_gh_usage_error base_gh_issue_usage "Issue number must be a positive integer."
        return $?
    }

    base_gh_require_git_repo || return 1
    if [[ -n "$category" ]]; then
        base_gh_validate_category "$category" || {
            base_gh_issue_usage >&2
            return 2
        }
    fi
    base_gh_require_command gh || return 1
    github_repo="$(base_gh_pr_target_repo "${repo_args[@]}")"
    status=$?
    if ((status != 0)); then
        if ((status == 2)); then
            base_gh_error "Option '--repo' or '-R' requires a repository argument."
            return 2
        fi
        base_gh_error "Unable to determine the target GitHub repository from --repo/-R, GH_REPO, or the origin remote."
        return 1
    fi
    issue_category="$(base_gh_issue_category "$github_repo" "$issue")" || return $?
    if [[ -n "$category" && "$category" != "$issue_category" ]]; then
        base_gh_error "Option '--category $category' does not match issue #$issue category '$issue_category'."
        return 2
    fi
    category="$issue_category"
    base_gh_validate_category "$category" || {
        base_gh_issue_usage >&2
        return 2
    }
    if [[ -z "$title" ]]; then
        title="$(base_gh_issue_title "$issue" "$github_repo")" || return 1
    fi

    slug="$(base_gh_slug "$title")"
    branch="$(base_github_branch_name "$category" "$issue" "$slug")" || {
        base_gh_error "Unable to generate the canonical branch name for issue #$issue."
        return 1
    }
    default_branch="$(base_gh_default_branch)"
    worktree_path="$(base_gh_issue_worktree_path "$issue" "$slug")" || return 1

    printf '%s\n' "$branch"
    printf '\n'
    printf 'To create a worktree:\n'
    printf '  git worktree add -b %s %s origin/%s\n' "$branch" "$worktree_path" "$default_branch"
}
