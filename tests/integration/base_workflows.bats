#!/usr/bin/env bats

load ../test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_WORKSPACE="$TEST_HOME/work"
    TEST_STATE_DIR="$TEST_TMPDIR/state"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_XCODE_DIR="$TEST_TMPDIR/CommandLineTools"
    TEST_INTEGRATION_PYTHON="${BASE_INTEGRATION_PYTHON:-$HOME/.base.d/base/.venv/bin/python}"

    [[ -x "$TEST_INTEGRATION_PYTHON" ]] || skip "set BASE_INTEGRATION_PYTHON to a Python with Base test dependencies"

    mkdir -p "$TEST_HOME" "$TEST_WORKSPACE" "$TEST_STATE_DIR" "$TEST_MOCKBIN" "$TEST_XCODE_DIR"
    TEST_HOME="$(cd "$TEST_HOME" && pwd -P)"
    TEST_WORKSPACE="$(cd "$TEST_WORKSPACE" && pwd -P)"
    TEST_STATE_DIR="$(cd "$TEST_STATE_DIR" && pwd -P)"
    TEST_MOCKBIN="$(cd "$TEST_MOCKBIN" && pwd -P)"
    TEST_XCODE_DIR="$(cd "$TEST_XCODE_DIR" && pwd -P)"
    TEST_BASE_HOME="$TEST_WORKSPACE/base"
    TEST_PROJECT_ROOT="$TEST_WORKSPACE/demo"

    mkdir -p "$TEST_XCODE_DIR/usr/bin"
    touch "$TEST_XCODE_DIR/usr/bin/clang"

    create_base_runtime "$TEST_BASE_HOME"
    create_fake_platform_tools
    create_python_venv "$TEST_HOME/.base.d/base/.venv"
    create_demo_project "$TEST_PROJECT_ROOT"
    create_python_venv "$TEST_PROJECT_ROOT/.venv"
    create_fake_project_test_command "$TEST_PROJECT_ROOT/.venv/bin/fake-test"
}

create_base_runtime() {
    local base_home="$1"
    local homebrew_prefix

    mkdir -p "$base_home"
    cp -R "$BASE_REPO_ROOT/bin" "$base_home/bin"
    cp -R "$BASE_REPO_ROOT/cli" "$base_home/cli"
    cp -R "$BASE_REPO_ROOT/lib" "$base_home/lib"
    cp -R "$BASE_REPO_ROOT/templates" "$base_home/templates"
    cp "$BASE_REPO_ROOT/base_init.sh" "$base_home/base_init.sh"
    cp "$BASE_REPO_ROOT/base_manifest.yaml" "$base_home/base_manifest.yaml"
    cp "$BASE_REPO_ROOT/VERSION" "$base_home/VERSION"

    copy_base_bash_libs_fixture "$base_home/../base-bash-libs/lib/bash"

    case "$base_home" in
        */opt/base/libexec)
            homebrew_prefix="${base_home%/opt/base/libexec}"
            copy_base_bash_libs_fixture "$homebrew_prefix/opt/base-bash-libs/libexec/lib/bash"
            ;;
    esac
}

create_fake_platform_tools() {
    cat > "$TEST_MOCKBIN/uname" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
    ""|-s)
        printf 'Darwin\n'
        exit 0
        ;;
esac

if [[ -x /usr/bin/uname ]]; then
    exec /usr/bin/uname "$@"
fi
exec /bin/uname "$@"
EOF
    chmod +x "$TEST_MOCKBIN/uname"

    cat > "$TEST_MOCKBIN/brew" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
    --prefix)
        printf '%s\n' "${BASE_INTEGRATION_BREW_PREFIX:?}"
        exit 0
        ;;
    list)
        case "${2:-}" in
            python@3.13) exit 0 ;;
        esac
        exit 1
        ;;
    bundle)
        [[ "${2:-}" == "check" ]] && exit 0
        ;;
esac
printf 'unexpected brew args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/brew"

    cat > "$TEST_MOCKBIN/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR:?}"
    exit 0
fi
printf 'unexpected xcode-select args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/xcode-select"
}

create_python_venv() {
    local venv_dir="$1"

    mkdir -p "$venv_dir/bin"
    cat > "$venv_dir/bin/python" <<EOF
#!/usr/bin/env bash
exec "$TEST_INTEGRATION_PYTHON" "\$@"
EOF
    chmod +x "$venv_dir/bin/python"
    printf 'python-home = integration-test\n' > "$venv_dir/pyvenv.cfg"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"
}

create_demo_project() {
    local project_root="$1"

    mkdir -p "$project_root"
    cat > "$project_root/base_manifest.yaml" <<'EOF'
project:
  name: demo
test:
  command: fake-test tests/
artifacts: []
EOF
}

create_fake_project_test_command() {
    local command_path="$1"

    cat > "$command_path" <<'EOF'
#!/usr/bin/env bash
{
    printf 'project=%s\n' "${BASE_PROJECT:-}"
    printf 'root=%s\n' "${BASE_PROJECT_ROOT:-}"
    printf 'manifest=%s\n' "${BASE_PROJECT_MANIFEST:-}"
    printf 'venv=%s\n' "${BASE_PROJECT_VENV_DIR:-}"
    printf 'pwd=%s\n' "$PWD"
    printf 'args='
    printf '<%s>' "$@"
    printf '\n'
} > "${BASE_INTEGRATION_STATE_DIR:?}/fake-test.out"
EOF
    chmod +x "$command_path"
}

run_basectl() {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE=darwin24 \
        BASE_TEST_MODE=true \
        BASE_INTEGRATION_BREW_PREFIX="$TEST_TMPDIR/homebrew-prefix" \
        BASE_INTEGRATION_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_NOTIFY=false \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_XCODE_DIR" \
        PIP_DISABLE_PIP_VERSION_CHECK=1 \
        "$TEST_BASE_HOME/bin/basectl" "$@"
}

run_basectl_separate_stderr() {
    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE=darwin24 \
        BASE_TEST_MODE=true \
        BASE_INTEGRATION_BREW_PREFIX="$TEST_TMPDIR/homebrew-prefix" \
        BASE_INTEGRATION_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_NOTIFY=false \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_XCODE_DIR" \
        PIP_DISABLE_PIP_VERSION_CHECK=1 \
        "$TEST_BASE_HOME/bin/basectl" "$@"
}

@test "basectl resolves version and discovers sibling workspace projects" {
    local expected_version

    expected_version="$(cat "$BASE_REPO_ROOT/VERSION")"

    run_basectl --version
    [ "$status" -eq 0 ]
    [ "$output" = "basectl $expected_version" ]

    run_basectl projects list
    [ "$status" -eq 0 ]
    [[ "$output" == *$'base\t'"$TEST_BASE_HOME"* ]]
    [[ "$output" == *$'demo\t'"$TEST_PROJECT_ROOT"* ]]
}

@test "basectl setup, check, and doctor run against an isolated project" {
    run_basectl setup demo
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved project 'demo' at '$TEST_PROJECT_ROOT'."* ]]
    [[ "$output" == *"Project 'demo' setup is complete."* ]]
    [[ "$output" == *"Base CLI setup is complete."* ]]

    run_basectl check demo
    [ "$status" -eq 0 ]
    [[ "$output" == *"Base CLI environment and project 'demo' check passed."* ]]

    run_basectl doctor demo
    [ "$status" -eq 0 ]
    [[ "$output" != *"Base doctor for project 'demo'"* ]]
    [[ "$output" != *"Project doctor: demo"* ]]
    [[ "$output" == *"Base doctor found no blocking issues for project 'demo'."* ]]
}

@test "basectl check and doctor emit structured project JSON" {
    run_basectl_separate_stderr check demo --format json
    [ "$status" -eq 0 ]
    [ "${stderr:-}" = "" ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "ok"'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
    [[ "$output" != *'"ok":'* ]]
    [[ "$output" == *'"name":"click"'* || "$output" == *'"name": "click"'* ]]

    run_basectl_separate_stderr doctor demo --format json
    [ "$status" -eq 0 ]
    [ "${stderr:-}" = "" ]
    [[ "$output" == *'"schema_version": 1'* ]]
    [[ "$output" == *'"status": "ok"'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_findings":'* ]]
    [[ "$output" != *'"ok":'* ]]
}

@test "basectl test delegates from the project root with project environment" {
    run_basectl trust allow demo
    [ "$status" -eq 0 ]
    [[ "$output" == *"Allowed manifest commands for project 'demo'."* ]]

    run_basectl test demo -- -k "focused case"
    [ "$status" -eq 0 ]

    grep -Fqx "project=demo" "$TEST_STATE_DIR/fake-test.out"
    grep -Fqx "root=$TEST_PROJECT_ROOT" "$TEST_STATE_DIR/fake-test.out"
    grep -Fqx "manifest=$TEST_PROJECT_ROOT/base_manifest.yaml" "$TEST_STATE_DIR/fake-test.out"
    grep -Fqx "venv=$TEST_PROJECT_ROOT/.venv" "$TEST_STATE_DIR/fake-test.out"
    grep -Fqx "pwd=$TEST_PROJECT_ROOT" "$TEST_STATE_DIR/fake-test.out"
    grep -Fqx "args=<tests/><-k><focused case>" "$TEST_STATE_DIR/fake-test.out"
}

@test "basectl update-profile dry-run does not write real shell startup files" {
    run_basectl update-profile --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would update '$TEST_HOME/.base.d/profile.conf'."* ]]
    [[ "$output" == *"[DRY-RUN] Would update '$TEST_HOME/.bashrc' with section 'bashrc'."* ]]

    [ ! -e "$TEST_HOME/.base.d/profile.conf" ]
    [ ! -e "$TEST_HOME/.bashrc" ]
    [ ! -e "$TEST_HOME/.zshrc" ]
}

@test "brew-like Base homes can discover projects through explicit workspace override" {
    local brew_base_home="$TEST_TMPDIR/homebrew/opt/base/libexec"

    create_base_runtime "$brew_base_home"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_INTEGRATION_BREW_PREFIX="$TEST_TMPDIR/homebrew-prefix" \
        "$brew_base_home/bin/basectl" projects list --workspace "$TEST_WORKSPACE"

    [ "$status" -eq 0 ]
    [[ "$output" == *$'base\t'"$TEST_BASE_HOME"* ]]
    [[ "$output" == *$'demo\t'"$TEST_PROJECT_ROOT"* ]]
}

@test "basectl workspace configure dry-run follows manifest without mutating missing repositories" {
    local manifest_path="$TEST_TMPDIR/workspace.yaml"

    manifest_path="$(cd "$TEST_TMPDIR" && pwd -P)/workspace.yaml"
    cat > "$manifest_path" <<'EOF'
schema_version: 1
workspace:
  name: integration-suite
repos:
  - name: demo
    url: git@github.com:basefoundry/demo.git
  - name: missing
    url: git@github.com:basefoundry/missing.git
EOF

    run_basectl workspace configure --workspace "$TEST_WORKSPACE" --manifest "$manifest_path" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"Workspace configure: $TEST_WORKSPACE (2 manifest repos)"* ]]
    [[ "$output" == *"Workspace manifest: $manifest_path (integration-suite)"* ]]
    [[ "$output" == *"CONFIGURE repository 'demo' at '$TEST_PROJECT_ROOT' for 'basefoundry/demo'."* ]]
    [[ "$output" == *"SKIP repository 'missing' is missing at '$TEST_WORKSPACE/missing'."* ]]
    [[ "$output" == *"[DRY-RUN] No repositories were modified."* ]]
    [[ "$output" == *"Workspace configure completed: configured=1 skipped=1 failed=0."* ]]
}
