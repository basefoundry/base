#!/usr/bin/env bats

load ../../../tests/test_helper.bash

readonly STDLIB_PATH="$BANYAN_BASH_DIR/lib/std/lib_std.sh"

create_script() {
    local script_path="$1"
    cat > "$script_path"
    chmod +x "$script_path"
}

normalize_tty_output() {
    local text="$1"
    text="${text//$'\r'/}"
    text="${text//$'\b'/}"
    printf '%s' "$text"
}

run_tty_script() {
    local script_path="$1"
    shift
    bats_run script -q /dev/null "$script_path" "$@"
}

setup() {
    setup_test_tmpdir
    PATH="$BANYAN_TEST_ORIG_PATH"
    unset DRY_RUN dry_run LOG_DEBUG LOG_UTC BANYAN_BASH_BOOTSTRAP_SOURCE
    source "$STDLIB_PATH"
}

teardown() {
    PATH="$BANYAN_TEST_ORIG_PATH"
}

@test "sourcing stdlib preserves original args and strips wrapper flags" {
    local script="$TEST_TMPDIR/check-init.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
printf 'orig=%s\n' "\${__SCRIPT_ARGS__[*]}"
printf 'argv=%s\n' "\$*"
printf 'debug=%s\n' "\${LOG_DEBUG:-}"
printf 'utc=%s\n' "\${LOG_UTC:-}"
printf 'color=%s\n' "\${COLOR_RED:-}"
EOF

    bats_run bash "$script" --verbose-wrapper --utc-wrapper --color alpha beta

    [ "$status" -eq 0 ]
    [[ "$output" == *"orig=--verbose-wrapper --utc-wrapper --color alpha beta"* ]]
    [[ "$output" == *"argv=alpha beta"* ]]
    [[ "$output" == *"debug=1"* ]]
    [[ "$output" == *"utc=1"* ]]
    [[ "$output" == *"color="* ]]
}

@test "bootstrap source override controls __SCRIPT_DIR__" {
    local command_dir="$TEST_TMPDIR/commands/demo"
    local script="$TEST_TMPDIR/bootstrap-dir.sh"
    local expected_dir

    mkdir -p "$command_dir"

    create_script "$script" <<EOF
#!/usr/bin/env bash
export BANYAN_BASH_BOOTSTRAP_SOURCE="$command_dir/demo.sh"
source "$STDLIB_PATH"
printf 'script_dir=%s\n' "\$__SCRIPT_DIR__"
EOF

    expected_dir="$(cd "$command_dir" && pwd -P)"

    bats_run bash "$script"

    [ "$status" -eq 0 ]
    [[ "$output" == *"script_dir=$expected_dir"* ]]
}

@test "is_interactive is false in a non-interactive subprocess" {
    local script="$TEST_TMPDIR/non-interactive.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
if is_interactive; then
    echo "interactive=yes"
else
    echo "interactive=no"
fi
EOF

    bats_run bash "$script" </dev/null

    [ "$status" -eq 0 ]
    [[ "$output" == *"interactive=no"* ]]
}

@test "is_interactive is true when run through a tty" {
    local script="$TEST_TMPDIR/tty-interactive.sh"
    local normalized

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
if is_interactive; then
    echo "interactive=yes"
else
    echo "interactive=no"
fi
EOF

    run_tty_script "$script"
    normalized="$(normalize_tty_output "$output")"

    [ "$status" -eq 0 ]
    [[ "$normalized" == *"interactive=yes"* ]]
}

@test "check_bash_version_and_upgrade succeeds on supported bash" {
    check_bash_version_and_upgrade
    [ "$?" -eq 0 ]
}

@test "color initialization honors tty mode when --color is passed" {
    local script="$TEST_TMPDIR/tty-colors.sh"
    local normalized

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
if [[ -n "\${COLOR_RED:-}" ]]; then
    echo "colors=enabled"
else
    echo "colors=disabled"
fi
EOF

    run_tty_script "$script" --color
    normalized="$(normalize_tty_output "$output")"

    [ "$status" -eq 0 ]
    [[ "$normalized" == *"colors=enabled"* ]]
}

@test "import loads relative and absolute libraries" {
    local relative_dir="$TEST_TMPDIR/helpers"
    local absolute_lib="$TEST_TMPDIR/absolute.sh"
    local script="$TEST_TMPDIR/import-driver.sh"

    mkdir -p "$relative_dir"
    cat > "$relative_dir/relative.sh" <<'EOF'
REL_IMPORTED="relative"
EOF
    cat > "$absolute_lib" <<'EOF'
ABS_IMPORTED="absolute"
EOF

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
import helpers/relative.sh "$absolute_lib"
printf 'rel=%s abs=%s\n' "\$REL_IMPORTED" "\$ABS_IMPORTED"
EOF

    bats_run bash "$script"

    [ "$status" -eq 0 ]
    [[ "$output" == *"rel=relative abs=absolute"* ]]
}

@test "import exits when a library is missing" {
    local script="$TEST_TMPDIR/import-missing.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
import missing.sh
echo "after"
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Library 'missing.sh' does not exist"* ]]
    [[ "$output" != *"after"* ]]
}

@test "add_to_path appends an existing directory only once" {
    mkdir -p "$TEST_TMPDIR/bin"
    PATH="/usr/bin:/bin"

    add_to_path "$TEST_TMPDIR/bin"
    add_to_path "$TEST_TMPDIR/bin"

    [ "$PATH" = "/usr/bin:/bin:$TEST_TMPDIR/bin" ]
}

@test "add_to_path prepends when requested" {
    mkdir -p "$TEST_TMPDIR/bin"
    PATH="/usr/bin:/bin"

    add_to_path -p "$TEST_TMPDIR/bin"

    [ "$PATH" = "$TEST_TMPDIR/bin:/usr/bin:/bin" ]
}

@test "add_to_path skips missing directories unless -n is used" {
    PATH="/usr/bin:/bin"

    add_to_path "$TEST_TMPDIR/missing"
    [ "$PATH" = "/usr/bin:/bin" ]

    add_to_path -n "$TEST_TMPDIR/missing"
    [ "$PATH" = "/usr/bin:/bin:$TEST_TMPDIR/missing" ]
}

@test "add_to_path rejects invalid options" {
    local stderr_file="$TEST_TMPDIR/add-to-path.err"
    local rc

    if add_to_path -z 2>"$stderr_file"; then
        rc=0
    else
        rc=$?
    fi

    [ "$rc" -eq 1 ]
    [[ "$(cat "$stderr_file")" == *"add_to_path: invalid option"* ]]
}

@test "dedupe_path removes duplicates and empty entries" {
    PATH="/one:/two:/one::/three:/two"

    dedupe_path

    [ "$PATH" = "/one:/two:/three" ]
}

@test "print_path emits one path entry per line" {
    PATH="/one:/two:/three"

    bats_run print_path

    [ "$status" -eq 0 ]
    [ "$output" = $'/one\n/two\n/three' ]
}

@test "__join_message__ joins fragments with single spaces" {
    local joined

    joined="$(__join_message__ alpha beta "gamma delta")"

    [ "$joined" = "alpha beta gamma delta" ]
}

@test "log initialization sets the default logger map" {
    [ "${_log_levels[ERROR]}" -eq 1 ]
    [ "${_log_levels[VERBOSE]}" -eq 5 ]
    [ "${_loggers_level_map[default]}" -eq 3 ]
    [ -z "${COLOR_RED:-}" ]
}

@test "set_log_level updates named loggers and falls back for unknown levels" {
    local stderr_file="$TEST_TMPDIR/set-log-level.err"

    set_log_level -l custom DEBUG
    [ "${_loggers_level_map[custom]}" -eq 4 ]

    set_log_level -l custom NOPE 2>"$stderr_file"
    [ "${_loggers_level_map[custom]}" -eq 3 ]
    [[ "$(cat "$stderr_file")" == *"Unknown log level 'NOPE'"* ]]
}

@test "_print_log requires a log level" {
    ! _print_log
}

@test "log wrappers respect the configured log level" {
    local stderr_file="$TEST_TMPDIR/log-wrappers.err"

    : > "$stderr_file"
    log_debug hidden 2>"$stderr_file"
    [ ! -s "$stderr_file" ]

    set_log_level VERBOSE
    {
        log_fatal "fatal message"
        log_error "error message"
        log_warn "warn message"
        log_info "info message"
        log_debug "debug message"
        log_verbose "verbose message"
    } 2>"$stderr_file"

    [[ "$(cat "$stderr_file")" == *"FATAL"* ]]
    [[ "$(cat "$stderr_file")" == *"ERROR"* ]]
    [[ "$(cat "$stderr_file")" == *"WARN"* ]]
    [[ "$(cat "$stderr_file")" == *"INFO"* ]]
    [[ "$(cat "$stderr_file")" == *"DEBUG"* ]]
    [[ "$(cat "$stderr_file")" == *"VERBOSE"* ]]
}

@test "file logging helpers print contents and warn on unknown loggers" {
    local target="$TEST_TMPDIR/log-target.txt"
    local stderr_file="$TEST_TMPDIR/log-file.err"

    printf 'hello file\n' > "$target"

    log_debug_file "$target" 2>"$stderr_file"
    [ ! -s "$stderr_file" ]

    set_log_level DEBUG
    log_debug_file "$target" 2>"$stderr_file"
    [[ "$(cat "$stderr_file")" == *"Contents of file '$target':"* ]]
    [[ "$(cat "$stderr_file")" == *"hello file"* ]]

    _print_log_file INFO -l missing "$target" 2>"$stderr_file"
    [[ "$(cat "$stderr_file")" == *"Unknown logger 'missing'"* ]]
}

@test "enter and leave logging helpers include the caller name" {
    local stderr_file="$TEST_TMPDIR/enter-leave.err"

    trace_me() {
        log_info_enter
        log_debug_enter
        log_verbose_enter
        log_info_leave
        log_debug_leave
        log_verbose_leave
    }

    set_log_level VERBOSE
    trace_me 2>"$stderr_file"

    [[ "$(cat "$stderr_file")" == *"Entering function trace_me"* ]]
    [[ "$(cat "$stderr_file")" == *"Leaving function trace_me"* ]]
}

@test "print helpers emit expected text" {
    local stderr_file="$TEST_TMPDIR/print.err"
    local stdout_file="$TEST_TMPDIR/print.out"

    {
        print_error "bad news"
        print_warn "careful"
        print_info "heads up"
        print_success "all good"
    } 2>"$stderr_file"

    {
        print_bold "strong text"
        print_message "line one" "line two"
    } >"$stdout_file"

    [[ "$(cat "$stderr_file")" == *"ERROR: bad news"* ]]
    [[ "$(cat "$stderr_file")" == *"WARN: careful"* ]]
    [[ "$(cat "$stderr_file")" == *"heads up"* ]]
    [[ "$(cat "$stderr_file")" == *"SUCCESS: all good"* ]]
    [ "$(cat "$stdout_file")" = $'strong text\nline one\nline two' ]
}

@test "print_tty is silent without a tty" {
    local stdout_file="$TEST_TMPDIR/tty.out"

    print_tty "hidden output" >"$stdout_file"

    [ ! -s "$stdout_file" ]
}

@test "print_tty emits output when a tty is present" {
    local script="$TEST_TMPDIR/print-tty.sh"
    local normalized

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
print_tty "tty output"
EOF

    run_tty_script "$script"
    normalized="$(normalize_tty_output "$output")"

    [ "$status" -eq 0 ]
    [[ "$normalized" == *"tty output"* ]]
}

@test "dump_trace prints the active function stack" {
    local script="$TEST_TMPDIR/dump-trace.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
inner_trace() {
    dump_trace
}
outer_trace() {
    inner_trace
}
outer_trace
EOF

    bats_run bash "$script"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Encountered a fatal error"* ]]
    [[ "$output" == *"inner_trace"* ]]
    [[ "$output" == *"outer_trace"* ]]
}

@test "exit_if_error returns success for zero and empty input" {
    local rc

    if exit_if_error; then
        rc=0
    else
        rc=$?
    fi
    [ "$rc" -eq 1 ]

    exit_if_error 0 "unused"
    [ "$?" -eq 0 ]
}

@test "exit_if_error exits with the provided code and message" {
    local script="$TEST_TMPDIR/exit-if-error.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
exit_if_error 7 "boom"
echo "after"
EOF

    bats_run bash "$script"

    [ "$status" -eq 7 ]
    [[ "$output" == *"boom"* ]]
    [[ "$output" != *"after"* ]]
}

@test "exit_if_error normalizes non-numeric exit codes" {
    local script="$TEST_TMPDIR/exit-if-error-nonnumeric.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
exit_if_error nope "bad code"
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"is not a valid exit code"* ]]
    [[ "$output" == *"bad code"* ]]
}

@test "fatal_error preserves the last non-zero status" {
    local script="$TEST_TMPDIR/fatal-error.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
bash -c 'exit 7'
fatal_error "fatal boom"
EOF

    bats_run bash "$script"

    [ "$status" -eq 7 ]
    [[ "$output" == *"fatal boom"* ]]
}

@test "run returns an error when no command is provided" {
    local stderr_file="$TEST_TMPDIR/run-empty.err"
    local rc

    if run 2>"$stderr_file"; then
        rc=0
    else
        rc=$?
    fi

    [ "$rc" -eq 1 ]
    [[ "$(cat "$stderr_file")" == *"run: No command provided."* ]]
}

@test "run honors dry-run mode without executing the command" {
    local target="$TEST_TMPDIR/dry-run.txt"
    DRY_RUN=true

    run touch "$target"

    [ "$?" -eq 0 ]
    [ ! -e "$target" ]
}

@test "run --no-exit returns the underlying failure status" {
    local stderr_file="$TEST_TMPDIR/run-no-exit.err"
    local rc

    if run --no-exit bash -c 'exit 7' 2>"$stderr_file"; then
        rc=0
    else
        rc=$?
    fi

    [ "$rc" -eq 7 ]
    [[ "$(cat "$stderr_file")" == *"continuing"* ]]
}

@test "run exits the script on failure by default" {
    local script="$TEST_TMPDIR/run-fail.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
run bash -c 'exit 9'
echo "after"
EOF

    bats_run bash "$script"

    [ "$status" -eq 9 ]
    [[ "$output" == *"Command failed (exit 9)"* ]]
    [[ "$output" != *"after"* ]]
}

@test "safe_mkdir creates directories and tolerates existing paths with -p" {
    local first="$TEST_TMPDIR/a"
    local second="$TEST_TMPDIR/b/c"

    safe_mkdir "$first"
    safe_mkdir -p "$second"
    safe_mkdir -p "$second"

    [ -d "$first" ]
    [ -d "$second" ]
}

@test "safe_mkdir exits when directory creation fails" {
    local script="$TEST_TMPDIR/safe-mkdir-fail.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
safe_mkdir /dev/null/blocked
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Failed to create directories"* ]]
}

@test "safe_touch creates files" {
    local target="$TEST_TMPDIR/touched.txt"

    safe_touch "$target"

    [ -f "$target" ]
}

@test "safe_touch warns when no files are provided" {
    local stderr_file="$TEST_TMPDIR/safe-touch.err"

    safe_touch 2>"$stderr_file"

    [ "$?" -eq 0 ]
    [[ "$(cat "$stderr_file")" == *"safe_touch: No files provided to touch."* ]]
}

@test "safe_touch exits when a file cannot be touched" {
    local script="$TEST_TMPDIR/safe-touch-fail.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
safe_touch /dev/null/blocked
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Failed to touch the following files"* ]]
}

@test "safe_truncate truncates files to zero bytes" {
    local target="$TEST_TMPDIR/truncate.txt"

    printf 'content\n' > "$target"
    safe_truncate "$target"

    [ ! -s "$target" ]
}

@test "safe_truncate warns when no files are provided" {
    local stderr_file="$TEST_TMPDIR/safe-truncate.err"

    safe_truncate 2>"$stderr_file"

    [ "$?" -eq 0 ]
    [[ "$(cat "$stderr_file")" == *"safe_truncate: No files provided to truncate."* ]]
}

@test "safe_truncate exits when a file cannot be truncated" {
    local script="$TEST_TMPDIR/safe-truncate-fail.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
safe_truncate /dev/null/blocked
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Failed to truncate the following files"* ]]
}

@test "assert_not_null accepts populated variables" {
    local user_name="admin"
    local token="secret"

    assert_not_null user_name token
}

@test "assert_not_null exits for unset or empty variables" {
    local script="$TEST_TMPDIR/assert-not-null.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
user_name="admin"
token=""
assert_not_null user_name token missing_var
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"These required variables are not set or are empty"* ]]
}

@test "assert_integer accepts integers and rejects invalid values" {
    local count=42
    local signed=-3
    local script="$TEST_TMPDIR/assert-integer.sh"

    assert_integer count signed

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
count="not-an-int"
assert_integer count
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"is not a valid integer"* ]]
}

@test "assert_integer_range enforces range bounds" {
    local count=5
    local script="$TEST_TMPDIR/assert-range.sh"

    assert_integer_range count 1 10

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
count=11
assert_integer_range count 1 10
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"is out of range [1, 10]"* ]]
}

@test "assert_arg_count accepts exact and ranged matches" {
    assert_arg_count 2 2
    assert_arg_count 2 1 3
}

@test "assert_arg_count exits when the count is out of range" {
    bats_run assert_arg_count 4 1 3

    [ "$status" -eq 1 ]
    [[ "$output" == *"Argument count mismatch"* ]]
}

@test "assert_arg_count exits on incorrect usage" {
    bats_run assert_arg_count 1

    [ "$status" -eq 1 ]
    [[ "$output" == *"Incorrect usage"* ]]
}

@test "assert_command_exists validates commands and warns on empty input" {
    local stderr_file="$TEST_TMPDIR/assert-command.err"

    assert_command_exists bash mkdir

    assert_command_exists 2>"$stderr_file"
    [ "$?" -eq 0 ]
    [[ "$(cat "$stderr_file")" == *"assert_command_exists: No commands provided to check."* ]]
}

@test "assert_command_exists exits for missing commands" {
    local script="$TEST_TMPDIR/assert-command-fail.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
assert_command_exists definitely_missing_command_name
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"were not found in your PATH"* ]]
}

@test "assert_file_exists validates files and warns on empty input" {
    local target="$TEST_TMPDIR/file.txt"
    local stderr_file="$TEST_TMPDIR/assert-file.err"

    touch "$target"
    assert_file_exists "$target"

    assert_file_exists 2>"$stderr_file"
    [ "$?" -eq 0 ]
    [[ "$(cat "$stderr_file")" == *"assert_file_exists: No files provided to check."* ]]
}

@test "assert_file_exists exits for missing files" {
    local script="$TEST_TMPDIR/assert-file-fail.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
assert_file_exists "$TEST_TMPDIR/missing.txt"
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"do not exist or are not regular files"* ]]
}

@test "assert_dir_exists validates directories and warns on empty input" {
    local target="$TEST_TMPDIR/dir"
    local stderr_file="$TEST_TMPDIR/assert-dir.err"

    mkdir -p "$target"
    assert_dir_exists "$target"

    assert_dir_exists 2>"$stderr_file"
    [ "$?" -eq 0 ]
    [[ "$(cat "$stderr_file")" == *"assert_dir_exists: No directories provided to check."* ]]
}

@test "assert_dir_exists exits for missing directories" {
    local script="$TEST_TMPDIR/assert-dir-fail.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
assert_dir_exists "$TEST_TMPDIR/missing-dir"
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"These required directories do not exist"* ]]
}

@test "safe_cd changes directories and exits on failure" {
    local target="$TEST_TMPDIR/go-here"
    local script="$TEST_TMPDIR/safe-cd-fail.sh"

    mkdir -p "$target"
    safe_cd "$target"
    [ "$PWD" = "$target" ]

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
safe_cd "$TEST_TMPDIR/missing-dir"
echo "after"
EOF

    bats_run bash "$script"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Can't cd to"* ]]
    [[ "$output" != *"after"* ]]
}

@test "safe_unalias removes aliases and ignores missing ones" {
    alias ll='ls -l'

    safe_unalias ll missing_alias

    ! alias ll >/dev/null 2>&1
}

@test "get_my_source_dir returns the caller script directory" {
    local script="$TEST_TMPDIR/get-source-dir.sh"
    local expected_dir

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
caller_dir=""
get_my_source_dir caller_dir
printf 'dir=%s\n' "\$caller_dir"
EOF

    expected_dir="$(cd "$TEST_TMPDIR" && pwd -P)"

    bats_run bash "$script"

    [ "$status" -eq 0 ]
    [[ "$output" == *"dir=$expected_dir"* ]]
}

@test "ask_yes_no accepts yes input" {
    local script="$TEST_TMPDIR/ask-yes.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
if ask_yes_no "Proceed" <<<"y"; then
    echo "answer=yes"
else
    echo "answer=no"
fi
EOF

    bats_run bash "$script"

    [ "$status" -eq 0 ]
    [[ "$output" == *"answer=yes"* ]]
}

@test "ask_yes_no accepts no input" {
    local script="$TEST_TMPDIR/ask-no.sh"

    create_script "$script" <<EOF
#!/usr/bin/env bash
source "$STDLIB_PATH"
if ask_yes_no "Proceed" <<<"n"; then
    echo "answer=yes"
else
    echo "answer=no"
fi
EOF

    bats_run bash "$script"

    [ "$status" -eq 0 ]
    [[ "$output" == *"answer=no"* ]]
}

@test "ask_yes_no validates argument count" {
    local stderr_file="$TEST_TMPDIR/ask-yes-no.err"
    local rc

    if ask_yes_no 2>"$stderr_file"; then
        rc=0
    else
        rc=$?
    fi

    [ "$rc" -eq 1 ]
    [[ "$(cat "$stderr_file")" == *"ask_yes_no: invalid arguments"* ]]
}

@test "wait_for_enter returns after receiving a newline on a tty" {
    skip "wait_for_enter reads from /dev/tty and needs a more reliable pseudo-tty harness on macOS."
}
