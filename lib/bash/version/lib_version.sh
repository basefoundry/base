# shellcheck shell=bash
#
# lib_version.sh: shared Base version helpers.
#

[[ -n "${_base_lib_version_sourced:-}" ]] && return 0
_base_lib_version_sourced=1
readonly _base_lib_version_sourced

base_version_read_file() {
    local version_file="$1"
    local version=""

    [[ -f "$version_file" ]] || return 1
    IFS= read -r version < "$version_file" || true
    [[ -n "$version" ]] || return 1
    printf '%s\n' "$version"
}

base_version_git_revision() {
    local base_home="$1"
    local revision=""

    base_version_is_git_checkout "$base_home" || return 1
    revision="$(git -C "$base_home" rev-parse --short=12 HEAD 2>/dev/null)" || return 1
    [[ -n "$revision" ]] || return 1
    printf '%s\n' "$revision"
}

base_version_is_git_checkout() {
    local base_home="$1"
    local base_root=""
    local git_root=""

    base_root="$(cd -- "$base_home" 2>/dev/null && pwd -P)" || return 1
    git_root="$(git -C "$base_home" rev-parse --show-toplevel 2>/dev/null)" || return 1
    git_root="$(cd -- "$git_root" 2>/dev/null && pwd -P)" || return 1
    [[ "$git_root" == "$base_root" ]]
}

base_version_exact_tag() {
    local base_home="$1"
    local tag=""

    base_version_is_git_checkout "$base_home" || return 1
    tag="$(git -C "$base_home" describe --tags --exact-match --match 'v[0-9]*' HEAD 2>/dev/null)" || return 1
    [[ -n "$tag" ]] || return 1
    printf '%s\n' "$tag"
}

base_version_worktree_dirty() {
    local base_home="$1"
    local status=""

    base_version_is_git_checkout "$base_home" || return 1
    status="$(git -C "$base_home" status --porcelain --untracked-files=normal 2>/dev/null)" || return 1
    [[ -n "$status" ]]
}

base_read_version() {
    local base_home="$1"
    local release_version
    local development_version
    local revision
    local exact_tag
    local tag_version
    local source_version
    local worktree_dirty=0

    release_version="$(base_version_read_file "$base_home/VERSION")" || {
        printf '%s\n' "unknown"
        return 0
    }

    development_version="$(base_version_read_file "$base_home/DEVELOPMENT_VERSION")" || {
        printf '%s\n' "$release_version"
        return 0
    }

    revision="$(base_version_git_revision "$base_home")" || {
        printf '%s\n' "$release_version"
        return 0
    }

    if base_version_worktree_dirty "$base_home"; then
        worktree_dirty=1
    fi

    exact_tag="$(base_version_exact_tag "$base_home" || true)"
    if [[ -n "$exact_tag" && "$worktree_dirty" -eq 0 ]]; then
        tag_version="${exact_tag#v}"
        if [[ "$tag_version" == "$release_version" ]]; then
            printf '%s\n' "$release_version"
            return 0
        fi
    fi

    if [[ "$development_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        source_version="${development_version}-dev+g${revision}"
        if [[ "$worktree_dirty" -eq 1 ]]; then
            source_version+=".dirty"
        fi
        printf '%s\n' "$source_version"
        return 0
    fi

    printf '%s\n' "$release_version"
}
