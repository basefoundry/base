#!/usr/bin/env bash

[[ -n "${_base_prompt_subcommand_sourced:-}" ]] && return 0
_base_prompt_subcommand_sourced=1
readonly _base_prompt_subcommand_sourced

base_prompt_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl prompt list
  basectl prompt <name>

Prompts:
  product-self-review  Periodic Base product self-review

Options:
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.

Print repo-owned Markdown prompts for AI-assisted Base workflows. Base renders
the prompt; an AI tool performs the review.
EOF
}

base_prompt_usage_error() {
    base_prompt_subcommand_usage >&2
    print_error "$*"
    return 2
}

base_prompt_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local debug=0
    local prompt_args=()
    local renderer_args=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_prompt_subcommand_usage
                return 0
                ;;
            -v)
                debug=1
                shift
                ;;
            -*)
                base_prompt_usage_error "Unknown prompt option '$1'."
                return $?
                ;;
            *)
                prompt_args+=("$1")
                shift
                ;;
        esac
    done

    if ((${#prompt_args[@]} == 0)); then
        base_prompt_usage_error "The 'prompt' command requires 'list' or a prompt name."
        return $?
    fi
    if ((${#prompt_args[@]} > 1)); then
        base_prompt_usage_error "The 'prompt' command accepts exactly one argument."
        return $?
    fi

    ((debug)) && renderer_args+=(--debug)

    [[ -x "$wrapper" ]] || fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    BASE_CLI_DISPLAY_COMMAND="basectl prompt" "$wrapper" --project base base_prompt "${renderer_args[@]}" "${prompt_args[@]}"
}
