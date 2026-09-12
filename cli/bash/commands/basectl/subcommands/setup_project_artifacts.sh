#!/usr/bin/env bash

[[ -n "${_base_setup_project_artifacts_sourced:-}" ]] && return 0
_base_setup_project_artifacts_sourced=1
readonly _base_setup_project_artifacts_sourced

setup_project_artifact_reset() {
    _BASE_SETUP_PROJECT_ARTIFACT_ACTION=""
    _BASE_SETUP_PROJECT_ARTIFACT_OUTPUT_FORMAT=""
    _BASE_SETUP_PROJECT_ARTIFACT_REQUESTED_PROJECT=""
    _BASE_SETUP_PROJECT_ARTIFACT_PROJECT=""
    _BASE_SETUP_PROJECT_ARTIFACT_PYTHON_BIN=""
    _BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT=""
    _BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH=""
    _BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR=""
    _BASE_SETUP_PROJECT_ARTIFACT_USES_UV_MANAGER=""
    _BASE_SETUP_PROJECT_ARTIFACT_REQUIRES_PYTHON=""
    _BASE_SETUP_PROJECT_ARTIFACT_REMOTE_NETWORK=false
    _BASE_SETUP_PROJECT_ARTIFACT_PLATFORM=""
    _BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE=0
    _BASE_SETUP_PROJECT_ARTIFACT_ARGS=()
    _BASE_SETUP_PROJECT_ARTIFACT_PROJECT_ENV_ARGS=()
}

setup_project_artifact_resolve_context() {
    local project resolved_root manifest_path route_output
    local requested_project="$_BASE_SETUP_PROJECT_ARTIFACT_REQUESTED_PROJECT"

    setup_ensure_cached_paths
    _BASE_SETUP_PROJECT_ARTIFACT_PYTHON_BIN="$(
        setup_base_venv_python_bin "$_BASE_SETUP_VENV_DIR_CACHE"
    )" || base_std_fatal_error "Base virtual environment Python was not found at '$_BASE_SETUP_VENV_DIR_CACHE/bin/python'. $(setup_recovery_venv)"
    setup_resolve_project_manifest "$requested_project" "$_BASE_SETUP_PROJECT_ARTIFACT_PYTHON_BIN" \
        project resolved_root manifest_path || {
        if [[ -z "$requested_project" && -n "${BASE_SETUP_MANIFEST:-}" ]]; then
            base_std_log_error "Unable to resolve a project from manifest '$BASE_SETUP_MANIFEST'."
        else
            base_std_log_error "Unable to resolve Base project '$requested_project'."
            base_std_log_error "Run 'basectl projects list' to see projects Base can discover."
        fi
        return 1
    }
    if [[ "$project" != base && "$_BASE_SETUP_PROJECT_ARTIFACT_OUTPUT_FORMAT" != json ]]; then
        if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == setup ]]; then
            base_std_log_info "Resolved project '$project' at '$resolved_root'."
        else
            base_std_log_debug "Resolved project '$project' at '$resolved_root'."
        fi
    fi
    route_output="$(setup_resolve_project_route "$project" "$manifest_path" \
        "$_BASE_SETUP_PROJECT_ARTIFACT_PYTHON_BIN")" || {
        base_std_log_error "Unable to resolve Base project environment for '$project'."
        return 1
    }
    base_command_protocol_decode_one project-setup-route "$route_output" || {
        base_std_log_error "Python project routing returned invalid metadata for '$project'."
        return 1
    }
    _BASE_SETUP_PROJECT_ARTIFACT_PROJECT="${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}"
    _BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT="${BASE_COMMAND_PROTOCOL_FIELDS[project_root]}"
    _BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH="${BASE_COMMAND_PROTOCOL_FIELDS[manifest_path]}"
    export BASE_CLI_HISTORY_PROJECT="$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT"
    export BASE_CLI_HISTORY_PROJECT_ROOT="$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT"
    export BASE_CLI_HISTORY_MANIFEST="$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH"
    _BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR="${BASE_COMMAND_PROTOCOL_FIELDS[project_venv_dir]}"
    _BASE_SETUP_PROJECT_ARTIFACT_USES_UV_MANAGER="${BASE_COMMAND_PROTOCOL_FIELDS[uses_uv_manager]}"
    _BASE_SETUP_PROJECT_ARTIFACT_REQUIRES_PYTHON="${BASE_COMMAND_PROTOCOL_FIELDS[requires_project_python]}"
    if [[ -z "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" ||
        -z "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" ||
        -z "$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH" ||
        -z "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR" ]]; then
        base_std_log_error "Python project routing returned incomplete metadata for '$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT'."
        return 1
    fi
    BASE_SETUP_PROJECT_NAME="$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT"
    export BASE_SETUP_PROJECT_NAME
    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_USES_UV_MANAGER" != true &&
        "$_BASE_SETUP_PROJECT_ARTIFACT_USES_UV_MANAGER" != false ]]; then
        base_std_log_error "Python project routing returned invalid uv-manager metadata for '$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT'."
        return 1
    fi
    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_REQUIRES_PYTHON" != true &&
        "$_BASE_SETUP_PROJECT_ARTIFACT_REQUIRES_PYTHON" != false ]]; then
        base_std_log_error "Python project routing returned invalid project-Python metadata for '$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT'."
        return 1
    fi
    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" == base ]]; then
        _BASE_SETUP_PROJECT_ARTIFACT_PROJECT_ENV_ARGS=(
            -u BASE_PROJECT
            -u BASE_PROJECT_ROOT
            -u BASE_PROJECT_MANIFEST
            -u BASE_PROJECT_VENV_DIR
        )
    fi
}

setup_project_artifact_build_command() {
    _BASE_SETUP_PROJECT_ARTIFACT_ARGS=()
    if setup_is_dry_run; then
        _BASE_SETUP_PROJECT_ARTIFACT_ARGS+=(--dry-run)
    fi
    _BASE_SETUP_PROJECT_ARTIFACT_ARGS+=(--manifest "$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH")
    _BASE_SETUP_PROJECT_ARTIFACT_ARGS+=(--action "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION")
    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == check ||
        "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == doctor ]]; then
        _BASE_SETUP_PROJECT_ARTIFACT_ARGS+=(--format "$_BASE_SETUP_PROJECT_ARTIFACT_OUTPUT_FORMAT")
    fi
    if [[ "${BASE_SETUP_REMOTE_NETWORK:-}" == true &&
        ( "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == check ||
        "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == doctor ) ]]; then
        _BASE_SETUP_PROJECT_ARTIFACT_ARGS+=(--remote-network)
        _BASE_SETUP_PROJECT_ARTIFACT_REMOTE_NETWORK=true
    fi
    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == setup ]] &&
        setup_project_ide_mutations_allowed; then
        _BASE_SETUP_PROJECT_ARTIFACT_ARGS+=(--allow-project-ide-mutations)
    fi
    _BASE_SETUP_PROJECT_ARTIFACT_ARGS+=("$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT")
    _BASE_SETUP_PROJECT_ARTIFACT_PLATFORM="$(setup_current_platform)" || return 1

    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_OUTPUT_FORMAT" != json ]]; then
        if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == setup ]]; then
            base_std_log_info "Running Python project $_BASE_SETUP_PROJECT_ARTIFACT_ACTION layer."
        else
            base_std_log_debug "Running Python project $_BASE_SETUP_PROJECT_ARTIFACT_ACTION layer."
        fi
    fi
}

setup_project_artifact_prepare_bootstrap() {
    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == setup &&
        "$_BASE_SETUP_PROJECT_ARTIFACT_REQUIRES_PYTHON" == true &&
        "$_BASE_SETUP_PROJECT_ARTIFACT_USES_UV_MANAGER" != true ]]; then
        setup_run_project_bootstrap_layer \
            "$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH" \
            "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
            "$_BASE_SETUP_PROJECT_ARTIFACT_OUTPUT_FORMAT" \
            "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
            "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR"
        _BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE=$?
        if ((_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE)); then
            base_std_log_error "$(setup_recovery_project_layer)"
            base_std_log_error "Python project $_BASE_SETUP_PROJECT_ARTIFACT_ACTION layer failed."
            return "$_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE"
        fi
    fi

    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == setup ]] &&
        setup_upgrade_pip_enabled &&
        [[ "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" != base ]]; then
        if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_USES_UV_MANAGER" == true ]]; then
            base_std_log_warn "Skipping pip upgrade for project '$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT': its virtual environment is managed by uv. Run 'uv sync' to reconcile the project environment."
        elif [[ "$_BASE_SETUP_PROJECT_ARTIFACT_REQUIRES_PYTHON" == true ]]; then
            setup_upgrade_project_pip \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR" || return $?
        else
            base_std_log_warn "Skipping pip upgrade for project '$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT': it does not declare a Python runtime."
        fi
    fi
}

setup_project_artifact_handle_unhealthy_venv() {
    local precheck_json

    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == setup ]] && setup_is_dry_run; then
        return 0
    fi
    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_REQUIRES_PYTHON" == true &&
        "$_BASE_SETUP_PROJECT_ARTIFACT_USES_UV_MANAGER" != true ]] &&
        ! setup_virtualenv_healthy_path "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR"; then
        if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_OUTPUT_FORMAT" == json ]]; then
            if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == doctor ]]; then
                precheck_json="$(setup_run_project_pre_venv_layer predoctor json \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_REMOTE_NETWORK")" || true
                [[ -n "$precheck_json" ]] || precheck_json="[]"
                setup_print_project_venv_doctor_json \
                    "$precheck_json" \
                    "error" \
                    "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
                    "$(setup_recovery_project_venv \
                        "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                        "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                        "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR")"
            else
                precheck_json="$(setup_run_project_pre_venv_layer precheck json \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_REMOTE_NETWORK")" || true
                [[ -n "$precheck_json" ]] || precheck_json="[]"
                setup_print_project_check_json_with_venv \
                    "$precheck_json" \
                    false \
                    "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
                    "$(setup_recovery_project_venv \
                        "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                        "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                        "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR")" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT"
            fi
        elif [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == doctor ]]; then
            setup_run_project_pre_venv_layer predoctor text \
                "$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_REMOTE_NETWORK" || true
            setup_print_doctor_finding \
                "error" \
                "BASE-P050" \
                "Project virtualenv" \
                "$_BASE_SETUP_VENV_HEALTH_MESSAGE" \
                "$(setup_recovery_project_venv \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                    "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR")"
        elif [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == check ]]; then
            setup_run_project_pre_venv_layer precheck text \
                "$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_REMOTE_NETWORK" || true
            base_std_log_error "$_BASE_SETUP_VENV_HEALTH_MESSAGE"
            base_std_log_error "$(setup_recovery_project_venv \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR")"
        else
            base_std_log_warn "$_BASE_SETUP_VENV_HEALTH_MESSAGE"
            base_std_log_warn "$(setup_recovery_project_venv \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
                "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR")"
        fi
        return 1
    fi
}

setup_project_artifact_execute() {
    if [[ "$_BASE_SETUP_PROJECT_ARTIFACT_USES_UV_MANAGER" == true ||
        "$_BASE_SETUP_PROJECT_ARTIFACT_REQUIRES_PYTHON" != true ]] ||
        { [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == setup ]] && setup_is_dry_run; }; then
        env "${_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_ENV_ARGS[@]}" \
            BASE_HOME="$BASE_HOME" \
            BASE_PLATFORM="$_BASE_SETUP_PROJECT_ARTIFACT_PLATFORM" \
            BASE_PROJECT="$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
            BASE_PROJECT_ROOT="$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
            BASE_PROJECT_MANIFEST="$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH" \
            BASE_PROJECT_VENV_DIR="$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR" \
            PYTHONPATH="$_BASE_SETUP_PYTHONPATH_CACHE" \
            "$_BASE_SETUP_PROJECT_ARTIFACT_PYTHON_BIN" -m base_setup "${_BASE_SETUP_PROJECT_ARTIFACT_ARGS[@]}"
    else
        env "${_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_ENV_ARGS[@]}" \
            BASE_PLATFORM="$_BASE_SETUP_PROJECT_ARTIFACT_PLATFORM" \
            BASE_PROJECT="$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" \
            BASE_PROJECT_ROOT="$_BASE_SETUP_PROJECT_ARTIFACT_RESOLVED_ROOT" \
            BASE_PROJECT_MANIFEST="$_BASE_SETUP_PROJECT_ARTIFACT_MANIFEST_PATH" \
            BASE_PROJECT_VENV_DIR="$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT_VENV_DIR" \
            "$BASE_HOME/bin/base-wrapper" --project "$_BASE_SETUP_PROJECT_ARTIFACT_PROJECT" base_setup "${_BASE_SETUP_PROJECT_ARTIFACT_ARGS[@]}"
    fi
    _BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE=$?
    return "$_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE"
}

setup_run_project_artifact_layer() {
    setup_project_artifact_reset
    _BASE_SETUP_PROJECT_ARTIFACT_ACTION="$1"
    _BASE_SETUP_PROJECT_ARTIFACT_OUTPUT_FORMAT="$2"
    _BASE_SETUP_PROJECT_ARTIFACT_REQUESTED_PROJECT="${BASE_SETUP_PROJECT_NAME:-}"

    if setup_is_dry_run && ! setup_base_python_package_installed "$(setup_pyyaml_package)"; then
        base_std_log_info "[DRY-RUN] Would run Python project setup layer after PyYAML is installed."
        return 0
    fi
    setup_project_artifact_resolve_context || return $?
    setup_project_artifact_build_command || return $?
    setup_project_artifact_prepare_bootstrap || return $?
    setup_project_artifact_handle_unhealthy_venv || return $?
    setup_project_artifact_execute
    _BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE=$?

    if ((_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE)) &&
        [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == setup ]]; then
        base_std_log_error "$(setup_recovery_project_layer)"
        base_std_log_error "Python project $_BASE_SETUP_PROJECT_ARTIFACT_ACTION layer failed."
        return "$_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE"
    fi
    if ((_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE)) &&
        [[ "$_BASE_SETUP_PROJECT_ARTIFACT_ACTION" == check ]]; then
        base_std_log_error "Python project check layer found missing requirements."
        return "$_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE"
    fi
    if ((_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE)); then
        return "$_BASE_SETUP_PROJECT_ARTIFACT_EXIT_CODE"
    fi
}
setup_run_project_artifact_check() {
    setup_run_project_artifact_layer check text
}

setup_run_project_artifact_check_json() {
    if [[ -n "${1:-}" ]]; then
        BASE_SETUP_REMOTE_NETWORK="$1"
        export BASE_SETUP_REMOTE_NETWORK
    fi
    setup_run_project_artifact_layer check json
}

setup_run_project_artifact_doctor() {
    setup_run_project_artifact_layer doctor text
}

setup_run_project_artifact_doctor_json() {
    if [[ -n "${1:-}" ]]; then
        BASE_SETUP_REMOTE_NETWORK="$1"
        export BASE_SETUP_REMOTE_NETWORK
    fi
    setup_run_project_artifact_layer doctor json
}
