#!/usr/bin/env bats

load ./setup_helpers.bash


@test "basectl check prints usage for help" {
    run_base_command check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl check [project] [options]"* ]]
    [[ "$output" != *"--dev"* ]]
    [[ "$output" == *"--profile <list>"* ]]
    [[ "$output" == *"Profile lists are comma-separated, for example: --profile dev,sre."* ]]
    [[ "$output" == *"dev - Base development tooling for this repository."* ]]
    [[ "$output" == *"sre - production/SRE prerequisite tooling."* ]]
    [[ "$output" == *"ai  - AI coding assistant tooling."* ]]
    [[ "$output" == *"--remote-network"* ]]
    [[ "$output" == *"Verify the local Base CLI environment and, when provided, project artifacts on macOS without making changes."* ]]
    [[ "$output" == *"Use check for a quick pass/fail result; use doctor for finding IDs and fix hints."* ]]
    [[ "$output" == *"See also:"* ]]
    [[ "$output" == *"basectl doctor [project] [options]"* ]]
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

@test "basectl check warns when Homebrew reports outdated Xcode Command Line Tools" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    touch "$TEST_STATE_DIR/xcode-outdated"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check

    [ "$status" -eq 0 ]
    [[ "$output" == *"Xcode Command Line Tools are installed, but Homebrew reports they are outdated or incomplete."* ]]
    [[ "$output" == *"Update Xcode Command Line Tools from Software Update, or reinstall them with 'xcode-select --install'."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
}

@test "basectl check preserves text order while base probes overlap" {
    local click_line homebrew_line python_line pyyaml_line venv_line xcode_line
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command \
        BASE_SETUP_TEST_XCODE_WAIT_FOR_PIP_SHOW=true \
        BASE_SETUP_TEST_XCODE_PIP_WAIT_SECONDS=2 \
        check

    [ "$status" -eq 0 ]
    homebrew_line="$(printf '%s\n' "$output" | grep -n "Homebrew is installed." | head -n 1 | cut -d: -f1)"
    xcode_line="$(printf '%s\n' "$output" | grep -n "Xcode Command Line Tools are installed." | head -n 1 | cut -d: -f1)"
    python_line="$(printf '%s\n' "$output" | grep -n "Python formula 'python@3.13' is installed via Homebrew." | head -n 1 | cut -d: -f1)"
    venv_line="$(printf '%s\n' "$output" | grep -n "Virtual environment is healthy at '$venv_dir'." | head -n 1 | cut -d: -f1)"
    pyyaml_line="$(printf '%s\n' "$output" | grep -n "Python package 'PyYAML' is installed in the Base virtual environment." | head -n 1 | cut -d: -f1)"
    click_line="$(printf '%s\n' "$output" | grep -n "Python package 'click' is installed in the Base virtual environment." | head -n 1 | cut -d: -f1)"
    [ "$homebrew_line" -lt "$xcode_line" ]
    [ "$xcode_line" -lt "$python_line" ]
    [ "$python_line" -lt "$venv_line" ]
    [ "$venv_line" -lt "$pyyaml_line" ]
    [ "$pyyaml_line" -lt "$click_line" ]
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

    run_base_command check --profile dev,SRE,AI

    [ "$status" -eq 1 ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' check --profile dev,sre,ai)" ]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
}

@test "basectl check rejects unknown profiles" {
    run_base_command check --profile ops

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported profile 'ops'. Expected one of: dev, sre, ai."* ]]
}

@test "basectl check rejects empty profile list entries" {
    run_base_command check --profile dev,,sre

    [ "$status" -eq 2 ]
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

@test "basectl check project records last check status" {
    local record_path="$TEST_HOME/.base.d/demo/checks/last.json"
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
    [ -f "$record_path" ]
    grep -Fq '"schema_version": 1' "$record_path"
    grep -Fq '"project": "demo"' "$record_path"
    grep -Fq '"command": "basectl check"' "$record_path"
    grep -Fq '"status": "ok"' "$record_path"
    grep -Eq '"checked_at": "20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"' "$record_path"
}

@test "basectl check project records failed checks with error status" {
    local record_path="$TEST_HOME/.base.d/demo/checks/last.json"
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

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo

    [ "$status" -eq 1 ]
    [ -f "$record_path" ]
    grep -Fq '"project": "demo"' "$record_path"
    grep -Fq '"command": "basectl check"' "$record_path"
    grep -Fq '"status": "error"' "$record_path"
    ! grep -Fq '"status": "ok"' "$record_path"
    [[ "$output" == *"Virtual environment is missing at '$TEST_HOME/.base.d/demo/.venv'."* ]]
}

@test "basectl check uv-managed project does not require historical Base project venv" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local project_root="$TEST_TMPDIR/demo"
    local manifest_path="$project_root/base_manifest.yaml"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$project_root"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_project_setup_venv_stub "$base_venv_dir"
    printf 'project:\n  name: demo\npython:\n  manager: uv\nartifacts: []\n' > "$manifest_path"

    run_base_command check demo --manifest "$manifest_path" --format json

    [ "$status" -eq 0 ]
    [[ "$output" != *"BASE-P050"* ]]
    [[ "$output" != *"$TEST_HOME/.base.d/demo/.venv"* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$manifest_path" --action check --format json demo)" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
}

@test "basectl check project passes opt-in remote network diagnostics flag" {
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

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo --remote-network

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format text --remote-network demo)" ]
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
    [[ "$output" == *'"schema_version": 1'* ]]
    assert_base_check_json_status_for_readiness "$output"
    [[ "$output" == *'"id":"BASE-D001","status":"ok","name":"homebrew"'* ]]
    assert_base_bash_libraries_json_finding "$output"
    [[ "$output" != *'"name":"bats"'* ]]
    [[ "$output" == *'"id":"BASE-D005","status":"ok","name":"pyyaml"'* ]]
    [[ "$output" == *'"id":"BASE-D006","status":"ok","name":"click"'* ]]
    [[ "$output" == *'"id":"BASE-D004","status":"ok","name":"base_virtualenv"'* ]]
    [[ "$output" != *'"ok":'* ]]
    venv_line="$(printf '%s\n' "$output" | grep -n '"name":"base_virtualenv"' | cut -d: -f1)"
    pyyaml_line="$(printf '%s\n' "$output" | grep -n '"name":"pyyaml"' | cut -d: -f1)"
    click_line="$(printf '%s\n' "$output" | grep -n '"name":"click"' | cut -d: -f1)"
    [ "$venv_line" -lt "$pyyaml_line" ]
    [ "$pyyaml_line" -lt "$click_line" ]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --format json preserves finding order while base probes overlap" {
    local bash_libs_line click_line homebrew_line python_line pyyaml_line venv_line xcode_line
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
        BASE_SETUP_TEST_XCODE_WAIT_FOR_PIP_SHOW=true \
        BASE_SETUP_TEST_XCODE_PIP_WAIT_SECONDS=2 \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    assert_base_check_json_status_for_readiness "$output"
    homebrew_line="$(printf '%s\n' "$output" | grep -n '"id":"BASE-D001","status":"ok","name":"homebrew"' | cut -d: -f1)"
    bash_libs_line="$(base_bash_libraries_json_line "$output")"
    xcode_line="$(printf '%s\n' "$output" | grep -n '"id":"BASE-D002","status":"ok","name":"xcode_command_line_tools"' | cut -d: -f1)"
    python_line="$(printf '%s\n' "$output" | grep -n '"id":"BASE-D003","status":"ok","name":"python"' | cut -d: -f1)"
    venv_line="$(printf '%s\n' "$output" | grep -n '"id":"BASE-D004","status":"ok","name":"base_virtualenv"' | cut -d: -f1)"
    pyyaml_line="$(printf '%s\n' "$output" | grep -n '"id":"BASE-D005","status":"ok","name":"pyyaml"' | cut -d: -f1)"
    click_line="$(printf '%s\n' "$output" | grep -n '"id":"BASE-D006","status":"ok","name":"click"' | cut -d: -f1)"
    [ "$homebrew_line" -lt "$bash_libs_line" ]
    [ "$bash_libs_line" -lt "$xcode_line" ]
    [ "$xcode_line" -lt "$python_line" ]
    [ "$python_line" -lt "$venv_line" ]
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
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "error"'* ]]
    [[ "$output" == *'"id":"BASE-D004","status":"error","name":"base_virtualenv"'* ]]
    [[ "$output" != *'"ok":'* ]]
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
        "$BASE_REPO_ROOT/bin/basectl" check demo --remote-network --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    assert_base_check_json_status_for_readiness "$output"
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
    [[ "$output" == *'"schema_version":1,"status":"ok","project":"demo","checks"'* ]]
    [[ "$output" == *'"id":"BASE-P040","status":"ok","name":"demo-artifact"'* ]]
    [[ "$output" != *'"ok":'* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check project --format json fails fast on runtime directory errors" {
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
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$TEST_HOME/.base.d/demo/.venv" 1
    touch "$TEST_STATE_DIR/project-setup-fail-before-output"
    printf "Error: Unable to create Base runtime directory '%s'.\n" "$TEST_TMPDIR/unwritable-cache/cli/base_setup/logs" > "$TEST_STATE_DIR/project-setup-stderr"

    run_base_command_separate_stderr BASE_SETUP_TEST_WORKSPACE="$workspace" check demo --format json

    [ "$status" -eq 1 ]
    [ "$output" = "" ]
    [[ "$stderr" == *"Error: Unable to create Base runtime directory"* ]]
    [[ "$stderr" != *'"project_checks"'* ]]
    [[ "$stderr" != *"Project artifact check passed."* ]]
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
        "$BASE_REPO_ROOT/bin/basectl" check demo --remote-network --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "error"'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
    [[ "$output" == *'"id":"BASE-P080","status":"ok","name":"git_repository"'* ]]
    [[ "$output" == *'"id":"BASE-P083","status":"ok","name":"git_origin_reachability"'* ]]
    [[ "$output" == *'"id":"BASE-P050","status":"error","name":"project_virtualenv"'* ]]
    [[ "$output" != *'"ok":'* ]]
    [[ "$output" == *"Virtual environment Python is broken because home path '$missing_home' no longer provides Python."* ]]
    [[ "$output" == *"Run 'basectl setup demo --recreate-venv' to back up and recreate the project virtual environment."* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --format json warns when Homebrew reports outdated Xcode Command Line Tools" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    touch "$TEST_STATE_DIR/xcode-outdated"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command_separate_stderr check --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"id":"BASE-D002","status":"warn","name":"xcode_command_line_tools"'* ]]
    [[ "$output" == *"Xcode Command Line Tools are installed, but Homebrew reports they are outdated or incomplete."* ]]
    [[ "$output" == *"Update Xcode Command Line Tools from Software Update, or reinstall them with 'xcode-select --install'."* ]]
    [[ "$output" != *'"ok":'* ]]
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
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "error"'* ]]
    [[ "$output" == *'"profile_checks":'* ]]
    [[ "$output" != *'"dev_checks":'* ]]
    [[ "$output" == *"bats-core"* ]]
    [[ "$output" == *"gh"* ]]
    [[ "$output" == *'"id":"BASE-D005","status":"ok","name":"pyyaml"'* ]]
    [[ "$output" == *'"id":"BASE-D006","status":"ok","name":"click"'* ]]
    [[ "$output" != *'"ok":'* ]]
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
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "error"'* ]]
    [[ "$output" == *'"id":"BASE-D001","status":"error","name":"homebrew"'* ]]
    [[ "$output" == *'"id":"BASE-D005","status":"error","name":"pyyaml"'* ]]
    [[ "$output" == *'"id":"BASE-D006","status":"error","name":"click"'* ]]
    [[ "$output" == *'"id":"BASE-D004","status":"error","name":"base_virtualenv"'* ]]
    [[ "$output" != *'"ok":'* ]]
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

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported check output format 'xml'."* ]]
}
