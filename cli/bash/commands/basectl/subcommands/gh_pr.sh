#!/usr/bin/env bash

[[ -n "${_base_gh_pr_sourced:-}" ]] && return 0
_base_gh_pr_sourced=1
readonly _base_gh_pr_sourced

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
  - base_manifest.yaml may declare github.pr sections for generated PR bodies.
  - --no-fixes disables automatic Fixes #<issue> body injection for create.
  - Pull request implementation work should happen in a dedicated worktree.
EOF
}

base_gh_pr_leaf_usage() {
    local pr_command="$1"
    local purpose

    case "$pr_command" in
        create) purpose="Create an issue-linked pull request from the current Base branch." ;;
        status) purpose="Show pull-request status through the GitHub CLI." ;;
        checks) purpose="Show pull-request checks through the GitHub CLI." ;;
        ready) purpose="Mark a pull request ready for review through the GitHub CLI." ;;
        merge) purpose="Merge a pull request through the GitHub CLI." ;;
        *) return 1 ;;
    esac

    cat <<EOF
Usage:
  basectl gh pr $pr_command [gh options...]

Purpose:
  $purpose

Options:
EOF
    if [[ "$pr_command" == create ]]; then
        printf '%s\n' '  --no-fixes  Do not add the issue-closing line derived from the branch.'
    fi
    cat <<EOF
  -h, --help  Show this help text.

Additional options are passed through to \`gh pr $pr_command\`.
EOF
}
base_gh_pr_create() {
    local branch branch_category issue issue_category github_repo body_file status
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
    branch="$(git branch --show-current 2>/dev/null)" || {
        base_gh_error "Unable to determine the current branch."
        return 1
    }
    if ! base_github_branch_name_is_valid "$branch"; then
        base_gh_error "Branch '$branch' does not follow <category>/<issue>-<YYYYMMDD>-<slug>."
        printf 'Categories: bug, enhancement, documentation, ci, security.\n' >&2
        printf "Fix: run 'basectl gh issue start <number>' and move the work to its printed branch/worktree.\n" >&2
        return 2
    fi
    issue="$(base_gh_current_issue_from_branch)" || return 1
    branch_category="${branch%%/*}"
    base_gh_require_command gh || return 1
    github_repo="$(base_gh_pr_target_repo "${passthrough[@]}")"
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
    if [[ "$branch_category" != "$issue_category" ]]; then
        base_gh_error "Branch category '$branch_category' does not match issue #$issue category '$issue_category'."
        printf "Fix: run 'basectl gh issue start %s' and move the work to its printed branch/worktree.\n" "$issue" >&2
        return 2
    fi
    if [[ -n "$issue" && "$no_fixes" -eq 0 ]]; then
        base_std_make_temp_file body_file basectl-gh-pr || return 1
        base_gh_pr_policy_body "$issue" "$github_repo" > "$body_file" || {
            status=$?
            rm -f "$body_file"
            return "$status"
        }
        printf 'Auto-linking PR to issue #%s from branch name. Pass --no-fixes to suppress.\n' "$issue"
        base_cli_gh_run pr create --fill --body-file "$body_file" "${passthrough[@]}"
        status=$?
        rm -f "$body_file"
        return "$status"
    fi
    base_cli_gh_run pr create --fill "${passthrough[@]}"
}

base_gh_pr_main() {
    local command="${1:-}"
    shift || true

    case "$command" in
        create)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_leaf_usage create
                return 0
            fi
            base_gh_pr_create "$@"
            ;;
        status)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_leaf_usage status
                return 0
            fi
            base_cli_gh_run pr status "$@"
            ;;
        checks)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_leaf_usage checks
                return 0
            fi
            base_cli_gh_run pr checks "$@"
            ;;
        ready)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_leaf_usage ready
                return 0
            fi
            base_cli_gh_run pr ready "$@"
            ;;
        merge)
            if base_gh_args_request_help "$@"; then
                base_gh_pr_leaf_usage merge
                return 0
            fi
            base_cli_gh_run pr merge "$@"
            ;;
        -h|--help|help|"")
            base_gh_pr_usage
            ;;
        *)
            base_gh_usage_error base_gh_pr_usage "Unknown gh pr command '$command'."
            return $?
            ;;
    esac
}
