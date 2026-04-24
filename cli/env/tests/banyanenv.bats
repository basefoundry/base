#!/usr/bin/env bats

load ../../bash/tests/test_helper.bash

readonly BANYAN_ENV_SCRIPT="$BANYAN_REPO_ROOT/cli/env/banyanenv.sh"

create_env_layout() {
    local repo_root="$1"

    mkdir -p "$repo_root/cli/env" "$repo_root/cli/bash/bin" "$repo_root/cli/bash/lib" "$repo_root/cli/bash/commands" "$repo_root/cli/python"
    cp "$BANYAN_ENV_SCRIPT" "$repo_root/cli/env/banyanenv.sh"
}

@test "banyanenv must be sourced rather than executed" {
    run bash "$BANYAN_ENV_SCRIPT"

    [ "$status" -eq 1 ]
    [[ "$output" == *"banyanenv.sh must be sourced, not executed."* ]]
}

@test "sourcing banyanenv under bash exports shared CLI roots and updates PATH once" {
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
source "$repo_root/cli/env/banyanenv.sh"
source "$repo_root/cli/env/banyanenv.sh"
printf 'repo=%s\n' "\$BANYAN_REPO_ROOT"
printf 'cli=%s\n' "\$BANYAN_CLI_ROOT"
printf 'env_dir=%s\n' "\$BANYAN_CLI_ENV_DIR"
printf 'env_script=%s\n' "\$BANYAN_CLI_ENV_SCRIPT"
printf 'bash_root=%s\n' "\$BANYAN_BASH_ROOT"
printf 'bash_bin=%s\n' "\$BANYAN_BASH_BIN_DIR"
printf 'python_root=%s\n' "\$BANYAN_PYTHON_ROOT"
count=0
IFS=':'
for entry in \$PATH; do
    if [[ "\$entry" == "\$BANYAN_BASH_BIN_DIR" ]]; then
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
    [[ "$output" == *"env_script=$expected_env_dir/banyanenv.sh"* ]]
    [[ "$output" == *"bash_root=$expected_bash_root"* ]]
    [[ "$output" == *"bash_bin=$expected_bash_bin"* ]]
    [[ "$output" == *"python_root=$expected_python_root"* ]]
    [[ "$output" == *"bin_count=1"* ]]
}

@test "sourcing banyanenv under zsh exports shared CLI roots and updates PATH once" {
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
        source '$repo_root/cli/env/banyanenv.sh'
        source '$repo_root/cli/env/banyanenv.sh'
        print -r -- repo:\$BANYAN_REPO_ROOT
        print -r -- cli:\$BANYAN_CLI_ROOT
        print -r -- env_dir:\$BANYAN_CLI_ENV_DIR
        print -r -- env_script:\$BANYAN_CLI_ENV_SCRIPT
        print -r -- bash_root:\$BANYAN_BASH_ROOT
        print -r -- bash_bin:\$BANYAN_BASH_BIN_DIR
        print -r -- python_root:\$BANYAN_PYTHON_ROOT
        count=0
        for entry in \${(s/:/)PATH}; do
            [[ \"\$entry\" == \"\$BANYAN_BASH_BIN_DIR\" ]] && ((count++))
        done
        print -r -- bin_count:\$count
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"repo:$expected_repo_root"* ]]
    [[ "$output" == *"cli:$expected_cli_root"* ]]
    [[ "$output" == *"env_dir:$expected_env_dir"* ]]
    [[ "$output" == *"env_script:$expected_env_dir/banyanenv.sh"* ]]
    [[ "$output" == *"bash_root:$expected_bash_root"* ]]
    [[ "$output" == *"bash_bin:$expected_bash_bin"* ]]
    [[ "$output" == *"python_root:$expected_python_root"* ]]
    [[ "$output" == *"bin_count:1"* ]]
}
