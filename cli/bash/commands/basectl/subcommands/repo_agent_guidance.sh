#!/usr/bin/env bash

[[ -n "${_base_repo_agent_guidance_sourced:-}" ]] && return 0
_base_repo_agent_guidance_sourced=1
readonly _base_repo_agent_guidance_sourced

base_repo_agent_guidance_usage() {
    cat <<'EOF'
Usage:
  basectl repo agent-guidance [path] [options]

Options:
  --repo <owner/name>           GitHub repository for --pr. Defaults to the target origin remote.
  --repo-name <name>            Repository name for generated agent guidance. Defaults to the target path basename.
  --default-branch <name>       Default branch for generated agent guidance. Defaults to detected branch, then main.
  --validation-command <cmd>    Validation command for generated agent guidance. Defaults to ./tests/validate.sh.
  --pr                          Commit generated guidance files on a branch and open a draft pull request.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Create optional repo-local agent guidance files for a Base-managed repository.
EOF
}

base_repo_agent_guidance_usage_error() {
    base_repo_print_usage_error "basectl repo agent-guidance" "$@"
}

base_repo_write_agent_instructions() {
    local default_branch="$3"
    local dry_run="$1"
    local repo_name="$2"
    local root="$5"
    local validation_command="$4"

    base_repo_write_stream "$dry_run" "$root/AGENTS.md" <<EOF
# Agent Instructions for $repo_name

Use this file for repository-local agent guidance. User instructions still take
precedence over this baseline.

## Workflow

1. Create or choose a GitHub issue before implementation work.
2. Use one standard issue label: \`bug\`, \`enhancement\`, \`documentation\`,
   \`ci\`, or \`security\`.
3. Branch from the issue with:

   \`\`\`text
   <category>/<issue>-<YYYYMMDD>-<slug>
   \`\`\`

4. Use a dedicated worktree for each pull request:

   \`\`\`bash
   git fetch origin
   git worktree add -b <branch> ../$repo_name-worktrees/<slug> origin/$default_branch
   \`\`\`

5. Keep the pull request scoped to the issue and link it with
   \`Fixes #<issue>\` or \`Closes #<issue>\` when merge should close the issue.
6. Preserve existing user changes. Do not overwrite project-owned files unless
   the user explicitly asks for that edit.

## Validation

Run the project validation command before publishing changes:

   \`\`\`bash
   $validation_command
   \`\`\`

Also run narrower tests for the files changed when available.

## Documentation

Update docs when behavior, commands, setup, or workflow expectations change.
Update \`CHANGELOG.md\` only for notable user-visible or release-worthy changes.

## Finish

After merge, sync $default_branch, remove the worktree, and delete merged local
and remote branches when safe.
EOF
}

base_repo_write_agent_skills() {
    local dry_run="$1"
    local repo_name="$2"
    local root="$3"

    base_repo_write_stream "$dry_run" "$root/skills.md" <<EOF
# Project Skills for $repo_name

Use this file as the repo-local index for project-specific agent workflows.
Keep entries short, concrete, and owned by this repository.

## Suggested Entries

- Development workflow: issue selection, branch naming, validation, PR creation,
  merge, and cleanup.
- Testing workflow: the commands that prove common changes are safe.
- Release workflow: version, changelog, tag, release, and package manager steps.
- Domain workflow: product-specific checks or demo expectations that agents
  should not have to rediscover.

## Boundaries

Do not vendor third-party methodology files here. Link to external guidance or
copy only repo-owned instructions that the project intends to maintain.
EOF
}

base_repo_write_agent_pull_request_template() {
    local dry_run="$1"
    local root="$2"

    base_repo_write_stream "$dry_run" "$root/.github/pull_request_template.md" <<'EOF'
## Summary

<!-- What changed and why. Focus on decisions and user impact, not just the diff. -->

## Issue

Closes #

## Validation

<!-- Commands run and relevant output. Include narrow checks and any broader suite used. -->

## Reviewer Notes

<!-- Optional: tradeoffs, follow-up work, or areas where reviewer attention would help. -->

## Checklist

- [ ] Branch name follows `<category>/<issue>-<YYYYMMDD>-<slug>`.
- [ ] Pull request is scoped to one issue, unless a documented multi-issue exception applies.
- [ ] Pull request body explains what changed and how it was validated.
- [ ] Relevant project checks pass.
- [ ] Documentation is updated when behavior or user-facing commands change.
- [ ] CHANGELOG is updated for notable user-visible or release-worthy changes.
- [ ] Pull request includes `Fixes #<issue>` or `Closes #<issue>` when merge should close the issue.
EOF
}

base_repo_print_agent_guidance_summary() {
    local created=()
    local created_count
    local created_word
    local total=3
    local unchanged=()
    local unchanged_count
    local unchanged_verb
    local unchanged_word

    while (($#)); do
        case "$1" in
            --created)
                created+=("$2")
                shift 2
                ;;
            --unchanged)
                unchanged+=("$2")
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    created_count="${#created[@]}"
    unchanged_count="${#unchanged[@]}"

    if ((unchanged_count == total)); then
        printf "Agent guidance: all %d files already exist and were left unchanged.\n" "$total"
        printf "To overwrite, remove the files first and re-run.\n"
        return 0
    fi

    created_word="files"
    unchanged_verb="were"
    unchanged_word="files"
    [[ "$created_count" == "1" ]] && created_word="file"
    if [[ "$unchanged_count" == "1" ]]; then
        unchanged_word="file"
        unchanged_verb="was"
    fi

    if ((created_count > 0 && unchanged_count > 0)); then
        printf "Agent guidance: %d %s created, %d %s already existed and %s left unchanged.\n" \
            "$created_count" "$created_word" "$unchanged_count" "$unchanged_word" "$unchanged_verb"
    elif ((created_count > 0)); then
        printf "Agent guidance: %d %s created.\n" "$created_count" "$created_word"
    else
        printf "Agent guidance: no files changed.\n"
    fi

    if ((created_count > 0)); then
        printf "  Created:   "
        base_repo_join_csv "${created[@]}"
        printf "\n"
    fi
    if ((unchanged_count > 0)); then
        printf "  Unchanged: "
        base_repo_join_csv "${unchanged[@]}"
        printf "\n"
    fi
}

base_repo_write_agent_guidance() {
    local agents_existed=0
    local default_branch="$3"
    local dry_run="$1"
    local pr_template_existed=0
    local repo_name="$2"
    local root="$5"
    local summary_args=()
    local skills_existed=0
    local status=0
    local validation_command="$4"

    if [[ "$dry_run" != "1" ]]; then
        [[ -e "$root/AGENTS.md" ]] && agents_existed=1
        [[ -e "$root/skills.md" ]] && skills_existed=1
        [[ -e "$root/.github/pull_request_template.md" ]] && pr_template_existed=1
    fi

    base_repo_write_agent_instructions "$dry_run" "$repo_name" "$default_branch" "$validation_command" "$root" || status=1
    base_repo_write_agent_skills "$dry_run" "$repo_name" "$root" || status=1
    base_repo_write_agent_pull_request_template "$dry_run" "$root" || status=1

    if [[ "$dry_run" != "1" && "$status" -eq 0 ]]; then
        if ((agents_existed)); then
            summary_args+=(--unchanged "AGENTS.md")
        else
            summary_args+=(--created "AGENTS.md")
        fi
        if ((skills_existed)); then
            summary_args+=(--unchanged "skills.md")
        else
            summary_args+=(--created "skills.md")
        fi
        if ((pr_template_existed)); then
            summary_args+=(--unchanged ".github/pull_request_template.md")
        else
            summary_args+=(--created ".github/pull_request_template.md")
        fi
        base_repo_print_agent_guidance_summary "${summary_args[@]}"
    fi

    return "$status"
}

base_repo_create_agent_guidance_pr_body() {
    local default_branch="$3"
    local repo="$5"
    local repo_name="$1"
    local root="$2"
    local validation_command="$4"

    cat <<EOF
## Summary

- Add Base repo-local agent guidance files.

## Validation

- $validation_command

Generated by:

\`\`\`bash
basectl repo agent-guidance $(base_repo_pretty_arg "$root") --repo-name $(base_repo_pretty_arg "$repo_name") --default-branch $(base_repo_pretty_arg "$default_branch") --validation-command $(base_repo_pretty_arg "$validation_command") --repo $repo --pr
\`\`\`
EOF
}

base_repo_finish_agent_guidance_pr() {
    local body_file
    local branch="$5"
    local default_branch="$6"
    local dry_run="$1"
    local repo="$4"
    local repo_name="$2"
    local root="$3"
    local status
    local validation_command="$7"

    if [[ "$dry_run" == "1" ]]; then
        base_repo_finish_generated_pr \
            "$dry_run" \
            "$root" \
            "$repo" \
            "$branch" \
            "$default_branch" \
            "Add Base agent guidance" \
            "agent guidance files" \
            "Add Base agent guidance" \
            "" \
            "${BASE_REPO_AGENT_GUIDANCE_FILES[@]}"
        return $?
    fi

    std_make_temp_file body_file base-repo-agent-guidance-pr || {
        log_error "Failed to create a temporary pull request body file."
        return 1
    }
    base_repo_create_agent_guidance_pr_body "$repo_name" "$root" "$default_branch" "$validation_command" "$repo" > "$body_file"
    base_repo_finish_generated_pr \
        "$dry_run" \
        "$root" \
        "$repo" \
        "$branch" \
        "$default_branch" \
        "Add Base agent guidance" \
        "agent guidance files" \
        "Add Base agent guidance" \
        "$body_file" \
        "${BASE_REPO_AGENT_GUIDANCE_FILES[@]}"
    status=$?
    rm -f "$body_file"
    return "$status"
}

base_repo_agent_guidance() {
    local create_pr=0
    local default_branch=""
    local default_branch_explicit=0
    local dry_run=0
    local github_repo=""
    local path=""
    local pr_branch=""
    local pr_default_branch=""
    local repo_name=""
    local root
    local validation_command="./tests/validate.sh"

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_agent_guidance_usage
                return 0
                ;;
            --repo)
                [[ -n "${2:-}" ]] || {
                    base_repo_agent_guidance_usage_error "Option '--repo' requires an argument."
                    return $?
                }
                github_repo="$2"
                shift 2
                ;;
            --repo=*)
                github_repo="${1#--repo=}"
                shift
                ;;
            --repo-name)
                [[ -n "${2:-}" ]] || {
                    base_repo_agent_guidance_usage_error "Option '--repo-name' requires an argument."
                    return $?
                }
                repo_name="$2"
                shift 2
                ;;
            --repo-name=*)
                repo_name="${1#--repo-name=}"
                shift
                ;;
            --default-branch)
                [[ -n "${2:-}" ]] || {
                    base_repo_agent_guidance_usage_error "Option '--default-branch' requires an argument."
                    return $?
                }
                default_branch="$2"
                default_branch_explicit=1
                shift 2
                ;;
            --default-branch=*)
                default_branch="${1#--default-branch=}"
                default_branch_explicit=1
                shift
                ;;
            --validation-command)
                [[ -n "${2:-}" ]] || {
                    base_repo_agent_guidance_usage_error "Option '--validation-command' requires an argument."
                    return $?
                }
                validation_command="$2"
                shift 2
                ;;
            --validation-command=*)
                validation_command="${1#--validation-command=}"
                shift
                ;;
            --pr)
                create_pr=1
                shift
                ;;
            --dry-run)
                dry_run=1
                shift
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_agent_guidance_usage_error "Unknown repo agent-guidance option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$path" ]]; then
                    base_repo_agent_guidance_usage_error "The 'repo agent-guidance' command accepts at most one path."
                    return $?
                fi
                path="$1"
                shift
                ;;
        esac
    done

    [[ -n "$path" ]] || path="."
    root="$(base_repo_target_path "$path")"
    [[ -n "$repo_name" ]] || repo_name="$(basename -- "$root")"
    if [[ "$default_branch_explicit" != "1" ]]; then
        if ! default_branch="$(base_repo_detect_default_branch "$root")"; then
            default_branch="main"
            printf "Note: Could not detect default branch from origin; defaulting to 'main'.\n"
            printf "      Pass --default-branch <name> to set it explicitly.\n"
        fi
    fi
    [[ -n "$default_branch" ]] || {
        base_repo_agent_guidance_usage_error "Option '--default-branch' requires a non-empty value."
        return $?
    }
    [[ -n "$validation_command" ]] || {
        base_repo_agent_guidance_usage_error "Option '--validation-command' requires a non-empty value."
        return $?
    }
    base_repo_validate_name "$repo_name" || return 2

    if ((create_pr)); then
        if [[ -z "$github_repo" ]]; then
            github_repo="$(base_repo_infer_github_repo "$root" || true)"
        fi
        [[ -n "$github_repo" ]] || {
            base_repo_agent_guidance_usage_error "Option '--pr' requires --repo <owner/name> or an inferable GitHub origin remote."
            return $?
        }

        pr_branch="$(base_repo_helper_pr_branch_name "agent-guidance" "$repo_name")"
        if [[ "$dry_run" == "1" ]]; then
            pr_default_branch="<default branch>"
        else
            base_repo_require_pr_worktree "$root" "repo agent-guidance --pr" || return 1
            pr_default_branch="$(base_repo_default_branch_for_pr "$github_repo")" || return 1
        fi
        base_repo_prepare_pr_branch "$dry_run" "$root" "$pr_branch" "$pr_default_branch" "repo agent-guidance --pr" || return 1
    fi

    base_repo_write_agent_guidance "$dry_run" "$repo_name" "$default_branch" "$validation_command" "$root" || return $?
    if ((create_pr)); then
        base_repo_finish_agent_guidance_pr \
            "$dry_run" \
            "$repo_name" \
            "$root" \
            "$github_repo" \
            "$pr_branch" \
            "$pr_default_branch" \
            "$validation_command"
        return $?
    fi
    if [[ "$dry_run" != "1" ]]; then
        base_repo_print_review_hint "$root"
    fi
}
