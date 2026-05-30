#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl onboard prints help" {
    run_basectl onboard --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl onboard [options]"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" == *"--no-profile"* ]]
}

@test "basectl onboard dry-run shows planned commands without prompting" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "unexpected run: %s\n" "$*" >&2; return 99; }
            base_onboard_subcommand_main --dry-run --dev
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run basectl check base --dev"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl setup base --dev --dry-run"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl update-profile --dry-run"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl doctor base --dev"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl projects list"* ]]
    [[ "$output" != *"Next: basectl check base --dev"* ]]
    [[ "$output" != *"Next: basectl setup base --dev --dry-run"* ]]
    [[ "$output" != *"Next: basectl update-profile --dry-run"* ]]
    [[ "$output" != *"unexpected run"* ]]
}

@test "basectl onboard declines setup conservatively" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "RUN:%s\n" "$*"; return 0; }
            printf "\n" | base_onboard_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"RUN:check base"* ]]
    [[ "$output" == *"Proceed with setup? [y/N]"* ]]
    [[ "$output" == *"Setup skipped."* ]]
    [[ "$output" != *"RUN:setup base"* ]]
}

@test "basectl onboard accepted flow runs setup profile doctor and projects" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "RUN:%s\n" "$*"; return 0; }
            printf "y\ny\n" | base_onboard_subcommand_main --dev
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"RUN:check base --dev"* ]]
    [[ "$output" == *"RUN:setup base --dev"* ]]
    [[ "$output" == *"RUN:update-profile"* ]]
    [[ "$output" == *"RUN:doctor base --dev"* ]]
    [[ "$output" == *"RUN:projects list"* ]]
}

@test "basectl onboard --yes accepts setup and profile prompts" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "RUN:%s\n" "$*"; return 0; }
            base_onboard_subcommand_main --yes --no-profile
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Proceed with setup? [yes]"* ]]
    [[ "$output" == *"RUN:setup base"* ]]
    [[ "$output" == *"Shell profile updates skipped because --no-profile was set."* ]]
    [[ "$output" != *"RUN:update-profile"* ]]
}

@test "basectl onboard setup failure stops profile updates and returns setup status" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() {
                printf "RUN:%s\n" "$*"
                [[ "$1" == setup ]] && return 7
                return 0
            }
            base_onboard_subcommand_main --yes
        '

    [ "$status" -eq 7 ]
    [[ "$output" == *"RUN:check base"* ]]
    [[ "$output" == *"RUN:setup base"* ]]
    [[ "$output" == *"Setup failed. Running doctor can show the remaining issues."* ]]
    [[ "$output" == *"RUN:doctor base"* ]]
    [[ "$output" != *"RUN:update-profile"* ]]
}
