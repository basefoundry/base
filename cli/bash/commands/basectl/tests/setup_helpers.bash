# Shared helpers for basectl setup/check/profile BATS suites.

load ../../../../../tests/test_helper.sh
load ./bash_lib_readiness_helpers.bash
bats_require_minimum_version 1.5.0

setup() {
    setup_test_tmpdir
    TEST_HOME="$TEST_TMPDIR/home"
    TEST_MOCKBIN="$TEST_TMPDIR/mockbin"
    TEST_STATE_DIR="$TEST_TMPDIR/state"
    TEST_BASH_BIN_DIR="$(dirname "$(command -v bash)")"
    unset OSTYPE_OVERRIDE

    mkdir -p "$TEST_HOME" "$TEST_MOCKBIN" "$TEST_STATE_DIR"
    export BASH_ENV="$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash"
    create_uname_stub
}

create_uname_stub() {
    cat > "$TEST_MOCKBIN/uname" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
    ""|-s)
        printf 'Darwin\n'
        exit 0
        ;;
esac

if [[ -x /usr/bin/uname ]]; then
    exec /usr/bin/uname "$@"
fi
exec /bin/uname "$@"
EOF
    chmod +x "$TEST_MOCKBIN/uname"
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

create_date_logger_stub() {
    cat > "$TEST_MOCKBIN/date" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${BASE_SETUP_TEST_STATE_DIR:?}/date-args"
case "$*" in
    "+%s")
        printf '1710000000\n'
        ;;
    "+%Y%m%dT%H%M%S")
        printf '20240309T160000\n'
        ;;
    "-u +%Y-%m-%dT%H:%M:%SZ"|"-u '+%Y-%m-%dT%H:%M:%SZ'")
        printf '2024-03-09T16:00:00Z\n'
        ;;
    *)
        printf 'unexpected date args: %s\n' "$*" >&2
        exit 1
        ;;
esac
EOF
    chmod +x "$TEST_MOCKBIN/date"
}

create_tr_failure_stub() {
    cat > "$TEST_MOCKBIN/tr" <<'EOF'
#!/usr/bin/env bash
printf 'tr should not run\n' >&2
exit 97
EOF
    chmod +x "$TEST_MOCKBIN/tr"
}

create_wc_failure_stub() {
    cat > "$TEST_MOCKBIN/wc" <<'EOF'
#!/usr/bin/env bash
printf 'wc should not run\n' >&2
exit 98
EOF
    chmod +x "$TEST_MOCKBIN/wc"
}

create_tail_failure_stub() {
    cat > "$TEST_MOCKBIN/tail" <<'EOF'
#!/usr/bin/env bash
printf 'tail should not run\n' >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/tail"
}

create_curl_failure_stub() {
    cat > "$TEST_MOCKBIN/curl" <<'EOF'
#!/usr/bin/env bash
printf 'curl should not run for pinned local Homebrew installer: %s\n' "$*" >&2
exit 96
EOF
    chmod +x "$TEST_MOCKBIN/curl"
}

create_system_python3_stub() {
    cat > "$TEST_MOCKBIN/python3" <<'EOF'
#!/usr/bin/env bash
touch "${BASE_SETUP_TEST_STATE_DIR:?}/system-python-ran"
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" && "${3:-}" == "--help" ]]; then
    printf 'usage: python3 -m venv ENV_DIR\n'
    exit 0
fi
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
    if [[ "$*" == *"--action route"* ]]; then
        base_test_protocol_project_route base "$BASE_HOME" "$BASE_HOME/base_manifest.yaml" \
            "$HOME/.base.d/base/.venv" false false
        exit 0
    fi
    touch "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-ran"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_dev" ]]; then
    shift 2
    printf '%s\n' "$@" > "${BASE_SETUP_TEST_STATE_DIR:?}/dev-args"
    printf '%s\n' "${BASE_PLATFORM:-}" > "${BASE_SETUP_TEST_STATE_DIR:?}/base-dev-platform"
    case "${1:-}" in
        setup)
            touch "${BASE_SETUP_TEST_STATE_DIR:?}/dev-setup-ran"
            exit 0
            ;;
    esac
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

create_linux_prerequisite_stubs() {
    local tool

    for tool in git gh bats shellcheck jq go; do
        cat > "$TEST_MOCKBIN/$tool" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
        chmod +x "$TEST_MOCKBIN/$tool"
    done
}

create_linux_dpkg_query_stub() {
    cat > "$TEST_MOCKBIN/dpkg-query" <<'EOF'
#!/usr/bin/env bash
state_dir="${BASE_SETUP_TEST_STATE_DIR:?}"
missing_packages=" ${BASE_SETUP_TEST_MISSING_APT_PACKAGES:-} "
package=""

printf '%s\n' "$*" >> "$state_dir/dpkg-query-args"
for package_arg in "$@"; do
    package="$package_arg"
done

if [[ "$missing_packages" == *" $package "* ]]; then
    exit 1
fi

printf 'install ok installed\n'
EOF
    chmod +x "$TEST_MOCKBIN/dpkg-query"
}

create_sudo_apt_get_stub() {
    cat > "$TEST_MOCKBIN/sudo" <<'EOF'
#!/usr/bin/env bash
state_dir="${BASE_SETUP_TEST_STATE_DIR:?}"
printf '%s\n' "$*" >> "$state_dir/sudo-args"
if [[ "${BASE_SETUP_TEST_APT_FAIL:-}" == true ]]; then
    printf 'apt failed\n' >&2
    exit 42
fi
if [[ "${1:-}" == "apt-get" && "${2:-}" == "update" ]]; then
    touch "$state_dir/apt-update-ran"
    exit 0
fi
if [[ "${1:-}" == "apt-get" && "${2:-}" == "install" && "${3:-}" == "-y" ]]; then
    touch "$state_dir/apt-install-ran"
    printf '%s\n' "${*:4}" > "$state_dir/apt-install-packages"
    if [[ "${4:-}" == "gh" ]]; then
        touch "$state_dir/gh-apt-install-ran"
    fi
    exit 0
fi
if [[ "${1:-}" == "install" && "${2:-}" == "-d" && "${3:-}" == "-m" && "${4:-}" == "0755" ]]; then
    case "${5:-}" in
        /etc/apt/keyrings)
            touch "$state_dir/github-cli-keyrings-dir-created"
            exit 0
            ;;
        /etc/apt/sources.list.d)
            touch "$state_dir/github-cli-sources-dir-created"
            exit 0
            ;;
    esac
fi
if [[ "${1:-}" == "install" && "${2:-}" == "-m" && "${3:-}" == "0644" ]]; then
    case "${5:-}" in
        /etc/apt/keyrings/githubcli-archive-keyring.gpg)
            cp "${4:-}" "$state_dir/github-cli-keyring"
            touch "$state_dir/github-cli-keyring-installed"
            exit 0
            ;;
        /etc/apt/sources.list.d/github-cli.list)
            cp "${4:-}" "$state_dir/github-cli-source-list"
            touch "$state_dir/github-cli-source-installed"
            exit 0
            ;;
    esac
fi
printf 'unexpected sudo args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/sudo"
}

create_github_cli_repo_stubs() {
    cat > "$TEST_MOCKBIN/curl" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-fsSL" && "${2:-}" == "-o" && -n "${3:-}" && "${4:-}" == "https://cli.github.com/packages/githubcli-archive-keyring.gpg" ]]; then
    printf 'test github cli keyring\n' > "$3"
    exit 0
fi
printf 'unexpected curl args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/curl"

    cat > "$TEST_MOCKBIN/dpkg" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "--print-architecture" ]]; then
    printf 'amd64\n'
    exit 0
fi
printf 'unexpected dpkg args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/dpkg"
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
    if [[ "$*" == *"--action route"* ]]; then
        base_test_protocol_project_route base "$BASE_HOME" "$BASE_HOME/base_manifest.yaml" \
            "$HOME/.base.d/base/.venv" false false
        exit 0
    fi
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
VENVEOF
    chmod +x "$3/bin/python"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    if [[ "$*" == *"--action route"* ]]; then
        base_test_protocol_project_route base "$BASE_HOME" "$BASE_HOME/base_manifest.yaml" \
            "$HOME/.base.d/base/.venv" false false
        exit 0
    fi
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
    doctor)
        if [[ -f "$state_dir/xcode-outdated" ]]; then
            printf 'Warning: Your Command Line Tools are too outdated.\n'
            printf 'Update them from Software Update in System Settings.\n'
            exit 1
        fi
        printf 'Your system is ready to brew.\n'
        exit 0
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
    if [[ "$*" == *"--action route"* ]]; then
        base_test_protocol_project_route base "$BASE_HOME" "$BASE_HOME/base_manifest.yaml" \
            "$HOME/.base.d/base/.venv" false false
        exit 0
    fi
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
VENVEOF
    chmod +x "$3/bin/python"
    exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    if [[ "$*" == *"--action route"* ]]; then
        base_test_protocol_project_route base "$BASE_HOME" "$BASE_HOME/base_manifest.yaml" \
            "$HOME/.base.d/base/.venv" false false
        exit 0
    fi
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

sha256_file() {
    local checksum

    checksum="$(shasum -a 256 "$1")"
    printf '%s\n' "${checksum%% *}"
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
        "$BASE_REPO_ROOT/bin/basectl" "${command_args[@]}" \
        </dev/null
}

run_base_command_separate_stderr() {
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

    run --separate-stderr env \
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
        "$BASE_REPO_ROOT/bin/basectl" "${command_args[@]}" \
        </dev/null
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
if [[ "${1:-}" == "-m" && "${2:-}" == "base_setup" ]]; then
    if [[ "$*" == *"--action route"* ]]; then
        base_test_protocol_project_route base "$BASE_HOME" "$BASE_HOME/base_manifest.yaml" \
            "$HOME/.base.d/base/.venv" false false
        exit 0
    fi
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
    original_args=("$@")
    action="setup"
    manifest_path=""
    output_format="text"
    project_arg=""
    remote_network=false
    while (($#)); do
        case "$1" in
            --manifest)
                shift
                manifest_path="${1:-}"
                ;;
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
            --*)
                ;;
            *)
                project_arg="$1"
                ;;
        esac
        shift || true
    done
    if [[ "$action" == "route" ]]; then
        project_root="$(cd -- "$(dirname -- "$manifest_path")" && pwd -P)"
        if [[ -z "$project_arg" && -f "$manifest_path" ]]; then
            project_arg="$(awk '/^[[:space:]]*name:/ { print $2; exit }' "$manifest_path")"
        fi
        if awk '
            /^[[:space:]]*#/ { next }
            /^[^[:space:]][^:]*:/ { in_python = 0 }
            /^[[:space:]]*python:[[:space:]]*$/ { in_python = 1; next }
            in_python && /^[[:space:]]+manager:[[:space:]]*['\''"]?uv['\''"]?[[:space:]]*(#.*)?$/ { found = 1 }
            END { exit found ? 0 : 1 }
        ' "$manifest_path"; then
            uses_uv_manager=true
        else
            uses_uv_manager=false
        fi
        if awk '
            /^[[:space:]]*#/ { next }
            /^python:[[:space:]]*/ { found = 1 }
            /^[[:space:]]*-[[:space:]]+type:[[:space:]]*['\''"]?python-package['\''"]?[[:space:]]*(#.*)?$/ { found = 1 }
            END { exit found ? 0 : 1 }
        ' "$manifest_path"; then
            requires_project_python=true
        else
            requires_project_python=false
        fi
        if awk '
            /^[[:space:]]*#/ { next }
            /^[^[:space:]][^:]*:/ { in_python = 0 }
            /^[[:space:]]*python:[[:space:]]*$/ { in_python = 1; next }
            in_python && /^[[:space:]]+venv_location:[[:space:]]*['\''"]?external['\''"]?[[:space:]]*(#.*)?$/ { found = 1 }
            END { exit found ? 0 : 1 }
        ' "$manifest_path"; then
            uses_external_venv=true
        else
            uses_external_venv=false
        fi
        if [[ "$project_arg" != base && -n "${BASE_PROJECT_VENV_DIR:-}" && ( -z "${BASE_PROJECT:-}" || "${BASE_PROJECT:-}" == "$project_arg" ) ]]; then
            route_venv_dir="$BASE_PROJECT_VENV_DIR"
        elif [[ "$project_arg" != base && "$uses_external_venv" != true ]]; then
            route_venv_dir="$project_root/.venv"
        else
            route_venv_dir="$HOME/.base.d/$project_arg/.venv"
        fi
        if [[ "$output_format" == "json" ]]; then
            printf '{"schema_version":1,"project":"%s","project_root":"%s","manifest_path":"%s","project_venv_dir":"%s","uses_uv_manager":%s,"requires_project_python":%s}\n' \
                "$project_arg" "$project_root" "$manifest_path" "$route_venv_dir" "$uses_uv_manager" "$requires_project_python"
        elif [[ "$output_format" == "command-protocol" ]]; then
            base_test_protocol_project_route \
                "$project_arg" "$project_root" "$manifest_path" "$route_venv_dir" "$uses_uv_manager" false "$requires_project_python"
        else
            printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
                "$project_arg" "$project_root" "$manifest_path" "$route_venv_dir" "$uses_uv_manager" "$requires_project_python"
        fi
        exit 0
    fi
    printf '%s\n' "${original_args[@]}" > "${BASE_SETUP_TEST_STATE_DIR:?}/project-setup-args"
    printf '%s\n' "$0" >> "$BASE_SETUP_TEST_STATE_DIR/project-setup-python"
    printf '%s\n' "${BASE_PROJECT:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-project"
    printf '%s\n' "${BASE_CI:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-base-ci"
    printf '%s\n' "${CI:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-ci"
    printf '%s\n' "${BASE_SETUP_NOTIFY:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-notify"
    printf '%s\n' "${BASE_SETUP_YES:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-yes"
    printf '%s\n' "${BASE_PLATFORM:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-setup-platform"
    touch "$BASE_SETUP_TEST_STATE_DIR/project-setup-ran"
    if [[ "$action" == "bootstrap" ]]; then
        printf '%s\n' "${BASE_SETUP_RECREATE_PROJECT_VENV:-}" > "$BASE_SETUP_TEST_STATE_DIR/project-bootstrap-recreate-venv"
    fi
    if [[ -f "$BASE_SETUP_TEST_STATE_DIR/project-setup-fail-before-output" ]]; then
        if [[ -f "$BASE_SETUP_TEST_STATE_DIR/project-setup-stderr" ]]; then
            cat "$BASE_SETUP_TEST_STATE_DIR/project-setup-stderr" >&2
        fi
        exit "$(cat "$BASE_SETUP_TEST_STATE_DIR/project-setup-exit-code")"
    fi
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
    elif [[ "$action" == "doctor" && "$output_format" == "json" ]]; then
        printf '[{"id":"BASE-P040","status":"ok","name":"demo-artifact","message":"Project artifact check passed.","fix":""}]\n'
    elif [[ "$action" == "doctor" ]]; then
        printf 'ok     demo-artifact               Project artifact check passed.\n'
    fi
    if [[ -f "$BASE_SETUP_TEST_STATE_DIR/project-setup-stderr" ]]; then
        cat "$BASE_SETUP_TEST_STATE_DIR/project-setup-stderr" >&2
    fi
    exit "$(cat "$BASE_SETUP_TEST_STATE_DIR/project-setup-exit-code")"
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" ]]; then
    project="${4:-}"
    project_root="${BASE_SETUP_TEST_WORKSPACE:?}/$project"
    manifest_path="$project_root/base_manifest.yaml"
    if [[ -f "$manifest_path" ]]; then
        base_test_protocol_project_route \
            "$project" "$project_root" "$manifest_path" "$project_root/.venv" false false
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
        base_test_protocol_project_reference "$project" "$project_root" "$manifest_path"
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
