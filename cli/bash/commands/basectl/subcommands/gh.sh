#!/usr/bin/env bash

[[ -n "${_base_gh_subcommand_sourced:-}" ]] && return 0
_base_gh_subcommand_sourced=1
readonly _base_gh_subcommand_sourced

import_base_lib git/lib_git.sh
import_base_lib gh/lib_gh.sh
import_base_lib str/lib_str.sh

source "$BASE_HOME/cli/bash/commands/basectl/subcommands/github_policy.sh"
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh_branch_worktree.sh"

base_gh_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue list [gh options...]
  basectl gh issue create [--category <bug|enhancement|documentation|ci|security>] --title <title> [--body <body>] [--repo <owner/name>] [--assignee <login>|--no-assignee] [--size <T|S|M|L>] [project options...]
  basectl gh issue readiness <number> [--repo <owner/name>] [--project-owner <login> --project-number <number>]
  basectl gh issue start <number> [--category <bug|enhancement|documentation|ci|security>] [--title <title>] [--repo <owner/name>|-R <owner/name>]
  basectl gh pr create [--no-fixes] [gh options...]
  basectl gh pr status [gh options...]
  basectl gh pr checks [gh options...]
  basectl gh pr ready [gh options...]
  basectl gh pr merge [gh options...]
  basectl gh project doctor --project <title> [--owner <login>] [--schema base-project]
  basectl gh project configure --project <title> [--owner <login>] [--repo <owner/name>] [--schema base-project] [--config <path>] [--copy-fields-from <title>] [--replace-project] [--initiative-option <name>] [--dry-run]
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
  --assignee <login>            Assign the issue to a GitHub login.
  --no-assignee                 Do not assign the issue, even when repo config has a default.
  --project <title>             Project to update. Defaults to the repository name.
  --project-owner <login>       Project owner. Defaults to the repository owner.
  --size <T|S|M|L>              Project Size value. Defaults to .github/base-project.yml or S.
  --no-project                  Skip Project metadata updates.

Issue categories:
  bug, enhancement, documentation, ci, security

Notes:
  - This command requires the GitHub CLI (`gh`) for GitHub operations.
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

base_gh_issue_usage() {
    cat <<'EOF'
Usage:
  basectl gh issue list [gh options...]
  basectl gh issue create [--category <bug|enhancement|documentation|ci|security>] --title <title> [--body <body>] [--repo <owner/name>] [--assignee <login>|--no-assignee] [--size <T|S|M|L>] [project options...]
  basectl gh issue readiness <number> [--repo <owner/name>] [--project-owner <login> --project-number <number>]
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

Issue readiness options:
  --repo <owner/name>           Repository containing the issue. Defaults to the origin remote.
  --project-owner <login>       Project owner for Project field validation.
  --project-number <number>     Project number for Project field validation.

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

base_gh_project_usage() {
    cat <<'EOF'
Usage:
  basectl gh project doctor --project <title> [--owner <login>] [--schema base-project]
  basectl gh project configure --project <title> [--owner <login>] [--repo <owner/name>] [--schema base-project] [--config <path>] [--copy-fields-from <title>] [--replace-project] [--initiative-option <name>] [--dry-run]
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

base_gh_project_issue_set_fields_usage() {
    cat <<'EOF'
Usage:
  basectl gh project issue set-fields <number> --project <title> --repo <owner/name> [--owner <login>] [--config <path>] [--status <name>] [--priority <name>] [--area <name>] [--initiative <name>] [--size <T|S|M|L>] [--dry-run]

Purpose:
  Add or update Base Project field values for a GitHub issue.

Options:
  --project <title>     Project title to update.
  --repo <owner/name>   Repository containing the issue. Defaults to the origin remote when available.
  --owner <login>       Project owner. Defaults to the repository owner or Git remote owner.
  --config <path>       Project intake config for issue defaults and repository-specific options.
  --status <name>       Status option, such as Backlog, In Progress, In Review, or Done.
  --priority <name>     Priority option, such as P0, P1, P2, or P3.
  --area <name>         Area option.
  --initiative <name>   Initiative option.
  --size <T|S|M|L>      Size option.
  --dry-run             Print the planned Project updates without applying them.
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

base_gh_usage_error() {
    local usage_function="$1"
    shift

    base_gh_error "$*"
    "$usage_function" >&2
    return 2
}

base_gh_require_command() {
    local command="$1"

    if [[ "$command" == "gh" ]]; then
        gh_require_cli
        return $?
    fi

    command -v "$command" >/dev/null 2>&1 || {
        base_gh_error "Required command '$command' was not found on PATH."
        return 1
    }
}

base_gh_auth_status_diagnostics() {
    gh_auth_status_diagnostics
}

base_gh_report_command_failure() {
    local status="$1"
    shift

    gh_report_command_failure "$status" "$@"
}

base_gh_run() {
    gh_run "$@"
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
    if git_detect_default_branch "$repo_root" base_default_branch; then
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

base_gh_issue_readiness_required_sections() {
    printf '%s\n' \
        "Goal" \
        "Background" \
        "Scope" \
        "Acceptance Criteria" \
        "Validation" \
        "Non-Goals" \
        "Project Fields" \
        "Agent Assignment"
}

base_gh_issue_readiness_required_project_fields() {
    printf '%s\n' Status Priority Size Area Initiative
}

base_gh_issue_readiness_has_section() {
    local section="$1"

    awk -v section="$section" '
        /^##[[:space:]]+/ {
            heading = $0
            sub(/^##[[:space:]]+/, "", heading)
            sub(/[[:space:]]+$/, "", heading)
            in_section = (heading == section)
            next
        }
        in_section && $0 !~ /^[[:space:]]*$/ {
            found = 1
        }
        END {
            exit(found ? 0 : 1)
        }
    '
}

base_gh_lines_to_csv() {
    local line
    local values=()

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -n "$line" ]] && values+=("$line")
    done

    if ((${#values[@]})); then
        base_gh_join_csv "${values[@]}"
    else
        printf 'none\n'
    fi
}

base_gh_jq_string_literal() {
    local value="$1"

    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    printf '"%s"\n' "$value"
}

base_gh_issue_readiness_project_row() {
    local issue="$1" repo="$2" project_owner="$3" project_number="$4"
    local repo_literal query

    repo_literal="$(base_gh_jq_string_literal "$repo")"
    query=".items[] | select((.content.number == $issue) and (.content.repository == $repo_literal)) | [.status // \"\", .priority // \"\", .size // \"\", .area // \"\", .initiative // \"\"] | join(\"\u001f\")"
    base_gh_run project item-list "$project_number" --owner "$project_owner" --format json --limit 1000 --jq "$query"
}

base_gh_issue_readiness() {
    local issue="${1:-}"
    local assignees_output="" assignees_summary=""
    local body="" labels_output="" labels_summary=""
    local github_repo=""
    local issue_ready_state="ready"
    local project_number="" project_owner=""
    local project_row="" project_status="" project_priority="" project_size="" project_area="" project_initiative=""
    local project_validation_requested=0
    local section field
    local missing_project_fields=()
    local missing_sections=()

    [[ -n "$issue" ]] || {
        base_gh_usage_error base_gh_issue_usage "Missing issue number."
        return $?
    }
    if [[ "$issue" == "help" || "$issue" == "-h" || "$issue" == "--help" ]]; then
        base_gh_issue_usage
        return 0
    fi
    [[ "$issue" =~ ^[0-9]+$ ]] || {
        base_gh_usage_error base_gh_issue_usage "Invalid issue number '$issue'."
        return $?
    }
    shift

    while (($#)); do
        case "$1" in
            --repo)
                github_repo="${2:-}"
                [[ -n "$github_repo" ]] || {
                    base_gh_usage_error base_gh_issue_usage "Option '--repo' requires an argument."
                    return $?
                }
                shift
                ;;
            --project-owner)
                project_owner="${2:-}"
                [[ -n "$project_owner" ]] || {
                    base_gh_usage_error base_gh_issue_usage "Option '--project-owner' requires an argument."
                    return $?
                }
                project_validation_requested=1
                shift
                ;;
            --project-number)
                project_number="${2:-}"
                [[ -n "$project_number" ]] || {
                    base_gh_usage_error base_gh_issue_usage "Option '--project-number' requires an argument."
                    return $?
                }
                [[ "$project_number" =~ ^[0-9]+$ ]] || {
                    base_gh_usage_error base_gh_issue_usage "Invalid project number '$project_number'."
                    return $?
                }
                project_validation_requested=1
                shift
                ;;
            -h|--help)
                base_gh_issue_usage
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_issue_usage "Unknown option '$1'."
                return $?
                ;;
        esac
        shift
    done

    if ((project_validation_requested)) && { [[ -z "$project_owner" ]] || [[ -z "$project_number" ]]; }; then
        base_gh_usage_error base_gh_issue_usage "Options '--project-owner' and '--project-number' must be used together."
        return $?
    fi

    [[ -n "$github_repo" ]] || github_repo="$(base_gh_infer_github_repo || true)"
    [[ -n "$github_repo" ]] || {
        base_gh_usage_error base_gh_issue_usage "Unable to infer GitHub repository. Pass --repo <owner/name>."
        return $?
    }

    body="$(base_gh_run issue view "$issue" --repo "$github_repo" --json body --jq .body)" || return $?
    labels_output="$(base_gh_run issue view "$issue" --repo "$github_repo" --json labels --jq '.labels[].name')" || return $?
    assignees_output="$(base_gh_run issue view "$issue" --repo "$github_repo" --json assignees --jq '.assignees[].login')" || return $?

    while IFS= read -r section || [[ -n "$section" ]]; do
        [[ -n "$section" ]] || continue
        if ! base_gh_issue_readiness_has_section "$section" <<<"$body"; then
            missing_sections+=("$section")
        fi
    done < <(base_gh_issue_readiness_required_sections)

    if ((project_validation_requested)); then
        project_row="$(base_gh_issue_readiness_project_row "$issue" "$github_repo" "$project_owner" "$project_number")" || return $?
        if [[ -z "$project_row" ]]; then
            missing_project_fields=("Project item")
            while IFS= read -r field || [[ -n "$field" ]]; do
                [[ -n "$field" ]] && missing_project_fields+=("$field")
            done < <(base_gh_issue_readiness_required_project_fields)
        else
            IFS=$'\037' read -r project_status project_priority project_size project_area project_initiative <<<"$project_row"
            [[ -n "$project_status" ]] || missing_project_fields+=("Status")
            [[ -n "$project_priority" ]] || missing_project_fields+=("Priority")
            [[ -n "$project_size" ]] || missing_project_fields+=("Size")
            [[ -n "$project_area" ]] || missing_project_fields+=("Area")
            [[ -n "$project_initiative" ]] || missing_project_fields+=("Initiative")
        fi
    fi

    labels_summary="$(base_gh_lines_to_csv <<<"$labels_output")"
    assignees_summary="$(base_gh_lines_to_csv <<<"$assignees_output")"

    if ((${#missing_sections[@]} || ${#missing_project_fields[@]})); then
        issue_ready_state="not ready"
    elif ((!project_validation_requested)); then
        issue_ready_state="partial"
    fi

    printf 'Issue #%s readiness: %s\n' "$issue" "$issue_ready_state"
    printf 'Repository: %s\n' "$github_repo"
    if ((${#missing_sections[@]})); then
        printf 'Body sections: missing %s\n' "$(base_gh_join_csv "${missing_sections[@]}")"
    else
        printf 'Body sections: ok\n'
    fi
    if ((project_validation_requested)); then
        if ((${#missing_project_fields[@]})); then
            printf 'Project fields: missing %s\n' "$(base_gh_join_csv "${missing_project_fields[@]}")"
        else
            printf 'Project fields: ok\n'
        fi
    else
        printf 'Project fields: skipped\n'
        printf 'Pass --project-owner and --project-number to validate Project fields.\n'
    fi
    printf 'Labels: %s\n' "$labels_summary"
    printf 'Assignees: %s\n' "$assignees_summary"

    if ((${#missing_sections[@]})); then
        printf 'Fix hint: add non-empty ## sections for the missing issue context.\n'
    fi
    if ((${#missing_project_fields[@]})); then
        printf 'Fix hint: set missing Project fields before assigning implementation work.\n'
    fi

    [[ "$issue_ready_state" == "ready" ]]
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
    gh_infer_repo_from_origin "$repo_root" github_repo || return 1

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
    # shellcheck disable=SC2034 # Passed by name to str_join.
    local values=("$@")

    str_join joined ", " values
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
            [[ -n "$line" ]] && log_warn "$line"
        done <<<"$output"
    fi
    log_warn "Project field update failed. Set fields manually or rerun:"
    log_warn "$(base_gh_project_issue_set_fields_command "$@")"
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
                base_gh_issue_usage
                return 0
            fi
            base_gh_run issue list "$@"
            ;;
        create)
            base_gh_issue_create "$@"
            ;;
        readiness)
            base_gh_issue_readiness "$@"
            ;;
        start)
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
            -h|--help)
                base_gh_issue_usage
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
    issue_output="$(base_gh_run "${issue_args[@]}")" || return $?
    printf '%s\n' "$issue_output"

    if ((configure_project)) && [[ -n "$github_repo" ]]; then
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
        std_make_temp_file body_file basectl-gh-pr || return 1
        base_gh_pr_policy_body "$issue" "$github_repo" > "$body_file" || {
            status=$?
            rm -f "$body_file"
            return "$status"
        }
        printf 'Auto-linking PR to issue #%s from branch name. Pass --no-fixes to suppress.\n' "$issue"
        base_gh_run pr create --fill --body-file "$body_file" "${passthrough[@]}"
        status=$?
        rm -f "$body_file"
        return "$status"
    fi
    base_gh_run pr create --fill "${passthrough[@]}"
}

base_gh_issue_start() {
    local issue="${1:-}" category="" issue_category="" github_repo="" title="" slug branch default_branch worktree_path
    local repo_args=()
    local status

    [[ -n "$issue" ]] || {
        base_gh_usage_error base_gh_issue_usage "Missing issue number."
        return $?
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
            --repo|-R)
                if (($# < 2)) || [[ -z "$2" || "$2" == -* ]]; then
                    base_gh_usage_error base_gh_issue_usage "Option '$1' requires a repository argument."
                    return $?
                fi
                repo_args+=("$1" "$2")
                shift
                ;;
            --repo=*|-R=*)
                if [[ -z "${1#*=}" ]]; then
                    base_gh_usage_error base_gh_issue_usage "Option '${1%%=*}' requires a repository argument."
                    return $?
                fi
                repo_args+=("$1")
                ;;
            -h|--help)
                base_gh_issue_usage
                return 0
                ;;
            *)
                base_gh_usage_error base_gh_issue_usage "Unknown option '$1'."
                return $?
                ;;
        esac
        shift
    done

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
    if base_gh_args_request_help "$@"; then
        base_gh_project_usage
        return 0
    fi

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
