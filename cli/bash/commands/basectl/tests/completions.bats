#!/usr/bin/env bats

load ./setup_helpers.bash


@test "Base-managed Bash startup registers basectl completion and project names" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$base_python")"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "list" ]]; then
    printf 'base\t/Users/test/base\n'
    printf 'demo\t/Users/test/demo\n'
    exit 0
fi
printf 'unexpected completion python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$base_python"

    run_base_command update-profile
    [ "$status" -eq 0 ]

    run env -u BASE_HOME -u BASE_HOST -u BASE_OS \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$TEST_HOME/.bashrc" -i -c '\
            complete -p basectl; \
            COMP_WORDS=(basectl activate ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "activate_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl activate demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "activate_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl check ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "check_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl doctor ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "doctor_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl test ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "test_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl run ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "run_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl check --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "check_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl test demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "test_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl run demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "run_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl projects list --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "projects_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl onboard --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "onboard_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl clean --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "clean_options=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"complete -F _base_basectl_completion basectl"* ]]
    [[ "$output" == *"activate_projects=base demo"* ]]
    [[ "$output" == *"activate_options=--workspace --no-cd"* ]]
    [[ "$output" == *"check_projects=base demo"* ]]
    [[ "$output" == *"doctor_projects=base demo"* ]]
    [[ "$output" == *"test_projects=base demo"* ]]
    [[ "$output" == *"run_projects=base demo"* ]]
    [[ "$output" == *"check_options=--dev --format"* ]]
    [[ "$output" == *"test_options=--workspace --dry-run"* ]]
    [[ "$output" == *"run_options=--workspace --dry-run --list"* ]]
    [[ "$output" == *"projects_options=--workspace --format"* ]]
    [[ "$output" == *"onboard_options=--dev --dry-run --yes --no-profile"* ]]
    [[ "$output" == *"clean_options=--older-than --keep-last --dry-run"* ]]
}

@test "Bash completion includes setup notification options" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '\
            source "$BASE_HOME/lib/shell/completions/basectl_completion.sh"; \
            COMP_WORDS=(basectl setup --no); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "reply=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"--notify"* ]]
    [[ "$output" == *"--no-notify"* ]]
}

@test "Bash completion uses gh issue category options" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '\
            source "$BASE_HOME/lib/shell/completions/basectl_completion.sh"; \
            COMP_WORDS=(basectl gh issue create --); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "reply=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"--category"* ]]
    [[ "$output" == *"--title"* ]]
    [[ "$output" == *"--body"* ]]
    [[ "$output" != *"--type"* ]]
}
