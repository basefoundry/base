#!/usr/bin/env bash

[[ -n "${_base_update_subcommand_sourced:-}" ]] && return
_base_update_subcommand_sourced=1
readonly _base_update_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_update_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl update [options]

Options:
  --dry-run   Show what would happen without pulling or running setup.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Update the Base repository from Git, then run basectl setup.

Notes:
  - The repository must be on its default branch.
  - The worktree must be clean, including untracked files.
EOF
}

base_update_source_git_library() {
    import_base_lib git/lib_git.sh
}

base_update_current_branch() {
    local repo="$1"
    git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null
}

base_update_default_branch() {
    local repo="$1"
    local default_branch

    if default_branch="$(git -C "$repo" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"; then
        default_branch="${default_branch#origin/}"
        if [[ -n "$default_branch" ]]; then
            printf '%s\n' "$default_branch"
            return 0
        fi
    fi

    if git -C "$repo" show-ref --verify --quiet refs/heads/main; then
        printf '%s\n' main
        return 0
    fi

    if git -C "$repo" show-ref --verify --quiet refs/heads/master; then
        printf '%s\n' master
        return 0
    fi

    return 1
}

base_update_worktree_clean() {
    local repo="$1"
    [[ -z "$(git -C "$repo" status --porcelain --untracked-files=normal --ignore-submodules=none)" ]]
}

base_update_run_setup() {
    "$BASE_HOME/bin/basectl" setup
}

base_update_head_revision() {
    local repo="$1"
    git -C "$repo" rev-parse --short HEAD 2>/dev/null
}

base_update_subcommand_main() {
    local after_revision
    local before_revision
    local branch
    local update_branch
    local dry_run=0

    while (($#)); do
        case "$1" in
            --dry-run)
                dry_run=1
                ;;
            -h|--help|help)
                base_update_subcommand_usage
                return 0
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            *)
                print_error "Unknown option '$1'."
                base_update_subcommand_usage >&2
                return 1
                ;;
        esac
        shift
    done

    log_debug "Running 'basectl update'."

    branch="$(base_update_current_branch "$BASE_HOME")" || {
        log_error "Base home '$BASE_HOME' is not a Git repository."
        return 1
    }
    update_branch="$(base_update_default_branch "$BASE_HOME")" || {
        log_error "Unable to determine the Base repository default branch."
        return 1
    }
    if [[ "$branch" != "$update_branch" ]]; then
        log_error "Base update only runs on default branch '$update_branch'; current branch is '$branch'."
        return 1
    fi

    if ! base_update_worktree_clean "$BASE_HOME"; then
        log_error "Base repository has local changes. Commit, stash, or remove them before running basectl update."
        return 1
    fi

    if ((dry_run)); then
        log_info "[DRY-RUN] Would update Base repository at '$BASE_HOME'."
        log_info "[DRY-RUN] Would run 'basectl setup' after updating."
        return 0
    fi

    base_update_source_git_library || return 1
    before_revision="$(base_update_head_revision "$BASE_HOME")" || {
        log_error "Unable to read current Base repository revision."
        return 1
    }

    log_info "Updating Base repository at '$BASE_HOME'."
    git_update_repo "$BASE_HOME" "" "$update_branch" || return 1
    after_revision="$(base_update_head_revision "$BASE_HOME")" || {
        log_error "Unable to read updated Base repository revision."
        return 1
    }

    if [[ "$before_revision" == "$after_revision" ]]; then
        log_info "Base repository is already up to date on '$update_branch' at '$after_revision'."
    else
        log_info "Base repository updated from '$before_revision' to '$after_revision' on '$update_branch'."
    fi

    log_info "Running basectl setup after update."
    base_update_run_setup || return $?
    log_info "Base update is complete."
}
