#!/usr/bin/env bash

[[ -n "${_base_repo_clone_sourced:-}" ]] && return 0
_base_repo_clone_sourced=1
readonly _base_repo_clone_sourced

base_repo_clone_check_destination() {
    local actual_repo=""
    local expected_repo="$1"
    local target="$2"

    [[ -e "$target" ]] || return 0

    if [[ ! -d "$target" ]]; then
        base_std_log_error "Destination '$target' already exists but is not a matching Git checkout."
        return 1
    fi

    actual_repo="$(base_repo_infer_github_repo "$target" || true)"
    if [[ "$actual_repo" == "$expected_repo" ]]; then
        printf "Repository '%s' already exists at '%s'.\n" "$expected_repo" "$target"
        printf "To update: git -C %s pull --ff-only\n" "$(base_repo_pretty_arg "$target")"
        return 2
    fi

    if [[ -n "$actual_repo" ]]; then
        base_std_log_error "Destination '$target' already points at GitHub repository '$actual_repo'."
        base_std_log_error "Expected '$expected_repo'."
        return 1
    fi

    base_std_log_error "Destination '$target' already exists but is not a matching Git checkout."
    return 1
}

base_repo_clone_with_gh() {
    local clone_url="$4"
    local dry_run="$1"
    local gh_path
    local parent
    local repo="$2"
    local status
    local target="$3"

    base_repo_clone_check_destination "$repo" "$target"
    status=$?
    case "$status" in
        0)
            ;;
        2)
            return 0
            ;;
        *)
            return 1
            ;;
    esac

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would clone %s (%s) into %s.\n" \
            "$repo" \
            "$clone_url" \
            "$(base_repo_pretty_arg "$target")"
        printf "[DRY-RUN] Would run: "
        base_repo_pretty_command gh repo clone "$repo" "$target"
        printf "\n"
        return 0
    fi

    base_std_command_path gh_path gh && [[ -n "$gh_path" ]] || {
        base_std_log_error "GitHub CLI 'gh' is required for repository clone."
        return 1
    }

    parent="$(dirname -- "$target")"
    base_repo_create_directory "$parent" || return 1
    printf "Cloning GitHub repository '%s' into '%s'.\n" "$repo" "$target"
    gh repo clone "$repo" "$target" || {
        base_std_log_error "Failed to clone GitHub repository '$repo' into '$target'."
        return 1
    }
    printf "Cloned '%s' to '%s'.\n" "$repo" "$target"
    if [[ -f "$target/base_manifest.yaml" ]]; then
        printf "Run 'basectl repo check %s' to verify the Base baseline.\n" \
            "$(base_repo_pretty_arg "$target")"
    fi
}

base_repo_clone() {
    local clone_url
    local dry_run=0
    local github_repo
    local name=""
    local owner=""
    local path=""
    local protocol
    local spec=""
    local status
    local target
    local -a parser_args=() positionals=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "owner|value|--owner"
        "path|value|--path"
        "dry_run|flag|--dry-run"
        "verbose|flag|-v"
    )
    local -A parsed_options=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_clone_usage
                return 0
                ;;
            --owner)
                [[ -n "${2:-}" ]] || {
                    base_repo_clone_usage_error "Option '--owner' requires an argument."
                    return $?
                }
                parser_args+=("$1" "$2")
                shift 2
                ;;
            --owner=*)
                parser_args+=("$1")
                shift
                ;;
            --path)
                [[ -n "${2:-}" ]] || {
                    base_repo_clone_usage_error "Option '--path' requires an argument."
                    return $?
                }
                parser_args+=("$1" "$2")
                shift 2
                ;;
            --path=*)
                parser_args+=("$1")
                shift
                ;;
            --dry-run)
                parser_args+=("$1")
                shift
                ;;
            -v)
                parser_args+=("$1")
                shift
                ;;
            -*)
                base_repo_clone_usage_error "Unknown repo clone option '$1'."
                return $?
                ;;
            *)
                parser_args+=("$1")
                shift
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_repo_clone_usage_error "Could not parse repo clone arguments."
        return $?
    fi
    if ((${#positionals[@]} == 0)); then
        base_repo_clone_usage_error "Repository name is required."
        return $?
    fi
    if ((${#positionals[@]} > 1)); then
        base_repo_clone_usage_error "The 'repo clone' command accepts exactly one repository name."
        return $?
    fi

    spec="${positionals[0]}"
    owner="${parsed_options[owner]:-}"
    path="${parsed_options[path]:-}"
    dry_run="${parsed_options[dry_run]:-0}"
    if [[ "${parsed_options[verbose]:-0}" == "1" ]]; then
        base_std_set_log_level DEBUG
        export BASE_BASH_LIBS_LOG_DEBUG=1
    fi

    if [[ "$spec" == */* ]]; then
        [[ "$spec" != */*/* ]] || {
            base_repo_clone_usage_error "Repository must be '<name>' or '<owner>/<name>'."
            return $?
        }
        [[ -z "$owner" ]] || {
            base_repo_clone_usage_error "Option '--owner' cannot be used with '<owner>/<name>'."
            return $?
        }
        owner="${spec%%/*}"
        name="${spec#*/}"
    else
        name="$spec"
        if [[ -z "$owner" ]]; then
            owner="$(base_repo_default_github_owner)"
            status=$?
            case "$status" in
                0)
                    ;;
                1)
                    base_repo_clone_usage_error "Repository owner is required for short repo names. Pass --owner <owner> or set github.default_owner in ~/.base.d/config.yaml."
                    return $?
                    ;;
                *)
                    return "$status"
                    ;;
            esac
        fi
    fi

    base_repo_validate_owner "$owner" || return 2
    base_repo_validate_name "$name" || return 2
    github_repo="$owner/$name"
    protocol="$(base_repo_clone_protocol)" || return $?
    clone_url="$(base_repo_clone_url "$protocol" "$github_repo")" || return 1

    if [[ -z "$path" ]]; then
        path="$(base_repo_default_target_path "$name")" || return $?
    else
        path="$(base_repo_expand_path "$path")"
    fi
    target="$(base_repo_target_path "$path")"

    base_repo_clone_with_gh "$dry_run" "$github_repo" "$target" "$clone_url"
}
