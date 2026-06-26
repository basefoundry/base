#!/usr/bin/env bats

load ./test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

@test "Bash source guard examples use explicit success returns" {
    grep -F '[[ -n "${_base_example_lib_sourced:-}" ]] && return 0' "$BASE_REPO_ROOT/STANDARDS.md"
}

@test "Bash source guards use single-underscore sentinels" {
    run grep -nE '__[A-Za-z0-9_]+_sourced__' \
        "$BASE_REPO_ROOT/base_init.sh" \
        "$BASE_REPO_ROOT/demo/demo.sh" \
        "$BASE_REPO_ROOT/lib/bash/version/lib_version.sh" \
        "$BASE_REPO_ROOT/lib/shell/"*.sh \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/basectl.sh" \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/"*.sh

    [ "$status" -eq 1 ]
}

@test "Bash source guards return explicit success" {
    run grep -nE '\[\[ -n "\$\{_[A-Za-z0-9_]+_sourced:-\}" \]\] && return$' \
        "$BASE_REPO_ROOT/base_init.sh" \
        "$BASE_REPO_ROOT/demo/demo.sh" \
        "$BASE_REPO_ROOT/lib/bash/version/lib_version.sh" \
        "$BASE_REPO_ROOT/lib/shell/"*.sh \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/basectl.sh" \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/"*.sh

    [ "$status" -eq 1 ]
}

@test "basectl dispatcher re-sourcing preserves local overrides" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/cli/bash/commands/basectl/basectl.sh"
            basectl_show_help() { printf "custom-help\n"; }
            source "$BASE_HOME/cli/bash/commands/basectl/basectl.sh"
            basectl_show_help
            declare -p _basectl_dispatcher_sourced
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"custom-help"* ]]
    [[ "$output" == *"declare -r _basectl_dispatcher_sourced=\"1\""* ]]
}

@test "Base self-demo re-sourcing preserves local overrides" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="${BASE_BASH_LIBS_DIR:-}" \
        bash -c '
            source "$BASE_HOME/demo/demo.sh"
            base_demo_pause() { printf "custom-pause\n"; }
            BASE_DEMO_NON_INTERACTIVE=9
            source "$BASE_HOME/demo/demo.sh"
            base_demo_pause
            printf "non_interactive=%s\n" "$BASE_DEMO_NON_INTERACTIVE"
            declare -p _base_demo_script_sourced
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"custom-pause"* ]]
    [[ "$output" == *"non_interactive=9"* ]]
    [[ "$output" == *"declare -r _base_demo_script_sourced=\"1\""* ]]
}

@test "Bash defaults re-sourcing preserves local overrides" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -i -c '
            source "$BASE_HOME/lib/shell/bash_defaults.sh"
            _base_bash_defaults_git_prompt() { printf "custom-git"; }
            PS1="custom-prompt"
            source "$BASE_HOME/lib/shell/bash_defaults.sh"
            printf "git_prompt=%s\n" "$(_base_bash_defaults_git_prompt)"
            printf "PS1=%s\n" "$PS1"
            declare -p _base_bash_defaults_sourced _base_defaults_sourced
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"git_prompt=custom-git"* ]]
    [[ "$output" == *"PS1=custom-prompt"* ]]
    [[ "$output" == *"declare -r _base_bash_defaults_sourced=\"1\""* ]]
    [[ "$output" == *"declare -r _base_defaults_sourced=\"1\""* ]]
}

@test "Zsh defaults re-sourcing preserves local overrides" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c '
            source "$BASE_HOME/lib/shell/zsh_defaults.sh"
            _base_zsh_defaults_git_prompt() { printf "custom-git"; }
            PROMPT="custom-prompt"
            source "$BASE_HOME/lib/shell/zsh_defaults.sh"
            printf "git_prompt=%s\n" "$(_base_zsh_defaults_git_prompt)"
            printf "PROMPT=%s\n" "$PROMPT"
            typeset -p _base_zsh_defaults_sourced _base_defaults_sourced
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"git_prompt=custom-git"* ]]
    [[ "$output" == *"PROMPT=custom-prompt"* ]]
    [[ "$output" == *"typeset -r _base_zsh_defaults_sourced=1"* ]]
    [[ "$output" == *"typeset -r _base_defaults_sourced=1"* ]]
}
