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

    zsh_completion_specs basectl "$area" "" |
        awk -v area="$area" '
        $0 ~ "^spec=2:" area " command:\\(" {
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
    ' |
        sort -u
}

zsh_completion_specs() {
    env BASE_HOME="$BASE_REPO_ROOT" zsh -fc '
        compdef() { :; }
        source "$BASE_HOME/lib/shell/completions/basectl_completion.zsh"
        _arguments() {
            printf "spec=%s\n" "$@"
        }
        _describe() { :; }
        _alternative() { :; }
        words=("$@")
        CURRENT=${#words}
        _base_basectl_completion
    ' zsh "$@"
}

zsh_completion_long_options() {
    zsh_completion_specs "$@" |
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

assert_zsh_completion_options_match_help() {
    local label="$1"
    shift
    local expected="$TEST_TMPDIR/zsh-$label-help-options"
    local actual="$TEST_TMPDIR/zsh-$label-completion-options"

    long_options_from_help "$@" > "$expected"
    zsh_completion_long_options basectl "$@" -- > "$actual"

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
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    assert_nested_completion_matches_help workspace zsh
    assert_nested_completion_matches_help repo zsh
}

@test "Bash option completions match command help" {
    assert_bash_completion_options_match_help setup setup
    assert_bash_completion_options_match_help activate activate
    assert_bash_completion_options_match_help check check
    assert_bash_completion_options_match_help doctor doctor
    assert_bash_completion_options_match_help test test
    assert_bash_completion_options_match_help build build
    assert_bash_completion_options_match_help demo demo
    assert_bash_completion_options_match_help run run
    assert_bash_completion_options_match_help devcontainer devcontainer
    assert_bash_completion_options_match_help devenv-report devenv-report
    assert_bash_completion_options_match_help repo-init repo init
    assert_bash_completion_options_match_help repo-check repo check
    assert_bash_completion_options_match_help repo-configure repo configure
    assert_bash_completion_options_match_help repo-installer-template repo installer-template
    assert_bash_completion_options_match_help release-check release check
    assert_bash_completion_options_match_help release-plan release plan
    assert_bash_completion_options_match_help release-notes release notes
    assert_bash_completion_options_match_help release-publish release publish
    assert_bash_completion_options_match_help trust-status trust status
    assert_bash_completion_options_match_help trust-allow trust allow
    assert_bash_completion_options_match_help trust-revoke trust revoke
    assert_bash_completion_options_match_help prompt-list prompt list
    assert_bash_completion_options_match_help prompt-render prompt product-self-review
    assert_bash_completion_options_match_help logs logs
    assert_bash_completion_options_match_help logs-last logs last
    assert_bash_completion_options_match_help gh-issue-readiness gh issue readiness
    assert_bash_completion_options_match_help gh-branch-stale gh branch stale
    assert_bash_completion_options_match_help gh-branch-prune gh branch prune
    assert_bash_completion_options_match_help gh-project-doctor gh project doctor
    assert_bash_completion_options_match_help gh-project-configure gh project configure
}

@test "Zsh option completions match focused leaf help" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    assert_zsh_completion_options_match_help activate activate
    assert_zsh_completion_options_match_help test test
    assert_zsh_completion_options_match_help build build
    assert_zsh_completion_options_match_help demo demo
    assert_zsh_completion_options_match_help run run
    assert_zsh_completion_options_match_help trust-status trust status
    assert_zsh_completion_options_match_help trust-allow trust allow
    assert_zsh_completion_options_match_help trust-revoke trust revoke
    assert_zsh_completion_options_match_help repo-check repo check
    assert_zsh_completion_options_match_help release-check release check
    assert_zsh_completion_options_match_help release-publish release publish
    assert_zsh_completion_options_match_help prompt-list prompt list
    assert_zsh_completion_options_match_help prompt-render prompt product-self-review
    assert_zsh_completion_options_match_help logs logs
    assert_zsh_completion_options_match_help logs-last logs last
    assert_zsh_completion_options_match_help gh-issue-readiness gh issue readiness
    assert_zsh_completion_options_match_help gh-branch-stale gh branch stale
    assert_zsh_completion_options_match_help gh-branch-prune gh branch prune
    assert_zsh_completion_options_match_help gh-project-doctor gh project doctor
    assert_zsh_completion_options_match_help gh-project-configure gh project configure
}

@test "format completions expose public values and preserve exceptions" {
    local public_values=$'text\ncsv\ntsv\nyaml\njson'
    local legacy_values=$'text\njson'
    local report_values=$'markdown\njson'
    local artifact_values=$'markdown\nzip'
    local specs

    run bash_completion_candidates basectl projects list --format ""
    [ "$status" -eq 0 ]
    [ "$output" = "$public_values" ]

    run bash_completion_candidates basectl history --report --format ""
    [ "$status" -eq 0 ]
    [ "$output" = "$report_values" ]

    run bash_completion_candidates basectl setup --format ""
    [ "$status" -eq 0 ]
    [ "$output" = "$legacy_values" ]

    run bash_completion_candidates basectl export-context --format ""
    [ "$status" -eq 0 ]
    [ "$output" = "$artifact_values" ]

    command -v zsh >/dev/null 2>&1 || return 0
    specs="$(zsh_completion_specs basectl projects list --format "")"
    [[ "$specs" == *"format:(text csv tsv yaml json)"* ]]
    specs="$(zsh_completion_specs basectl setup --format "")"
    [[ "$specs" == *"format:(text json)"* ]]
    specs="$(zsh_completion_specs basectl export-context --format "")"
    [[ "$specs" == *"format:(markdown zip)"* ]]
    specs="$(zsh_completion_specs basectl history --report --format "")"
    [[ "$specs" == *"format:(markdown json)"* ]]
}

@test "Bash help completion mirrors command and nested leaf candidates" {
    local direct nested

    direct="$(bash_completion_candidates basectl "" | sort)"
    nested="$(bash_completion_candidates basectl help "" | sort)"
    [ "$nested" = "$direct" ]

    direct="$(bash_completion_candidates basectl release "" | sort)"
    nested="$(bash_completion_candidates basectl help release "" | sort)"
    [ "$nested" = "$direct" ]

    direct="$(bash_completion_candidates basectl gh project "" | sort)"
    nested="$(bash_completion_candidates basectl help gh project "" | sort)"
    [ "$nested" = "$direct" ]
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
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

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

@test "Zsh public nested and positional completions use executable argument positions" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    run_zsh_positional_completion basectl projects ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:projects command:(list)"* ]]

    run_zsh_positional_completion basectl trust allow ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:Base project:->projects"* ]]
    [[ "$output" == *"projects=base demo"* ]]

    run_zsh_positional_completion basectl workspace init ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:workspace source:"* ]]

    run_zsh_positional_completion basectl test ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:Base project:->projects"* ]]

    run_zsh_positional_completion basectl run demo ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:Project command:"* ]]

    run_zsh_positional_completion basectl prompt ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:prompt:(list product-self-review)"* ]]

    run_zsh_positional_completion basectl repo ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:repo command:(init clone check configure agent-guidance installer-template)"* ]]

    run_zsh_positional_completion basectl repo check ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:path:_files"* ]]

    run_zsh_positional_completion basectl release ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:release command:(check plan notes publish)"* ]]

    run_zsh_positional_completion basectl logs ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:logs command:(last)"* ]]

    run_zsh_positional_completion basectl config ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:config command:(path show doctor)"* ]]

    run_zsh_positional_completion basectl doctor explain ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:finding id:"* ]]

    run_zsh_positional_completion basectl gh ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:gh area:(auth issue pr branch worktree project)"* ]]

    run_zsh_positional_completion basectl gh auth ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:auth command:(status refresh)"* ]]

    run_zsh_positional_completion basectl gh issue ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=3:issue command:(list create start readiness)"* ]]

    run_zsh_positional_completion basectl gh issue readiness ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=4:issue number:"* ]]

    run_zsh_positional_completion basectl gh project issue set-fields ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=5:issue number:"* ]]

    run_zsh_positional_completion basectl onboard ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:Base project:->projects"* ]]

    run_zsh_positional_completion basectl update ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"positional=2:Base project:->projects"* ]]
}

@test "Zsh repo installer-template completion includes print options" {
    local block

    block="$(zsh_completion_nested_block repo installer-template)"

    [[ "$block" == *"--print"* ]]
    [[ "$block" == *"--stdout"* ]]
}

@test "Zsh gh issue completion includes issue create project options" {
    local options specs

    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    specs="$(zsh_completion_specs basectl gh issue "")"
    options="$(zsh_completion_long_options basectl gh issue create --)"

    [[ "$specs" == *"3:issue command:(list create start readiness)"* ]]
    [[ "$options" == *"--repo"* ]]
    [[ "$options" == *"--assignee"* ]]
    [[ "$options" == *"--no-assignee"* ]]
    [[ "$options" == *"--project"* ]]
    [[ "$options" == *"--project-owner"* ]]
    [[ "$options" == *"--size"* ]]
    [[ "$options" == *"--no-project"* ]]
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
    [[ "$block" == *"--config"* ]]
    [[ "$block" == *"--copy-fields-from"* ]]
}

@test "Zsh gh project issue completion includes config option" {
    local block

    block="$(zsh_completion_deep_nested_block gh project issue)"

    [[ "$block" == *"--config"* ]]
}

@test "Zsh history completion includes report, ordering, and time options" {
    local block

    block="$(
        awk '
            /^[[:space:]]*history\)/ { in_block = 1 }
            in_block && /^[[:space:]]*;;/ { exit }
            in_block { print }
        ' "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"
    )"

    [[ "$block" == *"--report"* ]]
    [[ "$block" != *"--include-internal"* ]]
    [[ "$block" == *"--oldest-first"* ]]
    [[ "$block" == *"--last"* ]]
    [[ "$block" == *"--since"* ]]
    [[ "$block" == *"--until"* ]]
    [[ "$block" == *"--local-time"* ]]
}

@test "Zsh release completion scopes inspection and publish options" {
    local block

    block="$(sed -n '/^[[:space:]]*release)$/,/^[[:space:]]*clean)$/p' \
        "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh")"

    [[ "$block" == *"check)"* ]]
    [[ "$block" == *"plan|notes)"* ]]
    [[ "$block" == *"publish)"* ]]
    [[ "$block" == *"--format"* ]]
    [[ "$block" == *"--dry-run"* ]]
    [[ "$block" == *"--yes"* ]]
}

@test "Zsh help completion delegates to normal command completion" {
    local block

    block="$(
        awk '
            /^[[:space:]]*help\)/ { in_block = 1 }
            in_block && /^[[:space:]]*;;/ { exit }
            in_block { print }
        ' "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"
    )"

    [[ "$block" == *"_base_basectl_completion"* ]]
}

@test "Zsh prompt completion includes output option" {
    local list_options render_options

    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    list_options="$(zsh_completion_long_options basectl prompt list --)"
    render_options="$(zsh_completion_long_options basectl prompt product-self-review --)"

    [[ "$list_options" != *"--output"* ]]
    [[ "$render_options" == *"--output"* ]]
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
[[ "${4:-}" == list ]] || exit 9
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
            printf "ci-doctor=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl setup --profile dev ""); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "setup-after-options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl test --workspace /tmp ""); \
            COMP_CWORD=4; \
            _base_basectl_completion; \
            printf "test-after-options=%s\n" "${COMPREPLY[*]}"' \
            bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"first=base demo"* ]]
    [[ "$output" == *"second=base demo"* ]]
    [[ "$output" == *"setup=base demo"* ]]
    [[ "$output" == *"ci-setup=base demo"* ]]
    [[ "$output" == *"ci-check=base demo"* ]]
    [[ "$output" == *"ci-doctor=base demo"* ]]
    [[ "$output" == *"setup-after-options=base demo"* ]]
    [[ "$output" == *"test-after-options=base demo"* ]]
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
[[ "${4:-}" == list ]] || exit 9
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
    [[ "$(cat "$args_file")" == *"base_projects list --dry-run --format command-protocol"* ]]
}

@test "Bash lifecycle completion resolves current explicit and legacy manifest candidates read-only" {
    local args_file="$TEST_TMPDIR/completion-args"
    local base_home="$TEST_TMPDIR/base"
    local marker="$TEST_TMPDIR/executed"
    local version_file="$TEST_TMPDIR/manifest-version"
    local wrapper="$base_home/bin/base-wrapper"

    mkdir -p "$(dirname "$wrapper")"
    printf 'old\n' > "$version_file"
    cat > "$wrapper" <<'EOF'
#!/usr/bin/env bash
source "${BASE_COMPLETION_TEST_PROTOCOL_FIXTURE:?}"
printf '%s\n' "$*" >> "${BASE_COMPLETION_TEST_ARGS_FILE:?}"
[[ " $* " == *" --dry-run "* ]] || exit 9
case "${4:-}" in
    list)
        if [[ " $* " == *" --workspace /tmp/work space "* ]]; then
            base_test_protocol_begin project-list-entry 1
            base_test_protocol_project_list_record 0 remote "/tmp/work space/remote"
        else
            base_test_protocol_begin project-list-entry 2
            base_test_protocol_project_list_record 0 current "/Users/test/current project"
            base_test_protocol_project_list_record 1 api /Users/test/api
        fi
        base_test_protocol_end
        ;;
    run-commands)
        if [[ " $* " == *" run-commands api "* ]]; then
            base_test_protocol_begin named-command 1
            base_test_protocol_named_command_record 0 api /Users/test/api /Users/test/api/base_manifest.yaml deploy 'touch "$BASE_COMPLETION_TEST_MARKER"' ""
            base_test_protocol_end
        else
            command_name="$(<"${BASE_COMPLETION_TEST_VERSION_FILE:?}") command"
            base_test_protocol_begin named-command 3
            base_test_protocol_named_command_record 0 current "/Users/test/current project" "/Users/test/current project/base_manifest.yaml" "serve app" 'touch "$BASE_COMPLETION_TEST_MARKER"' ""
            base_test_protocol_named_command_record 1 current "/Users/test/current project" "/Users/test/current project/base_manifest.yaml" api 'touch "$BASE_COMPLETION_TEST_MARKER"' ""
            base_test_protocol_named_command_record 2 current "/Users/test/current project" "/Users/test/current project/base_manifest.yaml" "$command_name" 'touch "$BASE_COMPLETION_TEST_MARKER"' ""
            base_test_protocol_end
        fi
        ;;
    build-target-list)
        if [[ " $* " == *" build-target-list api "* ]]; then
            base_test_protocol_begin build-target 1
            base_test_protocol_build_target_record 0 api /Users/test/api /Users/test/api/base_manifest.yaml /Users/test/api/.venv false false package /Users/test/api 'touch "$BASE_COMPLETION_TEST_MARKER"' "Package" ""
            base_test_protocol_end
        else
            base_test_protocol_begin build-target 2
            base_test_protocol_build_target_record 0 current "/Users/test/current project" "/Users/test/current project/base_manifest.yaml" "/Users/test/current project/.venv" false false "web app" "/Users/test/current project" 'touch "$BASE_COMPLETION_TEST_MARKER"' "Web app" ""
            base_test_protocol_build_target_record 1 current "/Users/test/current project" "/Users/test/current project/base_manifest.yaml" "/Users/test/current project/.venv" false false api "/Users/test/current project" 'touch "$BASE_COMPLETION_TEST_MARKER"' "API" ""
            base_test_protocol_end
        fi
        ;;
    *) exit 8 ;;
esac
EOF
    chmod +x "$wrapper"

    run env BASE_HOME="$base_home" \
        BASE_COMPLETION_PROJECT_CACHE_TTL=60 \
        BASE_COMPLETION_TEST_ARGS_FILE="$args_file" \
        BASE_COMPLETION_TEST_MARKER="$marker" \
        BASE_COMPLETION_TEST_PROTOCOL_FIXTURE="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash" \
        BASE_COMPLETION_TEST_VERSION_FILE="$version_file" \
        bash -c '
            source "$1"
            complete_values() {
                COMP_WORDS=("$@")
                COMP_CWORD=$((${#COMP_WORDS[@]} - 1))
                _base_basectl_completion
                printf "<%s>" "${COMPREPLY[@]}"
                printf "\n"
            }
            printf "run-current="; complete_values basectl run ""
            printf "run-legacy="; complete_values basectl run api ""
            printf "run-explicit="; complete_values basectl run --project current a
            printf "build-current="; complete_values basectl build ""
            printf "build-legacy="; complete_values basectl build api ""
            printf "build-explicit="; complete_values basectl build --project current a
            printf "run-list="; complete_values basectl run --list ""
            printf "build-list="; complete_values basectl build --list ""
            printf "run-after-separator="; complete_values basectl run dev -- ""
            printf "build-after-separator="; complete_values basectl build api -- ""
            printf "run-workspace="; complete_values basectl run --workspace "/tmp/work space" ""
            printf "run-workspace-project="; complete_values basectl run --workspace "/tmp/work space" --project ""
            printf new > "$BASE_COMPLETION_TEST_VERSION_FILE"
            printf "run-changed="; complete_values basectl run n
        ' bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"run-current="*"<current>"*"<api>"*"<serve app>"*"<old command>"* ]]
    [[ "$output" == *"run-legacy=<deploy>"* ]]
    [[ "$output" == *"run-explicit=<api>"* ]]
    [[ "$output" == *"build-current="*"<current>"*"<api>"*"<web app>"* ]]
    [[ "$output" == *"build-legacy=<package>"* ]]
    [[ "$output" == *"build-explicit=<api>"* ]]
    [[ "$output" == *$'run-list=<current><api>\n'* ]]
    [[ "$output" == *$'build-list=<current><api>\n'* ]]
    [[ "$output" == *$'run-after-separator=<>\n'* ]]
    [[ "$output" == *$'build-after-separator=<>\n'* ]]
    [[ "$output" == *"run-workspace="*"<serve app>"* ]]
    [[ "$output" == *"run-workspace-project=<remote>"* ]]
    [[ "$output" == *"run-changed=<new command>"* ]]
    [ ! -e "$marker" ]
    [[ "$(cat "$args_file")" != *"base_trust"* ]]
    [[ "$(cat "$args_file")" == *"base_projects list --workspace /tmp/work space --dry-run --format command-protocol"* ]]
    ! grep -Ev 'base_projects (list|run-commands|build-target-list) ' "$args_file"
}

@test "Zsh lifecycle completion preserves manifest names and collision precedence" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    local base_home="$TEST_TMPDIR/base"
    local marker="$TEST_TMPDIR/executed"
    local wrapper="$base_home/bin/base-wrapper"

    mkdir -p "$(dirname "$wrapper")"
    cat > "$wrapper" <<'EOF'
#!/usr/bin/env bash
source "${BASE_COMPLETION_TEST_PROTOCOL_FIXTURE:?}"
[[ " $* " == *" --dry-run "* ]] || exit 9
case "${4:-}" in
    list)
        if [[ " $* " == *" --workspace /tmp/work space "* ]]; then
            base_test_protocol_begin project-list-entry 1
            base_test_protocol_project_list_record 0 remote "/tmp/work space/remote"
        else
            base_test_protocol_begin project-list-entry 2
            base_test_protocol_project_list_record 0 current "/Users/test/current project"
            base_test_protocol_project_list_record 1 api /Users/test/api
        fi
        base_test_protocol_end
        ;;
    run-commands)
        if [[ " $* " == *" run-commands api "* ]]; then
            base_test_protocol_begin named-command 1
            base_test_protocol_named_command_record 0 api /Users/test/api /Users/test/api/base_manifest.yaml deploy 'touch "$BASE_COMPLETION_TEST_MARKER"' ""
            base_test_protocol_end
        else
            base_test_protocol_begin named-command 2
            base_test_protocol_named_command_record 0 current "/Users/test/current project" "/Users/test/current project/base_manifest.yaml" "serve app" 'touch "$BASE_COMPLETION_TEST_MARKER"' ""
            base_test_protocol_named_command_record 1 current "/Users/test/current project" "/Users/test/current project/base_manifest.yaml" api 'touch "$BASE_COMPLETION_TEST_MARKER"' ""
            base_test_protocol_end
        fi
        ;;
    build-target-list)
        base_test_protocol_begin build-target 1
        base_test_protocol_build_target_record 0 current "/Users/test/current project" "/Users/test/current project/base_manifest.yaml" "/Users/test/current project/.venv" false false "web app" "/Users/test/current project" 'touch "$BASE_COMPLETION_TEST_MARKER"' "Web app" ""
        base_test_protocol_end
        ;;
    *) exit 8 ;;
esac
EOF
    chmod +x "$wrapper"

    run env BASE_HOME="$base_home" \
        BASE_COMPLETION_PROJECT_CACHE_TTL=60 \
        BASE_COMPLETION_TEST_MARKER="$marker" \
        BASE_COMPLETION_TEST_PROTOCOL_FIXTURE="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash" \
        zsh -fc '
            source "$1"
            _describe() {
                local name="${@: -1}"
                print -rl -- "${(@P)name}"
            }
            print run-current
            words=(basectl run ""); CURRENT=3; _base_basectl_completion_describe_lifecycle run
            print run-legacy
            words=(basectl run api ""); CURRENT=4; _base_basectl_completion_describe_lifecycle run
            print run-explicit
            words=(basectl run --project current a); CURRENT=5; _base_basectl_completion_describe_lifecycle run
            print run-workspace-project
            words=(basectl run --workspace "/tmp/work space" --project ""); CURRENT=6; _base_basectl_completion_describe_lifecycle_projects
            print run-list
            words=(basectl run --list ""); CURRENT=4; _base_basectl_completion_describe_lifecycle run
            print build-list
            words=(basectl build --list ""); CURRENT=4; _base_basectl_completion_describe_lifecycle build
            print run-after-separator
            words=(basectl run dev -- ""); CURRENT=5; _base_basectl_completion_describe_lifecycle run
            print build-after-separator
            words=(basectl build api -- ""); CURRENT=5; _base_basectl_completion_describe_lifecycle build
            print build-current
            words=(basectl build ""); CURRENT=3; _base_basectl_completion_describe_lifecycle build
        ' zsh "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.zsh"

    [ "$status" -eq 0 ]
    [[ "$output" == *$'run-current\ncurrent\napi\nserve app'* ]]
    [[ "$output" == *$'run-legacy\ndeploy'* ]]
    [[ "$output" == *$'run-explicit\nserve app\napi'* ]]
    [[ "$output" == *$'run-workspace-project\nremote'* ]]
    [[ "$output" == *$'run-list\ncurrent\napi\nbuild-list'* ]]
    [[ "$output" == *$'build-list\ncurrent\napi\nrun-after-separator\nbuild-after-separator\nbuild-current'* ]]
    [[ "$output" == *$'build-current\ncurrent\napi\nweb app'* ]]
    [ ! -e "$marker" ]
}

@test "Lifecycle completion degrades quietly for missing and malformed metadata" {
    local base_home="$TEST_TMPDIR/base"
    local wrapper="$base_home/bin/base-wrapper"

    mkdir -p "$(dirname "$wrapper")"
    cat > "$wrapper" <<'EOF'
#!/usr/bin/env bash
source "${BASE_COMPLETION_TEST_PROTOCOL_FIXTURE:?}"
case "${4:-}" in
    list)
        base_test_protocol_begin project-list-entry 1
        base_test_protocol_project_list_record 0 current /Users/test/current
        base_test_protocol_end
        ;;
    run-commands)
        printf 'completion metadata failed noisily\n' >&2
        base_test_protocol_begin named-command 2
        base_test_protocol_named_command_record 0 current /Users/test/current /Users/test/current/base_manifest.yaml valid 'printf safe' ""
        ;;
    *) exit 1 ;;
esac
EOF
    chmod +x "$wrapper"

    run env BASE_HOME="$base_home" \
        BASE_COMPLETION_TEST_PROTOCOL_FIXTURE="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash" \
        bash -c '
            source "$1"
            COMP_WORDS=(basectl run x)
            COMP_CWORD=2
            _base_basectl_completion
            printf "malformed=%s\n" "${#COMPREPLY[@]}"
        ' bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [ "$output" = "malformed=0" ]

    run env BASE_HOME="$TEST_TMPDIR/missing" bash -c '
        source "$1"
        COMP_WORDS=(basectl build x)
        COMP_CWORD=2
        _base_basectl_completion
        printf "missing=%s\n" "${#COMPREPLY[@]}"
    ' bash "$BASE_REPO_ROOT/lib/shell/completions/basectl_completion.sh"

    [ "$status" -eq 0 ]
    [ "$output" = "missing=0" ]
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
