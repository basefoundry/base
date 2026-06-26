#!/usr/bin/env bash

[[ -n "${_base_update_subcommand_sourced:-}" ]] && return 0
_base_update_subcommand_sourced=1
readonly _base_update_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_update_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl update [project] [options]

Options:
  --dry-run   Show what would happen without pulling or running setup.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Update a Base-managed project from Git, or update Base through Homebrew for
  Homebrew installs, then run basectl setup for the selected project.

Notes:
  - When project is omitted, Base updates project 'base'.
  - The selected project repository must be on its default branch.
  - Tracked project files must be clean; untracked files are left to Git's normal
    pull-time overwrite protection.
  - Homebrew installs update only project 'base' through the Base formula:
    brew upgrade basefoundry/base/base
  - If Homebrew requires tap trust, trust basefoundry/base before upgrading:
    brew trust basefoundry/base
EOF
}

base_update_usage_error() {
    print_error "$*"
    base_update_subcommand_usage >&2
    return 2
}

base_update_source_git_library() {
    import_base_lib git/lib_git.sh
}

base_update_homebrew_package() {
    printf '%s\n' "basefoundry/base/base"
}

base_update_homebrew_tap() {
    printf '%s\n' "basefoundry/base"
}

base_update_homebrew_bash_libs_package() {
    printf '%s\n' "basefoundry/base/base-bash-libs"
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

base_update_homebrew_requires_tap_trust() {
    local config_output

    [[ -n "${HOMEBREW_NO_REQUIRE_TAP_TRUST:-}" ]] && return 1
    [[ -n "${HOMEBREW_REQUIRE_TAP_TRUST:-}" ]] && return 0

    config_output="$(brew config 2>/dev/null)" || return 1
    [[ "$config_output" == *"HOMEBREW_REQUIRE_TAP_TRUST: set"* ]]
}

base_update_json_python_bin() {
    local candidate

    if [[ -n "${BASE_UPDATE_JSON_PYTHON:-}" && -x "${BASE_UPDATE_JSON_PYTHON:-}" ]]; then
        printf '%s\n' "$BASE_UPDATE_JSON_PYTHON"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi

    for candidate in \
        "/opt/homebrew/opt/$(setup_python_formula)/bin/python3" \
        "/usr/local/opt/$(setup_python_formula)/bin/python3" \
        /usr/bin/python3; do
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

base_update_homebrew_trust_contains() {
    local trust_json="$1"
    local target="$2"
    local python_bin

    python_bin="$(base_update_json_python_bin)" || return 1
    TRUST_JSON="$trust_json" TRUST_TARGET="$target" "$python_bin" - <<'PY'
import json
import os
import sys

try:
    data = json.loads(os.environ["TRUST_JSON"])
except (KeyError, json.JSONDecodeError):
    sys.exit(1)

target = os.environ.get("TRUST_TARGET", "")


def entry_matches(entry):
    if isinstance(entry, str):
        return entry == target
    if isinstance(entry, dict):
        return any(entry.get(key) == target for key in ("name", "full_name", "tap", "token"))
    return False


for key in ("taps", "formulae"):
    entries = data.get(key, [])
    if isinstance(entries, list) and any(entry_matches(entry) for entry in entries):
        sys.exit(0)

sys.exit(1)
PY
}

base_update_homebrew_trust_satisfied() {
    local bash_libs_package
    local tap
    local trust_json

    base_update_homebrew_requires_tap_trust || return 0

    trust_json="$(brew trust --json v1 2>/dev/null)" || return 0
    tap="$(base_update_homebrew_tap)"
    bash_libs_package="$(base_update_homebrew_bash_libs_package)"

    base_update_homebrew_trust_contains "$trust_json" "$tap" && return 0
    base_update_homebrew_trust_contains "$trust_json" "$bash_libs_package" && return 0

    return 1
}

base_update_report_homebrew_trust_required() {
    local bash_libs_package
    local tap

    tap="$(base_update_homebrew_tap)"
    bash_libs_package="$(base_update_homebrew_bash_libs_package)"

    log_error "Homebrew requires trust for '$tap' before upgrading Base's tap-owned Bash library dependency."
    log_error "Run 'brew trust $tap', then rerun 'basectl update'."
    log_error "To trust only the dependency formula instead, run 'brew trust --formula $bash_libs_package'."
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
    local base_home="$1"
    local dry_run="$2"
    local exit_code
    local package

    package="$(base_update_homebrew_package)"
    log_info "Detected Homebrew-managed Base install at '$base_home'."

    if ((dry_run)); then
        log_info "[DRY-RUN] Would run: brew upgrade $package"
        log_info "[DRY-RUN] Would run 'basectl setup' after the Homebrew upgrade with inherited Base environment cleared."
        return 0
    fi

    if ! command -v brew >/dev/null 2>&1; then
        log_error "Homebrew-managed Base install detected, but 'brew' is not available in PATH."
        return 1
    fi

    if ! base_update_homebrew_trust_satisfied; then
        base_update_report_homebrew_trust_required
        return 1
    fi

    log_info "Running Homebrew upgrade for $package."
    base_update_run_homebrew_upgrade "$package"
    exit_code=$?
    if ((exit_code != 0)); then
        log_error "Homebrew upgrade failed. If Homebrew refused to load '$package' or '$(base_update_homebrew_bash_libs_package)' from an untrusted tap, run 'brew trust $(base_update_homebrew_tap)' and retry."
        return "$exit_code"
    fi

    log_info "Running basectl setup after Homebrew upgrade."
    base_update_run_homebrew_setup "$base_home" "$package" || return $?

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
    local base_home="$1"
    local project="$2"

    "$base_home/bin/basectl" setup "$project"
}

base_update_resolve_project() {
    local base_home="$1"
    local project="$2"
    local wrapper="$base_home/bin/base-wrapper"
    local resolve_fields=()
    local resolve_output resolved_name resolved_root resolved_manifest

    if [[ -z "$project" ]]; then
        project=base
    fi

    if [[ "$project" == base ]]; then
        printf '%s\t%s\t%s\n' base "$base_home" "$base_home/base_manifest.yaml"
        return 0
    fi

    [[ -x "$wrapper" ]] || {
        log_error "Base Python wrapper '$wrapper' is missing or is not executable."
        return 1
    }

    resolve_output="$("$wrapper" --project base base_projects resolve "$project")" || return $?
    IFS=$'\t' read -r -a resolve_fields <<<"$resolve_output"
    resolved_name="${resolve_fields[0]:-}"
    resolved_root="${resolve_fields[1]:-}"
    resolved_manifest="${resolve_fields[2]:-}"
    [[ "$resolved_name" == "$project" && -n "$resolved_root" && -n "$resolved_manifest" ]] || {
        log_error "Unable to resolve Base project '$project'."
        return 1
    }

    printf '%s\t%s\t%s\n' "$resolved_name" "$resolved_root" "$resolved_manifest"
}

base_update_head_revision() {
    local repo="$1"
    git -C "$repo" rev-parse --short HEAD 2>/dev/null
}

base_update_subcommand_main() {
    local after_revision
    local base_home="${BASE_HOME:?}"
    local before_revision
    local branch
    local manifest_path
    local project=base
    local project_arg=""
    local repo
    local resolve_fields=()
    local resolve_output
    local resolved_project
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
            --*)
                base_update_usage_error "Unknown option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$project_arg" ]]; then
                    base_update_usage_error "The 'update' command accepts at most one project name."
                    return $?
                fi
                project_arg="$1"
                project="$1"
                ;;
        esac
        shift
    done

    resolve_output="$(base_update_resolve_project "$base_home" "$project")" || return $?
    IFS=$'\t' read -r -a resolve_fields <<<"$resolve_output"
    resolved_project="${resolve_fields[0]:-}"
    repo="${resolve_fields[1]:-}"
    manifest_path="${resolve_fields[2]:-}"
    [[ -n "$resolved_project" && -n "$repo" && -n "$manifest_path" ]] || {
        log_error "Unable to resolve Base project '$project'."
        return 1
    }

    log_debug "Running 'basectl update' for project '$resolved_project'."

    branch="$(base_update_current_branch "$repo")" || {
        if [[ "$resolved_project" == base ]] && base_update_is_homebrew_install "$base_home"; then
            base_update_homebrew_install "$base_home" "$dry_run"
            return $?
        fi
        log_error "Project '$resolved_project' repository '$repo' is not a Git repository."
        return 1
    }
    update_branch="$(base_update_default_branch "$repo")" || {
        log_error "Unable to determine the default branch for project '$resolved_project'."
        return 1
    }
    if [[ "$branch" != "$update_branch" ]]; then
        log_error "Project '$resolved_project' update only runs on default branch '$update_branch'; current branch is '$branch'."
        return 1
    fi

    if ! base_update_worktree_clean "$repo"; then
        log_error "Project '$resolved_project' repository has tracked local changes. Commit, stash, or remove them before running basectl update."
        return 1
    fi
    if base_update_has_untracked_files "$repo"; then
        log_warn "Project '$resolved_project' repository has untracked files. Continuing because tracked files are clean."
    fi

    if ((dry_run)); then
        log_info "[DRY-RUN] Would update project '$resolved_project' repository at '$repo'."
        log_info "[DRY-RUN] Would run 'basectl setup $resolved_project' after updating."
        return 0
    fi

    base_update_source_git_library || return 1
    before_revision="$(base_update_head_revision "$repo")" || {
        log_error "Unable to read current revision for project '$resolved_project'."
        return 1
    }

    log_info "Updating project '$resolved_project' repository at '$repo'."
    git_update_repo "$repo" "" "$update_branch" || return 1
    after_revision="$(base_update_head_revision "$repo")" || {
        log_error "Unable to read updated revision for project '$resolved_project'."
        return 1
    }

    if [[ "$before_revision" == "$after_revision" ]]; then
        log_info "Project '$resolved_project' repository is already up to date on '$update_branch' at '$after_revision'."
    else
        log_info "Project '$resolved_project' repository updated from '$before_revision' to '$after_revision' on '$update_branch'."
    fi

    log_info "Running basectl setup $resolved_project after update."
    base_update_run_setup "$base_home" "$resolved_project" || return $?
    log_info "Project '$resolved_project' update is complete."
}
