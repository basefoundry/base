#!/usr/bin/env bats

load ./basectl_helpers.bash

run_fallback() {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$(base_bash_libs_fixture_dir)" \
        BASE_FALLBACK_RECORD_PATH="$TEST_TMPDIR/record.json" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_check_results.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/setup_diagnostics_fallback.sh"
            setup_base_check_metadata() { printf "BASE-D001\t%s\t%s\n" "$1" "$1"; }
            base_std_fatal_error() { printf "fatal: %s\n" "$*" >&2; return 2; }
            setup_diagnostics_fallback_json "$@"
        ' bash "$@"
}

@test "record-check uses shared parsing and keeps the last scalar value" {
    run_fallback record-check \
        --project first --project demo \
        --status ok --status warn \
        --checked-at first-time --checked-at second-time \
        --output-path "$TEST_TMPDIR/nested/record.json"

    [ "$status" -eq 0 ]
    [ "$(jq -r '.project + ":" + .status + ":" + .checked_at' "$TEST_TMPDIR/nested/record.json")" = "demo:warn:second-time" ]
}

@test "project venv fallback parses its value options" {
    run_fallback project-venv-check-json \
        --project demo \
        --status warn \
        --message "venv is absent" \
        --fix "run basectl setup" \
        --precheck-json '[{"status":"ok"}]'

    [ "$status" -eq 0 ]
    [ "$(jq -r '.project + ":" + .status + ":" + (.checks | length | tostring)' <<<"$output")" = "demo:warn:2" ]
    [ "$(jq -r '.checks[1].message + ":" + .checks[1].fix' <<<"$output")" = "venv is absent:run basectl setup" ]
}

@test "check fallback normalizes grouped repeated records before shared parsing" {
    cat > "$TEST_TMPDIR/check-result" <<'EOF'
name=probe
ok=true
status=ok
message=probe is ready
recovery=
debug=
EOF

    run_fallback check-json \
        --project demo \
        --check homebrew warn "brew is unavailable" "install Homebrew" \
        --check python ok "python is ready" "" \
        --check-result-file "$TEST_TMPDIR/check-result" \
        --embedded-payload summary '{"status":"warn","message":"review"}' \
        --record-path "$TEST_TMPDIR/record.json" \
        --checked-at now

    [ "$status" -eq 0 ]
    [ "$(jq -r '[.checks[].name] | join(",")' <<<"$output")" = "homebrew,python,probe" ]
    [ "$(jq -r '.summary.status + ":" + .status' <<<"$output")" = "warn:warn" ]
    [ "$(jq -r '.project + ":" + .status' "$TEST_TMPDIR/record.json")" = "demo:warn" ]
}
