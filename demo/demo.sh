#!/usr/bin/env basectl
# shellcheck shell=bash

base_demo_script_dir() {
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P
}

base_demo_home() {
    if [[ -n "${BASE_HOME:-}" ]]; then
        cd -- "$BASE_HOME" && pwd -P
        return
    fi

    cd -- "$(base_demo_script_dir)/.." && pwd -P
}

if [[ -z "${BASE_HOME:-}" ]]; then
    BASE_HOME="$(base_demo_home)" || {
        printf 'ERROR: Unable to resolve Base home for demo.\n' >&2
        exit 1
    }
    export BASE_HOME
fi

# shellcheck source=/dev/null
source "$BASE_HOME/base_init.sh" || {
    printf 'ERROR: Unable to source Base initialization from %s.\n' "$BASE_HOME/base_init.sh" >&2
    exit 1
}

BASE_DEMO_BASECTL="${BASE_DEMO_BASECTL:-basectl}"
BASE_DEMO_BASE_WRAPPER="${BASE_DEMO_BASE_WRAPPER:-base-wrapper}"
BASE_DEMO_NON_INTERACTIVE=0

base_demo_usage() {
    cat <<'EOF'
Usage:
  demo/demo.sh [--non-interactive] [-h|--help]

Run Base's self-contained project workflow demo.
EOF
}

base_demo_parse_args() {
    while (($#)); do
        case "$1" in
            --non-interactive)
                BASE_DEMO_NON_INTERACTIVE=1
                ;;
            -h|--help|help)
                base_demo_usage
                return 2
                ;;
            *)
                printf 'ERROR: Unknown demo option %q\n' "$1" >&2
                base_demo_usage >&2
                return 1
                ;;
        esac
        shift
    done
}

base_demo_pause() {
    local tty_fd="${BASE_DEMO_TTY_FD:-}"
    local tty_path="${BASE_DEMO_TTY_PATH:-/dev/tty}"

    if [[ "$BASE_DEMO_NON_INTERACTIVE" == "1" ]]; then
        return 0
    fi
    if [[ -z "$tty_fd" && ! -r "$tty_path" ]]; then
        return 0
    fi

    printf '\nPress Enter to continue...'
    if [[ -n "$tty_fd" ]]; then
        [[ "$tty_fd" =~ ^[0-9]+$ ]] || return 0
        IFS= read -r -u "$tty_fd" _ || return 0
    else
        IFS= read -r _ < "$tty_path" || return 0
    fi
    printf '\n'
}

base_demo_step() {
    local number="$1"
    local title="$2"

    printf '\n== Step %s: %s ==\n\n' "$number" "$title"
}

base_demo_run() {
    printf '  $'
    printf ' %q' "$@"
    printf '\n'

    if ! "$@"; then
        printf '\nDemo step failed while running the command above.\n' >&2
        printf 'Run it manually with -v for more detail, then retry the demo.\n' >&2
        return 1
    fi
}

base_demo_capture() {
    local output

    printf '  $'
    printf ' %q' "$@"
    printf '\n'

    if ! output="$("$@" 2>&1)"; then
        printf '%s\n' "$output" >&2
        printf '\nDemo step failed while running the command above.\n' >&2
        printf 'Run it manually with -v for more detail, then retry the demo.\n' >&2
        return 1
    fi

    printf '%s\n' "$output"
}

base_demo_require_output() {
    local label="$1"
    local output="$2"
    local expected="$3"

    if [[ "$output" != *"$expected"* ]]; then
        printf 'ERROR: Expected %s output to contain %q.\n' "$label" "$expected" >&2
        return 1
    fi
}

base_demo_intro() {
    printf '\nBase Self-Demo\n\n'
    printf 'This walkthrough exercises the current Base project workflow using the Base repo itself.\n'
    printf 'It is intentionally local, inspectable, and safe to run repeatedly.\n'
    base_demo_pause
}

base_demo_runtime_step() {
    base_demo_step 1 "Runtime Contract"
    printf 'BASE_HOME=%s\n' "$BASE_HOME"
    printf 'BASE_PROJECT=%s\n' "${BASE_PROJECT:-base}"
    printf 'BASE_PROJECT_ROOT=%s\n' "${BASE_PROJECT_ROOT:-$BASE_HOME}"
    printf 'BASE_BASH_LIB_DIR=%s\n' "$BASE_BASH_LIB_DIR"
    base_demo_pause
}

base_demo_manifest_step() {
    base_demo_step 2 "Manifest Contract"
    printf 'Base declares its test and demo contracts in base_manifest.yaml.\n\n'
    base_demo_run grep -n "^demo:" "$BASE_HOME/base_manifest.yaml"
    base_demo_run grep -n "script: ./demo/demo.sh" "$BASE_HOME/base_manifest.yaml"
    base_demo_pause
}

base_demo_discovery_step() {
    local workspace_root
    local output

    base_demo_step 3 "Project Discovery"
    workspace_root="$(cd -- "$BASE_HOME/.." && pwd -P)" || return 1
    output="$(base_demo_capture "$BASE_DEMO_BASECTL" projects list --workspace "$workspace_root")"
    printf '%s\n' "$output"
    base_demo_require_output "project discovery" "$output" "base"
    base_demo_pause
}

base_demo_health_step() {
    base_demo_step 4 "Check And Doctor"
    base_demo_run "$BASE_DEMO_BASECTL" check base
    base_demo_run "$BASE_DEMO_BASECTL" doctor base
    base_demo_pause
}

base_demo_wrapper_step() {
    base_demo_step 5 "Base Wrapper"
    base_demo_run "$BASE_DEMO_BASE_WRAPPER" --project base base_projects resolve base
    base_demo_pause
}

base_demo_delegation_step() {
    base_demo_step 6 "Run And Test Delegation"
    base_demo_run "$BASE_DEMO_BASECTL" run base test --dry-run
    base_demo_run "$BASE_DEMO_BASECTL" test base --dry-run
    base_demo_pause
}

main() {
    base_demo_parse_args "$@" || {
        local status=$?
        [[ "$status" -eq 2 ]] && return 0
        return "$status"
    }

    base_demo_intro
    base_demo_runtime_step
    base_demo_manifest_step
    base_demo_discovery_step
    base_demo_health_step
    base_demo_wrapper_step
    base_demo_delegation_step

    printf '\nBase self-demo complete.\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
