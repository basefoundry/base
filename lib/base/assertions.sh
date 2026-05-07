##
## Assertions
##

[[ $__assertions_sourced__ ]] && return
__assertions_sourced__=1

#
# Given a version like x.y, where x and y are numbers, asserts that
# bash version is at least x.y
#
assert_minimum_bash_version() {
    local version=$1 message=$2
    local version_array curr_version version_re='^[0-9]+\.[0-9]+$'
    assert_arg_count $# 1 "Usage: assert_minimum_bash_version version"
    assert_regex_match "$version" "$version_re" "Version should be in the format x.y where x and y are integers"
    version_array=(${version//\./ })
    ((BASH_VERSINFO[0] < version_array[0] ||
        ((BASH_VERSINFO[0] == version_array[0] && BASH_VERSINFO[1] < version_array[1])))) && {
        curr_version="${BASH_VERSINFO[@]:0:4}"
        [[ $message ]] || message="Running with Bash version ${curr_version// /.}; need $version or above"
        printf '%s\n' "$message" >&2
        exit 1
    }
    return 0
}

#
# exit if number of arguments passed doesn't meet expectations
# example call:
#    assert_arg_count $# 2 "Need exactly two arguments"
#
assert_arg_count() {
    local actual=$1 expected=$2 message=$3
    ((actual != expected)) && {
        [[ $message ]] || message="Expected $expected arguments, got $actual arguments"
        printf '%s\n' "$message" >&2
        exit 1
    }
}

assert_regex_match() {
    local string=$1 regex=$2 message=$3
    [[ $string =~ $regex ]] || {
        [[ $message ]] || message="String '$string' does not match regex '$regex'"
        printf '%s\n' "$message" >&2
        exit 1
    }
}

#
# assert if variables are set
# if any variable is not set, exit 1 (when -f option is set) or return 1 otherwise
#
# Usage: assert_var_not_null [-f] variable ...
#
assert_var_not_null() {
    local fatal var num_null=0
    [[ "$1" = "-f" ]] && { shift; fatal=1; }
    for var in "$@"; do
        [[ -z "${!var}" ]] && printf '%s\n' "Variable '$var' not set" >&2 &&
        ((num_null++))
    done

    if ((num_null > 0)); then
        [[ "$fatal" ]] && exit 1
        return 1
    fi
    return 0
}

#
# assert if $1 is a valid URL
#
assert_valid_url() {
    (($#)) || return 0
    local url=$1
    curl --fail --head -o /dev/null --silent "$url" || fatal_error "Invalid URL - '$url'"
}

#
# assert if directories do exist
#
assert_dir_exists() {
    local dir
    local rc=0
    for dir; do
        if [[ ! -d "$dir" ]]; then
            log_error "Directory '$dir' does not exist"
            ((rc++))
        fi
    done
    ((rc)) && exit 1
}

#
# assert if directories do exist
#
assert_file_exists() {
    local file
    local rc=0
    for file; do
        if [[ ! -f "$file" ]]; then
            log_error "File '$file' does not exist"
            ((rc++))
        fi
    done
    ((rc)) && exit 1
}

#
# assert that we are running on the right OS
#
assert_os() {
    (($#)) || return
    if [[ $BASE_OS != "$1" ]]; then
        fatal_error "Required OS: $1, current OS: $BASE_OS"
    fi
}
