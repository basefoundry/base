#!/usr/bin/env bats

load ./basectl_helpers.bash


normalize_tty_output() {
    local text="$1"
    text="${text//$'\r'/}"
    text="${text//$'\b'/}"
    printf '%s' "$text"
}

run_tty_script() {
    local script_path="$1"
    local command
    shift

    command -v script >/dev/null 2>&1 || skip "The 'script' command is required for tty tests."

    if script --version >/dev/null 2>&1; then
        printf -v command '%q ' "$script_path" "$@"
        run script -q -e -c "${command% }" /dev/null
    else
        run script -q /dev/null "$script_path" "$@"
    fi
}

create_doctor_success_stubs() {
    local fake_bin="$1"
    local venv_python="$2"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
if [[ "${1:-}" == "doctor" ]]; then
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
exit 1
EOF
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$venv_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"
}

write_doctor_tty_script() {
    local script_path="$1"
    local fake_bin="$2"
    local term_value="$3"
    local no_color_value="$4"
    local doctor_args="$5"

    cat > "$script_path" <<EOF
#!/usr/bin/env bash
export HOME="$TEST_HOME"
export OSTYPE="darwin24"
export TERM="$term_value"
export PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin"
export BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools"
export BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools"
EOF
    if [[ -n "$no_color_value" ]]; then
        printf 'export NO_COLOR=%q\n' "$no_color_value" >> "$script_path"
    else
        printf 'unset NO_COLOR\n' >> "$script_path"
    fi
    printf 'exec %q/bin/basectl doctor %s\n' "$BASE_REPO_ROOT" "$doctor_args" >> "$script_path"
    chmod +x "$script_path"
}

@test "basectl doctor prints help" {
    run_basectl doctor --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl doctor [project] [options]"* ]]
    [[ "$output" == *"--profile <list>"* ]]
    [[ "$output" == *"Profile lists are comma-separated, for example: --profile dev,sre."* ]]
    [[ "$output" == *"dev - Base development tooling for this repository."* ]]
    [[ "$output" == *"sre - production/SRE prerequisite tooling."* ]]
    [[ "$output" == *"ai  - AI coding assistant tooling."* ]]
    [[ "$output" == *"--remote-network"* ]]
    [[ "$output" == *"--no-color"* ]]
    [[ "$output" != *"--dev"* ]]
    [[ "$output" == *"Diagnose the local Base CLI environment"* ]]
    [[ "$output" == *"Use doctor for finding IDs and fix hints; use check for a quick pass/fail result."* ]]
    [[ "$output" == *"See also:"* ]]
    [[ "$output" == *"basectl check [project] [options]"* ]]
}

@test "basectl doctor uses visual status indicators on a color-capable tty" {
    local fake_bin="$TEST_TMPDIR/bin"
    local normalized script="$TEST_TMPDIR/doctor-tty.sh"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    create_doctor_success_stubs "$fake_bin" "$venv_python"
    write_doctor_tty_script "$script" "$fake_bin" "xterm-256color" "" ""

    run_tty_script "$script"

    [ "$status" -eq 0 ]
    normalized="$(normalize_tty_output "$output")"
    [[ "$normalized" == *$'\033[0;32m✓ ok\033[0m'*"BASE-D001"*"Homebrew"*"Homebrew is installed."* ]]
    [[ "$normalized" == *$'\033[0;32m✓ ok\033[0m'*"BASE-D004"*"Base virtualenv"*"Virtual environment is healthy at"* ]]
}

@test "basectl doctor --no-color disables visual status indicators on a tty" {
    local fake_bin="$TEST_TMPDIR/bin"
    local normalized script="$TEST_TMPDIR/doctor-no-color-tty.sh"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    create_doctor_success_stubs "$fake_bin" "$venv_python"
    write_doctor_tty_script "$script" "$fake_bin" "xterm-256color" "" "--no-color"

    run_tty_script "$script"

    [ "$status" -eq 0 ]
    normalized="$(normalize_tty_output "$output")"
    [[ "$normalized" == *"ok     BASE-D001"*"Homebrew"*"Homebrew is installed."* ]]
    [[ "$normalized" != *"✓ ok"* ]]
    [[ "$normalized" != *$'\033['* ]]
}

@test "basectl doctor honors NO_COLOR on a tty" {
    local fake_bin="$TEST_TMPDIR/bin"
    local normalized script="$TEST_TMPDIR/doctor-no-color-env-tty.sh"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    create_doctor_success_stubs "$fake_bin" "$venv_python"
    write_doctor_tty_script "$script" "$fake_bin" "xterm-256color" "1" ""

    run_tty_script "$script"

    [ "$status" -eq 0 ]
    normalized="$(normalize_tty_output "$output")"
    [[ "$normalized" == *"ok     BASE-D001"*"Homebrew"*"Homebrew is installed."* ]]
    [[ "$normalized" != *"✓ ok"* ]]
    [[ "$normalized" != *$'\033['* ]]
}

@test "basectl doctor keeps plain status indicators for dumb terminals" {
    local fake_bin="$TEST_TMPDIR/bin"
    local normalized script="$TEST_TMPDIR/doctor-dumb-tty.sh"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    create_doctor_success_stubs "$fake_bin" "$venv_python"
    write_doctor_tty_script "$script" "$fake_bin" "dumb" "" ""

    run_tty_script "$script"

    [ "$status" -eq 0 ]
    normalized="$(normalize_tty_output "$output")"
    [[ "$normalized" == *"ok     BASE-D001"*"Homebrew"*"Homebrew is installed."* ]]
    [[ "$normalized" != *"✓ ok"* ]]
    [[ "$normalized" != *$'\033['* ]]
}

@test "basectl doctor reports ok findings and includes dev checks" {
    local fake_bin="$TEST_TMPDIR/bin"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13|bats-core) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/gh" <<'EOF'
#!/usr/bin/env bash
printf 'gh version test\n'
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" && "${3:-}" == "doctor" ]]; then
    printf 'ok     bats-core                   Artifact '\''bats-core'\'' is installed via Homebrew package '\''bats-core'\''.\n'
    printf 'ok     gh                          Artifact '\''gh'\'' is installed via Homebrew package '\''gh'\''.\n'
    exit 0
fi
exit 1
EOF
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$fake_bin/gh" "$venv_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor --profile dev

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base doctor"* ]]
    [[ "$output" == *"ok"*"Homebrew"*"Homebrew is installed."* ]]
    [[ "$output" == *"ok"*"bats-core"*"Artifact 'bats-core' is installed via Homebrew package 'bats-core'."* ]]
    [[ "$output" == *"ok"*"gh"*"Artifact 'gh' is installed via Homebrew package 'gh'."* ]]
    [[ "$output" == *"ok"*"Base virtualenv"*"Virtual environment is healthy at"* ]]
    [[ "$output" == *"Base doctor found no blocking issues."* ]]
}

@test "basectl doctor warns when Homebrew reports outdated Xcode Command Line Tools" {
    local fake_bin="$TEST_TMPDIR/bin"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
if [[ "${1:-}" == "doctor" ]]; then
    printf 'Warning: Your Command Line Tools are too outdated.\n'
    printf 'Update them from Software Update in System Settings.\n'
    exit 1
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
exit 1
EOF
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$venv_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor

    [ "$status" -eq 0 ]
    [[ "$output" == *"warn"*"BASE-D002"*"Xcode Command Line Tools"*"Homebrew reports they are outdated or incomplete."* ]]
    [[ "$output" == *"Fix: Update Xcode Command Line Tools from Software Update, or reinstall them with 'xcode-select --install'."* ]]
    [[ "$output" == *"Base doctor found no blocking issues."* ]]
}

@test "basectl doctor --profile dev reports missing GitHub CLI" {
    local fake_bin="$TEST_TMPDIR/bin"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13|bats-core) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" && "${3:-}" == "doctor" ]]; then
    printf 'ok     bats-core                   Artifact '\''bats-core'\'' is installed via Homebrew package '\''bats-core'\''.\n'
    printf 'error  gh                          Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.\n'
    printf '       Fix: basectl setup --profile dev\n'
    exit 1
fi
exit 1
EOF
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$venv_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor --profile dev

    [ "$status" -eq 1 ]
    [[ "$output" == *"error"*"gh"*"Artifact 'gh' is not installed via Homebrew package 'gh'."* ]]
    [[ "$output" == *"Fix: basectl setup --profile dev"* ]]
}

@test "basectl doctor rejects unknown profiles" {
    run_basectl doctor --profile ops

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported profile 'ops'. Expected one of: dev, sre, ai."* ]]
}

@test "basectl doctor reports errors with suggested fixes" {
    run env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_SETUP_BREW_BIN="$TEST_TMPDIR/missing-brew" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/missing-xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base doctor"* ]]
    [[ "$output" == *"error"*"Homebrew"*"Homebrew is not installed."* ]]
    [[ "$output" == *"Fix: basectl setup"* ]]
    [[ "$output" == *"Base doctor found"*"blocking issue(s)."* ]]
}

@test "basectl doctor reports broken Base virtualenv integrity" {
    local fake_bin="$TEST_TMPDIR/bin"
    local missing_home="$TEST_TMPDIR/missing-python-home"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
exit 1
EOF
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$venv_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    printf 'home = %s\n' "$missing_home" > "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor

    [ "$status" -eq 1 ]
    [[ "$output" == *"error"*"BASE-D004"*"Base virtualenv"*"home path '$missing_home'"* ]]
    [[ "$output" == *"Fix: basectl setup --recreate-venv"* ]]
}

@test "basectl doctor --format json reports structured findings" {
    run --separate-stderr env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_SETUP_BREW_BIN="$TEST_TMPDIR/missing-brew" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/missing-xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "error"'* ]]
    [[ "$output" == *'"findings":'* ]]
    [[ "$output" != *'"ok":'* ]]
    [[ "$output" == *'"id":"BASE-D001","status":"error","name":"homebrew","message":"Homebrew is not installed.","fix":"Run '\''basectl setup'\'' to install Homebrew, or install it manually from https://brew.sh/."'* ]]
    [[ "$output" == *'"id":"BASE-D002","status":"error","name":"xcode_command_line_tools"'* ]]
    [[ "$output" == *'"id":"BASE-D003","status":"error","name":"python"'* ]]
    [[ "$output" == *'"id":"BASE-D004","status":"error","name":"base_virtualenv"'* ]]
    [[ "$output" == *'"id":"BASE-D005","status":"error","name":"pyyaml"'* ]]
    [[ "$output" == *'"id":"BASE-D006","status":"error","name":"click"'* ]]
    [[ "$output" != *"Base doctor"* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl doctor --format json reports outdated Xcode Command Line Tools warning" {
    local fake_bin="$TEST_TMPDIR/bin"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
if [[ "${1:-}" == "doctor" ]]; then
    printf 'Warning: Your Command Line Tools are too outdated.\n'
    printf 'Update them from Software Update in System Settings.\n'
    exit 1
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
exit 1
EOF
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$venv_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"status": "warn"'* ]]
    [[ "$output" == *'"id":"BASE-D002","status":"warn","name":"xcode_command_line_tools","message":"Xcode Command Line Tools are installed, but Homebrew reports they are outdated or incomplete.","fix":"Update Xcode Command Line Tools from Software Update, or reinstall them with '\''xcode-select --install'\''."'* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl doctor project includes project artifact findings" {
    local fake_bin="$TEST_TMPDIR/bin"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")" "$(dirname "$project_python")" "$workspace/demo"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    printf 'ok     demo-artifact               Project artifact check passed.\n'
    exit 0
fi
printf 'unexpected doctor project python args: %s\n' "$*" >&2
exit 1
EOF
    cp "$venv_python" "$project_python"
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$venv_python" "$project_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"
    touch "$TEST_HOME/.base.d/demo/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base doctor for project 'demo'"* ]]
    [[ "$output" != *"Resolved project 'demo' at '$workspace/demo'."* ]]
    [[ "$output" != *"Running Python project doctor layer."* ]]
    [[ "$output" == *"ok"*"demo-artifact"*"Project artifact check passed."* ]]
    [[ "$output" == *"Base doctor found no blocking issues for project 'demo'."* ]]
}

@test "basectl doctor project passes opt-in remote network diagnostics flag" {
    local fake_bin="$TEST_TMPDIR/bin"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")" "$(dirname "$project_python")" "$workspace/demo"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    printf '%s\n' "$@" > "${BASE_TEST_PROJECT_ARGS:?}"
    printf 'ok     demo-artifact               Project artifact check passed.\n'
    exit 0
fi
printf 'unexpected doctor project python args: %s\n' "$*" >&2
exit 1
EOF
    cp "$venv_python" "$project_python"
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$venv_python" "$project_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"
    touch "$TEST_HOME/.base.d/demo/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ARGS="$TEST_TMPDIR/project-args" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor demo --remote-network

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_TMPDIR/project-args")" = "$(printf '%s\n' -m base_setup --manifest "$workspace/demo/base_manifest.yaml" --action doctor --format text --remote-network demo)" ]
}

@test "basectl doctor project --format json includes project findings" {
    local fake_bin="$TEST_TMPDIR/bin"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")" "$(dirname "$project_python")" "$workspace/demo"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    printf '[{"id":"BASE-P033","status":"warn","name":"demo-artifact","message":"Optional project artifact is not installed.","fix":"basectl setup demo"}]\n'
    exit 0
fi
printf 'unexpected doctor project json python args: %s\n' "$*" >&2
exit 1
EOF
    cp "$venv_python" "$project_python"
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$venv_python" "$project_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"
    touch "$TEST_HOME/.base.d/demo/.venv/pyvenv.cfg"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "warn"'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_findings":'* ]]
    [[ "$output" != *'"ok":'* ]]
    [[ "$output" == *'"id":"BASE-P033","status":"warn","name":"demo-artifact","message":"Optional project artifact is not installed.","fix":"basectl setup demo"'* ]]
    [[ "$output" != *"Running Python project doctor layer."* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl doctor project --format json reports broken project virtualenv integrity" {
    local fake_bin="$TEST_TMPDIR/bin"
    local missing_home="$TEST_TMPDIR/missing-project-python-home"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")" "$(dirname "$project_python")" "$workspace/demo"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    printf '%s\n' "$@" > "${BASE_TEST_PROJECT_ARGS:?}"
    shift 2
    action="setup"
    output_format="text"
    while (($#)); do
        case "$1" in
            --action)
                shift
                action="${1:-}"
                ;;
            --format)
                shift
                output_format="${1:-}"
                ;;
        esac
        shift || true
    done
    if [[ "$action" == "predoctor" && "$output_format" == "json" ]]; then
        printf '[{"id":"BASE-P080","status":"ok","name":"git_repository","message":"Project is inside a Git repository.","fix":""}]\n'
        exit 0
    fi
fi
printf 'unexpected doctor project broken venv python args: %s\n' "$*" >&2
exit 1
EOF
    cp "$venv_python" "$project_python"
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$venv_python" "$project_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"
    printf 'home = %s\n' "$missing_home" > "$TEST_HOME/.base.d/demo/.venv/pyvenv.cfg"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ARGS="$TEST_TMPDIR/project-args" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor demo --remote-network --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "error"'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_findings":'* ]]
    [[ "$output" != *'"ok":'* ]]
    [[ "$output" == *'"id":"BASE-P080","status":"ok","name":"git_repository"'* ]]
    [[ "$output" == *'"id":"BASE-P050","status":"error","name":"project_virtualenv"'* ]]
    [[ "$output" == *"Virtual environment Python is broken because home path '$missing_home' no longer provides Python."* ]]
    [[ "$output" == *"Run 'basectl setup demo --recreate-venv' to back up and recreate the project virtual environment."* ]]
    [ "$(cat "$TEST_TMPDIR/project-args")" = "$(printf '%s\n' -m base_setup --manifest "$workspace/demo/base_manifest.yaml" --action predoctor --format json --remote-network demo)" ]
    [ "${stderr:-}" = "" ]
}
