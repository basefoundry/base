#!/usr/bin/env bash

[[ -n "${_base_gh_branch_worktree_sourced:-}" ]] && return 0
_base_gh_branch_worktree_sourced=1
readonly _base_gh_branch_worktree_sourced

base_gh_branch_stale() {
    local days=30 now ref name timestamp age

    while (($#)); do
        case "$1" in
            --days)
                days="${2:-}"
                shift
                ;;
            -h|--help)
                base_gh_branch_usage
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_branch_usage "Unknown option '$1'."
                return $?
                ;;
        esac
        shift
    done

    [[ "$days" =~ ^[0-9]+$ ]] || {
        base_gh_usage_error base_gh_branch_usage "--days must be a positive integer."
        return $?
    }
    base_gh_require_git_repo || return 1

    printf -v now '%(%s)T' -1
    printf 'age_days\tlast_commit\tbranch\n'
    while read -r timestamp ref; do
        age=$(((now - timestamp) / 86400))
        if ((age >= days)); then
            name="${ref#refs/heads/}"
            name="${name#refs/remotes/}"
            printf '%s\t%s\t%s\n' "$age" "$(base_gh_format_unix_date "$timestamp")" "$name"
        fi
    done < <(git for-each-ref --format='%(committerdate:unix) %(refname)' refs/heads refs/remotes/origin | grep -v ' refs/remotes/origin/HEAD$')
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

    base_gh_prune_github_ready || return 2
    count="$(gh pr list --head "$branch" --state merged --json number --jq 'length' 2>/dev/null)" || return 2
    [[ "$count" =~ ^[0-9]+$ ]] || return 2
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
    local branch current_branch merge_source worktree_path upstream
    local deleted=0 skipped_worktree=0 skipped_upstream=0 failed=0 candidates=0

    current_branch="$(git branch --show-current)"
    printf 'Local branches\n'
    while read -r branch; do
        branch="${branch#\* }"
        branch="${branch## }"
        [[ -z "$branch" || "$branch" == "$default_branch" || "$branch" == "$current_branch" ]] && continue

        merge_source=""
        if ! base_gh_branch_cleanup_merged "$branch" "$default_branch" merge_source; then
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

    if ((candidates == 0)); then
        printf 'No merged local branches found.\n'
    fi
    if ((skipped_worktree > 0)); then
        printf 'Hint: run `basectl gh worktree prune` to inspect stale worktrees.\n'
    fi
    printf 'Summary: %s %s, %s skipped worktree, %s skipped upstream, %s failed.\n' \
        "$deleted" "$([[ "$dry_run" -eq 1 ]] && printf 'would delete' || printf 'deleted')" \
        "$skipped_worktree" "$skipped_upstream" "$failed"
    return "$failed"
}

base_gh_branch_prune_github_branches() {
    local dry_run="$1"
    local default_branch="$2"
    local branch current_branch worktree_path remote_branches
    local deleted=0 skipped_worktree=0 skipped_unmerged=0 failed=0 candidates=0 found=0

    printf 'GitHub branches\n'
    if ! base_gh_prune_github_ready; then
        printf 'SKIP   GitHub branch cleanup requires the GitHub CLI `gh` on PATH.\n'
        printf 'Summary: 0 %s, 0 skipped worktree, 0 skipped unmerged, 0 failed.\n' \
            "$([[ "$dry_run" -eq 1 ]] && printf 'would delete remotely' || printf 'deleted remotely')"
        return 0
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

        if ! base_gh_branch_github_merged "$branch"; then
            skipped_unmerged=$((skipped_unmerged + 1))
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
    elif ((candidates == 0)); then
        printf 'No merged GitHub remote branches found.\n'
    fi
    printf 'Summary: %s %s, %s skipped worktree, %s skipped unmerged, %s failed.\n' \
        "$deleted" "$([[ "$dry_run" -eq 1 ]] && printf 'would delete remotely' || printf 'deleted remotely')" \
        "$skipped_worktree" "$skipped_unmerged" "$failed"
    return "$failed"
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
                base_gh_branch_usage
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
        printf 'Run with --yes to apply these changes.\n'
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
    local path branch merge_source physical_path
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
        if ! base_gh_branch_cleanup_merged "$branch" "$default_branch" merge_source; then
            if [[ "$merge_source" == unknown ]]; then
                printf 'SKIP   %s (%s)  branch is not confirmed merged into %s or a merged GitHub PR\n' "$path" "$branch" "$default_branch"
            else
                printf 'SKIP   %s (%s)  branch is not merged into %s or a merged GitHub PR\n' "$path" "$branch" "$default_branch"
            fi
            skipped_unmerged=$((skipped_unmerged + 1))
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
        printf 'Run with --yes to apply these changes.\n'
    fi
    return "$failed"
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
