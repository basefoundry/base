# Test-only builders for Base command-protocol fixtures emitted by fake Python commands.

base_test_protocol_hex() {
    local LC_ALL=C
    local value="$1"
    local byte index

    for ((index = 0; index < ${#value}; index += 1)); do
        printf -v byte '%d' "'${value:index:1}"
        ((byte >= 0)) || byte=$((byte + 256))
        printf '%02x' "$byte"
    done
}

base_test_protocol_begin() {
    printf 'BASE_COMMAND_PROTOCOL_V1\nrecord_type=%s\nrecord_count=%s\n' "$1" "$2"
}

base_test_protocol_string() {
    printf 'field.%s:string=' "$1"
    base_test_protocol_hex "$2"
    printf '\n'
}

base_test_protocol_boolean() {
    printf 'field.%s:boolean=%s\n' "$1" "$2"
}

base_test_protocol_nullable_string() {
    if [[ -n "$2" ]]; then
        base_test_protocol_string "$1" "$2"
    else
        printf 'field.%s:null=\n' "$1"
    fi
}

base_test_protocol_end() {
    printf 'end_protocol=\n'
}

base_test_protocol_project_reference_record() {
    printf 'record=%s\n' "$1"
    base_test_protocol_string project_name "$2"
    base_test_protocol_string project_root "$3"
    base_test_protocol_string manifest_path "$4"
    printf 'end_record=%s\n' "$1"
}

base_test_protocol_project_route_record() {
    printf 'record=%s\n' "$1"
    base_test_protocol_string project_name "$2"
    base_test_protocol_string project_root "$3"
    base_test_protocol_string manifest_path "$4"
    base_test_protocol_string project_venv_dir "$5"
    base_test_protocol_boolean uses_uv_manager "$6"
    base_test_protocol_boolean manifest_command_trust_required "$7"
    printf 'end_record=%s\n' "$1"
}

base_test_protocol_project_setup_route_record() {
    local requires_project_python="${8:-true}"

    printf 'record=%s\n' "$1"
    base_test_protocol_string project_name "$2"
    base_test_protocol_string project_root "$3"
    base_test_protocol_string manifest_path "$4"
    base_test_protocol_string project_venv_dir "$5"
    base_test_protocol_boolean uses_uv_manager "$6"
    base_test_protocol_boolean manifest_command_trust_required "$7"
    base_test_protocol_boolean requires_project_python "$requires_project_python"
    printf 'end_record=%s\n' "$1"
}

base_test_protocol_project_command_record() {
    printf 'record=%s\n' "$1"
    base_test_protocol_string project_name "$2"
    base_test_protocol_string project_root "$3"
    base_test_protocol_string manifest_path "$4"
    base_test_protocol_string project_venv_dir "$5"
    base_test_protocol_boolean uses_uv_manager "$6"
    base_test_protocol_boolean manifest_command_trust_required "$7"
    base_test_protocol_string command "$8"
    base_test_protocol_nullable_string runner "${9:-}"
    printf 'end_record=%s\n' "$1"
}

base_test_protocol_named_command_record() {
    printf 'record=%s\n' "$1"
    base_test_protocol_string project_name "$2"
    base_test_protocol_string project_root "$3"
    base_test_protocol_string manifest_path "$4"
    base_test_protocol_string command_name "$5"
    base_test_protocol_string command "$6"
    base_test_protocol_nullable_string runner "${7:-}"
    printf 'end_record=%s\n' "$1"
}

base_test_protocol_build_target_record() {
    local record_index="$1"
    local command="${10}"
    local description="${11:-}"
    local runner="${12:-}"
    printf 'record=%s\n' "$record_index"
    base_test_protocol_string project_name "$2"
    base_test_protocol_string project_root "$3"
    base_test_protocol_string manifest_path "$4"
    base_test_protocol_string project_venv_dir "$5"
    base_test_protocol_boolean uses_uv_manager "$6"
    base_test_protocol_boolean manifest_command_trust_required "$7"
    base_test_protocol_string target_name "$8"
    base_test_protocol_string working_dir "$9"
    base_test_protocol_string command "$command"
    base_test_protocol_nullable_string description "$description"
    base_test_protocol_nullable_string runner "$runner"
    printf 'end_record=%s\n' "$record_index"
}

base_test_protocol_demo_record() {
    printf 'record=%s\n' "$1"
    base_test_protocol_string project_name "$2"
    base_test_protocol_string project_root "$3"
    base_test_protocol_string manifest_path "$4"
    base_test_protocol_string project_venv_dir "$5"
    base_test_protocol_boolean uses_uv_manager "$6"
    base_test_protocol_boolean manifest_command_trust_required "$7"
    base_test_protocol_string demo_script "$8"
    base_test_protocol_nullable_string runner "${9:-}"
    printf 'end_record=%s\n' "$1"
}

base_test_protocol_activation_source_record() {
    printf 'record=%s\n' "$1"
    base_test_protocol_string source_path "$2"
    printf 'end_record=%s\n' "$1"
}

base_test_protocol_project_list_record() {
    printf 'record=%s\n' "$1"
    base_test_protocol_string project_name "$2"
    base_test_protocol_string project_root "$3"
    printf 'end_record=%s\n' "$1"
}

base_test_protocol_project_reference() {
    base_test_protocol_begin project-reference 1
    base_test_protocol_project_reference_record 0 "$@"
    base_test_protocol_end
}

base_test_protocol_project_route() {
    base_test_protocol_begin project-route 1
    base_test_protocol_project_route_record 0 "$@"
    base_test_protocol_end
}

base_test_protocol_project_setup_route() {
    base_test_protocol_begin project-setup-route 1
    base_test_protocol_project_setup_route_record 0 "$@"
    base_test_protocol_end
}

base_test_protocol_project_command() {
    base_test_protocol_begin project-command 1
    base_test_protocol_project_command_record 0 "$@"
    base_test_protocol_end
}

base_test_protocol_demo() {
    base_test_protocol_begin demo 1
    base_test_protocol_demo_record 0 "$@"
    base_test_protocol_end
}
