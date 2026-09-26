#!/usr/bin/env bash

[[ -n "${_base_repo_pr_sourced:-}" ]] && return 0
_base_repo_pr_sourced=1
readonly _base_repo_pr_sourced

if ! declare -F base_repo_pretty_arg >/dev/null 2>&1; then
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo.sh
    source "$BASE_HOME/cli/bash/commands/basectl/subcommands/repo.sh"
fi

base_repo_pr_branch_name() {
    local category="$1"
    local issue="$2"
    local kind="$3"
    local name="${4,,}"
    local slug

    name="${name//[._]/-}"
    while [[ "$name" == *--* ]]; do
        name="${name//--/-}"
    done
    while [[ "$name" == *- ]]; do
        name="${name%-}"
    done
    slug="$kind-$name"

    base_github_branch_name "$category" "$issue" "$slug"
}

base_repo_pr_issue_category() {
    local category
    local issue="$2"
    local repo="$1"
    local status

    base_repo_require_gh || return 1
    category="$(base_github_issue_category "$repo" "$issue")"
    status=$?
    case "$status" in
        0)
            printf '%s\n' "$category"
            ;;
        2)
            base_std_log_error "GitHub issue #$issue in '$repo' must have exactly one category label: bug, enhancement, documentation, ci, or security."
            return 1
            ;;
        *)
            base_std_log_error "Unable to determine the category label for GitHub issue #$issue in '$repo'."
            return 1
            ;;
    esac
}

base_repo_print_pr_worktree_root_hint() {
    local command_label="$1"
    local provided_path="$2"
    local repository_root="$3"

    if [[ "$command_label" == "repo init --pr" ]]; then
        base_std_log_error "repo init --pr expects --path to point at the repository root."
    else
        base_std_log_error "$command_label expects the target path to point at the repository root."
    fi
    printf "  Provided path: %s\n" "$provided_path" >&2
    printf "  Repository root: %s\n" "$repository_root" >&2
    if [[ "$command_label" == "repo init --pr" ]]; then
        printf "  Fix: pass --path %s\n" "$(base_repo_pretty_arg "$repository_root")" >&2
    else
        printf "  Fix: pass %s as the target path.\n" "$(base_repo_pretty_arg "$repository_root")" >&2
    fi
}

base_repo_print_pr_worktree_dirty_hint() {
    local dirty_count=0
    local dirty_word
    local line
    local root="$1"
    local shown_count=0
    local status_output="$2"

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -n "$line" ]] || continue
        dirty_count=$((dirty_count + 1))
    done <<< "$status_output"

    dirty_word="files"
    [[ "$dirty_count" == "1" ]] && dirty_word="file"

    printf "  Uncommitted changes detected (%d %s).\n" "$dirty_count" "$dirty_word" >&2
    printf "  Dirty paths:\n" >&2
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -n "$line" ]] || continue
        if ((shown_count >= 5)); then
            break
        fi
        printf "    %s\n" "$line" >&2
        shown_count=$((shown_count + 1))
    done <<< "$status_output"
    if ((dirty_count > shown_count)); then
        printf "    ... (%d more)\n" "$((dirty_count - shown_count))" >&2
    fi
    printf "  Fix: commit or stash your changes before running this command.\n" >&2
    printf "    git -C %s status --short\n" "$(base_repo_pretty_arg "$root")" >&2
    printf "    git -C %s stash\n" "$(base_repo_pretty_arg "$root")" >&2
    printf "    git -C %s commit -am \"WIP\"\n" "$(base_repo_pretty_arg "$root")" >&2
}

base_repo_require_pr_worktree() {
    local command_label="${2:-repo init --pr}"
    local dirty_status
    local git_root
    local root="$1"

    [[ -d "$root" ]] || {
        base_std_log_error "$command_label requires '$root' to be an existing Git worktree."
        return 1
    }

    git_root="$(git -C "$root" rev-parse --show-toplevel 2>/dev/null)" || {
        base_std_log_error "$command_label requires '$root' to be an existing Git worktree."
        return 1
    }
    git_root="$(cd -- "$git_root" && pwd -P)" || return 1
    root="$(cd -- "$root" && pwd -P)" || return 1

    [[ "$git_root" == "$root" ]] || {
        base_repo_print_pr_worktree_root_hint "$command_label" "$root" "$git_root"
        return 1
    }

    dirty_status="$(git -C "$root" status --porcelain)"
    [[ -z "$dirty_status" ]] || {
        base_std_log_error "$command_label requires a clean Git worktree at '$root'."
        base_repo_print_pr_worktree_dirty_hint "$root" "$dirty_status"
        return 1
    }
}

base_repo_default_branch_for_pr() {
    local base_remote_default_branch
    local repo="$1"

    base_repo_require_gh || return 1
    if ! base_gh_repo_default_branch "$repo" base_remote_default_branch; then
        base_std_log_error "Unable to determine the default branch for GitHub repository '$repo'."
        return 1
    fi

    printf '%s\n' "$base_remote_default_branch"
}

base_repo_detect_default_branch() {
    local base_default_branch
    local root="$1"

    if base_git_detect_default_branch "$root" base_default_branch; then
        printf '%s\n' "$base_default_branch"
        return 0
    fi

    return 1
}

base_repo_prepare_pr_branch() {
    local branch="$3"
    local command_label="${5:-repo init --pr}"
    local default_branch="$4"
    local dry_run="$1"
    local root="$2"
    local start_point

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create or use branch '%s' from default branch '%s'.\n" "$branch" "$default_branch"
        return 0
    fi

    if git -C "$root" show-ref --verify --quiet "refs/heads/$branch"; then
        git -C "$root" switch "$branch" || {
            base_std_log_error "Failed to switch to branch '$branch'."
            return 1
        }
    else
        if git -C "$root" show-ref --verify --quiet "refs/heads/$default_branch"; then
            start_point="$default_branch"
        elif git -C "$root" show-ref --verify --quiet "refs/remotes/origin/$default_branch"; then
            start_point="origin/$default_branch"
        else
            base_std_log_error "Unable to find default branch '$default_branch' in '$root'."
            return 1
        fi

        git -C "$root" switch -c "$branch" "$start_point" || {
            base_std_log_error "Failed to create branch '$branch'."
            return 1
        }
    fi

    [[ -z "$(git -C "$root" status --porcelain)" ]] || {
        base_std_log_error "$command_label requires branch '$branch' to have a clean Git worktree."
        return 1
    }
}

base_repo_stage_pr_files() {
    local description="$2"
    local files=()
    local rel
    local root="$1"
    shift 2

    for rel in "$@"; do
        [[ -e "$root/$rel" ]] && files+=("$rel")
    done

    ((${#files[@]})) || {
        base_std_log_error "No $description exist to stage."
        return 1
    }

    git -C "$root" add -- "${files[@]}" || {
        base_std_log_error "Failed to stage $description."
        return 1
    }
}

base_repo_stage_pr_baseline_files() {
    local agent_ready="${2:-0}"
    local files=("${BASE_REPO_BASELINE_FILES[@]}")
    local release_contract="${3:-0}"
    local root="$1"

    if [[ "$agent_ready" == "1" ]]; then
        files+=(AGENTS.md skills.md)
    fi
    if [[ "$release_contract" == "1" ]]; then
        files+=(docs/release-process.md)
    fi

    base_repo_stage_pr_files "$root" "repository baseline files" "${files[@]}"
}

base_repo_relative_path_under_root() {
    local path="$2"
    local path_dir
    local path_real
    local root="$1"
    local root_real

    root_real="$(cd -- "$root" && pwd -P)" || return 1
    path_dir="$(dirname -- "$path")"
    [[ -d "$path_dir" ]] || return 1
    path_real="$(cd -- "$path_dir" && pwd -P)/$(basename -- "$path")" || return 1

    case "$path_real" in
        "$root_real"/*)
            printf '%s\n' "${path_real#"$root_real"/}"
            ;;
        *)
            return 1
            ;;
    esac
}

base_repo_finish_generated_pr() {
    local body_file="$9"
    local branch="$4"
    local commit_message="$6"
    local default_branch="$5"
    local dry_run="$1"
    local file_description="$7"
    local pr_title="$8"
    local repo="$3"
    local root="$2"
    shift 9

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would commit generated %s with message '%s'.\n" "$file_description" "$commit_message"
        printf "[DRY-RUN] Would push branch '%s' to origin.\n" "$branch"
        printf "[DRY-RUN] Would open a draft pull request in '%s' from '%s' to '%s' with title '%s'.\n" \
            "$repo" "$branch" "$default_branch" "$pr_title"
        return 0
    fi

    base_repo_stage_pr_files "$root" "$file_description" "$@" || return 1
    if git -C "$root" diff --cached --quiet --; then
        base_std_log_info "No $file_description changes to commit; skipping pull request creation."
        return 0
    fi

    git -C "$root" commit -m "$commit_message" || {
        base_std_log_error "Failed to commit $file_description."
        return 1
    }
    git -C "$root" push -u origin "$branch" || {
        base_std_log_error "Failed to push branch '$branch' to origin."
        return 1
    }

    gh pr create \
        --repo "$repo" \
        --base "$default_branch" \
        --head "$branch" \
        --title "$pr_title" \
        --draft \
        --body-file "$body_file"
}

base_repo_create_baseline_pr_body() {
    local command_hint="$5"
    local issue="$4"
    local name="$1"
    local repo="$3"
    local root="$2"

    cat <<EOF
## Summary

- Add Base-managed repository baseline files.

## Issue

Closes #$issue

## Validation

- ./tests/validate.sh

Generated by:

\`\`\`bash
$command_hint
\`\`\`
EOF
}

base_repo_print_init_pr_next_steps() {
    local command_hint="$2"
    local pr_output="$1"
    local pr_url=""

    pr_url="$(printf '%s\n' "$pr_output" | awk '/^https?:\/\/github.com\/.+\/pull\/[0-9]+/ { print; exit }')"
    if [[ -n "$pr_url" ]]; then
        printf "Baseline PR opened: %s\n" "$pr_url"
    else
        [[ -z "$pr_output" ]] || printf '%s\n' "$pr_output"
        printf "Baseline PR opened.\n"
    fi
    printf "\n"
    printf "Next steps:\n"
    printf "  1. Review and merge the pull request.\n"
    printf "  2. Re-run this command after merge to complete GitHub configuration:\n"
    printf "     %s\n" "$command_hint"
}

base_repo_print_init_github_skip_notice() {
    local dry_run="$1"
    local name="$2"
    local root="$3"
    local pretty_root

    pretty_root="$(base_repo_pretty_arg "$root")"

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would not create or configure a GitHub repository because no GitHub repo was provided or inferred. Pass --repo <owner/name> to include GitHub repository creation and configuration.\n"
        printf "[DRY-RUN] To include GitHub setup, run:\n"
        printf "  basectl repo init %s --path %s --repo <owner/%s>\n" \
            "$(base_repo_pretty_arg "$name")" \
            "$pretty_root" \
            "$name"
        return 0
    fi

    printf "Baseline files written to '%s'.\n" "$root"
    printf "\n"
    printf "GitHub repository not configured (no --repo provided and no origin remote found).\n"
    printf "To complete GitHub setup, run:\n"
    printf "  basectl repo configure %s --repo <owner/%s>\n" "$pretty_root" "$name"
    printf "\n"
    printf "Or to create the GitHub repository and configure it now:\n"
    printf "  basectl repo init %s --path %s --repo <owner/%s>\n" \
        "$(base_repo_pretty_arg "$name")" \
        "$pretty_root" \
        "$name"
}

base_repo_init_pr_rerun_command() {
    local agent_ready="${11}"
    local configure="$4"
    local configure_project="$6"
    local configure_release="${15}"
    local copy_project_fields_from="${10}"
    local issue="${13}"
    local category="${14}"
    local name="$1"
    local option
    local project_owner="$8"
    local project_schema="$9"
    local project_title="$7"
    local protect_default_branch="$5"
    local repo="$3"
    local root="$2"
    local command=(basectl repo init "$name" --path "$root" --repo "$repo" --issue "$issue" --category "$category" --pr)
    local languages_csv="${12}"
    shift 15

    [[ "$configure" == "1" ]] || command+=(--no-configure)
    [[ "$agent_ready" == "1" ]] && command+=(--agent-ready)
    [[ "$protect_default_branch" == "1" ]] || command+=(--no-protect-default-branch)
    [[ "$configure_project" == "1" ]] || command+=(--no-project)
    [[ "$configure_release" == "1" ]] && command+=(--release)
    [[ -z "$project_title" ]] || command+=(--project "$project_title")
    [[ -z "$project_owner" ]] || command+=(--project-owner "$project_owner")
    [[ "$project_schema" == "base-project" ]] || command+=(--project-schema "$project_schema")
    [[ -z "$copy_project_fields_from" ]] || command+=(--copy-project-fields-from "$copy_project_fields_from")
    [[ -z "$languages_csv" ]] || command+=(--language "$languages_csv")
    for option in "$@"; do
        command+=(--initiative-option "$option")
    done

    base_repo_pretty_command "${command[@]}"
}

base_repo_finish_pr_baseline() {
    local agent_ready="${8:-0}"
    local body_file
    local branch="$5"
    local command_hint="$7"
    local default_branch="$6"
    local dry_run="$1"
    local issue="$9"
    local name="$2"
    local output_file
    local pr_output=""
    local release_contract="${10:-0}"
    local repo="$4"
    local root="$3"
    local status

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would commit generated repository baseline files with message 'Add Base repository baseline'.\n"
        printf "[DRY-RUN] Would push branch '%s' to origin.\n" "$branch"
        printf "[DRY-RUN] Would open a pull request in '%s' from '%s' to '%s' with title 'Add Base repository baseline'.\n" "$repo" "$branch" "$default_branch"
        return 0
    fi

    base_repo_stage_pr_baseline_files "$root" "$agent_ready" "$release_contract" || return 1
    if git -C "$root" diff --cached --quiet --; then
        base_std_log_info "No repository baseline changes to commit; skipping pull request creation."
        return 0
    fi

    git -C "$root" commit -m "Add Base repository baseline" || {
        base_std_log_error "Failed to commit repository baseline files."
        return 1
    }
    git -C "$root" push -u origin "$branch" || {
        base_std_log_error "Failed to push branch '$branch' to origin."
        return 1
    }

    base_std_make_temp_file body_file base-repo-init-pr || {
        base_std_log_error "Failed to create a temporary pull request body file."
        return 1
    }
    base_std_make_temp_file output_file base-repo-init-pr-output || {
        base_std_log_error "Failed to create a temporary pull request output file."
        return 1
    }
    base_repo_create_baseline_pr_body "$name" "$root" "$repo" "$issue" "$command_hint" > "$body_file"
    gh pr create \
        --repo "$repo" \
        --base "$default_branch" \
        --head "$branch" \
        --title "Add Base repository baseline" \
        --body-file "$body_file" > "$output_file" 2>&1
    status=$?
    pr_output="$(cat "$output_file")"
    rm -f "$body_file"
    rm -f "$output_file"
    if [[ "$status" -eq 0 ]]; then
        base_repo_print_init_pr_next_steps "$pr_output" "$command_hint"
        return 0
    fi
    [[ -z "$pr_output" ]] || printf '%s\n' "$pr_output"
    return "$status"
}

base_repo_pr_baseline_has_changes() {
    local agent_ready="${2:-0}"
    local release_contract="${3:-0}"
    local root="$1"

    base_repo_stage_pr_baseline_files "$root" "$agent_ready" "$release_contract" || return 2
    if git -C "$root" diff --cached --quiet --; then
        git -C "$root" reset --quiet || return 2
        return 1
    fi
    git -C "$root" reset --quiet || return 2
    return 0
}
