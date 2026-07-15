#!/usr/bin/env bash

[[ -n "${_base_github_policy_sourced:-}" ]] && return 0
_base_github_policy_sourced=1
readonly _base_github_policy_sourced

BASE_GITHUB_BRANCH_CATEGORIES="bug|enhancement|documentation|ci|security"
BASE_GITHUB_BRANCH_NAME_PATTERN="^(${BASE_GITHUB_BRANCH_CATEGORIES})/[1-9][0-9]*-[0-9]{8}-[a-z0-9]+(-[a-z0-9]+)*$"
readonly BASE_GITHUB_BRANCH_CATEGORIES BASE_GITHUB_BRANCH_NAME_PATTERN

base_github_branch_category_is_valid() {
    local category="$1"

    [[ "$category" =~ ^($BASE_GITHUB_BRANCH_CATEGORIES)$ ]]
}

base_github_issue_number_is_valid() {
    local issue="$1"

    [[ "$issue" =~ ^[1-9][0-9]*$ ]]
}

base_github_branch_name_is_valid() {
    local branch="$1"

    [[ "$branch" =~ $BASE_GITHUB_BRANCH_NAME_PATTERN ]]
}

base_github_branch_name() {
    local branch
    local branch_date="${4:-}"
    local category="$1"
    local issue="$2"
    local slug="$3"

    base_github_branch_category_is_valid "$category" || return 1
    base_github_issue_number_is_valid "$issue" || return 1
    if [[ -z "$branch_date" ]]; then
        printf -v branch_date '%(%Y%m%d)T' -1
    fi

    branch="$category/$issue-$branch_date-$slug"
    base_github_branch_name_is_valid "$branch" || return 1
    printf '%s\n' "$branch"
}

base_github_issue_category() {
    local categories=()
    local issue="$2"
    local label
    local labels
    local repo="$1"

    [[ -n "$repo" ]] || return 1
    base_github_issue_number_is_valid "$issue" || return 1
    labels="$(gh issue view "$issue" --repo "$repo" --json labels --jq '.labels[].name')" || return 1
    while IFS= read -r label; do
        base_github_branch_category_is_valid "$label" && categories+=("$label")
    done <<< "$labels"

    ((${#categories[@]} == 1)) || return 2
    printf '%s\n' "${categories[0]}"
}

base_github_issue_from_branch_name() {
    local branch="$1"
    local issue_and_rest

    base_github_branch_name_is_valid "$branch" || return 1
    issue_and_rest="${branch#*/}"
    printf '%s\n' "${issue_and_rest%%-*}"
}
