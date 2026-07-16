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

zsh_completion_nested_long_options() {
    local parent="$1"
    local child="$2"

    zsh_completion_nested_block "$parent" "$child" |
        awk '
            {
                line = $0
                while (match(line, /--[-A-Za-z0-9_]+/)) {
                    print substr(line, RSTART, RLENGTH)
                    line = substr(line, RSTART + RLENGTH)
                }
            }
        ' |
        sort -u
}

assert_bash_ci_completion_options_match_help() {
    local command="$1"
    local expected="$TEST_TMPDIR/bash-ci-$command-help-options"
    local actual="$TEST_TMPDIR/bash-ci-$command-completion-options"

    long_options_from_help "$command" > "$expected"
    bash_completion_long_options basectl ci "$command" -- > "$actual"

    bats_run diff -u "$expected" "$actual"

    [ "$status" -eq 0 ]
}

assert_zsh_ci_completion_options_match_help() {
    local command="$1"
    local expected="$TEST_TMPDIR/zsh-ci-$command-help-options"
    local actual="$TEST_TMPDIR/zsh-ci-$command-completion-options"

    long_options_from_help "$command" > "$expected"
    zsh_completion_nested_long_options ci "$command" > "$actual"

    bats_run diff -u "$expected" "$actual"

    [ "$status" -eq 0 ]
}

run_zsh_positional_completion() {
    run env BASE_HOME="$BASE_REPO_ROOT" zsh -fc '
        compdef() { :; }
        source "$BASE_HOME/lib/shell/completions/basectl_completion.zsh"

        _arguments() {
            local positional_argument=$((CURRENT - 1)) spec

            for spec in "$@"; do
                if [[ "$spec" == "${positional_argument}:"* ]]; then
                    print -r -- "positional=$spec"
                    case "$spec" in
                        *"->projects") state=projects ;;
                        *"->doctor_targets") state=doctor_targets ;;
                    esac
                    return 0
                fi
            done
            print -r -- "positional=<none>"
        }
        _base_basectl_completion_describe_projects() {
            print -r -- "projects=base demo"
        }
        _alternative() {
            print -r -- "doctor_targets=explain base demo"
        }

        words=("$@")
        CURRENT=${#words}
        _base_basectl_completion
    ' zsh "$@"
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
    assert_bash_completion_options_match_help setup setup
    assert_bash_completion_options_match_help check check
    assert_bash_completion_options_match_help doctor doctor
    assert_bash_completion_options_match_help devcontainer devcontainer
    assert_bash_completion_options_match_help devenv-report devenv-report
    assert_bash_completion_options_match_help repo-init repo init
    assert_bash_completion_options_match_help repo-configure repo configure
    assert_bash_completion_options_match_help repo-installer-template repo installer-template
}

@test "Bash ci alias option completions match canonical command help" {
    assert_bash_ci_completion_options_match_help setup
    assert_bash_ci_completion_options_match_help check
    assert_bash_ci_completion_options_match_help doctor
}

@test "Zsh ci alias option completions match canonical command help" {
    assert_zsh_ci_completion_options_match_help setup
    assert_zsh_ci_completion_options_match_help check
    assert_zsh_ci_completion_options_match_help doctor
}

@test "Zsh lifecycle project completions use executable argument positions" {
    run_zsh_positional_completion basectl ci ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:ci command:(setup check doctor)"* ]]

    run_zsh_positional_completion basectl setup ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:Base project:->projects"* ]]
    [[ "$output" == *"projects=base demo"* ]]

    run_zsh_positional_completion basectl check ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:Base project:->projects"* ]]
    [[ "$output" == *"projects=base demo"* ]]

    run_zsh_positional_completion basectl doctor ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:doctor command or project:->doctor_targets"* ]]
    [[ "$output" == *"doctor_targets=explain base demo"* ]]

    run_zsh_positional_completion basectl ci setup ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:Base project:->projects"* ]]
    [[ "$output" == *"projects=base demo"* ]]

    run_zsh_positional_completion basectl ci check ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:Base project:->projects"* ]]
    [[ "$output" == *"projects=base demo"* ]]

    run_zsh_positional_completion basectl ci doctor ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:Base project:->projects"* ]]
    [[ "$output" == *"projects=base demo"* ]]
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

    [[ "$block" == *"2:issue command:(list create start readiness)"* ]]
    [[ "$block" == *"--repo"* ]]
    [[ "$block" == *"--assignee"* ]]
    [[ "$block" == *"--no-assignee"* ]]
    [[ "$block" == *"--project"* ]]
    [[ "$block" == *"--project-owner"* ]]
    [[ "$block" == *"--size"* ]]
    [[ "$block" == *"--no-project"* ]]
}

@test "Zsh gh issue start completion includes repository selectors" {
    local block

    block="$(zsh_completion_deep_nested_block gh issue start)"

    [[ "$block" == *"--repo"* ]]
    [[ "$block" == *"-R"* ]]
    [[ "$block" == *"--category"* ]]
    [[ "$block" == *"--title"* ]]
    [[ "$block" != *"--assignee"* ]]
}

@test "Zsh gh project configure completion includes replace-project option" {
    local block

    block="$(zsh_completion_deep_nested_block gh project configure)"

    [[ "$block" == *"--replace-project"* ]]
}

@test "Zsh prompt completion includes output option" {
    local block

    block="$(
        awk '
            /^[[:space:]]*prompt\)/ { in_block = 1 }
            in_block && /^[[:space:]]*;;/ { exit }
            in_block { print }
        ' "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"
    )"

    [[ "$block" == *"--output"* ]]
}

@test "Bash project-name completions reuse shell-session project cache" {
    local base_home="$TEST_TMPDIR/base"
    local wrapper="$base_home/bin/base-wrapper"
    local count_file="$TEST_TMPDIR/project-list-count"

    mkdir -p "$(dirname "$wrapper")"
    cat > "$wrapper" <<'EOF'
#!/usr/bin/env bash
source "${BASE_COMPLETION_TEST_PROTOCOL_FIXTURE:?}"
[[ " $* " == *" --format command-protocol "* ]] || exit 9
count=0
if [[ -f "${BASE_COMPLETION_TEST_COUNT_FILE:?}" ]]; then
    read -r count < "$BASE_COMPLETION_TEST_COUNT_FILE" || count=0
fi
count=$((count + 1))
printf '%s\n' "$count" > "$BASE_COMPLETION_TEST_COUNT_FILE"
base_test_protocol_begin project-list-entry 2
base_test_protocol_project_list_record 0 base /Users/test/base
base_test_protocol_project_list_record 1 demo /Users/test/demo
base_test_protocol_end
EOF
    chmod +x "$wrapper"

    run env BASE_HOME="$base_home" \
        BASE_COMPLETION_PROJECT_CACHE_TTL=60 \
        BASE_COMPLETION_TEST_COUNT_FILE="$count_file" \
        BASE_COMPLETION_TEST_PROTOCOL_FIXTURE="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash" \
        bash -c '\
            source "$1"; \
            COMP_WORDS=(basectl test ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "first=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl build ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "second=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl setup ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "setup=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci setup ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci-setup=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci check ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci-check=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl ci doctor ""); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "ci-doctor=%s\n" "${COMPREPLY[*]}"' \
            bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"first=base demo"* ]]
    [[ "$output" == *"second=base demo"* ]]
    [[ "$output" == *"setup=base demo"* ]]
    [[ "$output" == *"ci-setup=base demo"* ]]
    [[ "$output" == *"ci-check=base demo"* ]]
    [[ "$output" == *"ci-doctor=base demo"* ]]
    [ "$(cat "$count_file")" = "1" ]
}

@test "Bash project-name completion cache expires by TTL" {
    local base_home="$TEST_TMPDIR/base"
    local wrapper="$base_home/bin/base-wrapper"
    local count_file="$TEST_TMPDIR/project-list-count"

    mkdir -p "$(dirname "$wrapper")"
    cat > "$wrapper" <<'EOF'
#!/usr/bin/env bash
source "${BASE_COMPLETION_TEST_PROTOCOL_FIXTURE:?}"
[[ " $* " == *" --format command-protocol "* ]] || exit 9
count=0
if [[ -f "${BASE_COMPLETION_TEST_COUNT_FILE:?}" ]]; then
    read -r count < "$BASE_COMPLETION_TEST_COUNT_FILE" || count=0
fi
count=$((count + 1))
printf '%s\n' "$count" > "$BASE_COMPLETION_TEST_COUNT_FILE"
base_test_protocol_begin project-list-entry 1
if [[ "$count" -eq 1 ]]; then
    base_test_protocol_project_list_record 0 base /Users/test/base
else
    base_test_protocol_project_list_record 0 base-fresh /Users/test/base-fresh
fi
base_test_protocol_end
EOF
    chmod +x "$wrapper"

    run env BASE_HOME="$base_home" \
        BASE_COMPLETION_PROJECT_CACHE_TTL=1 \
        BASE_COMPLETION_TEST_COUNT_FILE="$count_file" \
        BASE_COMPLETION_TEST_PROTOCOL_FIXTURE="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash" \
        bash -c '\
            source "$1"; \
            _base_basectl_completion_now() { printf "%s\n" "$BASE_COMPLETION_TEST_NOW"; }; \
            BASE_COMPLETION_TEST_NOW=100; \
            COMP_WORDS=(basectl test ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "first=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl build ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "second=%s\n" "${COMPREPLY[*]}"; \
            BASE_COMPLETION_TEST_NOW=102; \
            COMP_WORDS=(basectl run ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "third=%s\n" "${COMPREPLY[*]}"' \
            bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"first=base"* ]]
    [[ "$output" == *"second=base"* ]]
    [[ "$output" == *"third=base-fresh"* ]]
    [ "$(cat "$count_file")" = "2" ]
}

@test "Bash project-name completion preserves names containing spaces" {
    local base_home="$TEST_TMPDIR/base"
    local wrapper="$base_home/bin/base-wrapper"

    mkdir -p "$(dirname "$wrapper")"
    cat > "$wrapper" <<'EOF'
#!/usr/bin/env bash
source "${BASE_COMPLETION_TEST_PROTOCOL_FIXTURE:?}"
[[ " $* " == *" --format command-protocol "* ]] || exit 9
base_test_protocol_begin project-list-entry 3
base_test_protocol_project_list_record 0 base /Users/test/base
base_test_protocol_project_list_record 1 "demo app" "/Users/test/demo app"
base_test_protocol_project_list_record 2 "data tools" "/Users/test/data tools"
base_test_protocol_end
EOF
    chmod +x "$wrapper"

    run env BASE_HOME="$base_home" \
        BASE_COMPLETION_PROJECT_CACHE_TTL=60 \
        BASE_COMPLETION_TEST_PROTOCOL_FIXTURE="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash" \
        bash -c '\
            source "$1"; \
            COMP_WORDS=(basectl test d); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "<%s>\n" "${COMPREPLY[@]}"' \
            bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"<demo app>"* ]]
    [[ "$output" == *"<data tools>"* ]]
    [[ "$output" != *"<demo>"* ]]
    [[ "$output" != *"<app>"* ]]
    [[ "$output" != *"<data>"* ]]
    [[ "$output" != *"<tools>"* ]]
}

@test "Zsh project-name completions consume structured names with spaces and Unicode" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    local args_file="$TEST_TMPDIR/project-list-args"
    local base_home="$TEST_TMPDIR/base"
    local wrapper="$base_home/bin/base-wrapper"

    mkdir -p "$(dirname "$wrapper")"
    cat > "$wrapper" <<'EOF'
#!/usr/bin/env bash
source "${BASE_COMPLETION_TEST_PROTOCOL_FIXTURE:?}"
printf '%s\n' "$*" > "${BASE_COMPLETION_TEST_ARGS_FILE:?}"
base_test_protocol_begin project-list-entry 2
base_test_protocol_project_list_record 0 base /Users/test/base
base_test_protocol_project_list_record 1 "demo app λ" "/Users/test/demo app λ"
base_test_protocol_end
EOF
    chmod +x "$wrapper"

    run env BASE_HOME="$base_home" \
        BASE_COMPLETION_PROJECT_CACHE_TTL=60 \
        BASE_COMPLETION_TEST_ARGS_FILE="$args_file" \
        BASE_COMPLETION_TEST_PROTOCOL_FIXTURE="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash" \
        zsh -fc '\
            source "$1"; \
            _base_basectl_completion_refresh_project_cache || exit; \
            print -r -- "$_BASE_BASECTL_COMPLETION_PROJECT_NAMES"' \
            zsh "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"

    [ "$status" -eq 0 ]
    [ "$output" = $'base\ndemo app λ' ]
    [[ "$(cat "$args_file")" == *"base_projects list --format command-protocol"* ]]
}

@test "Zsh project-name protocol reader rejects overflowing record counts" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    local payload=$'BASE_COMMAND_PROTOCOL_V1\nrecord_type=project-list-entry\nrecord_count=18446744073709551616\nend_protocol='

    run env PAYLOAD="$payload" zsh -fc '\
        source "$1"; \
        ! _base_basectl_completion_project_names_from_protocol "$PAYLOAD"' \
        zsh "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"

    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "Bash project-name protocol reader rejects overflowing record counts" {
    local payload=$'BASE_COMMAND_PROTOCOL_V1\nrecord_type=project-list-entry\nrecord_count=18446744073709551616\nend_protocol='

    run env PAYLOAD="$payload" /bin/bash -c '\
        source "$1"; \
        ! _base_basectl_completion_project_names_from_protocol "$PAYLOAD"' \
        bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "Bash completion now helper does not require external date" {
    local mockbin="$TEST_TMPDIR/mockbin"
    local date_called="$TEST_TMPDIR/date-called"

    mkdir -p "$mockbin"
    cat > "$mockbin/date" <<'EOF'
#!/usr/bin/env bash
printf 'called\n' > "${BASE_COMPLETION_TEST_DATE_CALLED:?}"
printf 'external date should not run\n' >&2
exit 99
EOF
    chmod +x "$mockbin/date"

    run env \
        BASE_COMPLETION_TEST_DATE_CALLED="$date_called" \
        PATH="$mockbin:/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -c '\
            source "$1"; \
            now="$(_base_basectl_completion_now)" || exit $?; \
            [[ "$now" =~ ^[0-9]+$ ]]; \
            printf "now=%s\n" "$now"' \
            bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == now=* ]]
    [ ! -e "$date_called" ]
}
