# shellcheck shell=bash
#
# lib_git.sh: Git operations
#

#
# Returns success when tracked changes are limited to one repo-relative path.
#
# @param $1 allowed_path Path in repository root that may be dirty (for example "shared").
#
_git_only_path_dirty() {
    local allowed_path="$1"
    local status_output line path

    status_output="$(git status --porcelain --untracked-files=no --ignore-submodules=none)"
    [[ -z "$status_output" ]] && return 1

    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        path="${line:3}"
        if [[ "$path" == *" -> "* ]]; then
            path="${path#* -> }"
        fi
        if [[ "$path" != "$allowed_path" ]]; then
            return 1
        fi
    done <<< "$status_output"

    return 0
}

#
# Safely updates a Git repository and its submodules after checking if the current branch is 'master'.
#
# @param $1 git_repo           The path to the local git repository.
# @param $2 allowed_dirty_path Optional repo-relative path that may be dirty.
#
git_update_repo() {
    local git_repo="$1"
    local allowed_dirty_path="${2:-}"
    local git_log

    if [[ -z "$git_repo" ]]; then
        log_error "No git repository path provided."
        log_info "Usage: update_repo /path/to/repo [allowed_dirty_path]"
        return 1
    fi

    if [[ ! -d "$git_repo" ]]; then
        log_error "Git repo not found at '$git_repo'"
        return 1
    fi

    git_log=$(mktemp -p /tmp)
    if ! pushd "$git_repo" > /dev/null; then
        # If cd fails, we can't proceed.
        return 1
    fi

    # Check if it's a valid git repo
    if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        log_error "'$git_repo' is not a Git repository."
        popd >/dev/null || return 1
        return 1
    fi

    # Make sure the current branch is master
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$current_branch" != "master" ]]; then
        log_debug "Current branch of '$git_repo' is '${current_branch}', not 'master'. Skipping update."
        popd >/dev/null || return 1
        return 1
    fi

    local dirty=false
    if ! git diff --quiet; then
        dirty=true
    fi
    if ! git diff --cached --quiet; then
        dirty=true
    fi
    if [[ "$dirty" == true ]]; then
        if [[ -n "$allowed_dirty_path" ]] && _git_only_path_dirty "$allowed_dirty_path"; then
            log_debug "Repo '$git_repo' only has tracked changes in '$allowed_dirty_path'; attempting git pull."
        else
            log_debug "Repo '$git_repo' has local changes; skipping auto-update. Commit or stash to enable git pull."
            popd >/dev/null || return 1
            return 0
        fi
    fi

    # sometimes git pull throws warnings and we need a second git pull to address it
    if ! { git pull || git pull; } >"$git_log" 2>&1; then
        log_error "git pull failed on repo '$git_repo'"
        [[ -s "$git_log" ]] && log_info_file "$git_log"
        popd >/dev/null || return 1
        return 1
    fi

    # it is safe to run submodule commands even if the repo has no submodules
    if ! { git submodule init && git submodule sync && git submodule update; } >/dev/null; then
        log_error "git submodule update failed on repo '$git_repo'"
        [[ -s "$git_log" ]] && log_info_file "$git_log"
        popd >/dev/null || return 1
        return 1
    fi

    log_debug "Git repo '$git_repo' updated to latest master"
    popd >/dev/null || return 1
    return 0
}

#
# Gets the currently checked-out branch of a Git repository without using a subshell.
#
# This function safely checks a directory, determines if it's a Git repository,
# and returns the current branch name via a name reference (nameref).
#
# @param $1 target_dir     The path to the directory to check.
# @param $2 result_var_name The name of the variable in the calling scope
#                          that will receive the output.
#
# Returns:
#   - The branch name (e.g., "master", "feature/login") is stored in the result variable.
#   - "detached head" if the repository is in a detached HEAD state.
#   - An empty string "" if the directory doesn't exist or is not a Git repo.
#   - The function itself returns an exit code of 0 on success, 1 on invalid usage.
#
git_get_current_branch() {
    local target_dir="$1"

    # --- Argument Validation ---
    if [[ -z "$target_dir" || -z "${2:-}" ]]; then
        log_error "Usage: get_git_branch <directory> <result_variable_name>"
        return 1
    fi

    # Create a name reference to the variable name passed as the second argument.
    local -n result_var="$2"
    result_var=""

    if [[ ! -d "$target_dir" ]]; then
        return 1
    fi

    # --- Core Logic without Subshell ---
    # Use pushd to change directory and add the current dir to a stack.
    # Redirect output to /dev/null to keep it clean.
    if ! pushd "$target_dir" > /dev/null; then
        # If cd fails, we can't proceed.
        return 1
    fi

    # Check if we are inside a Git repository.
    if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        # Not a Git repo, result is already an empty string.
        popd >/dev/null || return 1
        return 0
    fi

    # Use 'git symbolic-ref' to get the branch name.
    # It's the most reliable way to distinguish a branch from a detached HEAD.
    # -q (--quiet) suppresses errors and returns a non-zero exit code on failure.
    local branch_name
    if branch_name=$(git symbolic-ref --short -q HEAD); then
        # Success: We are on a named branch.
        result_var="$branch_name"
    else
        # Failure: We are in a detached HEAD state.
        result_var="detached head"
    fi

    popd >/dev/null || return 1
    return 0
}

#
# Checks whether a script appears up to date with its git upstream and logs status.
#
# @param $1 script_path The path to a script file tracked in a git repo.
#
# Returns:
#   - 0 if up to date or the check is skipped (no git, no upstream, not a repo).
#   - 1 on invalid usage.
#   - 2 if the repo is behind its upstream (script may be stale).
#   - 3 if the script has local modifications.
#
check_script_up_to_date() {
    local script_path="$1"
    if [[ -z "$script_path" ]]; then
        log_error "Usage: check_script_up_to_date <script_path>"
        return 1
    fi

    if [[ ! -e "$script_path" ]]; then
        log_warn "Script '$script_path' not found; skipping latest-version check."
        return 0
    fi

    if ! command -v git &> /dev/null; then
        log_info "git not available; skipping latest-version check."
        return 0
    fi

    local script_dir repo_root prefix rel_path
    script_dir=$(dirname "$script_path")
    repo_root=$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null) || {
        log_info "Not in a git repo; skipping latest-version check."
        return 0
    }
    prefix=$(git -C "$script_dir" rev-parse --show-prefix 2>/dev/null) || {
        log_info "Unable to resolve repo-relative path; skipping latest-version check."
        return 0
    }
    rel_path="${prefix}$(basename "$script_path")"

    if ! git -C "$repo_root" ls-files --error-unmatch "$rel_path" >/dev/null 2>&1; then
        log_info "Script '$rel_path' is not tracked in git; skipping latest-version check."
        return 0
    fi

    local dirty=false
    if ! git -C "$repo_root" diff --quiet -- "$rel_path"; then
        dirty=true
    fi
    if ! git -C "$repo_root" diff --cached --quiet -- "$rel_path"; then
        dirty=true
    fi
    if [[ "$dirty" == true ]]; then
        log_warn "Script '$rel_path' has local modifications; version may not match repo."
    fi

    local upstream behind ahead
    upstream=$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null) || {
        log_info "No upstream branch configured; skipping latest-version check."
        return 0
    }

    behind=$(git -C "$repo_root" rev-list --count HEAD.."$upstream" 2>/dev/null)
    ahead=$(git -C "$repo_root" rev-list --count "$upstream"..HEAD 2>/dev/null)
    if [[ -n "$behind" && "$behind" -gt 0 ]]; then
        log_warn "Repository is $behind commit(s) behind $upstream. Script may be out of date."
        return 2
    elif [[ -n "$ahead" && "$ahead" -gt 0 ]]; then
        log_info "Repository is $ahead commit(s) ahead of $upstream."
    else
        log_info "Repository is up to date with $upstream."
    fi

    if [[ "$dirty" == true ]]; then
        return 3
    fi

    return 0
}
