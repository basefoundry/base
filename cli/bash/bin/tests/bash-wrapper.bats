#!/usr/bin/env bats

load ../../tests/test_helper.bash

create_bare_wrapper_layout() {
    local layout_root="$1"
    local cli_root

    cli_root="$(dirname "$layout_root")"

    mkdir -p "$layout_root/bin" "$layout_root/commands" "$layout_root/lib/std" "$cli_root/env" "$cli_root/python"
    cp "$BANYAN_REPO_ROOT/cli/env/banyanenv.sh" "$cli_root/env/banyanenv.sh"
    cp "$BANYAN_BASH_DIR/bin/bash-wrapper" "$layout_root/bin/bash-wrapper"
    cp "$BANYAN_BASH_DIR/lib/std/lib_std.sh" "$layout_root/lib/std/lib_std.sh"
    chmod +x "$layout_root/bin/bash-wrapper"
}

create_wrapper_layout() {
    local layout_root="$1"
    local command_name="$2"
    local command_script_name="${3:-$command_name.sh}"

    create_bare_wrapper_layout "$layout_root"
    mkdir -p "$layout_root/commands/$command_name"

    cat > "$layout_root/commands/$command_name/$command_script_name" <<'EOF'
#!/usr/bin/env bash
printf 'script_dir=%s\n' "${__SCRIPT_DIR__:-}"
printf 'orig_args=%s\n' "${__SCRIPT_ARGS__[*]:-}"
printf 'command=%s\n' "${BANYAN_BASH_COMMAND_NAME:-}"
printf 'repo=%s\n' "${BANYAN_REPO_ROOT:-}"
printf 'bash_root=%s\n' "${BANYAN_BASH_ROOT:-}"
printf 'bin_dir=%s\n' "${BANYAN_BASH_BIN_DIR:-}"
printf 'env_script=%s\n' "${BANYAN_CLI_ENV_SCRIPT:-}"
printf 'script=%s\n' "${BANYAN_BASH_COMMAND_SCRIPT:-}"
case ":$PATH:" in
    *":${BANYAN_BASH_BIN_DIR:-__missing__}:"*) printf 'path_has_bin=yes\n' ;;
    *) printf 'path_has_bin=no\n' ;;
esac
printf 'argv=%s\n' "$*"
EOF
    chmod +x "$layout_root/commands/$command_name/$command_script_name"
}

@test "bash-wrapper dispatches directly to commands/<name>/<name>.sh" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"
    local expected_repo_root expected_bash_root expected_bin_dir expected_env_script expected_script_path
    local expected_command_dir

    create_wrapper_layout "$layout" demo
    expected_repo_root="$(cd "$repo_root" && pwd -P)"
    expected_bash_root="$(cd "$layout" && pwd -P)"
    expected_bin_dir="$(cd "$layout/bin" && pwd -P)"
    expected_env_script="$(cd "$repo_root/cli/env" && pwd -P)/banyanenv.sh"
    expected_command_dir="$(cd "$layout/commands/demo" && pwd -P)"
    expected_script_path="$(cd "$layout/commands/demo" && pwd -P)/demo.sh"

    run "$layout/bin/bash-wrapper" demo.sh --debug-wrapper alpha beta

    [ "$status" -eq 0 ]
    [[ "$output" == *"script_dir=$expected_command_dir"* ]]
    [[ "$output" == *"orig_args=--debug-wrapper alpha beta"* ]]
    [[ "$output" == *"command=demo"* ]]
    [[ "$output" == *"repo=$expected_repo_root"* ]]
    [[ "$output" == *"bash_root=$expected_bash_root"* ]]
    [[ "$output" == *"bin_dir=$expected_bin_dir"* ]]
    [[ "$output" == *"env_script=$expected_env_script"* ]]
    [[ "$output" == *"script=$expected_script_path"* ]]
    [[ "$output" == *"path_has_bin=yes"* ]]
    [[ "$output" == *"argv=alpha beta"* ]]
}

@test "symlink name with .sh suffix selects the command" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"
    local expected_script_path
    local expected_command_dir

    create_wrapper_layout "$layout" greet
    ln -s bash-wrapper "$layout/bin/greet.sh"
    expected_command_dir="$(cd "$layout/commands/greet" && pwd -P)"
    expected_script_path="$(cd "$layout/commands/greet" && pwd -P)/greet.sh"

    run "$layout/bin/greet.sh" hello world

    [ "$status" -eq 0 ]
    [[ "$output" == *"script_dir=$expected_command_dir"* ]]
    [[ "$output" == *"command=greet"* ]]
    [[ "$output" == *"script=$expected_script_path"* ]]
    [[ "$output" == *"argv=hello world"* ]]
}

@test "wrapper prints usage when no command is provided" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"

    run "$layout/bin/bash-wrapper"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "wrapper prints usage for help flags" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"

    run "$layout/bin/bash-wrapper" --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"Available commands:"* ]]
}

@test "wrapper lists commands with command scripts and skips empty directories" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_wrapper_layout "$layout" alpha
    mkdir -p "$layout/commands/empty-dir"
    mkdir -p "$layout/commands/readme-only"
    printf '# no script here\n' > "$layout/commands/readme-only/README.md"
    mkdir -p "$layout/commands/legacy"
    cat > "$layout/commands/legacy/legacy.sh" <<'EOF'
#!/usr/bin/env bash
echo "legacy"
EOF
    chmod +x "$layout/commands/legacy/legacy.sh"
    mkdir -p "$layout/commands/main-only"
    cat > "$layout/commands/main-only/main.sh" <<'EOF'
#!/usr/bin/env bash
echo "main-only"
EOF
    chmod +x "$layout/commands/main-only/main.sh"

    run "$layout/bin/bash-wrapper" --list

    [ "$status" -eq 0 ]
    [[ "$output" == *"  alpha.sh"* ]]
    [[ "$output" == *"  legacy.sh"* ]]
    [[ "$output" != *"empty-dir"* ]]
    [[ "$output" != *"main-only"* ]]
    [[ "$output" != *"readme-only"* ]]
}

@test "wrapper lists none when no commands exist yet" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"

    run "$layout/bin/bash-wrapper" --list

    [ "$status" -eq 0 ]
    [[ "$output" == *"  (none yet)"* ]]
}

@test "wrapper rejects invalid command names in direct mode" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"

    run "$layout/bin/bash-wrapper" ../bad

    [ "$status" -eq 1 ]
    [[ "$output" == *"Invalid command name '../bad'."* ]]
}

@test "wrapper errors when the command directory is missing" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"

    run "$layout/bin/bash-wrapper" missing.sh

    [ "$status" -eq 1 ]
    [[ "$output" == *"Command 'missing' was not found"* ]]
}

@test "wrapper rejects main.sh-only command directories" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"
    mkdir -p "$layout/commands/legacy"
    cat > "$layout/commands/legacy/main.sh" <<'EOF'
#!/usr/bin/env bash
echo "legacy"
EOF
    chmod +x "$layout/commands/legacy/main.sh"

    run "$layout/bin/bash-wrapper" legacy.sh

    [ "$status" -eq 1 ]
    [[ "$output" == *"Command 'legacy' was not found"* ]]
}

@test "wrapper errors when the stdlib is missing" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_wrapper_layout "$layout" demo
    rm -f "$layout/lib/std/lib_std.sh"

    run "$layout/bin/bash-wrapper" demo

    [ "$status" -eq 1 ]
    [[ "$output" == *"Required stdlib"* ]]
}

@test "wrapper errors when banyanenv is missing" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_wrapper_layout "$layout" demo
    rm -f "$repo_root/cli/env/banyanenv.sh"

    run "$layout/bin/bash-wrapper" demo

    [ "$status" -eq 1 ]
    [[ "$output" == *"Required environment bootstrap"* ]]
}

@test "wrapper preloads stdlib so commands can call stdlib helpers without sourcing it" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"
    mkdir -p "$layout/commands/stdlib-demo"
    cat > "$layout/commands/stdlib-demo/stdlib-demo.sh" <<'EOF'
#!/usr/bin/env bash
set_log_level DEBUG
run echo "wrapped output"
safe_touch "$BATS_TEST_TMPDIR/stdout.txt"
printf 'touched=%s\n' "$BATS_TEST_TMPDIR/stdout.txt"
EOF
    chmod +x "$layout/commands/stdlib-demo/stdlib-demo.sh"

    run "$layout/bin/bash-wrapper" stdlib-demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"wrapped output"* ]]
    [[ "$output" == *"touched=$BATS_TEST_TMPDIR/stdout.txt"* ]]
    [ -f "$BATS_TEST_TMPDIR/stdout.txt" ]
}

@test "wrapper strips wrapper flags before the command sees argv" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"
    mkdir -p "$layout/commands/flags"
    cat > "$layout/commands/flags/flags.sh" <<'EOF'
#!/usr/bin/env bash
printf 'orig=%s\n' "${__SCRIPT_ARGS__[*]}"
printf 'argv=%s\n' "$*"
printf 'log_debug=%s\n' "${LOG_DEBUG:-}"
printf 'log_utc=%s\n' "${LOG_UTC:-}"
EOF
    chmod +x "$layout/commands/flags/flags.sh"

    run "$layout/bin/bash-wrapper" flags --verbose-wrapper --utc-wrapper --color one two

    [ "$status" -eq 0 ]
    [[ "$output" == *"orig=--verbose-wrapper --utc-wrapper --color one two"* ]]
    [[ "$output" == *"argv=one two"* ]]
    [[ "$output" == *"log_debug=1"* ]]
    [[ "$output" == *"log_utc=1"* ]]
}

@test "symlink invocation reports missing command scripts for the symlink name" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local layout="$repo_root/cli/bash"

    create_bare_wrapper_layout "$layout"
    ln -s bash-wrapper "$layout/bin/orphan.sh"
    mkdir -p "$layout/commands/orphan"

    run "$layout/bin/orphan.sh"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Command 'orphan' was not found"* ]]
}
