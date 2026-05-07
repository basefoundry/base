#
# networking related functions
#

import lib/base/assertions.sh

#
# check if $1 is a valid IPV4 address; return 0 if true, 1 otherwise
#
validate_ip4() {
  local arr element
  IFS=. read -r -a arr <<< "$1"
  [[ ${#arr[@]} != 4 ]] && return 1
  for element in "${arr[@]}"; do
    [[ (! $element =~ ^[0-9]+$) ||
          $element =~ ^0[1-9]+$
    ]] && return 1
    ((element < 0 || element > 255)) && return 1
  done
  return 0
}

#
# check if URL is valid.  Credit: https://stackoverflow.com/a/12199125/6862601
#
is_valid_url() {
    assert_arg_count $# 1 "is_valid_url: expected 1 argument, got $#"
    curl --output /dev/null --silent --head --fail "$1"
}

is_valid_url_no_head() {
    assert_arg_count $# 1 "is_valid_url_no_head: expected 1 argument, got $#"
    curl --output /dev/null --silent --fail -r 0-0 "$1"
}
