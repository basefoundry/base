#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl onboard prints help" {
    run_basectl onboard --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl onboard [project] [options]"* ]]
    [[ "$output" == *"--profile <list>"* ]]
    [[ "$output" != *"--dev"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" == *"--no-profile"* ]]
    [[ "$output" == *"Defaults to 'base'."* ]]
    [[ "$output" == *"manifest command trust"* ]]
}

@test "basectl onboard dry-run shows planned commands without prompting" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "unexpected run: %s\n" "$*" >&2; return 99; }
            base_onboard_subcommand_main --dry-run --profile dev
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run basectl check base --profile dev"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl setup base --profile dev --dry-run"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl update-profile --dry-run"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl doctor base --profile dev"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl projects list"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl trust status"* ]]
    [[ "$output" != *"trust allow"* ]]
    [[ "$output" != *"Next: basectl check base --profile dev"* ]]
    [[ "$output" != *"Next: basectl setup base --profile dev --dry-run"* ]]
    [[ "$output" != *"Next: basectl update-profile --dry-run"* ]]
    [[ "$output" != *"unexpected run"* ]]
}

@test "basectl onboard dry-run forwards prerequisite profiles" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "unexpected run: %s\n" "$*" >&2; return 99; }
            base_onboard_subcommand_main --dry-run --profile dev,SRE,AI
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run basectl check base --profile dev\\,sre\\,ai"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl setup base --profile dev\\,sre\\,ai --dry-run"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl doctor base --profile dev\\,sre\\,ai"* ]]
    [[ "$output" != *"unexpected run"* ]]
}

@test "basectl onboard dry-run targets an explicit project" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "unexpected run: %s\n" "$*" >&2; return 99; }
            base_onboard_subcommand_main bankbuddy --dry-run --profile dev
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base onboard will verify project 'bankbuddy'"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl check bankbuddy --profile dev"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl setup bankbuddy --profile dev --dry-run"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl doctor bankbuddy --profile dev"* ]]
    [[ "$output" == *"[DRY-RUN] Would run basectl trust status"* ]]
    [[ "$output" == *"basectl activate bankbuddy"* ]]
    [[ "$output" != *"unexpected run"* ]]
}

@test "basectl onboard rejects multiple projects" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_subcommand_main bankbuddy base-demo --dry-run
    '

    [ "$status" -eq 2 ]
    [[ "$output" == *"The onboard command accepts at most one project."* ]]
}

@test "basectl onboard rejects unknown profiles" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_subcommand_main --profile ops
    '

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported profile 'ops'. Expected one of: dev, sre, ai, linux-lab."* ]]
}

@test "basectl onboard declines setup conservatively" {
    local tty_input="$TEST_TMPDIR/onboard-tty"

    printf '\n' > "$tty_input"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_ONBOARD_TTY_FD=9 \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "RUN:%s\n" "$*"; return 0; }
            exec 9< "$1"
            base_onboard_subcommand_main
        ' bash "$tty_input"

    [ "$status" -eq 0 ]
    [[ "$output" == *"RUN:check base"* ]]
    [[ "$output" == *"Proceed with setup? [y/N]"* ]]
    [[ "$output" == *"Setup skipped."* ]]
    [[ "$output" != *"RUN:setup base"* ]]
}

@test "basectl onboard reads prompts from terminal fd when stdin is redirected" {
    local tty_input="$TEST_TMPDIR/onboard-tty"

    printf 'y\nn\n' > "$tty_input"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_ONBOARD_TTY_FD=9 \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "RUN:%s\n" "$*"; return 0; }
            exec 9< "$1"
            printf "\n\n" | base_onboard_subcommand_main
        ' bash "$tty_input"

    [ "$status" -eq 0 ]
    [[ "$output" == *"RUN:setup base"* ]]
    [[ "$output" == *"Shell profile update skipped. You can run 'basectl update-profile' later."* ]]
    [[ "$output" != *"RUN:update-profile"* ]]
}

@test "basectl onboard accepted flow runs setup profile doctor and projects" {
    local tty_input="$TEST_TMPDIR/onboard-tty"

    printf 'y\ny\n' > "$tty_input"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_ONBOARD_TTY_FD=9 \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { printf "RUN:%s\n" "$*"; return 0; }
            exec 9< "$1"
            base_onboard_subcommand_main --profile dev
        ' bash "$tty_input"

    [ "$status" -eq 0 ]
    [[ "$output" == *"RUN:check base --profile dev"* ]]
    [[ "$output" == *"RUN:setup base --profile dev"* ]]
    [[ "$output" == *"RUN:update-profile"* ]]
    [[ "$output" == *"RUN:doctor base --profile dev"* ]]
    [[ "$output" == *"RUN:projects list"* ]]
    [[ "$output" == *"RUN:trust status"* ]]
    [[ "$output" != *"RUN:trust allow"* ]]
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
    [[ "$output" == *"This installs or verifies Base platform prerequisites, Base Python, and Base-managed artifacts."* ]]
    [[ "$output" != *"This installs or verifies Homebrew, Xcode Command Line Tools"* ]]
    [[ "$output" == *"RUN:setup base --yes"* ]]
    [[ "$output" == *"Shell profile updates skipped because --no-profile was set."* ]]
    [[ "$output" == *"RUN:trust status"* ]]
    [[ "$output" != *"RUN:trust allow"* ]]
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
    [[ "$output" == *"RUN:setup base --yes"* ]]
    [[ "$output" == *"Setup failed. Running doctor can show the remaining issues."* ]]
    [[ "$output" == *"RUN:doctor base"* ]]
    [[ "$output" != *"RUN:update-profile"* ]]
    [[ "$output" != *"RUN:trust status"* ]]
}

@test "basectl onboard stops before activation guidance when trust status fails" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() {
                printf "RUN:%s\n" "$*"
                [[ "$1 $2" == "trust status" ]] && return 8
                return 0
            }
            base_onboard_subcommand_main --yes --no-profile
        '

    [ "$status" -eq 8 ]
    [[ "$output" == *"RUN:trust status"* ]]
    [[ "$output" != *"RUN:trust allow"* ]]
    [[ "$output" != *"Next Steps"* ]]
    [[ "$output" != *"basectl activate base"* ]]
}
