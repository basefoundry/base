# shellcheck shell=bash
#
# lib_file.sh - Bash library of generic file manipulation functions.
#

[[ -n "${__lib_file_sourced__:-}" ]] && return 0
readonly __lib_file_sourced__=1

#
# update_file_section - Idempotently manages a block of text within a file,
#                       demarcated by start and end markers.
#
# This function can add, update, or remove a section of text in a file.
# It is designed to be safe to run multiple times. If the section already
# exists, it will be replaced. If it doesn't exist, it will be appended.
#
# Usage:
#   update_file_section [options] <target_file> <start_marker> <end_marker> [content_lines...]
#
# Options:
#   -r : Remove the section defined by the markers instead of adding/updating it.
#
# Arguments:
#   target_file:    The path to the file to be modified.
#   start_marker:   The exact string that marks the beginning of the section.
#   end_marker:     The exact string that marks the end of the section.
#   content_lines:  (Optional) One or more strings, each representing a line of
#                   content to be placed inside the section.
#
# Examples:
#
#   # Add/update a section in .bash_profile
#   local commands=("export FOO=bar" "alias myalias='echo hello'")
#   update_file_section ~/.bash_profile "# START" "# END" "${commands[@]}"
#
#   # Remove the same section
#   update_file_section -r ~/.bash_profile "# START" "# END"
#
update_file_section() {
    local remove_section=false
    local new_content_array=()

    if [[ "$1" == "-r" ]]; then
        remove_section=true
        shift # consume -r
    fi

    if [[ $# -lt 3 ]]; then
        log_error "Insufficient arguments."
        if [[ "$remove_section" == true ]]; then
            log_info "Usage: update_file_section -r <target_file> <beginning_marker> <end_marker>"
        else
            log_info "Usage: update_file_section <target_file> <beginning_marker> <end_marker> [new_lines...]"
        fi
        return 1
    fi

    local target_file="$1" beginning_marker="$2" end_marker="$3"
    shift 3 # consume target_file, beginning_marker, end_marker
    if [[ "$remove_section" == true ]]; then
        if [[ $# -gt 0 ]]; then
            log_error "When -r flag is used, no content arguments should be provided."
            log_info "Usage: update_file_section -r <target_file> <beginning_marker> <end_marker>"
            return 1
        fi
    else
        new_content_array=("$@") # Capture remaining arguments as new_lines
    fi

    if [[ ! -f "$target_file" ]]; then
        log_debug "Target file '$target_file' does not exist."
        return 0
    fi

    log_info "Updating '$target_file'"
    local new_content_string=""
    if [[ "$remove_section" == false ]]; then
        if [[ ${#new_content_array[@]} -gt 0 ]]; then
            # Use printf to join array elements with newlines, adding a final newline.
            # This ensures proper multi-line insertion.
            printf -v new_content_string '%s\n' "${new_content_array[@]}"
        fi
    fi

    local temp_file
    temp_file=$(mktemp "${target_file}.XXXXXX")
    if [[ ! -f "$temp_file" ]]; then
        log_error "Failed to create temporary file for '$target_file'."
        return 1
    fi

    if grep -qF -- "$beginning_marker" "$target_file" && grep -qF -- "$end_marker" "$target_file"; then
        if [[ "$remove_section" == true ]]; then
            if awk -v START_M="$beginning_marker" -v END_M="$end_marker" '
            BEGIN { in_section = 0 }
            $0 == START_M { in_section = 1; next }
            $0 == END_M   { in_section = 0; next }
            {
                if (in_section == 0) {
                    print $0
                }
            }
            ' "$target_file" > "$temp_file" && mv -f "$temp_file" "$target_file"; then
                return 0
            fi
        else
            # FIX: This awk script now correctly handles multiple sections. It only replaces the first one.
            export AWK_NEW_TEXT="$new_content_string"
            if awk -v START_M="$beginning_marker" -v END_M="$end_marker" '
            BEGIN {
                processed = 0 # 0 = not yet processed, 1 = processing, 2 = done
            }
            $0 == START_M && processed == 0 {
                print START_M
                printf "%s", ENVIRON["AWK_NEW_TEXT"] # Insert new content
                processed = 1 # We are now inside the section to be replaced
                next
            }
            $0 == END_M && processed == 1 {
                print END_M
                processed = 2 # We are done with the replacement
                next
            }
            processed != 1 { # Print the line if we are not inside the section being replaced
                print $0
            }
            ' "$target_file" > "$temp_file" && mv -f "$temp_file" "$target_file"; then
                unset AWK_NEW_TEXT
                return 0
            fi
            unset AWK_NEW_TEXT
        fi

        log_error "Failed to process sections in '$target_file'."
        rm -f "$temp_file"
        return 1
    else
        # Markers not found in the file
        if [[ "$remove_section" == true ]]; then
            rm -f "$temp_file"
            return 0
        else
            cp "$target_file" "$temp_file"

            if [[ $(tail -c 1 "$temp_file" 2>/dev/null | wc -l) -eq 0 ]]; then
                printf '\n' >> "$temp_file"
            fi

            if {
                printf '%s\n' "$beginning_marker"
                printf '%s' "$new_content_string"
                printf '%s\n' "$end_marker"
            } >> "$temp_file" && mv -f "$temp_file" "$target_file"; then
                return 0
            fi

            log_error "Failed to add new section to '$target_file'."
            rm -f "$temp_file"
            return 1
        fi
    fi
}
