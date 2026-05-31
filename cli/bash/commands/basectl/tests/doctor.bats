#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl doctor prints help" {
    run_basectl doctor --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl doctor [project] [options]"* ]]
    [[ "$output" == *"Diagnose the local Base CLI environment"* ]]
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
        "$BASE_REPO_ROOT/bin/basectl" doctor --dev

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base doctor"* ]]
    [[ "$output" == *"ok"*"Homebrew"*"Homebrew is installed."* ]]
    [[ "$output" == *"ok"*"bats-core"*"Artifact 'bats-core' is installed via Homebrew package 'bats-core'."* ]]
    [[ "$output" == *"ok"*"gh"*"Artifact 'gh' is installed via Homebrew package 'gh'."* ]]
    [[ "$output" == *"ok"*"Base virtualenv"*"Virtual environment exists at"* ]]
    [[ "$output" == *"Base doctor found no blocking issues."* ]]
}

@test "basectl doctor --dev reports missing GitHub CLI" {
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
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" && "${3:-}" == "doctor" ]]; then
    printf 'ok     bats-core                   Artifact '\''bats-core'\'' is installed via Homebrew package '\''bats-core'\''.\n'
    printf 'error  gh                          Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.\n'
    printf '       Fix: basectl setup --dev\n'
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
        "$BASE_REPO_ROOT/bin/basectl" doctor --dev

    [ "$status" -eq 1 ]
    [[ "$output" == *"error"*"gh"*"Artifact 'gh' is not installed via Homebrew package 'gh'."* ]]
    [[ "$output" == *"Fix: basectl setup --dev"* ]]
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

@test "basectl doctor --format json reports structured findings" {
    run --separate-stderr env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_SETUP_BREW_BIN="$TEST_TMPDIR/missing-brew" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/missing-xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"ok": false'* ]]
    [[ "$output" == *'"findings":'* ]]
    [[ "$output" == *'"status":"error","name":"homebrew","message":"Homebrew is not installed.","fix":"Run '\''basectl setup'\'' to install Homebrew, or install it manually from https://brew.sh/."'* ]]
    [[ "$output" == *'"status":"error","name":"xcode_command_line_tools"'* ]]
    [[ "$output" == *'"status":"error","name":"python"'* ]]
    [[ "$output" == *'"status":"error","name":"base_virtualenv"'* ]]
    [[ "$output" == *'"status":"error","name":"pyyaml"'* ]]
    [[ "$output" == *'"status":"error","name":"click"'* ]]
    [[ "$output" != *"Base doctor"* ]]
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
    printf '[{"status":"warn","name":"demo-artifact","message":"Optional project artifact is not installed.","fix":"basectl setup demo"}]\n'
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

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        OSTYPE="darwin24" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"ok": true'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_findings":'* ]]
    [[ "$output" == *'"status":"warn","name":"demo-artifact","message":"Optional project artifact is not installed.","fix":"basectl setup demo"'* ]]
    [[ "$output" != *"Running Python project doctor layer."* ]]
    [ "${stderr:-}" = "" ]
}
