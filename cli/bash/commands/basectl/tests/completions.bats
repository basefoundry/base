#!/usr/bin/env bats

load ./setup_helpers.bash


@test "Base-managed Bash startup registers basectl completion and project names" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$base_python")"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "list" ]]; then
    base_test_protocol_begin project-list-entry 2
    base_test_protocol_project_list_record 0 base /Users/test/base
    base_test_protocol_project_list_record 1 demo /Users/test/demo
    base_test_protocol_end
    exit 0
fi
printf 'unexpected completion python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$base_python"

    run_base_command update-profile
    [ "$status" -eq 0 ]

    run env -u BASE_HOME -u BASE_HOST -u BASE_HOST_ENV -u BASE_OS -u BASE_PLATFORM \
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
            COMP_WORDS=(basectl doctor explain --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "doctor_explain_options=%s\n" "${COMPREPLY[*]}"; \
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
            COMP_WORDS=(basectl export-context ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "export_context_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl update ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "update_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl check --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "check_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl update --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "update_options=%s\n" "${COMPREPLY[*]}"; \
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
            COMP_WORDS=(basectl export-context demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "export_context_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl devcontainer ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "devcontainer_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl devcontainer demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "devcontainer_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl devenv-report ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "devenv_report_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl devenv-report demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "devenv_report_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl projects list --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "projects_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl trust ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "trust_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl trust status ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "trust_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl trust status demo --); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "trust_status_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl trust allow demo --); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "trust_allow_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl trust revoke demo --); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "trust_revoke_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "workspace_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace status --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "workspace_status_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace agent-brief --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "workspace_agent_brief_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace clone --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "workspace_clone_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace pull --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "workspace_pull_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace init --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "workspace_init_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace configure --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "workspace_configure_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl onboard --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "onboard_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl onboard ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "onboard_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl onboard --profile ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "onboard_profiles=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl prompt ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "prompt_names=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl prompt product-self-review --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "prompt_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl docs --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "docs_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl clean --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "clean_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl logs --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "logs_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl logs last --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "logs_last_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl logs l); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "logs_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl history --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "history_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "repo_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo init --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo_init_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo clone --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo_clone_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo check --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo_check_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo configure --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo_configure_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo agent-guidance --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo_agent_guidance_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl repo installer-template --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo_installer_template_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "ci_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci setup ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci_setup_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci setup --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci_setup_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci check ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci_check_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci check --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci_check_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci doctor ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci_doctor_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci doctor --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci_doctor_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "gh_areas=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh project ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "gh_project_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh project configure --); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "gh_project_configure_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh project issue set-fields 604 --); \
            COMP_CWORD=6; \
            _base_basectl_completion; \
            printf "gh_project_issue_set_fields_options=%s\n" "${COMPREPLY[*]}"; \
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
    [[ "$output" == *"doctor_projects=base demo explain"* ]]
    [[ "$output" == *"doctor_explain_options=--format"* ]]
    [[ "$output" == *"test_projects=base demo"* ]]
    [[ "$output" == *"build_projects=base demo"* ]]
    [[ "$output" == *"run_projects=base demo"* ]]
    [[ "$output" == *"export_context_projects=base demo"* ]]
    [[ "$output" == *"update_projects=base demo"* ]]
    [[ "$output" == *"check_options=--ci --profile --format --manifest --remote-network"* ]]
    [[ "$output" == *"update_options=--dry-run"* ]]
    [[ "$output" == *"check_profiles=dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab"* ]]
    [[ "$output" == *"test_options=--workspace --project --dry-run"* ]]
    [[ "$output" == *"build_options=--workspace --project --dry-run --list --format"* ]]
    [[ "$output" == *"run_options=--workspace --project --dry-run --list --format"* ]]
    [[ "$output" == *"export_context_options=--workspace --format --output --print --list-files"* ]]
    [[ "$output" == *"devcontainer_projects=base demo"* ]]
    [[ "$output" == *"devcontainer_options=--workspace --format --write"* ]]
    [[ "$output" == *"devenv_report_projects=base demo"* ]]
    [[ "$output" == *"devenv_report_options=--workspace --format"* ]]
    [[ "$output" == *"projects_options=--workspace --format"* ]]
    [[ "$output" == *"workspace_commands=status check doctor onboarding agent-brief clone pull init configure"* ]]
    [[ "$output" == *"workspace_status_options=--workspace --manifest --format"* ]]
    [[ "$output" == *"workspace_agent_brief_options=--workspace --manifest --format"* ]]
    [[ "$output" == *"workspace_clone_options=--workspace --manifest --include-optional --dry-run"* ]]
    [[ "$output" == *"workspace_pull_options=--source --manifest --dry-run"* ]]
    [[ "$output" == *"workspace_init_options=--owner --path --workspace --manifest --include-optional --dry-run"* ]]
    [[ "$output" == *"workspace_configure_options=--workspace --manifest --dry-run"* ]]
    [[ "$output" == *"onboard_options=--profile --dry-run --yes --no-profile"* ]]
    [[ "$output" == *"onboard_projects=base demo"* ]]
    [[ "$output" == *"onboard_profiles=dev sre ai linux-lab dev,sre dev,ai dev,linux-lab sre,ai sre,linux-lab ai,linux-lab dev,sre,ai dev,sre,linux-lab dev,ai,linux-lab sre,ai,linux-lab dev,sre,ai,linux-lab"* ]]
    [[ "$output" == *"prompt_names=list product-self-review"* ]]
    [[ "$output" == *"prompt_options=--output --help"* ]]
    [[ "$output" == *"docs_options=--show-url"* ]]
    [[ "$output" == *"clean_options=--older-than --keep-last --dry-run"* ]]
    [[ "$output" == *"logs_options=--command --limit --path --tail --open --lines"* ]]
    [[ "$output" == *"logs_last_options=--command --lines --format"* ]]
    [[ "$output" == *"logs_commands=last"* ]]
    [[ "$output" == *"history_options=--project --command --status --limit --format --report --include-internal"* ]]
    [[ "$output" == *"trust_commands=status allow revoke"* ]]
    [[ "$output" == *"trust_projects=base demo"* ]]
    [[ "$output" == *"trust_status_options=--workspace --format"* ]]
    [[ "$output" == *"trust_allow_options=--workspace --manifest-sha256"* ]]
    [[ "$output" == *"trust_revoke_options=--workspace"* ]]
    [[ "$output" == *"repo_commands=init clone check configure agent-guidance installer-template"* ]]
    [[ "$output" == *"repo_init_options=--path --repo --issue --category --pr --agent-ready --release --language --description --copyright-holder --private --public --no-configure --no-protect-default-branch --project --project-owner --project-schema --initiative-option --copy-project-fields-from --no-project --dry-run"* ]]
    [[ "$output" == *"repo_clone_options=--owner --path --dry-run"* ]]
    [[ "$output" == *"repo_check_options=--agent-guidance --agent-ready --release"* ]]
    [[ "$output" == *"repo_configure_options=--repo --no-protect-default-branch --project --project-owner --project-schema --initiative-option --copy-project-fields-from --replace-project --no-project --release --dry-run"* ]]
    [[ "$output" == *"repo_agent_guidance_options=--repo --issue --category --repo-name --default-branch --validation-command --pr --dry-run"* ]]
    [[ "$output" == *"repo_installer_template_options=--print --stdout --repo --issue --category --pr --dry-run"* ]]
    [[ "$output" == *"ci_commands=setup check doctor"* ]]
    [[ "$output" == *"ci_setup_projects=base demo"* ]]
    [[ "$output" == *"ci_setup_options=--ci --format --profile --dry-run --manifest --notify --no-notify --recreate-venv --yes"* ]]
    [[ "$output" == *"ci_check_projects=base demo"* ]]
    [[ "$output" == *"ci_check_options=--ci --profile --format --manifest --remote-network"* ]]
    [[ "$output" == *"ci_doctor_projects=base demo"* ]]
    [[ "$output" == *"ci_doctor_options=--ci --profile --format --manifest --remote-network --no-color"* ]]
    [[ "$output" == *"gh_areas=issue pr branch worktree project"* ]]
    [[ "$output" == *"gh_project_commands=doctor configure issue"* ]]
    [[ "$output" == *"gh_project_configure_options=--project --owner --schema --config --copy-fields-from --initiative-option --repo --replace-project --dry-run"* ]]
    [[ "$output" == *"gh_project_issue_set_fields_options=--repo --project --owner --config --status --priority --area --initiative --size --dry-run"* ]]
    [[ "$output" == *"gh_worktree_commands=prune"* ]]
    [[ "$output" == *"gh_worktree_prune_options=--dry-run --yes"* ]]
}

@test "Zsh repo pull request helper completions include issue and category options" {
    local agent_block
    local completion="$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"
    local init_block
    local installer_block

    init_block="$(sed -n '/^                init)$/,/^                clone)$/p' "$completion")"
    agent_block="$(sed -n '/^                agent-guidance)$/,/^                installer-template)$/p' "$completion")"
    installer_block="$(sed -n '/^                installer-template)$/,/^                \*)/p' "$completion")"

    [[ "$init_block" == *"--issue[Issue number for pull request]"* ]]
    [[ "$init_block" == *"--category[Issue category for pull request dry-run]"* ]]
    [[ "$agent_block" == *"--issue[Issue number for pull request]"* ]]
    [[ "$agent_block" == *"--category[Issue category for pull request dry-run]"* ]]
    [[ "$installer_block" == *"--issue[Issue number for pull request]"* ]]
    [[ "$installer_block" == *"--category[Issue category for pull request dry-run]"* ]]
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
            printf "create_reply=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh issue ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "issue_commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh issue readiness 123 --); \
            COMP_CWORD=5; \
            _base_basectl_completion; \
            printf "readiness_reply=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh issue start 123 -); \
            COMP_CWORD=5; \
            _base_basectl_completion; \
            printf "start_reply=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"--category"* ]]
    [[ "$output" == *"--title"* ]]
    [[ "$output" == *"--body"* ]]
    [[ "$output" == *"--assignee"* ]]
    [[ "$output" == *"--no-assignee"* ]]
    [[ "$output" == *"--size"* ]]
    [[ "$output" == *"issue_commands=list create start readiness"* ]]
    [[ "$output" == *"readiness_reply=--repo --project-owner --project-number --format"* ]]
    [[ "$output" == *"start_reply=--category --title --repo -R"* ]]
    [[ "$output" != *"--type"* ]]
}

@test "Bash completion includes inspection JSON format options" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '\
            source "$BASE_HOME/lib/shell/completions/basectl_completion.sh"; \
            COMP_WORDS=(basectl repo check --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "repo=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl release check --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "release=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl gh branch stale --); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "branch=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"repo="*"--format"* ]]
    [[ "$output" == *"release="*"--format"* ]]
    [[ "$output" == *"branch="*"--format"* ]]
}

@test "Bash completion includes workspace configure options" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '\
            source "$BASE_HOME/lib/shell/completions/basectl_completion.sh"; \
            COMP_WORDS=(basectl workspace ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "commands=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl workspace configure ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "options=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"commands=status check doctor onboarding agent-brief clone pull init configure"* ]]
    [[ "$output" == *"options=--workspace --manifest --dry-run"* ]]
}
