# shellcheck shell=bash
# Version inspection deliberately runs before provider-dependent bootstrap.

basectl_version_usage() {
    cat <<'USAGE'
Usage:
  basectl version [--all [--json]]

Purpose:
  Show the installed Base version. Use --all to inspect selected component providers.

Options:
  --all         Show Base, base-cli, and base-bash-libs identity and source paths.
  --json        Emit a versioned JSON report (requires --all).
  -h, --help    Show this help text.

Detailed inspection requires Python 3, but does not require working providers.
Unavailable providers are reported without suppressing other components.
USAGE
}

basectl_version_usage_error() {
    printf 'ERROR: %s\n' "$*" >&2
    printf "Run 'basectl version --help' for usage.\n" >&2
    return 2
}

basectl_version_all() (
    # Subshell: runtime selection must not mutate a caller's loaded contract.
    local base_home="$1" output_format="$2"
    local cli_root cli_kind cli_error="" bash_error="" python_bin selected_python
    local base_version candidate
    BASE_HOME="$base_home"
    # shellcheck source=lib/base/base_cli_runtime.sh
    source "$base_home/lib/base/base_cli_runtime.sh" || return 1
    # shellcheck source=lib/base/base_bash_libs_runtime.sh
    source "$base_home/lib/base/base_bash_libs_runtime.sh" || return 1
    base_init_error() { printf 'ERROR: %s\n' "$*" >&2; }

    cli_root="$(base_cli_runtime_source_root 2>&1)" || { cli_error="$cli_root"; cli_root=""; }
    cli_kind="$(base_cli_runtime_source_kind)" || cli_kind=unavailable
    # Capture errors without a temporary file; resolve in this subshell after success.
    bash_error="$(base_init_set_bash_libs_contract 2>&1)"
    if [[ -z "$bash_error" ]]; then
        base_init_set_bash_libs_contract || return 1
    fi
    selected_python="${BASE_SETUP_VENV_DIR:-$HOME/.base.d/base/.venv}/bin/python"
    python_bin=""
    for candidate in "$selected_python" "$(command -v python3 || true)" /usr/bin/python3; do
        if [[ -x "$candidate" ]] && "$candidate" -I -S -c 'import importlib.metadata' >/dev/null 2>&1; then
            python_bin="$candidate"
            break
        fi
    done
    [[ -n "$python_bin" ]] || {
        printf 'ERROR: Detailed version inspection requires Python 3. Use basectl version for Base alone.\n' >&2
        return 1
    }
    base_version="$(base_read_version "$base_home")"
    # Bootstrap diagnostic exception: stdlib-only reporter must survive missing
    # venvs and incompatible providers, so it cannot use base-wrapper.
    "$python_bin" -I -S "$base_home/cli/python/base_version/report.py" \
        "$base_home" "$base_version" "$output_format" "$selected_python" \
        "$cli_kind" "$cli_root" "$cli_error" \
        "${BASE_BASH_LIBS_SOURCE:-unavailable}" "${BASE_BASH_LIBS_DIR:-}" "$bash_error"
)

basectl_version_main() {
    local base_home="$1" all=0 output_format=text arg
    shift
    if [[ "$#" -eq 1 && ( "$1" == -h || "$1" == --help || "$1" == help ) ]]; then
        basectl_version_usage
        return 0
    fi
    for arg in "$@"; do
        case "$arg" in
            --all) all=1 ;;
            --json) output_format=json ;;
            *) basectl_version_usage_error "Unknown version argument '$arg'."; return $? ;;
        esac
    done
    if [[ "$all" -eq 0 ]]; then
        [[ "$output_format" == text ]] || {
            basectl_version_usage_error '--json requires --all.'
            return $?
        }
        basectl_print_version "$base_home"
        return $?
    fi
    basectl_source_version_library "$base_home"
    basectl_version_all "$base_home" "$output_format"
}
