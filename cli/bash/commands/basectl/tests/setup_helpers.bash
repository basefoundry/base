# Shared helpers for basectl setup/check/profile BATS suites.

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
            if [[ "${BASE_SETUP_TEST_XCODE_WAIT_FOR_PIP_SHOW:-}" == true ]]; then
                waited=0
                wait_seconds="${BASE_SETUP_TEST_XCODE_PIP_WAIT_SECONDS:-5}"
                while [[ ! -s "$state_dir/pip-show.log" && "$waited" -lt "$wait_seconds" ]]; do
                    sleep 1
                    waited=$((waited + 1))
                done
                [[ -s "$state_dir/pip-show.log" ]] || exit 1
            fi
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
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
    exit 0
fi
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
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
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
                printf '{"schema_version":1,"status":"error","profiles":["dev"],"checks":[{"id":"BASE-D104","status":"error","name":"bats-core","message":"Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.","fix":"basectl setup --profile dev"},{"id":"BASE-D104","status":"error","name":"gh","message":"Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.","fix":"basectl setup --profile dev"}]}\n'
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
                printf '{"schema_version":1,"status":"error","profiles":["dev"],"checks":[{"id":"BASE-D104","status":"error","name":"bats-core","message":"Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.","fix":"basectl setup --profile dev"},{"id":"BASE-D104","status":"error","name":"gh","message":"Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.","fix":"basectl setup --profile dev"}]}\n'
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
if [[ "${1:-}" == "--version" ]]; then
    printf 'Python 3.13.test\n'
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
                printf '{"schema_version":1,"status":"error","profiles":["dev"],"checks":[{"id":"BASE-D104","status":"error","name":"bats-core","message":"Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.","fix":"basectl setup --profile dev"},{"id":"BASE-D104","status":"error","name":"gh","message":"Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.","fix":"basectl setup --profile dev"}]}\n'
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
                printf '{"schema_version":1,"status":"error","profiles":["dev"],"checks":[{"id":"BASE-D104","status":"error","name":"bats-core","message":"Artifact '\''bats-core'\'' is not installed via Homebrew package '\''bats-core'\''.","fix":"basectl setup --profile dev"},{"id":"BASE-D104","status":"error","name":"gh","message":"Artifact '\''gh'\'' is not installed via Homebrew package '\''gh'\''.","fix":"basectl setup --profile dev"}]}\n'
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
    shift 2
    printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-args"
    printf '%s\n' "${BASE_PROJECT:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-project"
    printf '%s\n' "${BASE_CI:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-base-ci"
    printf '%s\n' "${CI:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-ci"
    printf '%s\n' "${BASE_SETUP_NOTIFY:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-notify"
    touch "$BASE_SETUP_TEST_STATE_DIR/project-setup-ran"
    action="setup"
    output_format="text"
    remote_network=false
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
            --remote-network)
                remote_network=true
                ;;
        esac
        shift || true
    done
    if [[ "$action" == "precheck" && "$output_format" == "json" ]]; then
        if [[ "$remote_network" == true ]]; then
            printf '[{"id":"BASE-P080","status":"ok","name":"git_repository","message":"Project is inside a Git repository.","fix":""},{"id":"BASE-P083","status":"ok","name":"git_origin_reachability","message":"Project Git origin remote is reachable.","fix":""}]\n'
        else
            printf '[{"id":"BASE-P080","status":"ok","name":"git_repository","message":"Project is inside a Git repository.","fix":""}]\n'
        fi
    elif [[ "$action" == "precheck" ]]; then
        printf 'Project is inside a Git repository.\n' >&2
    elif [[ "$action" == "predoctor" && "$output_format" == "json" ]]; then
        if [[ "$remote_network" == true ]]; then
            printf '[{"id":"BASE-P080","status":"ok","name":"git_repository","message":"Project is inside a Git repository.","fix":""},{"id":"BASE-P083","status":"ok","name":"git_origin_reachability","message":"Project Git origin remote is reachable.","fix":""}]\n'
        else
            printf '[{"id":"BASE-P080","status":"ok","name":"git_repository","message":"Project is inside a Git repository.","fix":""}]\n'
        fi
    elif [[ "$action" == "predoctor" ]]; then
        printf 'ok     BASE-P080  git_repository            Project is inside a Git repository.\n'
    elif [[ "$action" == "check" && "$output_format" == "json" ]]; then
        printf '{"schema_version":1,"status":"ok","project":"demo","checks":[{"id":"BASE-P040","status":"ok","name":"demo-artifact","message":"Project artifact check passed.","fix":""}]}\n'
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
