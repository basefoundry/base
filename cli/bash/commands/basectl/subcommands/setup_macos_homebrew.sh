#!/usr/bin/env bash

#
# setup_macos_homebrew.sh
#     macOS/Homebrew-specific setup and check helpers for setup_common.sh.
#
# This file is sourced by setup_common.sh. It intentionally preserves the
# existing setup_* function names so setup/check/doctor call sites remain
# behavior-compatible while macOS/Homebrew ownership moves out of the shared
# file.
#

[[ -n "${_base_setup_macos_homebrew_sourced:-}" ]] && return 0
_base_setup_macos_homebrew_sourced=1
readonly _base_setup_macos_homebrew_sourced

setup_python_formula() {
    printf '%s\n' "${BASE_SETUP_PYTHON_FORMULA:-python@3.13}"
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

setup_allow_system_python() {
    [[ "${BASE_SETUP_ALLOW_SYSTEM_PYTHON:-false}" == true ]]
}

setup_recovery_homebrew() {
    printf "%s\n" "Run 'basectl setup' to install Homebrew, or install it manually from https://brew.sh/."
}

setup_recovery_brew_path() {
    printf "%s\n" "Check your Homebrew installation and make sure its bin directory is on PATH, then rerun 'basectl setup'."
}

setup_recovery_xcode_tools() {
    printf "%s\n" "Run 'xcode-select --install' in an interactive terminal, complete the installer, then rerun 'basectl setup'."
}

setup_recovery_xcode_tools_update() {
    printf "%s\n" "Update Xcode Command Line Tools from Software Update, or reinstall them with 'xcode-select --install'."
}

setup_recovery_python() {
    printf "Run 'basectl setup' to install Homebrew Python, or run 'brew install %s'.\n" "$(setup_python_formula)"
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

setup_homebrew_prefix() {
    local brew_bin prefix

    if [[ -n "${BASE_SETUP_TEST_HOMEBREW_PREFIX+x}" ]]; then
        setup_reject_test_hook_if_disallowed BASE_SETUP_TEST_HOMEBREW_PREFIX
        [[ -n "$BASE_SETUP_TEST_HOMEBREW_PREFIX" ]] || return 1
        printf '%s\n' "$BASE_SETUP_TEST_HOMEBREW_PREFIX"
        return 0
    fi

    if [[ -n "${HOMEBREW_PREFIX:-}" ]]; then
        printf '%s\n' "$HOMEBREW_PREFIX"
        return 0
    fi

    brew_bin="$(setup_find_brew_bin)" || return 1
    case "$brew_bin" in
        /opt/homebrew/bin/brew)
            printf '%s\n' "/opt/homebrew"
            return 0
            ;;
        /usr/local/bin/brew)
            printf '%s\n' "/usr/local"
            return 0
            ;;
    esac

    prefix="$("$brew_bin" --prefix 2>/dev/null || true)"
    [[ -n "$prefix" ]] || return 1
    printf '%s\n' "$prefix"
}

setup_refresh_brew_path() {
    local brew_bin

    brew_bin="$(setup_find_brew_bin)" || return 1
    add_to_path -p "$(dirname "$brew_bin")"
    return 0
}

setup_homebrew_doctor_output() {
    local brew_bin

    brew_bin="$(setup_find_brew_bin)" || return 1
    "$brew_bin" doctor 2>&1 || true
}

setup_homebrew_reports_xcode_tools_issue() {
    local doctor_output

    doctor_output="$(setup_homebrew_doctor_output)" || return 1
    [[ "$doctor_output" == *"Command Line Tools are too outdated"* ||
        "$doctor_output" == *"Command Line Tools installation may be broken or incomplete"* ]]
}

setup_xcode_homebrew_diagnostics_enabled() {
    [[ "${BASE_SETUP_XCODE_HOMEBREW_DIAGNOSTICS:-false}" == true ]]
}

setup_homebrew_default_installer_url() {
    printf '%s\n' "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
}

setup_homebrew_pinned_selected() {
    [[ -n "${BASE_HOMEBREW_INSTALLER_URL+x}" ||
        -n "${BASE_SETUP_HOMEBREW_INSTALLER_URL+x}" ||
        -n "${BASE_HOMEBREW_INSTALLER_SHA256+x}" ||
        -n "${BASE_SETUP_HOMEBREW_INSTALLER_SHA256+x}" ]]
}

setup_homebrew_pinned_url_selected() {
    [[ -n "${BASE_HOMEBREW_INSTALLER_URL+x}" ||
        -n "${BASE_SETUP_HOMEBREW_INSTALLER_URL+x}" ]]
}

setup_homebrew_pinned_sha256_selected() {
    [[ -n "${BASE_HOMEBREW_INSTALLER_SHA256+x}" ||
        -n "${BASE_SETUP_HOMEBREW_INSTALLER_SHA256+x}" ]]
}

setup_homebrew_installer_url() {
    if [[ -n "${BASE_HOMEBREW_INSTALLER_URL+x}" ]]; then
        printf '%s\n' "$BASE_HOMEBREW_INSTALLER_URL"
        return 0
    fi
    if [[ -n "${BASE_SETUP_HOMEBREW_INSTALLER_URL+x}" ]]; then
        printf '%s\n' "$BASE_SETUP_HOMEBREW_INSTALLER_URL"
        return 0
    fi
    setup_homebrew_default_installer_url
}

setup_homebrew_installer_sha256() {
    if [[ -n "${BASE_HOMEBREW_INSTALLER_SHA256+x}" ]]; then
        printf '%s\n' "$BASE_HOMEBREW_INSTALLER_SHA256"
        return 0
    fi
    if [[ -n "${BASE_SETUP_HOMEBREW_INSTALLER_SHA256+x}" ]]; then
        printf '%s\n' "$BASE_SETUP_HOMEBREW_INSTALLER_SHA256"
        return 0
    fi
}

setup_log_homebrew_mutable_policy() {
    log_info "Homebrew installer trust policy: using Homebrew's official mutable installer without checksum verification."
    log_info "Set BASE_HOMEBREW_INSTALLER_URL and BASE_HOMEBREW_INSTALLER_SHA256 to use a pinned verified installer."
}

setup_fetch_homebrew_installer() {
    local installer_url="$1"
    local target="$2"
    local installer_path

    case "$installer_url" in
        file://*)
            installer_path="${installer_url#file://}"
            cp "$installer_path" "$target"
            ;;
        /*|./*|../*)
            cp "$installer_url" "$target"
            ;;
        *)
            command -v curl >/dev/null 2>&1 || return 127
            curl -fsSL "$installer_url" -o "$target"
            ;;
    esac
}

setup_run_verified_homebrew_installer() {
    local installer_url="$1"
    local expected_sha256="$2"
    local installer_file
    local checksum
    local actual_sha256
    local exit_code

    std_make_temp_file installer_file base-homebrew-installer || fatal_error "Failed to create a temporary Homebrew installer file."
    setup_fetch_homebrew_installer "$installer_url" "$installer_file" || {
        fatal_error "Failed to read pinned Homebrew installer content from '$installer_url'."
    }

    command -v shasum >/dev/null 2>&1 || {
        fatal_error "shasum is required to verify pinned Homebrew installer content."
    }
    checksum="$(shasum -a 256 "$installer_file")" || {
        fatal_error "Failed to compute Homebrew installer checksum."
    }
    actual_sha256="${checksum%% *}"
    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
        fatal_error "Homebrew installer checksum mismatch (expected $expected_sha256, got $actual_sha256)."
    fi

    /bin/bash "$installer_file"
    exit_code=$?
    if ((exit_code)); then
        log_error "$(setup_recovery_homebrew)"
    fi
    exit_if_error "$exit_code" "Homebrew installer failed."
}

setup_install_homebrew() {
    # Trust decision: Base follows Homebrew's official install command, which
    # intentionally fetches the installer from the mutable HEAD ref. Pinning a
    # reviewed commit would reduce mutability risk, but would also make Base own
    # installer refreshes and drift from Homebrew's supported bootstrap path.
    local installer_url
    local installer_sha256
    local exit_code

    installer_url="$(setup_homebrew_installer_url)"
    installer_sha256="$(setup_homebrew_installer_sha256)"

    if setup_find_brew_bin >/dev/null 2>&1; then
        setup_refresh_brew_path || fatal_error "Homebrew is installed, but its bin directory could not be added to PATH. $(setup_recovery_brew_path)"
        log_info "Homebrew is already installed."
        return 0
    fi

    if setup_homebrew_pinned_selected; then
        setup_homebrew_pinned_url_selected &&
            setup_homebrew_pinned_sha256_selected &&
            [[ -n "$installer_url" && -n "$installer_sha256" ]] ||
            fatal_error "Pinned Homebrew installer URL and SHA-256 are both required."
        log_info "Installing Homebrew."
        log_info "Using pinned Homebrew installer from $installer_url."
        if setup_is_dry_run; then
            log_info "[DRY-RUN] Would verify Homebrew installer SHA-256 $installer_sha256"
            log_info "[DRY-RUN] Would run: /bin/bash <verified Homebrew installer from $installer_url>"
            return 0
        fi
        setup_run_verified_homebrew_installer "$installer_url" "$installer_sha256"
        setup_refresh_brew_path || fatal_error "Homebrew installation finished, but 'brew' was not found on PATH. $(setup_recovery_brew_path)"
        return 0
    fi

    setup_log_homebrew_mutable_policy
    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from $installer_url>"
        return 0
    fi

    log_info "Installing Homebrew."

    if [[ -n "${BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT:-}" ]]; then
        setup_reject_test_hook_if_disallowed BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT
        "$BASE_SETUP_HOMEBREW_INSTALLER_SCRIPT"
        exit_code=$?
        if ((exit_code)); then
            log_error "$(setup_recovery_homebrew)"
        fi
        exit_if_error "$exit_code" "Homebrew installation failed."
    else
        command -v curl >/dev/null 2>&1 || fatal_error "curl is required to install Homebrew. Install curl or install Homebrew manually from https://brew.sh/, then rerun 'basectl setup'."
        /bin/bash -c "$(curl -fsSL "$installer_url")"
        exit_code=$?
        if ((exit_code)); then
            log_error "$(setup_recovery_homebrew)"
        fi
        exit_if_error "$exit_code" "Homebrew installation failed."
    fi

    setup_refresh_brew_path || fatal_error "Homebrew installation finished, but 'brew' was not found on PATH. $(setup_recovery_brew_path)"
}

setup_require_macos() {
    [[ "$OSTYPE" == darwin* ]] || fatal_error "The setup command currently supports macOS only (OSTYPE='$OSTYPE')."
}

setup_xcode_tools_installed() {
    local tools_dir

    tools_dir="$(setup_xcode_tools_dir)"
    xcode-select -p >/dev/null 2>&1 &&
        [[ -d "$tools_dir" ]] &&
        [[ -f "$tools_dir/usr/bin/clang" ]]
}

setup_install_xcode_tools() {
    local timeout interval start_time current_time

    if setup_xcode_tools_installed; then
        log_info "Xcode Command Line Tools are already installed."
        return 0
    fi

    if ! is_interactive && ! setup_allow_noninteractive_xcode_install && ! setup_is_dry_run; then
        fatal_error "Xcode Command Line Tools installation requires an interactive terminal. $(setup_recovery_xcode_tools)"
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install Xcode Command Line Tools and wait for installation to complete."
        return 0
    fi

    log_info "Installing Xcode Command Line Tools."
    xcode-select --install || true

    timeout="$(setup_xcode_wait_timeout_seconds)"
    interval="$(setup_xcode_wait_interval_seconds)"
    start_time="$(setup_epoch_seconds)" || fatal_error "Unable to read current time while waiting for Xcode Command Line Tools."

    until setup_xcode_tools_installed; do
        current_time="$(setup_epoch_seconds)" || fatal_error "Unable to read current time while waiting for Xcode Command Line Tools."
        if ((current_time - start_time >= timeout)); then
            fatal_error "Timed out waiting for Xcode Command Line Tools installation to complete. If the installer is still open, finish it. Otherwise $(setup_recovery_xcode_tools)"
        fi
        sleep "$interval"
    done

    log_info "Xcode Command Line Tools installation detected."
}

setup_python_installed() {
    local brew_bin formula

    formula="$(setup_python_formula)"
    brew_bin="$(setup_find_brew_bin)" || return 1
    "$brew_bin" list "$formula" >/dev/null 2>&1
}

setup_install_python() {
    local brew_bin formula

    formula="$(setup_python_formula)"

    if setup_python_installed; then
        log_info "Python formula '$formula' is already installed via Homebrew."
        return 0
    fi

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Would install Python formula '$formula' via Homebrew."
        return 0
    fi

    brew_bin="$(setup_find_brew_bin)" || fatal_error "Homebrew is required to install Python formula '$formula'. $(setup_recovery_homebrew)"

    log_info "Installing Python formula '$formula' via Homebrew."
    "$brew_bin" install "$formula" || fatal_error "Homebrew failed to install Python formula '$formula'."
}

setup_find_python_bin() {
    local brew_bin formula prefix candidate
    local candidates=()

    if [[ -n "${BASE_SETUP_PYTHON_BIN:-}" ]]; then
        setup_reject_test_hook_if_disallowed BASE_SETUP_PYTHON_BIN
        [[ -x "${BASE_SETUP_PYTHON_BIN}" ]] || return 1
        printf '%s\n' "${BASE_SETUP_PYTHON_BIN}"
        return 0
    fi

    formula="$(setup_python_formula)"
    candidates+=("/opt/homebrew/opt/$formula/bin/python3")
    candidates+=("/usr/local/opt/$formula/bin/python3")

    for candidate in "${candidates[@]}"; do
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    candidates=()
    if brew_bin="$(setup_find_brew_bin)"; then
        prefix="$("$brew_bin" --prefix "$formula" 2>/dev/null || true)"
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

    if setup_allow_system_python && command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi

    return 1
}

setup_read_homebrew_check_result_file() {
    local path="$1"
    local refresh_brew_failure_mode="$2"

    setup_parse_check_result_file "$path"
    [[ "$_BASE_SETUP_PARSED_CHECK_NAME" == homebrew ]] ||
        fatal_error "Base check probe result '$path' contains unexpected name '$_BASE_SETUP_PARSED_CHECK_NAME'."

    if [[ "$_BASE_SETUP_PARSED_CHECK_OK" == true ]]; then
        if setup_refresh_brew_path; then
            setup_add_parsed_check_result
            return 0
        fi
        if [[ "$refresh_brew_failure_mode" == fatal ]]; then
            fatal_error "Homebrew is installed, but its bin directory could not be added to PATH. $(setup_recovery_brew_path)"
        fi
        setup_add_check_result \
            "homebrew" \
            false \
            "Homebrew is installed, but its bin directory could not be added to PATH." \
            "$(setup_recovery_brew_path)"
        return 1
    fi

    setup_add_parsed_check_result
    return 1
}

setup_write_homebrew_check_probe() {
    local brew_bin
    local result_file="$1"

    if brew_bin="$(setup_find_brew_bin)"; then
        setup_write_check_result_file \
            "$result_file" \
            "homebrew" \
            true \
            "Homebrew is installed." \
            "" \
            "Resolved Homebrew binary: $brew_bin"
    else
        setup_write_check_result_file \
            "$result_file" \
            "homebrew" \
            false \
            "Homebrew is not installed." \
            "$(setup_recovery_homebrew)"
    fi
}

setup_write_xcode_check_probe() {
    local result_file="$1"

    if setup_xcode_tools_installed; then
        if setup_xcode_homebrew_diagnostics_enabled && setup_homebrew_reports_xcode_tools_issue; then
            setup_write_check_result_file \
                "$result_file" \
                "xcode_command_line_tools" \
                true \
                "Xcode Command Line Tools are installed, but Homebrew reports they are outdated or incomplete." \
                "$(setup_recovery_xcode_tools_update)" \
                "" \
                "warn"
            return 0
        fi
        setup_write_check_result_file \
            "$result_file" \
            "xcode_command_line_tools" \
            true \
            "Xcode Command Line Tools are installed."
    else
        setup_write_check_result_file \
            "$result_file" \
            "xcode_command_line_tools" \
            false \
            "Xcode Command Line Tools are not installed." \
            "$(setup_recovery_xcode_tools)"
    fi
}

setup_write_python_check_probe() {
    local result_file="$1"

    if setup_python_installed; then
        setup_write_check_result_file \
            "$result_file" \
            "python" \
            true \
            "Python formula '$(setup_python_formula)' is installed via Homebrew."
    else
        setup_write_check_result_file \
            "$result_file" \
            "python" \
            false \
            "Python formula '$(setup_python_formula)' is not installed via Homebrew." \
            "$(setup_recovery_python)"
    fi
}

setup_collect_macos_base_check_results() {
    local click_package
    local missing=0
    local probe_pids=()
    local pyyaml_package
    local refresh_brew_failure_mode="${1:-warn}"
    local tmpdir

    click_package="$(setup_click_package)"
    pyyaml_package="$(setup_pyyaml_package)"
    setup_ensure_cached_paths

    std_make_temp_dir tmpdir base-check ||
        fatal_error "Unable to create temporary directory for Base check probes."

    setup_write_homebrew_check_probe "$tmpdir/homebrew" &
    probe_pids+=("$!")
    setup_write_xcode_check_probe "$tmpdir/xcode" &
    probe_pids+=("$!")
    setup_write_python_check_probe "$tmpdir/python" &
    probe_pids+=("$!")
    setup_write_virtualenv_check_probe "$tmpdir/base_virtualenv" &
    probe_pids+=("$!")
    setup_write_python_package_check_probe "$tmpdir/pyyaml" "pyyaml" "$pyyaml_package" &
    probe_pids+=("$!")
    setup_write_python_package_check_probe "$tmpdir/click" "click" "$click_package" &
    probe_pids+=("$!")

    setup_wait_for_base_check_probes "${probe_pids[@]}" ||
        fatal_error "One or more Base check probes failed before writing results."

    setup_read_homebrew_check_result_file "$tmpdir/homebrew" "$refresh_brew_failure_mode" || missing=1
    setup_add_base_bash_libraries_check_result
    setup_read_check_result_file "$tmpdir/xcode" || missing=1
    setup_read_check_result_file "$tmpdir/python" || missing=1
    setup_read_check_result_file "$tmpdir/base_virtualenv" || missing=1
    setup_read_check_result_file "$tmpdir/pyyaml" || missing=1
    setup_read_check_result_file "$tmpdir/click" || missing=1

    rm -rf "$tmpdir"

    return "$missing"
}

setup_run_macos_install() {
    setup_install_homebrew
    setup_install_xcode_tools
    setup_install_python
    setup_create_virtualenv
    setup_install_pyyaml
    setup_install_click
    if setup_profiles_enabled; then
        if setup_is_dry_run; then
            setup_run_base_dev_layer setup --dry-run || fatal_error "Python prerequisite profile layer failed."
        else
            setup_run_base_dev_layer setup || fatal_error "Python prerequisite profile layer failed."
        fi
    fi
    setup_run_project_artifact_setup || return $?
    setup_seed_user_config

    if setup_is_dry_run; then
        log_info "[DRY-RUN] Base CLI setup check is complete."
    else
        log_info "Base CLI setup is complete."
    fi
}
