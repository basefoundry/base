#!/usr/bin/env bats

load ./setup_helpers.bash


@test "basectl setup prints usage for help" {
    run_base_command setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl setup [options]"* ]]
    [[ "$output" != *"--dev"* ]]
    [[ "$output" == *"--profile <list>"* ]]
    [[ "$output" == *"Profile lists are comma-separated, for example: --profile dev,sre."* ]]
    [[ "$output" == *"dev - Base development tooling for this repository."* ]]
    [[ "$output" == *"sre - production/SRE prerequisite tooling."* ]]
    [[ "$output" == *"ai  - AI coding assistant tooling."* ]]
    [[ "$output" == *"--notify"* ]]
    [[ "$output" == *"--no-notify"* ]]
    [[ "$output" == *"--recreate-venv"* ]]
    [[ "$output" == *"Prepare the local Base CLI environment on macOS."* ]]
    [[ "$output" == *"Create ~/.base.d/config.yaml with workspace.root: ~/work if missing."* ]]
}

@test "setup profile normalization does not shell out to tr" {
    local bash_libs_dir

    bash_libs_dir="$(base_bash_libs_fixture_dir)"
    create_tr_failure_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_common.sh"
            setup_enable_profile_argument " DEV , Ai " || exit $?
            printf "profiles=%s\n" "$BASE_SETUP_PROFILES"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"profiles=dev ai"* ]]
    [[ "$output" != *"tr should not run"* ]]
}

@test "setup time helpers use Bash formatting without date subprocesses" {
    local bash_libs_dir

    bash_libs_dir="$(base_bash_libs_fixture_dir)"
    create_date_logger_stub

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_common.sh"
            epoch="$(setup_epoch_seconds)" || exit $?
            stamp="$(setup_backup_timestamp)" || exit $?
            [[ "$epoch" =~ ^[0-9]+$ ]] || exit 10
            [[ "$stamp" =~ ^[0-9]{8}T[0-9]{6}$ ]] || exit 11
            printf "epoch=%s\n" "$epoch"
            printf "stamp=%s\n" "$stamp"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"epoch="* ]]
    [[ "$output" == *"stamp="* ]]
    [ ! -e "$TEST_STATE_DIR/date-args" ]
}

@test "setup_common documents UTC date subprocess exceptions" {
    local comment_count

    comment_count="$(
        grep -B2 "date -u '+%Y-%m-%dT%H:%M:%SZ'" \
            "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/setup_common.sh" |
            grep -Fc "Keep external date -u"
    )"
    [ "$comment_count" -eq 2 ]
}

@test "basectl setup fails on unsupported operating systems" {
    OSTYPE_OVERRIDE="linux-gnu"

    run_base_command setup

    [ "$status" -eq 1 ]
    [[ "$output" == *"supports macOS only"* ]]
}

@test "basectl setup is idempotent when brew, xcode tools, python, and the venv already exist" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    mkdir -p "$venv_dir/bin"
    : > "$venv_dir/pyvenv.cfg"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"
    cat > "$venv_dir/bin/python" <<'EOF'
#!/usr/bin/env bash
pyyaml_package="${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
click_package="${BASE_SETUP_CLICK_PACKAGE:-click}"
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    if [[ "$*" == *"--action route"* ]]; then
        printf 'base\t%s\t%s\t%s\tfalse\n' "$BASE_HOME" "$BASE_HOME/base_manifest.yaml" "$HOME/.base.d/base/.venv"
        exit 0
    fi
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-ran"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$pyyaml_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" && "${4:-}" == "--disable-pip-version-check" && "${5:-}" == "$pyyaml_package" ]]; then
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-install-ran"
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$click_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" && "${4:-}" == "--disable-pip-version-check" && "${5:-}" == "$click_package" ]]; then
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
    [[ "$output" != *"BATS formula 'bats-core'"* ]]
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

@test "basectl setup base ignores inherited project virtualenv" {
    local inherited_venv="$TEST_TMPDIR/inherited-base-venv"
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_project_setup_venv_stub "$venv_dir"
    create_project_setup_venv_stub "$inherited_venv"

    run_base_command BASE_PROJECT_VENV_DIR="$inherited_venv" setup

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/project-setup-python" ]
    [[ "$(cat "$TEST_STATE_DIR/project-setup-python")" == *"$venv_dir/bin/python"* ]]
    [[ "$(cat "$TEST_STATE_DIR/project-setup-python")" != *"$inherited_venv/bin/python"* ]]
}

@test "setup installs Base Python packages without pip self-version notices" {
    local bash_libs_dir
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    bash_libs_dir="$(base_bash_libs_fixture_dir)"
    mkdir -p "$venv_dir/bin"
    : > "$venv_dir/pyvenv.cfg"
    cat > "$venv_dir/bin/python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" ]]; then
    exit 1
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" ]]; then
    printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/pip-install-args"
    exit 0
fi
printf 'unexpected venv python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$venv_dir/bin/python"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE=darwin24 \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        BASE_SETUP_VENV_DIR="$venv_dir" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        bash -c 'source "$BASE_HOME/base_init.sh"; source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_common.sh"; setup_install_base_python_package requests'

    [ "$status" -eq 0 ]
    grep -Fxq -- "--disable-pip-version-check" "$TEST_STATE_DIR/pip-install-args"
}

@test "basectl setup installs missing dependencies and creates the Base virtual environment" {
    local installer
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_NOTIFY_MIN_SECONDS=999999 \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [[ "$output" == *"Installing Homebrew."* ]]
    [[ "$output" == *"Installing Xcode Command Line Tools."* ]]
    [[ "$output" == *"Xcode Command Line Tools installation detected."* ]]
    [[ "$output" == *"Installing Python formula 'python@3.13' via Homebrew."* ]]
    [[ "$output" != *"BATS formula 'bats-core'"* ]]
    [[ "$output" == *"Creating Python virtual environment at '$venv_dir'."* ]]
    [[ "$output" == *"Installing Python package 'PyYAML' in the Base virtual environment."* ]]
    [[ "$output" == *"Installing Python package 'click' in the Base virtual environment."* ]]
    [[ "$output" == *"Running Python project setup layer."* ]]
    [[ "$output" == *"Base CLI setup is complete."* ]]
    [ -f "$TEST_STATE_DIR/homebrew-install-ran" ]
    [ -f "$TEST_STATE_DIR/python-install-ran" ]
    [ ! -f "$TEST_STATE_DIR/bats-install-ran" ]
    [ -f "$TEST_STATE_DIR/pyyaml-install-ran" ]
    [ -f "$TEST_STATE_DIR/click-install-ran" ]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
    [ -f "$venv_dir/pyvenv.cfg" ]
}

@test "basectl setup seeds missing user config with workspace root" {
    local config_path="$TEST_HOME/.base.d/config.yaml"
    local installer

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_NOTIFY_MIN_SECONDS=999999 \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [[ "$output" == *"Created Base user config at '$config_path'."* ]]
    [ -f "$config_path" ]
    [ "$(cat "$config_path")" = $'workspace:\n  root: ~/work' ]
}

@test "basectl setup leaves existing user config unchanged" {
    local config_path="$TEST_HOME/.base.d/config.yaml"
    local installer

    mkdir -p "$(dirname "$config_path")"
    printf 'workspace:\n  root: ~/src\n' > "$config_path"
    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_NOTIFY_MIN_SECONDS=999999 \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [[ "$output" != *"Created Base user config"* ]]
    [ "$(cat "$config_path")" = $'workspace:\n  root: ~/src' ]
}

@test "basectl setup leaves user config symlinks unchanged" {
    local config_path="$TEST_HOME/.base.d/config.yaml"
    local config_target="$TEST_TMPDIR/synced-config.yaml"
    local installer

    mkdir -p "$(dirname "$config_path")"
    printf 'workspace:\n  root: ~/synced-work\n' > "$config_target"
    ln -s "$config_target" "$config_path"
    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_NOTIFY_MIN_SECONDS=999999 \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [[ "$output" != *"Created Base user config"* ]]
    [ -L "$config_path" ]
    [ "$(readlink "$config_path")" = "$config_target" ]
    [ "$(cat "$config_target")" = $'workspace:\n  root: ~/synced-work' ]
}

@test "basectl setup dry-run reports user config seed without writing it" {
    local config_path="$TEST_HOME/.base.d/config.yaml"

    run_base_command setup --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create Base user config at '$config_path'."* ]]
    [ ! -e "$config_path" ]
}

@test "basectl setup rejects Homebrew installer override outside test mode" {
    local installer

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_TEST_MODE=false \
        CI=false \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 1 ]
    [[ "$output" == *"BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT is a test-only setup override."* ]]
    [ ! -f "$TEST_STATE_DIR/homebrew-install-ran" ]
}

@test "basectl setup rejects Python binary override outside test mode" {
    local python_bin="$TEST_TMPDIR/fake-python"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    printf '#!/usr/bin/env bash\nexit 0\n' > "$python_bin"
    chmod +x "$python_bin"

    run_base_command \
        BASE_TEST_MODE=false \
        CI=false \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_PYTHON_BIN="$python_bin" \
        setup

    [ "$status" -eq 1 ]
    [[ "$output" == *"BASE_SETUP_PYTHON_BIN is a test-only setup override."* ]]
}

@test "basectl setup does not fall back to system python3 by default" {
    create_brew_stub
    create_xcode_stubs
    create_system_python3_stub
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"

    run_base_command setup

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unable to locate a python3 executable after installation."* ]]
    [ ! -f "$TEST_STATE_DIR/system-python-ran" ]
}

@test "basectl setup uses system python3 only when explicitly allowed" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    create_system_python3_stub
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"

    run_base_command BASE_SETUP_ALLOW_SYSTEM_PYTHON=true setup

    [ "$status" -eq 0 ]
    [[ "$output" == *"Creating Python virtual environment at '$venv_dir'."* ]]
    [ -f "$TEST_STATE_DIR/system-python-ran" ]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
}

@test "basectl setup skips notifications for quick successful runs" {
    local installer

    create_xcode_stubs
    create_osascript_stub
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [ ! -f "$TEST_STATE_DIR/osascript-args" ]
}

@test "basectl setup sends a best-effort success notification after the threshold" {
    local installer

    create_xcode_stubs
    create_osascript_stub
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_NOTIFY_MIN_SECONDS=0 \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/osascript-args" ]
    [[ "$(cat "$TEST_STATE_DIR/osascript-args")" == *"Base setup complete"* ]]
    [[ "$(cat "$TEST_STATE_DIR/osascript-args")" == *"Base CLI setup completed successfully."* ]]
}

@test "basectl setup --notify forces a notification for quick runs" {
    local installer

    create_xcode_stubs
    create_osascript_stub
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup --notify

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/osascript-args" ]
    [[ "$(cat "$TEST_STATE_DIR/osascript-args")" == *"Base setup complete"* ]]
    [[ "$(cat "$TEST_STATE_DIR/osascript-args")" == *"Base CLI setup completed successfully."* ]]
}

@test "basectl setup --notify warns when osascript is unavailable on macOS" {
    local no_osascript_path="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/bin:/usr/sbin:/sbin"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE=darwin24 \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_SETUP_TEST_NO_OSASCRIPT_PATH="$no_osascript_path" \
        BASE_SETUP_NOTIFY=true \
        BASE_SETUP_NOTIFY_FORCE=true \
        bash -c 'source "$BASE_HOME/base_init.sh"; source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_common.sh"; PATH="$BASE_SETUP_TEST_NO_OSASCRIPT_PATH"; setup_notify_completion 0'

    [ "$status" -eq 0 ]
    [[ "$output" == *"Setup notification was requested, but 'osascript' is not available on this Mac."* ]]
}

@test "basectl setup forwards project setup arguments through the project wrapper" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local demo_venv_dir="$TEST_HOME/.base.d/demo/.venv"
    local manifest_path="$TEST_TMPDIR/demo_manifest.yaml"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_project_setup_venv_stub "$base_venv_dir"
    create_project_setup_venv_stub "$demo_venv_dir"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$manifest_path"

    run_base_command setup --dry-run --manifest "$manifest_path" demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"Running Python project setup layer."* ]]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --dry-run --manifest "$manifest_path" --action setup demo)" ]
}

@test "basectl setup project --recreate-venv targets the project virtualenv" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local demo_venv_dir="$TEST_HOME/.base.d/demo/.venv"
    local manifest_path="$TEST_TMPDIR/demo_manifest.yaml"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_project_setup_venv_stub "$base_venv_dir"
    create_project_setup_venv_stub "$demo_venv_dir"
    printf 'base marker\n' > "$base_venv_dir/old.txt"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$manifest_path"

    run_base_command setup --dry-run --manifest "$manifest_path" --recreate-venv demo

    [ "$status" -eq 0 ]
    [[ "$output" != *"Would move existing virtual environment '$base_venv_dir'"* ]]
    [ -f "$base_venv_dir/old.txt" ]
    [ "$(cat "$TEST_STATE_DIR/project-bootstrap-recreate-venv")" = "true" ]
}

@test "basectl setup infers project name from explicit manifest" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local demo_venv_dir="$TEST_HOME/.base.d/demo/.venv"
    local project_root="$TEST_TMPDIR/demo"
    local resolved_project_root
    local manifest_path="$project_root/base_manifest.yaml"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$project_root"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_project_setup_venv_stub "$base_venv_dir"
    create_project_setup_venv_stub "$demo_venv_dir"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$manifest_path"
    resolved_project_root="$(cd "$project_root" && pwd -P)"

    run_base_command setup --dry-run --manifest "$manifest_path"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved project 'demo' at '$resolved_project_root'."* ]]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --dry-run --manifest "$manifest_path" --action setup demo)" ]
}

@test "basectl setup uv-managed project does not bootstrap historical Base project venv" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local project_root="$TEST_TMPDIR/demo"
    local manifest_path="$project_root/base_manifest.yaml"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$project_root"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_project_setup_venv_stub "$base_venv_dir"
    printf 'project:\n  name: demo\npython:\n  manager: uv\nartifacts: []\n' > "$manifest_path"

    run_base_command setup --dry-run --manifest "$manifest_path"

    [ "$status" -eq 0 ]
    [[ "$output" != *"Would create project virtual environment at '$TEST_HOME/.base.d/demo/.venv'"* ]]
    [[ "$output" != *"Would run Python project setup layer through base-wrapper"* ]]
    [ ! -e "$TEST_HOME/.base.d/demo/.venv" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --dry-run --manifest "$manifest_path" --action setup demo)" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
}

@test "project setup resolves named project manifests from the workspace" {
    local base_venv_dir="$TEST_HOME/.base.d/base/.venv"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$workspace/brew"
    printf 'project:\n  name: brew\nartifacts: []\n' > "$workspace/brew/base_manifest.yaml"
    create_project_setup_venv_stub "$base_venv_dir"
    create_project_setup_venv_stub "$TEST_HOME/.base.d/brew/.venv"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_SETUP_PROJECT_NAME=brew \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_WORKSPACE="$workspace" \
        BASE_SETUP_VENV_DIR="$base_venv_dir" \
        bash -c '
            source "$1/base_init.sh"
            source "$1/cli/bash/commands/basectl/subcommands/setup_common.sh"
            setup_run_project_artifact_setup
        ' _ "$BASE_REPO_ROOT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved project 'brew' at '$workspace/brew'."* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "brew" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/brew/base_manifest.yaml" --action setup brew)" ]
}

@test "basectl setup propagates Python project setup failure" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_project_setup_venv_stub "$venv_dir" 42

    run_base_command setup

    [ "$status" -eq 42 ]
    [[ "$output" == *"Python project setup layer failed."* ]]
    [[ "$output" == *"Review the Python error above, then rerun 'basectl setup -v' for more detail."* ]]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
}

@test "basectl setup gives recovery guidance when Xcode install needs an interactive terminal" {
    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/python-installed"

    run_base_command setup

    [ "$status" -eq 1 ]
    [[ "$output" == *"Xcode Command Line Tools installation requires an interactive terminal."* ]]
    [[ "$output" == *"Run 'xcode-select --install' in an interactive terminal, complete the installer, then rerun 'basectl setup'."* ]]
}

@test "basectl setup sends a best-effort failure notification after the threshold" {
    create_brew_stub
    create_xcode_stubs
    create_osascript_stub
    touch "$TEST_STATE_DIR/python-installed"

    run_base_command BASE_SETUP_NOTIFY_MIN_SECONDS=0 setup

    [ "$status" -eq 1 ]
    [ -f "$TEST_STATE_DIR/osascript-args" ]
    [[ "$(cat "$TEST_STATE_DIR/osascript-args")" == *"Base setup failed"* ]]
    [[ "$(cat "$TEST_STATE_DIR/osascript-args")" == *"Base CLI setup failed. Check the terminal for details."* ]]
}

@test "basectl setup skips notifications during dry-run" {
    create_osascript_stub

    run_base_command setup --dry-run

    [ "$status" -eq 0 ]
    [ ! -f "$TEST_STATE_DIR/osascript-args" ]
}

@test "basectl setup --no-notify disables setup notifications" {
    local installer

    create_xcode_stubs
    create_osascript_stub
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup --no-notify

    [ "$status" -eq 0 ]
    [ ! -f "$TEST_STATE_DIR/osascript-args" ]
}

@test "BASE_SETUP_NOTIFY=false disables setup notifications" {
    local installer

    create_xcode_stubs
    create_osascript_stub
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_NOTIFY=false \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [ ! -f "$TEST_STATE_DIR/osascript-args" ]
}

@test "basectl setup --profile dev runs the Python developer prerequisite layer" {
    local installer

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup --profile dev

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/dev-setup-ran" ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' setup --profile dev)" ]
}

@test "basectl setup --profile sre runs the Python prerequisite profile layer" {
    local installer

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup --profile sre

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/dev-setup-ran" ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' setup --profile sre)" ]
}

@test "basectl setup --profile ai runs the Python prerequisite profile layer" {
    local installer

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup --profile ai

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/dev-setup-ran" ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' setup --profile ai)" ]
}

@test "basectl setup accepts comma separated profile lists case-insensitively" {
    local installer

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup --profile dev,SRE,AI

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/dev-setup-ran" ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "$(printf '%s\n' setup --profile dev,sre,ai)" ]
}

@test "basectl setup rejects unknown profiles" {
    run_base_command setup --profile ops

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported profile 'ops'. Expected one of: dev, sre, ai."* ]]
}

@test "basectl setup rejects empty profile list entries" {
    run_base_command setup --profile dev,,sre

    [ "$status" -eq 2 ]
    [[ "$output" == *"Profile list must not contain empty entries."* ]]
}

@test "basectl setup backs up an existing non-venv path before creating the Base virtual environment" {
    local backup_path
    local installer
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"
    mkdir -p "$venv_dir"
    printf 'stale content\n' > "$venv_dir/stale.txt"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup

    [ "$status" -eq 0 ]
    [[ "$output" == *"Moving existing non-venv path '$venv_dir' to '$venv_dir.backup."* ]]
    [[ "$output" == *"Creating Python virtual environment at '$venv_dir'."* ]]
    backup_path="$(find "$TEST_HOME/.base.d/base" -maxdepth 1 -type d -name '.venv.backup.*' -print)"
    [[ -n "$backup_path" ]]
    [ -f "$backup_path/stale.txt" ]
    [ -f "$venv_dir/pyvenv.cfg" ]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
}

@test "basectl setup dry-run reports backup for an existing non-venv path without moving it" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    mkdir -p "$venv_dir"
    printf 'stale content\n' > "$venv_dir/stale.txt"

    run_base_command setup --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would move existing non-venv path '$venv_dir' to '$venv_dir.backup."* ]]
    [[ "$output" == *"[DRY-RUN] Would create Python virtual environment at '$venv_dir'."* ]]
    [ -f "$venv_dir/stale.txt" ]
    [ -z "$(find "$TEST_HOME/.base.d/base" -maxdepth 1 -type d -name '.venv.backup.*' -print)" ]
}

@test "basectl setup --recreate-venv backs up a valid venv before creating a fresh one" {
    local backup_path
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/bats-installed"
    mkdir -p "$venv_dir/bin"
    printf 'python-home = old\n' > "$venv_dir/pyvenv.cfg"
    printf 'old venv marker\n' > "$venv_dir/old.txt"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"

    run_base_command setup --recreate-venv

    [ "$status" -eq 0 ]
    [[ "$output" == *"Moving existing virtual environment '$venv_dir' to '$venv_dir.backup."* ]]
    [[ "$output" == *"Creating Python virtual environment at '$venv_dir'."* ]]
    backup_path="$(find "$TEST_HOME/.base.d/base" -maxdepth 1 -type d -name '.venv.backup.*' -print)"
    [[ -n "$backup_path" ]]
    [ -f "$backup_path/old.txt" ]
    [ -f "$venv_dir/pyvenv.cfg" ]
    [ ! -f "$venv_dir/old.txt" ]
    [ -f "$TEST_STATE_DIR/project-setup-ran" ]
}

@test "basectl setup --recreate-venv dry-run reports rebuild without moving a valid venv" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    mkdir -p "$venv_dir/bin"
    printf 'python-home = old\n' > "$venv_dir/pyvenv.cfg"
    printf 'old venv marker\n' > "$venv_dir/old.txt"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"

    run_base_command setup --dry-run --recreate-venv

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would move existing virtual environment '$venv_dir' to '$venv_dir.backup."* ]]
    [[ "$output" == *"[DRY-RUN] Would create Python virtual environment at '$venv_dir'."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python package 'PyYAML' in the Base virtual environment."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python package 'click' in the Base virtual environment."* ]]
    [[ "$output" == *"[DRY-RUN] Would run Python project setup layer after PyYAML is installed."* ]]
    [ -f "$venv_dir/old.txt" ]
    [ -z "$(find "$TEST_HOME/.base.d/base" -maxdepth 1 -type d -name '.venv.backup.*' -print)" ]
}

@test "basectl setup supports dry-run without making changes" {
    run_base_command setup --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh>"* ]]
    [[ "$output" == *"[DRY-RUN] Would install Xcode Command Line Tools and wait for installation to complete."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python formula 'python@3.13' via Homebrew."* ]]
    [[ "$output" != *"BATS formula 'bats-core'"* ]]
    [[ "$output" == *"[DRY-RUN] Would create Python virtual environment at '$TEST_HOME/.base.d/base/.venv'."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python package 'PyYAML' in the Base virtual environment."* ]]
    [[ "$output" == *"[DRY-RUN] Would install Python package 'click' in the Base virtual environment."* ]]
    [[ "$output" == *"[DRY-RUN] Would run Python project setup layer after PyYAML is installed."* ]]
    [[ "$output" == *"[DRY-RUN] Base CLI setup check is complete."* ]]
    [ ! -e "$TEST_HOME/.base.d/base/.venv" ]
}

@test "basectl setup dry-run reports pinned Homebrew installer verification" {
    local installer
    local checksum

    installer="$(create_homebrew_installer_stub)"
    checksum="$(sha256_file "$installer")"

    run_base_command \
        BASE_HOMEBREW_INSTALLER_URL="$installer" \
        BASE_HOMEBREW_INSTALLER_SHA256="$checksum" \
        setup --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Using pinned Homebrew installer from $installer."* ]]
    [[ "$output" == *"[DRY-RUN] Would verify Homebrew installer SHA-256 $checksum"* ]]
    [[ "$output" == *"[DRY-RUN] Would run: /bin/bash <verified Homebrew installer from $installer>"* ]]
}

@test "basectl setup rejects pinned Homebrew installer without checksum" {
    local installer

    create_curl_failure_stub
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_HOMEBREW_INSTALLER_URL="$installer" \
        setup

    [ "$status" -eq 1 ]
    [[ "$output" == *"Pinned Homebrew installer URL and SHA-256 are both required."* ]]
    [ ! -e "$TEST_STATE_DIR/homebrew-install-ran" ]
}

@test "basectl setup rejects pinned Homebrew checksum without installer location" {
    run_base_command \
        BASE_SETUP_HOMEBREW_INSTALLER_SHA256=0000000000000000000000000000000000000000000000000000000000000000 \
        setup --dry-run

    [ "$status" -eq 1 ]
    [[ "$output" == *"Pinned Homebrew installer URL and SHA-256 are both required."* ]]
    [ ! -e "$TEST_STATE_DIR/homebrew-install-ran" ]
}

@test "basectl setup rejects mismatched pinned Homebrew installer checksum" {
    local installer

    create_curl_failure_stub
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_HOMEBREW_INSTALLER_URL="$installer" \
        BASE_SETUP_HOMEBREW_INSTALLER_SHA256=0000000000000000000000000000000000000000000000000000000000000000 \
        setup

    [ "$status" -eq 1 ]
    [[ "$output" == *"Homebrew installer checksum mismatch"* ]]
    [ ! -e "$TEST_STATE_DIR/homebrew-install-ran" ]
}

@test "basectl setup runs verified pinned Homebrew installer" {
    local installer
    local checksum
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_curl_failure_stub
    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"
    checksum="$(sha256_file "$installer")"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_URL="$installer" \
        BASE_SETUP_HOMEBREW_INSTALLER_SHA256="$checksum" \
        setup

    [ "$status" -eq 0 ]
    [[ "$output" == *"Using pinned Homebrew installer from $installer."* ]]
    [ -f "$TEST_STATE_DIR/homebrew-install-ran" ]
    [ -f "$venv_dir/pyvenv.cfg" ]
}

@test "basectl setup --profile dev dry-run defers developer prerequisites until Python bootstrap dependencies exist" {
    run_base_command setup --profile dev --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run Python prerequisite profile layer after Base Python bootstrap dependencies are installed."* ]]
}

@test "basectl setup ignores inherited DRY_RUN without --dry-run" {
    local installer
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

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
