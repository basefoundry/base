#!/usr/bin/env bats

load ./setup_helpers.bash


@test "basectl check prints usage for help" {
    run_base_command check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl check [project] [options]"* ]]
    [[ "$output" != *"--dev"* ]]
    [[ "$output" == *"--profile <list>"* ]]
    [[ "$output" == *"Verify the local Base CLI environment and, when provided, project artifacts on macOS without making changes."* ]]
}

@test "basectl check passes when all required components are present" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check

    [ "$status" -eq 0 ]
    [[ "$output" == *"Homebrew is installed."* ]]
    [[ "$output" == *"Xcode Command Line Tools are installed."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is installed via Homebrew."* ]]
    [[ "$output" != *"BATS formula 'bats-core'"* ]]
    [[ "$output" == *"Virtual environment is healthy at '$venv_dir'."* ]]
    [[ "$output" == *"Python package 'PyYAML' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Python package 'click' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
    [ "$(grep -c '^PyYAML$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
    [ "$(grep -c '^click$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
}

@test "basectl check ignores inherited setup dry-run and recreate state" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command \
        DRY_RUN=true \
        BASE_SETUP_RECREATE_VENV=true \
        check

    [ "$status" -eq 0 ]
    [[ "$output" == *"Python package 'PyYAML' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Python package 'click' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
    [ "$(grep -c '^PyYAML$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
    [ "$(grep -c '^click$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
}

@test "basectl check fails when a required Base Python package is missing" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check

    [ "$status" -eq 1 ]
    [[ "$output" == *"Virtual environment is healthy at '$venv_dir'."* ]]
    [[ "$output" == *"Python package 'PyYAML' is not installed in the Base virtual environment."* ]]
    [[ "$output" == *"Run 'basectl setup' to install Base Python bootstrap packages."* ]]
    [[ "$output" == *"Python package 'click' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
    [ "$(grep -c '^PyYAML$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
    [ "$(grep -c '^click$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
}

@test "basectl check --profile dev includes manifest-driven developer prerequisite checks" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check --profile dev

    [ "$status" -eq 1 ]
    [[ "$output" == *"Artifact 'bats-core' is not installed via Homebrew package 'bats-core'."* ]]
    [[ "$output" == *"Artifact 'gh' is not installed via Homebrew package 'gh'."* ]]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
}

@test "basectl check --profile sre forwards profile to prerequisite layer" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check --profile sre

    [ "$status" -eq 1 ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' check --profile sre)" ]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
}

@test "basectl check accepts comma separated profile lists case-insensitively" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check --profile dev,SRE

    [ "$status" -eq 1 ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' check --profile dev,sre)" ]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
}

@test "basectl check rejects unknown profiles" {
    run_base_command check --profile ai

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unsupported profile 'ai'. Expected one of: dev, sre."* ]]
}

@test "basectl check rejects empty profile list entries" {
    run_base_command check --profile dev,,sre

    [ "$status" -eq 1 ]
    [[ "$output" == *"Profile list must not contain empty entries."* ]]
}

@test "basectl check project verifies project artifacts" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"
    local workspace="$TEST_TMPDIR/workspace"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$TEST_HOME/.base.d/demo/.venv"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo

    [ "$status" -eq 0 ]
    [[ "$output" != *"Resolved project 'demo' at '$workspace/demo'."* ]]
    [[ "$output" != *"Running Python project check layer."* ]]
    [[ "$output" == *"Project artifact check passed."* ]]
    [[ "$output" == *"Base CLI environment and project 'demo' check passed."* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format text demo)" ]
}

@test "basectl check --format json writes successful check results to stdout" {
    local click_line
    local pyyaml_line
    local venv_line
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"ok": true'* ]]
    [[ "$output" == *'"name":"homebrew","ok":true'* ]]
    [[ "$output" != *'"name":"bats"'* ]]
    [[ "$output" == *'"name":"pyyaml","ok":true'* ]]
    [[ "$output" == *'"name":"click","ok":true'* ]]
    [[ "$output" == *'"name":"base_virtualenv","ok":true'* ]]
    venv_line="$(printf '%s\n' "$output" | grep -n '"name":"base_virtualenv"' | cut -d: -f1)"
    pyyaml_line="$(printf '%s\n' "$output" | grep -n '"name":"pyyaml"' | cut -d: -f1)"
    click_line="$(printf '%s\n' "$output" | grep -n '"name":"click"' | cut -d: -f1)"
    [ "$venv_line" -lt "$pyyaml_line" ]
    [ "$pyyaml_line" -lt "$click_line" ]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --format json reports broken Base virtualenv integrity" {
    local missing_home="$TEST_TMPDIR/missing-python-home"
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"
    printf 'home = %s\n' "$missing_home" > "$venv_dir/pyvenv.cfg"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"ok": false'* ]]
    [[ "$output" == *'"name":"base_virtualenv","ok":false'* ]]
    [[ "$output" == *"Virtual environment Python is broken because home path '$missing_home' no longer provides Python."* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --format json escapes C0 control characters and DEL in strings" {
    local control_package
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    control_package=$'Py\vYAML\177'
    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_PYYAML_PACKAGE="$control_package" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *"Py\\u000bYAML\\u007f"* ]]
    [[ "$output" != *"$control_package"* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check project --format json includes project check results" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"
    local workspace="$TEST_TMPDIR/workspace"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$TEST_HOME/.base.d/demo/.venv"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_TEST_WORKSPACE="$workspace" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
    [[ "$output" == *'"name":"demo-artifact","ok":true'* || "$output" == *'"name": "demo-artifact"'* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check project --format json reports broken project virtualenv integrity" {
    local missing_home="$TEST_TMPDIR/missing-project-python-home"
    local venv_dir="$TEST_HOME/.base.d/base/.venv"
    local workspace="$TEST_TMPDIR/workspace"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$TEST_HOME/.base.d/demo/.venv"
    printf 'home = %s\n' "$missing_home" > "$TEST_HOME/.base.d/demo/.venv/pyvenv.cfg"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_TEST_WORKSPACE="$workspace" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check demo --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"ok": false'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
    [[ "$output" == *'"name":"project_virtualenv","ok":false'* ]]
    [[ "$output" == *"Virtual environment Python is broken because home path '$missing_home' no longer provides Python."* ]]
    [[ "$output" == *"Run 'basectl setup demo --recreate-venv' to back up and recreate the project virtual environment."* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --profile dev --format json includes developer prerequisite check results" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --profile dev --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"ok": false'* ]]
    [[ "$output" == *'"profile_checks":'* ]]
    [[ "$output" != *'"dev_checks":'* ]]
    [[ "$output" == *"bats-core"* ]]
    [[ "$output" == *"gh"* ]]
    [[ "$output" == *'"name":"pyyaml","ok":true'* ]]
    [[ "$output" == *'"name":"click","ok":true'* ]]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' check --format json --profile dev)" ]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --profile sre --format json writes profile check results" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --profile sre --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"profile_checks":'* ]]
    [[ "$output" != *'"dev_checks":'* ]]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' check --format json --profile sre)" ]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --format json writes failed check results to stdout" {
    create_xcode_stubs

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"ok": false'* ]]
    [[ "$output" == *'"name":"homebrew","ok":false'* ]]
    [[ "$output" == *'"name":"pyyaml","ok":false'* ]]
    [[ "$output" == *'"name":"click","ok":false'* ]]
    [[ "$output" == *'"name":"base_virtualenv","ok":false'* ]]
    [[ "$output" == *"Virtual environment is missing at '$TEST_HOME/.base.d/base/.venv'."* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check fails when required components are missing" {
    run_base_command check

    [ "$status" -eq 1 ]
    [[ "$output" == *"Homebrew is not installed."* ]]
    [[ "$output" == *"Run 'basectl setup' to install Homebrew, or install it manually from https://brew.sh/."* ]]
    [[ "$output" == *"Xcode Command Line Tools are not installed."* ]]
    [[ "$output" == *"Run 'xcode-select --install' in an interactive terminal, complete the installer, then rerun 'basectl setup'."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is not installed via Homebrew."* ]]
    [[ "$output" == *"Run 'basectl setup' to install Homebrew Python, or run 'brew install python@3.13'."* ]]
    [[ "$output" != *"BATS formula 'bats-core'"* ]]
    [[ "$output" == *"Virtual environment is missing at '$TEST_HOME/.base.d/base/.venv'."* ]]
    [[ "$output" == *"Run 'basectl setup --recreate-venv' to back up and recreate the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
    [[ "$output" == *"Run 'basectl setup' to reconcile the missing requirements."* ]]
}

@test "basectl check rejects unsupported output formats" {
    run_base_command check --format xml

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unsupported check output format 'xml'."* ]]
}
