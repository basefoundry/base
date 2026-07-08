#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl prints help with --help" {
    run_basectl --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
    [[ "$output" == *"activate <project> [options]"* ]]
    [[ "$output" == *"setup [options] [project]"* ]]
    [[ "$output" == *"check [project] [options]"* ]]
    [[ "$output" == *"test [project] [options]"* ]]
    [[ "$output" == *"export-context [project] [options]"* ]]
    [[ "$output" == *"devcontainer [project] [options]"* ]]
    [[ "$output" == *"devenv-report [project] [options]"* ]]
    [[ "$output" == *"run <project> <command> [options]"* ]]
    [[ "$output" == *"repo <init|clone|check|configure|agent-guidance|installer-template> [options]"* ]]
    [[ "$output" == *"ci <setup|check|doctor> <project> [options]"* ]]
    [[ "$output" == *"release <check|plan|notes|publish> --version <version> [options]"* ]]
    [[ "$output" == *"prompt <list|name> [options]"* ]]
    [[ "$output" == *"docs [options]"* ]]
    [[ "$output" == *"clean [--older-than <age>] [--keep-last <count>] [options]"* ]]
    [[ "$output" == *"logs [options]"* ]]
    [[ "$output" == *"history [options]"* ]]
    [[ "$output" == *"config <path|show|doctor>"* ]]
    [[ "$output" == *"trust <status|allow|revoke> <project> [options]"* ]]
    [[ "$output" == *"doctor [project] [options]"* ]]
    [[ "$output" == *"gh <area> <command> [options]"* ]]
    [[ "$output" == *"onboard [project] [options]"* ]]
    [[ "$output" == *"demo [project] [options]"* ]]
    [[ "$output" == *"update [project] [options]"* ]]
    [[ "$output" == *"projects list [options]"* ]]
    [[ "$output" == *"workspace <status|check|doctor|clone|pull|init|configure> [options]"* ]]
    [[ "$output" == *"Invoking \`basectl\` with no command starts a Base runtime shell"* ]]
    [[ "$output" == *"--version"* ]]
    [[ "$output" == *"Wrapper options:"* ]]
    [[ "$output" == *"--debug-wrapper"* ]]
    [[ "$output" == *"--verbose-wrapper"* ]]
    [[ "$output" == *"--utc-wrapper"* ]]
    [[ "$output" == *"--color"* ]]
}

@test "basectl help omits legacy leftover commands" {
    run_basectl --help

    [ "$status" -eq 0 ]
    ! grep -Fqx '  run <command> [args...]' <<<"$output"
    ! grep -Fqx '  status' <<<"$output"
    ! grep -Fqx '  set-team TEAM' <<<"$output"
    ! grep -Fqx '  set-shared-teams TEAM...' <<<"$output"
    ! grep -Fqx '  man' <<<"$output"
    ! grep -Fqx '  embrace' <<<"$output"
    ! grep -Fqx '  install' <<<"$output"
    ! grep -Fqx '  shell' <<<"$output"
    grep -Fqx '  version' <<<"$output"
    grep -Fqx '  gh <area> <command> [options]' <<<"$output"
    grep -Fqx '  onboard [project] [options]' <<<"$output"
    grep -Fqx '  config <path|show|doctor>' <<<"$output"
    grep -Fqx '  run <project> <command> [options]' <<<"$output"
    grep -Fqx '  export-context [project] [options]' <<<"$output"
    grep -Fqx '  devcontainer [project] [options]' <<<"$output"
    grep -Fqx '  devenv-report [project] [options]' <<<"$output"
    grep -Fqx '  repo <init|clone|check|configure|agent-guidance|installer-template> [options]' <<<"$output"
    grep -Fqx '  ci <setup|check|doctor> <project> [options]' <<<"$output"
    grep -Fqx '  release <check|plan|notes|publish> --version <version> [options]' <<<"$output"
    grep -Fqx '  prompt <list|name> [options]' <<<"$output"
    grep -Fqx '  docs [options]' <<<"$output"
    grep -Fqx '  logs [options]' <<<"$output"
    grep -Fqx '  history [options]' <<<"$output"
    grep -Fqx '  workspace <status|check|doctor|clone|pull|init|configure> [options]' <<<"$output"
    grep -Fqx '  trust <status|allow|revoke> <project> [options]' <<<"$output"
    [[ "$output" != *"-b DIR"* ]]
    [[ "$output" != *"Force install"* ]]
    [[ "$output" != *"-V"* ]]
}

@test "basectl help routes to command-specific help" {
    run_basectl help repo

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo init <name>"* ]]
    [[ "$output" != *"Usage: basectl [options] <command> [args...]"* ]]

    run_basectl help workspace

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl workspace <status|check|doctor|onboarding|clone|pull|init|configure> [options]"* ]]
    [[ "$output" != *"Usage: basectl [options] <command> [args...]"* ]]

    run_basectl help release

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl release check --version <version>"* ]]
    [[ "$output" != *"Usage: basectl [options] <command> [args...]"* ]]
}

@test "basectl rejects equals-form long option values before command delegation" {
    run_basectl history --limit=2

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--limit' uses unsupported equals syntax. Use '--limit 2' instead."* ]]
    [[ "$output" != *"Project virtual environment Python was not found"* ]]

    run_basectl export-context demo --format=zip

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--format' uses unsupported equals syntax. Use '--format zip' instead."* ]]
    [[ "$output" != *"Project virtual environment Python was not found"* ]]
}

@test "basectl rejects Python standard options consistently before command delegation" {
    run_basectl logs --debug --path

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--debug' is not supported by basectl. Use '-v' for command-level debug logs or '--debug-wrapper' for wrapper startup logging."* ]]
    [[ "$output" != *"Project virtual environment Python was not found"* ]]

    run_basectl check --debug

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--debug' is not supported by basectl. Use '-v' for command-level debug logs or '--debug-wrapper' for wrapper startup logging."* ]]

    run_basectl logs --quiet --path

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--quiet' is not supported by basectl. Use command-specific options shown by 'basectl <command> --help'."* ]]
    [[ "$output" != *"Project virtual environment Python was not found"* ]]

    run_basectl logs --log-file "$TEST_TMPDIR/base.log" --path

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--log-file' is not supported by basectl. Use command-specific options shown by 'basectl <command> --help'."* ]]

    run_basectl logs --config "$TEST_TMPDIR/config.yaml" --path

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--config' is not supported by basectl. Use command-specific options shown by 'basectl <command> --help'."* ]]

    run_basectl logs --environment prod --path

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--environment' is not supported by basectl. Use command-specific options shown by 'basectl <command> --help'."* ]]

    run_basectl logs --keep-temp --path

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--keep-temp' is not supported by basectl. Use command-specific options shown by 'basectl <command> --help'."* ]]
}

@test "AI command context includes current clone and update surfaces" {
    local commands_file="$BASE_REPO_ROOT/.ai-context/COMMANDS.md"

    grep -Fqx -- "- \`basectl workspace <status|check|doctor|clone|pull|init|configure>\` - inspect" "$commands_file"
    grep -Fqx -- "  - \`workspace clone\` mutates repository checkouts only when invoked directly;" "$commands_file"
    grep -Fqx -- "- \`basectl repo <init|clone|check|configure|agent-guidance|installer-template>\` -" "$commands_file"
    grep -Fqx -- "- \`basectl update [project]\` - update Base or a named project using the" "$commands_file"
    grep -Fqx -- "- \`basectl docs\` - open the Base documentation home page on GitHub." "$commands_file"
    grep -Fqx -- "- \`basectl trust <status|allow|revoke> <project>\` - inspect, allow, or" "$commands_file"
}

@test "command reference documents workspace init help surface" {
    local command_reference="$BASE_REPO_ROOT/docs/command-reference.md"
    local workspace_init_row

    run_basectl workspace init --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl workspace init <workspace-source> [options]"* ]]

    workspace_init_row="$(grep -F '| `basectl workspace init <workspace-source>` |' "$command_reference")"
    [[ "$workspace_init_row" == *"Initialize a workspace from a workspace configuration repository"* ]]

    for flag in "--owner <owner>" "--path <path>" "--workspace <path>" "--manifest <path>" "--include-optional" "--dry-run"; do
        [[ "$output" == *"$flag"* ]]
        [[ "$workspace_init_row" == *"$flag"* ]]
    done
}

@test "command reference documents docs shortcut" {
    local command_reference="$BASE_REPO_ROOT/docs/command-reference.md"

    grep -Fqx -- "| \`basectl docs\` | Open the Base documentation home page on GitHub. | \`--show-url\` |" "$command_reference"
}

@test "command reference documents trust commands" {
    local command_reference="$BASE_REPO_ROOT/docs/command-reference.md"

    grep -Fqx -- "| \`basectl trust status <project>\` | Show local manifest command trust status. | \`--workspace <path>\`, \`--format <text\\|json>\` |" "$command_reference"
    grep -Fqx -- "| \`basectl trust allow <project>\` | Approve the current manifest command contract on this machine. | \`--workspace <path>\`, \`--manifest-sha256 <sha256>\` |" "$command_reference"
    grep -Fqx -- "| \`basectl trust revoke <project>\` | Remove local manifest command approval. | \`--workspace <path>\` |" "$command_reference"
}

@test "command reference documents repo and Project configuration options" {
    local command_reference="$BASE_REPO_ROOT/docs/command-reference.md"
    local repo_init_row repo_configure_row project_configure_row

    repo_init_row="$(grep -F '| `basectl repo init <name>` |' "$command_reference")"
    run_basectl repo init --help

    [ "$status" -eq 0 ]
    for flag in \
        "--description <text>" \
        "--copyright-holder <name>" \
        "--project <title>" \
        "--project-owner <login>" \
        "--project-schema <schema>" \
        "--copy-project-fields-from <title>" \
        "--initiative-option <name>" \
        "--no-protect-default-branch"; do
        [[ "$output" == *"$flag"* ]]
        [[ "$repo_init_row" == *"$flag"* ]]
    done

    repo_configure_row="$(grep -F '| `basectl repo configure [path]` |' "$command_reference")"
    run_basectl repo configure --help

    [ "$status" -eq 0 ]
    for flag in \
        "--project <title>" \
        "--project-owner <login>" \
        "--project-schema <schema>" \
        "--copy-project-fields-from <title>" \
        "--initiative-option <name>" \
        "--replace-project" \
        "--no-protect-default-branch"; do
        [[ "$output" == *"$flag"* ]]
        [[ "$repo_configure_row" == *"$flag"* ]]
    done

    project_configure_row="$(grep -F '| `basectl gh project configure` |' "$command_reference")"
    run_basectl gh project --help

    [ "$status" -eq 0 ]
    for flag in \
        "--schema base-project" \
        "--config <path>" \
        "--copy-fields-from <title>" \
        "--replace-project" \
        "--initiative-option <name>" \
        "--dry-run"; do
        [[ "$output" == *"$flag"* ]]
        [[ "$project_configure_row" == *"$flag"* ]]
    done
}

@test "basectl config prints help" {
    run_basectl config --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl config path"* ]]
    [[ "$output" == *"basectl config show"* ]]
    [[ "$output" == *"basectl config doctor"* ]]
}

@test "basectl config path prints default user config path without Python venv" {
    run_basectl config path

    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_HOME/.base.d/config.yaml" ]
}

@test "basectl config show forwards standard Python lifecycle options" {
    local base_home="$TEST_TMPDIR/base-home"
    mkdir -p "$base_home/bin"
    cat > "$base_home/bin/base-wrapper" <<'EOF'
#!/usr/bin/env bash
printf 'display=%s\n' "${BASE_CLI_DISPLAY_COMMAND:-}"
printf 'args=%s\n' "$*"
EOF
    chmod +x "$base_home/bin/base-wrapper"

    run env \
        BASE_HOME="$base_home" \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/config.sh"
            base_config_subcommand_main show --debug --log-file /tmp/base-config.log
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"display=basectl config"* ]]
    [[ "$output" == *"args=--project base base_config show --debug --log-file /tmp/base-config.log"* ]]
}

@test "basectl config reports unknown command as a usage error" {
    run_basectl config unknown

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown config command 'unknown'."* ]]
    [[ "$output" == *"Run 'basectl config --help' for usage."* ]]
    [[ "$output" != *"Usage:"* ]]
    [[ "$output" != *"FATAL"* ]]
    [[ "$output" != *"Encountered a fatal error"* ]]
}
