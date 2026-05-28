#!/usr/bin/env bash

set -euo pipefail

install_usage() {
    cat <<'EOF'
Usage:
  install.sh [options]

Options:
  --dir <path>       Install or update Base at this path. Defaults to ~/work/base.
  --repo-url <url>   Git repository URL to clone. Defaults to https://github.com/codeforester/base.git.
  --branch <name>    Clone a specific branch when installing into a new directory.
  --no-profile       Skip basectl update-profile after setup.
  --dry-run          Print planned actions without making changes.
  -h, --help         Show this help text.

Install or update Base, run basectl setup, and optionally update shell startup files.
EOF
}

install_log() {
    printf '%s\n' "$*"
}

install_die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

install_expand_path() {
    local path="$1"
    case "$path" in
        "~") printf '%s\n' "$HOME" ;;
        "~/"*) printf '%s/%s\n' "$HOME" "${path#"~/"}" ;;
        *) printf '%s\n' "$path" ;;
    esac
}

install_run() {
    if [[ "${BASE_INSTALL_DRY_RUN:-false}" == "true" ]]; then
        printf '[DRY-RUN] Would run:'
        printf ' %q' "$@"
        printf '\n'
        return 0
    fi
    "$@"
}

install_clone_or_update() {
    local repo_url="$1"
    local install_dir="$2"
    local branch="$3"

    if [[ "${BASE_INSTALL_DRY_RUN:-false}" != "true" ]] && ! command -v git >/dev/null 2>&1; then
        install_die "Git is required to install Base."
    fi

    if [[ -d "$install_dir/.git" ]]; then
        install_log "Updating existing Base checkout at '$install_dir'."
        install_run git -C "$install_dir" pull --ff-only
        return 0
    fi

    if [[ -e "$install_dir" ]]; then
        install_die "Install path '$install_dir' exists but is not a Git checkout."
    fi

    install_log "Cloning Base into '$install_dir'."
    install_run mkdir -p "$(dirname "$install_dir")"
    if [[ -n "$branch" ]]; then
        install_run git clone --branch "$branch" "$repo_url" "$install_dir"
    else
        install_run git clone "$repo_url" "$install_dir"
    fi
}

install_run_base_setup() {
    local install_dir="$1"

    install_log "Running basectl setup."
    install_run "$install_dir/bin/basectl" setup
}

install_run_update_profile() {
    local install_dir="$1"

    install_log "Updating shell startup files."
    install_run "$install_dir/bin/basectl" update-profile
}

install_main() {
    local repo_url="${BASE_INSTALL_REPO_URL:-https://github.com/codeforester/base.git}"
    local install_dir="${BASE_INSTALL_DIR:-$HOME/work/base}"
    local branch="${BASE_INSTALL_BRANCH:-}"
    local update_profile="${BASE_INSTALL_UPDATE_PROFILE:-true}"
    BASE_INSTALL_DRY_RUN="${BASE_INSTALL_DRY_RUN:-false}"

    while (($# > 0)); do
        case "$1" in
            -h|--help)
                install_usage
                return 0
                ;;
            --dir)
                [[ -n "${2:-}" ]] || install_die "Option '--dir' requires an argument."
                install_dir="$2"
                shift 2
                ;;
            --repo-url)
                [[ -n "${2:-}" ]] || install_die "Option '--repo-url' requires an argument."
                repo_url="$2"
                shift 2
                ;;
            --branch)
                [[ -n "${2:-}" ]] || install_die "Option '--branch' requires an argument."
                branch="$2"
                shift 2
                ;;
            --no-profile)
                update_profile=false
                shift
                ;;
            --dry-run)
                BASE_INSTALL_DRY_RUN=true
                shift
                ;;
            *)
                install_usage >&2
                install_die "Unknown option '$1'."
                ;;
        esac
    done

    install_dir="$(install_expand_path "$install_dir")"

    install_log "Base installer"
    install_log "Repository: $repo_url"
    install_log "Install path: $install_dir"

    install_clone_or_update "$repo_url" "$install_dir" "$branch"
    install_run_base_setup "$install_dir"
    if [[ "$update_profile" == "true" ]]; then
        install_run_update_profile "$install_dir"
    fi

    install_log "Base installation is complete."
    if [[ "$update_profile" == "true" ]]; then
        install_log "Restart your shell with: exec \"\$SHELL\" -l"
    fi
}

if [[ "${BASE_INSTALL_TESTING:-false}" != "true" ]]; then
    install_main "$@"
fi
