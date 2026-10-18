#!/usr/bin/env bash

if [[ -n "${_base_update_subcommand_sourced:-}" ]]; then
    # Source guards are shell-local. Ignore exported sentinels inherited from a
    # parent process so test and command shells still load their definitions.
    case "$(declare -p _base_update_subcommand_sourced 2>/dev/null)" in
        declare\ -*x*)
            unset _base_update_subcommand_sourced 2>/dev/null || return 0
            ;;
        *)
            return 0
            ;;
    esac
fi
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
  --project <name>  Select a project explicitly, including one named help.
  --release <tag>   Upgrade a clean detached source checkout to a later stable
                    published tag, for example v1.11.0.
  --dry-run   Show what would happen without pulling or running setup.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Update a Base-managed project from Git, or update Base through Homebrew for
  Homebrew installs. Git updates run setup when the selected project changes;
  Homebrew updates run setup when Base's installed version changes.

Notes:
  - When project is omitted, Base updates project 'base'.
  - The selected project repository must be on its default branch.
  - Tracked project files must be clean; untracked files are left to Git's normal
    pull-time overwrite protection.
  - Homebrew installs update only project 'base' through the Base formula:
    brew upgrade basefoundry/base/base
  - Stable tagged source installs use '--release <tag>'; they never follow
    'main' or another moving branch.
  - If Homebrew requires tap trust, trust basefoundry/base before upgrading:
    brew trust basefoundry/base
EOF
}

base_update_usage_error() {
    base_std_print_error "$*"
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
    local candidate
    local candidates=("base")
    local prefix

    if [[ -n "$package" && "$package" != "base" ]]; then
        candidates+=("$package")
    fi

    for candidate in "${candidates[@]}"; do
        if prefix="$(brew --prefix "$candidate" 2>/dev/null)" && [[ -n "$prefix" ]]; then
            printf '%s\n' "$prefix"
            return 0
        fi
    done

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

base_update_homebrew_installed_version_from_json() {
    local info_json="$1"
    local package="$2"
    local python_bin

    python_bin="$(base_update_json_python_bin)" || return 1
    INFO_JSON="$info_json" INFO_PACKAGE="$package" "$python_bin" - <<'PY'
import json
import os
import sys

package = os.environ.get("INFO_PACKAGE", "")
short_name = package.rsplit("/", 1)[-1] if package else ""

try:
    data = json.loads(os.environ["INFO_JSON"])
except (KeyError, json.JSONDecodeError):
    sys.exit(1)

formulae = data.get("formulae", [])
if not isinstance(formulae, list):
    sys.exit(1)

for formula in formulae:
    if not isinstance(formula, dict):
        continue
    names = {name for name in (formula.get("name"), formula.get("full_name")) if isinstance(name, str)}
    if package not in names and short_name not in names:
        continue

    linked_keg = formula.get("linked_keg")
    if isinstance(linked_keg, str) and linked_keg:
        print(linked_keg)
        sys.exit(0)

    installed_versions = [
        entry.get("version")
        for entry in formula.get("installed", [])
        if isinstance(entry, dict) and isinstance(entry.get("version"), str) and entry.get("version")
    ]
    if installed_versions:
        print(installed_versions[-1])
        sys.exit(0)

    sys.exit(1)

sys.exit(1)
PY
}

base_update_homebrew_installed_version() {
    local package="$1"
    local info_json

    info_json="$(brew info --json=v2 --installed "$package" 2>/dev/null)" || return 1
    base_update_homebrew_installed_version_from_json "$info_json" "$package"
}

base_update_homebrew_requires_tap_trust() {
    local config_output

    [[ -n "${HOMEBREW_NO_REQUIRE_TAP_TRUST:-}" ]] && return 1
    [[ -n "${HOMEBREW_REQUIRE_TAP_TRUST:-}" ]] && return 0

    config_output="$(brew config 2>/dev/null)" || return 1
    [[ "$config_output" == *"HOMEBREW_REQUIRE_TAP_TRUST: set"* ]]
}

base_update_json_python_bin() {
    local candidate python_path

    if [[ -n "${BASE_UPDATE_JSON_PYTHON:-}" && -x "${BASE_UPDATE_JSON_PYTHON:-}" ]]; then
        printf '%s\n' "$BASE_UPDATE_JSON_PYTHON"
        return 0
    fi

    if base_std_command_path python_path python3; then
        printf '%s\n' "$python_path"
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

    base_std_log_error "Homebrew requires trust for '$tap' before upgrading Base's tap-owned Bash library dependency."
    base_std_log_error "Run 'brew trust $tap', then rerun 'basectl update'."
    base_std_log_error "To trust only the dependency formula instead, run 'brew trust --formula $bash_libs_package'."
}

base_update_run_homebrew_setup() {
    local base_home="$1"
    local package="$2"
    local basectl

    basectl="$(base_update_homebrew_basectl "$base_home" "$package")" || {
        base_std_log_error "Unable to locate Homebrew-managed basectl after upgrade."
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
    local after_version
    local before_version
    local brew_path
    local exit_code
    local package

    package="$(base_update_homebrew_package)"
    base_std_log_info "Detected Homebrew-managed Base install at '$base_home'."

    if ((dry_run)); then
        base_std_log_info "[DRY-RUN] Would run: brew upgrade $package"
        base_std_log_info "[DRY-RUN] Would run 'basectl setup' if the Homebrew upgrade changes Base's installed version, with inherited Base environment cleared."
        return 0
    fi

    if ! base_std_command_path brew_path brew || [[ -z "$brew_path" ]]; then
        base_std_log_error "Homebrew-managed Base install detected, but 'brew' is not available in PATH."
        return 1
    fi

    if ! base_update_homebrew_trust_satisfied; then
        base_update_report_homebrew_trust_required
        return 1
    fi

    before_version="$(base_update_homebrew_installed_version "$package")" || {
        base_std_log_error "Unable to determine installed Homebrew version for $package before upgrade."
        return 1
    }

    base_std_log_info "Running Homebrew upgrade for $package."
    base_update_run_homebrew_upgrade "$package"
    exit_code=$?
    if ((exit_code != 0)); then
        base_std_log_error "Homebrew upgrade failed. If Homebrew refused to load '$package' or '$(base_update_homebrew_bash_libs_package)' from an untrusted tap, run 'brew trust $(base_update_homebrew_tap)' and retry."
        return "$exit_code"
    fi

    after_version="$(base_update_homebrew_installed_version "$package")" || {
        base_std_log_error "Unable to determine installed Homebrew version for $package after upgrade."
        return 1
    }

    if [[ "$before_version" == "$after_version" ]]; then
        base_std_log_info "Homebrew Base version is unchanged at '$after_version' after upgrade."
        base_std_log_info "Skipping basectl setup because the Homebrew Base version did not change."
    else
        base_std_log_info "Homebrew Base version changed from '$before_version' to '$after_version'."
        base_std_log_info "Running basectl setup after Homebrew upgrade."
        base_update_run_homebrew_setup "$base_home" "$package" || return $?
    fi

    base_std_log_info "Base update is complete."
}

base_update_current_branch() {
    local repo="$1"
    local branch

    base_git_get_current_branch "$repo" branch || return 1
    [[ -n "$branch" ]] || return 1
    printf '%s\n' "$branch"
}

base_update_default_branch() {
    local repo="$1"
    local default_branch

    base_git_detect_default_branch "$repo" default_branch || return 1
    printf '%s\n' "$default_branch"
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

    if [[ "$project" == help ]]; then
        "$base_home/bin/basectl" setup --project "$project"
    else
        "$base_home/bin/basectl" setup "$project"
    fi
}

base_update_resolve_project() {
    local base_home="$1"
    local project="$2"
    local output_name_var="$3"
    local output_root_var="$4"
    local output_manifest_var="$5"
    local wrapper="$base_home/bin/base-wrapper"
    local resolve_output resolved_name resolved_root resolved_manifest

    if [[ -z "$project" ]]; then
        project=base
    fi

    if [[ "$project" == base ]]; then
        resolved_name=base
        resolved_root="$base_home"
        resolved_manifest="$base_home/base_manifest.yaml"
    else
        [[ -x "$wrapper" ]] || {
            base_std_log_error "Base Python wrapper '$wrapper' is missing or is not executable."
            return 1
        }

        resolve_output="$("$wrapper" --project base base_projects resolve "$project" --format command-protocol)" || return $?
        base_command_protocol_decode_one project-route "$resolve_output" || return 1
        resolved_name="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
        resolved_root="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
        resolved_manifest="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
        [[ "$resolved_name" == "$project" && -n "$resolved_root" && -n "$resolved_manifest" ]] || {
            base_std_log_error "Unable to resolve Base project '$project'."
            return 1
        }
    fi

    printf -v "$output_name_var" '%s' "$resolved_name"
    printf -v "$output_root_var" '%s' "$resolved_root"
    printf -v "$output_manifest_var" '%s' "$resolved_manifest"
}

base_update_head_revision() {
    local repo="$1"
    git -C "$repo" rev-parse --short HEAD 2>/dev/null
}

base_update_release_tag_is_stable() {
    [[ "${1:-}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

base_update_release_tag_version() {
    local tag="${1#v}"
    local major minor patch

    IFS=. read -r major minor patch <<< "$tag"
    printf '%s %s %s\n' "$major" "$minor" "$patch"
}

base_update_release_target_is_later() {
    local current_tag="$1"
    local target_tag="$2"
    local current_major current_minor current_patch
    local target_major target_minor target_patch

    read -r current_major current_minor current_patch <<< "$(base_update_release_tag_version "$current_tag")"
    read -r target_major target_minor target_patch <<< "$(base_update_release_tag_version "$target_tag")"

    ((target_major > current_major)) ||
        { ((target_major == current_major && target_minor > current_minor)); } ||
        { ((target_major == current_major && target_minor == current_minor && target_patch > current_patch)); }
}

base_update_release_current_tag() {
    local repo="$1"
    local tag

    git -C "$repo" symbolic-ref --quiet --short HEAD >/dev/null 2>&1 && return 1
    tag="$(git -C "$repo" describe --tags --exact-match --match 'v[0-9]*.[0-9]*.[0-9]*' HEAD 2>/dev/null)" || return 1
    base_update_release_tag_is_stable "$tag" || return 1
    printf '%s\n' "$tag"
}

base_update_release_remote_commit() {
    local repo="$1"
    local tag="$2"
    local remote_output remote_line remote_status

    remote_output="$(git -C "$repo" ls-remote --exit-code origin "refs/tags/$tag^{}" 2>&1)"
    remote_status=$?
    if ((remote_status == 0)); then
        :
    elif ((remote_status == 2)); then
        remote_output="$(git -C "$repo" ls-remote --exit-code origin "refs/tags/$tag" 2>&1)"
        remote_status=$?
        if ((remote_status != 0)); then
            if ((remote_status == 2)); then
                return 2
            fi
            base_std_log_error "Unable to reach 'origin' while verifying published Base release tag '$tag': $remote_output"
            return 1
        fi
    else
        base_std_log_error "Unable to reach 'origin' while verifying published Base release tag '$tag': $remote_output"
        return 1
    fi

    remote_line="${remote_output%%$'\n'*}"
    [[ "$remote_line" == *$'\t'* ]] || return 1
    printf '%s\n' "${remote_line%%$'\t'*}"
}

base_update_release_fetch_tag() {
    local repo="$1"
    local tag="$2"
    local remote_commit local_commit resolved_commit remote_status

    remote_commit="$(base_update_release_remote_commit "$repo" "$tag")"
    remote_status=$?
    if ((remote_status != 0)); then
        if ((remote_status == 2)); then
            base_std_log_error "Published Base release tag '$tag' was not found on the 'origin' remote."
        fi
        return 1
    fi

    local_commit="$(git -C "$repo" rev-parse "refs/tags/$tag^{commit}" 2>/dev/null || true)"
    if [[ -n "$local_commit" && "$local_commit" != "$remote_commit" ]]; then
        base_std_log_error "Local tag '$tag' resolves to '$local_commit', but 'origin' resolves it to '$remote_commit'. Refusing to replace a conflicting local tag."
        return 1
    fi

    if [[ "$local_commit" != "$remote_commit" ]]; then
        git -C "$repo" fetch --no-tags origin "refs/tags/$tag:refs/tags/$tag" || {
            base_std_log_error "Unable to fetch verified published tag '$tag' from 'origin'."
            return 1
        }
    fi

    resolved_commit="$(git -C "$repo" rev-parse "refs/tags/$tag^{commit}" 2>/dev/null || true)"
    if [[ "$resolved_commit" != "$remote_commit" ]]; then
        base_std_log_error "Fetched tag '$tag' did not resolve to the verified remote commit '$remote_commit'."
        return 1
    fi
    printf '%s\n' "$resolved_commit"
}

base_update_release_tracked_worktree_clean() {
    local repo="$1"

    [[ -z "$(git -C "$repo" status --porcelain --untracked-files=no --ignore-submodules=none)" ]]
}

base_update_release_untracked_files_safe() {
    local repo="$1"
    local previous_commit="$2"
    local target_commit="$3"
    local target_tag="$4"
    local path

    while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        if [[ -e "$repo/$path" || -L "$repo/$path" ]] &&
            ! git -C "$repo" ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
            base_std_log_error "Untracked or ignored local path '$path' overlaps files changed by target release '$target_tag'; no checkout or environment changes were made. Move or save it before retrying."
            return 1
        fi
    done < <(git -C "$repo" diff --name-only --no-renames "$previous_commit" "$target_commit" --)
    return 0
}

base_update_release_report_trust_guidance() {
    local repo="$1"
    local previous_commit="$2"
    local target_commit="$3"
    local target_tag="$4"

    if git -C "$repo" diff --quiet "$previous_commit" "$target_commit" -- \
        base_manifest.yaml requirements-dev.txt; then
        return 0
    fi

    base_std_log_warn "Release '$target_tag' changes Base manifest or declared test requirements. Review with 'basectl trust status' before running 'basectl test base'; Base will not approve that trust change implicitly."
}

base_update_release_dry_run() {
    local repo="$1"
    local target_tag="$2"
    local current_tag
    local remote_commit
    local remote_status

    current_tag="$(base_update_release_current_tag "$repo" || true)"
    if [[ -z "$current_tag" ]]; then
        base_std_log_error "Stable tagged source upgrades require a clean detached checkout at an exact vMAJOR.MINOR.PATCH release tag. Use ordinary 'basectl update' for a mutable branch checkout."
        return 1
    fi
    if ! base_update_release_tracked_worktree_clean "$repo"; then
        base_std_log_error "Stable tagged source upgrade requires a clean checkout; no Git or environment changes would be made. Commit or save tracked local changes before retrying."
        return 1
    fi
    if [[ "$target_tag" != "$current_tag" ]] && ! base_update_release_target_is_later "$current_tag" "$target_tag"; then
        base_std_log_error "Target release '$target_tag' must be later than the current stable release '$current_tag'; no changes would be made."
        return 1
    fi
    remote_commit="$(base_update_release_remote_commit "$repo" "$target_tag")"
    remote_status=$?
    if ((remote_status != 0)); then
        if ((remote_status == 2)); then
            base_std_log_error "Published Base release tag '$target_tag' was not found on the 'origin' remote."
        fi
        return 1
    fi
    if [[ "$target_tag" == "$current_tag" ]]; then
        base_std_log_info "[DRY-RUN] Base source checkout is already at verified stable release '$current_tag' ('$remote_commit')."
        base_std_log_info "[DRY-RUN] Would run 'basectl setup' to reconcile the current release environment."
    else
        base_std_log_info "[DRY-RUN] Verified published tag '$target_tag' at commit '$remote_commit'."
        base_std_log_info "[DRY-RUN] Would move the clean detached Base checkout from '$current_tag' to '$target_tag', then run 'basectl setup'."
        base_std_log_info "[DRY-RUN] The real upgrade will also refuse an untracked or ignored local path that overlaps files changed by '$target_tag'."
    fi
}

base_update_release_source_install() {
    local base_home="$1"
    local repo="$2"
    local target_tag="$3"
    local current_tag
    local previous_commit
    local setup_status
    local target_commit

    current_tag="$(base_update_release_current_tag "$repo" || true)"
    if [[ -z "$current_tag" ]]; then
        base_std_log_error "Stable tagged source upgrades require a clean detached checkout at an exact vMAJOR.MINOR.PATCH release tag. Use ordinary 'basectl update' for a mutable branch checkout."
        return 1
    fi
    if ! base_update_release_tracked_worktree_clean "$repo"; then
        base_std_log_error "Stable tagged source upgrade requires a clean checkout; no Git or environment changes were made. Commit or save tracked local changes before retrying."
        return 1
    fi
    if [[ "$target_tag" == "$current_tag" ]]; then
        base_std_log_info "Base source checkout is already at stable release '$current_tag'."
        if base_update_run_setup "$base_home" base; then
            :
        else
            setup_status=$?
            base_std_log_error "Base setup failed at '$current_tag'. Rerun 'basectl setup' after resolving the reported issue."
            return "$setup_status"
        fi
        base_std_log_info "Base release '$current_tag' is ready."
        return 0
    fi
    if ! base_update_release_target_is_later "$current_tag" "$target_tag"; then
        base_std_log_error "Target release '$target_tag' must be later than the current stable release '$current_tag'; no Git or environment changes were made."
        return 1
    fi

    previous_commit="$(git -C "$repo" rev-parse HEAD)" || {
        base_std_log_error "Unable to read the current Base release revision; no changes were made."
        return 1
    }
    target_commit="$(base_update_release_fetch_tag "$repo" "$target_tag")" || return 1
    if ! base_update_release_untracked_files_safe "$repo" "$previous_commit" "$target_commit" "$target_tag"; then
        return 1
    fi
    if [[ -n "$(git -C "$repo" ls-files --others --exclude-standard --directory --no-empty-directory)" ]]; then
        base_std_log_info "Preserving unrelated untracked files while moving the Base checkout to '$target_tag'."
    fi

    base_std_log_info "Verified Base release tag '$target_tag' at commit '$target_commit'."
    base_std_log_info "Upgrading Base source checkout from '$current_tag' to '$target_tag'."
    git -C "$repo" checkout --detach "$target_commit" || {
        base_std_log_error "Unable to switch the clean Base checkout to '$target_tag'; the previous release remains checked out."
        return 1
    }

    base_update_release_report_trust_guidance "$repo" "$previous_commit" "$target_commit" "$target_tag"
    base_std_log_info "Base source checkout moved from '$current_tag' to '$target_tag' at '$(git -C "$repo" rev-parse --short HEAD)'."
    base_std_log_info "Running basectl setup after the stable source upgrade. Base-managed state and existing shell integration remain outside the Git checkout."
    if base_update_run_setup "$base_home" base; then
        :
    else
        setup_status=$?
        base_std_log_error "Base setup failed after moving to '$target_tag'. The checkout remains at '$target_tag'; resolve the reported issue and rerun 'basectl setup'."
        return "$setup_status"
    fi
    base_std_log_info "Base source upgrade completed from '$current_tag' to '$target_tag'."
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
    local resolved_project
    local update_branch
    local dry_run=0
    local release_tag=""

    while (($#)); do
        case "$1" in
            --project)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_update_usage_error "Option '--project' requires an argument."
                    return $?
                fi
                if [[ -n "$project_arg" ]]; then
                    base_update_usage_error "The 'update' command accepts only one project selection."
                    return $?
                fi
                project_arg="$1"
                project="$1"
                ;;
            --release)
                shift
                if [[ -z "${1:-}" ]]; then
                    base_update_usage_error "Option '--release' requires an argument."
                    return $?
                fi
                if [[ -n "$release_tag" ]]; then
                    base_update_usage_error "The 'update' command accepts only one release selection."
                    return $?
                fi
                release_tag="$1"
                ;;
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

    base_update_resolve_project "$base_home" "$project" resolved_project repo manifest_path || return $?
    [[ -n "$resolved_project" && -n "$repo" && -n "$manifest_path" ]] || {
        base_std_log_error "Unable to resolve Base project '$project'."
        return 1
    }

    base_std_log_debug "Running 'basectl update' for project '$resolved_project'."

    if [[ "$resolved_project" == base ]] && base_update_is_homebrew_install "$base_home"; then
        if [[ -n "$release_tag" ]]; then
            base_update_usage_error "Option '--release' is supported only for stable tagged source checkouts, not Homebrew installs."
            return $?
        fi
        base_update_homebrew_install "$base_home" "$dry_run"
        return $?
    fi

    if [[ -n "$release_tag" ]]; then
        if [[ "$resolved_project" != base ]]; then
            base_update_usage_error "Option '--release' is supported only when updating the Base checkout itself."
            return $?
        fi
        if ! base_update_release_tag_is_stable "$release_tag"; then
            base_update_usage_error "Option '--release' requires a stable vMAJOR.MINOR.PATCH tag, for example 'v1.11.0'."
            return $?
        fi
        if ((dry_run)); then
            base_update_source_git_library || return 1
            base_update_release_dry_run "$repo" "$release_tag"
            return $?
        fi
        base_update_source_git_library || return 1
        base_update_release_source_install "$base_home" "$repo" "$release_tag"
        return $?
    fi

    base_update_source_git_library || return 1
    branch="$(base_update_current_branch "$repo")" || {
        base_std_log_error "Project '$resolved_project' repository '$repo' is not a Git repository."
        return 1
    }
    update_branch="$(base_update_default_branch "$repo")" || {
        base_std_log_error "Unable to determine the default branch for project '$resolved_project'."
        return 1
    }
    if [[ "$branch" != "$update_branch" ]]; then
        base_std_log_error "Project '$resolved_project' update only runs on default branch '$update_branch'; current branch is '$branch'."
        return 1
    fi

    if ! base_update_worktree_clean "$repo"; then
        base_std_log_error "Project '$resolved_project' repository has tracked local changes. Commit, stash, or remove them before running basectl update."
        return 1
    fi
    if base_update_has_untracked_files "$repo"; then
        base_std_log_warn "Project '$resolved_project' repository has untracked files. Continuing because tracked files are clean."
    fi

    if ((dry_run)); then
        base_std_log_info "[DRY-RUN] Would update project '$resolved_project' repository at '$repo'."
        base_std_log_info "[DRY-RUN] Would run 'basectl setup $resolved_project' if the Git update changes the repository."
        return 0
    fi

    before_revision="$(base_update_head_revision "$repo")" || {
        base_std_log_error "Unable to read current revision for project '$resolved_project'."
        return 1
    }

    base_std_log_info "Updating project '$resolved_project' repository at '$repo'."
    base_git_update_repo "$repo" "" "$update_branch" || return 1
    after_revision="$(base_update_head_revision "$repo")" || {
        base_std_log_error "Unable to read updated revision for project '$resolved_project'."
        return 1
    }

    if [[ "$before_revision" == "$after_revision" ]]; then
        base_std_log_info "Project '$resolved_project' repository is already up to date on '$update_branch' at '$after_revision'."
        base_std_log_info "Skipping basectl setup $resolved_project because the repository did not change."
    else
        base_std_log_info "Project '$resolved_project' repository updated from '$before_revision' to '$after_revision' on '$update_branch'."
        base_std_log_info "Running basectl setup $resolved_project after update."
        base_update_run_setup "$base_home" "$resolved_project" || return $?
    fi

    base_std_log_info "Project '$resolved_project' update is complete."
}
