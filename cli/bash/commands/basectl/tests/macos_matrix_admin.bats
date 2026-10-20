#!/usr/bin/env bats

load ./basectl_helpers.bash

setup() {
    TEST_ROOT="$BATS_TEST_TMPDIR/matrix-admin"
    mkdir -p "$TEST_ROOT/bin"
    SHELLS_FILE="$TEST_ROOT/shells"
    SUDOERS_FILE="$TEST_ROOT/sudoers.d/base-matrix"
    STATE_FILE="$TEST_ROOT/state"
    printf '/bin/zsh\n' >"$SHELLS_FILE"
}

write_stub_commands() {
    cat >"$TEST_ROOT/bin/id" <<'EOF'
#!/bin/sh
if [ "$1" = "-u" ]; then
    printf '0\n'
else
    printf 'matrix-admin\n'
fi
EOF
    cat >"$TEST_ROOT/bin/dscl" <<'EOF'
#!/bin/sh
state="${BASE_MATRIX_DSCL_STATE:?}"
if [ "$2" = "-read" ]; then
    user="${3##*/}"
    shell="$(awk -F= -v user="$user" '$1 == user {print $2; exit}' "$state" 2>/dev/null)"
    printf 'UserShell: %s\n' "${shell:-/bin/zsh}"
    exit 0
fi
if [ "$2" = "-create" ]; then
    user="${3##*/}"
    printf '%s=%s\n' "$user" "$5" >>"$state"
    exit 0
fi
exit 2
EOF
    cat >"$TEST_ROOT/bin/visudo" <<'EOF'
#!/bin/sh
exit 0
EOF
    cat >"$TEST_ROOT/bin/install" <<'EOF'
#!/bin/sh
while [ "$#" -gt 0 ]; do
    case "$1" in
        -o|-g|-m) shift 2 ;;
        *) break ;;
    esac
done
source="$1"
destination="$2"
mkdir -p "$(dirname "$destination")"
cp "$source" "$destination"
EOF
    chmod +x "$TEST_ROOT/bin/id" "$TEST_ROOT/bin/dscl" "$TEST_ROOT/bin/visudo" "$TEST_ROOT/bin/install"
}

run_admin() {
    run env \
        PATH="$TEST_ROOT/bin:$PATH" \
        BASE_MATRIX_BASH_PATH=/opt/homebrew/bin/bash \
        BASE_MATRIX_SHELLS_FILE="$SHELLS_FILE" \
        BASE_MATRIX_SUDOERS_FILE="$SUDOERS_FILE" \
        BASE_MATRIX_STATE_FILE="$STATE_FILE" \
        BASE_MATRIX_OPERATOR=matrix-admin \
        BASE_MATRIX_DSCL="$TEST_ROOT/bin/dscl" \
        BASE_MATRIX_DSCL_STATE="$TEST_ROOT/dscl-state" \
        BASE_MATRIX_VISUDO="$TEST_ROOT/bin/visudo" \
        BASE_MATRIX_INSTALL="$TEST_ROOT/bin/install" \
        "$BASE_REPO_ROOT/tools/macos_matrix_admin.sh" "$@"
}

@test "macOS matrix admin dry-run is non-mutating and shows blast radius" {
    run env \
        BASE_MATRIX_BASH_PATH=/opt/homebrew/bin/bash \
        BASE_MATRIX_SHELLS_FILE="$SHELLS_FILE" \
        BASE_MATRIX_SUDOERS_FILE="$SUDOERS_FILE" \
        BASE_MATRIX_STATE_FILE="$STATE_FILE" \
        BASE_MATRIX_OPERATOR=matrix-admin \
        "$BASE_REPO_ROOT/tools/macos_matrix_admin.sh" --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"DRY-RUN: would configure matrix accounts"* ]]
    [[ "$output" == *"DRY-RUN: would grant matrix-admin passwordless sudo"* ]]
    [[ "$output" == *"DRY-RUN: would set base-source-bash login shell"* ]]
    [ ! -e "$STATE_FILE" ]
    [ ! -e "$SUDOERS_FILE" ]
    [ "$(cat "$SHELLS_FILE")" = "/bin/zsh" ]
}

@test "macOS matrix admin apply is idempotent and remove restores recorded state" {
    write_stub_commands

    run_admin
    [ "$status" -eq 0 ]
    [ -f "$STATE_FILE" ]
    [ -f "$SUDOERS_FILE" ]
    grep -Fxq /opt/homebrew/bin/bash "$SHELLS_FILE"
    grep -Fxq 'matrix-admin ALL = (base-source-bash, base-source-zsh, base-brew-bash, base-brew-zsh) NOPASSWD: ALL' "$SUDOERS_FILE"

    run_admin
    [ "$status" -eq 0 ]
    [ "$(grep -Fc /opt/homebrew/bin/bash "$SHELLS_FILE")" -eq 1 ]

    run_admin --remove
    [ "$status" -eq 0 ]
    [ ! -e "$STATE_FILE" ]
    [ ! -e "$SUDOERS_FILE" ]
    [ "$(cat "$SHELLS_FILE")" = "/bin/zsh" ]
    [[ "$output" == *"macOS install-matrix admin setup removed."* ]]
}
