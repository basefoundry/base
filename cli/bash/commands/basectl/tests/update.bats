#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl update prints help" {
    run_basectl update --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl update [project] [options]"* ]]
    [[ "$output" == *"Update a Base-managed project from Git, or update Base through Homebrew"* ]]
    [[ "$output" == *"When project is omitted, Base updates project 'base'."* ]]
    [[ "$output" == *"Tracked project files must be clean"* ]]
    [[ "$output" == *"brew upgrade basefoundry/base/base"* ]]
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
            base_update_has_untracked_files() { return 1; }
            base_update_subcommand_main --dry-run
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would update project 'base' repository at '$BASE_REPO_ROOT'."* ]]
    [[ "$output" == *"[DRY-RUN] Would run 'basectl setup base' after updating."* ]]
}

@test "basectl update dry-run resolves a named project" {
    local project_root="$TEST_TMPDIR/demo"

    mkdir -p "$project_root"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_PROJECT_ROOT="$project_root" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_resolve_project() { printf "demo\t%s\t%s\n" "$BASE_TEST_PROJECT_ROOT" "$BASE_TEST_PROJECT_ROOT/base_manifest.yaml"; }
            base_update_current_branch() { printf "%s\n" main; }
            base_update_default_branch() { printf "%s\n" main; }
            base_update_worktree_clean() { return 0; }
            base_update_has_untracked_files() { return 1; }
            base_update_subcommand_main --dry-run demo
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would update project 'demo' repository at '$project_root'."* ]]
    [[ "$output" == *"[DRY-RUN] Would run 'basectl setup demo' after updating."* ]]
}

@test "basectl update rejects multiple project arguments" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_subcommand_main demo other
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"The 'update' command accepts at most one project name."* ]]
}

@test "basectl update dry-run reports Homebrew handoff without running brew" {
    local fake_base="$TEST_TMPDIR/homebrew/opt/base/libexec"

    mkdir -p "$fake_base/bin"
    touch "$fake_base/bin/basectl"
    chmod +x "$fake_base/bin/basectl"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$fake_base" \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        bash -c '
            log_debug() { :; }
            log_error() { printf "ERROR: %s\n" "$*"; }
            log_info() { printf "INFO: %s\n" "$*"; }
            log_warn() { printf "WARN: %s\n" "$*"; }
            print_error() { printf "ERROR: %s\n" "$*"; }
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_run_homebrew_upgrade() { printf "brew should not run\n"; return 99; }
            base_update_run_homebrew_setup() { printf "setup should not run\n"; return 99; }
            base_update_subcommand_main --dry-run
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Detected Homebrew-managed Base install at '$fake_base'."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew upgrade basefoundry/base/base"* ]]
    [[ "$output" == *"[DRY-RUN] Would run 'basectl setup' after the Homebrew upgrade with inherited Base environment cleared."* ]]
    [[ "$output" != *"brew should not run"* ]]
    [[ "$output" != *"setup should not run"* ]]
}

@test "basectl update reports Homebrew tap trust recovery before upgrade" {
    local fake_bin="$TEST_TMPDIR/bin"
    local fake_base="$TEST_TMPDIR/homebrew/opt/base/libexec"
    local brew_log="$TEST_TMPDIR/brew.log"

    mkdir -p "$fake_bin" "$fake_base/bin"
    cat > "$fake_bin/brew" <<EOF
#!/usr/bin/env bash
case "\$1" in
    config)
        printf '%s\n' 'HOMEBREW_REQUIRE_TAP_TRUST: set'
        exit 0
        ;;
    trust)
        if [[ "\$2" == "--json" && "\$3" == "v1" ]]; then
            printf '%s\n' '{"taps":[],"formulae":["basefoundry/base/base"],"casks":[],"commands":[]}'
            exit 0
        fi
        ;;
esac
printf '%s\n' "\$*" >> "$brew_log"
exit 0
EOF
    chmod +x "$fake_bin/brew"
    touch "$fake_base/bin/basectl"
    chmod +x "$fake_base/bin/basectl"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$fake_base" \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -c '
            log_debug() { :; }
            log_error() { printf "ERROR: %s\n" "$*"; }
            log_info() { printf "INFO: %s\n" "$*"; }
            log_warn() { printf "WARN: %s\n" "$*"; }
            print_error() { printf "ERROR: %s\n" "$*"; }
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_subcommand_main
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"Homebrew requires trust for 'basefoundry/base' before upgrading Base's tap-owned Bash library dependency."* ]]
    [[ "$output" == *"Run 'brew trust basefoundry/base', then rerun 'basectl update'."* ]]
    [[ "$output" == *"brew trust --formula basefoundry/base/base-bash-libs"* ]]
    [[ ! -e "$brew_log" ]]
}

@test "basectl update runs exact Homebrew package upgrade and clears Base env for setup" {
    local fake_bin="$TEST_TMPDIR/bin"
    local fake_base="$TEST_TMPDIR/homebrew/opt/base/libexec"
    local brew_log="$TEST_TMPDIR/brew.log"
    local setup_log="$TEST_TMPDIR/setup.log"

    mkdir -p "$fake_bin" "$fake_base/bin"
    cat > "$fake_bin/brew" <<EOF
#!/usr/bin/env bash
if [[ "\$1" == "config" ]]; then
    exit 0
fi
printf '%s\n' "\$*" >> "$brew_log"
exit 0
EOF
    chmod +x "$fake_bin/brew"
    cat > "$fake_base/bin/basectl" <<EOF
#!/usr/bin/env bash
printf 'args=%s\n' "\$*" >> "$setup_log"
printf 'BASE_HOME=%s\n' "\${BASE_HOME-unset}" >> "$setup_log"
printf 'BASE_PROJECT=%s\n' "\${BASE_PROJECT-unset}" >> "$setup_log"
EOF
    chmod +x "$fake_base/bin/basectl"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$fake_base" \
        BASE_PROJECT=stale-project \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -c '
            log_debug() { :; }
            log_error() { printf "ERROR: %s\n" "$*"; }
            log_info() { printf "INFO: %s\n" "$*"; }
            log_warn() { printf "WARN: %s\n" "$*"; }
            print_error() { printf "ERROR: %s\n" "$*"; }
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [ "$(cat "$brew_log")" = "upgrade basefoundry/base/base" ]
    [[ "$(cat "$setup_log")" == *"args=setup"* ]]
    [[ "$(cat "$setup_log")" == *"BASE_HOME=unset"* ]]
    [[ "$(cat "$setup_log")" == *"BASE_PROJECT=unset"* ]]
    [[ "$output" == *"Detected Homebrew-managed Base install at '$fake_base'."* ]]
    [[ "$output" == *"Running Homebrew upgrade for basefoundry/base/base."* ]]
    [[ "$output" == *"Running basectl setup after Homebrew upgrade."* ]]
    [[ "$output" == *"Base update is complete."* ]]
}

@test "basectl update uses current Homebrew opt basectl after Cellar-launched upgrades" {
    local fake_bin="$TEST_TMPDIR/bin"
    local homebrew="$TEST_TMPDIR/homebrew"
    local cellar_base="$homebrew/Cellar/base/0.4.0/libexec"
    local opt_prefix="$homebrew/opt/base"
    local opt_base="$opt_prefix/libexec"
    local setup_log="$TEST_TMPDIR/setup.log"

    mkdir -p "$fake_bin" "$cellar_base/bin" "$opt_base/bin"
    touch "$cellar_base/bin/basectl"
    chmod +x "$cellar_base/bin/basectl"
    cat > "$fake_bin/brew" <<EOF
#!/usr/bin/env bash
if [[ "\$1" == "--prefix" ]]; then
    printf '%s\n' "$opt_prefix"
    exit 0
fi
exit 0
EOF
    chmod +x "$fake_bin/brew"
    cat > "$opt_base/bin/basectl" <<EOF
#!/usr/bin/env bash
printf 'opt-basectl args=%s\n' "\$*" >> "$setup_log"
printf 'BASE_HOME=%s\n' "\${BASE_HOME-unset}" >> "$setup_log"
EOF
    chmod +x "$opt_base/bin/basectl"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$cellar_base" \
        BASE_REPO_ROOT="$BASE_REPO_ROOT" \
        PATH="$fake_bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -c '
            log_debug() { :; }
            log_error() { printf "ERROR: %s\n" "$*"; }
            log_info() { printf "INFO: %s\n" "$*"; }
            log_warn() { printf "WARN: %s\n" "$*"; }
            print_error() { printf "ERROR: %s\n" "$*"; }
            source "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$(cat "$setup_log")" == *"opt-basectl args=setup"* ]]
    [[ "$(cat "$setup_log")" == *"BASE_HOME=unset"* ]]
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
            base_update_source_git_library() { printf "git library should not load\n"; return 99; }
            git_update_repo() { printf "git update should not run\n"; return 99; }
            base_update_run_setup() { printf "setup should not run\n"; return 99; }
            base_update_subcommand_main
        '

    [ "$status" -eq 1 ]
    [[ "$output" == *"Project 'base' repository has tracked local changes."* ]]
    [[ "$output" != *"git library should not load"* ]]
    [[ "$output" != *"git update should not run"* ]]
    [[ "$output" != *"setup should not run"* ]]
}

@test "basectl update allows untracked files before pulling" {
    local repo="$TEST_TMPDIR/repo"

    init_git_repo "$repo"
    repo="$(cd "$repo" && pwd -P)"
    printf 'base\n' > "$repo/README.md"
    commit_all "$repo" "Initial commit"
    cp "$BASE_REPO_ROOT/base_init.sh" "$repo/base_init.sh"
    cp -R "$BASE_REPO_ROOT/cli" "$repo/cli"
    cp -R "$BASE_REPO_ROOT/lib" "$repo/lib"
    copy_base_bash_libs_fixture "$TEST_TMPDIR/base-bash-libs/lib/bash"
    mkdir -p "$repo/bin"
    printf 'notes\n' > "$repo/local-notes.md"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$repo" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_source_git_library() { :; }
            git_update_repo() { printf "git update repo=%s branch=%s\n" "$1" "$3"; }
            base_update_head_revision() { printf "%s\n" abc1234; }
            base_update_run_setup() { printf "setup ran\n"; }
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Project 'base' repository has untracked files. Continuing because tracked files are clean."* ]]
    [[ "$output" == *"git update repo=$repo branch=master"* ]]
    [[ "$output" == *"setup ran"* ]]
    [[ "$output" == *"Project 'base' update is complete."* ]]
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
    [[ "$output" == *"Project 'base' update only runs on default branch 'main'; current branch is 'feature/example'."* ]]
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
            base_update_has_untracked_files() { return 1; }
            base_update_source_git_library() { :; }
            git_update_repo() { printf "git update repo=%s branch=%s\n" "$1" "$3"; }
            base_update_head_revision() { printf "%s\n" abc1234; }
            base_update_run_setup() { printf "setup ran\n"; }
            base_update_subcommand_main
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Updating project 'base' repository at '$BASE_REPO_ROOT'."* ]]
    [[ "$output" == *"Project 'base' repository is already up to date on 'master' at 'abc1234'."* ]]
    [[ "$output" == *"Running basectl setup base after update."* ]]
    [[ "$output" == *"setup ran"* ]]
    [[ "$output" == *"Project 'base' update is complete."* ]]
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
            base_update_has_untracked_files() { return 1; }
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
    [[ "$output" == *"Project 'base' repository updated from 'old1234' to 'new5678' on 'main'."* ]]
    [[ "$output" == *"setup ran"* ]]
    [[ "$output" == *"Project 'base' update is complete."* ]]
}

@test "basectl update runs Git update and setup for a named project" {
    local project_root="$TEST_TMPDIR/demo"

    mkdir -p "$project_root"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_TEST_PROJECT_ROOT="$project_root" \
        BASE_TEST_AFTER_UPDATE="$TEST_TMPDIR/after-update" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update.sh"
            base_update_resolve_project() { printf "demo\t%s\t%s\n" "$BASE_TEST_PROJECT_ROOT" "$BASE_TEST_PROJECT_ROOT/base_manifest.yaml"; }
            base_update_current_branch() { printf "%s\n" main; }
            base_update_default_branch() { printf "%s\n" main; }
            base_update_worktree_clean() { return 0; }
            base_update_has_untracked_files() { return 1; }
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
            base_update_run_setup() { printf "setup project=%s\n" "$2"; }
            base_update_subcommand_main demo
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"Updating project 'demo' repository at '$project_root'."* ]]
    [[ "$output" == *"git update repo=$project_root branch=main"* ]]
    [[ "$output" == *"Project 'demo' repository updated from 'old1234' to 'new5678' on 'main'."* ]]
    [[ "$output" == *"Running basectl setup demo after update."* ]]
    [[ "$output" == *"setup project=demo"* ]]
    [[ "$output" == *"Project 'demo' update is complete."* ]]
}
