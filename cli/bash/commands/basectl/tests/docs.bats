#!/usr/bin/env bats

load ./basectl_helpers.bash


readonly BASE_DOCS_URL="https://github.com/basefoundry/base#readme"


@test "basectl docs prints help without requiring the Base Python venv" {
    run_basectl docs --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl docs [options]"* ]]
    [[ "$output" == *"--show-url"* ]]
    [[ "$output" == *"Open the Base documentation home page on GitHub."* ]]
}

@test "basectl docs opens the GitHub README in the platform browser" {
    local state_file="$TEST_TMPDIR/docs-open-state"

    cat > "$TEST_MOCKBIN/open" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_TEST_DOCS_OPEN_STATE:?}"
EOF
    chmod +x "$TEST_MOCKBIN/open"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_DOCS_OPEN_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" docs

    [ "$status" -eq 0 ]
    [ "$(cat "$state_file")" = "$BASE_DOCS_URL" ]
}

@test "basectl docs --show-url prints the GitHub README URL without opening a browser" {
    local state_file="$TEST_TMPDIR/docs-open-state"

    cat > "$TEST_MOCKBIN/open" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_TEST_DOCS_OPEN_STATE:?}"
EOF
    chmod +x "$TEST_MOCKBIN/open"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_DOCS_OPEN_STATE="$state_file" \
        "$BASE_REPO_ROOT/bin/basectl" docs --show-url

    [ "$status" -eq 0 ]
    [ "$output" = "$BASE_DOCS_URL" ]
    [ ! -e "$state_file" ]
}

@test "basectl docs reports invalid arguments as usage errors" {
    run_basectl docs extra

    [ "$status" -eq 2 ]
    [[ "$output" == *"basectl docs [options]"* ]]
    [[ "$output" == *"The 'docs' command does not accept positional arguments."* ]]

    run_basectl docs --unknown

    [ "$status" -eq 2 ]
    [[ "$output" == *"basectl docs [options]"* ]]
    [[ "$output" == *"Unknown docs option '--unknown'."* ]]
}
