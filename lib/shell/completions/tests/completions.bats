#!/usr/bin/env bats

load ../../../../tests/test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
}

basectl_help_commands() {
    "$BASE_REPO_ROOT/bin/basectl" --help |
        awk '
            /^Commands:/ { in_commands = 1; next }
            /^Options:/ { in_commands = 0 }
            in_commands && /^  [a-z]/ {
                command = $1
                print command
            }
        ' |
        sort -u
}

bash_completion_commands() {
    sed -n 's/^[[:space:]]*local commands="\([^"]*\)".*/\1/p' \
        "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh" |
        tr ' ' '\n' |
        sed '/^$/d' |
        sort -u
}

zsh_completion_commands() {
    awk '
        /^[[:space:]]*commands=\(/ { in_commands = 1; next }
        in_commands && /^[[:space:]]*\)/ { in_commands = 0 }
        in_commands && /^[[:space:]]*'\''[^'\'']+:/ {
            command = $1
            sub(/^'\''/, "", command)
            sub(/:.*/, "", command)
            print command
        }
    ' "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh" |
        sort -u
}

nested_help_commands() {
    "$BASE_REPO_ROOT/bin/basectl" "$1" --help |
        awk '
            /^Commands:/ { in_commands = 1; next }
            /^Run / || /^Options:/ { in_commands = 0 }
            in_commands && /^  [a-z]/ {
                print $1
            }
        ' |
        sort -u
}

bash_completion_candidates() {
    env BASE_HOME="$BASE_REPO_ROOT" bash -c '\
        source "$BASE_HOME/lib/shell/completions/basectl_completion.sh"; \
        COMP_WORDS=("$@"); \
        COMP_CWORD=$((${#COMP_WORDS[@]} - 1)); \
        _base_basectl_completion; \
        printf "%s\n" "${COMPREPLY[@]}"' bash "$@"
}

bash_completion_long_options() {
    bash_completion_candidates "$@" |
        awk '/^--/ { print }' |
        sort -u
}

bash_completion_nested_commands() {
    bash_completion_candidates basectl "$1" "" |
        sort -u
}

zsh_completion_nested_commands() {
    local area="$1"

    awk -v area="$area" '
        $0 ~ "1:" area " command:\\(" {
            line = $0
            sub(/.*command:\(/, "", line)
            sub(/\).*/, "", line)
            split(line, commands, " ")
            for (command_index in commands) {
                if (commands[command_index] != "") {
                    print commands[command_index]
                }
            }
            exit
        }
    ' "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh" |
        sort -u
}

zsh_completion_nested_block() {
    local parent="$1"
    local child="$2"

    awk -v parent="$parent" -v child="$child" '
        $0 ~ "^[[:space:]]*" parent "\\)" { in_parent = 1 }
        in_parent && $0 ~ "^[[:space:]]*" child "\\)" {
            in_block = 1
            next
        }
        in_block && /^[[:space:]]*;;/ { exit }
        in_block { print }
    ' "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"
}

zsh_completion_deep_nested_block() {
    local parent="$1"
    local child="$2"
    local grandchild="$3"

    awk -v parent="$parent" -v child="$child" -v grandchild="$grandchild" '
        $0 ~ "^[[:space:]]*" parent "\\)" { in_parent = 1 }
        in_parent && $0 ~ "^[[:space:]]*" child "\\)" { in_child = 1 }
        in_child && $0 ~ "^[[:space:]]*" grandchild "\\)" {
            in_block = 1
            next
        }
        in_block && /^[[:space:]]*;;/ { exit }
        in_block { print }
    ' "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"
}

long_options_from_help() {
    "$BASE_REPO_ROOT/bin/basectl" "$@" --help |
        awk '
            /^Options:/ { in_options = 1; next }
            in_options && /^[^[:space:]]/ { in_options = 0 }
            in_options {
                for (i = 1; i <= NF; i++) {
                    if ($i ~ /^--/) {
                        option = $i
                        sub(/,.*/, "", option)
                        gsub(/[^-A-Za-z0-9_]/, "", option)
                        print option
                    }
                }
            }
        ' |
        sort -u
}

assert_nested_completion_matches_help() {
    local area="$1"
    local completion_shell="$2"
    local expected="$TEST_TMPDIR/$completion_shell-$area-help-commands"
    local actual="$TEST_TMPDIR/$completion_shell-$area-completion-commands"

    nested_help_commands "$area" > "$expected"
    "${completion_shell}_completion_nested_commands" "$area" > "$actual"

    bats_run diff -u "$expected" "$actual"

    [ "$status" -eq 0 ]
}

assert_bash_completion_options_match_help() {
    local label="$1"
    shift
    local expected="$TEST_TMPDIR/bash-$label-help-options"
    local actual="$TEST_TMPDIR/bash-$label-completion-options"

    long_options_from_help "$@" > "$expected"
    bash_completion_long_options basectl "$@" -- > "$actual"

    bats_run diff -u "$expected" "$actual"

    [ "$status" -eq 0 ]
}

@test "Bash completion top-level commands match basectl help" {
    local expected="$TEST_TMPDIR/help-commands"
    local actual="$TEST_TMPDIR/bash-completion-commands"

    basectl_help_commands > "$expected"
    bash_completion_commands > "$actual"

    bats_run diff -u "$expected" "$actual"

    [ "$status" -eq 0 ]
}

@test "Zsh completion top-level commands match basectl help" {
    local expected="$TEST_TMPDIR/help-commands"
    local actual="$TEST_TMPDIR/zsh-completion-commands"

    basectl_help_commands > "$expected"
    zsh_completion_commands > "$actual"

    bats_run diff -u "$expected" "$actual"

    [ "$status" -eq 0 ]
}

@test "Bash nested command completions match command help" {
    assert_nested_completion_matches_help workspace bash
    assert_nested_completion_matches_help repo bash
}

@test "Zsh nested command completions match command help" {
    assert_nested_completion_matches_help workspace zsh
    assert_nested_completion_matches_help repo zsh
}

@test "Bash option completions match command help" {
    assert_bash_completion_options_match_help check check
    assert_bash_completion_options_match_help doctor doctor
    assert_bash_completion_options_match_help repo-init repo init
    assert_bash_completion_options_match_help repo-configure repo configure
    assert_bash_completion_options_match_help repo-installer-template repo installer-template
}

@test "Zsh repo installer-template completion includes print options" {
    local block

    block="$(zsh_completion_nested_block repo installer-template)"

    [[ "$block" == *"--print"* ]]
    [[ "$block" == *"--stdout"* ]]
}

@test "Zsh gh issue completion includes issue create project options" {
    local block

    block="$(zsh_completion_nested_block gh issue)"

    [[ "$block" == *"--repo"* ]]
    [[ "$block" == *"--assignee"* ]]
    [[ "$block" == *"--no-assignee"* ]]
    [[ "$block" == *"--project"* ]]
    [[ "$block" == *"--project-owner"* ]]
    [[ "$block" == *"--size"* ]]
    [[ "$block" == *"--no-project"* ]]
}

@test "Zsh gh project configure completion includes replace-project option" {
    local block

    block="$(zsh_completion_deep_nested_block gh project configure)"

    [[ "$block" == *"--replace-project"* ]]
}
