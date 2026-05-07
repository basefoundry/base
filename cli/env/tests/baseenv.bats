#!/usr/bin/env bats

load ../../bash/tests/test_helper.bash

readonly BASE_ENV_SCRIPT="$BASE_REPO_ROOT/cli/env/baseenv.sh"

create_env_layout() {
    local repo_root="$1"

    mkdir -p "$repo_root/cli/env" "$repo_root/cli/bash/bin" "$repo_root/cli/bash/lib" "$repo_root/cli/bash/commands" "$repo_root/cli/python"
    cp "$BASE_ENV_SCRIPT" "$repo_root/cli/env/baseenv.sh"
}

@test "baseenv must be sourced rather than executed" {
    run bash "$BASE_ENV_SCRIPT"

    [ "$status" -eq 1 ]
    [[ "$output" == *"baseenv.sh must be sourced, not executed."* ]]
}

@test "sourcing baseenv defines shared CLI roots and exports only the stable contract" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local script="$BATS_TEST_TMPDIR/check-bash-env.sh"
    local expected_repo_root expected_cli_root expected_env_dir expected_bash_root expected_bash_bin expected_python_root

    create_env_layout "$repo_root"
    expected_repo_root="$(cd "$repo_root" && pwd -P)"
    expected_cli_root="$(cd "$repo_root/cli" && pwd -P)"
    expected_env_dir="$(cd "$repo_root/cli/env" && pwd -P)"
    expected_bash_root="$(cd "$repo_root/cli/bash" && pwd -P)"
    expected_bash_bin="$(cd "$repo_root/cli/bash/bin" && pwd -P)"
    expected_python_root="$(cd "$repo_root/cli/python" && pwd -P)"

    cat > "$script" <<EOF
#!/usr/bin/env bash
source "$repo_root/cli/env/baseenv.sh"
source "$repo_root/cli/env/baseenv.sh"
printf 'repo=%s\n' "\$BASE_REPO_ROOT"
printf 'cli=%s\n' "\$BASE_CLI_ROOT"
printf 'env_dir=%s\n' "\$BASE_CLI_ENV_DIR"
printf 'env_script=%s\n' "\$BASE_CLI_ENV_SCRIPT"
printf 'bash_root=%s\n' "\$BASE_BASH_ROOT"
printf 'bash_bin=%s\n' "\$BASE_BASH_BIN_DIR"
printf 'python_root=%s\n' "\$BASE_PYTHON_ROOT"
printf 'export_repo=%s\n' "\$(env | grep -c '^BASE_REPO_ROOT=')"
printf 'export_cli=%s\n' "\$(env | grep -c '^BASE_CLI_ROOT=')"
printf 'export_env_script=%s\n' "\$(env | grep -c '^BASE_CLI_ENV_SCRIPT=')"
printf 'export_bash_root=%s\n' "\$(env | grep -c '^BASE_BASH_ROOT=')"
printf 'export_python_root=%s\n' "\$(env | grep -c '^BASE_PYTHON_ROOT=')"
printf 'export_env_dir=%s\n' "\$(env | grep -c '^BASE_CLI_ENV_DIR=')"
printf 'export_bash_bin=%s\n' "\$(env | grep -c '^BASE_BASH_BIN_DIR=')"
printf 'export_bash_lib=%s\n' "\$(env | grep -c '^BASE_BASH_LIB_DIR=')"
printf 'export_commands=%s\n' "\$(env | grep -c '^BASE_BASH_COMMANDS_DIR=')"
count=0
IFS=':'
for entry in \$PATH; do
    if [[ "\$entry" == "\$BASE_BASH_BIN_DIR" ]]; then
        count=\$((count + 1))
    fi
done
unset IFS
printf 'bin_count=%s\n' "\$count"
EOF
    chmod +x "$script"

    run bash "$script"

    [ "$status" -eq 0 ]
    [[ "$output" == *"repo=$expected_repo_root"* ]]
    [[ "$output" == *"cli=$expected_cli_root"* ]]
    [[ "$output" == *"env_dir=$expected_env_dir"* ]]
    [[ "$output" == *"env_script=$expected_env_dir/baseenv.sh"* ]]
    [[ "$output" == *"bash_root=$expected_bash_root"* ]]
    [[ "$output" == *"bash_bin=$expected_bash_bin"* ]]
    [[ "$output" == *"python_root=$expected_python_root"* ]]
    [[ "$output" == *"export_repo=1"* ]]
    [[ "$output" == *"export_cli=1"* ]]
    [[ "$output" == *"export_env_script=1"* ]]
    [[ "$output" == *"export_bash_root=1"* ]]
    [[ "$output" == *"export_python_root=1"* ]]
    [[ "$output" == *"export_env_dir=0"* ]]
    [[ "$output" == *"export_bash_bin=0"* ]]
    [[ "$output" == *"export_bash_lib=0"* ]]
    [[ "$output" == *"export_commands=0"* ]]
    [[ "$output" == *"bin_count=1"* ]]
}

@test "sourcing baseenv under zsh defines shared CLI roots and updates PATH once" {
    local repo_root="$BATS_TEST_TMPDIR/repo"
    local expected_repo_root expected_cli_root expected_env_dir expected_bash_root expected_bash_bin expected_python_root

    create_env_layout "$repo_root"
    expected_repo_root="$(cd "$repo_root" && pwd -P)"
    expected_cli_root="$(cd "$repo_root/cli" && pwd -P)"
    expected_env_dir="$(cd "$repo_root/cli/env" && pwd -P)"
    expected_bash_root="$(cd "$repo_root/cli/bash" && pwd -P)"
    expected_bash_bin="$(cd "$repo_root/cli/bash/bin" && pwd -P)"
    expected_python_root="$(cd "$repo_root/cli/python" && pwd -P)"

    run zsh -lc "
        source '$repo_root/cli/env/baseenv.sh'
        source '$repo_root/cli/env/baseenv.sh'
        print -r -- repo:\$BASE_REPO_ROOT
        print -r -- cli:\$BASE_CLI_ROOT
        print -r -- env_dir:\$BASE_CLI_ENV_DIR
        print -r -- env_script:\$BASE_CLI_ENV_SCRIPT
        print -r -- bash_root:\$BASE_BASH_ROOT
        print -r -- bash_bin:\$BASE_BASH_BIN_DIR
        print -r -- python_root:\$BASE_PYTHON_ROOT
        count=0
        for entry in \${(s/:/)PATH}; do
            [[ \"\$entry\" == \"\$BASE_BASH_BIN_DIR\" ]] && ((count++))
        done
        print -r -- bin_count:\$count
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"repo:$expected_repo_root"* ]]
    [[ "$output" == *"cli:$expected_cli_root"* ]]
    [[ "$output" == *"env_dir:$expected_env_dir"* ]]
    [[ "$output" == *"env_script:$expected_env_dir/baseenv.sh"* ]]
    [[ "$output" == *"bash_root:$expected_bash_root"* ]]
    [[ "$output" == *"bash_bin:$expected_bash_bin"* ]]
    [[ "$output" == *"python_root:$expected_python_root"* ]]
    [[ "$output" == *"bin_count:1"* ]]
}
