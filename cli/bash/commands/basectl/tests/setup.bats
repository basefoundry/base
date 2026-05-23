#!/usr/bin/env bats

load ../../../../../lib/bash/tests/test_helper.sh

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
tools_dir="${BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR:?}"
state_dir="${BASE_SETUP_TEST_STATE_DIR:?}"
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
state_dir="${BASE_SETUP_TEST_STATE_DIR:?}"
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
state_dir="${BASE_SETUP_TEST_STATE_DIR:?}"
python_prefix="${BASE_SETUP_TEST_PYTHON_PREFIX:?}"
python_formula="${BASE_SETUP_PYTHON_FORMULA:-python@3.13}"
bats_formula="${BASE_SETUP_BATS_FORMULA:-bats-core}"
pyyaml_package="${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
click_package="${BASE_SETUP_CLICK_PACKAGE:-click}"

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
    cat > "$3/bin/python" <<'VENVEOF'
#!/usr/bin/env bash
pyyaml_package="${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
click_package="${BASE_SETUP_CLICK_PACKAGE:-click}"
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-ran"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$pyyaml_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" && "${4:-}" == "$pyyaml_package" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-install-ran"
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$click_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" && "${4:-}" == "$click_package" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/click-install-ran"
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed"
    exit 0
fi
printf 'unexpected venv python args: %s\n' "$*" >&2
exit 1
VENVEOF
    chmod +x "$3/bin/python"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-ran"
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
touch "${BASE_SETUP_TEST_STATE_DIR:?}/homebrew-install-ran"
cat > "${BASE_SETUP_TEST_MOCKBIN:?}/brew" <<'BREWEOF'
#!/usr/bin/env bash
state_dir="${BASE_SETUP_TEST_STATE_DIR:?}"
python_prefix="${BASE_SETUP_TEST_PYTHON_PREFIX:?}"
python_formula="${BASE_SETUP_PYTHON_FORMULA:-python@3.13}"
bats_formula="${BASE_SETUP_BATS_FORMULA:-bats-core}"
pyyaml_package="${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
click_package="${BASE_SETUP_CLICK_PACKAGE:-click}"

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
    cat > "$3/bin/python" <<'VENVEOF'
#!/usr/bin/env bash
pyyaml_package="${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
click_package="${BASE_SETUP_CLICK_PACKAGE:-click}"
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-ran"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$pyyaml_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" && "${4:-}" == "$pyyaml_package" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-install-ran"
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$click_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" && "${4:-}" == "$click_package" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/click-install-ran"
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed"
    exit 0
fi
printf 'unexpected venv python args: %s\n' "$*" >&2
exit 1
VENVEOF
    chmod +x "$3/bin/python"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-ran"
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
chmod +x "${BASE_SETUP_TEST_MOCKBIN:?}/brew"
EOF
    chmod +x "$installer"

    printf '%s\n' "$installer"
}

run_base_command() {
    local arg
    local env_args=()
    local command_args=()
    local python_prefix="$TEST_TMPDIR/python-prefix"
    local xcode_dir="$TEST_TMPDIR/CommandLineTools"

    for arg in "$@"; do
        if [[ ${#command_args[@]} -eq 0 && "$arg" == *=* ]]; then
            env_args+=("$arg")
        else
            command_args+=("$arg")
        fi
    done

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="${OSTYPE_OVERRIDE:-darwin24}" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$python_prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$xcode_dir" \
        BASE_SETUP_XCODE_WAIT_TIMEOUT_SECONDS=5 \
        BASE_SETUP_XCODE_WAIT_INTERVAL_SECONDS=0 \
        "${env_args[@]}" \
        "$BASE_REPO_ROOT/bin/basectl" "${command_args[@]}"
}

@test "basectl setup prints usage for help" {
    run_base_command setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl setup [options]"* ]]
    [[ "$output" == *"Prepare the local Base CLI environment on macOS."* ]]
}

@test "basectl check prints usage for help" {
    run_base_command check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl check [options]"* ]]
    [[ "$output" == *"Verify the local Base CLI environment on macOS without making changes."* ]]
}

@test "basectl setup fails on unsupported operating systems" {
    OSTYPE_OVERRIDE="linux-gnu"

    run_base_command setup

    [ "$status" -eq 1 ]
    [[ "$output" == *"supports macOS only"* ]]
}

@test "basectl setup is idempotent when brew, xcode tools, python, and the venv already exist" {
    local venv_dir="$TEST_HOME/.base.d/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    mkdir -p "$venv_dir/bin"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"
    cat > "$venv_dir/bin/python" <<'EOF'
#!/usr/bin/env bash
pyyaml_package="${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
click_package="${BASE_SETUP_CLICK_PACKAGE:-click}"
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-ran"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$pyyaml_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" && "${4:-}" == "$pyyaml_package" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-install-ran"
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$click_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" && "${4:-}" == "$click_package" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/click-install-ran"
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed"
    exit 0
fi
printf 'unexpected venv python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$venv_dir/bin/python"

    run_base_command setup

    [ "$status" -eq 0 ]
    [[ "$output" == *"Homebrew is already installed."* ]]
    [[ "$output" == *"Xcode Command Line Tools are already installed."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is already installed via Homebrew."* ]]
    [[ "$output" == *"BATS formula 'bats-core' is already installed via Homebrew."* ]]
    [[ "$output" == *"Virtual environment already exists at '$venv_dir'."* ]]
    [[ "$output" == *"Python package 'PyYAML' is already installed in the Base virtual environment."* ]]
    [[ "$output" == *"Python package 'click' is already installed in the Base virtual environment."* ]]
    [[ "$output" == *"Running Python project setup layer."* ]]
    [ ! -f "$TEST_STATE_DIR/python-install-ran" ]
    [ ! -f "$TEST_STATE_DIR/bats-install-ran" ]
    [ ! -f "$TEST_STATE_DIR/pyyaml-install-ran" ]
    [ ! -f "$TEST_STATE_DIR/click-install-ran" ]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
}

@test "basectl setup installs missing dependencies and creates the Base virtual environment" {
    local installer
    local venv_dir="$TEST_HOME/.base.d/.venv"

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [[ "$output" == *"Installing Homebrew."* ]]
    [[ "$output" == *"Installing Xcode Command Line Tools."* ]]
    [[ "$output" == *"Xcode Command Line Tools installation detected."* ]]
    [[ "$output" == *"Installing Python formula 'python@3.13' via Homebrew."* ]]
    [[ "$output" == *"Installing BATS formula 'bats-core' via Homebrew."* ]]
    [[ "$output" == *"Creating Python virtual environment at '$venv_dir'."* ]]
    [[ "$output" == *"Installing Python package 'PyYAML' in the Base virtual environment."* ]]
    [[ "$output" == *"Installing Python package 'click' in the Base virtual environment."* ]]
    [[ "$output" == *"Running Python project setup layer."* ]]
    [[ "$output" == *"Base CLI setup is complete."* ]]
    [ -f "$TEST_STATE_DIR/homebrew-install-ran" ]
    [ -f "$TEST_STATE_DIR/python-install-ran" ]
    [ -f "$TEST_STATE_DIR/bats-install-ran" ]
    [ -f "$TEST_STATE_DIR/pyyaml-install-ran" ]
    [ -f "$TEST_STATE_DIR/click-install-ran" ]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
    [ -f "$venv_dir/pyvenv.cfg" ]
}

@test "basectl setup supports dry-run without making changes" {
    run_base_command setup --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would install Homebrew using the official installer."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Xcode Command Line Tools and wait for installation to complete."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python formula 'python@3.13' via Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would install BATS formula 'bats-core' via Homebrew."* ]]
    [[ "$output" == *"[DRY-RUN] Would create Python virtual environment at '$TEST_HOME/.base.d/.venv'."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python package 'PyYAML' in the Base virtual environment."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python package 'click' in the Base virtual environment."* ]]
    [[ "$output" == *"[DRY-RUN] Would run Python project setup layer after PyYAML is installed."* ]]
    [[ "$output" == *"[DRY-RUN] Base CLI setup check is complete."* ]]
    [ ! -e "$TEST_HOME/.base.d/.venv" ]
}

@test "basectl setup ignores inherited DRY_RUN without --dry-run" {
    local installer
    local venv_dir="$TEST_HOME/.base.d/.venv"

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        DRY_RUN=true \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [[ "$output" != *"[DRY-RUN]"* ]]
    [[ "$output" == *"Installing Homebrew."* ]]
    [[ "$output" == *"Installing Xcode Command Line Tools."* ]]
    [[ "$output" == *"Creating Python virtual environment at '$venv_dir'."* ]]
    [ -f "$TEST_STATE_DIR/homebrew-install-ran" ]
    [ -f "$venv_dir/pyvenv.cfg" ]
}

@test "basectl check passes when all required components are present" {
    local venv_dir="$TEST_HOME/.base.d/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    mkdir -p "$venv_dir/bin"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"

    run_base_command check

    [ "$status" -eq 0 ]
    [[ "$output" == *"Homebrew is installed."* ]]
    [[ "$output" == *"Xcode Command Line Tools are installed."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is installed via Homebrew."* ]]
    [[ "$output" == *"BATS formula 'bats-core' is installed via Homebrew."* ]]
    [[ "$output" == *"Virtual environment exists at '$venv_dir'."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
}

@test "basectl check fails when required components are missing" {
    run_base_command check

    [ "$status" -eq 1 ]
    [[ "$output" == *"Homebrew is not installed."* ]]
    [[ "$output" == *"Xcode Command Line Tools are not installed."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is not installed via Homebrew."* ]]
    [[ "$output" == *"BATS formula 'bats-core' is not installed via Homebrew."* ]]
    [[ "$output" == *"Virtual environment is missing at '$TEST_HOME/.base.d/.venv'."* ]]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
}

@test "basectl -v setup enables DEBUG logs" {
    run_base_command -v setup --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"DEBUG"* ]]
    [[ "$output" == *"Running basectl command 'setup'"* ]]
    [[ "$output" == *"Running 'basectl setup'"* ]]
}

@test "basectl setup -v also enables DEBUG logs" {
    run_base_command setup -v --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"DEBUG"* ]]
    [[ "$output" == *"Running 'basectl setup'"* ]]
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

    [[ "$(cat "$TEST_HOME/.bash_profile")" == *"# --- BEGIN base bash_profile MANAGED SECTION - DO NOT EDIT ---"* ]]
    [[ "$(cat "$TEST_HOME/.bash_profile")" == *"source $BASE_REPO_ROOT/lib/shell/bash_profile"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *"# --- BEGIN base bashrc MANAGED SECTION - DO NOT EDIT ---"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *"source $BASE_REPO_ROOT/lib/shell/bashrc"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" != *"PATH="* ]]
    [[ "$(cat "$TEST_HOME/.zprofile")" == *"# --- BEGIN base zprofile MANAGED SECTION - DO NOT EDIT ---"* ]]
    [[ "$(cat "$TEST_HOME/.zprofile")" == *"source $BASE_REPO_ROOT/lib/shell/zprofile"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" == *"# --- BEGIN base zshrc MANAGED SECTION - DO NOT EDIT ---"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" == *"source $BASE_REPO_ROOT/lib/shell/zshrc"* ]]
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

    [ "$(grep -c '# --- BEGIN base bashrc MANAGED SECTION - DO NOT EDIT ---' "$TEST_HOME/.bashrc")" -eq 1 ]
    [ "$(grep -c '# --- END base bashrc MANAGED SECTION - DO NOT EDIT ---' "$TEST_HOME/.bashrc")" -eq 1 ]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *"user line before"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" == *$'user line before

# --- BEGIN base bashrc MANAGED SECTION - DO NOT EDIT ---'* ]]
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
