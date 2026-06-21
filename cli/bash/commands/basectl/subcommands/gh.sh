#!/usr/bin/env bash

[[ -n "${_base_gh_subcommand_sourced:-}" ]] && return
_base_gh_subcommand_sourced=1
readonly _base_gh_subcommand_sourced

base_gh_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue list [gh options...]
  basectl gh issue create [--category <bug|enhancement|documentation|ci|security>] --title <title> [--body <body>] [--repo <owner/name>] [--size <T|S|M|L>] [project options...]
  basectl gh issue start <number> [--category <bug|enhancement|documentation|ci|security>] [--title <title>]
  basectl gh pr create [--no-fixes] [gh options...]
  basectl gh pr status [gh options...]
  basectl gh pr checks [gh options...]
  basectl gh pr ready [gh options...]
  basectl gh pr merge [gh options...]
  basectl gh project doctor --project <title> [--owner <login>] [--schema base-project]
  basectl gh project configure --project <title> [--owner <login>] [--repo <owner/name>] [--schema base-project] [--replace-project] [--initiative-option <name>] [--dry-run]
  basectl gh project issue set-fields <number> --project <title> [--owner <login>] [--repo <owner/name>] [field options...]
  basectl gh branch stale [--days <days>]
  basectl gh branch prune [--dry-run] [--yes] [--remote]
  basectl gh worktree prune [--dry-run] [--yes]

Purpose:
  Manage GitHub issues, pull requests, Project metadata, branch naming, and
  repository hygiene using Base's opinionated workflow.

Branch naming:
  <category>/<issue>-<YYYYMMDD>-<slug>

Issue create project options:
  --repo <owner/name>           Repository to create the issue in. Defaults to the origin remote.
  --category <category>         Issue label category. Defaults to enhancement.
  --project <title>             Project to update. Defaults to the repository name.
  --project-owner <login>       Project owner. Defaults to the repository owner.
  --size <T|S|M|L>              Project Size value. Defaults to .github/base-project.yml or S.
  --no-project                  Skip Project metadata updates.

Issue categories:
  bug, enhancement, documentation, ci, security

Notes:
  - This command requires the GitHub CLI (`gh`) for GitHub operations.
  - Issues created through this command are assigned to codeforester.
  - When the GitHub repo is known, issue create also adds the issue to the
    repo-named Project and applies defaults from .github/base-project.yml.
  - PR creation auto-injects Fixes #<issue> when the branch follows the Base
    naming convention. Pass --no-fixes to suppress that body injection.
  - Pull request implementation work should happen in a dedicated worktree.
  - Branch and worktree pruning are dry-run by default and apply only when --yes is passed.
EOF
}

base_gh_issue_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue list [gh options...]
  basectl gh issue create [--category <bug|enhancement|documentation|ci|security>] --title <title> [--body <body>] [--repo <owner/name>] [--size <T|S|M|L>] [project options...]
  basectl gh issue start <number> [--category <bug|enhancement|documentation|ci|security>] [--title <title>]

Purpose:
  List, create, and start GitHub issues using Base's issue-first workflow.

Branch naming:
  <category>/<issue>-<YYYYMMDD>-<slug>

Issue create project options:
  --repo <owner/name>           Repository to create the issue in. Defaults to the origin remote.
  --category <category>         Issue label category. Defaults to enhancement.
  --project <title>             Project to update. Defaults to the repository name.
  --project-owner <login>       Project owner. Defaults to the repository owner.
  --size <T|S|M|L>              Project Size value. Defaults to .github/base-project.yml or S.
  --no-project                  Skip Project metadata updates.

Default category: enhancement.
Categories: bug, enhancement, documentation, ci, security.
EOF
}

base_gh_pr_usage() {
    cat <<'EOF'
Usage:
  basectl gh pr create [--no-fixes] [gh options...]
  basectl gh pr status [gh options...]
  basectl gh pr checks [gh options...]
  basectl gh pr ready [gh options...]
  basectl gh pr merge [gh options...]

Purpose:
  Create, inspect, ready, and merge pull requests with Base's issue-linked PR workflow.

Notes:
  - PR creation links the current issue automatically when the branch follows
    <category>/<issue>-<YYYYMMDD>-<slug>.
  - --no-fixes disables automatic Fixes #<issue> body injection for create.
  - Pull request implementation work should happen in a dedicated worktree.
EOF
}

base_gh_project_usage() {
    cat <<'EOF'
Usage:
  basectl gh project doctor --project <title> [--owner <login>] [--schema base-project]
  basectl gh project configure --project <title> [--owner <login>] [--repo <owner/name>] [--schema base-project] [--replace-project] [--initiative-option <name>] [--dry-run]
  basectl gh project issue set-fields <number> --project <title> [--owner <login>] [--repo <owner/name>] [field options...]

Purpose:
  Diagnose, configure, and update GitHub Project metadata for Base-managed repositories.

Notes:
  - Project operations delegate to Base's Python Project engine.
  - Use project issue set-fields to move issue cards through Backlog, In Progress, In Review, and Done.
  - Use --replace-project to replace a nonstandard repo Project from base-project-template.
    Already-standard Projects are left intact.
EOF
}

base_gh_branch_usage() {
    cat <<'EOF'
Usage:
  basectl gh branch stale [--days <days>]
  basectl gh branch prune [--dry-run] [--yes] [--remote]

Purpose:
  Inspect stale branches and prune merged local or GitHub branches.

Note:
  Runs in dry-run mode by default. Pass --yes to apply changes.

Options:
  --days <days>  Minimum age for stale branch reporting. Defaults to 30.
  --dry-run      Preview branches that would be deleted (default).
  --yes          Delete merged branches after preview.
  --remote       Also prune merged GitHub remote branches and stale origin/* refs.
EOF
}

base_gh_worktree_usage() {
    cat <<'EOF'
Usage:
  basectl gh worktree prune [--dry-run] [--yes]

Purpose:
  Prune safe, merged Git worktrees and their local branches.

Note:
  Runs in dry-run mode by default. Pass --yes to apply changes.

Options:
  --dry-run      Preview worktrees that would be removed (default).
  --yes          Remove safe merged worktrees after preview.
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

base_gh_auth_status_diagnostics() {
    local auth_output line

    base_gh_require_command gh || return 1

    auth_output="$(gh auth status -h github.com 2>&1)" || {
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ -n "$line" ]] && base_gh_error "gh auth status: $line"
        done <<<"$auth_output"
        base_gh_error "Run 'gh auth login -h github.com' and retry."
        return 1
    }
}

base_gh_report_command_failure() {
    local status="$1"
    shift

    base_gh_error "GitHub command failed: gh $*"
    base_gh_auth_status_diagnostics || true
    return "$status"
}

base_gh_run() {
    local status

    base_gh_require_command gh || return 1
    gh "$@"
    status=$?
    ((status == 0)) && return 0
    base_gh_report_command_failure "$status" "$@"
    return "$status"
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

    printf '%s\n' main
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

base_gh_infer_github_repo() {
    local remote_url

    remote_url="$(git remote get-url origin 2>/dev/null || true)"
    [[ -n "$remote_url" ]] || return 1

    case "$remote_url" in
        git@github.com:*.git)
            remote_url="${remote_url#git@github.com:}"
            remote_url="${remote_url%.git}"
            ;;
        https://github.com/*.git)
            remote_url="${remote_url#https://github.com/}"
            remote_url="${remote_url%.git}"
            ;;
        https://github.com/*)
            remote_url="${remote_url#https://github.com/}"
            ;;
        *)
            return 1
            ;;
    esac

    [[ "$remote_url" == */* ]] || return 1
    printf '%s\n' "$remote_url"
}

base_gh_default_project_title() {
    local repo="$1"

    printf '%s\n' "${repo#*/}"
}

base_gh_project_owner_from_repo() {
    local repo="$1"

    printf '%s\n' "${repo%%/*}"
}

base_gh_project_config_path() {
    local root path

    root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    [[ -n "$root" ]] || return 1
    path="$root/.github/base-project.yml"
    [[ -f "$path" ]] || return 1
    printf '%s\n' "$path"
}

base_gh_issue_number_from_output() {
    local output="$1"
    local issue_number

    issue_number="$(printf '%s\n' "$output" | sed -nE 's#.*github.com/[^/]+/[^/]+/issues/([0-9]+).*#\1#p' | tail -n 1)"
    [[ -n "$issue_number" ]] || return 1
    printf '%s\n' "$issue_number"
}

base_gh_project_issue_set_fields() {
    local wrapper="${BASE_GH_PROJECT_WRAPPER:-$BASE_HOME/bin/base-wrapper}"

    [[ -x "$wrapper" ]] || {
        base_gh_error "Base Python wrapper '$wrapper' is missing or is not executable."
        return 1
    }
    "$wrapper" --project base base_github_projects project issue set-fields "$@"
}

base_gh_validate_project_size() {
    local size="$1"

    case "$size" in
        T|S|M|L)
            return 0
            ;;
    esac
    base_gh_error "Invalid size '$size'. Expected one of: T, S, M, L."
    return 1
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
                base_gh_issue_usage
                return 0
            fi
            base_gh_run issue list "$@"
            ;;
        create)
            base_gh_issue_create "$@"
            ;;
        start)
            base_gh_issue_start "$@"
            ;;
        -h|--help|help|"")
            base_gh_issue_usage
            ;;
        *)
            base_gh_error "Unknown gh issue command '$command'."
            base_gh_issue_usage >&2
            return 1
            ;;
    esac
}

base_gh_issue_create() {
    local body=""
    local category=""
    local configure_project=1
    local config_path=""
    local github_repo=""
    local issue_number=""
    local issue_output=""
    local project_owner=""
    local project_size=""
    local project_title=""
    local title=""

    while (($#)); do
        case "$1" in
            --category)
                category="${2:-}"
                shift
                ;;
            --repo)
                github_repo="${2:-}"
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
            --project)
                project_title="${2:-}"
                shift
                ;;
            --project-owner)
                project_owner="${2:-}"
                shift
                ;;
            --size)
                project_size="${2:-}"
                shift
                ;;
            --no-project)
                configure_project=0
                ;;
            -h|--help)
                base_gh_issue_usage
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
    if [[ -z "$category" ]]; then
        category="enhancement"
        printf 'Using default --category: enhancement\n'
    fi
    base_gh_validate_category "$category" || return 1
    if [[ -n "$project_size" ]]; then
        base_gh_validate_project_size "$project_size" || return 1
    fi

    [[ -n "$github_repo" ]] || github_repo="$(base_gh_infer_github_repo || true)"
    if [[ -n "$body" ]]; then
        if [[ -n "$github_repo" ]]; then
            issue_output="$(base_gh_run issue create --title "$title" --body "$body" --label "$category" --assignee codeforester --repo "$github_repo")" || return $?
        else
            issue_output="$(base_gh_run issue create --title "$title" --body "$body" --label "$category" --assignee codeforester)" || return $?
        fi
    else
        if [[ -n "$github_repo" ]]; then
            issue_output="$(base_gh_run issue create --title "$title" --label "$category" --assignee codeforester --repo "$github_repo")" || return $?
        else
            issue_output="$(base_gh_run issue create --title "$title" --label "$category" --assignee codeforester)" || return $?
        fi
    fi
    printf '%s\n' "$issue_output"

    if ((configure_project)) && [[ -n "$github_repo" ]]; then
        issue_number="$(base_gh_issue_number_from_output "$issue_output")" || {
            base_gh_error "Unable to determine created issue number from gh output."
            return 1
        }
        [[ -n "$project_title" ]] || project_title="$(base_gh_default_project_title "$github_repo")"
        [[ -n "$project_owner" ]] || project_owner="$(base_gh_project_owner_from_repo "$github_repo")"
        config_path="$(base_gh_project_config_path || true)"
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
            base_gh_project_issue_set_fields "${field_args[@]}"
        else
            [[ -n "$project_size" ]] || project_size="S"
            base_gh_project_issue_set_fields "$issue_number" \
                --project "$project_title" \
                --owner "$project_owner" \
                --repo "$github_repo" \
                --status Backlog \
                --priority P2 \
                --size "$project_size"
        fi
    fi
}

base_gh_pr_create() {
    local issue body_file status
    local no_fixes=0
    local passthrough=()

    while (($#)); do
        case "$1" in
            --no-fixes)
                no_fixes=1
                ;;
            *)
                passthrough+=("$1")
                ;;
        esac
        shift
    done

    base_gh_require_git_repo || return 1
    issue="$(base_gh_current_issue_from_branch || true)"
    if [[ -n "$issue" && "$no_fixes" -eq 0 ]]; then
        body_file="$(mktemp "${TMPDIR:-/tmp}/basectl-gh-pr.XXXXXX")" || return 1
        printf 'Fixes #%s\n' "$issue" > "$body_file"
        printf 'Auto-linking PR to issue #%s from branch name. Pass --no-fixes to suppress.\n' "$issue"
        base_gh_run pr create --fill --body-file "$body_file" "${passthrough[@]}"
        status=$?
        rm -f "$body_file"
        return "$status"
    fi
    base_gh_run pr create --fill "${passthrough[@]}"
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
                base_gh_issue_usage
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
        base_gh_require_command gh || return 1
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
    shift || true

    case "$command" in
        create)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_usage
                return 0
            fi
            base_gh_pr_create "$@"
            ;;
        status)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_usage
                return 0
            fi
            base_gh_run pr status "$@"
            ;;
        checks)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_usage
                return 0
            fi
            base_gh_run pr checks "$@"
            ;;
        ready)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_usage
                return 0
            fi
            base_gh_run pr ready "$@"
            ;;
        merge)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_usage
                return 0
            fi
            base_gh_run pr merge "$@"
            ;;
        -h|--help|help|"")
            base_gh_pr_usage
            ;;
        *)
            base_gh_error "Unknown gh pr command '$command'."
            base_gh_pr_usage >&2
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
                base_gh_branch_usage
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
    local rc

    BASE_GH_BRANCH_MERGE_SOURCE=""
    if base_gh_branch_merged_to_ref "$branch" "$default_branch"; then
        BASE_GH_BRANCH_MERGE_SOURCE=git
        return 0
    fi

    base_gh_branch_github_merged "$branch"
    rc=$?
    if ((rc == 0)); then
        BASE_GH_BRANCH_MERGE_SOURCE=github
        return 0
    fi
    if ((rc == 2)); then
        BASE_GH_BRANCH_MERGE_SOURCE=unknown
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
    local output ref

    output="$(git ls-remote --heads origin)" || return 1
    while read -r _sha ref; do
        [[ "$ref" == refs/heads/* ]] || continue
        printf '%s\n' "${ref#refs/heads/}"
    done <<< "$output"
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

        if ! base_gh_branch_cleanup_merged "$branch" "$default_branch"; then
            continue
        fi
        merge_source="$BASE_GH_BRANCH_MERGE_SOURCE"
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
        if ! base_gh_branch_cleanup_merged "$branch" "$default_branch"; then
            if [[ "$BASE_GH_BRANCH_MERGE_SOURCE" == unknown ]]; then
                printf 'SKIP   %s (%s)  branch is not confirmed merged into %s or a merged GitHub PR\n' "$path" "$branch" "$default_branch"
            else
                printf 'SKIP   %s (%s)  branch is not merged into %s or a merged GitHub PR\n' "$path" "$branch" "$default_branch"
            fi
            skipped_unmerged=$((skipped_unmerged + 1))
            continue
        fi
        merge_source="$BASE_GH_BRANCH_MERGE_SOURCE"

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
            base_gh_error "Unknown gh branch command '$command'."
            base_gh_branch_usage >&2
            return 1
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
            base_gh_error "Unknown gh worktree command '$command'."
            base_gh_worktree_usage >&2
            return 1
            ;;
    esac
}

base_gh_do_project() {
    local wrapper="${BASE_GH_PROJECT_WRAPPER:-$BASE_HOME/bin/base-wrapper}"

    if base_gh_args_request_help "$@"; then
        base_gh_project_usage
        return 0
    fi

    [[ -x "$wrapper" ]] || {
        base_gh_error "Base Python wrapper '$wrapper' is missing or is not executable."
        return 1
    }
    "$wrapper" --project base base_github_projects project "$@"
}

base_gh_subcommand_main() {
    local area="${1:-}"
    shift || true

    case "$area" in
        issue) base_gh_do_issue "$@" ;;
        pr) base_gh_do_pr "$@" ;;
        project) base_gh_do_project "$@" ;;
        branch) base_gh_do_branch "$@" ;;
        worktree) base_gh_do_worktree "$@" ;;
        -h|--help|help|"") base_gh_usage ;;
        *)
            base_gh_error "Unknown gh area '$area'."
            base_gh_usage >&2
            return 1
            ;;
    esac
}
