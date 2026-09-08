#!/usr/bin/env bash

[[ -n "${_base_prompt_subcommand_sourced:-}" ]] && return 0
_base_prompt_subcommand_sourced=1
readonly _base_prompt_subcommand_sourced

import_base_lib arg/lib_arg.sh

base_prompt_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl prompt list
  basectl prompt <name> [--output <path>]

Prompts:
  product-self-review  Periodic Base product self-review

Options:
  --output <path>  Write the rendered prompt Markdown to this path.
  -v               Enable DEBUG logging for this subcommand.
  -h, --help       Show this help text.

Print repo-owned Markdown prompts for AI-assisted Base workflows. Base renders
the prompt; an AI tool performs the review.
EOF
}

base_prompt_leaf_usage() {
    local prompt_name="$1"

    if [[ "$prompt_name" == list ]]; then
        cat <<'EOF'
Usage:
  basectl prompt list

Purpose:
  List the repo-owned Markdown prompts that Base can render.

Options:
  -v          Enable DEBUG logging for this subcommand.
  -h, --help  Show this help text.
EOF
        return 0
    fi

    cat <<EOF
Usage:
  basectl prompt $prompt_name [--output <path>]

Purpose:
  Render the repo-owned '$prompt_name' Markdown prompt.

Options:
  --output <path>  Write the rendered prompt Markdown to this path.
  -v               Enable DEBUG logging for this subcommand.
  -h, --help       Show this help text.
EOF
}

base_prompt_usage_error() {
    base_prompt_subcommand_usage >&2
    base_std_print_error "$*"
    return 2
}

base_prompt_subcommand_main() {
    local wrapper="$BASE_HOME/bin/base-wrapper"
    local output_path=""
    local prompt_args=() parse_args=()
    local renderer_args=()
    local output_args=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "debug|flag|-v"
        "output|value|--output"
    )
    local -a positionals=()
    local -A parsed_options=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                if ((${#prompt_args[@]})); then
                    base_prompt_leaf_usage "${prompt_args[0]}"
                else
                    base_prompt_subcommand_usage
                fi
                return $?
                ;;
            -v)
                parse_args+=("$1")
                shift
                ;;
            --output)
                shift
                if (($# == 0)); then
                    base_prompt_usage_error "Option '--output' requires a path."
                    return $?
                fi
                # The legacy parser accepts any following token as the path,
                # including one that looks like a recognized option. Encode
                # the value with equals syntax so base_arg_parse preserves
                # that contract instead of treating it as a missing value.
                parse_args+=("--output=$1")
                shift
                ;;
            -*)
                base_prompt_usage_error "Unknown prompt option '$1'."
                return $?
                ;;
            *)
                prompt_args+=("$1")
                parse_args+=("$1")
                shift
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parse_args[@]}"; then
        base_prompt_subcommand_usage >&2
        return 2
    fi

    if ((${#positionals[@]} == 0)); then
        base_prompt_usage_error "The 'prompt' command requires 'list' or a prompt name."
        return $?
    fi
    if ((${#positionals[@]} > 1)); then
        base_prompt_usage_error "The 'prompt' command accepts exactly one argument."
        return $?
    fi

    [[ "${parsed_options[debug]:-}" == "1" ]] && renderer_args+=(--debug)
    output_path="${parsed_options[output]:-}"
    [[ -z "$output_path" ]] || output_args+=(--output "$output_path")

    [[ -x "$wrapper" ]] || base_std_fatal_error "Base Python wrapper '$wrapper' is missing or is not executable."
    BASE_CLI_DISPLAY_COMMAND="basectl prompt" \
        "$wrapper" --project base base_prompt \
        "${renderer_args[@]}" "${positionals[@]}" "${output_args[@]}"
}
