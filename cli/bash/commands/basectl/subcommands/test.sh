#!/usr/bin/env bash

[[ -n "${_base_test_subcommand_sourced:-}" ]] && return 0
_base_test_subcommand_sourced=1
readonly _base_test_subcommand_sourced

_base_project_command_helpers_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/project_command_helpers.sh"
# shellcheck source=/dev/null
source "$_base_project_command_helpers_path"

import_base_lib arg/lib_arg.sh

base_test_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl test [project] [options] [-- extra args...]

Options:
  --workspace <path>  Workspace directory to scan. Defaults to workspace.root, then BASE_HOME's parent.
  --project <name>    Select a project explicitly instead of the positional or nearest project.
  --dry-run           Print the resolved test command without running it.
  -v                  Enable DEBUG logging for this subcommand.
  -h, --help          Show this help text.

Run a project's declared test command from its project root.
Use -- to pass additional arguments to the declared test command.
EOF
}

base_test_usage_error() {
    base_test_subcommand_usage >&2
    base_std_print_error "$*"
    return 2
}

base_test_subcommand_main() {
    local project="" resolve_output resolved_name project_root manifest_path test_command command_runner
    local command_to_run display_command dry_run
    local args=() extra_args=()
    local route_venv_dir uses_uv_manager trust_required

    base_project_command_parse_args \
        test base_test_subcommand_usage base_test_usage_error \
        "The 'test' command accepts exactly one project name." "$@" || return $?
    [[ "$BASE_PROJECT_COMMAND_HELP_SHOWN" == 1 ]] && return 0
    project="$BASE_PROJECT_COMMAND_PROJECT"
    dry_run="$BASE_PROJECT_COMMAND_DRY_RUN"
    args=("${BASE_PROJECT_COMMAND_ARGUMENTS[@]}")
    extra_args=("${BASE_PROJECT_COMMAND_EXTRA_ARGS[@]}")

    base_project_command_resolve_context \
        test-command project-command command "test command" "$project" || return $?
    resolved_name="$BASE_PROJECT_COMMAND_RESOLVED_NAME"
    project_root="$BASE_PROJECT_COMMAND_RESOLVED_ROOT"
    manifest_path="$BASE_PROJECT_COMMAND_RESOLVED_MANIFEST"
    route_venv_dir="$BASE_PROJECT_COMMAND_ROUTE_VENV"
    uses_uv_manager="$BASE_PROJECT_COMMAND_USES_UV"
    trust_required="$BASE_PROJECT_COMMAND_TRUST_REQUIRED"
    test_command="$BASE_PROJECT_COMMAND_RESOLVED_ACTION"
    command_runner="$BASE_PROJECT_COMMAND_RUNNER"

    command_runner="${command_runner:-}"
    command_to_run="$(base_command_with_runner "$command_runner" "$test_command" "${extra_args[@]}")" || return $?
    display_command="$(base_display_command_with_runner "$command_runner" "$test_command" "${extra_args[@]}")" || return $?

    if [[ "$dry_run" == "1" ]]; then
        printf '[DRY-RUN] Would run tests for project %q in %q: %s\n' "$resolved_name" "$project_root" "$display_command"
        return 0
    fi

    base_project_require_manifest_command_trust "$resolved_name" "$manifest_path" "$trust_required" || return $?
    base_project_require_wrapper || return $?
    resolve_output="$("$BASE_PROJECT_COMMAND_WRAPPER" --project base base_projects test-command \
        "${BASE_PROJECT_COMMAND_SELECTION_ARGS[@]}" "${args[@]}" \
        --format command-protocol --test-preflight)" || return $?
    base_command_protocol_decode_one project-command "$resolve_output" || {
        base_std_fatal_error "Unable to resolve test command for project '$project'."
    }
    test_command="${BASE_COMMAND_PROTOCOL_FIELDS[command]}"
    command_runner="${BASE_COMMAND_PROTOCOL_FIELDS[runner]}"
    command_runner="${command_runner:-}"
    command_to_run="$(base_command_with_runner "$command_runner" "$test_command" "${extra_args[@]}")" || return $?

    base_project_activate_environment \
        "$resolved_name" "$project_root" "$manifest_path" "$dry_run" "$route_venv_dir" "$uses_uv_manager" >/dev/null

    base_std_log_info "Running tests for project '$resolved_name': $display_command"
    base_validate_command_runner "$command_runner"
    base_project_run_shell_command "$project_root" "$command_to_run" basectl-test "${extra_args[@]}"
}
