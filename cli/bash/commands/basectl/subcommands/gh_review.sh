#!/usr/bin/env bash

[[ -n "${_base_gh_review_sourced:-}" ]] && return 0
_base_gh_review_sourced=1
readonly _base_gh_review_sourced

BASE_GH_REVIEW_REF_PREFIX="refs/base-review/pr"
BASE_GH_REVIEW_ID_PATTERN='^pr-[1-9][0-9]*-[a-z0-9]+(-[a-z0-9]+)*$'
BASE_GH_REVIEW_SLUG_PATTERN='^[a-z0-9]+(-[a-z0-9]+)*$'
readonly BASE_GH_REVIEW_REF_PREFIX BASE_GH_REVIEW_ID_PATTERN BASE_GH_REVIEW_SLUG_PATTERN

base_gh_review_usage() {
    cat <<'EOF'
Usage:
  basectl gh review fetch <number> --name <slug> [--repo <owner/name>] [--root <path>] [--refresh]
  basectl gh review prune [--dry-run] [--yes] [--closed-unmerged] [--pr <number>] [--root <path>]

Purpose:
  Create detached PR-review worktrees under a namespaced local ref and prune
  only Base-owned review worktrees that are safe to remove.

Notes:
  - Review worktrees never create ordinary refs/heads/pr-* branches.
  - Fetch creates refs/base-review/pr/<number>/<slug> and a worktree named
    pr-<number>-<slug> under <repo>-review-worktrees by default.
  - Prune is dry-run by default and never removes dirty or open-PR worktrees.
  - Legacy local pr-* branches are a separate one-time cleanup and are not
    managed by this command.
EOF
}

base_gh_review_leaf_usage() {
    local command="$1"

    case "$command" in
        fetch)
            cat <<'EOF'
Usage:
  basectl gh review fetch <number> --name <slug> [options]

Purpose:
  Fetch a pull-request head into a namespaced local review ref and create a
  detached review worktree.

Options:
  --name <slug>       Required lower-case kebab-case review name.
  --repo <owner/name> Pull request repository. Defaults to origin and must
                      match the checkout's origin repository.
  --root <path>       Review worktree root. Defaults to ../<repo>-review-worktrees.
  --refresh           Replace an existing clean review worktree with the current PR head.
  -h, --help          Show this help text.
EOF
            ;;
        prune)
            cat <<'EOF'
Usage:
  basectl gh review prune [options]

Purpose:
  Prune Base-owned detached review worktrees and their namespaced local refs.

Options:
  --dry-run           Preview removals (default).
  --yes               Apply the preview.
  --closed-unmerged   Include clean worktrees for closed, unmerged PRs.
  --pr <number>       Restrict the scan to one pull request.
  --root <path>       Review worktree root. Defaults to ../<repo>-review-worktrees.
  -h, --help          Show this help text.
EOF
            ;;
        *)
            return 1
            ;;
    esac
}

base_gh_review_usage_error() {
    local command="$1"
    local message="$2"

    base_gh_error "$message"
    base_gh_review_leaf_usage "$command" >&2
    return 2
}

base_gh_review_validate_number() {
    local number="$1"

    [[ "$number" =~ ^[1-9][0-9]*$ ]]
}

base_gh_review_validate_slug() {
    local slug="$1"

    [[ "$slug" =~ $BASE_GH_REVIEW_SLUG_PATTERN ]]
}

base_gh_review_repo_root() {
    git rev-parse --show-toplevel 2>/dev/null
}

base_gh_review_common_dir() {
    local repo_root common_dir

    repo_root="$(base_gh_review_repo_root)" || return 1
    common_dir="$(git rev-parse --git-common-dir 2>/dev/null)" || return 1
    if [[ "$common_dir" != /* ]]; then
        common_dir="$repo_root/$common_dir"
    fi
    (cd "$common_dir" && pwd -P)
}

base_gh_review_metadata_dir() {
    local common_dir

    common_dir="$(base_gh_review_common_dir)" || return 1
    printf '%s/base-review/worktrees\n' "$common_dir"
}

base_gh_review_default_root() {
    local common_dir repo_root repo_name repo_parent

    common_dir="$(base_gh_review_common_dir)" || return 1
    repo_root="$(dirname "$common_dir")"
    repo_name="$(basename "$repo_root")"
    repo_parent="$(dirname "$repo_root")"
    printf '%s/%s-review-worktrees\n' "$repo_parent" "$repo_name"
}

base_gh_review_resolve_root() {
    local requested="${1:-}"
    local root

    if [[ -n "$requested" ]]; then
        root="$requested"
    else
        root="$(base_gh_review_default_root)" || return 1
    fi
    mkdir -p "$root" || return 1
    (cd "$root" && pwd -P)
}

base_gh_review_metadata_path() {
    local id="$1"
    local metadata_dir

    metadata_dir="$(base_gh_review_metadata_dir)" || return 1
    printf '%s/%s.json\n' "$metadata_dir" "$id"
}

base_gh_review_now() {
    printf '%(%Y-%m-%dT%H:%M:%SZ)T\n' -1
}

base_gh_review_ref() {
    local number="$1"
    local slug="$2"

    printf '%s/%s/%s\n' "$BASE_GH_REVIEW_REF_PREFIX" "$number" "$slug"
}

base_gh_review_id() {
    local number="$1"
    local slug="$2"

    printf 'pr-%s-%s\n' "$number" "$slug"
}

base_gh_review_path() {
    local root="$1"
    local number="$2"
    local slug="$3"

    printf '%s/%s\n' "$root" "$(base_gh_review_id "$number" "$slug")"
}

base_gh_review_ref_exists() {
    local ref="$1"

    git show-ref --verify --quiet "$ref"
}

base_gh_review_write_metadata() {
    local metadata_path="$1"
    local repo="$2"
    local number="$3"
    local slug="$4"
    local review_ref="$5"
    local worktree_path="$6"
    local head_sha="$7"
    local created_at="$8"
    local metadata_dir temporary_path

    metadata_dir="$(dirname "$metadata_path")"
    mkdir -p "$metadata_dir" || return 1
    temporary_path="$metadata_dir/.${number}-${slug}.json.tmp.$$"
    jq -n \
        --arg kind base-review-worktree \
        --arg repo "$repo" \
        --arg number "$number" \
        --arg slug "$slug" \
        --arg review_ref "$review_ref" \
        --arg worktree_path "$worktree_path" \
        --arg head_sha "$head_sha" \
        --arg created_at "$created_at" \
        '{kind:$kind,schema:1,repository:$repo,pull_request:($number|tonumber),slug:$slug,review_ref:$review_ref,worktree_path:$worktree_path,head_sha:$head_sha,created_at:$created_at}' \
        > "$temporary_path" || {
        rm -f "$temporary_path"
        return 1
    }
    mv -f "$temporary_path" "$metadata_path"
}

base_gh_review_remove_existing() {
    local worktree_path="$1"
    local review_ref="$2"
    local metadata_path="$3"

    if [[ -e "$worktree_path" ]]; then
        base_gh_worktree_is_valid "$worktree_path" || {
            base_gh_error "Cannot refresh review worktree '$worktree_path': path is not a valid Git worktree."
            return 1
        }
        base_gh_worktree_dirty "$worktree_path" && {
            base_gh_error "Cannot refresh review worktree '$worktree_path': worktree is dirty."
            return 1
        }
        git worktree remove "$worktree_path" || {
            base_gh_error "Unable to remove existing review worktree '$worktree_path'."
            return 1
        }
    fi
    if base_gh_review_ref_exists "$review_ref"; then
        git update-ref -d "$review_ref" || {
            base_gh_error "Unable to remove existing review ref '$review_ref'."
            return 1
        }
    fi
    rm -f "$metadata_path"
}

base_gh_review_fetch() {
    local number="${1:-}"
    local repo="" slug="" root="" review_root="" review_id review_ref worktree_path metadata_path
    local pr_json head_sha base_repo state created_at actual_sha origin_repo
    local refresh=0 review_ref_exists=0
    local -a parser_args=() positionals=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "name|value|--name"
        "repo|value|--repo"
        "root|value|--root"
        "refresh|flag|--refresh"
    )
    local -A parsed_options=()

    if [[ "$number" == -h || "$number" == --help ]]; then
        base_gh_review_leaf_usage fetch
        return 0
    fi
    [[ -n "$number" ]] || {
        base_gh_review_usage_error fetch "Missing pull request number."
        return $?
    }
    shift
    while (($#)); do
        case "$1" in
            --name|--repo|--root)
                (($# > 1)) || {
                    base_gh_review_usage_error fetch "Option '$1' requires an argument."
                    return $?
                }
                parser_args+=("$1" "$2")
                shift 2
                ;;
            --refresh)
                parser_args+=("$1")
                shift
                ;;
            -h|--help)
                base_gh_review_leaf_usage fetch
                return 0
                ;;
            *)
                positionals+=("$1")
                shift
                ;;
        esac
    done
    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_gh_review_usage_error fetch "Could not parse review fetch arguments."
        return $?
    fi
    if ((${#positionals[@]} > 0)); then
        base_gh_review_usage_error fetch "Unknown option '${positionals[0]}'."
        return $?
    fi
    base_gh_review_validate_number "$number" || {
        base_gh_review_usage_error fetch "Pull request number must be a positive integer."
        return $?
    }
    slug="${parsed_options[name]:-}"
    [[ -n "$slug" ]] || {
        base_gh_review_usage_error fetch "Missing required --name."
        return $?
    }
    base_gh_review_validate_slug "$slug" || {
        base_gh_review_usage_error fetch "Review name must be lower-case kebab-case."
        return $?
    }
    repo="${parsed_options[repo]:-}"
    if [[ -n "$repo" ]]; then
        repo="$(base_gh_normalize_github_repo "$repo")" || {
            base_gh_error "Invalid GitHub repository '$repo'."
            return 2
        }
    else
        repo="$(base_gh_infer_github_repo)" || {
            base_gh_error "Unable to infer the GitHub repository from origin."
            return 1
        }
    fi
    root="${parsed_options[root]:-}"
    review_root="$(base_gh_review_resolve_root "$root")" || {
        base_gh_error "Unable to prepare the review worktree root."
        return 1
    }
    refresh="${parsed_options[refresh]:-0}"
    review_id="$(base_gh_review_id "$number" "$slug")"
    review_ref="$(base_gh_review_ref "$number" "$slug")"
    worktree_path="$(base_gh_review_path "$review_root" "$number" "$slug")"
    metadata_path="$(base_gh_review_metadata_path "$review_id")"

    base_gh_require_command jq || return 1
    pr_json="$(base_cli_gh_run api "repos/$repo/pulls/$number" 2>&1)" || {
        base_gh_error "Unable to read pull request #$number from '$repo'."
        return 1
    }
    base_repo="$(jq -r '.base.repo.full_name // empty' <<< "$pr_json")"
    [[ "$base_repo" == "$repo" ]] || {
        base_gh_error "Pull request #$number is not based on '$repo'."
        return 1
    }
    head_sha="$(jq -r '.head.sha // empty' <<< "$pr_json")"
    [[ "$head_sha" =~ ^[0-9a-fA-F]{40}$ ]] || {
        base_gh_error "Pull request #$number did not provide a valid head SHA."
        return 1
    }
    state="$(jq -r '.state // empty' <<< "$pr_json")"
    [[ "$state" == open || "$state" == closed ]] || {
        base_gh_error "Pull request #$number returned an invalid state."
        return 1
    }

    origin_repo="$(base_gh_infer_github_repo)" || {
        base_gh_error "Unable to infer the GitHub repository from origin."
        return 1
    }
    if [[ "$origin_repo" != "$repo" ]]; then
        base_gh_error "Review fetch requires '$repo' to match the checkout's origin '$origin_repo'."
        return 1
    fi

    if base_gh_review_ref_exists "$review_ref"; then
        review_ref_exists=1
    fi
    if [[ -e "$metadata_path" || -e "$worktree_path" ]] || ((review_ref_exists)); then
        if ((refresh == 0)); then
            base_gh_error "Review checkout '$review_id' already exists; pass --refresh only for a clean checkout."
            return 1
        fi
        base_gh_review_remove_existing "$worktree_path" "$review_ref" "$metadata_path" || return $?
    fi

    git fetch origin "pull/$number/head:$review_ref" || {
        base_gh_error "Unable to fetch pull request #$number into '$review_ref'."
        return 1
    }
    git worktree add --detach "$worktree_path" "$review_ref" || {
        git update-ref -d "$review_ref" "$head_sha" >/dev/null 2>&1 || true
        base_gh_error "Unable to create detached review worktree '$worktree_path'."
        return 1
    }
    actual_sha="$(git -C "$worktree_path" rev-parse HEAD 2>/dev/null)" || actual_sha=""
    if [[ "$actual_sha" != "$head_sha" ]]; then
        git worktree remove "$worktree_path" >/dev/null 2>&1 || true
        git update-ref -d "$review_ref" "$actual_sha" >/dev/null 2>&1 || true
        base_gh_error "Fetched review head for #$number did not match the GitHub head SHA."
        return 1
    fi
    created_at="$(base_gh_review_now)"
    base_gh_review_write_metadata "$metadata_path" "$repo" "$number" "$slug" "$review_ref" "$worktree_path" "$head_sha" "$created_at" || {
        git worktree remove "$worktree_path" >/dev/null 2>&1 || true
        git update-ref -d "$review_ref" "$head_sha" >/dev/null 2>&1 || true
        base_gh_error "Unable to write review metadata '$metadata_path'."
        return 1
    }

    printf 'CREATED %s\n' "$worktree_path"
    printf '  PR:    #%s (%s)\n' "$number" "$state"
    printf '  Ref:   %s\n' "$review_ref"
    printf '  Head:  %s\n' "$head_sha"
    printf '  State: detached\n'
}

base_gh_review_metadata_valid() {
    local metadata_path="$1"

    jq -e '
        .kind == "base-review-worktree" and
        .schema == 1 and
        (.repository | type == "string" and length > 0) and
        (.pull_request | type == "number" and . >= 1 and floor == .) and
        (.slug | type == "string" and test("^[a-z0-9]+(-[a-z0-9]+)*$")) and
        (.review_ref | type == "string" and test("^refs/base-review/pr/[1-9][0-9]*/[a-z0-9]+(-[a-z0-9]+)*$")) and
        (.worktree_path | type == "string" and startswith("/")) and
        (.head_sha | type == "string" and test("^[0-9a-fA-F]{40}$")) and
        (.created_at | type == "string" and length > 0)
    ' "$metadata_path" >/dev/null 2>&1
}

base_gh_review_pr_state() {
    local repo="$1"
    local number="$2"
    local output_var="$3"
    local sha_var="$4"
    local pr_json pr_state merged_at head_sha

    pr_json="$(base_cli_gh_run api "repos/$repo/pulls/$number" 2>&1)" || {
        if [[ "$pr_json" == *"404"* || "$pr_json" == *"Not Found"* ]]; then
            printf -v "$output_var" '%s' missing
            printf -v "$sha_var" '%s' ''
            return 0
        fi
        return 2
    }
    pr_state="$(jq -r '.state // empty' <<< "$pr_json")"
    merged_at="$(jq -r '.merged_at // empty' <<< "$pr_json")"
    head_sha="$(jq -r '.head.sha // empty' <<< "$pr_json")"
    if [[ -n "$merged_at" ]]; then
        pr_state=merged
    elif [[ "$pr_state" == closed ]]; then
        pr_state=closed_unmerged
    elif [[ "$pr_state" == open ]]; then
        pr_state=open
    else
        return 2
    fi
    printf -v "$output_var" '%s' "$pr_state"
    printf -v "$sha_var" '%s' "$head_sha"
}

base_gh_review_prune() {
    local root="" review_root metadata_dir metadata_path
    local dry_run=1 dry_run_requested=0 yes=0 closed_unmerged=0 pr_filter=""
    local number slug repo current_repo review_ref worktree_path head_sha created_at id
    local state current_sha physical_root physical_path actual_sha
    local removed=0 skipped_open=0 skipped_closed=0 skipped_dirty=0 skipped_stale=0 skipped_orphan=0 failed=0
    local metadata_id
    local -a parser_args=() positionals=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "dry_run|flag|--dry-run"
        "yes|flag|--yes"
        "closed_unmerged|flag|--closed-unmerged"
        "pr|value|--pr"
        "root|value|--root"
    )
    local -A parsed_options=() seen_paths=() seen_refs=()

    while (($#)); do
        case "$1" in
            --dry-run|--yes|--closed-unmerged)
                parser_args+=("$1")
                shift
                ;;
            --pr|--root)
                (($# > 1)) || {
                    base_gh_review_usage_error prune "Option '$1' requires an argument."
                    return $?
                }
                parser_args+=("$1" "$2")
                shift 2
                ;;
            -h|--help)
                base_gh_review_leaf_usage prune
                return 0
                ;;
            *)
                positionals+=("$1")
                shift
                ;;
        esac
    done
    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_gh_review_usage_error prune "Could not parse review prune arguments."
        return $?
    fi
    if ((${#positionals[@]} > 0)); then
        base_gh_review_usage_error prune "Unknown option '${positionals[0]}'."
        return $?
    fi
    dry_run_requested="${parsed_options[dry_run]:-0}"
    yes="${parsed_options[yes]:-0}"
    closed_unmerged="${parsed_options[closed_unmerged]:-0}"
    pr_filter="${parsed_options[pr]:-}"
    if [[ -n "$pr_filter" ]]; then
        base_gh_review_validate_number "$pr_filter" || {
            base_gh_review_usage_error prune "--pr must be a positive integer."
            return $?
        }
    fi
    if ((dry_run_requested && yes)); then
        base_gh_review_usage_error prune "Options '--dry-run' and '--yes' cannot be used together."
        return $?
    fi
    ((yes)) && dry_run=0

    base_gh_require_git_repo || return 1
    base_gh_require_command jq || return 1
    current_repo="$(base_gh_infer_github_repo)" || {
        base_gh_error "Unable to infer the GitHub repository from origin."
        return 1
    }
    root="${parsed_options[root]:-}"
    review_root="$(base_gh_review_resolve_root "$root")" || {
        base_gh_error "Unable to prepare the review worktree root."
        return 1
    }
    physical_root="$(base_gh_resolve_physical_path "$review_root")" || return 1
    metadata_dir="$(base_gh_review_metadata_dir)" || return 1
    [[ "$dry_run" -eq 1 ]] && printf '[DRY-RUN] Review prune preview.\n'
    printf 'Review worktrees\n'

    if [[ -d "$metadata_dir" ]]; then
        while IFS= read -r metadata_path; do
            [[ -n "$metadata_path" ]] || continue
            metadata_id="$(basename "$metadata_path" .json)"
            if ! base_gh_review_metadata_valid "$metadata_path"; then
                printf 'SKIP   %s  invalid metadata; retained\n' "$metadata_path"
                skipped_orphan=$((skipped_orphan + 1))
                continue
            fi
            number="$(jq -r '.pull_request | tostring' "$metadata_path")"
            slug="$(jq -r '.slug' "$metadata_path")"
            repo="$(jq -r '.repository' "$metadata_path")"
            review_ref="$(jq -r '.review_ref' "$metadata_path")"
            worktree_path="$(jq -r '.worktree_path' "$metadata_path")"
            head_sha="$(jq -r '.head_sha' "$metadata_path")"
            created_at="$(jq -r '.created_at' "$metadata_path")"
            id="$(base_gh_review_id "$number" "$slug")"
            seen_paths["$worktree_path"]=1
            seen_refs["$review_ref"]=1

            if [[ "$metadata_id" != "$id" || "$repo" != "$current_repo" || "$review_ref" != "$(base_gh_review_ref "$number" "$slug")" || "$worktree_path" != "$(base_gh_review_path "$physical_root" "$number" "$slug")" ]]; then
                printf 'SKIP   %s  metadata ownership/path mismatch; retained\n' "$metadata_path"
                skipped_orphan=$((skipped_orphan + 1))
                continue
            fi
            [[ -z "$pr_filter" || "$number" == "$pr_filter" ]] || continue
            if [[ ! -e "$worktree_path" ]]; then
                printf 'SKIP   %s (%s)  worktree missing; metadata and ref retained\n' "$worktree_path" "$review_ref"
                skipped_orphan=$((skipped_orphan + 1))
                continue
            fi
            if ! base_gh_worktree_is_valid "$worktree_path"; then
                printf 'SKIP   %s (%s)  invalid worktree; retained\n' "$worktree_path" "$review_ref"
                skipped_orphan=$((skipped_orphan + 1))
                continue
            fi
            physical_path="$(base_gh_resolve_physical_path "$worktree_path")" || {
                printf 'SKIP   %s (%s)  path could not be resolved; retained\n' "$worktree_path" "$review_ref"
                skipped_orphan=$((skipped_orphan + 1))
                continue
            }
            if [[ "$physical_path" != "$physical_root"/* ]]; then
                printf 'SKIP   %s (%s)  worktree is outside the review root; retained\n' "$worktree_path" "$review_ref"
                skipped_orphan=$((skipped_orphan + 1))
                continue
            fi
            if git -C "$worktree_path" symbolic-ref -q HEAD >/dev/null 2>&1; then
                printf 'SKIP   %s (%s)  worktree is branch-attached; retained\n' "$worktree_path" "$review_ref"
                skipped_orphan=$((skipped_orphan + 1))
                continue
            fi
            if base_gh_worktree_dirty "$worktree_path"; then
                printf 'SKIP   %s (%s)  dirty worktree; retained\n' "$worktree_path" "$review_ref"
                skipped_dirty=$((skipped_dirty + 1))
                continue
            fi
            actual_sha="$(git -C "$worktree_path" rev-parse HEAD 2>/dev/null || true)"
            if [[ "$actual_sha" != "$head_sha" ]] || ! base_gh_review_ref_exists "$review_ref" || [[ "$(git rev-parse "$review_ref^{commit}" 2>/dev/null || true)" != "$head_sha" ]]; then
                printf 'SKIP   %s (%s)  review head/ref is stale or mismatched; retained\n' "$worktree_path" "$review_ref"
                skipped_stale=$((skipped_stale + 1))
                continue
            fi
            if ! base_gh_review_pr_state "$repo" "$number" state current_sha; then
                printf 'FAIL   %s (%s)  GitHub PR verification failed; retained\n' "$worktree_path" "$review_ref"
                failed=$((failed + 1))
                continue
            fi
            if [[ "$state" == missing ]]; then
                printf 'SKIP   %s (%s)  GitHub PR missing; retained\n' "$worktree_path" "$review_ref"
                skipped_orphan=$((skipped_orphan + 1))
                continue
            fi
            if [[ "$current_sha" != "$head_sha" ]]; then
                printf 'SKIP   %s (%s)  PR head changed since review checkout; retained\n' "$worktree_path" "$review_ref"
                skipped_stale=$((skipped_stale + 1))
                continue
            fi
            case "$state" in
                open)
                    printf 'SKIP   %s (%s)  open PR; retained\n' "$worktree_path" "$review_ref"
                    skipped_open=$((skipped_open + 1))
                    continue
                    ;;
                closed_unmerged)
                    if ((closed_unmerged == 0)); then
                        printf 'SKIP   %s (%s)  closed unmerged PR; retained\n' "$worktree_path" "$review_ref"
                        skipped_closed=$((skipped_closed + 1))
                        continue
                    fi
                    ;;
                merged)
                    ;;
                *)
                    printf 'FAIL   %s (%s)  unknown PR state; retained\n' "$worktree_path" "$review_ref"
                    failed=$((failed + 1))
                    continue
                    ;;
            esac

            if ((dry_run)); then
                printf '[DRY-RUN] REMOVE %s (%s); delete review ref and metadata\n' "$worktree_path" "$review_ref"
                removed=$((removed + 1))
                continue
            fi
            if ! git worktree remove "$worktree_path"; then
                printf 'FAIL   %s (%s)  worktree removal failed; retained\n' "$worktree_path" "$review_ref"
                failed=$((failed + 1))
                continue
            fi
            if ! git update-ref -d "$review_ref" "$head_sha"; then
                printf 'FAIL   %s (%s)  review ref removal failed; metadata retained\n' "$worktree_path" "$review_ref"
                failed=$((failed + 1))
                continue
            fi
            if ! rm -f "$metadata_path"; then
                printf 'FAIL   %s (%s)  metadata removal failed\n' "$worktree_path" "$review_ref"
                failed=$((failed + 1))
                continue
            fi
            printf 'REMOVE %s (%s)\n' "$worktree_path" "$review_ref"
            removed=$((removed + 1))
        done < <(find "$metadata_dir" -maxdepth 1 -type f -name '*.json' -print | sort)
    fi

    if [[ -d "$review_root" ]]; then
        for worktree_path in "$review_root"/pr-*; do
            [[ -d "$worktree_path" ]] || continue
            id="$(basename "$worktree_path")"
            [[ "$id" =~ $BASE_GH_REVIEW_ID_PATTERN ]] || continue
            [[ -n "$pr_filter" && "$id" != pr-${pr_filter}-* ]] && continue
            [[ ${seen_paths["$worktree_path"]+seen} ]] && continue
            printf 'SKIP   %s  no review metadata; retained\n' "$worktree_path"
            skipped_orphan=$((skipped_orphan + 1))
        done
    fi
    while IFS= read -r review_ref; do
        [[ -n "$review_ref" ]] || continue
        [[ ${seen_refs["$review_ref"]+seen} ]] && continue
        [[ -n "$pr_filter" && "$review_ref" != "$BASE_GH_REVIEW_REF_PREFIX/$pr_filter/"* ]] && continue
        printf 'SKIP   %s  no review metadata; retained\n' "$review_ref"
        skipped_orphan=$((skipped_orphan + 1))
    done < <(git for-each-ref --format='%(refname)' "$BASE_GH_REVIEW_REF_PREFIX")

    printf 'Summary: %s %s, %s skipped open, %s skipped closed-unmerged, %s skipped dirty, %s skipped stale, %s skipped orphaned/unowned, %s failed.\n' \
        "$removed" "$([[ "$dry_run" -eq 1 ]] && printf 'would remove' || printf 'removed')" \
        "$skipped_open" "$skipped_closed" "$skipped_dirty" "$skipped_stale" "$skipped_orphan" "$failed"
    if ((dry_run)); then
        printf 'Run with --yes to apply these changes.\n'
    fi
    ((failed == 0))
}

base_gh_review_main() {
    local command="${1:-}"
    shift || true

    case "$command" in
        fetch)
            base_gh_review_fetch "$@"
            ;;
        prune)
            base_gh_review_prune "$@"
            ;;
        -h|--help|help|"")
            base_gh_review_usage
            ;;
        *)
            base_gh_usage_error base_gh_review_usage "Unknown gh review command '$command'."
            return $?
            ;;
    esac
}
