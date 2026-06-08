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
            COMP_WORDS=(basectl build ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "build_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl run ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "run_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl check --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "check_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl check --profile ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "check_profiles=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl test demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "test_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl build demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "build_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl run demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "run_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl projects list --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "projects_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "workspace_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace status --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "workspace_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl onboard --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "onboard_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl onboard --profile ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "onboard_profiles=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl clean --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "clean_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl logs --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "logs_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "repo_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo init --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo_init_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo configure --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo_configure_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "gh_areas=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh worktree ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "gh_worktree_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh worktree prune --); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "gh_worktree_prune_options=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"complete -F _base_basectl_completion basectl"* ]]
    [[ "$output" == *"activate_projects=base demo"* ]]
    [[ "$output" == *"activate_options=--workspace --no-cd"* ]]
    [[ "$output" == *"check_projects=base demo"* ]]
    [[ "$output" == *"doctor_projects=base demo"* ]]
    [[ "$output" == *"test_projects=base demo"* ]]
    [[ "$output" == *"build_projects=base demo"* ]]
    [[ "$output" == *"run_projects=base demo"* ]]
    [[ "$output" == *"check_options=--profile --format"* ]]
    [[ "$output" == *"check_profiles=dev sre ai dev,sre dev,ai sre,ai dev,sre,ai"* ]]
    [[ "$output" == *"test_options=--workspace --dry-run"* ]]
    [[ "$output" == *"build_options=--workspace --dry-run --list"* ]]
    [[ "$output" == *"run_options=--workspace --dry-run --list"* ]]
    [[ "$output" == *"projects_options=--workspace --format"* ]]
    [[ "$output" == *"workspace_commands=status check doctor"* ]]
    [[ "$output" == *"workspace_options=--workspace --format"* ]]
    [[ "$output" == *"onboard_options=--profile --dry-run --yes --no-profile"* ]]
    [[ "$output" == *"onboard_profiles=dev sre ai dev,sre dev,ai sre,ai dev,sre,ai"* ]]
    [[ "$output" == *"clean_options=--older-than --keep-last --dry-run"* ]]
    [[ "$output" == *"logs_options=--command --limit --path --tail --open --lines"* ]]
    [[ "$output" == *"repo_commands=init check configure"* ]]
    [[ "$output" == *"repo_init_options=--path --repo --description --copyright-holder --private --public --no-configure --dry-run"* ]]
    [[ "$output" == *"repo_configure_options=--repo --dry-run"* ]]
    [[ "$output" == *"gh_areas=issue pr branch worktree todo"* ]]
    [[ "$output" == *"gh_worktree_commands=prune"* ]]
    [[ "$output" == *"gh_worktree_prune_options=--dry-run --yes"* ]]
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
