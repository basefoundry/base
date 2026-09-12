#!/usr/bin/env bats

load ./setup_helpers.bash


@test "basectl check prints usage for help" {
    run_base_command check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl check [project] [options]"* ]]
    [[ "$output" == *"Description:"* ]]
    [[ "$output" == *"With no project or"* ]]
    [[ "$output" == *"the command checks only the Base environment."* ]]
    [[ "$output" == *"manifest-declared requirements."* ]]
    [[ "$output" == *"does not install or repair prerequisites, modify project files, or run"* ]]
    [[ "$output" == *"Arguments:"* ]]
    [[ "$output" == *"--manifest can select the project instead."* ]]
    [[ "$output" == *"Options:"* ]]
    [[ "$output" == *"Use noninteractive CI-safe checks. Does not select JSON"* ]]
    [[ "$output" == *"output or run project tests."* ]]
    [[ "$output" != *"--dev"* ]]
    [[ "$output" == *"--profile <list>"* ]]
    [[ "$output" == *"Print human-readable text or structured JSON."* ]]
    [[ "$output" == *"project is omitted, infer it from manifest project.name."* ]]
    [[ "$output" == *"Off by default; requires project or --manifest."* ]]
    [[ "$output" == *"Profiles:"* ]]
    [[ "$output" == *"Profile lists are comma-separated, for example: --profile dev,sre."* ]]
    [[ "$output" == *"dev       - Base development tooling for this repository."* ]]
    [[ "$output" == *"sre       - production/SRE prerequisite tooling."* ]]
    [[ "$output" == *"ai        - AI coding assistant tooling."* ]]
    [[ "$output" == *"linux-lab - Multipass tooling for local Ubuntu lab VMs on macOS hosts."* ]]
    [[ "$output" == *"Examples:"* ]]
    [[ "$output" == *"basectl check base-demo"* ]]
    [[ "$output" == *"basectl check --profile dev,sre"* ]]
    [[ "$output" == *"basectl check --ci base-demo --format json"* ]]
    [[ "$output" == *"basectl check --manifest ./base_manifest.yaml"* ]]
    [[ "$output" == *"basectl check base-demo --remote-network"* ]]
    [[ "$output" == *"Results:"* ]]
    [[ "$output" == *"JSON output includes the aggregate status and"* ]]
    [[ "$output" == *"stable finding IDs for automation."* ]]
    [[ "$output" == *"Clean and warning-only results exit 0. Blocking findings exit 1. Invalid"* ]]
    [[ "$output" == *"command usage exits 2."* ]]
    [[ "$output" == *"Normal runs write Base runtime logs and command history to the local cache."* ]]
    [[ "$output" == *"~/.base.d/<project>/checks/last.json."* ]]
    [[ "$output" == *"See also:"* ]]
    [[ "$output" == *"basectl doctor [project] [options]  Explain findings and provide fix guidance."* ]]
    [[ "$output" == *"basectl test [project] [options]    Run the project-declared test command."* ]]
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
    local warning_recovery_line
    local warning_line

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
    warning_line="$(printf '%s\n' "$output" | grep -F "Xcode Command Line Tools are installed, but Homebrew reports they are outdated or incomplete.")"
    warning_recovery_line="$(printf '%s\n' "$output" | grep -F "Update Xcode Command Line Tools from Software Update, or reinstall them with 'xcode-select --install'.")"
    [[ "$warning_line" == *"WARN"* ]]
    [[ "$warning_recovery_line" == *"WARN"* ]]
    [[ "$output" == *"Xcode Command Line Tools are installed, but Homebrew reports they are outdated or incomplete."* ]]
    [[ "$output" == *"Update Xcode Command Line Tools from Software Update, or reinstall them with 'xcode-select --install'."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
}

@test "basectl check rejects unsupported BASE_PLATFORM before Homebrew probes" {
    run_base_command BASE_SETUP_TEST_PLATFORM=linux-unknown check

    [ "$status" -eq 1 ]
    [[ "$output" == *"supports macOS and Ubuntu/Debian Linux only"* ]]
    [[ "$output" == *"BASE_PLATFORM='linux-unknown'"* ]]
    [[ "$output" != *"Homebrew is not installed."* ]]
}

@test "basectl check supports linux-debian without Homebrew or Xcode probes" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_system_python3_stub
    create_linux_prerequisite_stubs
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command BASE_SETUP_TEST_PLATFORM=linux-debian check

    [ "$status" -eq 0 ]
    [[ "$output" == *"Python is available for Ubuntu/Debian runtime checks."* ]]
    [[ "$output" == *"Virtual environment is healthy at '$venv_dir'."* ]]
    [[ "$output" == *"Python package 'PyYAML' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Python package 'click' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
    [[ "$output" != *"Homebrew"* ]]
    [[ "$output" != *"Xcode"* ]]
}

@test "basectl check linux-debian treats missing dev tools as warnings" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_system_python3_stub
    create_linux_prerequisite_stubs
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command \
        BASE_SETUP_TEST_PLATFORM=linux-debian \
        BASE_SETUP_TEST_MISSING_LINUX_TOOLS=gh,bats,shellcheck,jq,go \
        check

    [ "$status" -eq 0 ]
    [[ "$output" == *"GitHub CLI 'gh' is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"BATS is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"ShellCheck is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"jq is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"Go is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
    [[ "$output" != *"found missing requirements"* ]]
}

@test "basectl check linux-debian reports missing prerequisite apt hints" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    cat > "$TEST_MOCKBIN/python3" <<'EOF'
#!/usr/bin/env bash
# Bash 3 reads BASH_ENV before assigning script arguments.
source "${BASH_ENV:?}"
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" && "${3:-}" == "--help" ]]; then
    exit 1
fi
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/python3"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command \
        BASE_SETUP_TEST_PLATFORM=linux-debian \
        BASE_SETUP_TEST_MISSING_LINUX_TOOLS=git,gh,bats,shellcheck,jq,go \
        check

    [ "$status" -eq 1 ]
    [[ "$output" == *"Python venv support is not available for Ubuntu/Debian runtime checks."* ]]
    [[ "$output" == *"Install python3-venv with 'sudo apt-get install python3-venv', then rerun 'basectl check'."* ]]
    [[ "$output" == *"Git is not available for Ubuntu/Debian runtime checks."* ]]
    [[ "$output" == *"Install git with 'sudo apt-get install git', then rerun 'basectl check'."* ]]
    [[ "$output" == *"GitHub CLI 'gh' is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"Configure GitHub CLI's official Debian/Ubuntu apt repository before installing 'gh'"* ]]
    [[ "$output" == *"https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian"* ]]
    [[ "$output" == *"sudo apt install gh -y"* ]]
    [[ "$output" == *"BATS is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"Install bats with 'sudo apt-get install bats', then rerun 'basectl check'."* ]]
    [[ "$output" == *"ShellCheck is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"Install shellcheck with 'sudo apt-get install shellcheck', then rerun 'basectl check'."* ]]
    [[ "$output" == *"jq is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"Install jq with 'sudo apt-get install jq', then rerun 'basectl check'."* ]]
    [[ "$output" == *"Go is not available for Ubuntu/Debian developer tooling checks."* ]]
    [[ "$output" == *"Install Go with 'sudo apt-get install golang-go', then rerun 'basectl check'."* ]]
    [[ "$output" != *"Homebrew"* ]]
    [[ "$output" != *"Xcode"* ]]
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
        BASE_BASH_LIBS_DRY_RUN=true \
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

    run_base_command check --profile dev,SRE,AI,LINUX-LAB

    [ "$status" -eq 1 ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' check --profile dev,sre,ai,linux-lab)" ]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
}

@test "basectl check rejects unknown profiles" {
    run_base_command check --profile ops

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported profile 'ops'. Expected one of: dev, sre, ai, linux-lab."* ]]
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
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo

    [ "$status" -eq 0 ]
    [[ "$output" != *"Resolved project 'demo' at '$workspace/demo'."* ]]
    [[ "$output" != *"Running Python project check layer."* ]]
    [[ "$output" == *"Project artifact check passed."* ]]
    [[ "$output" == *"Base CLI environment and project 'demo' check passed."* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format text demo)" ]
}

@test "basectl check explicit project ignores different active project virtualenv" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local inherited_venv="$TEST_TMPDIR/active-base-venv"
    local actual_python
    local workspace="$TEST_TMPDIR/workspace"
    local demo_venv_dir="$workspace/demo/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\npython: {}\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$base_venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$demo_venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$inherited_venv"

    run_base_command \
        BASE_SETUP_TEST_WORKSPACE="$workspace" \
        BASE_PROJECT=base \
        BASE_PROJECT_VENV_DIR="$inherited_venv" \
        check demo

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/project-setup-python" ]
    actual_python="$(cat "$TEST_STATE_DIR/project-setup-python")"
    [[ "$actual_python" == *"$base_venv_dir/bin/python"* ]] || {
        printf 'actual project check python: %s\n' "$actual_python" >&3
        false
    }
    [[ "$actual_python" != *"$inherited_venv/bin/python"* ]]
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
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo

    [ "$status" -eq 0 ]
    [ -f "$record_path" ]
    grep -Fq '"schema_version": 2' "$record_path"
    grep -Fq '"project": "demo"' "$record_path"
    grep -Fq '"command": "basectl check"' "$record_path"
    grep -Fq '"status": "ok"' "$record_path"
    grep -Eq '"checked_at": "20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"' "$record_path"
}

@test "basectl check continues with a warning when last check record cannot be saved" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"
    local workspace="$TEST_TMPDIR/workspace"
    local record_parent="$TEST_HOME/.base.d/demo/checks"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo" "$TEST_HOME/.base.d/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    printf 'not-a-directory\n' > "$record_parent"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"WARN"*"Unable to persist latest check record"* ]]
    [[ "$output" == *"Base CLI environment and project 'demo' check passed."* ]]
    [[ "$output" != *"Traceback"* ]]
}

@test "basectl check persists warnings from Base, profile, and project checks in text and JSON modes" {
    local args record_path="$TEST_HOME/.base.d/demo/checks/last.json"
    local source
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
    printf 'ok\n' > "$TEST_STATE_DIR/profile-check-status"
    printf 'ok\n' > "$TEST_STATE_DIR/project-check-status"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv"

    for source in profile project base; do
        printf 'ok\n' > "$TEST_STATE_DIR/profile-check-status"
        printf 'ok\n' > "$TEST_STATE_DIR/project-check-status"
        args=(check demo)
        case "$source" in
            profile)
                printf 'warn\n' > "$TEST_STATE_DIR/profile-check-status"
                args+=(--profile dev)
                ;;
            project)
                printf 'warn\n' > "$TEST_STATE_DIR/project-check-status"
                ;;
            base)
                touch "$TEST_STATE_DIR/xcode-outdated"
                ;;
        esac

        run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" "${args[@]}"

        [ "$status" -eq 0 ]
        grep -Fq '"status": "warn"' "$record_path" || {
            printf 'text mode did not persist %s warning\n' "$source" >&3
            false
        }

        run_base_command_separate_stderr \
            BASE_SETUP_TEST_WORKSPACE="$workspace" \
            "${args[@]}" \
            --format json

        [ "$status" -eq 0 ]
        [[ "$output" == *'"status": "warn"'* ]]
        grep -Fq '"status": "warn"' "$record_path" || {
            printf 'JSON mode did not persist %s warning\n' "$source" >&3
            false
        }
        [ "${stderr:-}" = "" ]
    done
}

@test "basectl check project records failed checks with error status" {
    local record_path="$TEST_HOME/.base.d/demo/checks/last.json"
    local venv_dir="$TEST_HOME/.base.d/base/.venv"
    local workspace="$TEST_TMPDIR/workspace"
    local resolved_demo_root
    local project_venv_error_line
    local project_venv_recovery_error_line
    local summary_error_line
    local summary_recovery_error_line

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\npython: {}\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    resolved_demo_root="$(cd "$workspace/demo" && pwd -P)"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo --verify-project-runtime

    [ "$status" -eq 1 ]
    project_venv_error_line="$(printf '%s\n' "$output" | grep -F "Virtual environment is missing at '$resolved_demo_root/.venv'.")"
    project_venv_recovery_error_line="$(printf '%s\n' "$output" | grep -F "Run 'basectl setup demo --recreate-venv' to back up and recreate the project virtual environment.")"
    summary_error_line="$(printf '%s\n' "$output" | grep -F "Base CLI environment or project 'demo' check found missing requirements.")"
    summary_recovery_error_line="$(printf '%s\n' "$output" | grep -F "Review the specific Fix lines above and rerun 'basectl check demo' after resolving the missing requirements.")"
    [[ "$project_venv_error_line" == *"ERROR"* ]]
    [[ "$project_venv_recovery_error_line" == *"ERROR"* ]]
    [[ "$summary_error_line" == *"ERROR"* ]]
    [[ "$summary_recovery_error_line" == *"ERROR"* ]]
    [ -f "$record_path" ]
    grep -Fq '"project": "demo"' "$record_path"
    grep -Fq '"command": "basectl check"' "$record_path"
    grep -Fq '"status": "error"' "$record_path"
    if grep -Fq '"status": "ok"' "$record_path"; then
        printf 'unexpected ok status in failed check record\n' >&2
        return 1
    fi
    [[ "$output" == *"Virtual environment is missing at '$resolved_demo_root/.venv'."* ]]
}

@test "basectl check reports a failing healthy project check layer as an error" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local project_check_error_line
    local workspace="$TEST_TMPDIR/workspace"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\npython: {}\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$base_venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv" 1

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo

    [ "$status" -eq 1 ]
    project_check_error_line="$(printf '%s\n' "$output" | grep -F "Python project check layer found missing requirements.")"
    [[ "$project_check_error_line" == *"ERROR"* ]]
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
    [[ "$output" != *"$workspace/demo/.venv"* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$manifest_path" --action check --format json demo)" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
}

@test "basectl check shell-only project runs from Base runtime without project venv" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local project_root="$TEST_TMPDIR/shell-only"
    local manifest_path="$project_root/base_manifest.yaml"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$project_root"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_project_setup_venv_stub "$base_venv_dir"
    cp "$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/fixtures/shell-only/base_manifest.yaml" "$manifest_path"

    run_base_command check shell-only --manifest "$manifest_path"

    [ "$status" -eq 0 ]
    [ ! -e "$project_root/.venv" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-python")" = "$base_venv_dir/bin/python" ]
    [[ "$output" != *"Project virtual environment"* ]]
    [[ "$output" != *"BASE-P050"* ]]
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
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo --remote-network

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format text --remote-network demo)" ]

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" \
        check --manifest "$workspace/demo/base_manifest.yaml" --remote-network

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base CLI environment and project 'demo' check passed."* ]]
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

@test "basectl check --format json supports linux-debian readiness findings" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_system_python3_stub
    create_linux_prerequisite_stubs
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command_separate_stderr BASE_SETUP_TEST_PLATFORM=linux-debian check --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    assert_base_check_json_status_for_readiness "$output"
    [[ "$output" == *'"id":"BASE-D003","status":"ok","name":"python","message":"Python is available for Ubuntu/Debian runtime checks."'* ]]
    [[ "$output" == *'"id":"BASE-D004","status":"ok","name":"base_virtualenv"'* ]]
    [[ "$output" == *'"id":"BASE-D005","status":"ok","name":"pyyaml"'* ]]
    [[ "$output" == *'"id":"BASE-D006","status":"ok","name":"click"'* ]]
    [[ "$output" == *'"id":"BASE-D008","status":"ok","name":"bash"'* ]]
    [[ "$output" == *'"id":"BASE-D009","status":"ok","name":"python_venv"'* ]]
    [[ "$output" == *'"id":"BASE-D010","status":"ok","name":"git"'* ]]
    [[ "$output" == *'"id":"BASE-D011","status":"ok","name":"gh"'* ]]
    [[ "$output" == *'"id":"BASE-D012","status":"ok","name":"bats"'* ]]
    [[ "$output" == *'"id":"BASE-D013","status":"ok","name":"shellcheck"'* ]]
    [[ "$output" == *'"id":"BASE-D014","status":"ok","name":"jq"'* ]]
    [[ "$output" == *'"id":"BASE-D015","status":"ok","name":"go"'* ]]
    assert_base_bash_libraries_json_finding "$output"
    [[ "$output" != *'"name":"homebrew"'* ]]
    [[ "$output" != *'"name":"xcode_command_line_tools"'* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --format json reports missing linux dev tools as warnings" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_system_python3_stub
    create_linux_prerequisite_stubs
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command_separate_stderr \
        BASE_SETUP_TEST_PLATFORM=linux-debian \
        BASE_SETUP_TEST_MISSING_LINUX_TOOLS=gh,bats,shellcheck,jq,go \
        check --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "warn"'* ]]
    [[ "$output" == *'"id":"BASE-D010","status":"ok","name":"git"'* ]]
    [[ "$output" == *'"id":"BASE-D011","status":"warn","name":"gh"'* ]]
    [[ "$output" == *'"id":"BASE-D012","status":"warn","name":"bats"'* ]]
    [[ "$output" == *'"id":"BASE-D013","status":"warn","name":"shellcheck"'* ]]
    [[ "$output" == *'"id":"BASE-D014","status":"warn","name":"jq"'* ]]
    [[ "$output" == *'"id":"BASE-D015","status":"warn","name":"go"'* ]]
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
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv"

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
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format json --remote-network demo)" ]
    [ "${stderr:-}" = "" ]

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
        "$BASE_REPO_ROOT/bin/basectl" check \
            --manifest "$workspace/demo/base_manifest.yaml" \
            --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format json demo)" ]
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
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv" 1
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
    printf 'project:\n  name: demo\npython: {}\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$workspace/demo/.venv"
    printf 'home = %s\n' "$missing_home" > "$workspace/demo/.venv/pyvenv.cfg"

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
        "$BASE_REPO_ROOT/bin/basectl" check demo --verify-project-runtime --remote-network --format json

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
    local homebrew_error_line
    local homebrew_recovery_error_line
    local summary_error_line
    local summary_recovery_error_line

    run_base_command check

    [ "$status" -eq 1 ]
    homebrew_error_line="$(printf '%s\n' "$output" | grep -F "Homebrew is not installed.")"
    homebrew_recovery_error_line="$(printf '%s\n' "$output" | grep -F "Run 'basectl setup' to install Homebrew, or install it manually from https://brew.sh/.")"
    summary_error_line="$(printf '%s\n' "$output" | grep -F "Base CLI environment check found missing requirements.")"
    summary_recovery_error_line="$(printf '%s\n' "$output" | grep -F "Review the specific Fix lines above and rerun 'basectl check' after resolving the missing requirements.")"
    [[ "$homebrew_error_line" == *"ERROR"* ]]
    [[ "$homebrew_recovery_error_line" == *"ERROR"* ]]
    [[ "$summary_error_line" == *"ERROR"* ]]
    [[ "$summary_recovery_error_line" == *"ERROR"* ]]
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
    [[ "$output" == *"Review the specific Fix lines above and rerun 'basectl check' after resolving the missing requirements."* ]]
}

@test "basectl check rejects unsupported output formats" {
    run_base_command check --format xml

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported check output format 'xml'."* ]]
}

@test "basectl check rejects remote network checks without a project selector" {
    run_base_command check --remote-network

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--remote-network' requires a project or '--manifest <path>'."* ]]
}

@test "basectl check reports an invalid manifest instead of ignoring it" {
    local manifest_path="$TEST_TMPDIR/missing/base_manifest.yaml"
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_project_setup_venv_stub "$venv_dir"

    run_base_command check --manifest "$manifest_path"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Manifest not found: $manifest_path"* ]]
    [[ "$output" == *"Unable to resolve a project from manifest '$manifest_path'."* ]]
    [ ! -e "$TEST_STATE_DIR/project-setup-ran" ]

    run_base_command check --manifest "$manifest_path" --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *"Manifest not found: $manifest_path"* ]]
    [[ "$output" == *"Unable to resolve a project from manifest '$manifest_path'."* ]]
}
