#!/usr/bin/env bash

# Base shell standards require explicit error handling instead of shell strict mode.

BASE_DEFAULT_HOMEBREW_INSTALLER_URL="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"

bootstrap_usage() {
    cat <<'EOF'
Usage:
  bootstrap.sh [options]

Options:
  --source                 Install or update Base from a Git checkout.
  --brew                   Install Base through Homebrew.
  --install-dir <path>     Source checkout path. Defaults to ~/work/base.
  --repo-url <url>         Git repository URL for source mode.
  --branch <name>          Clone a specific branch for a new source checkout.
  --no-homebrew-install    Fail instead of installing Homebrew when missing.
  --dry-run                Print planned actions without making changes.
  -h, --help               Show this help text.

Mode selection uses this precedence:
  command-line flag, BASE_BOOTSTRAP_MODE, existing Homebrew install,
  existing source checkout, then source mode.
EOF
}

bootstrap_log() {
    printf '%s\n' "$*"
}

bootstrap_die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

bootstrap_expand_path() {
    local path="$1"

    case "$path" in
        "~") printf '%s\n' "$HOME" ;;
        "~/"*) printf '%s/%s\n' "$HOME" "${path#"~/"}" ;;
        *) printf '%s\n' "$path" ;;
    esac
}

bootstrap_parent_dir() {
    local path="${1%/}"

    case "$path" in
        */*) printf '%s\n' "${path%/*}" ;;
        *) printf '.\n' ;;
    esac
}

bootstrap_run() {
    if [[ "${BASE_BOOTSTRAP_DRY_RUN:-false}" == "true" ]]; then
        printf '[DRY-RUN] Would run:'
        printf ' %q' "$@"
        printf '\n'
        return 0
    fi

    "$@"
}

bootstrap_uname() {
    if [[ -n "${BASE_BOOTSTRAP_TEST_OS:-}" ]]; then
        printf '%s\n' "$BASE_BOOTSTRAP_TEST_OS"
        return 0
    fi

    uname -s
}

bootstrap_require_macos() {
    local os_name

    os_name="$(bootstrap_uname)"
    [[ "$os_name" == "Darwin" ]] || bootstrap_die "bootstrap.sh currently supports macOS only."
}

bootstrap_find_brew() {
    local candidate
    local candidates="${BASE_BOOTSTRAP_BREW_CANDIDATES:-/opt/homebrew/bin/brew:/usr/local/bin/brew}"
    local -a candidate_paths

    if [[ -n "${BASE_BOOTSTRAP_BREW_BIN:-}" && -x "${BASE_BOOTSTRAP_BREW_BIN:-}" ]]; then
        printf '%s\n' "$BASE_BOOTSTRAP_BREW_BIN"
        return 0
    fi

    if command -v brew >/dev/null 2>&1; then
        command -v brew
        return 0
    fi

    IFS=: read -ra candidate_paths <<< "$candidates"
    for candidate in "${candidate_paths[@]}"; do
        [[ -n "$candidate" ]] || continue
        [[ -x "$candidate" ]] || continue
        printf '%s\n' "$candidate"
        return 0
    done

    return 1
}

bootstrap_refresh_brew() {
    local result_var="$1"
    local brew_bin
    local brew_dir

    brew_bin="$(bootstrap_find_brew || true)"
    [[ -n "$brew_bin" ]] || return 1

    printf -v "$result_var" '%s' "$brew_bin"
    brew_dir="$(bootstrap_parent_dir "$brew_bin")"
    case ":$PATH:" in
        *":$brew_dir:"*) ;;
        *) PATH="$brew_dir:$PATH"; export PATH ;;
    esac
    return 0
}

bootstrap_homebrew_pinned_selected() {
    [[ -n "${BASE_HOMEBREW_INSTALLER_URL+x}" ||
        -n "${BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL+x}" ||
        -n "${BASE_HOMEBREW_INSTALLER_SHA256+x}" ||
        -n "${BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256+x}" ]]
}

bootstrap_homebrew_pinned_url_selected() {
    [[ -n "${BASE_HOMEBREW_INSTALLER_URL+x}" ||
        -n "${BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL+x}" ]]
}

bootstrap_homebrew_pinned_sha256_selected() {
    [[ -n "${BASE_HOMEBREW_INSTALLER_SHA256+x}" ||
        -n "${BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256+x}" ]]
}

bootstrap_homebrew_installer_url() {
    if [[ -n "${BASE_HOMEBREW_INSTALLER_URL+x}" ]]; then
        printf '%s\n' "$BASE_HOMEBREW_INSTALLER_URL"
        return 0
    fi
    if [[ -n "${BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL+x}" ]]; then
        printf '%s\n' "$BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL"
        return 0
    fi
    printf '%s\n' "$BASE_DEFAULT_HOMEBREW_INSTALLER_URL"
}

bootstrap_homebrew_installer_sha256() {
    if [[ -n "${BASE_HOMEBREW_INSTALLER_SHA256+x}" ]]; then
        printf '%s\n' "$BASE_HOMEBREW_INSTALLER_SHA256"
        return 0
    fi
    if [[ -n "${BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256+x}" ]]; then
        printf '%s\n' "$BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256"
        return 0
    fi
}

bootstrap_log_homebrew_mutable_policy() {
    bootstrap_log "Homebrew installer trust policy: using Homebrew's official mutable installer without checksum verification."
    bootstrap_log "Set BASE_HOMEBREW_INSTALLER_URL and BASE_HOMEBREW_INSTALLER_SHA256 to use a pinned verified installer."
}

bootstrap_fetch_homebrew_installer() {
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

bootstrap_run_verified_homebrew_installer() {
    local installer_url="$1"
    local expected_sha256="$2"
    local installer_file
    local checksum
    local actual_sha256
    local exit_code

    installer_file="$(mktemp "${TMPDIR:-/tmp}/base-homebrew-installer.XXXXXX")" || bootstrap_die "Failed to create a temporary Homebrew installer file."
    bootstrap_fetch_homebrew_installer "$installer_url" "$installer_file" || {
        rm -f "$installer_file"
        bootstrap_die "Failed to read pinned Homebrew installer content from '$installer_url'."
    }

    command -v shasum >/dev/null 2>&1 || {
        rm -f "$installer_file"
        bootstrap_die "shasum is required to verify pinned Homebrew installer content."
    }
    checksum="$(shasum -a 256 "$installer_file")" || {
        rm -f "$installer_file"
        bootstrap_die "Failed to compute Homebrew installer checksum."
    }
    actual_sha256="${checksum%% *}"
    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
        rm -f "$installer_file"
        bootstrap_die "Homebrew installer checksum mismatch (expected $expected_sha256, got $actual_sha256)."
    fi

    /bin/bash "$installer_file"
    exit_code=$?
    rm -f "$installer_file"
    [[ "$exit_code" -eq 0 ]] || bootstrap_die "Homebrew installer failed."
}

bootstrap_install_homebrew() {
    local result_var="$1"
    local installer
    local installer_url
    local installer_sha256

    installer_url="$(bootstrap_homebrew_installer_url)"
    installer_sha256="$(bootstrap_homebrew_installer_sha256)"
    bootstrap_log "Installing Homebrew."
    if bootstrap_homebrew_pinned_selected; then
        bootstrap_homebrew_pinned_url_selected &&
            bootstrap_homebrew_pinned_sha256_selected &&
            [[ -n "$installer_url" && -n "$installer_sha256" ]] ||
            bootstrap_die "Pinned Homebrew installer URL and SHA-256 are both required."
        bootstrap_log "Using pinned Homebrew installer from $installer_url."
        if [[ "${BASE_BOOTSTRAP_DRY_RUN:-false}" == "true" ]]; then
            bootstrap_log "[DRY-RUN] Would verify Homebrew installer SHA-256 $installer_sha256"
            bootstrap_log "[DRY-RUN] Would run: /bin/bash <verified Homebrew installer from $installer_url>"
            printf -v "$result_var" '%s' brew
            return 0
        fi
        bootstrap_run_verified_homebrew_installer "$installer_url" "$installer_sha256"
        return 0
    fi

    bootstrap_log_homebrew_mutable_policy
    if [[ "${BASE_BOOTSTRAP_DRY_RUN:-false}" == "true" ]]; then
        bootstrap_log "[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from $installer_url>"
        printf -v "$result_var" '%s' brew
        return 0
    fi

    command -v curl >/dev/null 2>&1 || bootstrap_die "curl is required to install Homebrew."
    installer="$(curl -fsSL "$installer_url")" || bootstrap_die "Failed to download the Homebrew installer."
    /bin/bash -c "$installer" || bootstrap_die "Homebrew installer failed."
}

bootstrap_ensure_homebrew() {
    local allow_install="$1"
    local result_var="$2"
    local resolved_brew_bin

    if bootstrap_refresh_brew resolved_brew_bin; then
        printf -v "$result_var" '%s' "$resolved_brew_bin"
        bootstrap_log "Homebrew is available at '$resolved_brew_bin'."
        return 0
    fi

    [[ "$allow_install" == "true" ]] || bootstrap_die "Homebrew is required. Install Homebrew from https://brew.sh/ or rerun without --no-homebrew-install."

    bootstrap_install_homebrew resolved_brew_bin || bootstrap_die "Homebrew installation failed."
    if [[ "${BASE_BOOTSTRAP_DRY_RUN:-false}" == "true" ]]; then
        printf -v "$result_var" '%s' "$resolved_brew_bin"
        return 0
    fi

    bootstrap_refresh_brew resolved_brew_bin || bootstrap_die "Homebrew installation completed, but 'brew' was not found."
    printf -v "$result_var" '%s' "$resolved_brew_bin"
    bootstrap_log "Homebrew is available at '$resolved_brew_bin'."
}

bootstrap_git_usable() {
    command -v git >/dev/null 2>&1 || return 1
    git --version >/dev/null 2>&1
}

bootstrap_ensure_git() {
    local brew_bin="$1"

    if bootstrap_git_usable; then
        bootstrap_log "Git is available."
        return 0
    fi

    bootstrap_log "Installing Git through Homebrew."
    bootstrap_run "$brew_bin" install git || bootstrap_die "Failed to install Git through Homebrew."
    if [[ "${BASE_BOOTSTRAP_DRY_RUN:-false}" == "true" ]]; then
        return 0
    fi

    bootstrap_git_usable || bootstrap_die "Git was installed, but 'git --version' still does not work."
}

bootstrap_bash_version_number() {
    printf '%s\n' "${BASE_BOOTSTRAP_TEST_BASH_VERSION:-${BASH_VERSINFO[0]}${BASH_VERSINFO[1]}}"
}

bootstrap_find_supported_bash() {
    local candidate
    local candidates="${BASE_BOOTSTRAP_BASH_CANDIDATES:-/opt/homebrew/bin/bash:/usr/local/bin/bash}"
    local current_version
    local -a candidate_paths

    current_version="$(bootstrap_bash_version_number)"
    if [[ "$current_version" -ge 42 ]]; then
        printf '%s\n' "${BASH:-bash}"
        return 0
    fi

    IFS=: read -ra candidate_paths <<< "$candidates"
    for candidate in "${candidate_paths[@]}"; do
        [[ -n "$candidate" ]] || continue
        [[ -x "$candidate" ]] || continue
        printf '%s\n' "$candidate"
        return 0
    done

    return 1
}

bootstrap_ensure_supported_bash() {
    local brew_bin="$1"

    if bootstrap_find_supported_bash >/dev/null 2>&1; then
        bootstrap_log "Bash 4.2+ is available for Base."
        return 0
    fi

    bootstrap_log "Installing Bash 4.2+ through Homebrew."
    bootstrap_run "$brew_bin" install bash || bootstrap_die "Failed to install Bash through Homebrew."
    if [[ "${BASE_BOOTSTRAP_DRY_RUN:-false}" == "true" ]]; then
        return 0
    fi

    bootstrap_find_supported_bash >/dev/null 2>&1 || bootstrap_die "Bash was installed, but a supported Bash was not found."
}

bootstrap_source_checkout_present() {
    local install_dir="$1"

    [[ -d "$install_dir/.git" || -x "$install_dir/bin/basectl" ]]
}

bootstrap_brew_base_installed() {
    local brew_bin="$1"
    local formula="$2"

    [[ -n "$brew_bin" ]] || return 1
    "$brew_bin" list --formula "$formula" >/dev/null 2>&1
}

bootstrap_validate_mode() {
    local mode="$1"

    case "$mode" in
        ""|source|brew) return 0 ;;
        *) bootstrap_die "Invalid bootstrap mode '$mode'. Use --source, --brew, or BASE_BOOTSTRAP_MODE=source|brew." ;;
    esac
}

bootstrap_select_mode() {
    local requested_mode="$1"
    local install_dir="$2"
    local formula="$3"
    local brew_bin="$4"

    if [[ -n "$requested_mode" ]]; then
        printf '%s\n' "$requested_mode"
        return 0
    fi

    if bootstrap_brew_base_installed "$brew_bin" "$formula"; then
        printf 'brew\n'
        return 0
    fi

    if bootstrap_source_checkout_present "$install_dir"; then
        printf 'source\n'
        return 0
    fi

    printf 'source\n'
}

bootstrap_install_source() {
    local repo_url="$1"
    local install_dir="$2"
    local branch="$3"
    local parent_dir

    if [[ -d "$install_dir/.git" ]]; then
        bootstrap_log "Updating existing Base source checkout at '$install_dir'."
        bootstrap_run git -C "$install_dir" pull --ff-only || bootstrap_die "Failed to update Base source checkout."
        return 0
    fi

    if [[ -e "$install_dir" ]]; then
        bootstrap_die "Install path '$install_dir' exists but is not a Git checkout."
    fi

    bootstrap_log "Cloning Base into '$install_dir'."
    parent_dir="$(bootstrap_parent_dir "$install_dir")"
    bootstrap_run mkdir -p "$parent_dir" || bootstrap_die "Failed to create install parent directory '$parent_dir'."
    if [[ -n "$branch" ]]; then
        bootstrap_run git clone --branch "$branch" "$repo_url" "$install_dir" || bootstrap_die "Failed to clone Base repository."
    else
        bootstrap_run git clone "$repo_url" "$install_dir" || bootstrap_die "Failed to clone Base repository."
    fi
}

bootstrap_install_brew_base() {
    local brew_bin="$1"
    local formula="$2"

    if bootstrap_brew_base_installed "$brew_bin" "$formula"; then
        bootstrap_log "Base Homebrew formula '$formula' is already installed."
        return 0
    fi

    bootstrap_log "Installing Base with Homebrew formula '$formula'."
    bootstrap_run "$brew_bin" install "$formula" || bootstrap_die "Failed to install Base Homebrew formula '$formula'."
}

bootstrap_find_homebrew_basectl() {
    local brew_bin="$1"
    local active_basectl
    local candidate
    local prefix

    if [[ -n "$brew_bin" && "$brew_bin" != "brew" ]]; then
        prefix="$("$brew_bin" --prefix 2>/dev/null || true)"
        if [[ -n "$prefix" ]]; then
            candidate="$prefix/bin/basectl"
            if [[ -x "$candidate" ]]; then
                printf '%s\n' "$candidate"
                return 0
            fi
        fi
    fi

    active_basectl="$(command -v basectl 2>/dev/null || true)"
    case "$active_basectl" in
        /opt/homebrew/*|/usr/local/*)
            printf '%s\n' "$active_basectl"
            return 0
            ;;
    esac

    return 1
}

bootstrap_print_provenance() {
    local active_basectl
    local brew_bin="$3"
    local brew_basectl
    local install_dir="$1"
    local mode="$2"

    brew_basectl="$(bootstrap_find_homebrew_basectl "$brew_bin" || true)"
    active_basectl="$(command -v basectl 2>/dev/null || true)"

    bootstrap_log ""
    bootstrap_log "Base provenance:"
    if [[ "$mode" == "source" || -e "$install_dir" ]]; then
        bootstrap_log "  source checkout: $install_dir"
    else
        bootstrap_log "  source checkout: not found at $install_dir"
    fi
    if [[ -n "$brew_basectl" ]]; then
        bootstrap_log "  Homebrew basectl: $brew_basectl"
    else
        bootstrap_log "  Homebrew basectl: not found on PATH"
    fi
    if [[ -n "$active_basectl" ]]; then
        bootstrap_log "  active basectl: $active_basectl"
    else
        bootstrap_log "  active basectl: not found on PATH"
    fi
}

bootstrap_brew_basectl_command() {
    local brew_bin="$1"
    local brew_basectl
    local prefix

    brew_basectl="$(bootstrap_find_homebrew_basectl "$brew_bin" || true)"
    if [[ -n "$brew_basectl" ]]; then
        printf '%s\n' "$brew_basectl"
        return 0
    fi

    if [[ -n "$brew_bin" && "$brew_bin" != "brew" ]]; then
        prefix="$("$brew_bin" --prefix 2>/dev/null || true)"
        if [[ -n "$prefix" ]]; then
            printf '%s\n' "$prefix/bin/basectl"
            return 0
        fi
    fi

    printf 'basectl\n'
}

bootstrap_print_next_steps() {
    local basectl_command
    local brew_bin="$3"
    local install_dir="$1"
    local mode="$2"

    if [[ "$mode" == "source" ]]; then
        basectl_command="$install_dir/bin/basectl"
    else
        basectl_command="$(bootstrap_brew_basectl_command "$brew_bin")"
    fi

    bootstrap_log ""
    bootstrap_log "Run these commands to finish Base setup and shell integration:"
    bootstrap_log "  $basectl_command setup"
    bootstrap_log "  $basectl_command update-profile"
    bootstrap_log "  exec \"\$SHELL\" -l"
}

bootstrap_main() {
    local allow_homebrew_install="${BASE_BOOTSTRAP_HOMEBREW_INSTALL:-true}"
    local branch="${BASE_BOOTSTRAP_BRANCH:-}"
    local brew_bin=""
    local formula="${BASE_BOOTSTRAP_BREW_FORMULA:-basefoundry/base/base}"
    local install_dir="${BASE_BOOTSTRAP_INSTALL_DIR:-${BASE_HOME:-$HOME/work/base}}"
    local mode="${BASE_BOOTSTRAP_MODE:-}"
    local repo_url="${BASE_BOOTSTRAP_REPO_URL:-https://github.com/basefoundry/base.git}"

    BASE_BOOTSTRAP_DRY_RUN="${BASE_BOOTSTRAP_DRY_RUN:-false}"

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                bootstrap_usage
                return 0
                ;;
            --source)
                mode=source
                shift
                ;;
            --brew)
                mode=brew
                shift
                ;;
            --install-dir|--dir)
                [[ -n "${2:-}" ]] || bootstrap_die "Option '$1' requires an argument."
                install_dir="$2"
                shift 2
                ;;
            --repo-url)
                [[ -n "${2:-}" ]] || bootstrap_die "Option '--repo-url' requires an argument."
                repo_url="$2"
                shift 2
                ;;
            --branch)
                [[ -n "${2:-}" ]] || bootstrap_die "Option '--branch' requires an argument."
                branch="$2"
                shift 2
                ;;
            --no-homebrew-install)
                allow_homebrew_install=false
                shift
                ;;
            --dry-run)
                BASE_BOOTSTRAP_DRY_RUN=true
                shift
                ;;
            *)
                bootstrap_usage >&2
                bootstrap_die "Unknown option '$1'."
                ;;
        esac
    done

    bootstrap_validate_mode "$mode" || return $?
    install_dir="$(bootstrap_expand_path "$install_dir")" || return $?

    bootstrap_log "Base bootstrap"
    bootstrap_require_macos || return $?
    bootstrap_ensure_homebrew "$allow_homebrew_install" brew_bin || return $?
    bootstrap_ensure_git "$brew_bin" || return $?
    bootstrap_ensure_supported_bash "$brew_bin" || return $?

    mode="$(bootstrap_select_mode "$mode" "$install_dir" "$formula" "$brew_bin")" || return $?
    bootstrap_log "Install mode: $mode"

    case "$mode" in
        source)
            bootstrap_log "Repository: $repo_url"
            bootstrap_log "Install path: $install_dir"
            bootstrap_install_source "$repo_url" "$install_dir" "$branch" || return $?
            ;;
        brew)
            bootstrap_log "Formula: $formula"
            bootstrap_install_brew_base "$brew_bin" "$formula" || return $?
            ;;
    esac

    bootstrap_print_provenance "$install_dir" "$mode" "$brew_bin" || return $?
    bootstrap_print_next_steps "$install_dir" "$mode" "$brew_bin" || return $?
}

if [[ "${BASE_BOOTSTRAP_TESTING:-false}" != "true" ]]; then
    bootstrap_main "$@"
fi
