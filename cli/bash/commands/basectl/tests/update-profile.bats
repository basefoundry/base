#!/usr/bin/env bats

load ./setup_helpers.bash

create_fake_shell_base() {
    local fake_base="$1"

    mkdir -p "$fake_base/bin" "$fake_base/lib/shell"
    touch "$fake_base/base_init.sh"
    cp "$BASE_REPO_ROOT/lib/shell/bashrc" "$fake_base/lib/shell/bashrc"
    cp "$BASE_REPO_ROOT/lib/shell/zshrc" "$fake_base/lib/shell/zshrc"
    cp "$BASE_REPO_ROOT/lib/shell/baserc_guard.sh" "$fake_base/lib/shell/baserc_guard.sh"
    cp "$BASE_REPO_ROOT/lib/shell/zsh_baserc_guard.zsh" "$fake_base/lib/shell/zsh_baserc_guard.zsh"
    cp "$BASE_REPO_ROOT/lib/shell/base_platform_tools.sh" "$fake_base/lib/shell/base_platform_tools.sh"
    cat > "$fake_base/bin/basectl" <<'EOF'
#!/usr/bin/env bash
printf 'fake basectl\n'
EOF
    chmod +x "$fake_base/bin/basectl"
}

create_fake_platform_tools() {
    local platform_tools_home="$1"

    mkdir -p "$platform_tools_home/bin"
    touch "$platform_tools_home/base_manifest.yaml"
    cat > "$platform_tools_home/bin/caff" <<'EOF'
#!/usr/bin/env bash
printf 'fake caff\n'
EOF
    chmod +x "$platform_tools_home/bin/caff"
}


@test "basectl update-profile creates Base-managed sections in all shell dotfiles" {
    run_base_command update-profile

    [ "$status" -eq 0 ]
    [[ "$output" == *"Updating '$TEST_HOME/.bash_profile'"* ]]
    [[ "$output" == *"Updating '$TEST_HOME/.bashrc'"* ]]

    for dotfile in .bash_profile .bashrc .zprofile .zshrc; do
        [ -f "$TEST_HOME/$dotfile" ]
        [[ "$(cat "$TEST_HOME/$dotfile")" != *"export BASE_HOME"* ]]
        [[ "$(cat "$TEST_HOME/$dotfile")" != *"base_init.sh"* ]]
    done

    [[ "$(cat "$TEST_HOME/.bash_profile")" == *"# >>> base: bash_profile managed >>>"* ]]
    [[ "$(cat "$TEST_HOME/.bash_profile")" == *"source \"$BASE_REPO_ROOT/lib/shell/bash_profile\""* ]]
    [[ "$(cat "$TEST_HOME/.bash_profile")" == *"Local edits inside this block may be overwritten."* ]]
    [[ "$(cat "$TEST_HOME/.bash_profile")" == *"Refresh with: basectl update-profile"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *"# >>> base: bashrc managed >>>"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *"source \"$BASE_REPO_ROOT/lib/shell/bashrc\""* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" != *"basectl_completion"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" != *"PATH="* ]]
    [[ "$(cat "$TEST_HOME/.zprofile")" == *"# >>> base: zprofile managed >>>"* ]]
    [[ "$(cat "$TEST_HOME/.zprofile")" == *"source \"$BASE_REPO_ROOT/lib/shell/zprofile\""* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" == *"# >>> base: zshrc managed >>>"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" == *"source \"$BASE_REPO_ROOT/lib/shell/zshrc\""* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" != *"basectl_completion"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" != *"PATH="* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_PROFILE_VERSION=1"* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_BASH_DEFAULTS=false"* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_ZSH_DEFAULTS=false"* ]]
}

@test "basectl update-profile writes stable Homebrew opt-style paths" {
    local cellar_parent="$TEST_TMPDIR/homebrew/Cellar/base/0.4.0"
    local opt_dir="$TEST_TMPDIR/homebrew/opt"
    local opt_base="$opt_dir/base/libexec"

    mkdir -p "$cellar_parent" "$opt_dir"
    ln -s "$BASE_REPO_ROOT" "$cellar_parent/libexec"
    ln -s "../Cellar/base/0.4.0" "$opt_dir/base"

    run env \
        -u BASE_BIN_DIR \
        -u BASE_CLI_DIR \
        -u BASE_BASH_DIR \
        -u BASE_BASH_COMMANDS_DIR \
        -u BASE_LIB_DIR \
        -u BASE_BASH_LIB_DIR \
        -u BASE_SHELL_DIR \
        -u BASE_OS \
        -u BASE_HOST \
        -u BASE_SHELL \
        HOME="$TEST_HOME" \
        BASE_HOME="$opt_base" \
        PATH="$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$TEST_BASH_BIN_DIR/bash" -c '\
            source "$BASE_HOME/base_init.sh"; \
            source "$BASE_HOME/cli/bash/commands/basectl/basectl.sh"; \
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/update_profile.sh"; \
            base_update_profile_subcommand_main'

    [ "$status" -eq 0 ]
    [[ "$(cat "$TEST_HOME/.bash_profile")" == *"source \"$opt_base/lib/shell/bash_profile\""* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *"source \"$opt_base/lib/shell/bashrc\""* ]]
    [[ "$(cat "$TEST_HOME/.zprofile")" == *"source \"$opt_base/lib/shell/zprofile\""* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" == *"source \"$opt_base/lib/shell/zshrc\""* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" != *"/Cellar/base/0.4.0"* ]]
}

@test "basectl update-profile explains BASE_HOME mismatch recovery" {
    local runtime_base="$TEST_TMPDIR/runtime-base"
    local resolved_base="$TEST_TMPDIR/resolved-base"

    mkdir -p "$runtime_base" "$resolved_base"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$runtime_base" \
        PATH="$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$TEST_BASH_BIN_DIR/bash" -c '\
            base_repo_root="$1"; \
            resolved_base="$2"; \
            source "$base_repo_root/base_init.sh"; \
            source "$base_repo_root/cli/bash/commands/basectl/basectl.sh"; \
            source "$base_repo_root/cli/bash/commands/basectl/subcommands/update_profile.sh"; \
            basectl_runtime_base_home() { printf "%s\n" "$resolved_base"; }; \
            base_update_profile_subcommand_main' \
        bash "$BASE_REPO_ROOT" "$resolved_base"

    [ "$status" -eq 1 ]
    [[ "$output" == *"ERROR: Resolved Base home '$resolved_base' does not match runtime BASE_HOME '$runtime_base'."* ]]
    [[ "$output" == *"This command must be invoked through the Base dispatcher, not directly."* ]]
    [[ "$output" == *"Fix: unset BASE_HOME and run 'basectl update-profile' through the installed 'basectl' binary."* ]]
}

@test "basectl update-profile preserves non-Base dotfile content and is idempotent" {
    printf '%s
' 'user line before' > "$TEST_HOME/.bashrc"

    run_base_command update-profile
    [ "$status" -eq 0 ]

    run_base_command update-profile
    [ "$status" -eq 0 ]

    [[ "$output" != *"Updating '$TEST_HOME/.bash_profile'"* ]]
    [[ "$output" != *"Updating '$TEST_HOME/.bashrc'"* ]]
    [[ "$output" != *"Updating '$TEST_HOME/.zprofile'"* ]]
    [[ "$output" != *"Updating '$TEST_HOME/.zshrc'"* ]]
    [ "$(grep -c '# >>> base: bashrc managed >>>' "$TEST_HOME/.bashrc")" -eq 1 ]
    [ "$(grep -c '# <<< base: bashrc managed <<<' "$TEST_HOME/.bashrc")" -eq 1 ]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *"user line before"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *$'user line before

# >>> base: bashrc managed >>>'* ]]
}

@test "basectl update-profile makes basectl available in interactive Bash without runtime bootstrap" {
    run_base_command update-profile
    [ "$status" -eq 0 ]

    run env -u BASE_HOME -u BASE_HOST -u BASE_OS \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$TEST_HOME/.bashrc" -i -c 'command -v basectl; printf "BASE_HOME=%s\n" "${BASE_HOME-unset}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"$BASE_REPO_ROOT/bin/basectl"* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
}

@test "Base-managed Bash startup preserves Homebrew opt-style symlink paths" {
    local cellar_base="$TEST_TMPDIR/homebrew/Cellar/base/0.4.0/libexec"
    local opt_dir="$TEST_TMPDIR/homebrew/opt"
    local opt_base="$opt_dir/base/libexec"

    mkdir -p "$opt_dir"
    create_fake_shell_base "$cellar_base"
    ln -s "../Cellar/base/0.4.0" "$opt_dir/base"

    run env -u BASE_HOME -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$opt_base/lib/shell/bashrc" -i -c '\
            printf "BASE_HOME=%s\n" "$BASE_HOME"; \
            printf "BASE_BIN=%s\n" "$(command -v basectl)"; \
            printf "PATH=%s\n" "$PATH"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$opt_base"* ]]
    [[ "$output" == *"BASE_BIN=$opt_base/bin/basectl"* ]]
    [[ "$output" == *"PATH=$opt_base/bin:/usr/bin:/bin:/usr/sbin:/sbin"* ]]
}

@test "Base-managed Bash startup explains stale readonly BASE_HOME recovery" {
    local old_base="$TEST_TMPDIR/homebrew/Cellar/base/0.3.0/libexec"
    local cellar_base="$TEST_TMPDIR/homebrew/Cellar/base/0.4.1/libexec"
    local opt_dir="$TEST_TMPDIR/homebrew/opt"
    local opt_base="$opt_dir/base/libexec"

    mkdir -p "$old_base" "$opt_dir"
    create_fake_shell_base "$cellar_base"
    ln -s "../Cellar/base/0.4.1" "$opt_dir/base"

    run env -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -i -c '\
            readonly BASE_HOME="$1"; \
            source "$2"' \
        bash "$old_base" "$opt_base/lib/shell/bashrc"

    [ "$status" -eq 1 ]
    [[ "$output" == *"ERROR: BASE_HOME is readonly and points at '$old_base', not '$opt_base'."* ]]
    [[ "$output" == *"exec env -u BASE_HOME \\"* ]]
    [[ "$output" == *"-u BASE_PROJECT_VENV_DIR \\"* ]]
    [[ "$output" == *'"$SHELL" -l'* ]]
    [[ "$output" != *"ERROR:   exec env"* ]]
}

@test "Base-managed Bash startup skips mismatched snippet inside active Base runtime" {
    local runtime_base="$TEST_TMPDIR/homebrew/Cellar/base/1.0.2/libexec"
    local source_base="$TEST_TMPDIR/work/base"

    create_fake_shell_base "$runtime_base"
    create_fake_shell_base "$source_base"

    run env -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash -i -c '\
            readonly BASE_HOME="$1"; \
            export BASE_SHELL=1; \
            source "$2"; \
            printf "BASE_HOME=%s\n" "$BASE_HOME"' \
        bash "$runtime_base" "$source_base/lib/shell/bashrc"

    [ "$status" -eq 0 ]
    [[ "$output" == *"INFO: This shell is already running Base from '$runtime_base'; skipping Base profile snippet for '$source_base'."* ]]
    [[ "$output" == *"BASE_HOME=$runtime_base"* ]]
    [[ "$output" != *"Run basectl update-profile"* ]]
    [[ "$output" != *"Start a fresh shell without stale Base runtime variables"* ]]
}

@test "Base-managed Bash startup detects sibling Base Platform Tools without profile rewrite" {
    local workspace="$TEST_TMPDIR/fake-workspace"
    local fake_base="$workspace/base"
    local fake_platform_tools="$workspace/base-platform-tools"

    create_fake_shell_base "$fake_base"
    create_fake_platform_tools "$fake_platform_tools"
    fake_base="$(cd "$fake_base" && pwd -P)"
    fake_platform_tools="$(cd "$fake_platform_tools" && pwd -P)"

    run env -u BASE_HOME -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$fake_base/lib/shell/bashrc" -i -c '\
            printf "BASE_HOME=%s\n" "$BASE_HOME"; \
            printf "BASE_PLATFORM_TOOLS_HOME=%s\n" "$BASE_PLATFORM_TOOLS_HOME"; \
            printf "BASE_PLATFORM_TOOLS_BIN_DIR=%s\n" "$BASE_PLATFORM_TOOLS_BIN_DIR"; \
            printf "PATH=%s\n" "$PATH"; \
            printf "CAFF=%s\n" "$(command -v caff)"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$fake_base"* ]]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_HOME=$fake_platform_tools"* ]]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_BIN_DIR=$fake_platform_tools/bin"* ]]
    [[ "$output" == *"PATH=$fake_base/bin:$fake_platform_tools/bin:/usr/bin:/bin:/usr/sbin:/sbin"* ]]
    [[ "$output" == *"CAFF=$fake_platform_tools/bin/caff"* ]]
}

@test "Base-managed Bash startup leaves platform tools unset when sibling repo is absent" {
    local workspace="$TEST_TMPDIR/fake-workspace"
    local fake_base="$workspace/base"

    create_fake_shell_base "$fake_base"
    fake_base="$(cd "$fake_base" && pwd -P)"

    run env -u BASE_HOME -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$fake_base/lib/shell/bashrc" -i -c '\
            printf "BASE_PLATFORM_TOOLS_HOME=%s\n" "${BASE_PLATFORM_TOOLS_HOME-unset}"; \
            printf "BASE_PLATFORM_TOOLS_BIN_DIR=%s\n" "${BASE_PLATFORM_TOOLS_BIN_DIR-unset}"; \
            printf "PATH=%s\n" "$PATH"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_HOME=unset"* ]]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_BIN_DIR=unset"* ]]
    [[ "$output" == *"PATH=$fake_base/bin:/usr/bin:/bin:/usr/sbin:/sbin"* ]]
    [[ "$output" != *"base-platform-tools/bin"* ]]
}

@test "Base-managed Bash startup orders Base before platform tools and removes duplicates" {
    local workspace="$TEST_TMPDIR/fake-workspace"
    local fake_base="$workspace/base"
    local fake_platform_tools="$workspace/base-platform-tools"

    create_fake_shell_base "$fake_base"
    create_fake_platform_tools "$fake_platform_tools"
    fake_base="$(cd "$fake_base" && pwd -P)"
    fake_platform_tools="$(cd "$fake_platform_tools" && pwd -P)"

    run env -u BASE_HOME -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        PATH="$fake_platform_tools/bin:$fake_base/bin:/usr/bin:/bin:$fake_platform_tools/bin:$fake_base/bin" \
        bash --rcfile "$fake_base/lib/shell/bashrc" -i -c 'printf "PATH=%s\n" "$PATH"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"PATH=$fake_base/bin:$fake_platform_tools/bin:/usr/bin:/bin"* ]]
}

@test "BASE_DEBUG traces Base-managed Bash startup" {
    local base_only_trace
    local platform_tools_trace

    base_only_trace="BASE_DEBUG bashrc: prepended '$BASE_REPO_ROOT/bin' to PATH"
    platform_tools_trace="BASE_DEBUG bashrc: configured PATH with '$BASE_REPO_ROOT/bin' and "

    run_base_command update-profile
    [ "$status" -eq 0 ]

    run env -u BASE_HOME -u BASE_HOST -u BASE_OS \
        HOME="$TEST_HOME" \
        BASE_DEBUG=1 \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$TEST_HOME/.bashrc" -i -c 'command -v basectl >/dev/null'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG bashrc: loading"* ]]
    [[ "$output" == *"BASE_DEBUG bashrc: BASE_HOME=$BASE_REPO_ROOT"* ]]
    [[ "$output" == *"$base_only_trace"* || "$output" == *"$platform_tools_trace"* ]]
    [[ "$output" == *"BASE_DEBUG bashrc: complete"* ]]
}

@test "baserc can enable BASE_DEBUG for Base-managed Bash startup" {
    run_base_command update-profile
    [ "$status" -eq 0 ]

    printf '%s\n' 'BASE_DEBUG=1' > "$TEST_HOME/.baserc"
    run env -u BASE_HOME -u BASE_HOST -u BASE_OS -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$TEST_HOME/.bashrc" -i -c 'command -v basectl >/dev/null'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG bashrc: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"BASE_DEBUG bashrc: loading"* ]]
    [[ "$output" == *"BASE_DEBUG bashrc: complete"* ]]
}

@test "Bash profile bridge shares the baserc guard with bashrc" {
    run_base_command update-profile
    [ "$status" -eq 0 ]

    printf '%s\n' 'BASE_DEBUG=1' > "$TEST_HOME/.baserc"
    run env -u BASE_HOME -u BASE_HOST -u BASE_OS -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --norc -i -c 'source "$HOME/.bash_profile"; command -v basectl; printf "BASE_HOME=%s\n" "${BASE_HOME-unset}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG bash_profile: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"BASE_DEBUG bash_profile: sourcing '$TEST_HOME/.bashrc'"* ]]
    [[ "$output" == *"BASE_DEBUG bashrc: loading"* ]]
    [[ "$output" != *"BASE_DEBUG bashrc: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"$BASE_REPO_ROOT/bin/basectl"* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
}

@test "Zsh profile and zshrc share the baserc guard" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    run_base_command update-profile
    [ "$status" -eq 0 ]

    printf '%s\n' 'BASE_DEBUG=1' > "$TEST_HOME/.baserc"
    run env -u BASE_HOME -u BASE_HOST -u BASE_OS -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c 'source "$HOME/.zprofile"; source "$HOME/.zshrc"; command -v basectl; printf "BASE_HOME=%s\n" "${BASE_HOME-unset}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_DEBUG zprofile: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"BASE_DEBUG zprofile: loading"* ]]
    [[ "$output" == *"BASE_DEBUG zshrc: loading"* ]]
    [[ "$output" != *"BASE_DEBUG zshrc: sourced '$TEST_HOME/.baserc'"* ]]
    [[ "$output" == *"$BASE_REPO_ROOT/bin/basectl"* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
}

@test "baserc cannot override BASE_HOME for Base-managed Bash startup" {
    run_base_command update-profile
    [ "$status" -eq 0 ]

    printf '%s\n' 'BASE_HOME=/tmp/not-base' > "$TEST_HOME/.baserc"
    run env -u BASE_HOME -u BASE_HOST -u BASE_OS -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$TEST_HOME/.bashrc" -i -c 'printf "BASE_HOME=%s\n" "${BASE_HOME-unset}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"ERROR: ~/.baserc must not set Base-owned variable 'BASE_HOME'."* ]]
    [[ "$output" == *"BASE_HOME=unset"* ]]
}

@test "Bash baserc guard protects Base-owned runtime path variables" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/lib/shell/baserc_guard.sh"
            base_baserc_guard_owned_vars
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_BASH_DIR"* ]]
    [[ "$output" == *"BASE_BASH_COMMANDS_DIR"* ]]
    [[ "$output" == *"BASE_BASH_COMMAND_SCRIPT"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR"* ]]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_HOME"* ]]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_BIN_DIR"* ]]
    [[ "$output" != *"BASE_ARCH"* ]]
}

@test "basectl update-profile makes basectl available in interactive Zsh without runtime bootstrap" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    run_base_command update-profile
    [ "$status" -eq 0 ]

    run env -u BASE_HOME -u BASE_HOST -u BASE_OS \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c 'source "$HOME/.zshrc"; command -v basectl; printf "BASE_HOME=%s\n" "${BASE_HOME-unset}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"$BASE_REPO_ROOT/bin/basectl"* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
}

@test "Base-managed Zsh startup preserves Homebrew opt-style symlink paths" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    local cellar_base="$TEST_TMPDIR/homebrew/Cellar/base/0.4.0/libexec"
    local opt_dir="$TEST_TMPDIR/homebrew/opt"
    local opt_base="$opt_dir/base/libexec"

    mkdir -p "$opt_dir"
    create_fake_shell_base "$cellar_base"
    ln -s "../Cellar/base/0.4.0" "$opt_dir/base"

    run env -u BASE_HOME -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c 'source "$1"; printf "BASE_HOME=%s\n" "$BASE_HOME"; printf "BASE_BIN=%s\n" "$(command -v basectl)"; printf "PATH=%s\n" "$PATH"' \
        zsh "$opt_base/lib/shell/zshrc"

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$opt_base"* ]]
    [[ "$output" == *"BASE_BIN=$opt_base/bin/basectl"* ]]
    [[ "$output" == *"PATH=$opt_base/bin:/usr/bin:/bin:/usr/sbin:/sbin"* ]]
}

@test "Base-managed Zsh startup detects sibling Base Platform Tools without profile rewrite" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    local workspace="$TEST_TMPDIR/fake-workspace"
    local fake_base="$workspace/base"
    local fake_platform_tools="$workspace/base-platform-tools"

    create_fake_shell_base "$fake_base"
    create_fake_platform_tools "$fake_platform_tools"
    fake_base="$(cd "$fake_base" && pwd -P)"
    fake_platform_tools="$(cd "$fake_platform_tools" && pwd -P)"

    run env -u BASE_HOME -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c 'source "$1"; printf "BASE_HOME=%s\n" "$BASE_HOME"; printf "BASE_PLATFORM_TOOLS_BIN_DIR=%s\n" "$BASE_PLATFORM_TOOLS_BIN_DIR"; printf "PATH=%s\n" "$PATH"; printf "CAFF=%s\n" "$(command -v caff)"' \
        zsh "$fake_base/lib/shell/zshrc"

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_HOME=$fake_base"* ]]
    [[ "$output" == *"BASE_PLATFORM_TOOLS_BIN_DIR=$fake_platform_tools/bin"* ]]
    [[ "$output" == *"PATH=$fake_base/bin:$fake_platform_tools/bin:/usr/bin:/bin:/usr/sbin:/sbin"* ]]
    [[ "$output" == *"CAFF=$fake_platform_tools/bin/caff"* ]]
}

@test "baserc cannot override BASE_HOME for Base-managed Zsh startup" {
    command -v zsh >/dev/null 2>&1 || skip "zsh is not available"

    run_base_command update-profile
    [ "$status" -eq 0 ]

    printf '%s\n' 'BASE_HOME=/tmp/not-base' > "$TEST_HOME/.baserc"
    run env -u BASE_HOME -u BASE_HOST -u BASE_OS -u BASE_DEBUG \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        zsh -f -i -c 'source "$HOME/.zshrc"; printf "BASE_HOME=%s\n" "${BASE_HOME-unset}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"ERROR: ~/.baserc must not set Base-owned variable 'BASE_HOME'."* ]]
    [[ "$output" == *"BASE_HOME=unset"* ]]
}

@test "basectl update-profile --dry-run does not create dotfiles" {
    run_base_command update-profile --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would update '$TEST_HOME/.base.d/profile.conf'"* ]]
    [[ "$output" == *"[DRY-RUN] Would update '$TEST_HOME/.bash_profile'"* ]]
    [[ "$output" == *"[DRY-RUN] Would update '$TEST_HOME/.bashrc'"* ]]
    [ ! -e "$TEST_HOME/.base.d/profile.conf" ]
    [ ! -e "$TEST_HOME/.bash_profile" ]
    [ ! -e "$TEST_HOME/.bashrc" ]
    [ ! -e "$TEST_HOME/.zprofile" ]
    [ ! -e "$TEST_HOME/.zshrc" ]
}

@test "basectl update-profile --defaults enables defaults through profile config" {
    run_base_command update-profile --defaults

    [ "$status" -eq 0 ]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_BASH_DEFAULTS=true"* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_ZSH_DEFAULTS=true"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" != *"defaults.sh"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" != *"defaults.sh"* ]]

    run env -u BASE_HOME -u BASE_HOST -u BASE_OS -u EDITOR -u VISUAL -u EXINIT \
        -u HISTCONTROL -u HISTSIZE -u HISTFILESIZE \
        -u PAGER -u LESS -u MANPAGER -u GIT_PAGER \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$TEST_HOME/.bashrc" -i -c 'alias cp; printf "EDITOR=%s\n" "$EDITOR"; printf "VISUAL=%s\n" "$VISUAL"; printf "EXINIT=%s\n" "$EXINIT"; printf "PAGER=%s\n" "$PAGER"; printf "LESS=%s\n" "$LESS"; printf "MANPAGER=%s\n" "$MANPAGER"; printf "GIT_PAGER=%s\n" "$GIT_PAGER"; bind -v | grep -q "^set completion-ignore-case on$" && printf "completion_ignore_case=enabled\n"; bind -v | grep -q "^set show-all-if-ambiguous on$" && printf "show_all_if_ambiguous=enabled\n"; bind -v | grep -q "^set mark-symlinked-directories on$" && printf "mark_symlinked_directories=enabled\n"; printf "HISTCONTROL=%s\n" "$HISTCONTROL"; printf "HISTSIZE=%s\n" "$HISTSIZE"; printf "HISTFILESIZE=%s\n" "$HISTFILESIZE"; shopt -q checkwinsize && printf "checkwinsize=enabled\n"; shopt -q cmdhist && printf "cmdhist=enabled\n"; shopt -q lithist && printf "lithist=enabled\n"; printf "BASE_HOME=%s\n" "$BASE_HOME"; cd "$BASE_HOME"; printf "git=%s\n" "$(_base_bash_defaults_git_prompt)"; printf "PS1=%s\n" "$PS1"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"alias cp='cp -i'"* ]]
    [[ "$output" == *"EDITOR=vi"* ]]
    [[ "$output" == *"VISUAL=vi"* ]]
    [[ "$output" == *"EXINIT=set ts=4 sw=4 ai nows nosm expandtab"* ]]
    [[ "$output" == *"PAGER=less"* ]]
    [[ "$output" == *"LESS=-FRX"* ]]
    [[ "$output" == *"MANPAGER=less -R"* ]]
    [[ "$output" == *"GIT_PAGER=less -FRX"* ]]
    [[ "$output" == *"completion_ignore_case=enabled"* ]]
    [[ "$output" == *"show_all_if_ambiguous=enabled"* ]]
    [[ "$output" == *"mark_symlinked_directories=enabled"* ]]
    [[ "$output" == *"HISTCONTROL=ignoreboth:erasedups"* ]]
    [[ "$output" == *"HISTSIZE=10000"* ]]
    [[ "$output" == *"HISTFILESIZE=20000"* ]]
    [[ "$output" == *"checkwinsize=enabled"* ]]
    [[ "$output" == *"cmdhist=enabled"* ]]
    [[ "$output" == *"lithist=enabled"* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
    [[ "$output" == *"git=("* ]]
    [[ "$output" == *'PS1=\[\033[0;35m\]\T \h\[\033[0;33m\] $(_base_bash_defaults_git_prompt)\w\[\033[00m\]: '* ]]

    if command -v zsh >/dev/null 2>&1; then
        run env -u BASE_HOME -u BASE_HOST -u BASE_OS -u EDITOR -u VISUAL -u EXINIT \
            -u HISTFILE -u HISTSIZE -u SAVEHIST \
            -u PAGER -u LESS -u MANPAGER -u GIT_PAGER \
            HOME="$TEST_HOME" \
            PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
            zsh -f -i -c 'source "$HOME/.zshrc"; printf "PAGER=%s\n" "$PAGER"; printf "LESS=%s\n" "$LESS"; printf "MANPAGER=%s\n" "$MANPAGER"; printf "GIT_PAGER=%s\n" "$GIT_PAGER"; zstyle -s ":completion:*" matcher-list matcher_list && printf "matcher_list=%s\n" "$matcher_list"; zstyle -s ":completion:*" menu completion_menu && printf "completion_menu=%s\n" "$completion_menu"; printf "HISTFILE=%s\n" "$HISTFILE"; printf "HISTSIZE=%s\n" "$HISTSIZE"; printf "SAVEHIST=%s\n" "$SAVEHIST"; setopt | grep -q "^extendedhistory$" && printf "extended_history=enabled\n"; setopt | grep -q "^histignorespace$" && printf "hist_ignore_space=enabled\n"; setopt | grep -q "^histreduceblanks$" && printf "hist_reduce_blanks=enabled\n"; setopt | grep -q "^histexpiredupsfirst$" && printf "hist_expire_dups_first=enabled\n"; setopt | grep -q "^histsavenodups$" && printf "hist_save_no_dups=enabled\n"; setopt | grep -q "^histfindnodups$" && printf "hist_find_no_dups=enabled\n"; setopt | grep -q "^histverify$" && printf "hist_verify=enabled\n"; setopt | grep -q "^interactivecomments$" && printf "interactive_comments=enabled\n"; setopt | grep -q "^nobeep$" && printf "no_beep=enabled\n"; cd "$BASE_HOME"; printf "git=%s\n" "$(_base_zsh_defaults_git_prompt)"; printf "PROMPT=%s\n" "$PROMPT"; setopt | grep -q "^promptsubst$"; printf "prompt_subst=enabled\n"'

        [ "$status" -eq 0 ]
        [[ "$output" == *"PAGER=less"* ]]
        [[ "$output" == *"LESS=-FRX"* ]]
        [[ "$output" == *"MANPAGER=less -R"* ]]
        [[ "$output" == *"GIT_PAGER=less -FRX"* ]]
        [[ "$output" == *"matcher_list=m:{a-zA-Z}={A-Za-z}"* ]]
        [[ "$output" == *"completion_menu=select"* ]]
        [[ "$output" == *"HISTFILE=$TEST_HOME/.zsh_history"* ]]
        [[ "$output" == *"HISTSIZE=10000"* ]]
        [[ "$output" == *"SAVEHIST=10000"* ]]
        [[ "$output" == *"extended_history=enabled"* ]]
        [[ "$output" == *"hist_ignore_space=enabled"* ]]
        [[ "$output" == *"hist_reduce_blanks=enabled"* ]]
        [[ "$output" == *"hist_expire_dups_first=enabled"* ]]
        [[ "$output" == *"hist_save_no_dups=enabled"* ]]
        [[ "$output" == *"hist_find_no_dups=enabled"* ]]
        [[ "$output" == *"hist_verify=enabled"* ]]
        [[ "$output" == *"interactive_comments=enabled"* ]]
        [[ "$output" == *"no_beep=enabled"* ]]
        [[ "$output" == *"git=("* ]]
        [[ "$output" == *'PROMPT=%* %m $(_base_zsh_defaults_git_prompt)%1~: '* ]]
        [[ "$output" == *"prompt_subst=enabled"* ]]
    fi
}

@test "basectl update-profile preserves an existing defaults preference" {
    run_base_command update-profile --defaults
    [ "$status" -eq 0 ]

    run_base_command update-profile
    [ "$status" -eq 0 ]

    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_BASH_DEFAULTS=true"* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_ZSH_DEFAULTS=true"* ]]
}

@test "basectl update-profile --no-defaults disables existing defaults preference" {
    run_base_command update-profile --defaults
    [ "$status" -eq 0 ]

    run_base_command update-profile --no-defaults
    [ "$status" -eq 0 ]

    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_BASH_DEFAULTS=false"* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_ZSH_DEFAULTS=false"* ]]
}

@test "basectl update-profile rejects conflicting defaults options" {
    run_base_command update-profile --defaults --no-defaults

    [ "$status" -eq 2 ]
    [[ "$output" == *"Options '--defaults' and '--no-defaults' cannot be used together."* ]]
    [[ "$output" == *"Run 'basectl update-profile --help' for usage."* ]]
    [[ "$output" != *"Usage:"* ]]
    [ ! -e "$TEST_HOME/.base.d/profile.conf" ]
}
