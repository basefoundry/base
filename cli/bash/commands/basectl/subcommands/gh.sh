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
  - Branch pruning is dry-run by default and applies only when --yes is passed.
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

    gh auth status >/dev/null 2>&1 || {
        base_gh_error "GitHub CLI authentication is not ready."
        base_gh_error "Run 'gh auth login -h github.com' and retry."
        return 1
    }
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
            base_gh_require_auth || return 1
            gh pr status "$@"
            ;;
        checks)
            base_gh_require_auth || return 1
            gh pr checks "$@"
            ;;
        ready)
            base_gh_require_auth || return 1
            gh pr ready "$@"
            ;;
        merge)
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

base_gh_branch_prune() {
    local dry_run=1 remote=0 default_branch current_branch branch

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
    current_branch="$(git branch --show-current)"

    if ((dry_run)); then
        printf '[DRY-RUN] Local branches merged into %s that would be deleted:\n' "$default_branch"
    fi

    while read -r branch; do
        branch="${branch#\* }"
        branch="${branch## }"
        [[ -z "$branch" || "$branch" == "$default_branch" || "$branch" == "$current_branch" ]] && continue
        if ((dry_run)); then
            printf '%s\n' "$branch"
        else
            git branch -d "$branch"
        fi
    done < <(git branch --merged "$default_branch" --format='%(refname:short)')

    if ((remote)); then
        if ((dry_run)); then
            printf '[DRY-RUN] Remote pruning would run: git remote prune origin\n'
        else
            git remote prune origin
        fi
    fi
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
        todo) base_gh_do_todo "$@" ;;
        -h|--help|help|"") base_gh_usage ;;
        *)
            base_gh_error "Unknown gh area '$area'."
            base_gh_usage >&2
            return 1
            ;;
    esac
}
