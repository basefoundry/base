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
  Update Base from Git for source checkouts, or through Homebrew for Homebrew
  installs, then run basectl setup.

Notes:
  - The repository must be on its default branch.
  - Tracked Base files must be clean; untracked files are left to Git's normal
    pull-time overwrite protection.
  - Homebrew installs update only the Base formula:
    brew upgrade codeforester/base/base
EOF
}

base_update_source_git_library() {
    import_base_lib git/lib_git.sh
}

base_update_homebrew_package() {
    printf '%s\n' "codeforester/base/base"
}

base_update_is_homebrew_install() {
    local base_home="$1"

    case "$base_home" in
        */opt/base/libexec|*/Cellar/base/*/libexec)
            ;;
        *)
            return 1
            ;;
    esac

    [[ -d "$base_home" ]] || return 1
    [[ -f "$base_home/base_init.sh" || -x "$base_home/bin/basectl" ]]
}

base_update_homebrew_prefix() {
    local package="$1"
    local prefix

    if prefix="$(brew --prefix base 2>/dev/null)" && [[ -n "$prefix" ]]; then
        printf '%s\n' "$prefix"
        return 0
    fi

    if prefix="$(brew --prefix "$package" 2>/dev/null)" && [[ -n "$prefix" ]]; then
        printf '%s\n' "$prefix"
        return 0
    fi

    return 1
}

base_update_homebrew_basectl() {
    local base_home="$1"
    local package="$2"
    local basectl
    local prefix

    case "$base_home" in
        */opt/base/libexec)
            basectl="$base_home/bin/basectl"
            if [[ -x "$basectl" ]]; then
                printf '%s\n' "$basectl"
                return 0
            fi
            ;;
    esac

    if prefix="$(base_update_homebrew_prefix "$package")"; then
        basectl="$prefix/libexec/bin/basectl"
        if [[ -x "$basectl" ]]; then
            printf '%s\n' "$basectl"
            return 0
        fi

        basectl="$prefix/bin/basectl"
        if [[ -x "$basectl" ]]; then
            printf '%s\n' "$basectl"
            return 0
        fi
    fi

    basectl="$base_home/bin/basectl"
    if [[ -x "$basectl" ]]; then
        printf '%s\n' "$basectl"
        return 0
    fi

    return 1
}

base_update_run_homebrew_upgrade() {
    local package="$1"

    brew upgrade "$package"
}

base_update_run_homebrew_setup() {
    local base_home="$1"
    local package="$2"
    local basectl

    basectl="$(base_update_homebrew_basectl "$base_home" "$package")" || {
        log_error "Unable to locate Homebrew-managed basectl after upgrade."
        return 1
    }

    env \
        -u BASE_HOME \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_HOST \
        -u BASE_SHELL \
        -u BASE_PLATFORM_TOOLS_HOME \
        -u BASE_PLATFORM_TOOLS_BIN_DIR \
        -u BASE_PROJECT \
        -u BASE_PROJECT_ROOT \
        -u BASE_PROJECT_MANIFEST \
        -u BASE_PROJECT_VENV_DIR \
        "$basectl" setup
}

base_update_homebrew_install() {
    local dry_run="$1"
    local package

    package="$(base_update_homebrew_package)"
    log_info "Detected Homebrew-managed Base install at '$BASE_HOME'."

    if ((dry_run)); then
        log_info "[DRY-RUN] Would run: brew upgrade $package"
        log_info "[DRY-RUN] Would run 'basectl setup' after the Homebrew upgrade with inherited Base environment cleared."
        return 0
    fi

    if ! command -v brew >/dev/null 2>&1; then
        log_error "Homebrew-managed Base install detected, but 'brew' is not available in PATH."
        return 1
    fi

    log_info "Running Homebrew upgrade for $package."
    base_update_run_homebrew_upgrade "$package" || return $?

    log_info "Running basectl setup after Homebrew upgrade."
    base_update_run_homebrew_setup "$BASE_HOME" "$package" || return $?

    log_info "Base update is complete."
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
    [[ -z "$(git -C "$repo" status --porcelain --untracked-files=no --ignore-submodules=none)" ]]
}

base_update_has_untracked_files() {
    local repo="$1"
    [[ -n "$(git -C "$repo" ls-files --others --exclude-standard --directory --no-empty-directory)" ]]
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
        if base_update_is_homebrew_install "$BASE_HOME"; then
            base_update_homebrew_install "$dry_run"
            return $?
        fi
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
        log_error "Base repository has tracked local changes. Commit, stash, or remove them before running basectl update."
        return 1
    fi
    if base_update_has_untracked_files "$BASE_HOME"; then
        log_warn "Base repository has untracked files. Continuing because tracked files are clean."
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
