# shellcheck shell=bash
#
# lib_version.sh: shared Base version helpers.
#

[[ -n "${__lib_version_sourced__:-}" ]] && return 0
readonly __lib_version_sourced__=1

base_read_version() {
    local base_home="$1"
    local version_file="$base_home/VERSION"
    local version

    [[ -f "$version_file" ]] || {
        printf '%s\n' "unknown"
        return 0
    }

    IFS= read -r version < "$version_file" || version=""
    printf '%s\n' "${version:-unknown}"
}
