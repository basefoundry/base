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
    [[ "$output" == *"run <project> <command> [options]"* ]]
    [[ "$output" == *"clean [--older-than <age>] [--keep-last <count>] [options]"* ]]
    [[ "$output" == *"config <path|show|doctor>"* ]]
    [[ "$output" == *"doctor [project] [options]"* ]]
    [[ "$output" == *"gh <area> <command> [options]"* ]]
    [[ "$output" == *"onboard [options]"* ]]
    [[ "$output" == *"update [options]"* ]]
    [[ "$output" == *"projects list [options]"* ]]
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
    grep -Fqx '  onboard [options]' <<<"$output"
    grep -Fqx '  config <path|show|doctor>' <<<"$output"
    grep -Fqx '  run <project> <command> [options]' <<<"$output"
    [[ "$output" != *"-b DIR"* ]]
    [[ "$output" != *"Force install"* ]]
    [[ "$output" != *"-V"* ]]
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
