#!/usr/bin/env bats

load ../../../../../lib/bash/tests/test_helper.sh

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_STATE_DIR="$TEST_TMPDIR/state"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN" "$TEST_STATE_DIR"
}

run_caff() {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" caff "$@"
}

create_caffeinate_stub() {
    cat > "$TEST_MOCKBIN/caffeinate" <<'EOF'
#!/usr/bin/env bash
if [[ -n "${CAFF_TEST_RECORD:-}" ]]; then
    printf '%s\n' "$*" > "$CAFF_TEST_RECORD"
fi
sleep 0.2
EOF
    chmod +x "$TEST_MOCKBIN/caffeinate"
}

create_pgrep_stub() {
    cat > "$TEST_MOCKBIN/pgrep" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
    caffeinate)
        [[ -n "${CAFF_TEST_CAFFEINATE_PID:-}" ]] && printf '%s\n' "$CAFF_TEST_CAFFEINATE_PID"
        ;;
    "${CAFF_TEST_PROCESS_NAME:-}")
        [[ -n "${CAFF_TEST_TARGET_PID:-}" ]] && printf '%s\n' "$CAFF_TEST_TARGET_PID"
        ;;
esac
EOF
    chmod +x "$TEST_MOCKBIN/pgrep"
}

create_ps_stub() {
    cat > "$TEST_MOCKBIN/ps" <<'EOF'
#!/usr/bin/env bash
printf 'ARGS\n'
if [[ -n "${CAFF_TEST_CAFFEINATED_PID:-}" ]]; then
    printf 'caffeinate -iw %s\n' "$CAFF_TEST_CAFFEINATED_PID"
fi
EOF
    chmod +x "$TEST_MOCKBIN/ps"
}

create_core_tool_links_without_caffeinate() {
    local tool
    local tool_path

    for tool in uname dirname readlink basename; do
        tool_path="$(command -v "$tool")"
        ln -s "$tool_path" "$TEST_MOCKBIN/$tool"
    done
}

wait_for_record() {
    local record_file="$1"
    local attempt

    for attempt in 1 2 3 4 5; do
        [[ -f "$record_file" ]] && return 0
        sleep 0.1
    done

    return 1
}

@test "caff prints help" {
    run_caff --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"caff [-s] <process-name>"* ]]
}

@test "caff fails when caffeinate is unavailable" {
    create_core_tool_links_without_caffeinate

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" caff worker

    [ "$status" -eq 1 ]
    [[ "$output" == *"There is no caffeinate command on your system."* ]]
}

@test "caff requires exactly one process name" {
    create_caffeinate_stub

    run_caff

    [ "$status" -eq 2 ]
    [[ "$output" == *"A process name is required."* ]]
    [[ "$output" == *"Usage:"* ]]
}

@test "caff warns when the target process is not running" {
    create_caffeinate_stub
    create_pgrep_stub

    run_caff worker

    [ "$status" -eq 1 ]
    [[ "$output" == *"'worker' process is not running."* ]]
}

@test "caff starts caffeinate for the first matching process" {
    local record_file="$TEST_STATE_DIR/caffeinate.args"

    create_caffeinate_stub
    create_pgrep_stub
    create_ps_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        CAFF_TEST_PROCESS_NAME=worker \
        CAFF_TEST_TARGET_PID=1234 \
        CAFF_TEST_RECORD="$record_file" \
        "$BASE_REPO_ROOT/bin/basectl" caff worker

    [ "$status" -eq 0 ]
    [[ "$output" == *"Caffeinating PID 1234"* ]]
    wait_for_record "$record_file"
    [ "$(cat "$record_file")" = "-iw 1234" ]
}

@test "caff does not start another caffeinate for an already caffeinated process" {
    local record_file="$TEST_STATE_DIR/caffeinate.args"

    create_caffeinate_stub
    create_pgrep_stub
    create_ps_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        CAFF_TEST_PROCESS_NAME=worker \
        CAFF_TEST_TARGET_PID=1234 \
        CAFF_TEST_CAFFEINATE_PID=9999 \
        CAFF_TEST_CAFFEINATED_PID=1234 \
        CAFF_TEST_RECORD="$record_file" \
        "$BASE_REPO_ROOT/bin/basectl" caff worker

    [ "$status" -eq 0 ]
    [[ "$output" == *"Already caffeinating: worker pid=1234, caffeinate pid=9999"* ]]
    [ ! -e "$record_file" ]
}
