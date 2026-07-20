#!/usr/bin/env bash

[[ -n "${_base_gh_branch_worktree_sourced:-}" ]] && return 0
_base_gh_branch_worktree_sourced=1
readonly _base_gh_branch_worktree_sourced

base_gh_branch_stale() {
    local days=30 now ref name timestamp age
    local output_format="text" requested_format
    local refs_output status scope last_commit_json name_json data_json branches_joined envelope_status="ok"
    local branches_json=()

    base_inspection_find_output_format output_format "$@"

    while (($#)); do
        case "$1" in
            --days)
                days="${2:-}"
                shift
                ;;
            --format)
                [[ -n "${2:-}" ]] || {
                    base_gh_branch_stale_format_error "$output_format" "Option '--format' requires an argument."
                    return $?
                }
                requested_format="$2"
                case "$requested_format" in
                    text|json)
                        ;;
                    *)
                        base_gh_branch_stale_format_error "$output_format" "Unsupported branch stale format '$requested_format'. Expected text or json."
                        return $?
                        ;;
                esac
                output_format="$requested_format"
                shift
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
        shift
    done

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

base_gh_format_unix_date() {
    local timestamp="$1"
    local formatted

    if printf -v formatted '%(%Y-%m-%d)T' "$timestamp" 2>/dev/null; then
        printf '%s\n' "$formatted"
        return 0
    fi
    printf 'unknown\n'
}

base_gh_worktree_path_for_branch() {
    local branch="$1"

    git_worktree_path_for_branch "$branch"
}

base_gh_branch_upstream() {
    local branch="$1"

    git_branch_upstream . "$branch"
}

base_gh_branch_merged_to_ref() {
    local branch="$1"
    local ref="$2"

    git_branch_merged_to_ref . "$branch" "$ref"
}

base_gh_prune_github_ready() {
    if [[ -z "${_base_gh_prune_github_ready+x}" ]]; then
        if command -v gh >/dev/null 2>&1; then
            _base_gh_prune_github_ready=1
        else
            _base_gh_prune_github_ready=0
        fi
    fi
    [[ "$_base_gh_prune_github_ready" == 1 ]]
}

base_gh_branch_github_merged() {
    local branch="$1"
    local count

    if ! base_gh_prune_github_ready; then
        base_gh_error "GitHub merge verification requires the GitHub CLI 'gh' on PATH."
        return 2
    fi
    count="$(base_gh_run pr list --head "$branch" --state merged --json number --jq 'length')" || return 2
    if [[ ! "$count" =~ ^[0-9]+$ ]]; then
        base_gh_error "GitHub merge verification returned an invalid result for branch '$branch'."
        return 2
    fi
    ((count > 0))
}

base_gh_branch_cleanup_merged() {
    local branch="$1"
    local default_branch="$2"
    local merge_source_var="${3:-}"
    local rc

    if base_gh_branch_merged_to_ref "$branch" "$default_branch"; then
        [[ -z "$merge_source_var" ]] || printf -v "$merge_source_var" '%s' git
        return 0
    fi

    base_gh_branch_github_merged "$branch"
    rc=$?
    if ((rc == 0)); then
        [[ -z "$merge_source_var" ]] || printf -v "$merge_source_var" '%s' github
        return 0
    fi
    if ((rc == 2)); then
        [[ -z "$merge_source_var" ]] || printf -v "$merge_source_var" '%s' unknown
        return 2
    fi
    return 1
}

base_gh_branch_delete() {
    local branch="$1"
    local merge_source="$2"

    if [[ "$merge_source" == github ]]; then
        git branch -D "$branch" >/dev/null 2>&1
    else
        git branch -d "$branch" >/dev/null 2>&1
    fi
}

base_gh_list_remote_branches() {
    git_list_remote_branches .
}

base_gh_branch_delete_remote() {
    local branch="$1"

    git push origin --delete "$branch" >/dev/null 2>&1
}

base_gh_branch_prune_local() {
    local dry_run="$1"
    local default_branch="$2"
    local branch current_branch merge_source merge_status worktree_path upstream
    local deleted=0 skipped_worktree=0 skipped_upstream=0 failed=0 candidates=0

    current_branch="$(git branch --show-current)"
    printf 'Local branches\n'
    while read -r branch; do
        branch="${branch#\* }"
        branch="${branch## }"
        [[ -z "$branch" || "$branch" == "$default_branch" || "$branch" == "$current_branch" ]] && continue

        merge_source=""
        if base_gh_branch_cleanup_merged "$branch" "$default_branch" merge_source; then
            merge_status=0
        else
            merge_status=$?
        fi
        if ((merge_status == 1)); then
            continue
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
        if [[ "$merge_source" != github && -n "$upstream" ]] && ! base_gh_branch_merged_to_ref "$branch" "$upstream"; then
            printf 'SKIP   %s  not fully merged to upstream %s\n' "$branch" "$upstream"
            skipped_upstream=$((skipped_upstream + 1))
            continue
        fi

        if ((dry_run)); then
            if [[ "$merge_source" == github ]]; then
                printf '[DRY-RUN] DELETE %s  merged GitHub PR\n' "$branch"
            else
                printf '[DRY-RUN] DELETE %s\n' "$branch"
            fi
            deleted=$((deleted + 1))
        elif base_gh_branch_delete "$branch" "$merge_source"; then
            printf 'DELETE %s\n' "$branch"
            deleted=$((deleted + 1))
        else
            printf 'FAIL   %s  git branch -d failed\n' "$branch"
            failed=$((failed + 1))
        fi
    done < <(git branch --format='%(refname:short)')

    if ((candidates == 0 && failed == 0)); then
        printf 'No merged local branches found.\n'
    fi
    if ((skipped_worktree > 0)); then
        printf 'Hint: run `basectl gh worktree prune` to inspect stale worktrees.\n'
    fi
    printf 'Summary: %s %s, %s skipped worktree, %s skipped upstream, %s failed.\n' \
        "$deleted" "$([[ "$dry_run" -eq 1 ]] && printf 'would delete' || printf 'deleted')" \
        "$skipped_worktree" "$skipped_upstream" "$failed"
    if ((failed > 0)); then
        return 1
    fi
    return 0
}

base_gh_branch_prune_github_branches() {
    local dry_run="$1"
    local default_branch="$2"
    local branch current_branch merge_status worktree_path remote_branches
    local deleted=0 skipped_worktree=0 skipped_unmerged=0 failed=0 candidates=0 found=0

    printf 'GitHub branches\n'
    if ! base_gh_prune_github_ready; then
        base_gh_error "GitHub merge verification requires the GitHub CLI 'gh' on PATH."
        printf 'SKIP   GitHub merge verification unavailable; remote branches retained\n'
        printf 'Summary: 0 %s, 0 skipped worktree, 0 skipped unmerged, 1 failed.\n' \
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
        [[ "$branch" == "$default_branch" || "$branch" == "$current_branch" ]] && continue

        if base_gh_branch_github_merged "$branch"; then
            merge_status=0
        else
            merge_status=$?
        fi
        if ((merge_status == 1)); then
            skipped_unmerged=$((skipped_unmerged + 1))
            continue
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
            printf '[DRY-RUN] DELETE-REMOTE origin/%s  merged GitHub PR\n' "$branch"
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
    printf 'Summary: %s %s, %s skipped worktree, %s skipped unmerged, %s failed.\n' \
        "$deleted" "$([[ "$dry_run" -eq 1 ]] && printf 'would delete remotely' || printf 'deleted remotely')" \
        "$skipped_worktree" "$skipped_unmerged" "$failed"
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
    local dry_run=1 remote=0 default_branch status=0

    while (($#)); do
        case "$1" in
            --dry-run)
                dry_run=1
                ;;
            --yes)
                dry_run=0
                ;;
            --remote)
                remote=1
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

    base_gh_require_git_repo || return 1
    default_branch="$(base_gh_default_branch)"
    if ((dry_run)); then
        printf '[DRY-RUN] Branch prune preview for default branch %s.\n' "$default_branch"
    fi
    base_gh_branch_prune_local "$dry_run" "$default_branch" || status=$?

    if ((remote)); then
        base_gh_branch_prune_github_branches "$dry_run" "$default_branch" || status=$?
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
    git_list_worktree_branches .
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
    if [[ "$merge_source" != github && -n "$upstream" ]] && ! base_gh_branch_merged_to_ref "$branch" "$upstream"; then
        printf 'SKIP-BRANCH %s  not fully merged to upstream %s\n' "$branch" "$upstream"
        return 0
    fi

    if base_gh_branch_delete "$branch" "$merge_source"; then
        printf 'DELETE %s\n' "$branch"
    else
        printf 'SKIP-BRANCH %s  git branch -d refused\n' "$branch"
    fi
}

base_gh_worktree_prune() {
    local dry_run=1 default_branch current_worktree
    local path branch merge_source merge_status physical_path
    local removed=0 skipped_current=0 skipped_dirty=0 skipped_unmerged=0 failed=0 candidates=0

    while (($#)); do
        case "$1" in
            --dry-run)
                dry_run=1
                ;;
            --yes)
                dry_run=0
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
        if base_gh_branch_cleanup_merged "$branch" "$default_branch" merge_source; then
            merge_status=0
        else
            merge_status=$?
        fi
        if ((merge_status == 1)); then
            printf 'SKIP   %s (%s)  branch is not merged into %s or a merged GitHub PR\n' "$path" "$branch" "$default_branch"
            skipped_unmerged=$((skipped_unmerged + 1))
            continue
        fi
        if ((merge_status != 0)); then
            printf 'SKIP   %s (%s)  GitHub merge verification unavailable; worktree retained\n' "$path" "$branch"
            failed=$((failed + 1))
            continue
        fi

        if ((dry_run)); then
            if [[ "$merge_source" == github ]]; then
                printf '[DRY-RUN] REMOVE %s (%s) and delete local branch; merged GitHub PR\n' "$path" "$branch"
            else
                printf '[DRY-RUN] REMOVE %s (%s) and delete local branch\n' "$path" "$branch"
            fi
            removed=$((removed + 1))
        elif git worktree remove "$path" >/dev/null 2>&1; then
            printf 'REMOVE %s (%s)\n' "$path" "$branch"
            removed=$((removed + 1))
            base_gh_worktree_prune_delete_branch "$branch" "$merge_source"
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
