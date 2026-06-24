#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl prints help with --help" {
    run_basectl --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
    [[ "$output" == *"activate <project> [options]"* ]]
    [[ "$output" == *"setup [options]"* ]]
    [[ "$output" == *"check [project] [options]"* ]]
    [[ "$output" == *"test [project] [options]"* ]]
    [[ "$output" == *"export-context [project] [options]"* ]]
    [[ "$output" == *"run <project> <command> [options]"* ]]
    [[ "$output" == *"repo <init|clone|check|configure|agent-guidance|installer-template> [options]"* ]]
    [[ "$output" == *"ci <setup|check|doctor> <project> [options]"* ]]
    [[ "$output" == *"release <check|plan|notes|publish> --version <version> [options]"* ]]
    [[ "$output" == *"prompt <list|name> [options]"* ]]
    [[ "$output" == *"clean [--older-than <age>] [--keep-last <count>] [options]"* ]]
    [[ "$output" == *"logs [options]"* ]]
    [[ "$output" == *"history [options]"* ]]
    [[ "$output" == *"config <path|show|doctor>"* ]]
    [[ "$output" == *"doctor [project] [options]"* ]]
    [[ "$output" == *"gh <area> <command> [options]"* ]]
    [[ "$output" == *"onboard [project] [options]"* ]]
    [[ "$output" == *"update [options]"* ]]
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
    grep -Fqx '  repo <init|clone|check|configure|agent-guidance|installer-template> [options]' <<<"$output"
    grep -Fqx '  ci <setup|check|doctor> <project> [options]' <<<"$output"
    grep -Fqx '  release <check|plan|notes|publish> --version <version> [options]' <<<"$output"
    grep -Fqx '  prompt <list|name> [options]' <<<"$output"
    grep -Fqx '  logs [options]' <<<"$output"
    grep -Fqx '  history [options]' <<<"$output"
    grep -Fqx '  workspace <status|check|doctor|clone|pull|init|configure> [options]' <<<"$output"
    [[ "$output" != *"-b DIR"* ]]
    [[ "$output" != *"Force install"* ]]
    [[ "$output" != *"-V"* ]]
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

@test "AI command context includes current clone and update surfaces" {
    local commands_file="$BASE_REPO_ROOT/.ai-context/COMMANDS.md"

    grep -Fqx -- "- \`basectl workspace <status|check|doctor|clone|pull|init|configure>\` - inspect" "$commands_file"
    grep -Fqx -- "  - \`workspace clone\` mutates repository checkouts only when invoked directly;" "$commands_file"
    grep -Fqx -- "- \`basectl repo <init|clone|check|configure|agent-guidance|installer-template>\` -" "$commands_file"
    grep -Fqx -- "- \`basectl update [project]\` - update Base or a named project using the" "$commands_file"
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

@test "basectl config reports unknown command as a usage error" {
    run_basectl config unknown

    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"ERROR: Unknown config command 'unknown'."* ]]
    [[ "$output" != *"FATAL"* ]]
    [[ "$output" != *"Encountered a fatal error"* ]]
}
