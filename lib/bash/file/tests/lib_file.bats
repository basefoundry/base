#!/usr/bin/env bats

load ../../tests/test_helper.sh

setup() {
    setup_test_tmpdir
    source "$BASE_BASH_DIR/std/lib_std.sh"
    source "$BASE_BASH_DIR/file/lib_file.sh"
}

file_inode() {
    if stat -c '%i' "$1" >/dev/null 2>&1; then
        stat -c '%i' "$1"
    else
        stat -f '%i' "$1"
    fi
}

@test "update_file_section appends a new marked block when markers are absent" {
    local target="$TEST_TMPDIR/config.txt"
    printf 'line-one' > "$target"

    update_file_section "$target" "# BEGIN" "# END" "first" "second"

    [ "$(cat "$target")" = $'line-one\n# BEGIN\nfirst\nsecond\n# END' ]
}

@test "lib_file can be sourced more than once" {
    source "$BASE_BASH_DIR/file/lib_file.sh"

    [ "$(type -t update_file_section)" = "function" ]
}

@test "update_file_section writes option-like markers literally" {
    local target="$TEST_TMPDIR/config.txt"
    printf 'line-one' > "$target"

    update_file_section "$target" "-n" "-e" "value"

    [ "$(cat "$target")" = $'line-one\n-n\nvalue\n-e' ]
}

@test "update_file_section replaces the first matching section" {
    local target="$TEST_TMPDIR/config.txt"
    cat <<'EOF' > "$target"
before
# BEGIN
old
# END
after
EOF

    update_file_section "$target" "# BEGIN" "# END" "new"

    [ "$(cat "$target")" = $'before\n# BEGIN\nnew\n# END\nafter' ]
}

@test "update_file_section replaces an existing section with multi-line content" {
    local target="$TEST_TMPDIR/config.txt"
    cat <<'EOF' > "$target"
before
# BEGIN
old
# END
after
EOF

    update_file_section "$target" "# BEGIN" "# END" "first" "second" "third"

    [ "$(cat "$target")" = $'before\n# BEGIN\nfirst\nsecond\nthird\n# END\nafter' ]
}

@test "update_file_section skips unchanged existing section" {
    local before_inode
    local target="$TEST_TMPDIR/config.txt"
    cat <<'EOF' > "$target"
before
# BEGIN
same
content
# END
after
EOF
    before_inode="$(file_inode "$target")"

    bats_run update_file_section "$target" "# BEGIN" "# END" "same" "content"

    [ "$status" -eq 0 ]
    [[ "$output" != *"Updating '$target'"* ]]
    [ "$(file_inode "$target")" = "$before_inode" ]
    [ "$(cat "$target")" = $'before\n# BEGIN\nsame\ncontent\n# END\nafter' ]

    set_log_level DEBUG
    bats_run update_file_section "$target" "# BEGIN" "# END" "same" "content"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Section already up to date in '$target'."* ]]
}

@test "update_file_section does not export replacement content to awk" {
    local awk_log="$TEST_TMPDIR/awk-env.log"
    local target="$TEST_TMPDIR/config.txt"
    cat <<'EOF' > "$target"
before
# BEGIN
old
# END
after
EOF

    awk() {
        if [[ -n "${AWK_NEW_TEXT+x}" ]]; then
            printf 'leaked=%s\n' "$AWK_NEW_TEXT" > "$awk_log"
        else
            printf 'not-leaked\n' > "$awk_log"
        fi
        command awk "$@"
    }

    update_file_section "$target" "# BEGIN" "# END" "secret" "value"
    unset -f awk

    [ "$(cat "$awk_log")" = "not-leaked" ]
    [ "$(cat "$target")" = $'before\n# BEGIN\nsecret\nvalue\n# END\nafter' ]
}

@test "update_file_section removes a marked block with -r" {
    local target="$TEST_TMPDIR/config.txt"
    cat <<'EOF' > "$target"
before
# BEGIN
remove-me
# END
after
EOF

    update_file_section -r "$target" "# BEGIN" "# END"

    [ "$(cat "$target")" = $'before\nafter' ]
}

@test "update_file_section rejects a section with only a start marker" {
    local target="$TEST_TMPDIR/config.txt"
    cat <<'EOF' > "$target"
before
# BEGIN
orphaned
EOF

    bats_run update_file_section "$target" "# BEGIN" "# END" "new"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Asymmetric markers in '$target': 1 start, 0 end. Manual repair needed."* ]]
    [ "$(cat "$target")" = $'before\n# BEGIN\norphaned' ]
}

@test "update_file_section rejects a section with only an end marker" {
    local target="$TEST_TMPDIR/config.txt"
    cat <<'EOF' > "$target"
before
orphaned
# END
EOF

    bats_run update_file_section "$target" "# BEGIN" "# END" "new"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Asymmetric markers in '$target': 0 start, 1 end. Manual repair needed."* ]]
    [ "$(cat "$target")" = $'before\norphaned\n# END' ]
}

@test "update_file_section is a no-op for a missing target file" {
    local target="$TEST_TMPDIR/missing.txt"

    bats_run update_file_section "$target" "# BEGIN" "# END" "value"

    [ "$status" -eq 0 ]
    [ ! -e "$target" ]
}

@test "update_file_section rejects content arguments when removing a section" {
    local target="$TEST_TMPDIR/config.txt"
    touch "$target"

    bats_run update_file_section -r "$target" "# BEGIN" "# END" "unexpected"

    [ "$status" -eq 1 ]
    [[ "$output" == *"When -r flag is used"* ]]
}

@test "update_file_section cleans up temp file when initial copy fails" {
    local target="$TEST_TMPDIR/config.txt"
    printf 'line-one' > "$target"

    cp() {
        : > "$2"
        return 1
    }

    bats_run update_file_section "$target" "# BEGIN" "# END" "value"
    unset -f cp

    [ "$status" -eq 1 ]
    [[ "$output" == *"Failed to copy"* ]]
    [ "$(cat "$target")" = "line-one" ]
    ! compgen -G "$target".'*' >/dev/null
}
