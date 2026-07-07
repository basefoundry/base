#!/usr/bin/env bash

[[ -n "${_base_update_profile_subcommand_sourced:-}" ]] && return 0
_base_update_profile_subcommand_sourced=1
readonly _base_update_profile_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_update_profile_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl update-profile [options]

Options:
  --defaults  Enable Base's optional Bash/Zsh shell defaults.
  --no-defaults
              Disable Base's optional Bash/Zsh shell defaults.
  --remove    Remove Base-managed sections from Bash/Zsh startup files.
  --dry-run   Show what would be updated without changing files.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Create or update Base-managed sections in Bash and Zsh startup files.

Updated files:
  ~/.base.d/profile.conf
  ~/.bash_profile
  ~/.bashrc
  ~/.zprofile
  ~/.zshrc
EOF
}

base_update_profile_usage_error() {
    print_error "$*"
    printf "Run 'basectl update-profile --help' for usage.\n" >&2
    return 2
}

base_update_profile_source_file_library() {
    import_base_lib file/lib_file.sh
    assert_function_exists file_section_exists file_section_needs_update
}

base_update_profile_shell_double_quote() {
    local value="$1"
    local escaped="$value"

    escaped="${escaped//\\/\\\\}"
    escaped="${escaped//\"/\\\"}"
    escaped="${escaped//\$/\\$}"
    escaped="${escaped//\`/\\\`}"
    printf '"%s"\n' "$escaped"
}

base_update_profile_source_line() {
    local source_path="$1"
    local quoted_source_path

    quoted_source_path="$(base_update_profile_shell_double_quote "$source_path")" || return 1
    printf '%s\n' '# shellcheck source=/dev/null'
    printf 'source %s\n' "$quoted_source_path"
}

base_update_profile_file_ends_with_newline() {
    local target_file="$1"
    local line=""

    [[ -r "$target_file" && -s "$target_file" ]] || return 0
    while IFS= read -r line; do
        line=""
    done < "$target_file" 2>/dev/null || return 0

    [[ -z "$line" ]]
}

base_update_profile_file_last_line_is_empty() {
    local target_file="$1"
    local last_line=""
    local line=""

    [[ -r "$target_file" && -s "$target_file" ]] || return 0
    while IFS= read -r line; do
        last_line="$line"
        line=""
    done < "$target_file" 2>/dev/null || return 0
    [[ -z "$line" ]] || last_line="$line"

    [[ -z "$last_line" ]]
}

base_update_profile_section_lines() {
    local snippet_name="$1"
    local snippet_path="$BASE_SHELL_DIR/$snippet_name"

    printf '%s\n' "# Managed by Base. Local edits inside this block may be overwritten."
    printf '%s\n' "# Refresh with: basectl update-profile"
    base_update_profile_source_line "$snippet_path" || return 1
}

base_update_profile_prepare_section_spacing() {
    local target_file="$1"
    local start_marker="$2"
    [[ -s "$target_file" ]] || return 0
    grep -qF -- "$start_marker" "$target_file" && return 0

    if ! base_update_profile_file_ends_with_newline "$target_file"; then
        printf '\n\n' >> "$target_file"
        return 0
    fi

    base_update_profile_file_last_line_is_empty "$target_file" && return 0

    printf '\n' >> "$target_file"
}

base_update_profile_start_marker() {
    local snippet_name="$1"

    printf '# >>> base: %s managed >>>\n' "$snippet_name"
}

base_update_profile_end_marker() {
    local snippet_name="$1"

    printf '# <<< base: %s managed <<<\n' "$snippet_name"
}

base_update_profile_backup_path() {
    local target_file="$1"
    local timestamp="$2"
    local backup_path="${target_file}.backup.${timestamp}"
    local suffix=1

    while [[ -e "$backup_path" ]]; do
        backup_path="${target_file}.backup.${timestamp}.${suffix}"
        suffix=$((suffix + 1))
    done

    printf '%s\n' "$backup_path"
}

base_update_profile_backup_existing_file() {
    local target_file="$1"
    local timestamp="$2"
    local dry_run="$3"
    local backup_path

    [[ -f "$target_file" ]] || return 0

    backup_path="$(base_update_profile_backup_path "$target_file" "$timestamp")" ||
        fatal_error "Unable to resolve backup path for '$target_file'."

    if ((dry_run)); then
        log_info "[DRY-RUN] Would back up '$target_file' to '$backup_path'."
        return 0
    fi

    log_info "Backing up '$target_file' to '$backup_path'."
    cp -p "$target_file" "$backup_path" || fatal_error "Unable to back up '$target_file' to '$backup_path'."
}

base_update_profile_update_file_needs_change() {
    local target_file="$1"
    local snippet_name="$2"
    local start_marker="$3"
    local end_marker="$4"
    local lines=()

    [[ -f "$target_file" ]] || return 0

    mapfile -t lines < <(base_update_profile_section_lines "$snippet_name") || return 2
    file_section_needs_update "$target_file" "$start_marker" "$end_marker" "${lines[@]}"
}

base_update_profile_remove_file_needs_change() {
    local target_file="$1"
    local start_marker="$2"
    local end_marker="$3"

    file_section_exists "$target_file" "$start_marker" "$end_marker"
}

base_update_profile_update_file() {
    local target_file="$1"
    local snippet_name="$2"
    local dry_run="$3"
    local backup_timestamp="$4"
    local start_marker
    local end_marker
    local lines=()

    start_marker="$(base_update_profile_start_marker "$snippet_name")" || return 1
    end_marker="$(base_update_profile_end_marker "$snippet_name")" || return 1
    mapfile -t lines < <(base_update_profile_section_lines "$snippet_name") || return 1

    base_update_profile_update_file_needs_change "$target_file" "$snippet_name" "$start_marker" "$end_marker"
    case $? in
        0)
            ;;
        1)
            return 0
            ;;
        *)
            return 1
            ;;
    esac

    if ((dry_run)); then
        base_update_profile_backup_existing_file "$target_file" "$backup_timestamp" "$dry_run" || return 1
        log_info "[DRY-RUN] Would update '$target_file' with section '$snippet_name'."
        return 0
    fi

    base_update_profile_backup_existing_file "$target_file" "$backup_timestamp" "$dry_run" || return 1
    safe_touch "$target_file"
    base_update_profile_prepare_section_spacing "$target_file" "$start_marker" || return 1
    update_file_section "$target_file" "$start_marker" "$end_marker" "${lines[@]}"
}

base_update_profile_remove_file() {
    local target_file="$1"
    local snippet_name="$2"
    local dry_run="$3"
    local backup_timestamp="$4"
    local start_marker
    local end_marker

    start_marker="$(base_update_profile_start_marker "$snippet_name")" || return 1
    end_marker="$(base_update_profile_end_marker "$snippet_name")" || return 1

    base_update_profile_remove_file_needs_change "$target_file" "$start_marker" "$end_marker"
    case $? in
        0)
            ;;
        1)
            return 0
            ;;
        *)
            return 1
            ;;
    esac

    if ((dry_run)); then
        base_update_profile_backup_existing_file "$target_file" "$backup_timestamp" "$dry_run" || return 1
        log_info "[DRY-RUN] Would remove section '$snippet_name' from '$target_file'."
        return 0
    fi

    base_update_profile_backup_existing_file "$target_file" "$backup_timestamp" "$dry_run" || return 1
    update_file_section -r "$target_file" "$start_marker" "$end_marker"
}

base_update_profile_state_dir() {
    printf '%s\n' "$HOME/.base.d"
}

base_update_profile_profile_conf() {
    printf '%s/profile.conf\n' "$(base_update_profile_state_dir)"
}

base_update_profile_defaults_previously_enabled() {
    local profile_conf

    profile_conf="$(base_update_profile_profile_conf)" || return 1
    [[ -f "$profile_conf" ]] || return 1

    (
        # shellcheck source=/dev/null
        source "$profile_conf"
        [[ "${BASE_ENABLE_BASH_DEFAULTS:-false}" == true || "${BASE_ENABLE_ZSH_DEFAULTS:-false}" == true ]]
    )
}

base_update_profile_write_profile_conf() {
    local enable_defaults="$1"
    local disable_defaults="$2"
    local dry_run="$3"
    local state_dir
    local profile_conf
    local temp_file
    local enable_value=false

    state_dir="$(base_update_profile_state_dir)" || return 1
    profile_conf="$(base_update_profile_profile_conf)" || return 1

    if ((disable_defaults)); then
        enable_value=false
    elif ((enable_defaults)) || base_update_profile_defaults_previously_enabled; then
        enable_value=true
    fi

    if ((dry_run)); then
        log_info "[DRY-RUN] Would update '$profile_conf'."
        return 0
    fi

    safe_mkdir -p "$state_dir"
    temp_file="$(mktemp "$profile_conf.XXXXXX")" || fatal_error "Unable to create temporary profile config for '$profile_conf'."

    if ! {
        printf '%s\n' '# Managed by Base. Run `basectl update-profile` to refresh this file.'
        printf '%s\n' 'BASE_PROFILE_VERSION=1'
        printf 'BASE_ENABLE_BASH_DEFAULTS=%s\n' "$enable_value"
        printf 'BASE_ENABLE_ZSH_DEFAULTS=%s\n' "$enable_value"
    } > "$temp_file"; then
        rm -f -- "$temp_file"
        fatal_error "Unable to write Base profile config '$profile_conf'."
    fi

    mv -f -- "$temp_file" "$profile_conf" || fatal_error "Unable to update Base profile config '$profile_conf'."
}

base_update_profile_subcommand_main() {
    local enable_defaults=0
    local disable_defaults=0
    local remove_sections=0
    local dry_run=0
    local base_home
    local backup_timestamp

    while (($#)); do
        case "$1" in
            --defaults)
                enable_defaults=1
                ;;
            --no-defaults)
                disable_defaults=1
                ;;
            --remove)
                remove_sections=1
                ;;
            --dry-run)
                dry_run=1
                ;;
            -h|--help|help)
                base_update_profile_subcommand_usage
                return 0
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            *)
                base_update_profile_usage_error "Unknown option '$1'."
                return $?
                ;;
        esac
        shift
    done

    if ((enable_defaults && disable_defaults)); then
        base_update_profile_usage_error "Options '--defaults' and '--no-defaults' cannot be used together."
        return $?
    fi
    if ((remove_sections && (enable_defaults || disable_defaults))); then
        base_update_profile_usage_error "Option '--remove' cannot be combined with '--defaults' or '--no-defaults'."
        return $?
    fi

    log_debug "Running 'basectl update-profile'."

    base_home="$(basectl_runtime_base_home)" || {
        print_error "${BASE_CLI_ERROR_MESSAGE:-Unable to find Base home.}"
        return 1
    }
    if [[ "${BASE_HOME:-}" != "$base_home" ]]; then
        print_error "Resolved Base home '$base_home' does not match runtime BASE_HOME '${BASE_HOME:-unset}'."
        printf "       This command must be invoked through the Base dispatcher, not directly.\n" >&2
        printf "       Fix: unset BASE_HOME and run 'basectl update-profile' through the installed 'basectl' binary.\n" >&2
        return 1
    fi
    export BASE_HOME

    base_update_profile_source_file_library || return 1
    backup_timestamp="$(setup_backup_timestamp)" || fatal_error "Unable to generate update-profile backup timestamp."

    if ((remove_sections)); then
        base_update_profile_remove_file "$HOME/.bash_profile" bash_profile "$dry_run" "$backup_timestamp" || return 1
        base_update_profile_remove_file "$HOME/.bashrc" bashrc "$dry_run" "$backup_timestamp" || return 1
        base_update_profile_remove_file "$HOME/.zprofile" zprofile "$dry_run" "$backup_timestamp" || return 1
        base_update_profile_remove_file "$HOME/.zshrc" zshrc "$dry_run" "$backup_timestamp" || return 1
        return 0
    fi

    base_update_profile_write_profile_conf "$enable_defaults" "$disable_defaults" "$dry_run" || return 1

    base_update_profile_update_file "$HOME/.bash_profile" bash_profile "$dry_run" "$backup_timestamp" || return 1
    base_update_profile_update_file "$HOME/.bashrc" bashrc "$dry_run" "$backup_timestamp" || return 1
    base_update_profile_update_file "$HOME/.zprofile" zprofile "$dry_run" "$backup_timestamp" || return 1
    base_update_profile_update_file "$HOME/.zshrc" zshrc "$dry_run" "$backup_timestamp" || return 1
}
