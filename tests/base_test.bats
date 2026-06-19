#!/usr/bin/env bats

load ./test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_PACKAGE_HOME="$TEST_TMPDIR/homebrew/opt/base/libexec"
    TEST_STATE_DIR="$TEST_TMPDIR/state"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN" "$TEST_STATE_DIR"
}

create_packaged_base_home() {
    mkdir -p \
        "$TEST_PACKAGE_HOME/bin" \
        "$TEST_PACKAGE_HOME/cli/python" \
        "$TEST_PACKAGE_HOME/lib/python"
    cp "$BASE_REPO_ROOT/bin/base-test" "$TEST_PACKAGE_HOME/bin/base-test"
}

create_python_stub() {
    cat > "$TEST_MOCKBIN/python" <<'EOF'
#!/usr/bin/env bash
printf 'python %s\n' "$*" >> "${BASE_TEST_STATE_DIR:?}/python.log"
if [[ "${1:-}" == "-m" && "${2:-}" == "pytest" ]]; then
    exit 0
fi
printf 'unexpected python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/python"
}

create_bats_stub() {
    cat > "$TEST_MOCKBIN/bats" <<'EOF'
#!/usr/bin/env bash
printf 'bats %s\n' "$*" >> "${BASE_TEST_STATE_DIR:?}/bats.log"
exit 42
EOF
    chmod +x "$TEST_MOCKBIN/bats"
}

@test "base-test skips source-only Bats suite for packaged Base homes" {
    create_packaged_base_home
    create_python_stub
    create_bats_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_HOME="$TEST_PACKAGE_HOME" \
        BASE_TEST_PYTHON="$TEST_MOCKBIN/python" \
        BASE_TEST_STATE_DIR="$TEST_STATE_DIR" \
        "$TEST_PACKAGE_HOME/bin/base-test"

    [ "$status" -eq 0 ]
    grep -Fqx 'python -m pytest' "$TEST_STATE_DIR/python.log"
    [ ! -f "$TEST_STATE_DIR/bats.log" ]
    [[ "$output" == *"Base source checkout not detected at '$TEST_PACKAGE_HOME'."* ]]
    [[ "$output" == *"Skipping source-checkout-only Bats tests for packaged Base."* ]]
    [[ "$output" == *"Run 'env -u BASE_HOME ./bin/base-test' from a Base source checkout for the full developer suite."* ]]
}
