#!/usr/bin/env bash

setup_usage() {
    cat <<'EOF'
Usage:
  setup [options] <command>

Commands:
  install
    Install Homebrew, Xcode Command Line Tools, Python, BATS, and ~/.base.d/.venv.
  check
    Verify the required local CLI setup without making changes.
  update-profile
    Reserved for future shell profile updates.

Options:
  --dry-run   Log what would happen without making changes.
  -v          Enable DEBUG logging for this command.
  -h, --help  Show this help text.

Purpose:
  Prepare and verify the local Base CLI environment on macOS.

Install does:
  1. Install Homebrew if needed.
  2. Install Xcode Command Line Tools if needed.
  3. Install Python 3.13 via Homebrew if needed.
  4. Install BATS via Homebrew if needed.
  5. Create ~/.base.d/.venv if it does not already exist.

Check does:
  1. Verify Homebrew is installed.
  2. Verify Xcode Command Line Tools are installed.
  3. Verify Python 3.13 is installed via Homebrew.
  4. Verify BATS is installed via Homebrew.
  5. Verify ~/.base.d/.venv exists.

Notes:
  - This command is intentionally idempotent.
  - It does not support uninstall yet.
EOF
}

setup_is_dry_run() {
    [[ "${DRY_RUN-}" == true || "${dry_run-}" == true ]]
}

setup_virtualenv_exists() {
    local venv_dir

    venv_dir="$(setup_venv_dir)"
    [[ -f "$venv_dir/bin/activate" || -f "$venv_dir/pyvenv.cfg" ]]
}

setup_venv_dir() {
    printf '%s\n' "${BASE_SETUP_VENV_DIR:-$HOME/.base.d/.venv}"
}

setup_python_formula() {
    printf '%s\n' "${BASE_SETUP_PYTHON_FORMULA:-python@3.13}"
}

setup_bats_formula() {
    printf '%s\n' "${BASE_SETUP_BATS_FORMULA:-bats-core}"
}

setup_xcode_tools_dir() {
    printf '%s\n' "${BASE_SETUP_XCODE_COMMAND_LINE_TOOLS_DIR:-/Library/Developer/CommandLineTools}"
}

setup_xcode_wait_timeout_seconds() {
    printf '%s\n' "${BASE_SETUP_XCODE_WAIT_TIMEOUT_SECONDS:-1800}"
}

setup_xcode_wait_interval_seconds() {
    printf '%s\n' "${BASE_SETUP_XCODE_WAIT_INTERVAL_SECONDS:-5}"
}

setup_allow_noninteractive_xcode_install() {
    [[ "${BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL:-false}" == true ]]
}

setup_find_brew_bin() {
    local candidate

    if [[ -n "${BASE_SETUP_BREW_BIN+x}" ]]; then
        if [[ -x "${BASE_SETUP_BREW_BIN}" ]]; then
            printf '%s\n' "${BASE_SETUP_BREW_BIN}"
            return 0
        fi
        return 1
    fi

    if command -v brew >/dev/null 2>&1; then
        command -v brew
        return 0
    fi

    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        [[ -x "$candidate" ]] || continue
        printf '%s\n' "$candidate"
        return 0
    done

    return 1
}

setup_refresh_brew_path() {
    local brew_bin

    brew_bin="$(setup_find_brew_bin)" || return 1
    add_to_path -p "$(dirname "$brew_bin")"
    return 0
}

setup_install_homebrew() {
    local installer_url="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"

    if setup_find_brew_bin >/dev/null 2>&1; then
        setup_refresh_brew_path || fatal_error "Homebrew is installed, but its bin directory could not be added to PATH."
        log_info "Homebrew is already installed."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install Homebrew using the official installer."
        return 0
    fi

    log_info "Installing Homebrew."

    if [[ -n "${BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT:-}" ]]; then
        run "$BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT"
    else
        command -v curl >/dev/null 2>&1 || fatal_error "curl is required to install Homebrew."
        /bin/bash -c "$(curl -fsSL "$installer_url")"
        exit_if_error $? "Homebrew installation failed."
    fi

    setup_refresh_brew_path || fatal_error "Homebrew installation finished, but 'brew' was not found on PATH."
}

setup_require_macos() {
    [[ "$OSTYPE" == darwin* ]] || fatal_error "The setup command currently supports macOS only (OSTYPE='$OSTYPE')."
}

setup_xcode_tools_installed() {
    local tools_dir

    tools_dir="$(setup_xcode_tools_dir)"
    xcode-select -p >/dev/null 2>&1 &&
        [[ -d "$tools_dir" ]] &&
        xcrun -f clang >/dev/null 2>&1
}

setup_install_xcode_tools() {
    local timeout interval start_time current_time

    if setup_xcode_tools_installed; then
        log_info "Xcode Command Line Tools are already installed."
        return 0
    fi

    if ! is_interactive && ! setup_allow_noninteractive_xcode_install && ! setup_is_dry_run; then
        fatal_error "Xcode Command Line Tools installation requires an interactive terminal."
    fi

    log_info "Installing Xcode Command Line Tools."
    run --no-exit xcode-select --install

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would wait for Xcode Command Line Tools installation to complete."
        return 0
    fi

    timeout="$(setup_xcode_wait_timeout_seconds)"
    interval="$(setup_xcode_wait_interval_seconds)"
    start_time="$(date +%s)"

    until setup_xcode_tools_installed; do
        current_time="$(date +%s)"
        if ((current_time - start_time >= timeout)); then
            fatal_error "Timed out waiting for Xcode Command Line Tools installation to complete."
        fi
        sleep "$interval"
    done

    log_info "Xcode Command Line Tools installation detected."
}

setup_python_installed() {
    local formula

    formula="$(setup_python_formula)"
    command -v brew >/dev/null 2>&1 && brew list "$formula" >/dev/null 2>&1
}

setup_install_python() {
    local formula

    formula="$(setup_python_formula)"

    if setup_python_installed; then
        log_info "Python formula '$formula' is already installed via Homebrew."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install Python formula '$formula' via Homebrew."
        return 0
    fi

    command -v brew >/dev/null 2>&1 || fatal_error "Homebrew is required to install Python formula '$formula'."

    log_info "Installing Python formula '$formula' via Homebrew."
    run brew install "$formula"
}

setup_bats_installed() {
    local formula

    formula="$(setup_bats_formula)"
    command -v brew >/dev/null 2>&1 && brew list "$formula" >/dev/null 2>&1
}

setup_install_bats() {
    local formula

    formula="$(setup_bats_formula)"

    if setup_bats_installed; then
        log_info "BATS formula '$formula' is already installed via Homebrew."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install BATS formula '$formula' via Homebrew."
        return 0
    fi

    command -v brew >/dev/null 2>&1 || fatal_error "Homebrew is required to install BATS formula '$formula'."

    log_info "Installing BATS formula '$formula' via Homebrew."
    run brew install "$formula"
}

setup_find_python_bin() {
    local formula prefix candidate candidates=()

    if [[ -n "${BASE_SETUP_PYTHON_BIN:-}" && -x "${BASE_SETUP_PYTHON_BIN}" ]]; then
        printf '%s\n' "${BASE_SETUP_PYTHON_BIN}"
        return 0
    fi

    formula="$(setup_python_formula)"
    if command -v brew >/dev/null 2>&1; then
        prefix="$(brew --prefix "$formula" 2>/dev/null || true)"
        if [[ -n "$prefix" ]]; then
            candidates+=("$prefix/bin/python3")
            candidates+=("$prefix/libexec/bin/python3")
            if [[ "$formula" == python@* ]]; then
                candidates+=("$prefix/bin/python${formula#python@}")
                candidates+=("$prefix/libexec/bin/python${formula#python@}")
            fi
            for candidate in "${candidates[@]}"; do
                if [[ -x "$candidate" ]]; then
                    printf '%s\n' "$candidate"
                    return 0
                fi
            done
        fi
    fi

    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi

    return 1
}

setup_create_virtualenv() {
    local venv_dir python_bin

    venv_dir="$(setup_venv_dir)"

    if setup_virtualenv_exists; then
        log_info "Virtual environment already exists at '$venv_dir'."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would create Python virtual environment at '$venv_dir'."
        return 0
    fi

    python_bin="$(setup_find_python_bin)" || fatal_error "Unable to locate a python3 executable after installation."

    safe_mkdir -p "$(dirname "$venv_dir")"
    log_info "Creating Python virtual environment at '$venv_dir'."
    run "$python_bin" -m venv "$venv_dir"
}

setup_run_check() {
    local brew_bin="" venv_dir missing=0

    setup_require_macos
    venv_dir="$(setup_venv_dir)"

    if brew_bin="$(setup_find_brew_bin)"; then
        setup_refresh_brew_path || fatal_error "Homebrew is installed, but its bin directory could not be added to PATH."
        log_info "Homebrew is installed."
        log_debug "Resolved Homebrew binary: $brew_bin"
    else
        log_warn "Homebrew is not installed."
        missing=1
    fi

    if setup_xcode_tools_installed; then
        log_info "Xcode Command Line Tools are installed."
    else
        log_warn "Xcode Command Line Tools are not installed."
        missing=1
    fi

    if setup_python_installed; then
        log_info "Python formula '$(setup_python_formula)' is installed via Homebrew."
    else
        log_warn "Python formula '$(setup_python_formula)' is not installed via Homebrew."
        missing=1
    fi

    if setup_bats_installed; then
        log_info "BATS formula '$(setup_bats_formula)' is installed via Homebrew."
    else
        log_warn "BATS formula '$(setup_bats_formula)' is not installed via Homebrew."
        missing=1
    fi

    if setup_virtualenv_exists; then
        log_info "Virtual environment exists at '$venv_dir'."
    else
        log_warn "Virtual environment is missing at '$venv_dir'."
        missing=1
    fi

    if ((missing == 0)); then
        log_info "Base CLI environment check passed."
        return 0
    fi

    log_warn "Base CLI environment check found missing requirements."
    return 1
}

setup_run_install() {
    setup_require_macos
    setup_install_homebrew
    setup_install_xcode_tools
    setup_install_python
    setup_install_bats
    setup_create_virtualenv

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Base CLI setup check is complete."
    else
        log_info "Base CLI setup is complete."
    fi
}

setup_run_update_profile() {
    print_warn "The 'update-profile' subcommand is not implemented yet."
    return 1
}

setup_main() {
    local command=""

    while (($#)); do
        case "$1" in
            -h|--help|help)
                setup_usage
                return 0
                ;;
            --dry-run)
                dry_run=true
                export DRY_RUN=true
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                ;;
            install|check|update-profile)
                if [[ -n "$command" ]]; then
                    print_error "Only one setup command may be provided."
                    setup_usage >&2
                    return 1
                fi
                command="$1"
                ;;
            *)
                print_error "Unknown option or command '$1'."
                setup_usage >&2
                return 1
                ;;
        esac
        shift
    done

    if [[ -z "$command" ]]; then
        print_error "A setup command is required."
        setup_usage >&2
        return 1
    fi

    log_debug "Running setup command '$command' (dry_run=${dry_run:-false})."

    case "$command" in
        install)
            setup_run_install
            ;;
        check)
            setup_run_check
            ;;
        update-profile)
            setup_run_update_profile
            ;;
    esac
}

setup_main "$@"
