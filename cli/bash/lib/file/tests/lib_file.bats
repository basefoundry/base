#!/usr/bin/env bats

load ../../../tests/test_helper.bash

setup() {
    setup_test_tmpdir
    source "$BASE_BASH_DIR/lib/std/lib_std.sh"
    source "$BASE_BASH_DIR/lib/file/lib_file.sh"
}

@test "update_file_section appends a new marked block when markers are absent" {
    local target="$TEST_TMPDIR/config.txt"
    printf 'line-one' > "$target"

    update_file_section "$target" "# BEGIN" "# END" "first" "second"

    [ "$(cat "$target")" = $'line-one\n# BEGIN\nfirst\nsecond\n# END' ]
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
