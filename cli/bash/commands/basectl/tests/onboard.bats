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

@test "basectl onboard preserves the selected project for history" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() { return 0; }
            base_onboard_subcommand_main bankbuddy --dry-run --no-profile
            printf "history_project=%s history_root=%s history_manifest=%s\\n" \
                "${BASE_CLI_HISTORY_PROJECT:-}" "${BASE_CLI_HISTORY_PROJECT_ROOT:-}" "${BASE_CLI_HISTORY_MANIFEST:-}"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"history_project=bankbuddy history_root= history_manifest="* ]]
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

@test "basectl onboard --yes satisfies the Ubuntu Debian setup consent boundary" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_MODE=true \
        BASE_ONBOARD_TEST_STATE="$TEST_STATE_DIR/onboard-linux-consent" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_setup_run_text() {
                setup_require_linux_debian_system_consent \
                    "Ubuntu/Debian setup requires package-manager consent." || return $?
                touch "$BASE_ONBOARD_TEST_STATE"
            }
            base_onboard_run_command() {
                if [[ "$1" == setup ]]; then
                    shift
                    base_setup_subcommand_main "$@"
                    return $?
                fi
                printf "RUN:%s\n" "$*"
            }
            base_onboard_subcommand_main --yes --no-profile
        '

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/onboard-linux-consent" ]
    [[ "$output" == *"Next: basectl setup base --yes"* ]]
    [[ "$output" != *"rerun with '--yes'"* ]]
    [[ "$output" != *"Proceed with Ubuntu/Debian setup changes?"* ]]
    [[ "$output" != *"trust allow"* ]]
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

@test "basectl onboard stops consistently when project discovery fails" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/onboard.sh"
            base_onboard_run_command() {
                printf "RUN:%s\n" "$*"
                [[ "$1 $2" == "projects list" ]] && return 9
                return 0
            }
            base_onboard_subcommand_main --yes --no-profile
        '

    [ "$status" -eq 9 ]
    [[ "$output" == *"Project discovery failed after setup."* ]]
    [[ "$output" == *"Retry 'basectl projects list', then run 'basectl trust status'"* ]]
    [[ "$output" != *"RUN:trust status"* ]]
    [[ "$output" != *"Next Steps"* ]]
}
