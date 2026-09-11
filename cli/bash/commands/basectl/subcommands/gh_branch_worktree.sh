#!/usr/bin/env bash

[[ -n "${_base_gh_branch_worktree_sourced:-}" ]] && return 0
_base_gh_branch_worktree_sourced=1
readonly _base_gh_branch_worktree_sourced

declare -gA BASE_GH_BRANCH_PR_STATE_CACHE=()
declare -g BASE_GH_BRANCH_PR_STATE_CACHE_LOADED=0
declare -g BASE_GH_BRANCH_PR_STATE_CACHE_LOAD_STATUS=0

base_gh_branch_stale() {
    local days=30 now ref name timestamp age
    local output_format="text" requested_format
    local refs_output status scope last_commit_json name_json data_json branches_joined envelope_status="ok"
    local branches_json=()
    local -a parser_args=() positionals=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "days|value|--days"
        "format|value|--format"
    )
    local -A parsed_options=()

    base_inspection_find_output_format output_format "$@"

    while (($#)); do
        case "$1" in
            --days)
                if (($# >= 2)); then
                    parser_args+=("--days=$2")
                    shift 2
                else
                    parser_args+=("--days=")
                    shift
                fi
                continue
                ;;
            --format)
                [[ -n "${2:-}" ]] || {
                    base_gh_branch_stale_format_error "$output_format" "Option '--format' requires an argument."
                    return $?
                }
                requested_format="${2:-}"
                case "$requested_format" in
                    text|json)
                        ;;
                    *)
                        base_gh_branch_stale_format_error "$output_format" "Unsupported branch stale format '$requested_format'. Expected text or json."
                        return $?
                        ;;
                esac
                parser_args+=("--format=$requested_format")
                if (($# >= 2)); then
                    shift 2
                else
                    shift
                fi
                continue
                ;;
            -h|--help)
                base_gh_branch_leaf_usage stale
                return 0
                ;;
            *)
                base_gh_branch_stale_format_error "$output_format" "Unknown option '$1'."
                return $?
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_gh_branch_stale_format_error "$output_format" "Could not parse branch stale arguments."
        return $?
    fi
    if ((${#positionals[@]} > 0)); then
        base_gh_branch_stale_format_error "$output_format" "Unknown option '${positionals[0]}'."
        return $?
    fi

    if [[ -n "${parsed_options[days]+set}" ]]; then
        days="${parsed_options[days]}"
    fi
    if [[ -n "${parsed_options[format]+set}" ]]; then
        output_format="${parsed_options[format]}"
    fi

    [[ "$days" =~ ^[0-9]+$ ]] || {
        base_gh_branch_stale_format_error "$output_format" "--days must be a positive integer."
        return $?
    }
    days="$(base_inspection_json_decimal "$days")"
    base_inspection_json_decimal_fits_bash_integer "$days" || {
        base_gh_branch_stale_format_error "$output_format" "--days exceeds the supported integer range."
        return $?
    }
    if ! base_gh_require_git_repo; then
        if [[ "$output_format" == "json" ]]; then
            base_inspection_json_emit_error \
                "gh branch stale" environment_error \
                "Current directory is not inside a Git worktree." \
                '{"operation":"git_repository_check"}'
        fi
        return 1
    fi

    refs_output="$(git for-each-ref --format='%(committerdate:unix) %(refname)' refs/heads refs/remotes/origin)"
    status=$?
    if ((status != 0)); then
        if [[ "$output_format" == "json" ]]; then
            base_inspection_json_emit_error \
                "gh branch stale" upstream_error \
                "Git reference inspection failed." \
                '{"operation":"git_for_each_ref"}'
        else
            base_gh_error "Git reference inspection failed."
        fi
        return "$status"
    fi

    printf -v now '%(%s)T' -1
    [[ "$output_format" == "json" ]] || printf 'age_days\tlast_commit\tbranch\n'
    while read -r timestamp ref; do
        [[ -n "$timestamp" && -n "$ref" ]] || continue
        [[ "$ref" != refs/remotes/origin/HEAD ]] || continue
        age=$(((now - timestamp) / 86400))
        if ((age >= days)); then
            name="${ref#refs/heads/}"
            name="${name#refs/remotes/}"
            if [[ "$output_format" == "json" ]]; then
                if [[ "$ref" == refs/remotes/* ]]; then
                    scope=remote
                else
                    scope=local
                fi
                name_json="$(base_inspection_json_string "$name")"
                last_commit_json="$(base_inspection_json_string "$(base_gh_format_unix_date "$timestamp")")"
                printf -v ref \
                    '{"name":%s,"scope":"%s","age_days":%d,"last_commit":%s,"last_commit_unix":%d}' \
                    "$name_json" "$scope" "$age" "$last_commit_json" "$timestamp"
                branches_json+=("$ref")
            else
                printf '%s\t%s\t%s\n' "$age" "$(base_gh_format_unix_date "$timestamp")" "$name"
            fi
        fi
    done <<<"$refs_output"

    if [[ "$output_format" == "json" ]]; then
        ((${#branches_json[@]})) && envelope_status=warn
        branches_joined="$(IFS=,; printf '%s' "${branches_json[*]}")"
        printf -v data_json \
            '{"days":%d,"inspected_at_unix":%d,"branches":[%s]}' \
            "$days" "$now" "$branches_joined"
        base_inspection_json_envelope "gh branch stale" "$envelope_status" "$data_json" null
    fi
}

base_gh_branch_stale_format_error() {
    local output_format="$1"
    local message="$2"

    if [[ "$output_format" == "json" ]]; then
        base_inspection_json_emit_error "gh branch stale" usage_error "$message" '{}'
        return 2
    fi
    base_gh_usage_error base_gh_branch_usage "$message"
}

base_gh_validate_prune_mode() {
    local usage_function="$1"
    local dry_run_requested="$2"
    local yes_requested="$3"

    if ((dry_run_requested && yes_requested)); then
        base_gh_usage_error "$usage_function" \
            "Options '--dry-run' and '--yes' cannot be used together; choose either '--dry-run' (preview) or '--yes' (apply)."
        return $?
    fi
    return 0
}

base_gh_format_unix_date() {
    local timestamp="$1"
    local formatted

    if printf -v formatted '%(%Y-%m-%d)T' "$timestamp" 2>/dev/null; then
        printf '%s\n' "$formatted"
        return 0
    fi
    printf 'unknown\n'
}

base_gh_closed_age_days() {
    local closed_unix="$1"
    local now age

    [[ "$closed_unix" =~ ^[0-9]+$ ]] || {
        printf 'unknown\n'
        return 0
    }
    printf -v now '%(%s)T' -1
    age=$(((now - closed_unix) / 86400))
    ((age < 0)) && age=0
    printf '%s\n' "$age"
}

base_gh_branch_pr_detail() {
    local state="$1"
    local pr_numbers="$2"
    local closed_at="$3"
    local closed_unix="$4"
    local age

    case "$state" in
        open)
            printf 'open GitHub PR #%s; branch retained' "$pr_numbers"
            ;;
        closed_unmerged)
            age="$(base_gh_closed_age_days "$closed_unix")"
            if [[ -n "$closed_at" ]]; then
                printf 'closed GitHub PR #%s without merge (%s days ago, %s); branch retained' \
                    "$pr_numbers" "$age" "${closed_at%%T*}"
            else
                printf 'closed GitHub PR #%s without merge; branch retained' "$pr_numbers"
            fi
            ;;
        no_pr)
            printf 'no GitHub PR found; branch retained'
            ;;
        *)
            printf 'branch retained'
            ;;
    esac
}

base_gh_worktree_path_for_branch() {
    local branch="$1"

    base_git_worktree_path_for_branch "$branch"
}

base_gh_branch_upstream() {
    local branch="$1"

    base_git_branch_upstream . "$branch"
}

base_gh_branch_merged_to_ref() {
    local branch="$1"
    local ref="$2"

    base_git_branch_merged_to_ref . "$branch" "$ref"
}

base_gh_prune_github_ready() {
    local gh_path

    if [[ -z "${_base_gh_prune_github_ready+x}" ]]; then
        if base_std_command_path gh_path gh && [[ -n "$gh_path" ]]; then
            _base_gh_prune_github_ready=1
        else
            _base_gh_prune_github_ready=0
        fi
    fi
    [[ "$_base_gh_prune_github_ready" == 1 ]]
}

base_gh_branch_pr_state_cache_reset() {
    BASE_GH_BRANCH_PR_STATE_CACHE=()
    BASE_GH_BRANCH_PR_STATE_CACHE_LOADED=0
    BASE_GH_BRANCH_PR_STATE_CACHE_LOAD_STATUS=0
}

base_gh_branch_github_pr_state_load() {
    local result status branch pr_state pr_number closed_at closed_unix merged_at
    local current_state current_numbers
    local -A state_by_branch=() numbers_by_branch=() closed_at_by_branch=() closed_unix_by_branch=()

    if ((BASE_GH_BRANCH_PR_STATE_CACHE_LOADED)); then
        return "$BASE_GH_BRANCH_PR_STATE_CACHE_LOAD_STATUS"
    fi
    BASE_GH_BRANCH_PR_STATE_CACHE_LOADED=1

    if ! base_gh_prune_github_ready; then
        base_gh_error "GitHub merge verification requires the GitHub CLI 'gh' on PATH."
        BASE_GH_BRANCH_PR_STATE_CACHE_LOAD_STATUS=2
        return 2
    fi

    # `gh pr list --json` uses GitHub's GraphQL API and costs one query per
    # branch. Fetch all pull requests through the paginated REST API so a large
    # repository cannot exhaust the GraphQL budget during a prune scan. Keep
    # `--jq` on the paginated request and aggregate pages here because some gh
    # versions reject combining `--slurp` with `--jq`.
    result="$(base_cli_gh_run api 'repos/{owner}/{repo}/pulls' \
        --method GET \
        --paginate \
        --raw-field state=all \
        --raw-field per_page=100 \
        --jq '
            .[]
            | select(.head.ref != null)
            | [
                .head.ref,
                .state,
                (.number | tostring),
                (.closed_at // "-"),
                (if .closed_at == null then 0 else (.closed_at | fromdateiso8601) end),
                (.merged_at // "-")
            ]
            | @tsv')"
    status=$?
    if ((status != 0)); then
        BASE_GH_BRANCH_PR_STATE_CACHE_LOAD_STATUS=2
        return 2
    fi

    while IFS=$'\t' read -r branch pr_state pr_number closed_at closed_unix merged_at; do
        [[ -n "$branch" ]] || continue
        if [[ "$pr_state" != open && "$pr_state" != closed ]]; then
            base_gh_error "GitHub PR state verification returned an invalid state for branch '$branch'."
            BASE_GH_BRANCH_PR_STATE_CACHE_LOAD_STATUS=2
            return 2
        fi

        current_state="${state_by_branch[$branch]-}"
        current_numbers="${numbers_by_branch[$branch]-}"
        case "$pr_state:$merged_at:$current_state" in
            open:*:*)
                if [[ "$current_state" == open ]]; then
                    current_numbers+="${current_numbers:+,}$pr_number"
                else
                    current_state=open
                    current_numbers="$pr_number"
                fi
                state_by_branch["$branch"]="$current_state"
                numbers_by_branch["$branch"]="$current_numbers"
                ;;
            closed:-:open|closed:-:merged)
                ;;
            closed:-:closed_unmerged)
                current_numbers+="${current_numbers:+,}$pr_number"
                numbers_by_branch["$branch"]="$current_numbers"
                if ((closed_unix > ${closed_unix_by_branch[$branch]:-0})); then
                    closed_at_by_branch["$branch"]="$closed_at"
                    closed_unix_by_branch["$branch"]="$closed_unix"
                fi
                ;;
            closed:-:*)
                current_state=closed_unmerged
                state_by_branch["$branch"]="$current_state"
                numbers_by_branch["$branch"]="$pr_number"
                closed_at_by_branch["$branch"]="$closed_at"
                closed_unix_by_branch["$branch"]="$closed_unix"
                ;;
            closed:*:open)
                ;;
            closed:*:merged)
                current_numbers+="${current_numbers:+,}$pr_number"
                numbers_by_branch["$branch"]="$current_numbers"
                ;;
            closed:*:closed_unmerged)
                current_state=merged
                state_by_branch["$branch"]="$current_state"
                numbers_by_branch["$branch"]="$pr_number"
                closed_at_by_branch["$branch"]=""
                closed_unix_by_branch["$branch"]=0
                ;;
            closed:*:*)
                current_state=merged
                state_by_branch["$branch"]="$current_state"
                numbers_by_branch["$branch"]="$pr_number"
                ;;
        esac
    done <<< "$result"

    for branch in "${!state_by_branch[@]}"; do
        BASE_GH_BRANCH_PR_STATE_CACHE["$branch"]="${state_by_branch[$branch]}"$'\t'"${numbers_by_branch[$branch]}"$'\t'"${closed_at_by_branch[$branch]:--}"$'\t'"${closed_unix_by_branch[$branch]:-0}"
    done

    BASE_GH_BRANCH_PR_STATE_CACHE_LOAD_STATUS=0
    return 0
}

base_gh_branch_github_pr_state() {
    local branch="$1"
    local output_var="${2:-}"
    local state_result

    if [[ ${BASE_GH_BRANCH_PR_STATE_CACHE[$branch]+cached} ]]; then
        state_result="${BASE_GH_BRANCH_PR_STATE_CACHE[$branch]}"
        if [[ -n "$output_var" ]]; then
            printf -v "$output_var" '%s' "$state_result"
        else
            printf '%s\n' "$state_result"
        fi
        return 0
    fi

    base_gh_branch_github_pr_state_load || return $?
    if [[ ${BASE_GH_BRANCH_PR_STATE_CACHE[$branch]+cached} ]]; then
        state_result="${BASE_GH_BRANCH_PR_STATE_CACHE[$branch]}"
        if [[ -n "$output_var" ]]; then
            printf -v "$output_var" '%s' "$state_result"
        else
            printf '%s\n' "$state_result"
        fi
        return 0
    fi

    state_result=$'no_pr\t-\t-\t0'
    BASE_GH_BRANCH_PR_STATE_CACHE["$branch"]="$state_result"
    if [[ -n "$output_var" ]]; then
        printf -v "$output_var" '%s' "$state_result"
    else
        printf '%s\n' "$state_result"
    fi
}

base_gh_branch_github_merged() {
    local branch="$1"
    local result state pr_numbers closed_at closed_unix

    base_gh_branch_github_pr_state "$branch" result || return $?
    IFS=$'\t' read -r state pr_numbers closed_at closed_unix <<< "$result"
    [[ "$state" == merged ]]
}

base_gh_branch_cleanup_state() {
    local branch="$1"
    local default_branch="$2"
    local state_var="$3"
    local merge_source_var="$4"
    local pr_numbers_var="$5"
    local closed_at_var="$6"
    local closed_unix_var="$7"
    local result resolved_state resolved_pr_numbers resolved_closed_at resolved_closed_unix

    if base_gh_branch_merged_to_ref "$branch" "$default_branch"; then
        printf -v "$state_var" '%s' merged
        printf -v "$merge_source_var" '%s' git
        printf -v "$pr_numbers_var" '%s' ''
        printf -v "$closed_at_var" '%s' ''
        printf -v "$closed_unix_var" '%s' 0
        return 0
    fi

    base_gh_branch_github_pr_state "$branch" result || return $?
    IFS=$'\t' read -r resolved_state resolved_pr_numbers resolved_closed_at resolved_closed_unix <<< "$result"
    [[ "$resolved_pr_numbers" == - ]] && resolved_pr_numbers=""
    [[ "$resolved_closed_at" == - ]] && resolved_closed_at=""
    printf -v "$state_var" '%s' "$resolved_state"
    printf -v "$merge_source_var" '%s' "$([[ "$resolved_state" == merged ]] && printf github || printf '')"
    printf -v "$pr_numbers_var" '%s' "$resolved_pr_numbers"
    printf -v "$closed_at_var" '%s' "$resolved_closed_at"
    printf -v "$closed_unix_var" '%s' "$resolved_closed_unix"
    [[ "$resolved_state" == merged ]]
}

base_gh_branch_cleanup_merged() {
    local branch="$1"
    local default_branch="$2"
    local merge_source_var="${3:-}"
    local state resolved_source pr_numbers closed_at closed_unix rc

    if base_gh_branch_cleanup_state "$branch" "$default_branch" state resolved_source pr_numbers closed_at closed_unix; then
        [[ -z "$merge_source_var" ]] || printf -v "$merge_source_var" '%s' "$resolved_source"
        return 0
    fi
    rc=$?
    if ((rc == 2)); then
        [[ -z "$merge_source_var" ]] || printf -v "$merge_source_var" '%s' unknown
        return 2
    fi
    return 1
}

base_gh_branch_delete() {
    local branch="$1"
    local merge_source="$2"

    if [[ "$merge_source" == github || "$merge_source" == closed_unmerged ]]; then
        git branch -D "$branch" >/dev/null 2>&1
    else
        git branch -d "$branch" >/dev/null 2>&1
    fi
}

base_gh_list_remote_branches() {
    base_git_list_remote_branches .
}

base_gh_branch_delete_remote() {
    local branch="$1"

    git push origin --delete "$branch" >/dev/null 2>&1
}

base_gh_branch_prune_local() {
    local dry_run="$1"
    local default_branch="$2"
    local include_closed_unmerged="${3:-0}"
    local branch current_branch merge_source merge_status worktree_path upstream
    local state pr_numbers closed_at closed_unix detail
    local deleted=0 skipped_current=0 skipped_worktree=0 skipped_upstream=0 failed=0 candidates=0
    local closed_review=0 open_review=0 no_pr_review=0

    current_branch="$(git branch --show-current)"
    printf 'Local branches\n'
    while read -r branch; do
        branch="${branch#\* }"
        branch="${branch## }"
        [[ -n "$branch" ]] || continue
        if [[ "$branch" == "$default_branch" || "$branch" == "$current_branch" ]]; then
            printf 'SKIP   %s  current/default branch protected\n' "$branch"
            skipped_current=$((skipped_current + 1))
            continue
        fi

        merge_source=""
        if base_gh_branch_cleanup_state "$branch" "$default_branch" state merge_source pr_numbers closed_at closed_unix; then
            merge_status=0
        else
            merge_status=$?
        fi
        if ((merge_status == 1)); then
            if [[ "$state" == closed_unmerged && "$include_closed_unmerged" == 1 ]]; then
                merge_source=closed_unmerged
                merge_status=0
            else
                detail="$(base_gh_branch_pr_detail "$state" "$pr_numbers" "$closed_at" "$closed_unix")"
                printf 'SKIP   %s  %s\n' "$branch" "$detail"
                case "$state" in
                    closed_unmerged) closed_review=$((closed_review + 1)) ;;
                    open) open_review=$((open_review + 1)) ;;
                    no_pr) no_pr_review=$((no_pr_review + 1)) ;;
                esac
                continue
            fi
        fi
        if ((merge_status != 0)); then
            printf 'SKIP   %s  GitHub merge verification unavailable; local branch retained\n' "$branch"
            failed=$((failed + 1))
            continue
        fi
        candidates=$((candidates + 1))

        worktree_path="$(base_gh_worktree_path_for_branch "$branch" || true)"
        if [[ -n "$worktree_path" ]]; then
            printf 'SKIP   %s  attached to worktree %s\n' "$branch" "$worktree_path"
            skipped_worktree=$((skipped_worktree + 1))
            continue
        fi

        upstream="$(base_gh_branch_upstream "$branch")"
        if [[ "$merge_source" != github && "$merge_source" != closed_unmerged && -n "$upstream" ]] && ! base_gh_branch_merged_to_ref "$branch" "$upstream"; then
            printf 'SKIP   %s  not fully merged to upstream %s\n' "$branch" "$upstream"
            skipped_upstream=$((skipped_upstream + 1))
            continue
        fi

        if ((dry_run)); then
            if [[ "$merge_source" == closed_unmerged ]]; then
                printf '[DRY-RUN] DELETE %s  closed unmerged GitHub PR #%s\n' "$branch" "$pr_numbers"
            elif [[ "$merge_source" == github ]]; then
                printf '[DRY-RUN] DELETE %s  merged GitHub PR\n' "$branch"
            else
                printf '[DRY-RUN] DELETE %s\n' "$branch"
            fi
            deleted=$((deleted + 1))
        elif base_gh_branch_delete "$branch" "$merge_source"; then
            printf 'DELETE %s\n' "$branch"
            deleted=$((deleted + 1))
        else
            printf 'FAIL   %s  local branch deletion failed\n' "$branch"
            failed=$((failed + 1))
        fi
    done < <(git branch --format='%(refname:short)')

    if ((candidates == 0 && failed == 0)); then
        printf 'No merged local branches found.\n'
    fi
    if ((skipped_worktree > 0)); then
        printf 'Hint: run `basectl gh worktree prune` to preview these worktrees, then `basectl gh worktree prune --yes` and rerun this command.\n'
    fi
    printf 'Summary: %s %s, %s skipped current/default, %s skipped worktree, %s skipped upstream, %s failed.\n' \
        "$deleted" "$([[ "$dry_run" -eq 1 ]] && printf 'would delete' || printf 'deleted')" \
        "$skipped_current" "$skipped_worktree" "$skipped_upstream" "$failed"
    printf 'Classification: %s closed-unmerged review, %s open PR, %s no PR.\n' \
        "$closed_review" "$open_review" "$no_pr_review"
    if ((failed > 0)); then
        return 1
    fi
    return 0
}

base_gh_branch_prune_github_branches() {
    local dry_run="$1"
    local default_branch="$2"
    local include_closed_unmerged="${3:-0}"
    local branch current_branch merge_source merge_status worktree_path remote_branches result
    local state pr_numbers closed_at closed_unix detail
    local deleted=0 skipped_current=0 skipped_worktree=0 skipped_unmerged=0 failed=0 candidates=0 found=0
    local closed_review=0 open_review=0 no_pr_review=0

    printf 'GitHub branches\n'
    if ! base_gh_prune_github_ready; then
        base_gh_error "GitHub merge verification requires the GitHub CLI 'gh' on PATH."
        printf 'SKIP   GitHub merge verification unavailable; remote branches retained\n'
        printf 'Summary: 0 %s, 0 skipped current/default, 0 skipped worktree, 0 skipped unmerged, 1 failed.\n' \
            "$([[ "$dry_run" -eq 1 ]] && printf 'would delete remotely' || printf 'deleted remotely')"
        return 1
    fi

    current_branch="$(git branch --show-current)"
    remote_branches="$(base_gh_list_remote_branches)" || {
        base_gh_error "Unable to list remote branches from origin."
        return 1
    }
    while read -r branch; do
        [[ -n "$branch" ]] || continue
        found=1
        if [[ "$branch" == "$default_branch" || "$branch" == "$current_branch" ]]; then
            printf 'SKIP   origin/%s  current/default branch protected\n' "$branch"
            skipped_current=$((skipped_current + 1))
            continue
        fi

        merge_source=""
        if base_gh_branch_github_pr_state "$branch" result; then
            merge_status=0
            IFS=$'\t' read -r state pr_numbers closed_at closed_unix <<< "$result"
            [[ "$pr_numbers" == - ]] && pr_numbers=""
            [[ "$closed_at" == - ]] && closed_at=""
            if [[ "$state" != merged ]]; then
                if [[ "$state" == closed_unmerged && "$include_closed_unmerged" == 1 ]]; then
                    merge_source=closed_unmerged
                else
                    detail="$(base_gh_branch_pr_detail "$state" "$pr_numbers" "$closed_at" "$closed_unix")"
                    printf 'SKIP   origin/%s  %s\n' "$branch" "$detail"
                    skipped_unmerged=$((skipped_unmerged + 1))
                    case "$state" in
                        closed_unmerged) closed_review=$((closed_review + 1)) ;;
                        open) open_review=$((open_review + 1)) ;;
                        no_pr) no_pr_review=$((no_pr_review + 1)) ;;
                    esac
                    continue
                fi
            else
                merge_source=github
            fi
        else
            merge_status=$?
        fi
        if ((merge_status != 0)); then
            printf 'SKIP   origin/%s  GitHub merge verification unavailable; remote branch retained\n' "$branch"
            failed=$((failed + 1))
            continue
        fi
        candidates=$((candidates + 1))

        worktree_path="$(base_gh_worktree_path_for_branch "$branch" || true)"
        if [[ -n "$worktree_path" ]]; then
            printf 'SKIP   origin/%s  attached to worktree %s\n' "$branch" "$worktree_path"
            skipped_worktree=$((skipped_worktree + 1))
            continue
        fi

        if ((dry_run)); then
            if [[ "$merge_source" == closed_unmerged ]]; then
                printf '[DRY-RUN] DELETE-REMOTE origin/%s  closed unmerged GitHub PR #%s\n' "$branch" "$pr_numbers"
            else
                printf '[DRY-RUN] DELETE-REMOTE origin/%s  merged GitHub PR\n' "$branch"
            fi
            deleted=$((deleted + 1))
        elif base_gh_branch_delete_remote "$branch"; then
            printf 'DELETE-REMOTE origin/%s\n' "$branch"
            deleted=$((deleted + 1))
        else
            printf 'FAIL   origin/%s  git push origin --delete failed\n' "$branch"
            failed=$((failed + 1))
        fi
    done <<< "$remote_branches"

    if ((found == 0)); then
        printf 'No GitHub remote branches found.\n'
    elif ((candidates == 0 && failed == 0)); then
        printf 'No merged GitHub remote branches found.\n'
    fi
    printf 'Summary: %s %s, %s skipped current/default, %s skipped worktree, %s skipped unmerged, %s failed.\n' \
        "$deleted" "$([[ "$dry_run" -eq 1 ]] && printf 'would delete remotely' || printf 'deleted remotely')" \
        "$skipped_current" "$skipped_worktree" "$skipped_unmerged" "$failed"
    printf 'Classification: %s closed-unmerged review, %s open PR, %s no PR.\n' \
        "$closed_review" "$open_review" "$no_pr_review"
    if ((failed > 0)); then
        return 1
    fi
    return 0
}

base_gh_branch_prune_remote_tracking_refs() {
    local dry_run="$1"
    local output line ref found=0

    printf 'Remote tracking refs\n'
    if ((dry_run)); then
        output="$(git remote prune origin --dry-run 2>&1)" || {
            base_gh_error "git remote prune origin --dry-run failed."
            [[ -n "$output" ]] && printf '%s\n' "$output" >&2
            return 1
        }
    else
        output="$(git remote prune origin 2>&1)" || {
            base_gh_error "git remote prune origin failed."
            [[ -n "$output" ]] && printf '%s\n' "$output" >&2
            return 1
        }
    fi

    while IFS= read -r line; do
        case "$line" in
            *"[would prune]"*)
                ref="${line##*] }"
                printf '[DRY-RUN] PRUNE %s\n' "$ref"
                found=1
                ;;
            *"[pruned]"*)
                ref="${line##*] }"
                printf 'PRUNE %s\n' "$ref"
                found=1
                ;;
        esac
    done <<< "$output"

    if ((found == 0)); then
        printf 'No stale remote-tracking refs found.\n'
    fi
    printf 'Note: remote-tracking ref cleanup prunes stale local origin/* refs after GitHub branch cleanup.\n'
}

base_gh_branch_prune() {
    local dry_run=1 remote=0 include_closed_unmerged=0 default_branch status=0
    local dry_run_requested=0 yes_requested=0
    local -a parser_args=() positionals=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "dry_run|flag|--dry-run"
        "yes|flag|--yes"
        "remote|flag|--remote"
        "closed_unmerged|flag|--closed-unmerged"
    )
    local -A parsed_options=()

    base_gh_branch_pr_state_cache_reset
    while (($#)); do
        case "$1" in
            --dry-run)
                parser_args+=("$1")
                ;;
            --yes)
                parser_args+=("$1")
                ;;
            --remote)
                parser_args+=("$1")
                ;;
            --closed-unmerged)
                parser_args+=("$1")
                ;;
            -h|--help)
                base_gh_branch_leaf_usage prune
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_branch_usage "Unknown option '$1'."
                return $?
                ;;
        esac
        shift
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_gh_usage_error base_gh_branch_usage "Could not parse branch prune arguments."
        return $?
    fi
    if ((${#positionals[@]} > 0)); then
        base_gh_usage_error base_gh_branch_usage "Unknown option '${positionals[0]}'."
        return $?
    fi

    dry_run_requested="${parsed_options[dry_run]:-0}"
    yes_requested="${parsed_options[yes]:-0}"
    remote="${parsed_options[remote]:-0}"
    include_closed_unmerged="${parsed_options[closed_unmerged]:-0}"

    base_gh_validate_prune_mode base_gh_branch_usage "$dry_run_requested" "$yes_requested" || return $?
    ((yes_requested)) && dry_run=0

    base_gh_require_git_repo || return 1
    default_branch="$(base_gh_default_branch)"
    if ((dry_run)); then
        printf '[DRY-RUN] Branch prune preview for default branch %s.\n' "$default_branch"
    fi
    base_gh_branch_prune_local "$dry_run" "$default_branch" "$include_closed_unmerged" || status=$?

    if ((remote)); then
        base_gh_branch_prune_github_branches "$dry_run" "$default_branch" "$include_closed_unmerged" || status=$?
        base_gh_branch_prune_remote_tracking_refs "$dry_run" || status=$?
    fi
    if ((dry_run)); then
        if ((status == 0)); then
            printf 'Run with --yes to apply these changes.\n'
        else
            printf 'Resolve the reported failures and rerun before using --yes.\n'
        fi
    fi
    return "$status"
}

base_gh_resolve_physical_path() {
    local path="$1"
    (cd "$path" && pwd -P)
}

base_gh_list_worktree_branches() {
    base_git_list_worktree_branches .
}

base_gh_worktree_dirty() {
    local path="$1"
    [[ -n "$(git -C "$path" status --porcelain --ignore-submodules=none)" ]]
}

base_gh_worktree_prune_delete_branch() {
    local branch="$1"
    local merge_source="$2"
    local upstream

    upstream="$(base_gh_branch_upstream "$branch")"
    if [[ "$merge_source" != github && "$merge_source" != closed_unmerged && -n "$upstream" ]] && ! base_gh_branch_merged_to_ref "$branch" "$upstream"; then
        printf 'SKIP-BRANCH %s  not fully merged to upstream %s\n' "$branch" "$upstream"
        return 1
    fi

    if base_gh_branch_delete "$branch" "$merge_source"; then
        printf 'DELETE %s\n' "$branch"
    else
        printf 'SKIP-BRANCH %s  git branch -d refused\n' "$branch"
        return 1
    fi
}

base_gh_worktree_prune() {
    local dry_run=1 default_branch current_worktree
    local path branch merge_source merge_status physical_path
    local include_closed_unmerged=0 state pr_numbers closed_at closed_unix detail
    local removed=0 skipped_current=0 skipped_dirty=0 skipped_unmerged=0 failed=0 candidates=0
    local closed_review=0 open_review=0 no_pr_review=0
    local dry_run_requested=0 yes_requested=0
    local -a parser_args=() positionals=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "dry_run|flag|--dry-run"
        "yes|flag|--yes"
        "closed_unmerged|flag|--closed-unmerged"
    )
    local -A parsed_options=()

    base_gh_branch_pr_state_cache_reset
    while (($#)); do
        case "$1" in
            --dry-run)
                parser_args+=("$1")
                ;;
            --yes)
                parser_args+=("$1")
                ;;
            --closed-unmerged)
                parser_args+=("$1")
                ;;
            --remote)
                base_gh_usage_error base_gh_worktree_usage \
                    "Option '--remote' is only supported by 'basectl gh branch prune'. Run 'basectl gh branch prune --remote' for remote branch cleanup."
                return $?
                ;;
            -h|--help)
                base_gh_worktree_usage
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_worktree_usage "Unknown option '$1'."
                return $?
                ;;
        esac
        shift
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_gh_usage_error base_gh_worktree_usage "Could not parse worktree prune arguments."
        return $?
    fi
    if ((${#positionals[@]} > 0)); then
        base_gh_usage_error base_gh_worktree_usage "Unknown option '${positionals[0]}'."
        return $?
    fi

    dry_run_requested="${parsed_options[dry_run]:-0}"
    yes_requested="${parsed_options[yes]:-0}"
    include_closed_unmerged="${parsed_options[closed_unmerged]:-0}"

    base_gh_validate_prune_mode base_gh_worktree_usage "$dry_run_requested" "$yes_requested" || return $?
    ((yes_requested)) && dry_run=0

    base_gh_require_git_repo || return 1
    default_branch="$(base_gh_default_branch)"
    current_worktree="$(base_gh_resolve_physical_path "$(git rev-parse --show-toplevel)")" || return 1

    if ((dry_run)); then
        printf '[DRY-RUN] Worktree prune preview for default branch %s.\n' "$default_branch"
    fi
    printf 'Worktrees\n'

    while IFS=$'\t' read -r path branch; do
        [[ -n "$path" && -n "$branch" ]] || continue
        physical_path="$(base_gh_resolve_physical_path "$path")" || {
            printf 'FAIL   %s (%s)  unable to inspect worktree path\n' "$path" "$branch"
            failed=$((failed + 1))
            continue
        }
        candidates=$((candidates + 1))

        if [[ "$physical_path" == "$current_worktree" ]]; then
            printf 'SKIP   %s (%s)  current worktree\n' "$path" "$branch"
            skipped_current=$((skipped_current + 1))
            continue
        fi
        if [[ "$branch" == "$default_branch" ]]; then
            printf 'SKIP   %s (%s)  default branch worktree\n' "$path" "$branch"
            skipped_current=$((skipped_current + 1))
            continue
        fi
        if base_gh_worktree_dirty "$path"; then
            printf 'SKIP   %s (%s)  dirty worktree\n' "$path" "$branch"
            skipped_dirty=$((skipped_dirty + 1))
            continue
        fi
        merge_source=""
        if base_gh_branch_cleanup_state "$branch" "$default_branch" state merge_source pr_numbers closed_at closed_unix; then
            merge_status=0
        else
            merge_status=$?
        fi
        if ((merge_status == 1)); then
            if [[ "$state" == closed_unmerged && "$include_closed_unmerged" == 1 ]]; then
                merge_source=closed_unmerged
                merge_status=0
            else
                detail="$(base_gh_branch_pr_detail "$state" "$pr_numbers" "$closed_at" "$closed_unix")"
                printf 'SKIP   %s (%s)  %s\n' "$path" "$branch" "$detail"
                skipped_unmerged=$((skipped_unmerged + 1))
                case "$state" in
                    closed_unmerged) closed_review=$((closed_review + 1)) ;;
                    open) open_review=$((open_review + 1)) ;;
                    no_pr) no_pr_review=$((no_pr_review + 1)) ;;
                esac
                continue
            fi
        fi
        if ((merge_status != 0)); then
            printf 'SKIP   %s (%s)  GitHub merge verification unavailable; worktree retained\n' "$path" "$branch"
            failed=$((failed + 1))
            continue
        fi

        if ((dry_run)); then
            if [[ "$merge_source" == closed_unmerged ]]; then
                printf '[DRY-RUN] REMOVE %s (%s) and delete local branch; closed unmerged GitHub PR #%s; remote branch retained\n' \
                    "$path" "$branch" "$pr_numbers"
            elif [[ "$merge_source" == github ]]; then
                printf '[DRY-RUN] REMOVE %s (%s) and delete local branch; merged GitHub PR\n' "$path" "$branch"
            else
                printf '[DRY-RUN] REMOVE %s (%s) and delete local branch\n' "$path" "$branch"
            fi
            removed=$((removed + 1))
        elif git worktree remove "$path" >/dev/null 2>&1; then
            if [[ "$merge_source" == closed_unmerged ]]; then
                printf 'REMOVE %s (%s); remote branch retained\n' "$path" "$branch"
            else
                printf 'REMOVE %s (%s)\n' "$path" "$branch"
            fi
            removed=$((removed + 1))
            if ! base_gh_worktree_prune_delete_branch "$branch" "$merge_source"; then
                failed=$((failed + 1))
            fi
        else
            printf 'FAIL   %s (%s)  git worktree remove failed\n' "$path" "$branch"
            failed=$((failed + 1))
        fi
    done < <(base_gh_list_worktree_branches)

    if ((candidates == 0)); then
        printf 'No Git worktrees found.\n'
    fi
    printf 'Summary: %s %s, %s skipped current/default, %s skipped dirty, %s skipped unmerged, %s failed.\n' \
        "$removed" "$([[ "$dry_run" -eq 1 ]] && printf 'would remove' || printf 'removed')" \
        "$skipped_current" "$skipped_dirty" "$skipped_unmerged" "$failed"
    printf 'Classification: %s closed-unmerged review, %s open PR, %s no PR.\n' \
        "$closed_review" "$open_review" "$no_pr_review"
    if ((dry_run)); then
        if ((failed == 0)); then
            printf 'Run with --yes to apply these changes.\n'
        else
            printf 'Resolve the reported failures and rerun before using --yes.\n'
        fi
    fi
    if ((failed > 0)); then
        return 1
    fi
    return 0
}

base_gh_do_branch() {
    local command="${1:-}"
    shift || true

    case "$command" in
        stale) base_gh_branch_stale "$@" ;;
        prune) base_gh_branch_prune "$@" ;;
        -h|--help|help|"") base_gh_branch_usage ;;
        *)
            base_gh_usage_error base_gh_branch_usage "Unknown gh branch command '$command'."
            return $?
            ;;
    esac
}

base_gh_do_worktree() {
    local command="${1:-}"
    shift || true

    case "$command" in
        prune) base_gh_worktree_prune "$@" ;;
        -h|--help|help|"") base_gh_worktree_usage ;;
        *)
            base_gh_usage_error base_gh_worktree_usage "Unknown gh worktree command '$command'."
            return $?
            ;;
    esac
}
