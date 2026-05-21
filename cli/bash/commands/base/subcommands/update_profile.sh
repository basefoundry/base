#!/usr/bin/env bash

[[ -n "${_base_update_profile_subcommand_sourced:-}" ]] && return
_base_update_profile_subcommand_sourced=1
readonly _base_update_profile_subcommand_sourced

_base_setup_common_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/setup_common.sh"
# shellcheck source=/dev/null
source "$_base_setup_common_path"

base_update_profile_subcommand_usage() {
    cat <<'EOF'
Usage:
  base update-profile [options]

Options:
  --defaults  Enable Base's optional Bash/Zsh shell defaults in managed rc sections.
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Purpose:
  Create or update Base-managed sections in Bash and Zsh startup files.

Updated files:
  ~/.bash_profile
  ~/.bashrc
  ~/.zprofile
  ~/.zshrc
EOF
}

base_update_profile_source_file_library() {
    local file_lib="${BASE_BASH_LIB_DIR:-$BASE_REPO_ROOT/lib/bash}/file/lib_file.sh"

    [[ -f "$file_lib" ]] || {
        print_error "File library '$file_lib' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$file_lib"
}

base_update_profile_quote() {
    local value="$1"
    printf '%q\n' "$value"
}

base_update_profile_section_lines() {
    local snippet_name="$1"
    local enable_defaults="$2"
    local quoted_base_home

    quoted_base_home="$(base_update_profile_quote "$BASE_HOME")" || return 1

    printf '%s\n' "# Managed by Base. Run 'base update-profile' to refresh this section."
    printf 'export BASE_HOME=%s\n' "$quoted_base_home"

    case "$snippet_name:$enable_defaults" in
        bashrc:1|zshrc:1)
            printf '%s\n' 'export BASE_ENABLE_SHELL_DEFAULTS=true'
            ;;
    esac

    printf '%s\n' '# shellcheck source=/dev/null'
    printf 'source "$BASE_HOME/lib/shell/%s"\n' "$snippet_name"
}

base_update_profile_update_file() {
    local target_file="$1"
    local snippet_name="$2"
    local enable_defaults="$3"
    local start_marker="# >>> base ${snippet_name} >>>"
    local end_marker="# <<< base ${snippet_name} <<<"
    local lines=()

    safe_touch "$target_file"

    mapfile -t lines < <(base_update_profile_section_lines "$snippet_name" "$enable_defaults") || return 1
    update_file_section "$target_file" "$start_marker" "$end_marker" "${lines[@]}"
}

base_update_profile_subcommand_main() {
    local enable_defaults=0
    local repo_root

    while (($#)); do
        case "$1" in
            --defaults)
                enable_defaults=1
                ;;
            -h|--help|help)
                base_update_profile_subcommand_usage
                return 0
                ;;
            -v)
                setup_enable_debug_logging
                ;;
            *)
                print_error "Unknown option '$1'."
                base_update_profile_subcommand_usage >&2
                return 1
                ;;
        esac
        shift
    done

    log_debug "Running 'base update-profile'."

    repo_root="$(base_cli_runtime_repo_root)" || {
        print_error "${BASE_CLI_ERROR_MESSAGE:-Unable to find the Base repository root.}"
        return 1
    }
    BASE_HOME="$repo_root"
    export BASE_HOME

    base_update_profile_source_file_library || return 1

    base_update_profile_update_file "$HOME/.bash_profile" bash_profile 0 || return 1
    base_update_profile_update_file "$HOME/.bashrc" bashrc "$enable_defaults" || return 1
    base_update_profile_update_file "$HOME/.zprofile" zprofile 0 || return 1
    base_update_profile_update_file "$HOME/.zshrc" zshrc "$enable_defaults" || return 1

    print_success "Updated Base-managed shell startup sections."
}
