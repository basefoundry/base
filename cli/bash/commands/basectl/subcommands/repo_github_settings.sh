#!/usr/bin/env bash

[[ -n "${_base_repo_github_settings_sourced:-}" ]] && return 0
_base_repo_github_settings_sourced=1
readonly _base_repo_github_settings_sourced

source "$BASE_HOME/cli/bash/commands/basectl/subcommands/github_policy.sh"

BASE_GITHUB_ACTIONS_INTEGRATION_ID=15368
readonly BASE_GITHUB_ACTIONS_INTEGRATION_ID

BASE_REPO_REVIEW_POLICY_CONFIGURED=0
BASE_REPO_REVIEW_REQUIRED_APPROVALS=0
BASE_REPO_REVIEW_CODE_OWNER_REQUIRED=false
BASE_REPO_REVIEW_POLICY_PATH=""

# Set by base_repo_ensure_github_repo so repo init can distinguish a newly
# created empty remote (safe to bootstrap) from an existing remote (never
# implicitly push to it).
BASE_REPO_GITHUB_REPO_CREATED=0

base_repo_homebrew_gh_outdated() {
    local brew_path
    local output=""

    base_std_command_path brew_path brew && [[ -n "$brew_path" ]] || return 1
    HOMEBREW_NO_AUTO_UPDATE=1 brew list gh >/dev/null 2>&1 || return 1
    output="$(HOMEBREW_NO_AUTO_UPDATE=1 brew outdated gh 2>/dev/null || true)"
    printf '%s\n' "$output" | awk '$1 == "gh" { found = 1 } END { exit found ? 0 : 1 }'
}

base_repo_warn_if_gh_outdated() {
    if base_repo_homebrew_gh_outdated; then
        base_std_log_warn "GitHub CLI 'gh' is outdated; run 'basectl setup --profile dev' to upgrade Base-managed developer prerequisites."
    fi
}

base_repo_configure_label() {
    local color="$3"
    local description="$4"
    local dry_run="$1"
    local label="$2"
    local repo="$5"
    local quoted_description

    if [[ "$dry_run" == "1" ]]; then
        quoted_description="$(base_repo_pretty_quote "$description")"
        printf "[DRY-RUN] Would run: gh label create %s --repo %s --color %s --description %s --force\n" \
            "$label" "$repo" "$color" "$quoted_description"
        return 0
    fi

    gh label create "$label" --repo "$repo" --color "$color" --description "$description" --force || return 1
    printf "  Label: %s (created or updated).\n" "$label"
}

base_repo_ensure_github_repo() {
    local description="$3"
    local dry_run="$1"
    local repo="$2"
    local visibility="$4"

    BASE_REPO_GITHUB_REPO_CREATED=0

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create %s GitHub repository '%s' if it does not already exist.\n" "$visibility" "$repo"
        return 0
    fi

    base_repo_require_gh || return 1
    if gh repo view "$repo" >/dev/null 2>&1; then
        base_std_log_info "GitHub repository '$repo' already exists."
        return 0
    fi

    base_std_log_info "Creating $visibility GitHub repository '$repo'."
    gh repo create "$repo" "--$visibility" --description "$description" || return 1
    BASE_REPO_GITHUB_REPO_CREATED=1
}

base_repo_load_review_policy() {
    local path="${1:-}"
    local parsed=""

    BASE_REPO_REVIEW_POLICY_CONFIGURED=0
    BASE_REPO_REVIEW_REQUIRED_APPROVALS=0
    BASE_REPO_REVIEW_CODE_OWNER_REQUIRED=false
    BASE_REPO_REVIEW_POLICY_PATH=""

    [[ -n "$path" ]] || return 0
    BASE_REPO_REVIEW_POLICY_PATH="$path/.github/base-review-policy.yml"
    [[ -e "$BASE_REPO_REVIEW_POLICY_PATH" ]] || {
        BASE_REPO_REVIEW_POLICY_PATH=""
        return 0
    }
    [[ -f "$BASE_REPO_REVIEW_POLICY_PATH" ]] || {
        base_std_log_error "Review policy path '$BASE_REPO_REVIEW_POLICY_PATH' is not a regular file."
        return 1
    }

    parsed="$(awk '
        function fail(message) {
            print message > "/dev/stderr"
            failed = 1
        }
        function value_for(line, value) {
            value = line
            sub(/^  [^:]+:[[:space:]]*/, "", value)
            sub(/[[:space:]]+#.*$/, "", value)
            gsub(/[[:space:]]+$/, "", value)
            return value
        }
        BEGIN {
            in_review_policy = 0
            seen_review_policy = 0
            approvals = 0
            seen_approvals = 0
            code_owner = "false"
            seen_code_owner = 0
        }
        /^[[:space:]]*($|#)/ { next }
        /^review_policy:[[:space:]]*$/ {
            if (seen_review_policy) fail("review_policy must not be repeated.")
            in_review_policy = 1
            seen_review_policy = 1
            next
        }
        /^[^[:space:]#]/ {
            if (in_review_policy) in_review_policy = 0
            fail("Only the review_policy mapping is supported in base-review-policy.yml.")
            next
        }
        {
            if (!in_review_policy || $0 !~ /^  [a-z_]+:[[:space:]]*/) {
                fail("Review policy keys must be indented two spaces under review_policy.")
                next
            }
            key = $0
            sub(/^  /, "", key)
            sub(/:.*/, "", key)
            value = value_for($0)
            if (key == "required_approving_reviews") {
                if (seen_approvals) fail("required_approving_reviews must not be repeated.")
                if (value !~ /^[0-6]$/) fail("required_approving_reviews must be an integer from 0 through 6.")
                else {
                    approvals = value + 0
                    seen_approvals = 1
                }
            } else if (key == "require_code_owner_review") {
                if (seen_code_owner) fail("require_code_owner_review must not be repeated.")
                if (value != "true" && value != "false") fail("require_code_owner_review must be true or false.")
                else {
                    code_owner = value
                    seen_code_owner = 1
                }
            } else {
                fail("Unsupported review policy key: " key ".")
            }
        }
        END {
            if (!seen_review_policy) fail("base-review-policy.yml must declare review_policy.")
            if (!failed) print approvals "\t" code_owner
            exit failed ? 1 : 0
        }
    ' "$BASE_REPO_REVIEW_POLICY_PATH")" || {
        base_std_log_error "Invalid review policy '$BASE_REPO_REVIEW_POLICY_PATH'."
        return 1
    }

    IFS=$'\t' read -r BASE_REPO_REVIEW_REQUIRED_APPROVALS BASE_REPO_REVIEW_CODE_OWNER_REQUIRED <<< "$parsed"
    BASE_REPO_REVIEW_POLICY_CONFIGURED=1
}

base_repo_review_policy_summary() {
    local configured="$1"

    if [[ "$configured" == "1" ]]; then
        printf '%s\n' "configured from $BASE_REPO_REVIEW_POLICY_PATH: $BASE_REPO_REVIEW_REQUIRED_APPROVALS approving review(s), code-owner review $([[ "$BASE_REPO_REVIEW_CODE_OWNER_REQUIRED" == "true" ]] && printf required || printf not-required)"
    else
        printf '%s\n' "default compatibility policy: 0 approving reviews, code-owner review not-required"
    fi
}

base_repo_default_branch_ruleset_payload() {
    local require_issue_branch_policy="${1:-0}"
    local required_approving_reviews="${2:-0}"
    local require_code_owner_review="${3:-false}"

    if [[ "$require_issue_branch_policy" == "1" ]]; then
        cat <<JSON
{"name":"Base default branch protection","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"allowed_merge_methods":["squash"],"dismiss_stale_reviews_on_push":false,"require_code_owner_review":$require_code_owner_review,"require_last_push_approval":false,"required_approving_review_count":$required_approving_reviews,"required_review_thread_resolution":false}},{"type":"required_status_checks","parameters":{"do_not_enforce_on_create":true,"required_status_checks":[{"context":"base/issue-branch-policy","integration_id":15368}],"strict_required_status_checks_policy":false}},{"type":"deletion"},{"type":"non_fast_forward"}]}
JSON
        return 0
    fi

    cat <<JSON
{"name":"Base default branch protection","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"allowed_merge_methods":["squash"],"dismiss_stale_reviews_on_push":false,"require_code_owner_review":$require_code_owner_review,"require_last_push_approval":false,"required_approving_review_count":$required_approving_reviews,"required_review_thread_resolution":false}},{"type":"deletion"},{"type":"non_fast_forward"}]}
JSON
}

base_repo_branch_naming_ruleset_payload() {
    printf '%s\n' \
        "{\"name\":\"Base branch naming\",\"target\":\"branch\",\"enforcement\":\"active\",\"conditions\":{\"ref_name\":{\"include\":[\"~ALL\"],\"exclude\":[\"~DEFAULT_BRANCH\"]}},\"rules\":[{\"type\":\"branch_name_pattern\",\"parameters\":{\"name\":\"Issue-backed Base branch name\",\"negate\":false,\"operator\":\"regex\",\"pattern\":\"$BASE_GITHUB_BRANCH_NAME_PATTERN\"}}]}"
}

base_repo_rulesets_plan_gated_error() {
    local message="$1"

    [[ "$message" == *"Upgrade to GitHub Pro"* ]] &&
        [[ "$message" == *"make this repository public"* ]] &&
        [[ "$message" == *"(HTTP 403)"* ]]
}

base_repo_branch_name_rule_unavailable_error() {
    local message="$1"

    [[ "$message" == *"Invalid rule 'branch_name_pattern'"* ]] &&
        [[ "$message" == *"(HTTP 422)"* ]]
}

base_repo_configure_default_branch_protection() {
    local dry_run="$1"
    local repo="$2"
    local require_issue_branch_policy="${3:-0}"
    local requested_approvals="${4:-0}"
    local requested_code_owner="${5:-false}"
    local policy_configured="${6:-0}"
    local current_approvals=0
    local current_code_owner="false"
    local current_policy=""
    local payload
    local ruleset_lookup_output=""
    local ruleset_id=""
    local ruleset_write_output=""

    if [[ "$dry_run" == "1" ]]; then
        payload="$(base_repo_default_branch_ruleset_payload "$require_issue_branch_policy" "$requested_approvals" "$requested_code_owner")"
        printf "[DRY-RUN] Would create or update GitHub ruleset 'Base default branch protection' on '%s' targeting '~DEFAULT_BRANCH'.\n" "$repo"
        printf "[DRY-RUN] Review policy: current stronger settings are preserved at apply time; proposed %s.\n" "$(base_repo_review_policy_summary "$policy_configured")"
        printf "[DRY-RUN] Would run: gh api repos/%s/rulesets --jq %s\n" \
            "$repo" \
            "$(base_repo_pretty_quote 'map(select(.name == "Base default branch protection" and .source_type == "Repository")) | .[0].id // ""')"
        printf "[DRY-RUN] Would run: gh api repos/%s/rulesets --method POST --input -\n" "$repo"
        printf "[DRY-RUN] Payload: %s\n" "$payload"
        return 0
    fi

    base_repo_require_gh || return 1
    ruleset_lookup_output="$(gh api "repos/$repo/rulesets" \
        --jq 'map(select(.name == "Base default branch protection" and .source_type == "Repository")) | .[0].id // ""' 2>&1)" || {
        if base_repo_rulesets_plan_gated_error "$ruleset_lookup_output"; then
            base_std_log_warn "Default branch protection skipped for '$repo'."
            base_std_log_warn "$ruleset_lookup_output"
            return 0
        fi
        [[ -z "$ruleset_lookup_output" ]] || base_std_log_error "$ruleset_lookup_output"
        base_std_log_error "Unable to inspect GitHub rulesets for '$repo'."
        return 1
    }
    ruleset_id="$ruleset_lookup_output"

    if [[ "$policy_configured" == "1" && -n "$ruleset_id" ]]; then
        current_policy="$(gh api "repos/$repo/rulesets/$ruleset_id" \
            --jq '[.rules[]? | select(.type == "pull_request") | .parameters | [.required_approving_review_count // 0, (.require_code_owner_review // false)] | @tsv] | first // ""' 2>&1)" || {
            [[ -z "$current_policy" ]] || base_std_log_error "$current_policy"
            base_std_log_error "Unable to read the current review policy for '$repo'."
            return 1
        }
        IFS=$'\t' read -r current_approvals current_code_owner <<< "$current_policy"
        [[ "$current_approvals" =~ ^[0-6]$ && ( "$current_code_owner" == "true" || "$current_code_owner" == "false" ) ]] || {
            base_std_log_error "GitHub returned an invalid review policy for '$repo'."
            return 1
        }
        if ((current_approvals > requested_approvals)); then
            requested_approvals="$current_approvals"
            base_std_log_warn "Preserving the stronger existing approving-review requirement for '$repo'."
        fi
        if [[ "$current_code_owner" == "true" ]]; then
            requested_code_owner="true"
            if [[ "${BASE_REPO_REVIEW_CODE_OWNER_REQUIRED:-false}" != "true" ]]; then
                base_std_log_warn "Preserving the stronger existing code-owner review requirement for '$repo'."
            fi
        fi
    fi

    payload="$(base_repo_default_branch_ruleset_payload "$require_issue_branch_policy" "$requested_approvals" "$requested_code_owner")"

    if [[ -n "$ruleset_id" ]]; then
        ruleset_write_output="$(printf '%s\n' "$payload" | gh api "repos/$repo/rulesets/$ruleset_id" --method PUT --input - 2>&1)" || {
            if base_repo_rulesets_plan_gated_error "$ruleset_write_output"; then
                base_std_log_warn "Default branch protection skipped for '$repo'."
                base_std_log_warn "$ruleset_write_output"
                return 0
            fi
            [[ -z "$ruleset_write_output" ]] || base_std_log_error "$ruleset_write_output"
            base_std_log_error "Unable to update Base default branch protection ruleset for '$repo'."
            return 1
        }
        printf "  Branch protection: updated 'Base default branch protection'.\n"
    else
        ruleset_write_output="$(printf '%s\n' "$payload" | gh api "repos/$repo/rulesets" --method POST --input - 2>&1)" || {
            if base_repo_rulesets_plan_gated_error "$ruleset_write_output"; then
                base_std_log_warn "Default branch protection skipped for '$repo'."
                base_std_log_warn "$ruleset_write_output"
                return 0
            fi
            [[ -z "$ruleset_write_output" ]] || base_std_log_error "$ruleset_write_output"
            base_std_log_error "Unable to create Base default branch protection ruleset for '$repo'."
            return 1
        }
        printf "  Branch protection: created 'Base default branch protection'.\n"
    fi
}

base_repo_remote_issue_branch_policy_ready() {
    local actions_app_id=""
    local cutoff_epoch
    local cutoff_timestamp
    local default_branch=""
    local eligible_runs=""
    local now_epoch
    local output=""
    local ready_run_found=0
    local repo="$1"
    local run_id=""
    local run_json=""
    local run_target_url=""
    local run_sha=""
    local run_timestamp=""
    local status_creator=""
    local TZ=UTC
    local workflow_state=""

    output="$(gh api "repos/$repo/actions/workflows/issue-branch-policy.yml" --jq '.state' 2>&1)" || {
        if [[ "$output" == *"(HTTP 404)"* ]]; then
            return 1
        fi
        [[ -z "$output" ]] || base_std_log_error "$output"
        base_std_log_error "Unable to verify the Issue Branch Policy workflow on '$repo'."
        return 2
    }
    workflow_state="$output"
    if [[ "$workflow_state" != "active" ]]; then
        return 1
    fi

    output="$(gh api "repos/$repo" --jq '.default_branch' 2>&1)" || {
        [[ -z "$output" ]] || base_std_log_error "$output"
        base_std_log_error "Unable to determine the default branch for '$repo'."
        return 2
    }
    default_branch="$output"
    [[ -n "$default_branch" ]] || return 1

    run_json="$(gh api "repos/$repo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" 2>&1)" || {
        [[ -z "$run_json" ]] || base_std_log_error "$run_json"
        base_std_log_error "Unable to inspect successful Issue Branch Policy runs on '$repo'."
        return 2
    }
    output="$(jq -r \
        --arg default_branch "$default_branch" \
        --arg repo "$repo" \
        '.workflow_runs[]? | select(
            .event == "workflow_dispatch" and
            .head_branch == $default_branch and
            .head_repository.full_name == $repo and
            .path == ".github/workflows/issue-branch-policy.yml"
        ) | [.id, .head_sha, .updated_at, .html_url] | @tsv' \
        <<< "$run_json" 2>&1)" || {
        [[ -z "$output" ]] || base_std_log_error "$output"
        base_std_log_error "Unable to parse successful Issue Branch Policy runs on '$repo'."
        return 2
    }
    eligible_runs="$output"
    [[ -n "$eligible_runs" ]] || return 1
    printf -v now_epoch '%(%s)T' -1
    [[ "$now_epoch" =~ ^[1-9][0-9]*$ ]] || return 2
    cutoff_epoch=$((now_epoch - 7 * 24 * 60 * 60))
    printf -v cutoff_timestamp '%(%Y-%m-%dT%H:%M:%SZ)T' "$cutoff_epoch"

    while IFS=$'\t' read -r run_id run_sha run_timestamp run_target_url; do
        [[ -n "$run_id" ]] || continue
        if [[ ! "$run_id" =~ ^[1-9][0-9]*$ ||
            ! "$run_sha" =~ ^[0-9a-f]{40}$ ||
            ! "$run_timestamp" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ||
            "$run_target_url" != "https://github.com/$repo/actions/runs/$run_id" ]]; then
            base_std_log_error "GitHub returned malformed Issue Branch Policy run metadata for '$repo'."
            return 2
        fi
        [[ "$run_timestamp" > "$cutoff_timestamp" ]] || continue

        output="$(gh api --paginate --slurp \
            "repos/$repo/commits/$run_sha/statuses?per_page=100" 2>&1)" || {
            [[ -z "$output" ]] || base_std_log_error "$output"
            base_std_log_error "Unable to verify the Issue Branch Policy status source on '$repo'."
            return 2
        }
        status_creator="$(jq -r \
            --arg target_url "$run_target_url" \
            '[.[][]? | select(
                .context == "base/issue-branch-policy" and
                .state == "success" and
                .description == "Issue branch policy workflow is ready" and
                .target_url == $target_url and
                .creator.login == "github-actions[bot]"
            )][0].creator.login // ""' <<< "$output")" || return 2
        if [[ "$status_creator" == "github-actions[bot]" ]]; then
            ready_run_found=1
            break
        fi
    done <<< "$eligible_runs"
    ((ready_run_found == 1)) || return 1

    output="$(gh api /apps/github-actions --jq '.id' 2>&1)" || {
        [[ -z "$output" ]] || base_std_log_error "$output"
        base_std_log_error "Unable to verify the GitHub Actions integration id."
        return 2
    }
    actions_app_id="$output"
    [[ "$actions_app_id" == "$BASE_GITHUB_ACTIONS_INTEGRATION_ID" ]]
}

base_repo_current_issue_branch_policy_integration_id() {
    local output=""
    local repo="$1"
    local ruleset_id=""

    output="$(gh api "repos/$repo/rulesets" \
        --jq 'map(select(.name == "Base default branch protection" and .source_type == "Repository")) | .[0].id // ""' 2>&1)" || {
        if base_repo_rulesets_plan_gated_error "$output"; then
            return 1
        fi
        [[ -z "$output" ]] || base_std_log_error "$output"
        base_std_log_error "Unable to inspect current default branch protection for '$repo'."
        return 2
    }
    ruleset_id="$output"
    [[ -n "$ruleset_id" ]] || return 1

    output="$(gh api "repos/$repo/rulesets/$ruleset_id" \
        --jq '[.rules[]? | select(.type == "required_status_checks") | .parameters.required_status_checks[]? | select(.context == "base/issue-branch-policy") | (.integration_id // 0)] | first // ""' 2>&1)" || {
        [[ -z "$output" ]] || base_std_log_error "$output"
        base_std_log_error "Unable to inspect the current Issue Branch Policy requirement on '$repo'."
        return 2
    }
    [[ -n "$output" ]] || return 1
    printf '%s\n' "$output"
}

base_repo_configure_branch_naming() {
    local dry_run="$1"
    local payload
    local repo="$2"
    local ruleset_lookup_output=""
    local ruleset_id=""
    local ruleset_write_output=""

    payload="$(base_repo_branch_naming_ruleset_payload)"

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create or update GitHub ruleset 'Base branch naming' on '%s' targeting all non-default branches.\n" "$repo"
        printf "[DRY-RUN] Would run: gh api repos/%s/rulesets --jq %s\n" \
            "$repo" \
            "$(base_repo_pretty_quote 'map(select(.name == "Base branch naming" and .source_type == "Repository")) | .[0].id // ""')"
        printf "[DRY-RUN] Would run: gh api repos/%s/rulesets --method POST --input -\n" "$repo"
        printf "[DRY-RUN] Payload: %s\n" "$payload"
        return 0
    fi

    base_repo_require_gh || return 1
    ruleset_lookup_output="$(gh api "repos/$repo/rulesets" \
        --jq 'map(select(.name == "Base branch naming" and .source_type == "Repository")) | .[0].id // ""' 2>&1)" || {
        if base_repo_rulesets_plan_gated_error "$ruleset_lookup_output"; then
            base_std_log_warn "Branch naming enforcement skipped for '$repo'."
            base_std_log_warn "$ruleset_lookup_output"
            return 0
        fi
        [[ -z "$ruleset_lookup_output" ]] || base_std_log_error "$ruleset_lookup_output"
        base_std_log_error "Unable to inspect GitHub rulesets for '$repo'."
        return 1
    }
    ruleset_id="$ruleset_lookup_output"

    if [[ -n "$ruleset_id" ]]; then
        ruleset_write_output="$(printf '%s\n' "$payload" | gh api "repos/$repo/rulesets/$ruleset_id" --method PUT --input - 2>&1)" || {
            if base_repo_rulesets_plan_gated_error "$ruleset_write_output"; then
                base_std_log_warn "Branch naming enforcement skipped for '$repo'."
                base_std_log_warn "$ruleset_write_output"
                return 0
            fi
            if base_repo_branch_name_rule_unavailable_error "$ruleset_write_output"; then
                base_std_log_warn "Branch naming ruleset unavailable for '$repo'; issue branch policy workflow remains the fallback."
                base_std_log_warn "$ruleset_write_output"
                return 0
            fi
            [[ -z "$ruleset_write_output" ]] || base_std_log_error "$ruleset_write_output"
            base_std_log_error "Unable to update Base branch naming ruleset for '$repo'."
            return 1
        }
        printf "  Branch naming: updated 'Base branch naming'.\n"
    else
        ruleset_write_output="$(printf '%s\n' "$payload" | gh api "repos/$repo/rulesets" --method POST --input - 2>&1)" || {
            if base_repo_rulesets_plan_gated_error "$ruleset_write_output"; then
                base_std_log_warn "Branch naming enforcement skipped for '$repo'."
                base_std_log_warn "$ruleset_write_output"
                return 0
            fi
            if base_repo_branch_name_rule_unavailable_error "$ruleset_write_output"; then
                base_std_log_warn "Branch naming ruleset unavailable for '$repo'; issue branch policy workflow remains the fallback."
                base_std_log_warn "$ruleset_write_output"
                return 0
            fi
            [[ -z "$ruleset_write_output" ]] || base_std_log_error "$ruleset_write_output"
            base_std_log_error "Unable to create Base branch naming ruleset for '$repo'."
            return 1
        }
        printf "  Branch naming: created 'Base branch naming'.\n"
    fi
}

base_repo_default_project_title() {
    local repo="$1"

    printf '%s\n' "${repo#*/}"
}

base_repo_project_owner_from_repo() {
    local repo="$1"

    printf '%s\n' "${repo%%/*}"
}

base_repo_project_config_path() {
    local root="$1"
    local path="$root/.github/base-project.yml"

    if [[ -f "$path" ]]; then
        printf '%s\n' "$path"
    fi
}

base_repo_project_intake_secret_fix_command() {
    local repo="$1"

    printf 'gh auth token | gh secret set BASE_PROJECT_TOKEN --repo %s\n' "$repo"
}

base_repo_secret_list_has_project_token() {
    awk '
        $1 == "BASE_PROJECT_TOKEN" { found = 1 }
        END { exit found ? 0 : 1 }
    '
}

base_repo_check_project_intake_secret() {
    local dry_run="$1"
    local output=""
    local repo="$2"

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would verify GitHub Actions secret 'BASE_PROJECT_TOKEN' exists for '%s'.\n" "$repo"
        return 0
    fi

    base_repo_require_gh || return 1
    output="$(gh secret list --repo "$repo" 2>&1)" || {
        base_std_log_warn "Unable to inspect GitHub Actions secrets for '$repo'."
        [[ -z "$output" ]] || base_std_log_warn "$output"
        base_std_log_warn "Project Intake may fail unless BASE_PROJECT_TOKEN is configured with user Project access."
        base_std_log_warn "Fix: $(base_repo_project_intake_secret_fix_command "$repo")"
        return 0
    }

    if printf '%s\n' "$output" | base_repo_secret_list_has_project_token; then
        return 0
    fi

    base_std_log_warn "Project Intake secret 'BASE_PROJECT_TOKEN' is not configured for '$repo'."
    base_std_log_warn "GitHub Actions default token cannot access user-level Projects."
    base_std_log_warn "Fix: $(base_repo_project_intake_secret_fix_command "$repo")"
}

base_repo_configure_project_metadata() {
    local dry_run="$1"
    local config_path="$6"
    local copy_fields_from_project="$7"
    local replace_project="$8"
    local option
    local owner="$4"
    local output=""
    local project_title="$3"
    local repo="$2"
    local schema="$5"
    local status=0
    local wrapper="${BASE_REPO_PROJECT_WRAPPER:-$BASE_HOME/bin/base-wrapper}"
    shift 8

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would configure GitHub Project '%s' for '%s'.\n" "$project_title" "$repo"
        if [[ "$replace_project" == "1" ]]; then
            printf "[DRY-RUN] Would replace nonstandard existing GitHub Project '%s' from 'base-project-template'.\n" "$project_title"
        else
            printf "[DRY-RUN] Would copy GitHub Project 'base-project-template' to '%s' if missing.\n" "$project_title"
        fi
        printf "[DRY-RUN] Would link GitHub Project '%s' to repository '%s'.\n" "$project_title" "$repo"
        printf "[DRY-RUN] Would backfill issues from '%s' into GitHub Project '%s'.\n" "$repo" "$project_title"
        if [[ -n "$config_path" ]]; then
            printf "[DRY-RUN] Would read GitHub Project config from '%s'.\n" "$config_path"
            printf "[DRY-RUN] Would apply issue defaults from '%s' to missing Project item fields.\n" "$config_path"
        fi
        if [[ -n "$copy_fields_from_project" ]]; then
            printf "[DRY-RUN] Would copy missing Project item field values from '%s' into '%s'.\n" \
                "$copy_fields_from_project" \
                "$project_title"
        fi
        base_repo_check_project_intake_secret "$dry_run" "$repo"
        printf "[DRY-RUN] Would run: %s --project base base_github_projects project configure --project %s --owner %s --repo %s --schema %s" \
            "$wrapper" \
            "$(base_repo_pretty_arg "$project_title")" \
            "$owner" \
            "$repo" \
            "$schema"
        if [[ -n "$config_path" ]]; then
            printf " --config %s" "$(base_repo_pretty_arg "$config_path")"
        fi
        if [[ -n "$copy_fields_from_project" ]]; then
            printf " --copy-fields-from %s" "$(base_repo_pretty_arg "$copy_fields_from_project")"
        fi
        if [[ "$replace_project" == "1" ]]; then
            printf " --replace-project"
        fi
        for option in "$@"; do
            printf " --initiative-option %s" "$(base_repo_pretty_arg "$option")"
        done
        printf "\n"
        printf "[DRY-RUN] Project fields: Status, Priority, Area, Size, Initiative\n"
        return 0
    fi

    [[ -x "$wrapper" ]] || {
        base_std_log_error "Base Python wrapper '$wrapper' is missing or is not executable."
        return 1
    }
    base_repo_check_project_intake_secret "$dry_run" "$repo" || return 1

    local command=(
        "$wrapper"
        --project base
        base_github_projects
        project
        configure
        --project "$project_title"
        --owner "$owner"
        --repo "$repo"
        --schema "$schema"
    )
    if [[ -n "$config_path" ]]; then
        command+=(--config "$config_path")
    fi
    if [[ -n "$copy_fields_from_project" ]]; then
        command+=(--copy-fields-from "$copy_fields_from_project")
    fi
    if [[ "$replace_project" == "1" ]]; then
        command+=(--replace-project)
    fi
    for option in "$@"; do
        command+=(--initiative-option "$option")
    done

    base_std_log_info "Configuring GitHub Project '$project_title' for '$repo'."
    base_std_log_info "Running: $(base_repo_pretty_command "${command[@]}")"
    output="$(BASE_CLI_DISPLAY_COMMAND="basectl gh" "${command[@]}" 2>&1)" || status=$?
    if [[ "$status" -eq 0 ]]; then
        [[ -z "$output" ]] || printf '%s\n' "$output"
        printf "  GitHub Project '%s': Status, Priority, Area, Size, Initiative fields configured.\n" "$project_title"
        return 0
    fi
    if [[ "$status" -eq 3 ]]; then
        base_std_log_warn "GitHub Project metadata skipped for '$repo'."
        [[ -z "$output" ]] || base_std_log_warn "$output"
        return 0
    fi

    [[ -z "$output" ]] || base_std_log_error "$output"
    base_std_log_error "Unable to configure GitHub Project metadata for '$repo'."
    return 1
}

base_repo_configure_github() {
    local applied_labels=()
    local current_issue_branch_policy_integration_id=""
    local current_issue_branch_policy_required=0
    local dry_run="$1"
    local issue_branch_policy_available=0
    local labels=()
    local protect_default_branch="${3:-1}"
    local repo="$2"
    local root="${4:-}"
    local status=0

    base_repo_load_review_policy "$root" || return 1

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would run: gh repo edit %s --enable-issues --enable-projects --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge --squash-merge-commit-message pr-title-description\n" "$repo"
        printf "[DRY-RUN] Review policy: %s.\n" "$(base_repo_review_policy_summary "$BASE_REPO_REVIEW_POLICY_CONFIGURED")"
    else
        base_repo_require_gh || return 1
        base_repo_warn_if_gh_outdated
        printf "Configuring GitHub repository '%s'...\n" "$repo"
        gh repo edit "$repo" \
            --enable-issues \
            --enable-projects \
            --enable-squash-merge \
            --enable-merge-commit=false \
            --enable-rebase-merge=false \
            --delete-branch-on-merge \
            --squash-merge-commit-message pr-title-description || return 1
        printf "  Repository settings: applied.\n"
    fi

    base_repo_configure_label "$dry_run" bug "d73a4a" "Something is not working" "$repo" && applied_labels+=(bug) || status=1
    base_repo_configure_label "$dry_run" enhancement "a2eeef" "New feature or product improvement" "$repo" && applied_labels+=(enhancement) || status=1
    base_repo_configure_label "$dry_run" documentation "0075ca" "Documentation improvements" "$repo" && applied_labels+=(documentation) || status=1
    base_repo_configure_label "$dry_run" ci "0e8a16" "Continuous integration, tests, automation, or release workflows" "$repo" && applied_labels+=(ci) || status=1
    base_repo_configure_label "$dry_run" security "ee0701" "Security hardening or vulnerability work" "$repo" && applied_labels+=(security) || status=1
    base_repo_configure_label "$dry_run" needs-demo "fbca04" "Change should update a project demo" "$repo" && applied_labels+=(needs-demo) || status=1
    if [[ "$dry_run" != "1" && "${#applied_labels[@]}" -gt 0 ]]; then
        labels=("${applied_labels[@]}")
        printf "  Labels: "
        base_repo_join_csv "${labels[@]}"
        printf " (%d applied).\n" "${#labels[@]}"
    fi
    if [[ "$protect_default_branch" == "1" ]]; then
        if [[ "$dry_run" == "1" ]]; then
            [[ -n "$root" && -f "$root/.github/workflows/issue-branch-policy.yml" ]] &&
                issue_branch_policy_available=1
        else
            current_issue_branch_policy_integration_id="$(base_repo_current_issue_branch_policy_integration_id "$repo")"
            case $? in
                0) current_issue_branch_policy_required=1 ;;
                1) ;;
                *) return 1 ;;
            esac
            if base_repo_remote_issue_branch_policy_ready "$repo"; then
                issue_branch_policy_available=1
            else
                case $? in
                    1)
                        if [[ "$current_issue_branch_policy_required" == "1" && "$current_issue_branch_policy_integration_id" == "$BASE_GITHUB_ACTIONS_INTEGRATION_ID" ]]; then
                            issue_branch_policy_available=1
                            base_std_log_warn "Preserving the existing Issue Branch Policy requirement on '$repo' without recent bootstrap evidence."
                        elif [[ "$current_issue_branch_policy_required" == "1" ]]; then
                            base_std_log_error "Refusing to replace the existing unbound Issue Branch Policy requirement on '$repo' without a recent trusted success."
                            return 1
                        else
                            base_std_log_warn "Issue branch policy is not required for '$repo' yet."
                            base_std_log_warn "Enable '.github/workflows/issue-branch-policy.yml', complete one recent successful run, and rerun 'basectl repo configure'."
                        fi
                        ;;
                    *) return 1 ;;
                esac
            fi
        fi
        base_repo_configure_default_branch_protection \
            "$dry_run" \
            "$repo" \
            "$issue_branch_policy_available" \
            "$BASE_REPO_REVIEW_REQUIRED_APPROVALS" \
            "$BASE_REPO_REVIEW_CODE_OWNER_REQUIRED" \
            "$BASE_REPO_REVIEW_POLICY_CONFIGURED" || status=1
    fi
    base_repo_configure_branch_naming "$dry_run" "$repo" || status=1

    return "$status"
}
