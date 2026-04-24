#!/usr/bin/env bats

load ../../../tests/test_helper.bash

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_STATE_DIR="$TEST_TMPDIR/state"
    TEST_BASH_BIN_DIR="$(dirname "$(command -v bash)")"
    unset OSTYPE_OVERRIDE

    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN" "$TEST_STATE_DIR"
}

create_xcode_stubs() {
    cat > "$TEST_MOCKBIN/xcode-select" <<'EOF'
#!/usr/bin/env bash
tools_dir="${BANYAN_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR:?}"
state_dir="${BANYAN_SETUP_TEST_STATE_DIR:?}"
installed_file="$state_dir/xcode-installed"

case "${1:-}" in
    -p)
        if [[ -f "$installed_file" ]]; then
            printf '%s\n' "$tools_dir"
            exit 0
        fi
        exit 1
        ;;
    --install)
        touch "$installed_file"
        mkdir -p "$tools_dir"
        exit 0
        ;;
    *)
        printf 'unexpected xcode-select args: %s\n' "$*" >&2
        exit 1
        ;;
esac
EOF
    chmod +x "$TEST_MOCKBIN/xcode-select"

    cat > "$TEST_MOCKBIN/xcrun" <<'EOF'
#!/usr/bin/env bash
state_dir="${BANYAN_SETUP_TEST_STATE_DIR:?}"
installed_file="$state_dir/xcode-installed"

if [[ "${1:-}" == "-f" && "${2:-}" == "clang" && -f "$installed_file" ]]; then
    printf '/usr/bin/clang\n'
    exit 0
fi

exit 1
EOF
    chmod +x "$TEST_MOCKBIN/xcrun"
}

create_brew_stub() {
    cat > "$TEST_MOCKBIN/brew" <<'EOF'
#!/usr/bin/env bash
state_dir="${BANYAN_SETUP_TEST_STATE_DIR:?}"
python_prefix="${BANYAN_SETUP_TEST_PYTHON_PREFIX:?}"
python_formula="${BANYAN_SETUP_PYTHON_FORMULA:-python@3.13}"
bats_formula="${BANYAN_SETUP_BATS_FORMULA:-bats-core}"

case "${1:-}" in
    list)
        case "${2:-}" in
            "$python_formula")
                [[ -f "$state_dir/python-installed" ]]
                exit $?
                ;;
            "$bats_formula")
                [[ -f "$state_dir/bats-installed" ]]
                exit $?
                ;;
        esac
        exit 1
        ;;
    install)
        if [[ "${2:-}" == "$python_formula" ]]; then
            touch "$state_dir/python-install-ran"
            touch "$state_dir/python-installed"
            mkdir -p "$python_prefix/bin"
            cat > "$python_prefix/bin/python3" <<'PYEOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" && -n "${3:-}" ]]; then
    mkdir -p "$3/bin"
    printf 'python-home = test\n' > "$3/pyvenv.cfg"
    printf '#!/usr/bin/env bash\n' > "$3/bin/activate"
    exit 0
fi
printf 'unexpected python3 args: %s\n' "$*" >&2
exit 1
PYEOF
            chmod +x "$python_prefix/bin/python3"
            exit 0
        fi
        if [[ "${2:-}" == "$bats_formula" ]]; then
            touch "$state_dir/bats-install-ran"
            touch "$state_dir/bats-installed"
            exit 0
        fi
        printf 'unexpected brew install args: %s\n' "$*" >&2
        exit 1
        ;;
    --prefix)
        if [[ "${2:-}" == "$python_formula" ]]; then
            printf '%s\n' "$python_prefix"
            exit 0
        fi
        exit 1
        ;;
    *)
        printf 'unexpected brew args: %s\n' "$*" >&2
        exit 1
        ;;
esac
EOF
    chmod +x "$TEST_MOCKBIN/brew"
}

create_homebrew_installer_stub() {
    local installer="$TEST_TMPDIR/homebrew-installer.sh"

    cat > "$installer" <<'EOF'
#!/usr/bin/env bash
touch "${BANYAN_SETUP_TEST_STATE_DIR:?}/homebrew-install-ran"
cat > "${BANYAN_SETUP_TEST_MOCKBIN:?}/brew" <<'BREWEOF'
#!/usr/bin/env bash
state_dir="${BANYAN_SETUP_TEST_STATE_DIR:?}"
python_prefix="${BANYAN_SETUP_TEST_PYTHON_PREFIX:?}"
python_formula="${BANYAN_SETUP_PYTHON_FORMULA:-python@3.13}"
bats_formula="${BANYAN_SETUP_BATS_FORMULA:-bats-core}"

case "${1:-}" in
    list)
        case "${2:-}" in
            "$python_formula")
                [[ -f "$state_dir/python-installed" ]]
                exit $?
                ;;
            "$bats_formula")
                [[ -f "$state_dir/bats-installed" ]]
                exit $?
                ;;
        esac
        exit 1
        ;;
    install)
        if [[ "${2:-}" == "$python_formula" ]]; then
            touch "$state_dir/python-install-ran"
            touch "$state_dir/python-installed"
            mkdir -p "$python_prefix/bin"
            cat > "$python_prefix/bin/python3" <<'PYEOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" && -n "${3:-}" ]]; then
    mkdir -p "$3/bin"
    printf 'python-home = test\n' > "$3/pyvenv.cfg"
    printf '#!/usr/bin/env bash\n' > "$3/bin/activate"
    exit 0
fi
printf 'unexpected python3 args: %s\n' "$*" >&2
exit 1
PYEOF
            chmod +x "$python_prefix/bin/python3"
            exit 0
        fi
        if [[ "${2:-}" == "$bats_formula" ]]; then
            touch "$state_dir/bats-install-ran"
            touch "$state_dir/bats-installed"
            exit 0
        fi
        printf 'unexpected brew install args: %s\n' "$*" >&2
        exit 1
        ;;
    --prefix)
        if [[ "${2:-}" == "$python_formula" ]]; then
            printf '%s\n' "$python_prefix"
            exit 0
        fi
        exit 1
        ;;
    *)
        printf 'unexpected brew args: %s\n' "$*" >&2
        exit 1
        ;;
esac
BREWEOF
chmod +x "${BANYAN_SETUP_TEST_MOCKBIN:?}/brew"
EOF
    chmod +x "$installer"

    printf '%s\n' "$installer"
}

run_setup() {
    local python_prefix="$TEST_TMPDIR/python-prefix"
    local xcode_dir="$TEST_TMPDIR/CommandLineTools"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="${OSTYPE_OVERRIDE:-darwin24}" \
        BANYAN_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BANYAN_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BANYAN_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BANYAN_SETUP_TEST_PYTHON_PREFIX="$python_prefix" \
        BANYAN_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$xcode_dir" \
        BANYAN_SETUP_XCODE_WAIT_TIMEOUT_SECONDS=5 \
        BANYAN_SETUP_XCODE_WAIT_INTERVAL_SECONDS=0 \
        "$@"
}

@test "setup prints usage for help" {
    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"setup [options] <command>"* ]]
    [[ "$output" == *"check"* ]]
    [[ "$output" == *"Prepare and verify the local Base CLI environment on macOS."* ]]
}

@test "setup requires an explicit command" {
    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh"

    [ "$status" -eq 1 ]
    [[ "$output" == *"A setup command is required."* ]]
}

@test "setup fails on unsupported operating systems" {
    OSTYPE_OVERRIDE="linux-gnu"

    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" install

    [ "$status" -eq 1 ]
    [[ "$output" == *"supports macOS only"* ]]
}

@test "setup is idempotent when brew, xcode tools, python, and the venv already exist" {
    local venv_dir="$TEST_HOME/.banyanlabs.d/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    mkdir -p "$venv_dir/bin"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"

    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" install

    [ "$status" -eq 0 ]
    [[ "$output" == *"Homebrew is already installed."* ]]
    [[ "$output" == *"Xcode Command Line Tools are already installed."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is already installed via Homebrew."* ]]
    [[ "$output" == *"BATS formula 'bats-core' is already installed via Homebrew."* ]]
    [[ "$output" == *"Virtual environment already exists at '$venv_dir'."* ]]
    [ ! -f "$TEST_STATE_DIR/python-install-ran" ]
    [ ! -f "$TEST_STATE_DIR/bats-install-ran" ]
}

@test "setup installs missing dependencies and creates the Banyan virtual environment" {
    local installer
    local venv_dir="$TEST_HOME/.banyanlabs.d/.venv"

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_setup \
        BANYAN_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BANYAN_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" install

    [ "$status" -eq 0 ]
    [[ "$output" == *"Installing Homebrew."* ]]
    [[ "$output" == *"Installing Xcode Command Line Tools."* ]]
    [[ "$output" == *"Xcode Command Line Tools installation detected."* ]]
    [[ "$output" == *"Installing Python formula 'python@3.13' via Homebrew."* ]]
    [[ "$output" == *"Installing BATS formula 'bats-core' via Homebrew."* ]]
    [[ "$output" == *"Creating Python virtual environment at '$venv_dir'."* ]]
    [[ "$output" == *"Base CLI setup is complete."* ]]
    [ -f "$TEST_STATE_DIR/homebrew-install-ran" ]
    [ -f "$TEST_STATE_DIR/python-install-ran" ]
    [ -f "$TEST_STATE_DIR/bats-install-ran" ]
    [ -f "$venv_dir/pyvenv.cfg" ]
}

@test "setup install supports dry-run without making changes" {
    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" install --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would install Homebrew using the official installer."* ]]
    [[ "$output" == *"[DRY-RUN] Would wait for Xcode Command Line Tools installation to complete."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python formula 'python@3.13' via Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would install BATS formula 'bats-core' via Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would create Python virtual environment at '$TEST_HOME/.banyanlabs.d/.venv'."* ]]
    [[ "$output" == *"[DRY-RUN] Base CLI setup check is complete."* ]]
    [ ! -e "$TEST_HOME/.banyanlabs.d/.venv" ]
}

@test "setup check passes when all required components are present" {
    local venv_dir="$TEST_HOME/.banyanlabs.d/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    mkdir -p "$venv_dir/bin"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"

    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" check

    [ "$status" -eq 0 ]
    [[ "$output" == *"Homebrew is installed."* ]]
    [[ "$output" == *"Xcode Command Line Tools are installed."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is installed via Homebrew."* ]]
    [[ "$output" == *"BATS formula 'bats-core' is installed via Homebrew."* ]]
    [[ "$output" == *"Virtual environment exists at '$venv_dir'."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
}

@test "setup check fails when required components are missing" {
    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" check

    [ "$status" -eq 1 ]
    [[ "$output" == *"Homebrew is not installed."* ]]
    [[ "$output" == *"Xcode Command Line Tools are not installed."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is not installed via Homebrew."* ]]
    [[ "$output" == *"BATS formula 'bats-core' is not installed via Homebrew."* ]]
    [[ "$output" == *"Virtual environment is missing at '$TEST_HOME/.banyanlabs.d/.venv'."* ]]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
}

@test "setup install enables DEBUG logs with -v" {
    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" -v install --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"DEBUG"* ]]
    [[ "$output" == *"Running setup command 'install'"* ]]
}

@test "setup update-profile is reserved for later work" {
    run_setup "$BANYAN_REPO_ROOT/cli/bash/bin/setup.sh" update-profile

    [ "$status" -eq 1 ]
    [[ "$output" == *"update-profile"* ]]
    [[ "$output" == *"not implemented yet"* ]]
}
