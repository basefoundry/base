#!/usr/bin/env bats

load ../../../../../lib/bash/tests/test_helper.sh
bats_require_minimum_version 1.5.0

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
            mkdir -p "$tools_dir/usr/bin"
            touch "$tools_dir/usr/bin/clang"
            printf '%s\n' "$tools_dir"
            exit 0
        fi
        exit 1
        ;;
    --install)
        touch "$installed_file"
        mkdir -p "$tools_dir/usr/bin"
        touch "$tools_dir/usr/bin/clang"
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

create_osascript_stub() {
    cat > "$TEST_MOCKBIN/osascript" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/osascript-args"
EOF
    chmod +x "$TEST_MOCKBIN/osascript"
}

create_system_python3_stub() {
    cat > "$TEST_MOCKBIN/python3" <<'EOF'
#!/usr/bin/env bash
touch "${BASE_SETUP_TEST_STATE_DIR:?}/system-python-ran"
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" && -n "${3:-}" ]]; then
    mkdir -p "$3/bin"
    printf 'python-home = system-test\n' > "$3/pyvenv.cfg"
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
printf 'unexpected system venv python args: %s\n' "$*" >&2
exit 1
VENVEOF
    chmod +x "$3/bin/python"
    exit 0
fi
printf 'unexpected system python3 args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/python3"
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
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" ]]; then
    shift 2
    printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/dev-args"
    case "${1:-}" in
        setup)
            touch "${BASE_SETUP_TEST_STATE_DIR:?}/dev-setup-ran"
            exit 0
            ;;
        check)
            if [[ "${2:-}" == "--format" && "${3:-}" == "json" ]]; then
                printf '[{"name":"bats-core","ok":false,"message":"Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.","fix":"basectl setup --dev"},{"name":"gh","ok":false,"message":"Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.","fix":"basectl setup --dev"}]\n'
            else
                printf 'Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.\n' >&2
                printf 'Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.\n' >&2
            fi
            exit 1
            ;;
    esac
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
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" ]]; then
    shift 2
    printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/dev-args"
    case "${1:-}" in
        setup)
            touch "${BASE_SETUP_TEST_STATE_DIR:?}/dev-setup-ran"
            exit 0
            ;;
        check)
            if [[ "${2:-}" == "--format" && "${3:-}" == "json" ]]; then
                printf '[{"name":"bats-core","ok":false,"message":"Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.","fix":"basectl setup --dev"},{"name":"gh","ok":false,"message":"Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.","fix":"basectl setup --dev"}]\n'
            else
                printf 'Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.\n' >&2
                printf 'Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.\n' >&2
            fi
            exit 1
            ;;
    esac
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
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" ]]; then
    shift 2
    printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/dev-args"
    case "${1:-}" in
        setup)
            touch "${BASE_SETUP_TEST_STATE_DIR:?}/dev-setup-ran"
            exit 0
            ;;
        check)
            if [[ "${2:-}" == "--format" && "${3:-}" == "json" ]]; then
                printf '[{"name":"bats-core","ok":false,"message":"Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.","fix":"basectl setup --dev"},{"name":"gh","ok":false,"message":"Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.","fix":"basectl setup --dev"}]\n'
            else
                printf 'Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.\n' >&2
                printf 'Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.\n' >&2
            fi
            exit 1
            ;;
    esac
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
        BASE_TEST_MODE=true \
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

create_base_venv_stub() {
    local venv_dir="${1:-$TEST_HOME/.base.d/base/.venv}"

    mkdir -p "$venv_dir/bin"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"
    cat > "$venv_dir/bin/python" <<'EOF'
#!/usr/bin/env bash
pyyaml_package="${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
click_package="${BASE_SETUP_CLICK_PACKAGE:-click}"
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$pyyaml_package" ]]; then
    printf '%s\n' "$4" >> "${BASE_SETUP_TEST_STATE_DIR:?}/pip-show.log"
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$click_package" ]]; then
    printf '%s\n' "$4" >> "${BASE_SETUP_TEST_STATE_DIR:?}/pip-show.log"
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" ]]; then
    shift 2
    printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/dev-args"
    case "${1:-}" in
        check)
            if [[ "${2:-}" == "--format" && "${3:-}" == "json" ]]; then
                printf '[{"name":"bats-core","ok":false,"message":"Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.","fix":"basectl setup --dev"},{"name":"gh","ok":false,"message":"Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.","fix":"basectl setup --dev"}]\n'
            else
                printf 'Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.\n' >&2
                printf 'Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.\n' >&2
            fi
            exit 1
            ;;
    esac
fi
printf 'unexpected check venv python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$venv_dir/bin/python"
}

create_project_setup_venv_stub() {
    local exit_code="${2:-0}"
    local venv_dir="${1:-$TEST_HOME/.base.d/base/.venv}"

    mkdir -p "$venv_dir/bin"
    printf '#!/usr/bin/env bash\n' > "$venv_dir/bin/activate"
    cat > "$venv_dir/bin/python" <<'EOF'
#!/usr/bin/env bash
pyyaml_package="${BASE_SETUP_PYYAML_PACKAGE:-PyYAML}"
click_package="${BASE_SETUP_CLICK_PACKAGE:-click}"
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    shift 2
    printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-args"
    printf '%s\n' "${BASE_PROJECT:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-project"
    touch "$BASE_SETUP_TEST_STATE_DIR/project-setup-ran"
    action="setup"
    output_format="text"
    while (($#)); do
        case "$1" in
            --action)
                shift
                action="${1:-}"
                ;;
            --format)
                shift
                output_format="${1:-}"
                ;;
        esac
        shift || true
    done
    if [[ "$action" == "check" && "$output_format" == "json" ]]; then
        printf '[{"name":"demo-artifact","ok":true,"message":"Project artifact check passed.","fix":""}]\n'
    elif [[ "$action" == "check" ]]; then
        printf 'Project artifact check passed.\n' >&2
    elif [[ "$action" == "doctor" ]]; then
        printf 'ok     demo-artifact               Project artifact check passed.\n'
    fi
    exit "$(cat "$BASE_SETUP_TEST_STATE_DIR/project-setup-exit-code")"
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" ]]; then
    project="${4:-}"
    project_root="${BASE_SETUP_TEST_WORKSPACE:?}/$project"
    manifest_path="$project_root/base_manifest.yaml"
    if [[ -f "$manifest_path" ]]; then
        printf '%s\t%s\t%s\n' "$project" "$project_root" "$manifest_path"
        exit 0
    fi
    printf 'Project not found: %s\n' "$project" >&2
    exit 1
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "manifest" ]]; then
    manifest_path="${4:-}"
    if [[ -f "$manifest_path" ]]; then
        project="$(awk '/^[[:space:]]*name:/ { print $2; exit }' "$manifest_path")"
        project_root="$(cd -- "$(dirname -- "$manifest_path")" && pwd -P)"
        printf '%s\t%s\t%s\n' "$project" "$project_root" "$manifest_path"
        exit 0
    fi
    printf 'Manifest not found: %s\n' "$manifest_path" >&2
    exit 1
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$pyyaml_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/pyyaml-installed" ]]
    exit $?
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "show" && "${4:-}" == "$click_package" ]]; then
    [[ -f "${BASE_SETUP_TEST_STATE_DIR:?}/click-installed" ]]
    exit $?
fi
printf 'unexpected project setup venv python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$venv_dir/bin/python"
    printf '%s\n' "$exit_code" > "$TEST_STATE_DIR/project-setup-exit-code"
}

@test "basectl setup prints usage for help" {
    run_base_command setup --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl setup [options]"* ]]
    [[ "$output" == *"--dev"* ]]
    [[ "$output" == *"--notify"* ]]
    [[ "$output" == *"--no-notify"* ]]
    [[ "$output" == *"--recreate-venv"* ]]
    [[ "$output" == *"Prepare the local Base CLI environment on macOS."* ]]
}

@test "basectl check prints usage for help" {
    run_base_command check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl check [project] [options]"* ]]
    [[ "$output" == *"--dev"* ]]
    [[ "$output" == *"Verify the local Base CLI environment and, when provided, project artifacts on macOS without making changes."* ]]
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
    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/bin:/usr/sbin:/sbin" \
        OSTYPE=darwin24 \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_SETUP_NOTIFY=true \
        BASE_SETUP_NOTIFY_FORCE=true \
        bash -c 'source "$BASE_HOME/lib/bash/std/lib_std.sh"; source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_common.sh"; setup_notify_completion 0'

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

@test "basectl setup --dev runs the Python developer prerequisite layer" {
    local installer

    create_xcode_stubs
    installer="$(create_homebrew_installer_stub)"

    run_base_command \
        BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL=true \
        BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT="$installer" \
        setup --dev

    [ "$status" -eq 0 ]
    [ -f "$TEST_STATE_DIR/dev-setup-ran" ]
    [ "$(cat "$TEST_STATE_DIR/dev-args")" = "setup" ]
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
    [[ "$output" == *"[DRY-RUN] Would install Homebrew using the official installer."* ]]
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

@test "basectl setup --dev dry-run defers developer prerequisites until Python bootstrap dependencies exist" {
    run_base_command setup --dev --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would run Python developer prerequisite layer after Base Python bootstrap dependencies are installed."* ]]
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

@test "basectl check passes when all required components are present" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check

    [ "$status" -eq 0 ]
    [[ "$output" == *"Homebrew is installed."* ]]
    [[ "$output" == *"Xcode Command Line Tools are installed."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is installed via Homebrew."* ]]
    [[ "$output" != *"BATS formula 'bats-core'"* ]]
    [[ "$output" == *"Virtual environment exists at '$venv_dir'."* ]]
    [[ "$output" == *"Python package 'PyYAML' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Python package 'click' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
    [ "$(grep -c '^PyYAML$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
    [ "$(grep -c '^click$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
}

@test "basectl check ignores inherited setup dry-run and recreate state" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command \
        DRY_RUN=true \
        BASE_SETUP_RECREATE_VENV=true \
        check

    [ "$status" -eq 0 ]
    [[ "$output" == *"Python package 'PyYAML' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Python package 'click' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check passed."* ]]
    [ "$(grep -c '^PyYAML$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
    [ "$(grep -c '^click$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
}

@test "basectl check fails when a required Base Python package is missing" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check

    [ "$status" -eq 1 ]
    [[ "$output" == *"Virtual environment exists at '$venv_dir'."* ]]
    [[ "$output" == *"Python package 'PyYAML' is not installed in the Base virtual environment."* ]]
    [[ "$output" == *"Run 'basectl setup' to install Base Python bootstrap packages."* ]]
    [[ "$output" == *"Python package 'click' is installed in the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
    [ "$(grep -c '^PyYAML$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
    [ "$(grep -c '^click$' "$TEST_STATE_DIR/pip-show.log")" -eq 1 ]
}

@test "basectl check --dev includes manifest-driven developer prerequisite checks" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run_base_command check --dev

    [ "$status" -eq 1 ]
    [[ "$output" == *"Artifact 'bats-core' is not installed via Homebrew package 'bats-core'."* ]]
    [[ "$output" == *"Artifact 'gh' is not installed via Homebrew package 'gh'."* ]]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
}

@test "basectl check project verifies project artifacts" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"
    local workspace="$TEST_TMPDIR/workspace"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$TEST_HOME/.base.d/demo/.venv"

    run_base_command BASE_SETUP_TEST_WORKSPACE="$workspace" check demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolved project 'demo' at '$workspace/demo'."* ]]
    [[ "$output" == *"Running Python project check layer."* ]]
    [[ "$output" == *"Project artifact check passed."* ]]
    [[ "$output" == *"Base CLI environment and project 'demo' check passed."* ]]
    [ "$(cat "$TEST_STATE_DIR/project-setup-project")" = "demo" ]
    [ "$(cat "$TEST_STATE_DIR/project-setup-args")" = "$(printf '%s\n' --manifest "$workspace/demo/base_manifest.yaml" --action check --format text demo)" ]
}

@test "basectl check --format json writes successful check results to stdout" {
    local click_line
    local pyyaml_line
    local venv_line
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"ok": true'* ]]
    [[ "$output" == *'"name":"homebrew","ok":true'* ]]
    [[ "$output" != *'"name":"bats"'* ]]
    [[ "$output" == *'"name":"pyyaml","ok":true'* ]]
    [[ "$output" == *'"name":"click","ok":true'* ]]
    [[ "$output" == *'"name":"base_virtualenv","ok":true'* ]]
    venv_line="$(printf '%s\n' "$output" | grep -n '"name":"base_virtualenv"' | cut -d: -f1)"
    pyyaml_line="$(printf '%s\n' "$output" | grep -n '"name":"pyyaml"' | cut -d: -f1)"
    click_line="$(printf '%s\n' "$output" | grep -n '"name":"click"' | cut -d: -f1)"
    [ "$venv_line" -lt "$pyyaml_line" ]
    [ "$pyyaml_line" -lt "$click_line" ]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --format json escapes all C0 control characters in strings" {
    local control_package
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    control_package=$'Py\vYAML'
    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_PYYAML_PACKAGE="$control_package" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *"Py\\u000bYAML"* ]]
    [[ "$output" != *"$control_package"* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check project --format json includes project check results" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"
    local workspace="$TEST_TMPDIR/workspace"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools" "$workspace/demo"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/bats-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$venv_dir"
    BASE_SETUP_TEST_WORKSPACE="$workspace" create_project_setup_venv_stub "$TEST_HOME/.base.d/demo/.venv"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_TEST_WORKSPACE="$workspace" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check demo --format json

    [ "$status" -eq 0 ]
    [[ "$output" == *'"project": "demo"'* ]]
    [[ "$output" == *'"project_checks":'* ]]
    [[ "$output" == *'"name":"demo-artifact","ok":true'* || "$output" == *'"name": "demo-artifact"'* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --dev --format json includes developer prerequisite check results" {
    local venv_dir="$TEST_HOME/.base.d/base/.venv"

    create_brew_stub
    create_xcode_stubs
    touch "$TEST_STATE_DIR/xcode-installed"
    mkdir -p "$TEST_TMPDIR/CommandLineTools"
    touch "$TEST_STATE_DIR/python-installed"
    touch "$TEST_STATE_DIR/pyyaml-installed"
    touch "$TEST_STATE_DIR/click-installed"
    create_base_venv_stub "$venv_dir"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --dev --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"ok": false'* ]]
    [[ "$output" == *'"dev_checks":'* ]]
    [[ "$output" == *"bats-core"* ]]
    [[ "$output" == *"gh"* ]]
    [[ "$output" == *'"name":"pyyaml","ok":true'* ]]
    [[ "$output" == *'"name":"click","ok":true'* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check --format json writes failed check results to stdout" {
    create_xcode_stubs

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$TEST_BASH_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin" \
        OSTYPE="darwin24" \
        BASE_SETUP_BREW_BIN="$TEST_MOCKBIN/brew" \
        BASE_SETUP_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_SETUP_TEST_MOCKBIN="$TEST_MOCKBIN" \
        BASE_SETUP_TEST_PYTHON_PREFIX="$TEST_TMPDIR/python-prefix" \
        BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR="$TEST_TMPDIR/CommandLineTools" \
        "$BASE_REPO_ROOT/bin/basectl" check --format json

    [ "$status" -eq 1 ]
    [[ "$output" == *'"ok": false'* ]]
    [[ "$output" == *'"name":"homebrew","ok":false'* ]]
    [[ "$output" == *'"name":"pyyaml","ok":false'* ]]
    [[ "$output" == *'"name":"click","ok":false'* ]]
    [[ "$output" == *'"name":"base_virtualenv","ok":false'* ]]
    [[ "$output" == *"Virtual environment is missing at '$TEST_HOME/.base.d/base/.venv'."* ]]
    [ "${stderr:-}" = "" ]
}

@test "basectl check fails when required components are missing" {
    run_base_command check

    [ "$status" -eq 1 ]
    [[ "$output" == *"Homebrew is not installed."* ]]
    [[ "$output" == *"Run 'basectl setup' to install Homebrew, or install it manually from https://brew.sh/."* ]]
    [[ "$output" == *"Xcode Command Line Tools are not installed."* ]]
    [[ "$output" == *"Run 'xcode-select --install' in an interactive terminal, complete the installer, then rerun 'basectl setup'."* ]]
    [[ "$output" == *"Python formula 'python@3.13' is not installed via Homebrew."* ]]
    [[ "$output" == *"Run 'basectl setup' to install Homebrew Python, or run 'brew install python@3.13'."* ]]
    [[ "$output" != *"BATS formula 'bats-core'"* ]]
    [[ "$output" == *"Virtual environment is missing at '$TEST_HOME/.base.d/base/.venv'."* ]]
    [[ "$output" == *"Run 'basectl setup --recreate-venv' to back up and recreate the Base virtual environment."* ]]
    [[ "$output" == *"Base CLI environment check found missing requirements."* ]]
    [[ "$output" == *"Run 'basectl setup' to reconcile the missing requirements."* ]]
}

@test "basectl check rejects unsupported output formats" {
    run_base_command check --format xml

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unsupported check output format 'xml'."* ]]
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
    [[ "$(cat "$TEST_HOME/.bashrc")" != *"completion"* ]]
    [[ "$(cat "$TEST_HOME/.bashrc")" != *"PATH="* ]]
    [[ "$(cat "$TEST_HOME/.zprofile")" == *"# --- BEGIN base zprofile MANAGED SECTION - DO NOT EDIT ---"* ]]
    [[ "$(cat "$TEST_HOME/.zprofile")" == *"source $BASE_REPO_ROOT/lib/shell/zprofile"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" == *"# --- BEGIN base zshrc MANAGED SECTION - DO NOT EDIT ---"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" == *"source $BASE_REPO_ROOT/lib/shell/zshrc"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" != *"completion"* ]]
    [[ "$(cat "$TEST_HOME/.zshrc")" != *"PATH="* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_PROFILE_VERSION=1"* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_BASH_DEFAULTS=false"* ]]
    [[ "$(cat "$TEST_HOME/.base.d/profile.conf")" == *"BASE_ENABLE_ZSH_DEFAULTS=false"* ]]
}

@test "Base-managed Bash startup registers basectl completion and project names" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$base_python")"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "list" ]]; then
    printf 'base\t/Users/test/base\n'
    printf 'demo\t/Users/test/demo\n'
    exit 0
fi
printf 'unexpected completion python args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$base_python"

    run_base_command update-profile
    [ "$status" -eq 0 ]

    run env -u BASE_HOME -u BASE_HOST -u BASE_OS \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        bash --rcfile "$TEST_HOME/.bashrc" -i -c '\
            complete -p basectl; \
            COMP_WORDS=(basectl activate ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "activate_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl activate demo --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "activate_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl check ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "check_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl doctor ""); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "doctor_projects=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl check --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "check_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl projects list --); \
            COMP_CWORD=3; \
            _base_basectl_completion; \
            printf "projects_options=%s\n" "${COMPREPLY[*]}"; \
            COMP_WORDS=(basectl onboard --); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "onboard_options=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"complete -F _base_basectl_completion basectl"* ]]
    [[ "$output" == *"activate_projects=base demo"* ]]
    [[ "$output" == *"activate_options=--workspace --no-cd"* ]]
    [[ "$output" == *"check_projects=base demo"* ]]
    [[ "$output" == *"doctor_projects=base demo"* ]]
    [[ "$output" == *"check_options=--dev --format"* ]]
    [[ "$output" == *"projects_options=--workspace --format"* ]]
    [[ "$output" == *"onboard_options=--dev --dry-run --yes --no-profile"* ]]
}

@test "Bash completion includes setup notification options" {
    run env \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '\
            source "$BASE_HOME/lib/shell/completions/basectl_completion.sh"; \
            COMP_WORDS=(basectl setup --no); \
            COMP_CWORD=2; \
            _base_basectl_completion; \
            printf "reply=%s\n" "${COMPREPLY[*]}"'

    [ "$status" -eq 0 ]
    [[ "$output" == *"--notify"* ]]
    [[ "$output" == *"--no-notify"* ]]
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
