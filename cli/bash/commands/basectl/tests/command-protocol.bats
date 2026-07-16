#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "command protocol preserves field boundaries and nullable values" {
    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" "$BASH" -c '
        source "$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash"
        source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"
        value=$'"'"'tabs\t spaces λ\nline\x01'"'"'
        payload="$(base_test_protocol_project_command \
            "$value" "/tmp/root with spaces" "/tmp/base_manifest.yaml" "/tmp/.venv" \
            true false "$value" "")"
        base_command_protocol_decode_one project-command "$payload" || exit
        [[ "${BASE_COMMAND_PROTOCOL_FIELDS[project_name]}" == "$value" ]]
        [[ "${BASE_COMMAND_PROTOCOL_FIELDS[command]}" == "$value" ]]
        [[ "${BASE_COMMAND_PROTOCOL_FIELDS[runner]}" == "" ]]
        [[ "${BASE_COMMAND_PROTOCOL_NULL_FIELDS[runner]:-}" == 1 ]]
        printf "decoded\n"
    '

    [ "$status" -eq 0 ]
    [ "$output" = decoded ]
}

@test "command protocol distinguishes an empty string from null" {
    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" "$BASH" -c '
        source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"
        payload="BASE_COMMAND_PROTOCOL_V1
record_type=project-command
record_count=1
record=0
field.project_name:string=64656d6f
field.project_root:string=2f746d702f64656d6f
field.manifest_path:string=2f746d702f64656d6f2f626173655f6d616e69666573742e79616d6c
field.project_venv_dir:string=2f746d702f64656d6f2f2e76656e76
field.uses_uv_manager:boolean=false
field.requires_project_python:boolean=true
field.manifest_command_trust_required:boolean=true
field.command:string=7072696e7466206f6b
field.runner:string=
end_record=0
end_protocol="
        base_command_protocol_decode_one project-command "$payload" || exit
        [[ "${BASE_COMMAND_PROTOCOL_FIELDS[runner]}" == "" ]]
        [[ -z "${BASE_COMMAND_PROTOCOL_NULL_FIELDS[runner]+present}" ]]
    '

    [ "$status" -eq 0 ]
}

@test "command protocol iterates multiple explicitly named records" {
    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" "$BASH" -c '
        source "$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash"
        source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"
        collect() { names+="${names:+,}${BASE_COMMAND_PROTOCOL_FIELDS[command_name]}"; }
        names=""
        payload="$(
            base_test_protocol_begin named-command 2
            base_test_protocol_named_command_record 0 demo /tmp/demo /tmp/demo/base_manifest.yaml test "pytest tests/" ""
            base_test_protocol_named_command_record 1 demo /tmp/demo /tmp/demo/base_manifest.yaml dev "uvicorn app:app" uv
            base_test_protocol_end
        )"
        base_command_protocol_each named-command "$payload" collect || exit
        printf "%s\n" "$names"
    '

    [ "$status" -eq 0 ]
    [ "$output" = test,dev ]
}

@test "command protocol validates every record before invoking callbacks" {
    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" "$BASH" -c '
        source "$BASE_REPO_ROOT/cli/bash/commands/basectl/tests/command_protocol_fixtures.bash"
        source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"
        collect() { ((callback_count += 1)); }
        callback_count=0
        payload="$(
            base_test_protocol_begin named-command 2
            base_test_protocol_named_command_record 0 demo /tmp/demo /tmp/demo/base_manifest.yaml test "pytest tests/" ""
            base_test_protocol_named_command_record 1 demo /tmp/demo /tmp/demo/base_manifest.yaml dev "uvicorn app:app" uv
            base_test_protocol_end
        )"
        payload="${payload/field.command_name:string=646576/field.unknown:string=646576}"
        if base_command_protocol_each named-command "$payload" collect; then
            exit 1
        fi
        printf "callbacks=%s\n" "$callback_count"
    '

    [ "$status" -eq 0 ]
    [[ "$output" == *"unknown field 'unknown'"* ]]
    [[ "$output" == *"callbacks=0"* ]]
}

@test "command protocol rejects unsupported versions and record types" {
    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" "$BASH" -c '
        source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"
        payload="BASE_COMMAND_PROTOCOL_V2
record_type=project-reference
record_count=0
end_protocol="
        ! base_command_protocol_parse project-reference "$payload"
    '
    [ "$status" -eq 0 ]
    [[ "$output" == *"unsupported protocol header"* ]]

    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" "$BASH" -c '
        source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"
        payload="BASE_COMMAND_PROTOCOL_V1
record_type=project-route
record_count=0
end_protocol="
        ! base_command_protocol_parse project-reference "$payload"
    '
    [ "$status" -eq 0 ]
    [[ "$output" == *"expected record_type 'project-reference', got 'project-route'"* ]]
}

@test "command protocol rejects noncanonical and overflowing record counts" {
    local count

    for count in 01 1000001 18446744073709551616; do
        run env BASE_REPO_ROOT="$BASE_REPO_ROOT" COUNT="$count" "$BASH" -c '
            source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"
            payload="BASE_COMMAND_PROTOCOL_V1
record_type=project-reference
record_count=$COUNT
end_protocol="
            ! base_command_protocol_parse project-reference "$payload"
        '
        [ "$status" -eq 0 ]
        [[ "$output" == *"record_count"* ]]
    done
}

@test "command protocol rejects missing unknown duplicate and mistyped fields" {
    local manifest_line valid
    valid=$'BASE_COMMAND_PROTOCOL_V1\nrecord_type=project-reference\nrecord_count=1\nrecord=0\nfield.project_name:string=64656d6f\nfield.project_root:string=2f746d702f64656d6f\nfield.manifest_path:string=2f746d702f64656d6f2f626173655f6d616e69666573742e79616d6c\nend_record=0\nend_protocol='
    manifest_line=$'field.manifest_path:string=2f746d702f64656d6f2f626173655f6d616e69666573742e79616d6c\n'

    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" PAYLOAD="${valid/"$manifest_line"/}" \
        "$BASH" -c 'source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"; ! base_command_protocol_decode_one project-reference "$PAYLOAD"'
    [ "$status" -eq 0 ]
    [[ "$output" == *"missing field 'manifest_path'"* ]]

    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" PAYLOAD="${valid/field.manifest_path/field.unknown}" \
        "$BASH" -c 'source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"; ! base_command_protocol_decode_one project-reference "$PAYLOAD"'
    [ "$status" -eq 0 ]
    [[ "$output" == *"unknown field 'unknown'"* ]]

    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" PAYLOAD="${valid/field.manifest_path:string=2f746d702f64656d6f2f626173655f6d616e69666573742e79616d6c/field.project_name:string=6f74686572}" \
        "$BASH" -c 'source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"; ! base_command_protocol_decode_one project-reference "$PAYLOAD"'
    [ "$status" -eq 0 ]
    [[ "$output" == *"duplicates field 'project_name'"* ]]

    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" PAYLOAD="${valid/field.project_name:string/field.project_name:boolean}" \
        "$BASH" -c 'source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"; ! base_command_protocol_decode_one project-reference "$PAYLOAD"'
    [ "$status" -eq 0 ]
    [[ "$output" == *"wire type 'boolean'"* ]]
}

@test "command protocol rejects malformed hexadecimal UTF-8 NUL and framing" {
    local valid
    valid=$'BASE_COMMAND_PROTOCOL_V1\nrecord_type=project-reference\nrecord_count=1\nrecord=0\nfield.project_name:string=64656d6f\nfield.project_root:string=2f746d702f64656d6f\nfield.manifest_path:string=2f746d702f64656d6f2f626173655f6d616e69666573742e79616d6c\nend_record=0\nend_protocol='

    for replacement in abc c080 00; do
        run env BASE_REPO_ROOT="$BASE_REPO_ROOT" PAYLOAD="${valid/64656d6f/$replacement}" \
            "$BASH" -c 'source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"; ! base_command_protocol_decode_one project-reference "$PAYLOAD"'
        [ "$status" -eq 0 ]
        [[ "$output" == *"Invalid Base command protocol"* ]]
    done

    run env BASE_REPO_ROOT="$BASE_REPO_ROOT" PAYLOAD="$valid"$'\nunexpected=true' \
        "$BASH" -c 'source "$BASE_REPO_ROOT/lib/bash/runtime/command_protocol.sh"; ! base_command_protocol_decode_one project-reference "$PAYLOAD"'
    [ "$status" -eq 0 ]
    [[ "$output" == *"unexpected data after end_protocol"* ]]
}
