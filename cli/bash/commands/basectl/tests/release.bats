#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl release prints help without requiring the Base Python venv" {
    run_basectl release --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl release check --version <version>"* ]]
    [[ "$output" == *"basectl release plan --version <version>"* ]]
    [[ "$output" == *"basectl release notes --version <version>"* ]]
}

@test "basectl release delegates to the Python release layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local manifest="$TEST_TMPDIR/base_manifest.yaml"

    mkdir -p "$(dirname "$python_bin")"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$manifest"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_release" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT" > "${BASE_TEST_RELEASE_STATE:?}"
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected release python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_RELEASE_STATE="$TEST_TMPDIR/release-state" \
        "$BASE_REPO_ROOT/bin/basectl" release plan --version 1.2.3 --manifest "$manifest"

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=plan --version 1.2.3 --manifest $manifest" ]
    [ "$(cat "$TEST_TMPDIR/release-state")" = "BASE_PROJECT=base" ]
}
