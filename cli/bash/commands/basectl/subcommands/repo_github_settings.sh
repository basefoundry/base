#!/usr/bin/env bash

[[ -n "${_base_repo_github_settings_sourced:-}" ]] && return 0
_base_repo_github_settings_sourced=1
readonly _base_repo_github_settings_sourced

source "$BASE_HOME/cli/bash/commands/basectl/subcommands/github_policy.sh"

base_repo_homebrew_gh_outdated() {
    local output=""

    command -v brew >/dev/null 2>&1 || return 1
    HOMEBREW_NO_AUTO_UPDATE=1 brew list gh >/dev/null 2>&1 || return 1
    output="$(HOMEBREW_NO_AUTO_UPDATE=1 brew outdated gh 2>/dev/null || true)"
    printf '%s\n' "$output" | awk '$1 == "gh" { found = 1 } END { exit found ? 0 : 1 }'
}

base_repo_warn_if_gh_outdated() {
    if base_repo_homebrew_gh_outdated; then
        log_warn "GitHub CLI 'gh' is outdated; run 'basectl setup --profile dev' to upgrade Base-managed developer prerequisites."
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

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create %s GitHub repository '%s' if it does not already exist.\n" "$visibility" "$repo"
        return 0
    fi

    base_repo_require_gh || return 1
    if gh repo view "$repo" >/dev/null 2>&1; then
        log_info "GitHub repository '$repo' already exists."
        return 0
    fi

    log_info "Creating $visibility GitHub repository '$repo'."
    gh repo create "$repo" "--$visibility" --description "$description"
}

base_repo_default_branch_ruleset_payload() {
    cat <<'JSON'
{"name":"Base default branch protection","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"allowed_merge_methods":["squash"],"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_approving_review_count":0,"required_review_thread_resolution":false}},{"type":"deletion"},{"type":"non_fast_forward"}]}
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

base_repo_configure_default_branch_protection() {
    local dry_run="$1"
    local payload
    local repo="$2"
    local ruleset_lookup_output=""
    local ruleset_id=""
    local ruleset_write_output=""

    payload="$(base_repo_default_branch_ruleset_payload)"

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create or update GitHub ruleset 'Base default branch protection' on '%s' targeting '~DEFAULT_BRANCH'.\n" "$repo"
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
            log_warn "Default branch protection skipped for '$repo'."
            log_warn "$ruleset_lookup_output"
            return 0
        fi
        [[ -z "$ruleset_lookup_output" ]] || log_error "$ruleset_lookup_output"
        log_error "Unable to inspect GitHub rulesets for '$repo'."
        return 1
    }
    ruleset_id="$ruleset_lookup_output"

    if [[ -n "$ruleset_id" ]]; then
        ruleset_write_output="$(printf '%s\n' "$payload" | gh api "repos/$repo/rulesets/$ruleset_id" --method PUT --input - 2>&1)" || {
            if base_repo_rulesets_plan_gated_error "$ruleset_write_output"; then
                log_warn "Default branch protection skipped for '$repo'."
                log_warn "$ruleset_write_output"
                return 0
            fi
            [[ -z "$ruleset_write_output" ]] || log_error "$ruleset_write_output"
            log_error "Unable to update Base default branch protection ruleset for '$repo'."
            return 1
        }
        printf "  Branch protection: updated 'Base default branch protection'.\n"
    else
        ruleset_write_output="$(printf '%s\n' "$payload" | gh api "repos/$repo/rulesets" --method POST --input - 2>&1)" || {
            if base_repo_rulesets_plan_gated_error "$ruleset_write_output"; then
                log_warn "Default branch protection skipped for '$repo'."
                log_warn "$ruleset_write_output"
                return 0
            fi
            [[ -z "$ruleset_write_output" ]] || log_error "$ruleset_write_output"
            log_error "Unable to create Base default branch protection ruleset for '$repo'."
            return 1
        }
        printf "  Branch protection: created 'Base default branch protection'.\n"
    fi
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
            log_warn "Branch naming enforcement skipped for '$repo'."
            log_warn "$ruleset_lookup_output"
            return 0
        fi
        [[ -z "$ruleset_lookup_output" ]] || log_error "$ruleset_lookup_output"
        log_error "Unable to inspect GitHub rulesets for '$repo'."
        return 1
    }
    ruleset_id="$ruleset_lookup_output"

    if [[ -n "$ruleset_id" ]]; then
        ruleset_write_output="$(printf '%s\n' "$payload" | gh api "repos/$repo/rulesets/$ruleset_id" --method PUT --input - 2>&1)" || {
            if base_repo_rulesets_plan_gated_error "$ruleset_write_output"; then
                log_warn "Branch naming enforcement skipped for '$repo'."
                log_warn "$ruleset_write_output"
                return 0
            fi
            [[ -z "$ruleset_write_output" ]] || log_error "$ruleset_write_output"
            log_error "Unable to update Base branch naming ruleset for '$repo'."
            return 1
        }
        printf "  Branch naming: updated 'Base branch naming'.\n"
    else
        ruleset_write_output="$(printf '%s\n' "$payload" | gh api "repos/$repo/rulesets" --method POST --input - 2>&1)" || {
            if base_repo_rulesets_plan_gated_error "$ruleset_write_output"; then
                log_warn "Branch naming enforcement skipped for '$repo'."
                log_warn "$ruleset_write_output"
                return 0
            fi
            [[ -z "$ruleset_write_output" ]] || log_error "$ruleset_write_output"
            log_error "Unable to create Base branch naming ruleset for '$repo'."
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
        log_warn "Unable to inspect GitHub Actions secrets for '$repo'."
        [[ -z "$output" ]] || log_warn "$output"
        log_warn "Project Intake may fail unless BASE_PROJECT_TOKEN is configured with user Project access."
        log_warn "Fix: $(base_repo_project_intake_secret_fix_command "$repo")"
        return 0
    }

    if printf '%s\n' "$output" | base_repo_secret_list_has_project_token; then
        return 0
    fi

    log_warn "Project Intake secret 'BASE_PROJECT_TOKEN' is not configured for '$repo'."
    log_warn "GitHub Actions default token cannot access user-level Projects."
    log_warn "Fix: $(base_repo_project_intake_secret_fix_command "$repo")"
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
        log_error "Base Python wrapper '$wrapper' is missing or is not executable."
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

    log_info "Configuring GitHub Project '$project_title' for '$repo'."
    log_info "Running: $(base_repo_pretty_command "${command[@]}")"
    output="$(BASE_CLI_DISPLAY_COMMAND="basectl gh" "${command[@]}" 2>&1)" || status=$?
    if [[ "$status" -eq 0 ]]; then
        [[ -z "$output" ]] || printf '%s\n' "$output"
        printf "  GitHub Project '%s': Status, Priority, Area, Size, Initiative fields configured.\n" "$project_title"
        return 0
    fi
    if [[ "$status" -eq 3 ]]; then
        log_warn "GitHub Project metadata skipped for '$repo'."
        [[ -z "$output" ]] || log_warn "$output"
        return 0
    fi

    [[ -z "$output" ]] || log_error "$output"
    log_error "Unable to configure GitHub Project metadata for '$repo'."
    return 1
}

base_repo_configure_github() {
    local applied_labels=()
    local dry_run="$1"
    local labels=()
    local protect_default_branch="${3:-1}"
    local repo="$2"
    local status=0

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would run: gh repo edit %s --enable-issues --enable-projects --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge --squash-merge-commit-message pr-title-description\n" "$repo"
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
        base_repo_configure_default_branch_protection "$dry_run" "$repo" || status=1
    fi
    base_repo_configure_branch_naming "$dry_run" "$repo" || status=1

    return "$status"
}
