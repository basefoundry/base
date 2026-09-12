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

    copy_base_cli_fixture "$base_home/../base-cli/lib/python"
    copy_base_bash_libs_fixture "$base_home/../base-bash-libs/lib/bash"

    case "$base_home" in
        */opt/base/libexec)
            homebrew_prefix="${base_home%/opt/base/libexec}"
            copy_base_bash_libs_fixture "$homebrew_prefix/opt/base-bash-libs/libexec/lib/bash"
            ;;
    esac
}

copy_base_cli_fixture() {
    local source_dir="${BASE_CLI_SOURCE_DIR:-}"
    local candidate target_dir="$1"

    if [[ -n "$source_dir" && -f "$source_dir/base_cli/__init__.py" ]]; then
        :
    else
        source_dir=""
        for candidate in \
            "$BASE_REPO_ROOT/../base-cli/lib/python" \
            "$BASE_REPO_ROOT/../../base-cli/lib/python"; do
            if [[ -f "$candidate/base_cli/__init__.py" ]]; then
                source_dir="$candidate"
                break
            fi
        done
    fi

    [[ -n "$source_dir" ]] || {
        printf 'Base integration tests require a base-cli source checkout.\n' >&2
        return 1
    }
    mkdir -p "$target_dir"
    cp -R "$source_dir/." "$target_dir/"
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
        BASE_CLI_SOURCE_DIR="$TEST_BASE_HOME/../base-cli/lib/python" \
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
        BASE_CLI_SOURCE_DIR="$TEST_BASE_HOME/../base-cli/lib/python" \
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

@test "fresh project setup preview completes without creating its runtime" {
    rm -rf "$TEST_PROJECT_ROOT/.venv"
    cat > "$TEST_PROJECT_ROOT/base_manifest.yaml" <<'YAML'
project:
  name: demo
test:
  command: 'true'
  requirements: requirements.txt
artifacts: []
YAML
    printf 'fixture==1.0\n' > "$TEST_PROJECT_ROOT/requirements.txt"

    run_basectl setup --dry-run --manifest "$TEST_PROJECT_ROOT/base_manifest.yaml"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would create project virtual environment at '$TEST_PROJECT_ROOT/.venv'"* ]]
    [[ "$output" == *"-r $TEST_PROJECT_ROOT/requirements.txt"* ]]
    [[ "$output" == *"Project 'demo' setup is complete."* ]]
    [ ! -e "$TEST_PROJECT_ROOT/.venv" ]
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

@test "basectl test rejects unsupported requirement extras before running tests" {
    cat > "$TEST_PROJECT_ROOT/base_manifest.yaml" <<'EOF'
project:
  name: demo
test:
  command: fake-test tests/
  requirements: requirements.txt
artifacts: []
EOF
    printf 'pip[feature]\n' > "$TEST_PROJECT_ROOT/requirements.txt"
    run_basectl trust allow demo
    [ "$status" -eq 0 ]

    run_basectl test demo

    [ "$status" -eq 1 ]
    [[ "$output" == *"unsupported requirement syntax 'pip[feature]'"* ]]
    [[ "$output" == *"direct package names"* ]]
    [ ! -e "$TEST_STATE_DIR/fake-test.out" ]
}


@test "public inspection keeps the project runtime unverified until explicitly requested" {
    local command
    cat > "$TEST_PROJECT_ROOT/base_manifest.yaml" <<'EOF'
project:
  name: demo
python: {}
test:
  command: fake-test tests/
  requirements: requirements.txt
artifacts: []
EOF
    printf 'pip\n' > "$TEST_PROJECT_ROOT/requirements.txt"
    cat > "$TEST_PROJECT_ROOT/.venv/bin/python" <<EOF
#!/usr/bin/env bash
printf probe >> "$TEST_STATE_DIR/project-runtime-probed"
exec "$TEST_INTEGRATION_PYTHON" "\$@"
EOF
    chmod +x "$TEST_PROJECT_ROOT/.venv/bin/python"
    for command in check doctor; do
        run_basectl "$command" --ci --manifest "$TEST_PROJECT_ROOT/base_manifest.yaml" --format json
        [ "$status" -eq 0 ]
        [[ "$output" == *"unverified"* ]]
        [ ! -e "$TEST_STATE_DIR/project-runtime-probed" ]
    done
    run_basectl test demo
    [ "$status" -eq 1 ]
    [ ! -e "$TEST_STATE_DIR/project-runtime-probed" ]
    [ ! -e "$TEST_STATE_DIR/fake-test.out" ]

    run_basectl check --ci --manifest "$TEST_PROJECT_ROOT/base_manifest.yaml" --verify-project-runtime --format json
    [ "$status" -eq 0 ]
    [ -e "$TEST_STATE_DIR/project-runtime-probed" ]
}

@test "inspection uses Base imports and runtime from an active project directory" {
    local module command
    local workspace="$TEST_TMPDIR/inspection-workspace"
    local workspace_manifest="$TEST_TMPDIR/inspection-workspace.yaml"
    mkdir -p "$workspace"
    mv "$TEST_PROJECT_ROOT" "$workspace/demo"
    TEST_PROJECT_ROOT="$workspace/demo"
    cat > "$TEST_PROJECT_ROOT/base_manifest.yaml" <<'EOF'
project:
  name: demo
python: {}
test:
  command: fake-test tests/
artifacts: []
EOF
    printf 'schema_version: 1\nworkspace:\n  name: demo\nrepos:\n  - name: demo\n' > "$workspace_manifest"
    for module in base_projects base_setup base_cli_adapters platform pip; do
        printf 'open("%s", "w").close()\nraise RuntimeError("unexpected project import")\n' \
            "$TEST_STATE_DIR/project-imported" > "$TEST_PROJECT_ROOT/$module.py"
    done
    cat > "$TEST_PROJECT_ROOT/.venv/bin/python" <<EOF
#!/usr/bin/env bash
printf probe >> "$TEST_STATE_DIR/project-runtime-probed"
exec "$TEST_INTEGRATION_PYTHON" "\$@"
EOF
    chmod +x "$TEST_PROJECT_ROOT/.venv/bin/python"
    export BASE_PROJECT=demo BASE_PROJECT_VENV_DIR="$TEST_PROJECT_ROOT/.venv"
    cd "$TEST_PROJECT_ROOT"

    run_basectl projects list --workspace "$workspace"
    [ "$status" -eq 0 ]
    for command in check doctor; do
        run_basectl "$command" --ci --manifest ./base_manifest.yaml --format json
        [ "$status" -eq 0 ]
        [[ "$output" == *"unverified"* ]]
    done
    for command in status check doctor onboarding; do
        run_basectl workspace "$command" --workspace "$workspace" --manifest "$workspace_manifest" --format json
        [ "$status" -eq 0 ]
        [[ "$output" == *"unverified"* || "$output" == *"needs_verification"* ]]
    done
    [ ! -e "$TEST_STATE_DIR/project-runtime-probed" ]
    [ ! -e "$TEST_STATE_DIR/project-imported" ]
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

@test "basectl workspace setup dry-run reports ordered setup plan" {
    local manifest_path="$TEST_TMPDIR/workspace.yaml"

    manifest_path="$(cd "$TEST_TMPDIR" && pwd -P)/workspace.yaml"
    cat > "$manifest_path" <<'EOF'
schema_version: 1
workspace:
  name: integration-suite
repos:
  - name: base
  - name: demo
  - name: missing
    required: false
EOF

    run_basectl workspace setup --workspace "$TEST_WORKSPACE" --manifest "$manifest_path" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"Workspace setup plan: $TEST_WORKSPACE (3 manifest repos)"* ]]
    [[ "$output" == *"SKIP repository 'base'"* ]]
    [[ "$output" == *"SETUP repository 'demo'"* ]]
    [[ "$output" == *"SKIP repository 'missing'"* ]]
    [[ "$output" == *"Workspace setup plan complete: setup=1 skipped=2 failed=0."* ]]
    [[ "$output" == *"[DRY-RUN] No repositories were modified."* ]]
}

@test "workspace test runs only the selected project beside a malformed sibling" {
    local workspace_manifest="$TEST_TMPDIR/test-workspace.yaml"
    cat > "$TEST_PROJECT_ROOT/base_manifest.yaml" <<'YAML'
project:
  name: demo
python: {}
test:
  command: fake-test tests/
  requirements: requirements.txt
artifacts: []
YAML
    printf 'pip\n' > "$TEST_PROJECT_ROOT/requirements.txt"
    run_basectl test demo
    [ "$status" -eq 1 ]
    [ ! -e "$TEST_STATE_DIR/fake-test.out" ]
    run_basectl trust allow demo
    [ "$status" -eq 0 ]
    mkdir -p "$TEST_WORKSPACE/bad"
    printf 'project:\n  name: bad\nunsupported: true\n' > "$TEST_WORKSPACE/bad/base_manifest.yaml"
    printf 'schema_version: 1\nworkspace:\n  name: tests\nrepos:\n  - name: bad\n  - name: demo\n' > "$workspace_manifest"

    run_basectl workspace test --workspace "$TEST_WORKSPACE" --manifest "$workspace_manifest" --projects demo --format json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"passed": 1'* ]]
    [ -e "$TEST_STATE_DIR/fake-test.out" ]
    grep -Fqx "pwd=$TEST_PROJECT_ROOT" "$TEST_STATE_DIR/fake-test.out"

    rm "$TEST_STATE_DIR/fake-test.out"
    run_basectl workspace test --workspace "$TEST_WORKSPACE" --manifest "$workspace_manifest" --format json
    [ "$status" -eq 1 ]
    [[ "$output" == *'"passed": 1'* ]]
    [[ "$output" == *'"failed": 1'* ]]
    [ -e "$TEST_STATE_DIR/fake-test.out" ]
    rm "$TEST_STATE_DIR/fake-test.out"

    mv "$TEST_PROJECT_ROOT/.venv" "$TEST_PROJECT_ROOT/.venv-hidden"
    run_basectl workspace test --workspace "$TEST_WORKSPACE" --manifest "$workspace_manifest" --projects demo --format json
    [ "$status" -eq 1 ]
    [[ "$output" == *'"failed": 1'* ]]
    [ ! -e "$TEST_STATE_DIR/fake-test.out" ]
    mv "$TEST_PROJECT_ROOT/.venv-hidden" "$TEST_PROJECT_ROOT/.venv"

    run_basectl workspace test --workspace "$TEST_WORKSPACE" --manifest "$workspace_manifest" --fail-fast --format json
    [ "$status" -eq 1 ]
    [[ "$output" == *'"failed": 1'* ]]
    [[ "$output" == *'"skipped": 1'* ]]
    [ ! -e "$TEST_STATE_DIR/fake-test.out" ]
}

@test "workspace test keeps same-name checkouts distinct and rejects duplicate aliases" {
    local workspace_manifest="$TEST_TMPDIR/test-workspace.yaml"
    run_basectl trust allow demo
    [ "$status" -eq 0 ]
    mkdir -p "$TEST_WORKSPACE/other"
    printf 'project:\n  name: demo\ntest:\n  command: touch wrong-checkout\nartifacts: []\n' \
        > "$TEST_WORKSPACE/other/base_manifest.yaml"
    printf 'schema_version: 1\nworkspace:\n  name: tests\nrepos:\n  - name: demo\n  - name: other\n' > "$workspace_manifest"

    run_basectl workspace test --workspace "$TEST_WORKSPACE" --manifest "$workspace_manifest" --projects demo --format json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"passed": 1'* ]]
    [ ! -e "$TEST_WORKSPACE/other/wrong-checkout" ]
    grep -Fqx "pwd=$TEST_PROJECT_ROOT" "$TEST_STATE_DIR/fake-test.out"

    rm "$TEST_STATE_DIR/fake-test.out"
    ln -s "$TEST_PROJECT_ROOT" "$TEST_WORKSPACE/alias"
    printf '  - name: alias\n' >> "$workspace_manifest"
    run_basectl workspace test --workspace "$TEST_WORKSPACE" --manifest "$workspace_manifest" --projects demo,alias --format json
    [ "$status" -eq 2 ]
    [[ "$output" == *"same manifest"* ]]
    [ ! -e "$TEST_STATE_DIR/fake-test.out" ]
}

@test "public listing and workspace status recover from malformed optional JSON" {
    local cache
    export BASE_CACHE_DIR="$TEST_TMPDIR/optional-cache"
    run_basectl projects list --workspace "$TEST_WORKSPACE"
    [ "$status" -eq 0 ]
    for cache in "$BASE_CACHE_DIR/base/cache/discovery/"*.json; do
        [ -f "$cache" ]
        printf '[]\n' > "$cache"
    done
    mkdir -p "$TEST_HOME/.base.d/demo/checks"
    printf '\377' > "$TEST_HOME/.base.d/demo/checks/last.json"

    run_basectl projects list --workspace "$TEST_WORKSPACE" --format json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"name": "demo"'* || "$output" == *'"name":"demo"'* ]]
    run_basectl workspace status --workspace "$TEST_WORKSPACE" --format json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"last_check": null'* ]]
    [[ "$output" != *"Traceback"* ]]
}

@test "saved check evidence follows the exact checkout and current manifest" {
    local mode root
    local first="$TEST_TMPDIR/first/shared"
    local second="$TEST_TMPDIR/second/shared"
    for root in "$first" "$second"; do
        mkdir -p "$root"
        printf 'project:\n  name: shared\nartifacts: []\n' > "$root/base_manifest.yaml"
    done
    for mode in text json; do
        run_basectl check --ci --manifest "$first/base_manifest.yaml" --format "$mode"
        [ "$status" -eq 0 ]
        run "$TEST_INTEGRATION_PYTHON" -c '
import hashlib, json, pathlib, sys
record = json.loads(pathlib.Path(sys.argv[1]).read_text())
root = pathlib.Path(sys.argv[2]).resolve()
manifest = root / "base_manifest.yaml"
assert record["schema_version"] == 2
assert record["identity"] == {"project_root": str(root), "manifest_path": str(manifest),
    "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()}
' "$TEST_HOME/.base.d/shared/checks/last.json" "$first"
        [ "$status" -eq 0 ]

        run_basectl workspace status --workspace "$TEST_TMPDIR/first" --format json
        [ "$status" -eq 0 ]
        [[ "$output" == *'"checked_at":'* ]]
        run_basectl workspace status --workspace "$TEST_TMPDIR/second" --format json
        [ "$status" -eq 0 ]
        [[ "$output" == *'"last_check": null'* ]]
    done
    printf '# Changed since the saved check.\n' >> "$first/base_manifest.yaml"
    run_basectl workspace status --workspace "$TEST_TMPDIR/first" --format json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"last_check": null'* ]]
}

@test "public diagnostics report invalid manifest encoding without a traceback" {
    local command
    printf 'project: \377\n' > "$TEST_PROJECT_ROOT/base_manifest.yaml"
    for command in check doctor; do
        run_basectl "$command" --manifest "$TEST_PROJECT_ROOT/base_manifest.yaml" --format json
        [ "$status" -eq 1 ]
        [[ "$output" == *"UTF-8"* ]]
        [[ "$output" != *"Traceback"* ]]
    done
    run_basectl workspace status --workspace "$TEST_WORKSPACE" --format json
    [ "$status" -eq 1 ]
    [[ "$output" == *'"manifest": "invalid"'* ]]
    [[ "$output" == *'"name": "base"'* ]]
    [[ "$output" != *"Traceback"* ]]
}

@test "onboarding trust guidance selects its explicit workspace from another directory" {
    local workspace="$TEST_TMPDIR/team workspace's checkout"
    local manifest="$TEST_TMPDIR/team workspace.yaml"
    local trust_command payload
    mkdir -p "$workspace/demo"
    cp "$TEST_PROJECT_ROOT/base_manifest.yaml" "$workspace/demo/base_manifest.yaml"
    printf 'schema_version: 1\nworkspace:\n  name: team\nrepos:\n  - name: demo\n' > "$manifest"
    cd "$TEST_PROJECT_ROOT"

    run_basectl workspace onboarding --workspace "$workspace" --manifest "$manifest" --format json
    [ "$status" -eq 0 ]
    payload="$output"
    trust_command="$(printf '%s' "$payload" | "$TEST_INTEGRATION_PYTHON" -c '
import json, sys
payload = json.load(sys.stdin)
command = payload["repositories"][0]["trust_command"]
assert command in [c for action in payload["next_actions"] for c in action["commands"]]
print(command)
')"
    [ -n "$trust_command" ]
    run_basectl workspace onboarding --workspace "$workspace" --manifest "$manifest"
    [ "$status" -eq 0 ]

    run env HOME="$TEST_HOME" PATH="$TEST_BASE_HOME/bin:$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_CLI_SOURCE_DIR="$TEST_BASE_HOME/../base-cli/lib/python" \
        bash -c "$trust_command"
    [ "$status" -eq 0 ]
    run_basectl trust status demo --workspace "$workspace"
    [ "$status" -eq 0 ]
    [[ "$output" == *$'demo\tallowed\t'* ]]
    run_basectl trust status demo --workspace "$TEST_WORKSPACE"
    [[ "$output" == *$'demo\tblocked\t'* ]]

    printf '\n# reviewed manifest changed\n' >> "$workspace/demo/base_manifest.yaml"
    run env HOME="$TEST_HOME" PATH="$TEST_BASE_HOME/bin:$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_CLI_SOURCE_DIR="$TEST_BASE_HOME/../base-cli/lib/python" \
        bash -c "$trust_command"
    [ "$status" -ne 0 ]
    [[ "$output" == *"SHA-256"* ]]
}
