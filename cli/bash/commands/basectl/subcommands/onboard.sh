#!/usr/bin/env bash

[[ -n "${_base_onboard_subcommand_sourced:-}" ]] && return
_base_onboard_subcommand_sourced=1
readonly _base_onboard_subcommand_sourced

base_onboard_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl onboard [options]

Options:
  --dev         Include Base developer prerequisites.
  --dry-run     Explain planned onboarding steps without making changes.
  --yes         Accept default answers for setup and shell profile prompts.
  --no-profile  Skip shell profile updates.
  -v            Enable DEBUG logging for underlying commands.
  -h, --help    Show this help text.

Purpose:
  Guide a user through the first Base setup by orchestrating check, setup,
  update-profile, doctor, and project discovery commands.
EOF
}

base_onboard_print_heading() {
    printf '\n%s\n' "$1"
    printf '%s\n' "----------------"
}

base_onboard_command_text() {
    printf 'basectl'
    printf ' %q' "$@"
    printf '\n'
}

base_onboard_run_command() {
    "$BASE_HOME/bin/basectl" "$@"
}

base_onboard_prompt() {
    local prompt="$1"
    local answer

    printf '%s [y/N] ' "$prompt"
    if ! IFS= read -r answer; then
        printf '\n'
        return 1
    fi

    case "$answer" in
        y|Y|yes|YES|Yes)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

base_onboard_confirm() {
    local yes="$1"
    local prompt="$2"

    if ((yes)); then
        printf '%s [yes]\n' "$prompt"
        return 0
    fi

    base_onboard_prompt "$prompt"
}

base_onboard_print_next() {
    printf 'Next: '
    base_onboard_command_text "$@"
}

base_onboard_execute() {
    local dry_run="$1"
    shift

    if ((dry_run)); then
        printf '[DRY-RUN] Would run '
        base_onboard_command_text "$@"
        return 0
    fi

    base_onboard_print_next "$@"
    base_onboard_run_command "$@"
}

base_onboard_subcommand_main() {
    local dev=0
    local dry_run=0
    local no_profile=0
    local verbose=0
    local yes=0
    local check_status=0
    local profile_status=0
    local setup_status=0
    local check_args=(check base)
    local doctor_args=(doctor base)
    local setup_args=(setup base)
    local profile_args=(update-profile)
    local projects_args=(projects list)

    while (($#)); do
        case "$1" in
            --dev)
                dev=1
                ;;
            --dry-run)
                dry_run=1
                ;;
            --yes)
                yes=1
                ;;
            --no-profile)
                no_profile=1
                ;;
            -v)
                verbose=1
                ;;
            -h|--help|help)
                base_onboard_subcommand_usage
                return 0
                ;;
            *)
                print_error "Unknown option '$1'."
                base_onboard_subcommand_usage >&2
                return 1
                ;;
        esac
        shift
    done

    if ((dev)); then
        check_args+=(--dev)
        setup_args+=(--dev)
        doctor_args+=(--dev)
    fi
    if ((verbose)); then
        check_args+=(-v)
        setup_args+=(-v)
        doctor_args+=(-v)
        profile_args+=(-v)
        projects_args+=(-v)
    fi
    if ((dry_run)); then
        setup_args+=(--dry-run)
        profile_args+=(--dry-run)
    fi

    printf '%s\n' "Base onboard will verify project 'base' and guide the setup steps it can reconcile."

    base_onboard_print_heading "Check"
    printf '%s\n' "Base will check the current machine state before making changes."
    if ((dry_run)); then
        base_onboard_execute "$dry_run" "${check_args[@]}" || return $?
    else
        base_onboard_print_next "${check_args[@]}"
        base_onboard_run_command "${check_args[@]}"
        check_status=$?
        if ((check_status != 0)); then
            printf '%s\n' "Some checks did not pass. Setup can reconcile missing Base prerequisites."
        fi
    fi

    base_onboard_print_heading "Setup"
    printf '%s\n' "This installs or verifies Homebrew, Xcode Command Line Tools, Base Python, and Base-managed artifacts."
    if ((dry_run)); then
        base_onboard_execute "$dry_run" "${setup_args[@]}" || return $?
    elif base_onboard_confirm "$yes" "Proceed with setup?"; then
        base_onboard_print_next "${setup_args[@]}"
        base_onboard_run_command "${setup_args[@]}"
        setup_status=$?
        if ((setup_status != 0)); then
            printf '%s\n' "Setup failed. Running doctor can show the remaining issues."
            base_onboard_print_next "${doctor_args[@]}"
            base_onboard_run_command "${doctor_args[@]}" || true
            return "$setup_status"
        fi
    else
        printf '%s\n' "Setup skipped."
        return 0
    fi

    base_onboard_print_heading "Shell Profile"
    if ((no_profile)); then
        printf '%s\n' "Shell profile updates skipped because --no-profile was set."
    elif ((dry_run)); then
        base_onboard_execute "$dry_run" "${profile_args[@]}" || return $?
    elif base_onboard_confirm "$yes" "Update shell startup files for Base?"; then
        base_onboard_print_next "${profile_args[@]}"
        base_onboard_run_command "${profile_args[@]}"
        profile_status=$?
        if ((profile_status != 0)); then
            printf '%s\n' "Shell profile update failed. You can retry with 'basectl update-profile'."
            return "$profile_status"
        fi
    else
        printf '%s\n' "Shell profile update skipped. You can run 'basectl update-profile' later."
    fi

    base_onboard_print_heading "Doctor"
    base_onboard_execute "$dry_run" "${doctor_args[@]}" || return $?

    base_onboard_print_heading "Projects"
    if ((dry_run)); then
        base_onboard_execute "$dry_run" "${projects_args[@]}" || return $?
    else
        base_onboard_print_next "${projects_args[@]}"
        base_onboard_run_command "${projects_args[@]}" || printf '%s\n' "Project discovery is not available yet."
    fi

    base_onboard_print_heading "Next Steps"
    printf '%s\n' "Run 'basectl' to enter the nearest Base project shell, or 'basectl activate base' to start with Base itself."
}
