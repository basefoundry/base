#!/usr/bin/env bash

[[ -n "${_base_ci_subcommand_sourced:-}" ]] && return 0
_base_ci_subcommand_sourced=1
readonly _base_ci_subcommand_sourced

_base_ci_subcommand_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

base_ci_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl ci setup [project] [options]
  basectl ci check [project] [options]
  basectl ci doctor [project] [options]

Options:
  Target command options are passed through unchanged after --ci is added.
  Run `basectl setup --help`, `basectl check --help`, or
  `basectl doctor --help` for the canonical option list.
  -h, --help  Show this help text.

Purpose:
  Compatibility alias for setup/check/doctor --ci.
  Prefer: basectl <setup|check|doctor> --ci [project] [options]
  Sets BASE_CI=true so setup and diagnostic paths can choose CI-safe behavior.
  Does not run project tests, launch GitHub Actions, or create Ubuntu/Multipass VMs.
EOF
}

base_ci_usage_error() {
    print_error "$*"
    base_ci_subcommand_usage >&2
    return 2
}

base_ci_source_subcommand_module() {
    local module_name="$1"
    local subcommand_script="$_base_ci_subcommand_dir/${module_name}.sh"

    [[ -f "$subcommand_script" ]] || {
        print_error "Subcommand module '$subcommand_script' was not found."
        return 1
    }

    # shellcheck source=/dev/null
    source "$subcommand_script"
}

base_ci_delegate() {
    local command="$1"
    shift

    base_ci_source_subcommand_module "$command" || return 1
    case "$command" in
        setup)
            base_setup_subcommand_main --ci "$@"
            ;;
        check)
            base_check_subcommand_main --ci "$@"
            ;;
        doctor)
            base_doctor_subcommand_main --ci "$@"
            ;;
    esac
}

base_ci_subcommand_main() {
    local command="${1:-}"

    case "$command" in
        -h|--help|help)
            base_ci_subcommand_usage
            return 0
            ;;
        "")
            base_ci_usage_error "CI command is required."
            return $?
            ;;
        setup|check|doctor)
            shift
            base_ci_delegate "$command" "$@"
            return $?
            ;;
        *)
            base_ci_usage_error "Unknown ci command '$command'."
            return $?
            ;;
    esac
}
