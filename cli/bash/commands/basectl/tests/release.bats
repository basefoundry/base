#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl release prints help without requiring the Base Python venv" {
    run_basectl release --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl release check --version <version>"* ]]
    [[ "$output" == *"basectl release plan --version <version>"* ]]
    [[ "$output" == *"basectl release notes --version <version>"* ]]
    [[ "$output" == *"basectl release publish --version <version>"* ]]
    [[ "$output" == *"Subcommands:"* ]]
    [[ "$output" == *"check    Verify release readiness"* ]]
    [[ "$output" == *"plan     Show the release plan"* ]]
    [[ "$output" == *"notes    Print the changelog notes"* ]]
    [[ "$output" == *"publish  Tag the release and create the GitHub Release"* ]]
    [[ "$output" == *"Typical order: check -> plan -> notes -> publish."* ]]
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
        "$BASE_REPO_ROOT/bin/basectl" release publish --dry-run --version 1.2.3 --manifest "$manifest"

    [ "$status" -eq 0 ]
    [ "$output" = "ARGS=publish --dry-run --version 1.2.3 --manifest $manifest" ]
    [ "$(cat "$TEST_TMPDIR/release-state")" = "BASE_PROJECT=base" ]
}

@test "Bash completion includes release publish commands and options" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '\
            source "$BASE_HOME/lib/shell/completions/basectl_completion.sh"; \
            COMP_WORDS=(basectl release ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "release_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl release publish --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "release_publish_options=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"release_commands=check plan notes publish"* ]]
    [[ "$output" == *"release_publish_options=--version --manifest --dry-run --yes"* ]]
}
