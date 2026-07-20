#!/usr/bin/env bats

load ./basectl_helpers.bash


write_manifest_trust_python() {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_trust" && "${3:-}" == "require" && "${4:-}" == "demo" ]]; then
    if [[ "${BASE_TEST_TRUST_ALLOWED:-0}" == "1" ]]; then
        exit 0
    fi
    cat >&2 <<TRUST
ERROR: Manifest-declared commands are not allowed for project 'demo' on this machine.
Project root: ${BASE_TEST_PROJECT_ROOT:?}
Manifest: ${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml
Manifest SHA-256: 0123456789abcdef
Origin: https://github.com/example/demo.git

Review first:
  basectl run demo --list
  basectl build demo --list
  basectl test demo --dry-run

Allow after review:
  basectl trust allow demo --manifest-sha256 0123456789abcdef
TRUST
    exit 1
fi

if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" ]]; then
    case "${3:-}" in
        test-command)
            base_test_protocol_project_command demo "${BASE_TEST_PROJECT_ROOT:?}" \
                "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false true \
                'touch "$BASE_TEST_TRUST_STATE"; exit 7' ""
            exit 0
            ;;
        run-command)
            base_test_protocol_project_command demo "${BASE_TEST_PROJECT_ROOT:?}" \
                "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false true \
                'touch "$BASE_TEST_TRUST_STATE"; exit 7' ""
            exit 0
            ;;
        run-commands)
            base_test_protocol_begin named-command 1
            base_test_protocol_named_command_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
                "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" dev \
                'touch "$BASE_TEST_TRUST_STATE"; exit 7' ""
            base_test_protocol_end
            exit 0
            ;;
        build-targets)
            base_test_protocol_begin build-target 1
            base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
                "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false true api \
                "${BASE_TEST_PROJECT_ROOT:?}" 'touch "$BASE_TEST_TRUST_STATE"; exit 7' 'Build API' ""
            base_test_protocol_end
            exit 0
            ;;
        build-target-list)
            base_test_protocol_begin build-target 1
            base_test_protocol_build_target_record 0 demo "${BASE_TEST_PROJECT_ROOT:?}" \
                "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false false api \
                "${BASE_TEST_PROJECT_ROOT:?}" 'touch "$BASE_TEST_TRUST_STATE"; exit 7' 'Build API' ""
            base_test_protocol_end
            exit 0
            ;;
        demo-script)
            base_test_protocol_demo demo "${BASE_TEST_PROJECT_ROOT:?}" \
                "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false true \
                "${BASE_TEST_PROJECT_ROOT:?}/demo.sh" ""
            exit 0
            ;;
        resolve)
            base_test_protocol_project_route demo "${BASE_TEST_PROJECT_ROOT:?}" \
                "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml" "${BASE_TEST_PROJECT_ROOT:?}/.venv" false true
            exit 0
            ;;
    esac
fi

printf 'unexpected trust test python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
}

setup_manifest_trust_project() {
    local project_root="$1"
    mkdir -p "$project_root/.venv/bin"
    printf '#!/usr/bin/env bash\n' > "$project_root/.venv/bin/python"
    chmod +x "$project_root/.venv/bin/python"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$project_root/base_manifest.yaml"
    cat > "$project_root/demo.sh" <<'EOF'
#!/usr/bin/env bash
touch "$BASE_TEST_TRUST_STATE"
exit 7
EOF
    chmod +x "$project_root/demo.sh"
    write_manifest_trust_python
}

assert_untrusted_block() {
    [ "$status" -eq 1 ]
    [[ "$output" == *"Manifest-declared commands are not allowed for project 'demo'"* ]]
    [[ "$output" == *"Review first:"* ]]
    [[ "$output" == *"basectl run demo --list"* ]]
    [[ "$output" == *"basectl trust allow demo --manifest-sha256 0123456789abcdef"* ]]
}

@test "manifest command trust blocks basectl test before project command execution" {
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/trust-state"
    setup_manifest_trust_project "$workspace/demo"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" test demo

    assert_untrusted_block
    [ ! -e "$state_file" ]
}

@test "manifest command trust blocks basectl run before project command execution" {
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/trust-state"
    setup_manifest_trust_project "$workspace/demo"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" run demo dev

    assert_untrusted_block
    [ ! -e "$state_file" ]
}

@test "manifest command trust blocks basectl build before project command execution" {
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/trust-state"
    setup_manifest_trust_project "$workspace/demo"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" build demo

    assert_untrusted_block
    [ ! -e "$state_file" ]
}

@test "manifest command trust blocks basectl demo before project script execution" {
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/trust-state"
    setup_manifest_trust_project "$workspace/demo"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" demo demo

    assert_untrusted_block
    [ ! -e "$state_file" ]
}

@test "manifest command trust blocks basectl activate before project activation sources can run" {
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/trust-state"
    local fake_bash="$TEST_TMPDIR/fake-bash"
    setup_manifest_trust_project "$workspace/demo"
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
touch "$BASE_TEST_TRUST_STATE"
EOF
    chmod +x "$fake_bash"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    assert_untrusted_block
    [ ! -e "$state_file" ]
}

@test "manifest command trust preserves dry-run and list inspection paths before approval" {
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/trust-state"
    setup_manifest_trust_project "$workspace/demo"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" test demo --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run tests for project demo"* ]]

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" run demo --list
    [ "$status" -eq 0 ]
    [[ "$output" == *$'demo\tdev\ttouch "$BASE_TEST_TRUST_STATE"; exit 7\t'* ]]

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" build demo --list
    [ "$status" -eq 0 ]
    [[ "$output" == *$'demo\tapi\t'* ]]

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" demo demo --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run demo for project demo"* ]]
    [ ! -e "$state_file" ]
}

@test "manifest command trust allows execution when require succeeds" {
    local workspace="$TEST_TMPDIR/workspace"
    local state_file="$TEST_TMPDIR/trust-state"
    setup_manifest_trust_project "$workspace/demo"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_TRUST_ALLOWED=1 \
        BASE_TEST_TRUST_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" run demo dev

    [ "$status" -eq 7 ]
    [ -e "$state_file" ]
}
