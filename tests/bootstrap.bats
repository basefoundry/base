#!/usr/bin/env bats

load ./test_helper.sh
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_COMMAND_LOG="$TEST_TMPDIR/bootstrap-commands"
    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN"
}

run_bootstrap() {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_BOOTSTRAP_BREW_CANDIDATES="$TEST_TMPDIR/missing-brew" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" "$@"
}

create_unusable_git_stub() {
    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/bin/sh
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/git"
}

create_git_stub() {
    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/bin/sh
printf 'git %s\n' "$*" >> "${BASE_BOOTSTRAP_TEST_COMMAND_LOG:?}"
if [ "${1:-}" = "--version" ]; then
    printf 'git version 2.0.0\n'
    exit 0
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/git"
}

create_failing_git_clone_stub() {
    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/bin/sh
printf 'git %s\n' "$*" >> "${BASE_BOOTSTRAP_TEST_COMMAND_LOG:?}"
if [ "${1:-}" = "--version" ]; then
    printf 'git version 2.0.0\n'
    exit 0
fi
if [ "${1:-}" = "clone" ]; then
    exit 2
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/git"
}

create_brew_stub() {
    cat > "$TEST_MOCKBIN/brew" <<'EOF'
#!/bin/sh
printf 'brew %s\n' "$*" >> "${BASE_BOOTSTRAP_TEST_COMMAND_LOG:?}"
case "${1:-}" in
    --prefix)
        printf '%s\n' "${BASE_BOOTSTRAP_TEST_BREW_PREFIX:?}"
        exit 0
        ;;
    list)
        if [ "${BASE_BOOTSTRAP_TEST_BREW_BASE_INSTALLED:-false}" = "true" ]; then
            exit 0
        fi
        exit 1
        ;;
    install)
        exit 0
        ;;
esac
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/brew"
}

create_sudo_stub() {
    cat > "$TEST_MOCKBIN/sudo" <<'EOF'
#!/bin/sh
printf 'sudo %s\n' "$*" >> "${BASE_BOOTSTRAP_TEST_COMMAND_LOG:?}"
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/sudo"
}

create_supported_bash_candidate() {
    local bash_path="$1"

    mkdir -p "$(dirname "$bash_path")"
    cat > "$bash_path" <<'EOF'
#!/bin/sh
if [ "${1:-}" = "-c" ]; then
    printf '42\n'
fi
exit 0
EOF
    chmod +x "$bash_path"
}

create_homebrew_installer_stub() {
    local installer="$TEST_TMPDIR/homebrew-installer.sh"

    cat > "$installer" <<'EOF'
#!/usr/bin/env bash
touch "${BASE_BOOTSTRAP_TEST_MARKER:?}"
EOF
    chmod +x "$installer"
    printf '%s\n' "$installer"
}

sha256_file() {
    local checksum

    checksum="$(shasum -a 256 "$1")"
    printf '%s\n' "${checksum%% *}"
}

@test "bootstrap prints help" {
    run_bootstrap --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"--source"* ]]
    [[ "$output" == *"--brew"* ]]
    [[ "$output" == *"--ensure-bash"* ]]
    [[ "$output" == *"--yes"* ]]
}

@test "bootstrap avoids shell strict mode" {
    run grep -nE '^[[:space:]]*set[[:space:]].*(-e|-u|pipefail)' "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 1 ]
    [ "$output" = "" ]
}

@test "bootstrap uses scoped colon splitting for candidate lists" {
    run grep -n 'old_ifs' "$BASE_REPO_ROOT/bootstrap.sh"
    [ "$status" -eq 1 ]
    [ "$output" = "" ]

    run grep -c 'IFS=: read -ra' "$BASE_REPO_ROOT/bootstrap.sh"
    [ "$status" -eq 0 ]
    [ "$output" -eq 2 ]
}

@test "bootstrap keeps Homebrew binary state out of module globals" {
    run grep -nE '(^|[^A-Z_])BOOTSTRAP_BREW_BIN([^A-Z_]|$)' "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 1 ]
    [ "$output" = "" ]
}

@test "bootstrap has no stale macOS-only guard" {
    run grep -n 'bootstrap_require_macos' "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 1 ]
    [ "$output" = "" ]
}

@test "bootstrap source dry-run installs first-mile prerequisites and prints handoff commands" {
    local install_dir="$TEST_HOME/work/base"

    create_unusable_git_stub

    run_bootstrap --dry-run --source --install-dir "$install_dir" --repo-url https://example.test/base.git

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base bootstrap"* ]]
    [[ "$output" == *"Installing Homebrew."* ]]
    [[ "$output" == *"Homebrew installer trust policy: using Homebrew's official mutable installer without checksum verification."* ]]
    [[ "$output" == *"BASE_HOMEBREW_INSTALLER_URL"* ]]
    [[ "$output" == *"BASE_HOMEBREW_INSTALLER_SHA256"* ]]
    [[ "$output" == *"BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL"* ]]
    [[ "$output" == *"BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh>"* ]]
    [[ "$output" == *"Installing Git through Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew install git"* ]]
    [[ "$output" == *"Installing Bash 4.2+ through Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew install bash"* ]]
    [[ "$output" == *"Install mode: source"* ]]
    [[ "$output" == *"Repository: https://example.test/base.git"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: git clone https://example.test/base.git $install_dir"* ]]
    [[ "$output" == *"$install_dir/bin/basectl setup"* ]]
    [[ "$output" == *"$install_dir/bin/basectl update-profile"* ]]
    [[ "$output" == *"exec \"\$SHELL\" -l"* ]]
}

@test "bootstrap ensure-bash no-ops when current Bash is supported" {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=42 \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --ensure-bash --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base bootstrap"* ]]
    [[ "$output" == *"Bash 4.2+ is available for Base."* ]]
    [[ "$output" != *"Install mode:"* ]]
    [[ "$output" != *"git clone"* ]]
    [[ "$output" != *"basectl setup"* ]]
}

@test "bootstrap ensure-bash macOS dry-run installs Homebrew Bash only" {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_BOOTSTRAP_BREW_CANDIDATES="$TEST_TMPDIR/missing-brew" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --ensure-bash --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Installing Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh>"* ]]
    [[ "$output" == *"Installing Bash 4.2+ through Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew install bash"* ]]
    [[ "$output" != *"Installing Git through Homebrew."* ]]
    [[ "$output" != *"Install mode:"* ]]
    [[ "$output" != *"git clone"* ]]
    [[ "$output" != *"basectl setup"* ]]
}

@test "bootstrap dry-run reports pinned Homebrew installer verification" {
    local install_dir="$TEST_HOME/work/base"
    local installer
    local checksum

    create_unusable_git_stub
    installer="$(create_homebrew_installer_stub)"
    checksum="$(sha256_file "$installer")"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_BOOTSTRAP_BREW_CANDIDATES="$TEST_TMPDIR/missing-brew" \
        BASE_HOMEBREW_INSTALLER_URL="$installer" \
        BASE_HOMEBREW_INSTALLER_SHA256="$checksum" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --dry-run --source --install-dir "$install_dir" --repo-url https://example.test/base.git

    [ "$status" -eq 0 ]
    [[ "$output" == *"Using pinned Homebrew installer from $installer."* ]]
    [[ "$output" == *"[DRY-RUN] Would verify Homebrew installer SHA-256 $checksum"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: /bin/bash <verified Homebrew installer from $installer>"* ]]
}

@test "bootstrap rejects pinned Homebrew installer without checksum" {
    local installer

    installer="$(create_homebrew_installer_stub)"

    run env \
        BASE_BOOTSTRAP_TESTING=true \
        BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL="$installer" \
        "$BASH" -c 'source "$1"; bootstrap_install_homebrew resolved_brew; printf "resolved=%s\n" "$resolved_brew"' _ "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Pinned Homebrew installer URL and SHA-256 are both required."* ]]
}

@test "bootstrap rejects pinned Homebrew checksum without installer location" {
    run env \
        BASE_BOOTSTRAP_TESTING=true \
        BASE_BOOTSTRAP_DRY_RUN=true \
        BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256=0000000000000000000000000000000000000000000000000000000000000000 \
        "$BASH" -c 'source "$1"; bootstrap_install_homebrew resolved_brew' _ "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Pinned Homebrew installer URL and SHA-256 are both required."* ]]
}

@test "bootstrap rejects mismatched pinned Homebrew installer checksum" {
    local installer
    local marker="$TEST_TMPDIR/homebrew-install-ran"

    installer="$(create_homebrew_installer_stub)"

    run env \
        BASE_BOOTSTRAP_TESTING=true \
        BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL="$installer" \
        BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256=0000000000000000000000000000000000000000000000000000000000000000 \
        BASE_BOOTSTRAP_TEST_MARKER="$marker" \
        "$BASH" -c 'source "$1"; bootstrap_install_homebrew resolved_brew; printf "resolved=%s\n" "$resolved_brew"' _ "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Homebrew installer checksum mismatch"* ]]
    [ ! -e "$marker" ]
}

@test "bootstrap runs verified pinned Homebrew installer" {
    local installer
    local checksum
    local marker="$TEST_TMPDIR/homebrew-install-ran"

    installer="$(create_homebrew_installer_stub)"
    checksum="$(sha256_file "$installer")"

    run env \
        BASE_BOOTSTRAP_TESTING=true \
        BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL="$installer" \
        BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256="$checksum" \
        BASE_BOOTSTRAP_TEST_MARKER="$marker" \
        "$BASH" -c 'source "$1"; bootstrap_install_homebrew resolved_brew; printf "resolved=%s\n" "$resolved_brew"' _ "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Using pinned Homebrew installer from $installer."* ]]
    [ -f "$marker" ]
}

@test "bootstrap reports source clone failures without printing handoff commands" {
    local install_dir="$TEST_HOME/work/base"

    create_brew_stub
    create_failing_git_clone_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=42 \
        BASE_BOOTSTRAP_TEST_COMMAND_LOG="$TEST_COMMAND_LOG" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --source --install-dir "$install_dir" --repo-url https://example.test/base.git

    [ "$status" -eq 1 ]
    [[ "$output" == *"Failed to clone Base repository."* ]]
    [[ "$output" != *"Run these commands to finish Base setup"* ]]
}

@test "bootstrap brew dry-run installs Base through Homebrew and prints basectl handoff" {
    create_unusable_git_stub

    run_bootstrap --dry-run --brew

    [ "$status" -eq 0 ]
    [[ "$output" == *"Install mode: brew"* ]]
    [[ "$output" == *"Formula: basefoundry/base/base"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: brew install basefoundry/base/base"* ]]
    [[ "$output" == *"  basectl setup"* ]]
    [[ "$output" == *"  basectl update-profile"* ]]
}

@test "bootstrap defaults to an existing Homebrew Base install" {
    local brew_prefix="$TEST_TMPDIR/homebrew"
    local supported_bash="$brew_prefix/bin/bash"

    mkdir -p "$brew_prefix/bin"
    create_brew_stub
    create_git_stub
    create_supported_bash_candidate "$supported_bash"
    touch "$brew_prefix/bin/basectl"
    touch "$TEST_MOCKBIN/basectl"
    chmod +x "$brew_prefix/bin/basectl"
    chmod +x "$TEST_MOCKBIN/basectl"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$supported_bash" \
        BASE_BOOTSTRAP_TEST_BREW_BASE_INSTALLED=true \
        BASE_BOOTSTRAP_TEST_BREW_PREFIX="$brew_prefix" \
        BASE_BOOTSTRAP_TEST_COMMAND_LOG="$TEST_COMMAND_LOG" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Homebrew is available at '$TEST_MOCKBIN/brew'."* ]]
    [[ "$output" == *"Git is available."* ]]
    [[ "$output" == *"Bash 4.2+ is available for Base."* ]]
    [[ "$output" == *"Install mode: brew"* ]]
    [[ "$output" == *"Base Homebrew formula 'basefoundry/base/base' is already installed."* ]]
    [[ "$output" == *"Homebrew basectl: $brew_prefix/bin/basectl"* ]]
    [[ "$output" == *"active basectl: $TEST_MOCKBIN/basectl"* ]]
    [[ "$output" == *"$brew_prefix/bin/basectl setup"* ]]
    [[ "$output" == *"$brew_prefix/bin/basectl update-profile"* ]]
    ! grep -Fqx "brew install basefoundry/base/base" "$TEST_COMMAND_LOG"
}

@test "bootstrap command-line mode overrides BASE_BOOTSTRAP_MODE" {
    create_unusable_git_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Darwin \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_BOOTSTRAP_BREW_CANDIDATES="$TEST_TMPDIR/missing-brew" \
        BASE_BOOTSTRAP_MODE=brew \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --dry-run --source

    [ "$status" -eq 0 ]
    [[ "$output" == *"Install mode: source"* ]]
    [[ "$output" != *"Formula: basefoundry/base/base"* ]]
}

@test "bootstrap linux-debian dry-run prints manual source checkout path" {
    local install_dir="$TEST_HOME/work/base"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_PLATFORM=linux-debian \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --dry-run --source --install-dir "$install_dir" --repo-url https://example.test/base.git

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base bootstrap"* ]]
    [[ "$output" == *"Ubuntu/Debian Linux bootstrap path"* ]]
    [[ "$output" == *"sudo apt-get update"* ]]
    [[ "$output" == *"sudo apt-get install -y bash git python3 python3-venv python3-pip bats shellcheck jq golang-go"* ]]
    [[ "$output" == *"Configure GitHub CLI's official Debian/Ubuntu apt repository before installing 'gh'"* ]]
    [[ "$output" == *"git clone https://example.test/base.git $install_dir"* ]]
    [[ "$output" == *"git clone https://github.com/basefoundry/base-bash-libs.git $TEST_HOME/work/base-bash-libs"* ]]
    [[ "$output" == *"$install_dir/bin/basectl setup --dry-run"* ]]
    [[ "$output" == *"$install_dir/bin/basectl setup --yes"* ]]
    [[ "$output" == *"$install_dir/bin/basectl update-profile"* ]]
    [[ "$output" == *"exec \"\$SHELL\" -l"* ]]
    [[ "$output" != *"Homebrew"* ]]
    [[ "$output" != *"Xcode"* ]]
}

@test "bootstrap ensure-bash linux-debian dry-run prints Bash apt commands only" {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_PLATFORM=linux-debian \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --ensure-bash --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Bash 4.2+ is not available for Base."* ]]
    [[ "$output" == *"[DRY-RUN] Would run: sudo apt-get update"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: sudo apt-get install -y bash"* ]]
    [[ "$output" != *"git python3"* ]]
    [[ "$output" != *"git clone"* ]]
    [[ "$output" != *"basectl setup"* ]]
}

@test "bootstrap ensure-bash linux-debian requires yes before apt mutation" {
    create_sudo_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_PLATFORM=linux-debian \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_BOOTSTRAP_TEST_COMMAND_LOG="$TEST_COMMAND_LOG" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --ensure-bash

    [ "$status" -eq 1 ]
    [[ "$output" == *"Installing Bash on Ubuntu/Debian requires --yes."* ]]
    [ ! -e "$TEST_COMMAND_LOG" ]
}

@test "bootstrap ensure-bash linux-debian yes runs Bash apt commands" {
    create_sudo_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_PLATFORM=linux-debian \
        BASE_BOOTSTRAP_TEST_BASH_VERSION=32 \
        BASE_BOOTSTRAP_BASH_CANDIDATES="$TEST_TMPDIR/missing-bash" \
        BASE_BOOTSTRAP_TEST_COMMAND_LOG="$TEST_COMMAND_LOG" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --ensure-bash --yes

    [ "$status" -eq 0 ]
    [[ "$output" == *"Installing Bash 4.2+ through apt."* ]]
    [[ "$output" == *"Bash install command completed; start a new shell or rerun bootstrap if the current shell is still too old."* ]]
    grep -Fqx "sudo apt-get update" "$TEST_COMMAND_LOG"
    grep -Fqx "sudo apt-get install -y bash" "$TEST_COMMAND_LOG"
    [[ "$output" != *"git clone"* ]]
    [[ "$output" != *"basectl setup"* ]]
}

@test "bootstrap linux-debian rejects Homebrew mode" {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_PLATFORM=linux-debian \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --dry-run --brew

    [ "$status" -eq 1 ]
    [[ "$output" == *"Homebrew bootstrap mode is macOS-only; use --source on Ubuntu/Debian Linux."* ]]
}

@test "bootstrap detects Ubuntu from os-release" {
    local install_dir="$TEST_HOME/work/base"
    local os_release="$TEST_TMPDIR/os-release"

    printf 'ID=ubuntu\nID_LIKE=debian\n' > "$os_release"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Linux \
        BASE_BOOTSTRAP_TEST_OS_RELEASE_PATH="$os_release" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --dry-run --source --install-dir "$install_dir" --repo-url https://example.test/base.git

    [ "$status" -eq 0 ]
    [[ "$output" == *"Ubuntu/Debian Linux bootstrap path"* ]]
    [[ "$output" == *"git clone https://example.test/base.git $install_dir"* ]]
}

@test "bootstrap can refuse to install missing Homebrew" {
    run_bootstrap --no-homebrew-install

    [ "$status" -eq 1 ]
    [[ "$output" == *"Base bootstrap"* ]]
    [[ "$output" == *"Homebrew is required"* ]]
}

@test "bootstrap rejects unsupported Linux systems" {
    local os_release="$TEST_TMPDIR/os-release"

    printf 'ID=fedora\nID_LIKE="rhel fedora"\n' > "$os_release"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_OS=Linux \
        BASE_BOOTSTRAP_TEST_OS_RELEASE_PATH="$os_release" \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --dry-run

    [ "$status" -eq 1 ]
    [[ "$output" == *"bootstrap.sh currently supports macOS and Ubuntu/Debian Linux only"* ]]
}

@test "bootstrap ensure-bash rejects unsupported platforms" {
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_BOOTSTRAP_TEST_PLATFORM=unsupported \
        "$BASH" "$BASE_REPO_ROOT/bootstrap.sh" --ensure-bash --dry-run

    [ "$status" -eq 1 ]
    [[ "$output" == *"bootstrap.sh --ensure-bash currently supports macOS and Ubuntu/Debian Linux only."* ]]
}
