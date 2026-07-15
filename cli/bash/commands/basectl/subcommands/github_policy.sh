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

base_github_branch_date_is_valid() {
    local branch_date="$1"
    local day days_in_month month year

    [[ "$branch_date" =~ ^([0-9]{4})([0-9]{2})([0-9]{2})$ ]] || return 1
    year=$((10#${BASH_REMATCH[1]}))
    month=$((10#${BASH_REMATCH[2]}))
    day=$((10#${BASH_REMATCH[3]}))

    ((year >= 1 && month >= 1 && month <= 12 && day >= 1)) || return 1
    case "$month" in
        1|3|5|7|8|10|12) days_in_month=31 ;;
        4|6|9|11) days_in_month=30 ;;
        2)
            days_in_month=28
            if ((year % 400 == 0 || (year % 4 == 0 && year % 100 != 0))); then
                days_in_month=29
            fi
            ;;
    esac

    ((day <= days_in_month))
}

base_github_branch_name_is_valid() {
    local branch="$1"
    local branch_date issue_and_rest

    [[ "$branch" =~ $BASE_GITHUB_BRANCH_NAME_PATTERN ]] || return 1
    issue_and_rest="${branch#*/}"
    branch_date="${issue_and_rest#*-}"
    branch_date="${branch_date%%-*}"
    base_github_branch_date_is_valid "$branch_date"
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

base_github_issue_response_values() {
    local output="$1"

    case "$output" in
        pull_request)
            return 3
            ;;
        issue)
            return 0
            ;;
        issue$'\n'*)
            printf '%s\n' "${output#*$'\n'}"
            ;;
        *)
            return 1
            ;;
    esac
}

base_github_issue_labels() {
    local issue="$2"
    local output
    local repo="$1"

    [[ -n "$repo" ]] || return 1
    base_github_issue_number_is_valid "$issue" || return 1
    output="$(
        gh api "repos/$repo/issues/$issue" \
            --jq 'if has("pull_request") then "pull_request" else "issue", (.labels[].name) end'
    )" || return 1
    base_github_issue_response_values "$output"
}

base_github_issue_title() {
    local issue="$2"
    local output
    local repo="$1"

    [[ -n "$repo" ]] || return 1
    base_github_issue_number_is_valid "$issue" || return 1
    output="$(
        gh api "repos/$repo/issues/$issue" \
            --jq 'if has("pull_request") then "pull_request" else "issue", .title end'
    )" || return 1
    base_github_issue_response_values "$output"
}

base_github_issue_category() {
    local categories=()
    local issue="$2"
    local label
    local labels
    local repo="$1"
    local status

    labels="$(base_github_issue_labels "$repo" "$issue")"
    status=$?
    ((status == 0)) || return "$status"
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
