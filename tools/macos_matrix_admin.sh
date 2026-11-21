#!/usr/bin/env bash

# Configure the four local macOS accounts used by the install matrix. This
# script is intentionally separate from Base's ordinary setup path: it changes
# login shells and a narrowly scoped sudoers drop-in and therefore belongs to a
# maintainer-run, one-time machine preparation step.

MATRIX_USERS=(base-source-bash base-source-zsh base-brew-bash base-brew-zsh)
MATRIX_SUDOERS_FILE="${BASE_MATRIX_SUDOERS_FILE:-/etc/sudoers.d/base-macos-install-matrix}"
MATRIX_STATE_FILE="${BASE_MATRIX_STATE_FILE:-/var/db/base-macos-install-matrix/state}"
MATRIX_SHELLS_FILE="${BASE_MATRIX_SHELLS_FILE:-/etc/shells}"
MATRIX_OPERATOR="${BASE_MATRIX_OPERATOR:-${SUDO_USER:-$(id -un 2>/dev/null)}}"
MATRIX_DSCL="${BASE_MATRIX_DSCL:-/usr/bin/dscl}"
MATRIX_VISUDO="${BASE_MATRIX_VISUDO:-/usr/sbin/visudo}"
MATRIX_INSTALL="${BASE_MATRIX_INSTALL:-/usr/bin/install}"
MATRIX_BASH_PATH="${BASE_MATRIX_BASH_PATH:-}"

usage() {
    cat <<'EOF'
Usage:
  tools/macos_matrix_admin.sh [--dry-run]
  tools/macos_matrix_admin.sh --remove [--dry-run]
  tools/macos_matrix_admin.sh --help

Configure or remove the local four-account macOS install-matrix contract.

The normal action writes a scoped sudoers drop-in, registers the Homebrew Bash
login shell, and sets the two Bash matrix accounts to that shell. --dry-run
prints the planned actions without requiring root or changing the machine.
--remove restores the login shells and removes only state recorded by this
script.
EOF
}

log() {
    printf '%s\n' "$*"
}

error() {
    printf 'ERROR: %s\n' "$*" >&2
}

fail() {
    error "$*"
    return 1
}

is_dry_run=0
is_remove=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) is_dry_run=1 ;;
        --remove) is_remove=1 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; error "Unknown option '$arg'."; exit 2 ;;
    esac
done

if [[ -z "$MATRIX_BASH_PATH" ]]; then
    if ((is_remove)) && [[ -f "$MATRIX_STATE_FILE" ]]; then
        MATRIX_BASH_PATH="$(awk -F= '$1 == "bash_path" {print substr($0, index($0, "=") + 1); exit}' "$MATRIX_STATE_FILE")"
    elif ((is_remove)); then
        MATRIX_BASH_PATH=/opt/homebrew/bin/bash
    elif [[ -x /opt/homebrew/bin/bash ]]; then
        MATRIX_BASH_PATH=/opt/homebrew/bin/bash
    elif [[ -x /usr/local/bin/bash ]]; then
        MATRIX_BASH_PATH=/usr/local/bin/bash
    else
        error "Homebrew Bash was not found at /opt/homebrew/bin/bash or /usr/local/bin/bash."
        exit 1
    fi
fi

require_root() {
    local uid
    uid="$(id -u 2>/dev/null)" || return 1
    ((uid == 0)) || fail "This action changes macOS account state and must run as root (use --dry-run to preview it)."
}

read_user_shell() {
    local user="$1" output line
    output="$($MATRIX_DSCL . -read "/Users/$user" UserShell 2>/dev/null)" || return 1
    while IFS= read -r line; do
        case "$line" in
            UserShell:*) printf '%s\n' "${line#UserShell: }"; return 0 ;;
        esac
    done <<<"$output"
    return 1
}

state_value() {
    local key="$1"
    [[ -f "$MATRIX_STATE_FILE" ]] || return 1
    awk -F= -v wanted="$key" '$1 == wanted {print substr($0, index($0, "=") + 1); exit}' "$MATRIX_STATE_FILE"
}

state_user_shell() {
    local user="$1"
    [[ -f "$MATRIX_STATE_FILE" ]] || return 1
    awk -F '\t' -v wanted="$user" '$1 == "user" && $2 == wanted {print $3; exit}' "$MATRIX_STATE_FILE"
}

write_state() {
    local state_dir user shell
    state_dir="$(dirname "$MATRIX_STATE_FILE")"
    mkdir -p "$state_dir" || return 1
    {
        printf 'version=1\n'
        printf 'bash_path=%s\n' "$MATRIX_BASH_PATH"
        printf 'operator=%s\n' "$MATRIX_OPERATOR"
        printf 'shell_added=%s\n' "$(grep -Fxq "$MATRIX_BASH_PATH" "$MATRIX_SHELLS_FILE" 2>/dev/null && printf 0 || printf 1)"
        for user in "${MATRIX_USERS[@]}"; do
            shell="$(read_user_shell "$user")" || return 1
            printf 'user\t%s\t%s\n' "$user" "$shell"
        done
    } >"$MATRIX_STATE_FILE" || return 1
    chmod 0600 "$MATRIX_STATE_FILE" || return 1
}

ensure_shell_entry() {
    if grep -Fxq "$MATRIX_BASH_PATH" "$MATRIX_SHELLS_FILE" 2>/dev/null; then
        log "Homebrew Bash is already registered in $MATRIX_SHELLS_FILE."
        return 0
    fi
    log "Registering $MATRIX_BASH_PATH in $MATRIX_SHELLS_FILE."
    ((is_dry_run)) && return 0
    printf '%s\n' "$MATRIX_BASH_PATH" >>"$MATRIX_SHELLS_FILE" || return 1
}

write_sudoers() {
    local sudoers_dir temp
    sudoers_dir="$(dirname "$MATRIX_SUDOERS_FILE")"
    mkdir -p "$sudoers_dir" || return 1
    temp="${MATRIX_SUDOERS_FILE}.tmp.$$"
    printf '%s ALL = (base-source-bash, base-source-zsh, base-brew-bash, base-brew-zsh) NOPASSWD: ALL\n' "$MATRIX_OPERATOR" >"$temp" || return 1
    if ! "$MATRIX_VISUDO" -cf "$temp" >/dev/null 2>&1; then
        rm -f "$temp"
        return 1
    fi
    "$MATRIX_INSTALL" -o root -g wheel -m 0440 "$temp" "$MATRIX_SUDOERS_FILE" || {
        rm -f "$temp"
        return 1
    }
    rm -f "$temp"
}

configure() {
    local user desired current
    if ((is_dry_run)); then
        log "DRY-RUN: would configure matrix accounts: ${MATRIX_USERS[*]}"
        log "DRY-RUN: would grant $MATRIX_OPERATOR passwordless sudo only when running as the four matrix users."
        log "DRY-RUN: would register $MATRIX_BASH_PATH in $MATRIX_SHELLS_FILE."
    else
        require_root || return 1
        if [[ ! -f "$MATRIX_STATE_FILE" ]]; then
            write_state || return 1
        else
            MATRIX_BASH_PATH="$(state_value bash_path)" || return 1
            log "Using existing matrix state at $MATRIX_STATE_FILE."
        fi
    fi

    ensure_shell_entry || return 1
    if ((is_dry_run)); then
        for user in "${MATRIX_USERS[@]}"; do
            desired=/bin/zsh
            [[ "$user" == *-bash ]] && desired="$MATRIX_BASH_PATH"
            log "DRY-RUN: would set $user login shell to $desired."
        done
        log "DRY-RUN: would validate and install $MATRIX_SUDOERS_FILE."
        return 0
    fi

    for user in "${MATRIX_USERS[@]}"; do
        desired=/bin/zsh
        [[ "$user" == *-bash ]] && desired="$MATRIX_BASH_PATH"
        current="$(read_user_shell "$user")" || return 1
        if [[ "$current" == "$desired" ]]; then
            log "$user already uses $desired."
        else
            log "Setting $user login shell to $desired."
            "$MATRIX_DSCL" . -create "/Users/$user" UserShell "$desired" || return 1
        fi
    done
    log "Validating and installing $MATRIX_SUDOERS_FILE."
    write_sudoers || return 1
    log "macOS install-matrix admin setup complete."
}

remove_configuration() {
    local user old_shell shell_added
    if [[ ! -f "$MATRIX_STATE_FILE" ]]; then
        log "No matrix state exists at $MATRIX_STATE_FILE; nothing to remove."
        return 0
    fi
    MATRIX_BASH_PATH="$(state_value bash_path)" || return 1
    if ((is_dry_run)); then
        log "DRY-RUN: would restore matrix account login shells from $MATRIX_STATE_FILE."
        log "DRY-RUN: would remove $MATRIX_SUDOERS_FILE."
        if [[ "$(state_value shell_added)" == 1 ]]; then
            log "DRY-RUN: would remove $MATRIX_BASH_PATH from $MATRIX_SHELLS_FILE."
        fi
        return 0
    fi
    require_root || return 1
    for user in "${MATRIX_USERS[@]}"; do
        old_shell="$(state_user_shell "$user")" || return 1
        log "Restoring $user login shell to $old_shell."
        "$MATRIX_DSCL" . -create "/Users/$user" UserShell "$old_shell" || return 1
    done
    shell_added="$(state_value shell_added)"
    if [[ "$shell_added" == 1 ]] && grep -Fxq "$MATRIX_BASH_PATH" "$MATRIX_SHELLS_FILE"; then
        log "Removing $MATRIX_BASH_PATH from $MATRIX_SHELLS_FILE."
        grep -Fvx "$MATRIX_BASH_PATH" "$MATRIX_SHELLS_FILE" >"${MATRIX_SHELLS_FILE}.tmp.$$" || {
            [[ "$?" -eq 1 ]] || return 1
        }
        "$MATRIX_INSTALL" -o root -g wheel -m 0644 "${MATRIX_SHELLS_FILE}.tmp.$$" "$MATRIX_SHELLS_FILE" || return 1
        rm -f "${MATRIX_SHELLS_FILE}.tmp.$$"
    fi
    if [[ -e "$MATRIX_SUDOERS_FILE" ]]; then
        log "Removing $MATRIX_SUDOERS_FILE."
        rm -f "$MATRIX_SUDOERS_FILE" || return 1
    fi
    rm -f "$MATRIX_STATE_FILE" || return 1
    log "macOS install-matrix admin setup removed."
}

if ((is_remove)); then
    remove_configuration
else
    configure
fi
