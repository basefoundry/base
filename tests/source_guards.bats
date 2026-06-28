#!/usr/bin/env bats

load ./test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN"
}

write_prompt_git_stub() {
    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$*" >> "${BASE_TEST_GIT_ARGS:?}"

case "$*" in
    "rev-parse --is-inside-work-tree --abbrev-ref HEAD")
        [[ "${BASE_TEST_GIT_MODE:-repo}" == "repo" ]] || exit 128
        printf 'true\nmain\n'
        ;;
    "rev-parse --is-inside-work-tree")
        [[ "${BASE_TEST_GIT_MODE:-repo}" == "repo" ]] || exit 128
        printf 'true\n'
        ;;
    "symbolic-ref --quiet --short HEAD")
        [[ "${BASE_TEST_GIT_MODE:-repo}" == "repo" ]] || exit 1
        printf 'main\n'
        ;;
    "rev-parse --short HEAD")
        [[ "${BASE_TEST_GIT_MODE:-repo}" == "repo" ]] || exit 128
        printf 'abc1234\n'
        ;;
    *)
        exit 127
        ;;
esac
EOF
    chmod +x "$TEST_MOCKBIN/git"
}

write_prompt_git_head() {
    local repo_dir="$1"
    local head_value="$2"

    mkdir -p "$repo_dir/.git"
    printf '%s\n' "$head_value" > "$repo_dir/.git/HEAD"
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

@test "Bash defaults git prompt reads branch metadata without Git subprocesses" {
    local repo_dir="$TEST_TMPDIR/bash-repo"

    write_prompt_git_stub
    write_prompt_git_head "$repo_dir" "ref: refs/heads/main"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_GIT_ARGS="$TEST_TMPDIR/bash-git-args" \
        BASE_TEST_REPO="$repo_dir" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -i -c '
            : > "$BASE_TEST_GIT_ARGS"
            source "$BASE_HOME/lib/shell/bash_defaults.sh"
            cd "$BASE_TEST_REPO"
            printf "first=%s\n" "$(_base_bash_defaults_git_prompt)"
            printf "second=%s\n" "$(_base_bash_defaults_git_prompt)"
            printf "git_calls=%s\n" "$(wc -l < "$BASE_TEST_GIT_ARGS" | tr -d "[:space:]")"
            printf "git_args=%s\n" "$(tr "\n" "|" < "$BASE_TEST_GIT_ARGS")"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"first=(main) "* ]]
    [[ "$output" == *"second=(main) "* ]]
    [[ "$output" == *"git_calls=0"* ]]
    [[ "$output" == *"git_args="* ]]
}

@test "Bash defaults git prompt reads detached HEAD metadata without Git subprocesses" {
    local repo_dir="$TEST_TMPDIR/bash-detached-repo"

    write_prompt_git_stub
    write_prompt_git_head "$repo_dir" "abc1234567890"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_GIT_ARGS="$TEST_TMPDIR/bash-detached-git-args" \
        BASE_TEST_REPO="$repo_dir" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -i -c '
            : > "$BASE_TEST_GIT_ARGS"
            source "$BASE_HOME/lib/shell/bash_defaults.sh"
            cd "$BASE_TEST_REPO"
            printf "prompt=%s\n" "$(_base_bash_defaults_git_prompt)"
            printf "git_calls=%s\n" "$(wc -l < "$BASE_TEST_GIT_ARGS" | tr -d "[:space:]")"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"prompt=(abc1234) "* ]]
    [[ "$output" == *"git_calls=0"* ]]
}

@test "Bash defaults git prompt keeps non-Git directories quiet with one probe" {
    write_prompt_git_stub

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_GIT_ARGS="$TEST_TMPDIR/bash-non-git-args" \
        BASE_TEST_GIT_MODE="non-git" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -i -c '
            : > "$BASE_TEST_GIT_ARGS"
            source "$BASE_HOME/lib/shell/bash_defaults.sh"
            printf "prompt=%s\n" "$(_base_bash_defaults_git_prompt)"
            printf "git_calls=%s\n" "$(wc -l < "$BASE_TEST_GIT_ARGS" | tr -d "[:space:]")"
            printf "git_args=%s\n" "$(tr "\n" "|" < "$BASE_TEST_GIT_ARGS")"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"prompt="* ]]
    [[ "$output" == *"git_calls=0"* ]]
    [[ "$output" == *"git_args="* ]]
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

@test "Zsh defaults git prompt reads branch metadata without Git subprocesses" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"
    local repo_dir="$TEST_TMPDIR/zsh-repo"

    write_prompt_git_stub
    write_prompt_git_head "$repo_dir" "ref: refs/heads/main"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_GIT_ARGS="$TEST_TMPDIR/zsh-git-args" \
        BASE_TEST_REPO="$repo_dir" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c '
            : > "$BASE_TEST_GIT_ARGS"
            source "$BASE_HOME/lib/shell/zsh_defaults.sh"
            cd "$BASE_TEST_REPO"
            printf "first=%s\n" "$(_base_zsh_defaults_git_prompt)"
            printf "second=%s\n" "$(_base_zsh_defaults_git_prompt)"
            printf "git_calls=%s\n" "$(wc -l < "$BASE_TEST_GIT_ARGS" | tr -d "[:space:]")"
            printf "git_args=%s\n" "$(tr "\n" "|" < "$BASE_TEST_GIT_ARGS")"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"first=(main) "* ]]
    [[ "$output" == *"second=(main) "* ]]
    [[ "$output" == *"git_calls=0"* ]]
    [[ "$output" == *"git_args="* ]]
}

@test "Zsh defaults git prompt reads detached HEAD metadata without Git subprocesses" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"
    local repo_dir="$TEST_TMPDIR/zsh-detached-repo"

    write_prompt_git_stub
    write_prompt_git_head "$repo_dir" "abc1234567890"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_GIT_ARGS="$TEST_TMPDIR/zsh-detached-git-args" \
        BASE_TEST_REPO="$repo_dir" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c '
            : > "$BASE_TEST_GIT_ARGS"
            source "$BASE_HOME/lib/shell/zsh_defaults.sh"
            cd "$BASE_TEST_REPO"
            printf "prompt=%s\n" "$(_base_zsh_defaults_git_prompt)"
            printf "git_calls=%s\n" "$(wc -l < "$BASE_TEST_GIT_ARGS" | tr -d "[:space:]")"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"prompt=(abc1234) "* ]]
    [[ "$output" == *"git_calls=0"* ]]
}

@test "Zsh defaults git prompt keeps non-Git directories quiet with one probe" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"
    write_prompt_git_stub

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_GIT_ARGS="$TEST_TMPDIR/zsh-non-git-args" \
        BASE_TEST_GIT_MODE="non-git" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c '
            : > "$BASE_TEST_GIT_ARGS"
            source "$BASE_HOME/lib/shell/zsh_defaults.sh"
            printf "prompt=%s\n" "$(_base_zsh_defaults_git_prompt)"
            printf "git_calls=%s\n" "$(wc -l < "$BASE_TEST_GIT_ARGS" | tr -d "[:space:]")"
            printf "git_args=%s\n" "$(tr "\n" "|" < "$BASE_TEST_GIT_ARGS")"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"prompt="* ]]
    [[ "$output" == *"git_calls=0"* ]]
    [[ "$output" == *"git_args="* ]]
}
