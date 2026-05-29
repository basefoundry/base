#!/usr/bin/env bats

load ../../../../../lib/bash/tests/test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_STATE_DIR="$TEST_TMPDIR/state"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN" "$TEST_STATE_DIR"
}

run_basectl() {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" "$@"
}

@test "basectl prints help with --help" {
    run_basectl --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
    [[ "$output" == *"activate <project> [options]"* ]]
    [[ "$output" == *"setup [options]"* ]]
    [[ "$output" == *"check [project] [options]"* ]]
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

@test "basectl gh prints help" {
    run_basectl gh --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl gh issue start <number>"* ]]
    [[ "$output" == *"<type>/<issue>-<YYYYMMDD>-<slug>"* ]]
}

@test "basectl gh issue create applies type label" {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue create --type fix --title "Repair branch pruning"
        '

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "issue create --title Repair branch pruning --label type:fix" ]
}

@test "basectl gh issue start creates convention branch from issue metadata" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "issue view 117 --json labels --jq .labels[].name | select(startswith(\"type:\")) | sub(\"^type:\"; \"\")" ]]; then
    printf 'feat\n'
    exit 0
fi
if [[ "$*" == "issue view 117 --json title --jq .title" ]]; then
    printf 'Add basectl gh workflow for issues\n'
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == "feat/117-"*"-add-basectl-gh-workflow-for-issues" ]]
    [ "$(git -C "$repo" branch --show-current)" = "$output" ]
}

@test "basectl gh issue start accepts explicit type and title without gh" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main issue start 117 --type chore --title "Prune merged branches"
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$output" == "chore/117-"*"-prune-merged-branches" ]]
}

@test "basectl gh pr create links current branch issue" {
    local repo

    repo="$TEST_TMPDIR/repo"
    init_git_repo "$repo"
    printf 'hello\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    git -C "$repo" switch -c "feat/117-20260528-basectl-gh-workflow" >/dev/null

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/gh-args"
body_file=""
while (($#)); do
    if [[ "$1" == "--body-file" ]]; then
        body_file="$2"
        break
    fi
    shift
done
[[ -n "$body_file" ]] && cat "$body_file" > "${BASE_GH_TEST_STATE_DIR:?}/body"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            cd "$1"
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main pr create
        ' bash "$repo"

    [ "$status" -eq 0 ]
    [[ "$(cat "$TEST_STATE_DIR/gh-args")" == pr\ create\ --fill\ --body-file* ]]
    [ "$(cat "$TEST_STATE_DIR/body")" = "Fixes #117" ]
}

@test "basectl gh todo import dry-run classifies TODO items" {
    local todo_file

    todo_file="$TEST_TMPDIR/TODO.md"
    cat > "$todo_file" <<'EOF'
## P0 — Security And Correctness

- [ ] Detect outdated Xcode Command Line Tools in `basectl doctor`.

## P1 — Product Core And Composability

- [ ] Add first-class `mise` integration.
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main todo import --dry-run --file "$1"
        ' bash "$todo_file"

    [ "$status" -eq 0 ]
    [[ "$output" == *$'type:fix\tDetect outdated Xcode Command Line Tools in `basectl doctor`'* ]]
    [[ "$output" == *$'type:feat\tAdd first-class `mise` integration'* ]]
}

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

@test "basectl update prints help" {
    run_basectl update --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl update [options]"* ]]
    [[ "$output" == *"Update the Base repository from Git"* ]]
}

@test "basectl update dry-run reports planned update and setup" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" master; }
            base_update_default_branch() { printf "%s\n" master; }
            base_update_worktree_clean() { return 0; }
            base_update_subcommand_main --dry-run
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would update Base repository at '$BASE_REPO_ROOT'."* ]]
    [[ "$output" == *"[DRY-RUN] Would run 'basectl setup' after updating."* ]]
}

@test "basectl update refuses dirty worktrees before pulling" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" master; }
            base_update_default_branch() { printf "%s\n" master; }
            base_update_worktree_clean() { return 1; }
            base_update_run_setup() { printf "setup should not run\n"; return 99; }
            base_update_subcommand_main
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base repository has local changes."* ]]
    [[ "$output" != *"setup should not run"* ]]
}

@test "basectl update refuses non-default branches" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" feature/example; }
            base_update_default_branch() { printf "%s\n" main; }
            base_update_worktree_clean() { printf "clean should not run\n"; return 99; }
            base_update_run_setup() { printf "setup should not run\n"; return 99; }
            base_update_subcommand_main
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base update only runs on default branch 'main'; current branch is 'feature/example'."* ]]
    [[ "$output" != *"clean should not run"* ]]
    [[ "$output" != *"setup should not run"* ]]
}

@test "basectl update reports already up-to-date repositories" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" master; }
            base_update_default_branch() { printf "%s\n" master; }
            base_update_worktree_clean() { return 0; }
            base_update_source_git_library() { :; }
            git_update_repo() { printf "git update repo=%s branch=%s\n" "$1" "$3"; }
            base_update_head_revision() { printf "%s\n" abc1234; }
            base_update_run_setup() { printf "setup ran\n"; }
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Updating Base repository at '$BASE_REPO_ROOT'."* ]]
    [[ "$output" == *"Base repository is already up to date on 'master' at 'abc1234'."* ]]
    [[ "$output" == *"Running basectl setup after update."* ]]
    [[ "$output" == *"setup ran"* ]]
    [[ "$output" == *"Base update is complete."* ]]
}

@test "basectl update reports changed revisions" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_AFTER_UPDATE="$TEST_TMPDIR/after-update" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_current_branch() { printf "%s\n" main; }
            base_update_default_branch() { printf "%s\n" main; }
            base_update_worktree_clean() { return 0; }
            base_update_source_git_library() { :; }
            git_update_repo() { printf "git update repo=%s branch=%s\n" "$1" "$3"; }
            base_update_head_revision() {
                if [[ -f "$BASE_TEST_AFTER_UPDATE" ]]; then
                    printf "%s\n" new5678
                else
                    touch "$BASE_TEST_AFTER_UPDATE"
                    printf "%s\n" old1234
                fi
            }
            base_update_run_setup() { printf "setup ran\n"; }
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"git update repo=$BASE_REPO_ROOT branch=main"* ]]
    [[ "$output" == *"Base repository updated from 'old1234' to 'new5678' on 'main'."* ]]
    [[ "$output" == *"setup ran"* ]]
    [[ "$output" == *"Base update is complete."* ]]
}

@test "basectl prints help when no command is given in a non-interactive shell" {
    run_basectl

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: basectl [options] <command> [args...]"* ]]
}

@test "basectl with no command activates the current Base project in an interactive shell" {
    local fake_base_home="$TEST_TMPDIR/fake-base-home"

    mkdir -p "$fake_base_home/bin"
    cat > "$fake_base_home/bin/base-wrapper" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--project" && "${2:-}" == "base" && "${3:-}" == "base_projects" && "${4:-}" == "current" ]]; then
    printf 'brew\t/tmp/work/brew\t/tmp/work/brew/base_manifest.yaml\n'
    exit 0
fi
printf 'unexpected args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$fake_base_home/bin/base-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_FAKE_BASE_HOME="$fake_base_home" \
        bash -c '
            source "$BASE_HOME/cli/bash/commands/basectl/basectl.sh"
            log_debug() { :; }
            basectl_should_start_shell() { return 0; }
            basectl_get_base_home() { BASE_HOME="$BASE_TEST_FAKE_BASE_HOME"; export BASE_HOME; }
            basectl_do_activate() { printf "activate=%s preserve=%s\n" "$*" "${BASE_ACTIVATE_PRESERVE_CWD:-}"; }
            basectl_main
        '

    [ "$status" -eq 0 ]
    [ "$output" = "activate=brew preserve=1" ]
}

@test "basectl with no command falls back to base when current directory is not in a Base project" {
    local fake_base_home="$TEST_TMPDIR/fake-base-home"

    mkdir -p "$fake_base_home/bin"
    cat > "$fake_base_home/bin/base-wrapper" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
    chmod +x "$fake_base_home/bin/base-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_FAKE_BASE_HOME="$fake_base_home" \
        bash -c '
            source "$BASE_HOME/cli/bash/commands/basectl/basectl.sh"
            log_debug() { :; }
            basectl_should_start_shell() { return 0; }
            basectl_get_base_home() { BASE_HOME="$BASE_TEST_FAKE_BASE_HOME"; export BASE_HOME; }
            basectl_do_activate() { printf "activate=%s preserve=%s\n" "$*" "${BASE_ACTIVATE_PRESERVE_CWD:-}"; }
            basectl_main
        '

    [ "$status" -eq 0 ]
    [ "$output" = "activate=base preserve=1" ]
}

@test "basectl prints version with --version and version" {
    local expected_version

    expected_version="$(head -n 1 "$BASE_REPO_ROOT/VERSION")"

    run_basectl --version
    [ "$status" -eq 0 ]
    [ "$output" = "basectl $expected_version" ]

    run_basectl version
    [ "$status" -eq 0 ]
    [ "$output" = "basectl $expected_version" ]
}

@test "basectl re-execs through an installed supported Bash when current Bash is too old" {
    local fake_bash="$TEST_TMPDIR/fake-bash"

    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'fake_bash=%s\n' "$0"
printf 'args=%s\n' "$*"
EOF
    chmod +x "$fake_bash"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_BASH_VERSION=32 \
        BASE_TEST_BASH_CANDIDATES="$fake_bash" \
        "$BASE_REPO_ROOT/bin/basectl" --version

    [ "$status" -eq 0 ]
    [[ "$output" == *"fake_bash=$fake_bash"* ]]
    [[ "$output" == *"args=$BASE_REPO_ROOT/bin/basectl --version"* ]]
}

@test "basectl gives setup guidance when current Bash is too old and no supported Bash is installed" {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_BASH_VERSION=32 \
        BASE_TEST_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        "$BASE_REPO_ROOT/bin/basectl" --version

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base requires Bash 4.2 or newer; current version is 3.2."* ]]
    [[ "$output" == *"A supported Bash was not found"* ]]
    [[ "$output" == *"basectl setup"* ]]
    [[ "$output" == *"brew install bash"* ]]
}

@test "basectl setup prints setup-specific help" {
    run_basectl setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl setup [options]"* ]]
    [[ "$output" == *"Prepare the local Base CLI environment on macOS."* ]]
}

@test "basectl projects list discovers manifests in a workspace" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$python_bin")" "$workspace/base" "$workspace/demo" "$workspace/notes"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "list" && "${4:-}" == "--workspace" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT" > "${BASE_TEST_PROJECTS_LIST_STATE:?}"
    printf '%s\t%s\n' base "$5/base"
    printf '%s\t%s\n' demo "$5/demo"
    exit 0
fi
printf 'unexpected projects list python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"
    printf 'project:\n  name: base\nartifacts: []\n' > "$workspace/base/base_manifest.yaml"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECTS_LIST_STATE="$TEST_TMPDIR/projects-list-state" \
        "$BASE_REPO_ROOT/bin/basectl" projects list --workspace "$workspace"

    [ "$status" -eq 0 ]
    [[ "$output" == *$'base\t'"$workspace/base"* ]]
    [[ "$output" == *$'demo\t'"$workspace/demo"* ]]
    [ "$(cat "$TEST_TMPDIR/projects-list-state")" = "BASE_PROJECT=base" ]
}

@test "basectl projects list prints help without requiring the Base Python venv" {
    run_basectl projects list --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl projects list [options]"* ]]
}

@test "basectl clean delegates to the Python cleanup layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_clean" ]]; then
    printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
    printf 'ARGS=%s\n' "${*:3}"
    exit 0
fi
printf 'unexpected clean python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$python_bin"

    run_basectl clean --older-than 30d --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"ARGS=--older-than 30d --dry-run"* ]]
}

@test "basectl clean prints help without requiring the Base Python venv" {
    run_basectl clean --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl clean [--older-than <age>] [--keep-last <count>] [options]"* ]]
}

@test "basectl clean reports missing cleanup criterion as a usage error" {
    run_basectl clean

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: One of '--older-than' or '--keep-last' is required."* ]]
    [[ "$output" != *"Traceback"* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl clean --older-than

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--older-than' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl clean --keep-last

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--keep-last' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]
}

@test "basectl doctor prints help" {
    run_basectl doctor --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl doctor [project] [options]"* ]]
    [[ "$output" == *"Diagnose the local Base CLI environment"* ]]
}

@test "basectl doctor reports ok findings and includes dev checks" {
    local fake_bin="$TEST_TMPDIR/bin"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13|bats-core) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/gh" <<'EOF'
#!/usr/bin/env bash
printf 'gh version test\n'
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" && "${3:-}" == "doctor" ]]; then
    printf 'ok     bats-core                   Artifact '\''bats-core'\'' is installed via Homebrew package '\''bats-core'\''.\n'
    printf 'ok     gh                          Artifact '\''gh'\'' is installed via Homebrew package '\''gh'\''.\n'
    exit 0
fi
exit 1
EOF
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$fake_bin/gh" "$venv_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor --dev

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base doctor"* ]]
    [[ "$output" == *"ok"*"Homebrew"*"Homebrew is installed."* ]]
    [[ "$output" == *"ok"*"bats-core"*"Artifact 'bats-core' is installed via Homebrew package 'bats-core'."* ]]
    [[ "$output" == *"ok"*"gh"*"Artifact 'gh' is installed via Homebrew package 'gh'."* ]]
    [[ "$output" == *"ok"*"Base virtualenv"*"Virtual environment exists at"* ]]
    [[ "$output" == *"Base doctor found no blocking issues."* ]]
}

@test "basectl doctor --dev reports missing GitHub CLI" {
    local fake_bin="$TEST_TMPDIR/bin"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13|bats-core) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" && "${3:-}" == "doctor" ]]; then
    printf 'ok     bats-core                   Artifact '\''bats-core'\'' is installed via Homebrew package '\''bats-core'\''.\n'
    printf 'error  gh                          Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.\n'
    printf '       Fix: basectl setup --dev\n'
    exit 1
fi
exit 1
EOF
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$venv_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor --dev

    [ "$status" -eq 1 ]
    [[ "$output" == *"error"*"gh"*"Artifact 'gh' is not installed via Homebrew package 'gh'."* ]]
    [[ "$output" == *"Fix: basectl setup --dev"* ]]
}

@test "basectl doctor reports errors with suggested fixes" {
    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_SETUP_BREW_BIN="$TEST_TMPDIR/missing-brew" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/missing-xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base doctor"* ]]
    [[ "$output" == *"error"*"Homebrew"*"Homebrew is not installed."* ]]
    [[ "$output" == *"Fix: basectl setup"* ]]
    [[ "$output" == *"Base doctor found"*"blocking issue(s)."* ]]
}

@test "basectl doctor --format json reports structured findings" {
    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_SETUP_BREW_BIN="$TEST_TMPDIR/missing-brew" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/missing-xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"ok": false'* ]]
    [[ "$output" == *'"findings":'* ]]
    [[ "$output" == *'"status":"error","name":"Homebrew","message":"Homebrew is not installed.","fix":"basectl setup"'* ]]
    [[ "$output" == *'"status":"error","name":"Base virtualenv"'* ]]
    [[ "$output" != *"Base doctor"* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl doctor project includes project artifact findings" {
    local fake_bin="$TEST_TMPDIR/bin"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")" "$(dirname "$project_python")" "$workspace/demo"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    printf 'ok     demo-artifact               Project artifact check passed.\n'
    exit 0
fi
printf 'unexpected doctor project python args: %s\n' "$*" >&2
exit 1
EOF
    cp "$venv_python" "$project_python"
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$venv_python" "$project_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run env \
        HOME="$TEST_HOME" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base doctor for project 'demo'"* ]]
    [[ "$output" == *"Running Python project doctor layer."* ]]
    [[ "$output" == *"ok"*"demo-artifact"*"Project artifact check passed."* ]]
    [[ "$output" == *"Base doctor found no blocking issues for project 'demo'."* ]]
}

@test "basectl doctor project --format json includes project findings" {
    local fake_bin="$TEST_TMPDIR/bin"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local venv_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$fake_bin" "$(dirname "$venv_python")" "$(dirname "$project_python")" "$workspace/demo"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    cat > "$fake_bin/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "list" ]]; then
    case "${2:-}" in
        python@3.13) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "--prefix" ]]; then
    printf '/tmp/fake-prefix\n'
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcode-select" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-p" ]]; then
    printf '%s\n' "${BASE_TEST_XCODE_TOOLS_DIR:?}"
    exit 0
fi
exit 1
EOF
    cat > "$fake_bin/xcrun" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "clang" ]]; then
    printf '/tmp/fake-clang\n'
    exit 0
fi
exit 1
EOF
    cat > "$venv_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    case "${4:-}" in
        PyYAML|click) exit 0 ;;
    esac
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    printf '[{"status":"warn","name":"demo-artifact","message":"Optional project artifact is not installed.","fix":"basectl setup demo"}]\n'
    exit 0
fi
printf 'unexpected doctor project json python args: %s\n' "$*" >&2
exit 1
EOF
    cp "$venv_python" "$project_python"
    chmod +x "$fake_bin/brew" "$fake_bin/xcode-select" "$fake_bin/xcrun" "$venv_python" "$project_python"
    mkdir -p "$TEST_TMPDIR/xcode-tools/usr/bin"
    touch "$TEST_TMPDIR/xcode-tools/usr/bin/clang"
    touch "$TEST_HOME/.base.d/base/.venv/pyvenv.cfg"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        BASE_TEST_XCODE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/xcode-tools" \
        "$BASE_REPO_ROOT/bin/basectl" doctor demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"ok": true'* ]]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_findings":'* ]]
    [[ "$output" == *'"status":"warn","name":"demo-artifact","message":"Optional project artifact is not installed.","fix":"basectl setup demo"'* ]]
    [[ "$output" != *"Running Python project doctor layer."* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl activate resolves a project and execs a project subshell" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local project_activate="$TEST_HOME/.base.d/demo/.venv/bin/activate"
    local workspace="$TEST_TMPDIR/workspace"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'args=%s\n' "$*"
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_ROOT=%s\n' "$BASE_PROJECT_ROOT"
printf 'BASE_PROJECT_MANIFEST=%s\n' "$BASE_PROJECT_MANIFEST"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
printf 'PWD=%s\n' "$PWD"
EOF
    printf '#!/usr/bin/env bash\n' > "$project_python"
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$TEST_HOME/.base.d/demo/.venv" > "$project_activate"
    chmod +x "$base_python" "$project_python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"args=--rcfile $BASE_REPO_ROOT/lib/bash/runtime/bashrc"* ]]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$workspace/demo"* ]]
    [[ "$output" == *"BASE_PROJECT_MANIFEST=$workspace/demo/base_manifest.yaml"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$TEST_HOME/.base.d/demo/.venv"* ]]
    [[ "$output" == *"PWD=$workspace/demo"* ]]
}

@test "basectl activate honors BASE_PROJECT_VENV_DIR override" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_python="$TEST_TMPDIR/custom-venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
EOF
    printf '#!/usr/bin/env bash\n' > "$project_python"
    chmod +x "$base_python" "$project_python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_PROJECT_VENV_DIR="$TEST_TMPDIR/custom-venv" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$TEST_TMPDIR/custom-venv"* ]]
}

@test "basectl default runtime shell preserves caller working directory" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_activate="$TEST_HOME/.base.d/base/.venv/bin/activate"
    local workspace="$TEST_TMPDIR/workspace"
    local caller="$TEST_TMPDIR/caller"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$workspace/base" "$caller"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "base" ]]; then
    printf 'base\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_ROOT=%s\n' "$BASE_PROJECT_ROOT"
printf 'PWD=%s\n' "$PWD"
EOF
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$TEST_HOME/.base.d/base/.venv" > "$project_activate"
    chmod +x "$base_python" "$fake_bash"
    printf 'project:\n  name: base\nartifacts: []\n' > "$workspace/base/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"
    caller="$(cd "$caller" && pwd -P)"

    run bash -c 'cd "$1" || exit 1; shift; exec "$@"' _ "$caller" \
        env \
            HOME="$TEST_HOME" \
            PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
            BASE_ACTIVATE_PRESERVE_CWD=1 \
            BASE_ACTIVATE_SHELL="$fake_bash" \
            BASE_TEST_PROJECT_ROOT="$workspace/base" \
            "$BASE_REPO_ROOT/bin/basectl" activate base

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$workspace/base"* ]]
    [[ "$output" == *"PWD=$caller"* ]]
}

@test "basectl activate prints help without requiring the Base Python venv" {
    run_basectl activate --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl activate <project> [options]"* ]]
}

@test "basectl activate reports missing project as a usage error" {
    run_basectl activate

    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"ERROR: Project name is required."* ]]
    [[ "$output" != *"FATAL"* ]]
    [[ "$output" != *"Encountered a fatal error"* ]]
}

@test "basectl activate reports invalid arguments as usage errors" {
    run_basectl activate --workspace
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--workspace' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl activate --unknown demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown activate option '--unknown'."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl activate demo extra
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: The 'activate' command accepts exactly one project name."* ]]
    [[ "$output" != *"FATAL"* ]]
}

@test "basectl rejects removed legacy commands" {
    local legacy_command

    for legacy_command in status run set-team set-shared-teams man embrace install shell; do
        run_basectl "$legacy_command"
        [ "$status" -eq 2 ]
        [[ "$output" == *"Unrecognized command: $legacy_command"* ]]
    done
}

@test "Base home verification does not require a git repository" {
    local base_home="$TEST_TMPDIR/embedded/base"

    mkdir -p \
        "$base_home/bin" \
        "$base_home/lib/shell" \
        "$base_home/lib/bash/runtime" \
        "$base_home/lib/bash/version" \
        "$base_home/cli/bash/commands/basectl"
    touch \
        "$base_home/VERSION" \
        "$base_home/base_init.sh" \
        "$base_home/lib/shell/bash_profile" \
        "$base_home/lib/shell/bashrc" \
        "$base_home/lib/shell/baserc_guard.sh" \
        "$base_home/lib/bash/runtime/bashrc" \
        "$base_home/lib/bash/version/lib_version.sh" \
        "$base_home/bin/basectl" \
        "$base_home/bin/base-wrapper" \
        "$base_home/cli/bash/commands/basectl/basectl.sh"

    run bash -c 'source "$1"; basectl_verify_home "$2"' _ \
        "$BASE_REPO_ROOT/cli/bash/commands/basectl/basectl.sh" \
        "$base_home"

    [ "$status" -eq 0 ]
}


@test "base-wrapper runs package commands in the selected project venv" {
    local python_bin="$TEST_HOME/.base.d/demo/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_HOME=%s\n' "$BASE_HOME"
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'PYTHONPATH=%s\n' "$PYTHONPATH"
printf 'ARGS=%s\n' "$*"
EOF
    chmod +x "$python_bin"

    run env \
        HOME="$TEST_HOME" \
        PYTHONPATH="existing" \
        "$BASE_REPO_ROOT/bin/base-wrapper" --project demo base_setup --dry-run demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"PYTHONPATH=$BASE_REPO_ROOT/lib/python:$BASE_REPO_ROOT/cli/python:existing"* ]]
    [[ "$output" == *"ARGS=-m base_setup --dry-run demo"* ]]
}


@test "basectl dispatches command implementations by command name" {
    run_basectl sort-in-place --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Sort text files in place."* ]]
}

@test "basectl treats path-like arguments as scripts before command names" {
    local script_path="$TEST_TMPDIR/sort-in-place"

    cat > "$script_path" <<'EOF'
main() {
    printf 'script path wins: %s\n' "$1"
}
EOF

    run_basectl "$script_path" arg1

    [ "$status" -eq 0 ]
    [[ "$output" == *"script path wins: arg1"* ]]
}

@test "sort-in-place launcher delegates through basectl" {
    local input_file="$TEST_TMPDIR/input.txt"

    printf 'b\na\nb\n' > "$input_file"
    run env \
        HOME="$TEST_HOME" \
        PATH="$BASE_REPO_ROOT/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        sort-in-place -u "$input_file"

    [ "$status" -eq 0 ]
    [ "$(cat "$input_file")" = $'a\nb' ]
}


@test "Base runtime shell prompt includes host, venv, and git segments" {
    local venv_dir="$TEST_TMPDIR/.venv"
    local mockbin="$TEST_TMPDIR/mockbin"

    mkdir -p "$venv_dir" "$mockbin"
    cat > "$mockbin/scutil" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--get" && "${2:-}" == "ComputerName" ]]; then
    printf '%s\n' "aadhara"
    exit 0
fi
if [[ "${1:-}" == "--get" && "${2:-}" == "LocalHostName" ]]; then
    printf '%s\n' "aadhara-local"
    exit 0
fi
exit 1
EOF
    chmod +x "$mockbin/scutil"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        VIRTUAL_ENV="$venv_dir" \
        PATH="$mockbin:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            printf "PS1=%s\n" "$PS1"; \
            printf "host=%s\n" "$(_base_runtime_host_prompt)"; \
            printf "venv=%s\n" "$(_base_runtime_venv_prompt)"; \
            cd "$BASE_HOME"; \
            printf "git=%s\n" "$(_base_runtime_git_prompt)"; \
            printf "disable=%s\n" "${VIRTUAL_ENV_DISABLE_PROMPT:-}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *'PS1=\T ${_BASE_RUNTIME_HOST_PROMPT:-unknown} ${BASE_PROJECT:+[$BASE_PROJECT] }$(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
    [[ "$output" == *"host=aadhara"* ]]
    [[ "$output" == *"venv=[.venv] "* ]]
    [[ "$output" == *"git=("* ]]
    [[ "$output" == *"disable=1"* ]]
}

@test "Base runtime shell activates project virtual environment" {
    local project_root="$TEST_TMPDIR/demo"
    local venv_dir="$TEST_TMPDIR/demo-venv"

    mkdir -p "$project_root/bin" "$venv_dir/bin"
    cat > "$venv_dir/bin/activate" <<'EOF'
VIRTUAL_ENV="$BASE_PROJECT_VENV_DIR"
PATH="$VIRTUAL_ENV/bin:$PATH"
export VIRTUAL_ENV PATH
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_PROJECT=demo \
        BASE_PROJECT_ROOT="$project_root" \
        BASE_PROJECT_VENV_DIR="$venv_dir" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            printf "BASE_PROJECT=%s\n" "$BASE_PROJECT"; \
            printf "VIRTUAL_ENV=%s\n" "$VIRTUAL_ENV"; \
            printf "PATH=%s\n" "$PATH"; \
            printf "PS1=%s\n" "$PS1"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"VIRTUAL_ENV=$venv_dir"* ]]
    [[ "$output" == *"PATH=$venv_dir/bin:$BASE_REPO_ROOT/bin:$project_root/bin:"* ]]
    [[ "$output" == *'PS1=\T ${_BASE_RUNTIME_HOST_PROMPT:-unknown} ${BASE_PROJECT:+[$BASE_PROJECT] }$(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
}


@test "Base runtime shell loads base_init before user bashrc and owns final prompt" {
    cat > "$TEST_HOME/.bashrc" <<'EOF'
alias user_bashrc_alias='printf user-bashrc'
export USER_BASHRC_LOADED=1
if declare -F import_base_lib >/dev/null 2>&1; then
    export USER_BASHRC_HAS_BASE_IMPORT=1
fi
PS1='user prompt: '
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c '\
            alias user_bashrc_alias; \
            printf "USER_BASHRC_LOADED=%s\n" "${USER_BASHRC_LOADED:-}"; \
            printf "USER_BASHRC_HAS_BASE_IMPORT=%s\n" "${USER_BASHRC_HAS_BASE_IMPORT:-}"; \
            printf "PS1=%s\n" "$PS1"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"alias user_bashrc_alias='printf user-bashrc'"* ]]
    [[ "$output" == *"USER_BASHRC_LOADED=1"* ]]
    [[ "$output" == *"USER_BASHRC_HAS_BASE_IMPORT=1"* ]]
    [[ "$output" == *'PS1=\T ${_BASE_RUNTIME_HOST_PROMPT:-unknown} ${BASE_PROJECT:+[$BASE_PROJECT] }$(_base_runtime_venv_prompt)$(_base_runtime_git_prompt)\w: '* ]]
}

@test "BASE_DEBUG traces Base runtime shell startup" {
    cat > "$TEST_HOME/.bashrc" <<'EOF'
export USER_BASHRC_LOADED=1
EOF

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_DEBUG=1 \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "ok\n"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG runtime: loading"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: sourcing '$BASE_REPO_ROOT/base_init.sh'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: sourcing '$TEST_HOME/.bashrc'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: complete"* ]]
}


@test "baserc can enable BASE_DEBUG for Base runtime shells" {
    printf '%s\n' 'BASE_DEBUG=1' > "$TEST_HOME/.baserc"

    run env -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "ok\n"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG runtime: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: loading"* ]]
    [[ "$output" == *"BASE_DEBUG runtime: complete"* ]]
}

@test "baserc cannot override BASE_HOME for Base runtime shells" {
    printf '%s\n' 'BASE_HOME=/tmp/not-base' > "$TEST_HOME/.baserc"

    run env -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" --rcfile "$BASE_REPO_ROOT/lib/bash/runtime/bashrc" -i -c 'printf "BASE_HOME=%s\n" "$BASE_HOME"; printf "BASE_BIN_DIR=%s\n" "${BASE_BIN_DIR-unset}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"ERROR: ~/.baserc must not set Base-owned variable 'BASE_HOME'."* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
    [[ "$output" == *"BASE_BIN_DIR=unset"* ]]
}
