#!/usr/bin/env bash

# Explicit error handling is used instead of set -e to keep failure paths
# clear and predictable. See Base STANDARDS.md section 2.

# Project-owned values. Copy this template into your project and customize them.
PROJECT_NAME="${PROJECT_NAME:-example-project}"
PROJECT_REPO_URL="${PROJECT_REPO_URL:-https://github.com/example/example-project.git}"
WORKSPACE_DIR="${WORKSPACE_DIR:-$HOME/work}"
BASE_DIR="${BASE_DIR:-$WORKSPACE_DIR/base}"
PROJECT_DIR="${PROJECT_DIR:-$WORKSPACE_DIR/$PROJECT_NAME}"
BASE_INSTALL_URL="${BASE_INSTALL_URL:-https://raw.githubusercontent.com/basefoundry/base/master/install.sh}"
RUN_UPDATE_PROFILE="${RUN_UPDATE_PROFILE:-true}"

INSTALLER_TMP=""

log() {
    printf '%s\n' "$*"
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

run() {
    printf '+'
    printf ' %q' "$@"
    printf '\n'
    "$@"
}

cleanup() {
    if [[ -n "$INSTALLER_TMP" && -f "$INSTALLER_TMP" ]]; then
        rm -f "$INSTALLER_TMP"
    fi
}
trap cleanup EXIT

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "Required command '$1' was not found."
}

ensure_workspace() {
    run mkdir -p "$WORKSPACE_DIR" || die "Failed to create workspace directory '$WORKSPACE_DIR'."
}

install_or_update_base() {
    require_command git

    if [[ -d "$BASE_DIR/.git" ]]; then
        log "Updating Base at '$BASE_DIR'."
        run git -C "$BASE_DIR" pull --ff-only || die "Failed to update Base at '$BASE_DIR'."
        return 0
    fi

    if [[ -e "$BASE_DIR" ]]; then
        die "Base path '$BASE_DIR' exists but is not a Git checkout."
    fi

    require_command curl
    INSTALLER_TMP="$(mktemp "${TMPDIR:-/tmp}/base-install.XXXXXX")" || die "Failed to create installer temp file."
    log "Installing Base into '$BASE_DIR'."
    run curl -fsSL -o "$INSTALLER_TMP" "$BASE_INSTALL_URL" || die "Failed to download Base installer."
    run bash "$INSTALLER_TMP" --dir "$BASE_DIR" --no-profile || die "Failed to install Base into '$BASE_DIR'."
}

clone_or_update_project() {
    require_command git

    if [[ -d "$PROJECT_DIR/.git" ]]; then
        log "Updating $PROJECT_NAME at '$PROJECT_DIR'."
        run git -C "$PROJECT_DIR" pull --ff-only || die "Failed to update $PROJECT_NAME at '$PROJECT_DIR'."
        return 0
    fi

    if [[ -e "$PROJECT_DIR" ]]; then
        die "Project path '$PROJECT_DIR' exists but is not a Git checkout."
    fi

    log "Cloning $PROJECT_NAME into '$PROJECT_DIR'."
    run git clone "$PROJECT_REPO_URL" "$PROJECT_DIR" || die "Failed to clone $PROJECT_NAME into '$PROJECT_DIR'."
}

run_project_setup() {
    local manifest="$PROJECT_DIR/base_manifest.yaml"

    [[ -f "$manifest" ]] || die "Project manifest was not found at '$manifest'."
    [[ -x "$BASE_DIR/bin/basectl" ]] || die "Base CLI was not found at '$BASE_DIR/bin/basectl'."

    if ! run "$BASE_DIR/bin/basectl" setup --manifest "$PROJECT_DIR/base_manifest.yaml" "$PROJECT_NAME"; then
        log "Project setup failed. Running Base doctor for more detail."
        run "$BASE_DIR/bin/basectl" doctor "$PROJECT_NAME" || true
        die "Project setup failed."
    fi
}

maybe_update_profile() {
    case "$RUN_UPDATE_PROFILE" in
        true|1|yes)
            run "$BASE_DIR/bin/basectl" update-profile || die "Failed to update shell profiles."
            ;;
        false|0|no)
            log "Skipping shell profile update."
            ;;
        *)
            die "RUN_UPDATE_PROFILE must be true or false."
            ;;
    esac
}

main() {
    log "Installing $PROJECT_NAME workspace."
    log "Workspace: $WORKSPACE_DIR"

    ensure_workspace || die "Workspace preparation failed."
    install_or_update_base || die "Base installation failed."
    clone_or_update_project || die "$PROJECT_NAME checkout failed."
    run_project_setup || die "$PROJECT_NAME setup failed."
    maybe_update_profile || die "Shell profile update failed."

    log "$PROJECT_NAME setup is complete."
    log "Project-specific next steps belong here."
}

main "$@"
