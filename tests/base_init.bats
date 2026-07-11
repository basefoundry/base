#!/usr/bin/env bats

load ./test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_BASE_HOME="$TEST_TMPDIR/base"
    mkdir -p "$TEST_BASE_HOME"
    TEST_BASE_HOME="$(cd "$TEST_BASE_HOME" && pwd -P)"
    create_minimal_base_home "$TEST_BASE_HOME"
    copy_base_bash_libs_fixture "$TEST_TMPDIR/base-bash-libs/lib/bash"
}

create_minimal_base_home() {
    local base_home="$1"

    mkdir -p \
        "$base_home/bin" \
        "$base_home/cli/bash/commands" \
        "$base_home/lib/bash" \
        "$base_home/lib/shell"

    cp "$BASE_REPO_ROOT/base_init.sh" "$base_home/base_init.sh"
}

create_external_bash_libs() {
    local target_dir="$1"

    copy_base_bash_libs_fixture "$target_dir"
}

run_base_init_script() {
    local script="$1"

    run env \
        -u BASE_HOME \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_BASH_LIBS_DIR \
        -u BASE_BASH_LIBS_SOURCE \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_PLATFORM \
        -u BASE_HOST_ENV \
        -u BASE_HOST \
        -u BASE_SHELL \
        bash -c "$script" bash "$TEST_BASE_HOME"
}

create_uname_stub() {
    local mockbin="$1"
    local uname_os="$2"

    mkdir -p "$mockbin"
    cat > "$mockbin/uname" <<EOF
#!/usr/bin/env bash
if [[ "\${1:-}" == "-s" ]]; then
    printf '%s\n' "$uname_os"
    exit 0
fi
printf 'unexpected uname args: %s\n' "\$*" >&2
exit 1
EOF
    chmod +x "$mockbin/uname"
}

@test "base_init exports the Base runtime path contract" {
    local expected_bash_libs_dir

    expected_bash_libs_dir="$(cd "$TEST_TMPDIR/base-bash-libs/lib/bash" && pwd -P)"

    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        printf "BASE_HOME=%s\n" "$BASE_HOME"
        printf "BASE_BIN_DIR=%s\n" "$BASE_BIN_DIR"
        printf "BASE_CLI_DIR=%s\n" "$BASE_CLI_DIR"
        printf "BASE_BASH_DIR=%s\n" "$BASE_BASH_DIR"
        printf "BASE_BASH_COMMANDS_DIR=%s\n" "$BASE_BASH_COMMANDS_DIR"
        printf "BASE_LIB_DIR=%s\n" "$BASE_LIB_DIR"
        printf "BASE_BASH_LIB_DIR=%s\n" "$BASE_BASH_LIB_DIR"
        printf "BASE_BASH_LIBS_DIR=%s\n" "$BASE_BASH_LIBS_DIR"
        printf "BASE_BASH_LIBS_SOURCE=%s\n" "$BASE_BASH_LIBS_SOURCE"
        printf "BASE_SHELL_DIR=%s\n" "$BASE_SHELL_DIR"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$TEST_BASE_HOME"* ]]
    [[ "$output" == *"BASE_BIN_DIR=$TEST_BASE_HOME/bin"* ]]
    [[ "$output" == *"BASE_CLI_DIR=$TEST_BASE_HOME/cli"* ]]
    [[ "$output" == *"BASE_BASH_DIR=$TEST_BASE_HOME/cli/bash"* ]]
    [[ "$output" == *"BASE_BASH_COMMANDS_DIR=$TEST_BASE_HOME/cli/bash/commands"* ]]
    [[ "$output" == *"BASE_LIB_DIR=$TEST_BASE_HOME/lib"* ]]
    [[ "$output" == *"BASE_BASH_LIB_DIR=$TEST_BASE_HOME/lib/bash"* ]]
    [[ "$output" == *"BASE_BASH_LIBS_DIR=$expected_bash_libs_dir"* ]]
    [[ "$output" == *"BASE_BASH_LIBS_SOURCE=sibling"* ]]
    [[ "$output" == *"BASE_SHELL_DIR=$TEST_BASE_HOME/lib/shell"* ]]
}

@test "base_init preserves explicit symlinked BASE_HOME paths" {
    local cellar_base="$TEST_TMPDIR/homebrew/Cellar/base/0.4.0/libexec"
    local opt_dir="$TEST_TMPDIR/homebrew/opt"
    local opt_base="$opt_dir/base/libexec"

    mkdir -p "$opt_dir"
    create_minimal_base_home "$cellar_base"
    ln -s "../Cellar/base/0.4.0" "$opt_dir/base"

    run env \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_BASH_LIBS_DIR \
        -u BASE_BASH_LIBS_SOURCE \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_PLATFORM \
        -u BASE_HOST_ENV \
        -u BASE_HOST \
        -u BASE_SHELL \
        BASE_HOME="$opt_base" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            printf "BASE_HOME=%s\n" "$BASE_HOME"
            printf "BASE_BIN_DIR=%s\n" "$BASE_BIN_DIR"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$opt_base"* ]]
    [[ "$output" == *"BASE_BIN_DIR=$opt_base/bin"* ]]
}

@test "base_init exports host operating system platform and shell metadata" {
    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        printf "BASE_OS=%s\n" "$BASE_OS"
        printf "BASE_PLATFORM=%s\n" "$BASE_PLATFORM"
        printf "BASE_HOST_ENV=%s\n" "$BASE_HOST_ENV"
        printf "BASE_HOST=%s\n" "$BASE_HOST"
        printf "BASE_SHELL=%s\n" "$BASE_SHELL"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOST="* ]]
    [[ "$output" == *"BASE_SHELL=bash"* ]]
    [[ "$output" == *"BASE_OS=linux"* || "$output" == *"BASE_OS=macos"* ]]
    [[ "$output" == *"BASE_PLATFORM=linux-debian"* || "$output" == *"BASE_PLATFORM=linux-unknown"* || "$output" == *"BASE_PLATFORM=macos"* ]]
    [[ "$output" == *"BASE_HOST_ENV=native"* || "$output" == *"BASE_HOST_ENV=wsl2"* ]]
}

@test "base_init keeps BASE_OS coarse while classifying Ubuntu as linux-debian" {
    local mockbin="$TEST_TMPDIR/mockbin"
    local os_release="$TEST_TMPDIR/os-release"

    create_uname_stub "$mockbin" Linux
    printf 'ID=ubuntu\nID_LIKE=debian\n' > "$os_release"

    PATH="$mockbin:$PATH" BASE_INIT_TEST_OS_RELEASE_PATH="$os_release" run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        printf "BASE_OS=%s\n" "$BASE_OS"
        printf "BASE_PLATFORM=%s\n" "$BASE_PLATFORM"
        printf "BASE_HOST_ENV=%s\n" "$BASE_HOST_ENV"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_OS=linux"* ]]
    [[ "$output" == *"BASE_PLATFORM=linux-debian"* ]]
    [[ "$output" == *"BASE_HOST_ENV=native"* ]]
}

@test "base_init keeps Ubuntu WSL2 on linux-debian with host environment metadata" {
    local mockbin="$TEST_TMPDIR/mockbin"
    local os_release="$TEST_TMPDIR/os-release"
    local kernel_osrelease="$TEST_TMPDIR/kernel-osrelease"
    local proc_version="$TEST_TMPDIR/proc-version"

    create_uname_stub "$mockbin" Linux
    printf 'ID=ubuntu\nID_LIKE=debian\n' > "$os_release"
    printf '5.15.146.1-microsoft-standard-WSL2\n' > "$kernel_osrelease"
    printf 'Linux version 5.15.146.1-microsoft-standard-WSL2\n' > "$proc_version"

    PATH="$mockbin:$PATH" \
        BASE_INIT_TEST_OS_RELEASE_PATH="$os_release" \
        BASE_INIT_TEST_KERNEL_OSRELEASE_PATH="$kernel_osrelease" \
        BASE_INIT_TEST_PROC_VERSION_PATH="$proc_version" \
        run_base_init_script '
            base_home="$1"
            source "$base_home/base_init.sh"
            printf "BASE_OS=%s\n" "$BASE_OS"
            printf "BASE_PLATFORM=%s\n" "$BASE_PLATFORM"
            printf "BASE_HOST_ENV=%s\n" "$BASE_HOST_ENV"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_OS=linux"* ]]
    [[ "$output" == *"BASE_PLATFORM=linux-debian"* ]]
    [[ "$output" == *"BASE_HOST_ENV=wsl2"* ]]
}

@test "base_init keeps non-Debian WSL2 distributions unsupported" {
    local mockbin="$TEST_TMPDIR/mockbin"
    local os_release="$TEST_TMPDIR/os-release"
    local kernel_osrelease="$TEST_TMPDIR/kernel-osrelease"
    local proc_version="$TEST_TMPDIR/proc-version"

    create_uname_stub "$mockbin" Linux
    printf 'ID=fedora\nID_LIKE="rhel fedora"\n' > "$os_release"
    printf '5.15.146.1-microsoft-standard-WSL2\n' > "$kernel_osrelease"
    printf 'Linux version 5.15.146.1-microsoft-standard-WSL2\n' > "$proc_version"

    PATH="$mockbin:$PATH" \
        BASE_INIT_TEST_OS_RELEASE_PATH="$os_release" \
        BASE_INIT_TEST_KERNEL_OSRELEASE_PATH="$kernel_osrelease" \
        BASE_INIT_TEST_PROC_VERSION_PATH="$proc_version" \
        run_base_init_script '
            base_home="$1"
            source "$base_home/base_init.sh"
            printf "BASE_OS=%s\n" "$BASE_OS"
            printf "BASE_PLATFORM=%s\n" "$BASE_PLATFORM"
            printf "BASE_HOST_ENV=%s\n" "$BASE_HOST_ENV"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_OS=linux"* ]]
    [[ "$output" == *"BASE_PLATFORM=linux-unknown"* ]]
    [[ "$output" == *"BASE_HOST_ENV=wsl2"* ]]
}

@test "base_init classifies non-Debian Linux as linux-unknown" {
    local mockbin="$TEST_TMPDIR/mockbin"
    local os_release="$TEST_TMPDIR/os-release"

    create_uname_stub "$mockbin" Linux
    printf 'ID=fedora\nID_LIKE="rhel fedora"\n' > "$os_release"

    PATH="$mockbin:$PATH" BASE_INIT_TEST_OS_RELEASE_PATH="$os_release" run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        printf "BASE_OS=%s\n" "$BASE_OS"
        printf "BASE_PLATFORM=%s\n" "$BASE_PLATFORM"
        printf "BASE_HOST_ENV=%s\n" "$BASE_HOST_ENV"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_OS=linux"* ]]
    [[ "$output" == *"BASE_PLATFORM=linux-unknown"* ]]
    [[ "$output" == *"BASE_HOST_ENV=native"* ]]
}

@test "base_init classifies macOS platform from uname" {
    local mockbin="$TEST_TMPDIR/mockbin"

    create_uname_stub "$mockbin" Darwin

    PATH="$mockbin:$PATH" run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        printf "BASE_OS=%s\n" "$BASE_OS"
        printf "BASE_PLATFORM=%s\n" "$BASE_PLATFORM"
        printf "BASE_HOST_ENV=%s\n" "$BASE_HOST_ENV"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_OS=macos"* ]]
    [[ "$output" == *"BASE_PLATFORM=macos"* ]]
    [[ "$output" == *"BASE_HOST_ENV=native"* ]]
}

@test "base_init marks the Base runtime contract readonly" {
    local var

    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        for var in \
            BASE_HOME \
            BASE_BIN_DIR \
            BASE_CLI_DIR \
            BASE_BASH_DIR \
            BASE_BASH_COMMANDS_DIR \
            BASE_LIB_DIR \
            BASE_BASH_LIB_DIR \
            BASE_BASH_LIBS_DIR \
            BASE_BASH_LIBS_SOURCE \
            BASE_SHELL_DIR \
            BASE_OS \
            BASE_PLATFORM \
            BASE_HOST_ENV \
            BASE_HOST \
            BASE_SHELL; do
            declare -p "$var"
        done
    '

    [ "$status" -eq 0 ]
    for var in \
        BASE_HOME \
        BASE_BIN_DIR \
        BASE_CLI_DIR \
        BASE_BASH_DIR \
        BASE_BASH_COMMANDS_DIR \
        BASE_LIB_DIR \
        BASE_BASH_LIB_DIR \
        BASE_BASH_LIBS_DIR \
        BASE_BASH_LIBS_SOURCE \
        BASE_SHELL_DIR \
        BASE_OS \
        BASE_PLATFORM \
        BASE_HOST_ENV \
        BASE_HOST \
        BASE_SHELL; do
        [[ "$output" == *"declare -rx $var="* ]]
    done
}

@test "base_init readonly contract rejects later mutation" {
    run_base_init_script '
        base_home="$1"
        (
            source "$base_home/base_init.sh"
            BASE_HOME=/tmp/not-base
        )
        printf "mutation_status=%s\n" "$?"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME: readonly variable"* ]]
    [[ "$output" == *"mutation_status=1"* ]]
}

@test "runtime environment docs list the base_init contract variables" {
    local var

    for var in \
        BASE_HOME \
        BASE_BIN_DIR \
        BASE_CLI_DIR \
        BASE_BASH_DIR \
        BASE_BASH_COMMANDS_DIR \
        BASE_LIB_DIR \
        BASE_BASH_LIB_DIR \
        BASE_BASH_LIBS_DIR \
        BASE_BASH_LIBS_SOURCE \
        BASE_SHELL_DIR \
        BASE_OS \
        BASE_PLATFORM \
        BASE_HOST_ENV \
        BASE_HOST \
        BASE_SHELL; do
        grep -F "| \`$var\` |" "$BASE_REPO_ROOT/docs/runtime-environment.md"
    done
}

@test "base_init is idempotent when sourced twice" {
    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        source "$base_home/base_init.sh"
        print_path | grep -Fxc "$BASE_BIN_DIR"
    '

    [ "$status" -eq 0 ]
    [ "$output" = "1" ]
}

@test "base_init import_base_lib resolves libraries relative to external reusable root" {
    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
        import_base_lib file/lib_file.sh
        declare -F safe_touch >/dev/null
    '

    [ "$status" -eq 0 ]
}

@test "base_init can resolve reusable Bash libraries from explicit external dir" {
    local external_dir="$TEST_TMPDIR/base-bash-libs/lib/bash"

    create_external_bash_libs "$external_dir"
    printf '\nexternal_file_marker() { :; }\n' >>"$external_dir/file/lib_file.sh"

    run env \
        -u BASE_HOME \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_BASH_LIBS_SOURCE \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_PLATFORM \
        -u BASE_HOST_ENV \
        -u BASE_HOST \
        -u BASE_SHELL \
        BASE_BASH_LIBS_DIR="$external_dir" \
        bash -c '
            base_home="$1"
            source "$base_home/base_init.sh"
            printf "BASE_BASH_LIBS_DIR=%s\n" "$BASE_BASH_LIBS_DIR"
            printf "BASE_BASH_LIBS_SOURCE=%s\n" "$BASE_BASH_LIBS_SOURCE"
            import_base_lib file/lib_file.sh
            declare -F external_file_marker >/dev/null
        ' bash "$TEST_BASE_HOME"

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_BASH_LIBS_DIR=$external_dir"* ]]
    [[ "$output" == *"BASE_BASH_LIBS_SOURCE=explicit"* ]]
}

@test "base_init resolves sibling base-bash-libs checkout before Homebrew" {
    local external_dir="$TEST_TMPDIR/base-bash-libs/lib/bash"
    local expected_dir

    create_external_bash_libs "$external_dir"
    printf '\nsibling_file_marker() { :; }\n' >>"$external_dir/file/lib_file.sh"
    expected_dir="$(cd "$external_dir" && pwd -P)"

    run env \
        -u BASE_HOME \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_BASH_LIBS_DIR \
        -u BASE_BASH_LIBS_SOURCE \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_PLATFORM \
        -u BASE_HOST_ENV \
        -u BASE_HOST \
        -u BASE_SHELL \
        bash -c '
            base_home="$1"
            source "$base_home/base_init.sh"
            printf "BASE_BASH_LIBS_DIR=%s\n" "$BASE_BASH_LIBS_DIR"
            printf "BASE_BASH_LIBS_SOURCE=%s\n" "$BASE_BASH_LIBS_SOURCE"
            import_base_lib file/lib_file.sh
            declare -F sibling_file_marker >/dev/null
        ' bash "$TEST_BASE_HOME"

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_BASH_LIBS_DIR=$expected_dir"* ]]
    [[ "$output" == *"BASE_BASH_LIBS_SOURCE=sibling"* ]]
}

@test "base_init runs from external reusable libraries when bundled reusable dirs are absent" {
    local external_dir="$TEST_TMPDIR/base-bash-libs/lib/bash"
    local expected_dir

    create_external_bash_libs "$external_dir"
    printf '\nexternal_only_file_marker() { :; }\n' >>"$external_dir/file/lib_file.sh"
    printf '\nexternal_only_git_marker() { :; }\n' >>"$external_dir/git/lib_git.sh"
    expected_dir="$(cd "$external_dir" && pwd -P)"

    run env \
        -u BASE_HOME \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_BASH_LIBS_DIR \
        -u BASE_BASH_LIBS_SOURCE \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_PLATFORM \
        -u BASE_HOST_ENV \
        -u BASE_HOST \
        -u BASE_SHELL \
        bash -c '
            base_home="$1"
            source "$base_home/base_init.sh"
            printf "BASE_BASH_LIBS_DIR=%s\n" "$BASE_BASH_LIBS_DIR"
            printf "BASE_BASH_LIBS_SOURCE=%s\n" "$BASE_BASH_LIBS_SOURCE"
            import_base_lib file/lib_file.sh
            import_base_lib git/lib_git.sh
            declare -F external_only_file_marker >/dev/null
            declare -F external_only_git_marker >/dev/null
            [[ ! -d "$BASE_BASH_LIB_DIR/std" ]]
            [[ ! -d "$BASE_BASH_LIB_DIR/file" ]]
            [[ ! -d "$BASE_BASH_LIB_DIR/git" ]]
        ' bash "$TEST_BASE_HOME"

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_BASH_LIBS_DIR=$expected_dir"* ]]
    [[ "$output" == *"BASE_BASH_LIBS_SOURCE=sibling"* ]]
}

@test "base_init import_base_lib fails when the external reusable library is missing" {
    local external_dir="$TEST_TMPDIR/partial-base-bash-libs/lib/bash"
    local source_dir
    local source_root
    local target_root

    source_dir="$(base_bash_libs_fixture_dir)"
    source_root="$(cd "$source_dir/../.." && pwd -P)"
    mkdir -p "$external_dir/std"
    target_root="$(cd "$external_dir/../.." && pwd -P)"
    cp "$source_dir/std/lib_std.sh" "$external_dir/std/lib_std.sh"
    cp "$source_root/VERSION" "$target_root/VERSION"

    run env \
        -u BASE_HOME \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_BASH_LIBS_SOURCE \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_PLATFORM \
        -u BASE_HOST_ENV \
        -u BASE_HOST \
        -u BASE_SHELL \
        BASE_BASH_LIBS_DIR="$external_dir" \
        bash -c '
            base_home="$1"
            source "$base_home/base_init.sh"
            import_base_lib file/lib_file.sh
        ' bash "$TEST_BASE_HOME"

    [ "$status" -ne 0 ]
    [[ "$output" == *"Base reusable library 'file/lib_file.sh' was not found at '$external_dir/file/lib_file.sh'"* ]]
}

@test "base_init fails clearly when external reusable Bash libraries are unavailable" {
    rm -rf "$TEST_TMPDIR/base-bash-libs"

    run_base_init_script '
        base_home="$1"
        source "$base_home/base_init.sh"
    '

    [ "$status" -ne 0 ]
    [[ "$output" == *"Base reusable Bash libraries were not found."* ]]
    [[ "$output" == *"Tried sibling base-bash-libs checkout at '$TEST_BASE_HOME/../base-bash-libs/lib/bash'."* ]]
    [[ "$output" == *"Clone basefoundry/base-bash-libs next to Base"* ]]
}

@test "base_init resolves Homebrew base-bash-libs next to Homebrew Base" {
    local cellar_base="$TEST_TMPDIR/homebrew/Cellar/base/1.0.3/libexec"
    local opt_dir="$TEST_TMPDIR/homebrew/opt"
    local opt_base="$opt_dir/base/libexec"
    local external_dir="$opt_dir/base-bash-libs/libexec/lib/bash"

    mkdir -p "$opt_dir"
    create_minimal_base_home "$cellar_base"
    create_external_bash_libs "$external_dir"
    printf '\nhomebrew_file_marker() { :; }\n' >>"$external_dir/file/lib_file.sh"
    ln -s "../Cellar/base/1.0.3" "$opt_dir/base"

    run env \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_BASH_LIBS_DIR \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_PLATFORM \
        -u BASE_HOST_ENV \
        -u BASE_HOST \
        -u BASE_SHELL \
        BASE_HOME="$opt_base" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            printf "BASE_BASH_LIBS_DIR=%s\n" "$BASE_BASH_LIBS_DIR"
            printf "BASE_BASH_LIBS_SOURCE=%s\n" "$BASE_BASH_LIBS_SOURCE"
            import_base_lib file/lib_file.sh
            declare -F homebrew_file_marker >/dev/null
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_BASH_LIBS_DIR=$external_dir"* ]]
    [[ "$output" == *"BASE_BASH_LIBS_SOURCE=homebrew"* ]]
}
