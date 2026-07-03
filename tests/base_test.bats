#!/usr/bin/env bats

load ./test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_PACKAGE_HOME="$TEST_TMPDIR/homebrew/opt/base/libexec"
    TEST_SOURCE_HOME="$TEST_TMPDIR/source/base"
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

create_source_base_home_without_bash_libs() {
    mkdir -p \
        "$TEST_SOURCE_HOME/bin" \
        "$TEST_SOURCE_HOME/cli/python" \
        "$TEST_SOURCE_HOME/lib/python"
    cp "$BASE_REPO_ROOT/bin/base-test" "$TEST_SOURCE_HOME/bin/base-test"
    git -C "$TEST_SOURCE_HOME" init -q
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

create_failing_python_stub() {
    cat > "$TEST_MOCKBIN/python" <<'EOF'
#!/usr/bin/env bash
printf 'python %s\n' "$*" >> "${BASE_TEST_STATE_DIR:?}/python.log"
exit 7
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

create_bats_env_stub() {
    cat > "$TEST_MOCKBIN/bats" <<'EOF'
#!/usr/bin/env bash
printf 'preserve=%s\n' "${BASE_ACTIVATE_PRESERVE_CWD-__unset__}" >> "${BASE_TEST_STATE_DIR:?}/bats-env.log"
printf 'shell=%s\n' "${BASE_ACTIVATE_SHELL-__unset__}" >> "${BASE_TEST_STATE_DIR:?}/bats-env.log"
exit 0
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

@test "base-test stops before Bats when the Python suite fails" {
    create_packaged_base_home
    create_failing_python_stub
    create_bats_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_HOME="$TEST_PACKAGE_HOME" \
        BASE_TEST_PYTHON="$TEST_MOCKBIN/python" \
        BASE_TEST_STATE_DIR="$TEST_STATE_DIR" \
        "$TEST_PACKAGE_HOME/bin/base-test"

    [ "$status" -eq 7 ]
    grep -Fqx 'python -m pytest' "$TEST_STATE_DIR/python.log"
    [ ! -f "$TEST_STATE_DIR/bats.log" ]
}

@test "base-test preflights source checkout base-bash-libs dependency before Bats" {
    create_source_base_home_without_bash_libs
    create_python_stub
    create_bats_stub

    run env \
        -u BASE_BASH_LIBS_DIR \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_HOME="$TEST_SOURCE_HOME" \
        BASE_TEST_PYTHON="$TEST_MOCKBIN/python" \
        BASE_TEST_STATE_DIR="$TEST_STATE_DIR" \
        "$TEST_SOURCE_HOME/bin/base-test"

    [ "$status" -eq 1 ]
    [ ! -f "$TEST_STATE_DIR/python.log" ]
    [ ! -f "$TEST_STATE_DIR/bats.log" ]
    [[ "$output" == *"Base source-checkout Bats tests require base-bash-libs."* ]]
    [[ "$output" == *"Clone basefoundry/base-bash-libs next to Base or set BASE_BASH_LIBS_DIR."* ]]
}

@test "base-test includes source guard coverage in the source checkout suite" {
    grep -Fqx "    tests/source_guards.bats \\" "$BASE_REPO_ROOT/bin/base-test"
}

@test "base-test clears activate override variables before Bats" {
    create_python_stub
    create_bats_env_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_PYTHON="$TEST_MOCKBIN/python" \
        BASE_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_ACTIVATE_PRESERVE_CWD=1 \
        BASE_ACTIVATE_SHELL="$TEST_TMPDIR/leaked-bash" \
        "$BASE_REPO_ROOT/bin/base-test"

    [ "$status" -eq 0 ]
    grep -Fqx 'python -m pytest' "$TEST_STATE_DIR/python.log"
    grep -Fqx 'preserve=__unset__' "$TEST_STATE_DIR/bats-env.log"
    grep -Fqx 'shell=__unset__' "$TEST_STATE_DIR/bats-env.log"
}

@test "base-test uses explicit error handling instead of shell strict mode" {
    run grep -nE '^[[:space:]]*set[[:space:]].*(-e|-u|pipefail)' "$BASE_REPO_ROOT/bin/base-test"

    [ "$status" -eq 1 ]
}
