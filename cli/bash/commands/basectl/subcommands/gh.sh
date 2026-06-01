#!/usr/bin/env bash

[[ -n "${_base_gh_subcommand_sourced:-}" ]] && return
_base_gh_subcommand_sourced=1
readonly _base_gh_subcommand_sourced

base_gh_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue list [gh options...]
  basectl gh issue create --category <bug|enhancement|documentation|ci|security> --title <title> [--body <body>]
  basectl gh issue start <number> [--category <bug|enhancement|documentation|ci|security>] [--title <title>]
  basectl gh pr create [gh options...]
  basectl gh pr status [gh options...]
  basectl gh pr checks [gh options...]
  basectl gh pr ready [gh options...]
  basectl gh pr merge [gh options...]
  basectl gh branch stale [--days <days>]
  basectl gh branch prune [--dry-run] [--yes] [--remote]
  basectl gh worktree prune [--dry-run] [--yes]
  basectl gh todo import [--dry-run] [--file <path>]

Purpose:
  Manage GitHub issues, pull requests, branch naming, and repository hygiene
  using Base's opinionated workflow.

Branch naming:
  <category>/<issue>-<YYYYMMDD>-<slug>

Notes:
  - This command requires the GitHub CLI (`gh`) for GitHub operations.
  - Issues created through this command are assigned to codeforester.
  - Pull request implementation work should happen in a dedicated worktree.
  - Branch and worktree pruning are dry-run by default and apply only when --yes is passed.
  - TODO import is currently a dry-run planning command.
EOF
}

base_gh_error() {
    print_error "$*"
}

base_gh_require_command() {
    local command="$1"

    command -v "$command" >/dev/null 2>&1 || {
        base_gh_error "Required command '$command' was not found on PATH."
        return 1
    }
}

base_gh_require_auth() {
    base_gh_require_command gh || return 1

    gh auth status -h github.com >/dev/null 2>&1 || {
        base_gh_error "GitHub CLI authentication is not ready."
        base_gh_error "Run 'gh auth login -h github.com' and retry."
        return 1
    }
}

base_gh_args_request_help() {
    local arg

    [[ "${1:-}" == "help" ]] && return 0
    for arg in "$@"; do
        case "$arg" in
            -h|--help) return 0 ;;
        esac
    done
    return 1
}

base_gh_require_git_repo() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
        base_gh_error "Current directory is not inside a Git worktree."
        return 1
    }
}

base_gh_default_branch() {
    local default_branch

    if default_branch="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"; then
        default_branch="${default_branch#origin/}"
        [[ -n "$default_branch" ]] && {
            printf '%s\n' "$default_branch"
            return 0
        }
    fi

    if git show-ref --verify --quiet refs/heads/main; then
        printf '%s\n' main
        return 0
    fi

    if git show-ref --verify --quiet refs/heads/master; then
        printf '%s\n' master
        return 0
    fi

    printf '%s\n' master
}

base_gh_validate_category() {
    case "$1" in
        bug|enhancement|documentation|ci|security) return 0 ;;
        *)
            base_gh_error "Invalid category '$1'. Expected one of: bug, enhancement, documentation, ci, security."
            return 1
            ;;
    esac
}

base_gh_slug() {
    local input="$1"
    local slug

    slug="$(printf '%s\n' "$input" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
    if [[ -z "$slug" ]]; then
        slug="work"
    fi
    printf '%.60s\n' "$slug" | sed -E 's/-+$//'
}

base_gh_issue_category_from_labels() {
    local issue="$1"
    local category

    category="$(gh issue view "$issue" --json labels --jq '.labels[].name | select(. == "bug" or . == "enhancement" or . == "documentation" or . == "ci" or . == "security")' 2>/dev/null | head -n 1)"
    if [[ -z "$category" ]]; then
        category="enhancement"
    fi
    base_gh_validate_category "$category" || return 1
    printf '%s\n' "$category"
}

base_gh_issue_title() {
    local issue="$1"
    gh issue view "$issue" --json title --jq '.title'
}

base_gh_current_issue_from_branch() {
    local branch

    branch="$(git branch --show-current 2>/dev/null)" || return 1
    [[ "$branch" =~ ^[^/]+/([0-9]+)- ]] || return 1
    printf '%s\n' "${BASH_REMATCH[1]}"
}

base_gh_do_issue() {
    local command="${1:-}"
    shift || true

    case "$command" in
        list)
            if base_gh_args_request_help "$@"; then
                base_gh_usage
                return 0
            fi
            base_gh_require_auth || return 1
            gh issue list "$@"
            ;;
        create)
            base_gh_issue_create "$@"
            ;;
        start)
            base_gh_issue_start "$@"
            ;;
        -h|--help|help|"")
            base_gh_usage
            ;;
        *)
            base_gh_error "Unknown gh issue command '$command'."
            base_gh_usage >&2
            return 1
            ;;
    esac
}

base_gh_issue_create() {
    local category="" title="" body=""

    while (($#)); do
        case "$1" in
            --category)
                category="${2:-}"
                shift
                ;;
            --title)
                title="${2:-}"
                shift
                ;;
            --body)
                body="${2:-}"
                shift
                ;;
            -h|--help)
                base_gh_usage
                return 0
                ;;
            *)
                base_gh_error "Unknown option '$1'."
                return 1
                ;;
        esac
        shift
    done

    [[ -n "$title" ]] || {
        base_gh_error "Missing required --title."
        return 1
    }
    category="${category:-enhancement}"
    base_gh_validate_category "$category" || return 1
    base_gh_require_auth || return 1

    if [[ -n "$body" ]]; then
        gh issue create --title "$title" --body "$body" --label "$category" --assignee codeforester
    else
        gh issue create --title "$title" --label "$category" --assignee codeforester
    fi
}

base_gh_issue_start() {
    local issue="${1:-}" category="" title="" slug branch today

    [[ -n "$issue" ]] || {
        base_gh_error "Missing issue number."
        return 1
    }
    shift

    while (($#)); do
        case "$1" in
            --category)
                category="${2:-}"
                shift
                ;;
            --title)
                title="${2:-}"
                shift
                ;;
            -h|--help)
                base_gh_usage
                return 0
                ;;
            *)
                base_gh_error "Unknown option '$1'."
                return 1
                ;;
        esac
        shift
    done

    base_gh_require_git_repo || return 1
    if [[ -z "$category" || -z "$title" ]]; then
        base_gh_require_auth || return 1
    fi
    if [[ -z "$category" ]]; then
        category="$(base_gh_issue_category_from_labels "$issue")" || return 1
    fi
    base_gh_validate_category "$category" || return 1
    if [[ -z "$title" ]]; then
        title="$(base_gh_issue_title "$issue")" || return 1
    fi

    slug="$(base_gh_slug "$title")"
    today="$(date +%Y%m%d)"
    branch="$category/$issue-$today-$slug"

    git switch --quiet -c "$branch"
    printf '%s\n' "$branch"
}

base_gh_do_pr() {
    local command="${1:-}"
    local issue body_file status
    shift || true

    case "$command" in
        create)
            if base_gh_args_request_help "$@"; then
                base_gh_usage
                return 0
            fi
            base_gh_require_auth || return 1
            base_gh_require_git_repo || return 1
            issue="$(base_gh_current_issue_from_branch || true)"
            if [[ -n "$issue" ]]; then
                body_file="$(mktemp "${TMPDIR:-/tmp}/basectl-gh-pr.XXXXXX")" || return 1
                printf 'Fixes #%s\n' "$issue" > "$body_file"
                gh pr create --fill --body-file "$body_file" "$@"
                status=$?
                rm -f "$body_file"
                return "$status"
            fi
            gh pr create --fill "$@"
            ;;
        status)
            if base_gh_args_request_help "$@"; then
                base_gh_usage
                return 0
            fi
            base_gh_require_auth || return 1
            gh pr status "$@"
            ;;
        checks)
            if base_gh_args_request_help "$@"; then
                base_gh_usage
                return 0
            fi
            base_gh_require_auth || return 1
            gh pr checks "$@"
            ;;
        ready)
            if base_gh_args_request_help "$@"; then
                base_gh_usage
                return 0
            fi
            base_gh_require_auth || return 1
            gh pr ready "$@"
            ;;
        merge)
            if base_gh_args_request_help "$@"; then
                base_gh_usage
                return 0
            fi
            base_gh_require_auth || return 1
            gh pr merge "$@"
            ;;
        -h|--help|help|"")
            base_gh_usage
            ;;
        *)
            base_gh_error "Unknown gh pr command '$command'."
            base_gh_usage >&2
            return 1
            ;;
    esac
}

base_gh_branch_stale() {
    local days=30 now ref name timestamp age

    while (($#)); do
        case "$1" in
            --days)
                days="${2:-}"
                shift
                ;;
            -h|--help)
                base_gh_usage
                return 0
                ;;
            *)
                base_gh_error "Unknown option '$1'."
                return 1
                ;;
        esac
        shift
    done

    [[ "$days" =~ ^[0-9]+$ ]] || {
        base_gh_error "--days must be a positive integer."
        return 1
    }
    base_gh_require_git_repo || return 1

    now="$(date +%s)"
    printf 'age_days\tlast_commit\tbranch\n'
    while read -r timestamp ref; do
        age=$(((now - timestamp) / 86400))
        if ((age >= days)); then
            name="${ref#refs/heads/}"
            name="${name#refs/remotes/}"
            printf '%s\t%s\t%s\n' "$age" "$(date -r "$timestamp" +%Y-%m-%d 2>/dev/null || date -d "@$timestamp" +%Y-%m-%d)" "$name"
        fi
    done < <(git for-each-ref --format='%(committerdate:unix) %(refname)' refs/heads refs/remotes/origin | grep -v ' refs/remotes/origin/HEAD$')
}

base_gh_worktree_path_for_branch() {
    local branch="$1"
    local target_ref="refs/heads/$branch"
    local line path="" ref

    while IFS= read -r line; do
        case "$line" in
            "worktree "*)
                path="${line#worktree }"
                ;;
            "branch "*)
                ref="${line#branch }"
                if [[ "$ref" == "$target_ref" ]]; then
                    printf '%s\n' "$path"
                    return 0
                fi
                ;;
        esac
    done < <(git worktree list --porcelain)

    return 1
}

base_gh_branch_upstream() {
    local branch="$1"
    git for-each-ref --format='%(upstream:short)' "refs/heads/$branch"
}

base_gh_branch_merged_to_ref() {
    local branch="$1"
    local ref="$2"

    git merge-base --is-ancestor "refs/heads/$branch" "$ref" >/dev/null 2>&1
}

base_gh_branch_prune_local() {
    local dry_run="$1"
    local default_branch="$2"
    local branch worktree_path upstream
    local deleted=0 skipped_worktree=0 skipped_upstream=0 failed=0 candidates=0

    printf 'Local branches\n'
    while read -r branch; do
        branch="${branch#\* }"
        branch="${branch## }"
        [[ -z "$branch" || "$branch" == "$default_branch" ]] && continue
        candidates=$((candidates + 1))

        worktree_path="$(base_gh_worktree_path_for_branch "$branch" || true)"
        if [[ -n "$worktree_path" ]]; then
            printf 'SKIP   %s  attached to worktree %s\n' "$branch" "$worktree_path"
            skipped_worktree=$((skipped_worktree + 1))
            continue
        fi

        upstream="$(base_gh_branch_upstream "$branch")"
        if [[ -n "$upstream" ]] && ! base_gh_branch_merged_to_ref "$branch" "$upstream"; then
            printf 'SKIP   %s  not fully merged to upstream %s\n' "$branch" "$upstream"
            skipped_upstream=$((skipped_upstream + 1))
            continue
        fi

        if ((dry_run)); then
            printf '[DRY-RUN] DELETE %s\n' "$branch"
            deleted=$((deleted + 1))
        elif git branch -d "$branch" >/dev/null 2>&1; then
            printf 'DELETE %s\n' "$branch"
            deleted=$((deleted + 1))
        else
            printf 'FAIL   %s  git branch -d failed\n' "$branch"
            failed=$((failed + 1))
        fi
    done < <(git branch --merged "$default_branch" --format='%(refname:short)')

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

base_gh_branch_prune_remote() {
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
    printf 'Note: --remote prunes stale origin/* tracking refs; it does not delete GitHub branches.\n'
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
                base_gh_usage
                return 0
                ;;
            *)
                base_gh_error "Unknown option '$1'."
                return 1
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
        base_gh_branch_prune_remote "$dry_run" || status=$?
    fi
    return "$status"
}

base_gh_resolve_physical_path() {
    local path="$1"
    (cd "$path" && pwd -P)
}

base_gh_list_worktree_branches() {
    local line path="" branch=""

    while IFS= read -r line; do
        if [[ -z "$line" ]]; then
            if [[ -n "$path" && -n "$branch" ]]; then
                branch="${branch#refs/heads/}"
                printf '%s\t%s\n' "$path" "$branch"
            fi
            path=""
            branch=""
            continue
        fi
        case "$line" in
            "worktree "*)
                path="${line#worktree }"
                ;;
            "branch "*)
                branch="${line#branch }"
                ;;
        esac
    done < <(git worktree list --porcelain; printf '\n')
}

base_gh_worktree_dirty() {
    local path="$1"
    [[ -n "$(git -C "$path" status --porcelain --ignore-submodules=none)" ]]
}

base_gh_worktree_prune_delete_branch() {
    local branch="$1"
    local upstream

    upstream="$(base_gh_branch_upstream "$branch")"
    if [[ -n "$upstream" ]] && ! base_gh_branch_merged_to_ref "$branch" "$upstream"; then
        printf 'SKIP-BRANCH %s  not fully merged to upstream %s\n' "$branch" "$upstream"
        return 0
    fi

    if git branch -d "$branch" >/dev/null 2>&1; then
        printf 'DELETE %s\n' "$branch"
    else
        printf 'SKIP-BRANCH %s  git branch -d refused\n' "$branch"
    fi
}

base_gh_worktree_prune() {
    local dry_run=1 default_branch current_worktree
    local path branch physical_path
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
                base_gh_usage
                return 0
                ;;
            *)
                base_gh_error "Unknown option '$1'."
                return 1
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
        if ! base_gh_branch_merged_to_ref "$branch" "$default_branch"; then
            printf 'SKIP   %s (%s)  branch is not merged into %s\n' "$path" "$branch" "$default_branch"
            skipped_unmerged=$((skipped_unmerged + 1))
            continue
        fi

        if ((dry_run)); then
            printf '[DRY-RUN] REMOVE %s (%s) and delete local branch\n' "$path" "$branch"
            removed=$((removed + 1))
        elif git worktree remove "$path" >/dev/null 2>&1; then
            printf 'REMOVE %s (%s)\n' "$path" "$branch"
            removed=$((removed + 1))
            base_gh_worktree_prune_delete_branch "$branch"
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
    return "$failed"
}

base_gh_do_branch() {
    local command="${1:-}"
    shift || true

    case "$command" in
        stale) base_gh_branch_stale "$@" ;;
        prune) base_gh_branch_prune "$@" ;;
        -h|--help|help|"") base_gh_usage ;;
        *)
            base_gh_error "Unknown gh branch command '$command'."
            base_gh_usage >&2
            return 1
            ;;
    esac
}

base_gh_do_worktree() {
    local command="${1:-}"
    shift || true

    case "$command" in
        prune) base_gh_worktree_prune "$@" ;;
        -h|--help|help|"") base_gh_usage ;;
        *)
            base_gh_error "Unknown gh worktree command '$command'."
            base_gh_usage >&2
            return 1
            ;;
    esac
}

base_gh_todo_infer_category() {
    local section="$1"
    local title="${2:-}"

    case "$title" in
        Harden*) printf '%s\n' security; return 0 ;;
        Fix*|Repair*) printf '%s\n' bug; return 0 ;;
    esac

    case "$section" in
        *Correctness*) printf '%s\n' bug ;;
        *Security*) printf '%s\n' security ;;
        *CI*|*Test*|*Release*) printf '%s\n' ci ;;
        *Documentation*|*Docs*) printf '%s\n' documentation ;;
        *) printf '%s\n' enhancement ;;
    esac
}

base_gh_todo_import() {
    local file="$BASE_HOME/TODO.md" dry_run=1 line section="" title category

    while (($#)); do
        case "$1" in
            --dry-run)
                dry_run=1
                ;;
            --file)
                file="${2:-}"
                shift
                ;;
            -h|--help)
                base_gh_usage
                return 0
                ;;
            *)
                base_gh_error "Unknown option '$1'."
                return 1
                ;;
        esac
        shift
    done

    [[ -f "$file" ]] || {
        base_gh_error "TODO file '$file' was not found."
        return 1
    }

    if ((dry_run)); then
        printf '[DRY-RUN] Issues that would be created from %s:\n' "$file"
    else
        base_gh_error "TODO import creation is not enabled yet; run with --dry-run."
        return 1
    fi

    while IFS= read -r line; do
        case "$line" in
            "## "*)
                section="${line#'## '}"
                ;;
            "- [ ] "*)
                title="${line#'- [ ] '}"
                title="${title%.}"
                category="$(base_gh_todo_infer_category "$section" "$title")"
                printf '%s\t%s\n' "$category" "$title"
                ;;
        esac
    done < "$file"
}

base_gh_do_todo() {
    local command="${1:-}"
    shift || true

    case "$command" in
        import) base_gh_todo_import "$@" ;;
        -h|--help|help|"") base_gh_usage ;;
        *)
            base_gh_error "Unknown gh todo command '$command'."
            base_gh_usage >&2
            return 1
            ;;
    esac
}

base_gh_subcommand_main() {
    local area="${1:-}"
    shift || true

    case "$area" in
        issue) base_gh_do_issue "$@" ;;
        pr) base_gh_do_pr "$@" ;;
        branch) base_gh_do_branch "$@" ;;
        worktree) base_gh_do_worktree "$@" ;;
        todo) base_gh_do_todo "$@" ;;
        -h|--help|help|"") base_gh_usage ;;
        *)
            base_gh_error "Unknown gh area '$area'."
            base_gh_usage >&2
            return 1
            ;;
    esac
}
