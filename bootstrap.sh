#!/usr/bin/env bash

set -euo pipefail

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

BOOTSTRAP_BREW_BIN=""

bootstrap_find_brew() {
    local candidate
    local candidates="${BASE_BOOTSTRAP_BREW_CANDIDATES:-/opt/homebrew/bin/brew:/usr/local/bin/brew}"
    local old_ifs

    if [[ -n "${BASE_BOOTSTRAP_BREW_BIN:-}" && -x "${BASE_BOOTSTRAP_BREW_BIN:-}" ]]; then
        printf '%s\n' "$BASE_BOOTSTRAP_BREW_BIN"
        return 0
    fi

    if command -v brew >/dev/null 2>&1; then
        command -v brew
        return 0
    fi

    old_ifs="$IFS"
    IFS=:
    for candidate in $candidates; do
        IFS="$old_ifs"
        [[ -x "$candidate" ]] || continue
        printf '%s\n' "$candidate"
        return 0
    done
    IFS="$old_ifs"

    return 1
}

bootstrap_refresh_brew() {
    local brew_bin
    local brew_dir

    brew_bin="$(bootstrap_find_brew || true)"
    [[ -n "$brew_bin" ]] || return 1

    BOOTSTRAP_BREW_BIN="$brew_bin"
    brew_dir="$(bootstrap_parent_dir "$brew_bin")"
    case ":$PATH:" in
        *":$brew_dir:"*) ;;
        *) PATH="$brew_dir:$PATH"; export PATH ;;
    esac
    return 0
}

bootstrap_install_homebrew() {
    local installer_url="${BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL:-https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh}"

    bootstrap_log "Installing Homebrew."
    if [[ "${BASE_BOOTSTRAP_DRY_RUN:-false}" == "true" ]]; then
        bootstrap_log "[DRY-RUN] Would run: /bin/bash -c <Homebrew installer from $installer_url>"
        BOOTSTRAP_BREW_BIN=brew
        return 0
    fi

    command -v curl >/dev/null 2>&1 || bootstrap_die "curl is required to install Homebrew."
    /bin/bash -c "$(curl -fsSL "$installer_url")"
}

bootstrap_ensure_homebrew() {
    local allow_install="$1"

    if bootstrap_refresh_brew; then
        bootstrap_log "Homebrew is available at '$BOOTSTRAP_BREW_BIN'."
        return 0
    fi

    [[ "$allow_install" == "true" ]] || bootstrap_die "Homebrew is required. Install Homebrew from https://brew.sh/ or rerun without --no-homebrew-install."

    bootstrap_install_homebrew
    if [[ "${BASE_BOOTSTRAP_DRY_RUN:-false}" == "true" ]]; then
        return 0
    fi

    bootstrap_refresh_brew || bootstrap_die "Homebrew installation completed, but 'brew' was not found."
    bootstrap_log "Homebrew is available at '$BOOTSTRAP_BREW_BIN'."
}

bootstrap_git_usable() {
    command -v git >/dev/null 2>&1 || return 1
    git --version >/dev/null 2>&1
}

bootstrap_ensure_git() {
    if bootstrap_git_usable; then
        bootstrap_log "Git is available."
        return 0
    fi

    bootstrap_log "Installing Git through Homebrew."
    bootstrap_run "$BOOTSTRAP_BREW_BIN" install git
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
    local old_ifs

    current_version="$(bootstrap_bash_version_number)"
    if [[ "$current_version" -ge 42 ]]; then
        printf '%s\n' "${BASH:-bash}"
        return 0
    fi

    old_ifs="$IFS"
    IFS=:
    for candidate in $candidates; do
        IFS="$old_ifs"
        [[ -x "$candidate" ]] || continue
        printf '%s\n' "$candidate"
        return 0
    done
    IFS="$old_ifs"

    return 1
}

bootstrap_ensure_supported_bash() {
    if bootstrap_find_supported_bash >/dev/null 2>&1; then
        bootstrap_log "Bash 4.2+ is available for Base."
        return 0
    fi

    bootstrap_log "Installing Bash 4.2+ through Homebrew."
    bootstrap_run "$BOOTSTRAP_BREW_BIN" install bash
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
    local formula="$1"

    [[ -n "$BOOTSTRAP_BREW_BIN" ]] || return 1
    "$BOOTSTRAP_BREW_BIN" list --formula "$formula" >/dev/null 2>&1
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

    if [[ -n "$requested_mode" ]]; then
        printf '%s\n' "$requested_mode"
        return 0
    fi

    if bootstrap_brew_base_installed "$formula"; then
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
        bootstrap_run git -C "$install_dir" pull --ff-only
        return 0
    fi

    if [[ -e "$install_dir" ]]; then
        bootstrap_die "Install path '$install_dir' exists but is not a Git checkout."
    fi

    bootstrap_log "Cloning Base into '$install_dir'."
    parent_dir="$(bootstrap_parent_dir "$install_dir")"
    bootstrap_run mkdir -p "$parent_dir"
    if [[ -n "$branch" ]]; then
        bootstrap_run git clone --branch "$branch" "$repo_url" "$install_dir"
    else
        bootstrap_run git clone "$repo_url" "$install_dir"
    fi
}

bootstrap_install_brew_base() {
    local formula="$1"

    if bootstrap_brew_base_installed "$formula"; then
        bootstrap_log "Base Homebrew formula '$formula' is already installed."
        return 0
    fi

    bootstrap_log "Installing Base with Homebrew formula '$formula'."
    bootstrap_run "$BOOTSTRAP_BREW_BIN" install "$formula"
}

bootstrap_find_homebrew_basectl() {
    local active_basectl
    local candidate
    local prefix

    if [[ -n "$BOOTSTRAP_BREW_BIN" && "$BOOTSTRAP_BREW_BIN" != "brew" ]]; then
        prefix="$("$BOOTSTRAP_BREW_BIN" --prefix 2>/dev/null || true)"
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
    local brew_basectl
    local install_dir="$1"
    local mode="$2"

    brew_basectl="$(bootstrap_find_homebrew_basectl || true)"
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
    local brew_basectl
    local prefix

    brew_basectl="$(bootstrap_find_homebrew_basectl || true)"
    if [[ -n "$brew_basectl" ]]; then
        printf '%s\n' "$brew_basectl"
        return 0
    fi

    if [[ -n "$BOOTSTRAP_BREW_BIN" && "$BOOTSTRAP_BREW_BIN" != "brew" ]]; then
        prefix="$("$BOOTSTRAP_BREW_BIN" --prefix 2>/dev/null || true)"
        if [[ -n "$prefix" ]]; then
            printf '%s\n' "$prefix/bin/basectl"
            return 0
        fi
    fi

    printf 'basectl\n'
}

bootstrap_print_next_steps() {
    local basectl_command
    local install_dir="$1"
    local mode="$2"

    if [[ "$mode" == "source" ]]; then
        basectl_command="$install_dir/bin/basectl"
    else
        basectl_command="$(bootstrap_brew_basectl_command)"
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
    local formula="${BASE_BOOTSTRAP_BREW_FORMULA:-codeforester/base/base}"
    local install_dir="${BASE_BOOTSTRAP_INSTALL_DIR:-${BASE_HOME:-$HOME/work/base}}"
    local mode="${BASE_BOOTSTRAP_MODE:-}"
    local repo_url="${BASE_BOOTSTRAP_REPO_URL:-https://github.com/codeforester/base.git}"

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

    bootstrap_validate_mode "$mode"
    install_dir="$(bootstrap_expand_path "$install_dir")"

    bootstrap_log "Base bootstrap"
    bootstrap_require_macos
    bootstrap_ensure_homebrew "$allow_homebrew_install"
    bootstrap_ensure_git
    bootstrap_ensure_supported_bash

    mode="$(bootstrap_select_mode "$mode" "$install_dir" "$formula")"
    bootstrap_log "Install mode: $mode"

    case "$mode" in
        source)
            bootstrap_log "Repository: $repo_url"
            bootstrap_log "Install path: $install_dir"
            bootstrap_install_source "$repo_url" "$install_dir" "$branch"
            ;;
        brew)
            bootstrap_log "Formula: $formula"
            bootstrap_install_brew_base "$formula"
            ;;
    esac

    bootstrap_print_provenance "$install_dir" "$mode"
    bootstrap_print_next_steps "$install_dir" "$mode"
}

if [[ "${BASE_BOOTSTRAP_TESTING:-false}" != "true" ]]; then
    bootstrap_main "$@"
fi
