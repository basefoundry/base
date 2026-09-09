#!/usr/bin/env bash

[[ -n "${_base_gh_subcommand_sourced:-}" ]] && return 0
_base_gh_subcommand_sourced=1
readonly _base_gh_subcommand_sourced

import_base_lib git/lib_git.sh
import_base_lib gh/lib_gh.sh
import_base_lib str/lib_str.sh
import_base_lib arg/lib_arg.sh

source "$BASE_HOME/cli/bash/commands/basectl/subcommands/github_policy.sh"
# shellcheck source=cli/bash/commands/basectl/subcommands/inspection_json.sh
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/inspection_json.sh"
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh_branch_worktree.sh"

base_gh_load_issue_readiness() {
    local module_path

    if declare -F base_gh_issue_readiness >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/gh_issue_readiness.sh" || return 1
    [[ -f "$module_path" ]] || {
        base_std_log_error "gh issue readiness helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/gh_issue_readiness.sh
    source "$module_path"
}

base_gh_usage() {
    cat <<'EOF'
Usage:
  basectl gh auth status [--hostname <host>]
  basectl gh auth refresh [--hostname <host>] [--scope <scope>]... [--scopes <scope,...>] [--clipboard]
  basectl gh issue list [gh options...]
  basectl gh issue create [--category <bug|enhancement|documentation|ci|security>] --title <title> [--body <body>] [--repo <owner/name>] [--assignee <login>|--no-assignee] [--size <T|S|M|L>] [--allow-cross-repo] [project options...]
  basectl gh issue readiness <number> [--repo <owner/name>] [--project-owner <login> --project-number <number>] [--format <text|json>]
  basectl gh issue start <number> [--category <bug|enhancement|documentation|ci|security>] [--title <title>] [--repo <owner/name>|-R <owner/name>]
  basectl gh pr create [--no-fixes] [gh options...]
  basectl gh pr status [gh options...]
  basectl gh pr checks [gh options...]
  basectl gh pr ready [gh options...]
  basectl gh pr merge [gh options...]
  basectl gh project doctor --project <title> [--owner <login>] [--schema base-project]
  basectl gh project configure --project <title> [--owner <login>] [--repo <owner/name>] [--schema base-project] [--config <path>] [--copy-fields-from <title>] [--replace-project] [--initiative-option <name>] [--dry-run]
  basectl gh project issue set-fields <number> --project <title> [--owner <login>] [--repo <owner/name>] [--allow-cross-repo] [field options...]
  basectl gh branch stale [--days <days>] [--format <text|json>]
  basectl gh branch prune [--dry-run] [--yes] [--remote] [--closed-unmerged]
  basectl gh worktree prune [--dry-run] [--yes] [--closed-unmerged]

Purpose:
  Manage GitHub issues, pull requests, Project metadata, branch naming, and
  repository hygiene using Base's opinionated workflow.

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

Issue categories:
  bug, enhancement, documentation, ci, security

Notes:
  - This command requires the GitHub CLI (`gh`) for GitHub operations.
  - `auth status` reports credential state without displaying token values.
  - `auth refresh` updates stored credentials only. Environment tokens such as
    `GH_TOKEN` take precedence and must be rotated or unset separately.
  - Issues are unassigned unless --assignee is passed or .github/base-project.yml
    sets project.issue_defaults.assignee.
  - When the GitHub repo is known, issue create also adds the issue to the
    repo-named Project and applies defaults from .github/base-project.yml.
  - Issue start resolves its issue repository from --repo/-R, then GH_REPO,
    then the origin remote.
  - PR creation auto-injects Fixes #<issue> when the branch follows the Base
    naming convention. If base_manifest.yaml declares github.pr, the generated
    body also follows that project policy. Pass --no-fixes to suppress body
    injection.
  - Pull request implementation work should happen in a dedicated worktree.
  - Branch and worktree pruning are dry-run by default and apply only when --yes is passed.
EOF
}

base_gh_auth_usage() {
    cat <<'EOF'
Usage:
  basectl gh auth status [--hostname <host>]
  basectl gh auth refresh [--hostname <host>] [--scope <scope>]... [--scopes <scope,...>] [--clipboard]

Purpose:
  Inspect GitHub authentication safely or refresh the stored credential for an
  active account.

Options:
  --hostname <host>       GitHub host. Defaults to github.com.
  --scope <scope>         Additional OAuth scope; repeat this option as needed.
  --scopes <scope,...>    Comma-separated additional OAuth scopes.
  --clipboard             Copy the one-time OAuth device code to the clipboard.
  -h, --help              Show this help text.

Notes:
  - Refresh is explicit and may open the GitHub browser/device authorization flow.
  - Refresh changes stored credentials only. GH_TOKEN/GITHUB_TOKEN (or their
    Enterprise variants) override stored credentials for the active process.
  - If the stored credential is invalid, run `gh auth login -h <host>` first.
EOF
}

base_gh_auth_environment_token_name() {
    local hostname="${1:-github.com}"

    case "$hostname" in
        github.com|*.ghe.com)
            if [[ -n "${GH_TOKEN:-}" ]]; then
                printf '%s\n' GH_TOKEN
                return 0
            fi
            if [[ -n "${GITHUB_TOKEN:-}" ]]; then
                printf '%s\n' GITHUB_TOKEN
                return 0
            fi
            ;;
        *)
            if [[ -n "${GH_ENTERPRISE_TOKEN:-}" ]]; then
                printf '%s\n' GH_ENTERPRISE_TOKEN
                return 0
            fi
            if [[ -n "${GITHUB_ENTERPRISE_TOKEN:-}" ]]; then
                printf '%s\n' GITHUB_ENTERPRISE_TOKEN
                return 0
            fi
            ;;
    esac

    return 1
}

base_gh_auth_environment_warning() {
    local hostname="${1:-github.com}"
    local token_name

    token_name="$(base_gh_auth_environment_token_name "$hostname")" || return 1
    base_std_log_warn "GitHub CLI is using $token_name from the environment. Stored credentials and 'basectl gh auth refresh' will not affect commands until this variable is unset or rotated at its source."
    return 0
}

base_gh_auth_status() {
    local hostname="${1:-github.com}"
    local output
    local status=0

    base_gh_require_command gh || return 1
    base_gh_auth_environment_warning "$hostname" || true
    output="$(gh auth status --hostname "$hostname" 2>&1)" || status=$?
    [[ -z "$output" ]] || printf '%s\n' "$output"
    ((status == 0)) && return 0

    if grep -Eqi 'lookup .*api\.[^[:space:]]+|error connecting|no such host|network' <<<"$output"; then
        base_std_log_warn "Unable to reach GitHub while checking authentication. Verify network or DNS and retry."
    elif grep -Eqi 'not logged in|invalid|failed to log in|bad credentials|401' <<<"$output"; then
        base_std_log_warn "GitHub authentication is unavailable for '$hostname'. Run 'gh auth login -h $hostname'."
    fi

    return "$status"
}

base_gh_auth_status_command() {
    local hostname="github.com"

    while (($#)); do
        case "$1" in
            --hostname)
                [[ -n "${2:-}" ]] || {
                    base_gh_usage_error base_gh_auth_usage "Option '$1' requires a host argument."
                    return $?
                }
                hostname="$2"
                shift
                ;;
            -h|--help)
                base_gh_auth_usage
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_auth_usage "Unknown auth status option '$1'."
                return $?
                ;;
        esac
        shift
    done

    base_gh_auth_status "$hostname"
}

base_gh_auth_refresh_command() {
    local hostname="github.com"
    local clipboard=0
    local scope
    local scopes_csv=""
    local token_name
    local args
    local status=0

    while (($#)); do
        case "$1" in
            --hostname)
                [[ -n "${2:-}" ]] || {
                    base_gh_usage_error base_gh_auth_usage "Option '$1' requires a host argument."
                    return $?
                }
                hostname="$2"
                shift
                ;;
            --scope)
                [[ -n "${2:-}" ]] || {
                    base_gh_usage_error base_gh_auth_usage "Option '--scope' requires a scope argument."
                    return $?
                }
                scope="$2"
                [[ -n "$scopes_csv" ]] && scopes_csv+=,
                scopes_csv+="$scope"
                shift
                ;;
            --scopes)
                [[ -n "${2:-}" ]] || {
                    base_gh_usage_error base_gh_auth_usage "Option '--scopes' requires a scope argument."
                    return $?
                }
                [[ -n "$scopes_csv" ]] && scopes_csv+=,
                scopes_csv+="$2"
                shift
                ;;
            --clipboard)
                clipboard=1
                ;;
            -h|--help)
                base_gh_auth_usage
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_auth_usage "Unknown auth refresh option '$1'."
                return $?
                ;;
        esac
        shift
    done

    token_name="$(base_gh_auth_environment_token_name "$hostname")" || true
    if [[ -n "$token_name" ]]; then
        base_gh_error "Cannot refresh the stored GitHub credential while $token_name is set."
        base_std_log_warn "Unset $token_name for this process or rotate the environment token at its source, then retry."
        return 2
    fi

    base_gh_require_command gh || return 1
    args=(auth refresh --hostname "$hostname")
    [[ -z "$scopes_csv" ]] || args+=(--scopes "$scopes_csv")
    ((clipboard)) && args+=(--clipboard)
    base_cli_gh_run "${args[@]}" || status=$?
    ((status == 0)) || return "$status"
    printf "GitHub credentials refreshed for '%s'.\n" "$hostname"
}

base_gh_do_auth() {
    local command="${1:-}"
    shift || true

    case "$command" in
        status)
            base_gh_auth_status_command "$@"
            ;;
        refresh)
            base_gh_auth_refresh_command "$@"
            ;;
        -h|--help|help|"")
            base_gh_auth_usage
            ;;
        *)
            base_gh_usage_error base_gh_auth_usage "Unknown gh auth command '$command'."
            return $?
            ;;
    esac
}

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

base_gh_project_usage() {
    cat <<'EOF'
Usage:
  basectl gh project doctor --project <title> [--owner <login>] [--schema base-project]
  basectl gh project configure --project <title> [--owner <login>] [--repo <owner/name>] [--schema base-project] [--config <path>] [--copy-fields-from <title>] [--replace-project] [--initiative-option <name>] [--dry-run]
  basectl gh project issue set-fields <number> --project <title> [--owner <login>] [--repo <owner/name>] [--allow-cross-repo] [field options...]

Purpose:
  Diagnose, configure, and update GitHub Project metadata for Base-managed repositories.

Notes:
  - Project operations delegate to Base's Python Project engine.
  - Use project issue set-fields to move issue cards through Backlog, In Progress, In Review, and Done.
  - Use --replace-project to replace a nonstandard repo Project from base-project-template.
    Already-standard Projects are left intact.
EOF
}

base_gh_project_leaf_usage() {
    local project_command="$1"

    case "$project_command" in
        doctor)
            cat <<'EOF'
Usage:
  basectl gh project doctor --project <title> [options]

Purpose:
  Inspect GitHub Project metadata against the Base Project schema.

Options:
  --project <title>  Project title to inspect.
  --owner <login>    Project owner.
  --schema base-project  Project schema. This is the only supported value.
  -h, --help         Show this help text.
EOF
            ;;
        configure)
            cat <<'EOF'
Usage:
  basectl gh project configure --project <title> [options]

Purpose:
  Create or repair Base-managed GitHub Project metadata.

Options:
  --project <title>           Project title to configure.
  --owner <login>             Project owner.
  --repo <owner/name>         Repository to link and backfill.
  --schema base-project       Project schema. This is the only supported value.
  --config <path>             Project intake config.
  --copy-fields-from <title>  Copy missing field values from another Project.
  --replace-project           Replace a nonstandard repository Project.
  --initiative-option <name>  Initiative option to seed.
  --dry-run                   Print planned changes.
  -h, --help                  Show this help text.
EOF
            ;;
        *)
            return 1
            ;;
    esac
}

base_gh_project_issue_set_fields_usage() {
    cat <<'EOF'
Usage:
  basectl gh project issue set-fields <number> --project <title> --repo <owner/name> [--owner <login>] [--config <path>] [--allow-cross-repo] [--status <name>] [--priority <name>] [--area <name>] [--initiative <name>] [--size <T|S|M|L>] [--dry-run]

Purpose:
  Add or update Base Project field values for a GitHub issue.

Options:
  --project <title>     Project title to update.
  --repo <owner/name>   Repository containing the issue. Defaults to the origin remote when available.
  --owner <login>       Project owner. Defaults to the repository owner or Git remote owner.
  --config <path>       Project intake config for issue defaults and repository-specific options.
  --allow-cross-repo    Explicitly allow updating a Project that is not linked to the issue repository.
  --status <name>       Status option, such as Backlog, In Progress, In Review, or Done.
  --priority <name>     Priority option, such as P0, P1, P2, or P3.
  --area <name>         Area option.
  --initiative <name>   Initiative option.
  --size <T|S|M|L>      Size option.
  --dry-run             Print the planned Project updates without applying them.
  -h, --help            Show this help text.
EOF
}

base_gh_branch_usage() {
    cat <<'EOF'
Usage:
  basectl gh branch stale [--days <days>] [--format <text|json>]
  basectl gh branch prune [--dry-run] [--yes] [--remote] [--closed-unmerged]

Purpose:
  Inspect stale branches and prune merged local or GitHub branches.

Note:
  Runs in dry-run mode by default. Pass --yes to apply changes.
  --dry-run and --yes are mutually exclusive; choose one when overriding the default.

Options:
  stale: --days <days>, --format <text|json>
  prune: --dry-run, --yes, --remote, --closed-unmerged
  -h, --help     Show this help text.
EOF
}

base_gh_branch_leaf_usage() {
    local branch_command="$1"

    case "$branch_command" in
        stale)
            cat <<'EOF'
Usage:
  basectl gh branch stale [--days <days>] [--format <text|json>]

Purpose:
  Report local and origin branches older than the selected threshold.

Options:
  --days <days>        Minimum age in days. Defaults to 30.
  --format <text|json> Select human text or stable inspection JSON.
  -h, --help          Show this help text.
EOF
            ;;
        prune)
            cat <<'EOF'
Usage:
  basectl gh branch prune [options]

Purpose:
  Preview or remove safely merged local and GitHub branches.

Options:
  --dry-run          Preview branches that would be deleted (default).
  --yes              Delete selected branches after preview.
  --remote           Also clean selected GitHub branches and stale origin refs.
  --closed-unmerged  Include branches whose PRs were closed without merging.
  -h, --help         Show this help text.
EOF
            ;;
        *)
            return 1
            ;;
    esac
}

base_gh_worktree_usage() {
    cat <<'EOF'
Usage:
  basectl gh worktree prune [--dry-run] [--yes] [--closed-unmerged]

Purpose:
  Prune safe merged worktrees and explicitly selected closed-unmerged worktrees.

Note:
  Runs in dry-run mode by default. Pass --yes to apply changes.
  --dry-run and --yes are mutually exclusive; choose one when overriding the default.

Options:
  --dry-run          Preview worktrees that would be removed (default).
  --yes              Remove selected worktrees after preview.
  --closed-unmerged  Include clean worktrees tied to closed, unmerged PRs.
  -h, --help         Show this help text.
EOF
}

base_gh_error() {
    base_std_print_error "$*"
}

base_gh_usage_error() {
    local usage_function="$1"
    shift

    base_gh_error "$*"
    "$usage_function" >&2
    return 2
}

base_gh_require_command() {
    local command="$1"
    local command_path

    if [[ "$command" == "gh" ]]; then
        base_gh_require_cli
        return $?
    fi

    base_std_command_path command_path "$command" && [[ -n "$command_path" ]] || {
        base_gh_error "Required command '$command' was not found on PATH."
        return 1
    }
}

base_gh_run() {
    local status=0

    base_gh_require_cli || return 1
    gh "$@" || status=$?
    ((status == 0)) && return 0

    base_gh_report_command_failure "$status" "$@" || true
    base_gh_auth_environment_warning github.com || true
    if [[ "${1:-}" == project ]]; then
        base_std_log_warn "GitHub Project operations require the 'project' scope for stored OAuth credentials."
        base_std_log_warn "Run 'basectl gh auth refresh --scope project' if the stored credential is active."
    fi

    return "$status"
}

base_cli_gh_run() {
    base_gh_run "$@"
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
    local base_default_branch repo_root

    repo_root="$(git rev-parse --show-toplevel 2>/dev/null || printf '.')"
    if base_git_detect_default_branch "$repo_root" base_default_branch; then
        printf '%s\n' "$base_default_branch"
        return 0
    fi

    printf '%s\n' main
}

base_gh_validate_category() {
    local category="$1"

    base_github_branch_category_is_valid "$category" && return 0
    base_gh_error "Invalid category '$category'. Expected one of: bug, enhancement, documentation, ci, security."
    return 2
}

base_gh_slug() {
    local input="$1"
    local char
    local i
    local previous_dash=1
    local slug=""

    input="${input,,}"
    for ((i = 0; i < ${#input}; i++)); do
        char="${input:i:1}"
        case "$char" in
            [a-z0-9])
                slug+="$char"
                previous_dash=0
                ;;
            *)
                if ((previous_dash == 0)); then
                    slug+="-"
                    previous_dash=1
                fi
                ;;
        esac
    done
    while [[ "$slug" == *- ]]; do
        slug="${slug%-}"
    done
    if [[ -z "$slug" ]]; then
        slug="work"
    fi
    slug="${slug:0:60}"
    while [[ "$slug" == *- ]]; do
        slug="${slug%-}"
    done
    [[ -n "$slug" ]] || slug="work"
    printf '%s\n' "$slug"
}

base_gh_issue_worktree_path() {
    local issue="$1" slug="$2"
    local repo_root repo_name repo_parent slug_short

    repo_root="$(git rev-parse --show-toplevel)" || return 1
    repo_name="$(basename "$repo_root")"
    repo_parent="$(dirname "$repo_root")"
    slug_short="${slug:0:40}"
    while [[ "$slug_short" == *- ]]; do
        slug_short="${slug_short%-}"
    done
    [[ -n "$slug_short" ]] || slug_short="work"

    printf '%s/%s-worktrees/%s-%s\n' "$repo_parent" "$repo_name" "$issue" "$slug_short"
}

base_gh_issue_category() {
    local category
    local issue="$2"
    local repo="$1"
    local status

    category="$(base_github_issue_category "$repo" "$issue")"
    status=$?
    case "$status" in
        0)
            printf '%s\n' "$category"
            ;;
        2)
            base_gh_error "GitHub issue #$issue in '$repo' must have exactly one category label: bug, enhancement, documentation, ci, or security."
            return 2
            ;;
        3)
            base_gh_error "GitHub reference #$issue in '$repo' is a pull request, not an issue."
            return 2
            ;;
        *)
            base_gh_error "Unable to determine the category label for GitHub issue #$issue in '$repo'. Confirm that the issue exists and is accessible."
            return 1
            ;;
    esac
}

base_gh_issue_title() {
    local issue="$1"
    local repo="$2"

    base_github_issue_title "$repo" "$issue"
}

base_gh_issue_labels() {
    local issue="$1"
    local repo="$2"

    base_github_issue_labels "$repo" "$issue" 2>/dev/null || true
}


base_gh_pr_changed_paths() {
    local default_branch base_ref candidate

    default_branch="$(base_gh_default_branch)"
    for candidate in "origin/$default_branch" "$default_branch"; do
        if git rev-parse --verify --quiet "$candidate^{commit}" >/dev/null; then
            base_ref="$candidate"
            break
        fi
    done
    [[ -n "${base_ref:-}" ]] || return 0
    git diff --name-only "$base_ref"...HEAD
}

base_gh_infer_github_repo() {
    local github_repo repo_root

    repo_root="$(git rev-parse --show-toplevel 2>/dev/null || printf '.')"
    base_gh_infer_repo_from_origin "$repo_root" github_repo || return 1

    printf '%s\n' "$github_repo"
}

base_gh_normalize_github_repo() {
    local repo="$1"

    if [[ "$repo" == */*/* ]]; then
        repo="${repo#*/}"
    fi
    [[ "$repo" =~ ^[^/[:space:]]+/[^/[:space:]]+$ ]] || return 1
    printf '%s\n' "$repo"
}

base_gh_pr_target_repo() {
    local repo="${GH_REPO:-}"

    while (($#)); do
        case "$1" in
            --repo|-R)
                shift
                (($#)) || return 2
                repo="$1"
                ;;
            --repo=*|-R=*)
                repo="${1#*=}"
                [[ -n "$repo" ]] || return 2
                ;;
        esac
        shift
    done

    if [[ -z "$repo" ]]; then
        repo="$(base_gh_infer_github_repo)" || return 1
    fi
    base_gh_normalize_github_repo "$repo"
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

base_gh_manifest_path() {
    local root path

    root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    [[ -n "$root" ]] || return 1
    path="$root/base_manifest.yaml"
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
    BASE_CLI_DISPLAY_COMMAND="basectl gh" "$wrapper" --project base base_github_projects project issue set-fields "$@"
}

base_gh_project_issue_defaults() {
    local wrapper="${BASE_GH_PROJECT_WRAPPER:-$BASE_HOME/bin/base-wrapper}"

    [[ -x "$wrapper" ]] || {
        base_gh_error "Base Python wrapper '$wrapper' is missing or is not executable."
        return 1
    }
    BASE_CLI_DISPLAY_COMMAND="basectl gh" "$wrapper" --project base base_github_projects project issue defaults "$@"
}

base_gh_issue_default_from_config() {
    local path="$1" key="$2"
    local default_key default_value

    while IFS=$'\t' read -r default_key default_value; do
        [[ "$default_key" == "$key" && -n "$default_value" ]] || continue
        printf '%s\n' "$default_value"
        return 0
    done < <(base_gh_project_issue_defaults --config "$path")

    return 1
}

base_gh_issue_default_assignee_from_config() {
    base_gh_issue_default_from_config "$1" assignee
}

base_gh_join_csv() {
    local joined=""
    # shellcheck disable=SC2034 # Passed by name to base_str_join.
    local values=("$@")

    base_str_join joined ", " values
    printf '%s\n' "$joined"
}

base_gh_project_field_summary() {
    local project_title="$1" config_path="$2" project_size="$3"
    local status="" priority="" size="" area="" initiative=""
    local fields=()

    if [[ -n "$config_path" ]]; then
        status="$(base_gh_issue_default_from_config "$config_path" status || true)"
        priority="$(base_gh_issue_default_from_config "$config_path" priority || true)"
        size="$(base_gh_issue_default_from_config "$config_path" size || true)"
        area="$(base_gh_issue_default_from_config "$config_path" area || true)"
        initiative="$(base_gh_issue_default_from_config "$config_path" initiative || true)"
    else
        status="Backlog"
        priority="P2"
        size="${project_size:-S}"
    fi
    if [[ -n "$project_size" ]]; then
        size="$project_size"
    fi

    [[ -n "$status" ]] && fields+=("Status=$status")
    [[ -n "$priority" ]] && fields+=("Priority=$priority")
    [[ -n "$size" ]] && fields+=("Size=$size")
    [[ -n "$area" ]] && fields+=("Area=$area")
    [[ -n "$initiative" ]] && fields+=("Initiative=$initiative")

    if ((${#fields[@]})); then
        printf "Project '%s': %s applied.\n" "$project_title" "$(base_gh_join_csv "${fields[@]}")"
    else
        printf "Project '%s': fields applied.\n" "$project_title"
    fi
}

base_gh_project_issue_set_fields_command() {
    printf 'basectl gh project issue set-fields'
    printf ' %q' "$@"
    printf '\n'
}

base_gh_apply_project_issue_fields() {
    local project_title="$1" config_path="$2" project_size="$3"
    local output status line
    shift 3

    output="$(base_gh_project_issue_set_fields "$@" 2>&1)"
    status=$?
    if ((status == 0)); then
        if [[ -n "$output" ]]; then
            printf '%s\n' "$output"
        fi
        base_gh_project_field_summary "$project_title" "$config_path" "$project_size"
        return 0
    fi

    if [[ -n "$output" ]]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ -n "$line" ]] && base_std_log_warn "$line"
        done <<<"$output"
    fi
    base_std_log_warn "Project field update failed. Set fields manually or rerun:"
    base_std_log_warn "$(base_gh_project_issue_set_fields_command "$@")"
    return "$status"
}

base_gh_pr_policy_body() {
    local issue="$1"
    local github_repo="$2"
    local manifest wrapper label path
    local policy_args=()

    manifest="$(base_gh_manifest_path || true)"
    if [[ -z "$manifest" ]]; then
        printf 'Fixes #%s\n' "$issue"
        return 0
    fi

    wrapper="${BASE_GH_PYTHON_WRAPPER:-${BASE_GH_PROJECT_WRAPPER:-$BASE_HOME/bin/base-wrapper}}"
    [[ -x "$wrapper" ]] || {
        printf 'Fixes #%s\n' "$issue"
        return 0
    }

    policy_args=(--project base base_pr_policy body --manifest "$manifest" --issue "$issue")
    while IFS= read -r label || [[ -n "$label" ]]; do
        [[ -n "$label" ]] && policy_args+=(--label "$label")
    done < <(base_gh_issue_labels "$issue" "$github_repo")
    while IFS= read -r path || [[ -n "$path" ]]; do
        [[ -n "$path" ]] && policy_args+=(--path "$path")
    done < <(base_gh_pr_changed_paths)

    "$wrapper" "${policy_args[@]}"
}

base_gh_validate_project_size() {
    local size="$1"

    case "$size" in
        T|S|M|L)
            return 0
            ;;
    esac
    base_gh_error "Invalid size '$size'. Expected one of: T, S, M, L."
    return 2
}

base_gh_current_issue_from_branch() {
    local branch

    branch="$(git branch --show-current 2>/dev/null)" || return 1
    base_github_issue_from_branch_name "$branch"
}

base_gh_do_issue() {
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
            --assignee)
                assignee="${2:-}"
                assignee_explicit=1
                shift
                ;;
            --no-assignee)
                no_assignee=1
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
            --allow-cross-repo)
                allow_cross_repo=1
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
        shift
    done

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
            base_gh_apply_project_issue_fields "$project_title" "$config_path" "$project_size" "${field_args[@]}" || return $?
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
            base_gh_apply_project_issue_fields "$project_title" "" "$project_size" "${field_args[@]}" || return $?
        fi
    fi
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

base_gh_issue_start() {
    local issue="${1:-}" category="" issue_category="" github_repo="" title="" slug branch default_branch worktree_path
    local option_value
    local repo_args=()
    local parser_args=()
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

base_gh_do_pr() {
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

base_gh_do_project() {
    local wrapper="${BASE_GH_PROJECT_WRAPPER:-$BASE_HOME/bin/base-wrapper}"

    if [[ "${1:-}" == "issue" && "${2:-}" == "set-fields" ]] && base_gh_args_request_help "$@"; then
        base_gh_project_issue_set_fields_usage
        return 0
    fi
    if [[ "${1:-}" == doctor || "${1:-}" == configure ]] && base_gh_args_request_help "$@"; then
        base_gh_project_leaf_usage "$1"
        return $?
    fi
    if base_gh_args_request_help "$@"; then
        base_gh_project_usage
        return 0
    fi

    base_gh_auth_environment_warning github.com || true

    [[ -x "$wrapper" ]] || {
        base_gh_error "Base Python wrapper '$wrapper' is missing or is not executable."
        return 1
    }
    BASE_CLI_DISPLAY_COMMAND="basectl gh" "$wrapper" --project base base_github_projects project "$@"
}

base_gh_subcommand_main() {
    local area="${1:-}"
    shift || true

    case "$area" in
        auth) base_gh_do_auth "$@" ;;
        issue) base_gh_do_issue "$@" ;;
        pr) base_gh_do_pr "$@" ;;
        project) base_gh_do_project "$@" ;;
        branch) base_gh_do_branch "$@" ;;
        worktree) base_gh_do_worktree "$@" ;;
        -h|--help|help|"") base_gh_usage ;;
        *)
            base_gh_usage_error base_gh_usage "Unknown gh area '$area'."
            return $?
            ;;
    esac
}
