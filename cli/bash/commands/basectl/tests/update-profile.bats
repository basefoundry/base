#!/usr/bin/env bats

load ./setup_helpers.bash


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

@test "BASE_DEBUG traces Base-managed Bash startup" {
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
    [[ "$output" == *"BASE_DEBUG bashrc: prepended '$BASE_REPO_ROOT/bin' to PATH"* ]]
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
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$TEST_HOME/.bashrc" -i -c 'alias cp; printf "EDITOR=%s\n" "$EDITOR"; printf "VISUAL=%s\n" "$VISUAL"; printf "EXINIT=%s\n" "$EXINIT"; printf "BASE_HOME=%s\n" "$BASE_HOME"; cd "$BASE_HOME"; printf "git=%s\n" "$(_base_bash_defaults_git_prompt)"; printf "PS1=%s\n" "$PS1"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"alias cp='cp -i'"* ]]
    [[ "$output" == *"EDITOR=vi"* ]]
    [[ "$output" == *"VISUAL=vi"* ]]
    [[ "$output" == *"EXINIT=set ts=4 sw=4 ai nows nosm expandtab"* ]]
    [[ "$output" == *"BASE_HOME=$BASE_REPO_ROOT"* ]]
    [[ "$output" == *"git=("* ]]
    [[ "$output" == *'PS1=\[\033[0;35m\]\T \h\[\033[0;33m\] $(_base_bash_defaults_git_prompt)\w\[\033[00m\]: '* ]]

    if command -v zsh >/dev/null 2>&1; then
        run env -u BASE_HOME -u BASE_HOST -u BASE_OS -u EDITOR -u VISUAL -u EXINIT \
            HOME="$TEST_HOME" \
            PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
            zsh -f -i -c 'source "$HOME/.zshrc"; cd "$BASE_HOME"; printf "git=%s\n" "$(_base_zsh_defaults_git_prompt)"; printf "PROMPT=%s\n" "$PROMPT"; setopt | grep -q "^promptsubst$"; printf "prompt_subst=enabled\n"'

        [ "$status" -eq 0 ]
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

    [ "$status" -eq 1 ]
    [[ "$output" == *"Options '--defaults' and '--no-defaults' cannot be used together."* ]]
    [[ "$output" == *"Usage:"* ]]
    [ ! -e "$TEST_HOME/.base.d/profile.conf" ]
}
