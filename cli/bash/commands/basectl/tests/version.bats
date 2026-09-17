#!/usr/bin/env bats

load ../../../../../tests/test_helper.sh

setup() {
    setup_test_tmpdir
    unset BASE_BASH_LIBS_DIR BASE_CLI_SOURCE_DIR BASE_SETUP_VENV_DIR
    TEST_INSTALL="$TEST_TMPDIR/base"
    mkdir -p "$TEST_INSTALL/bin" "$TEST_INSTALL/lib/bash/version" \
        "$TEST_INSTALL/lib/base" "$TEST_INSTALL/cli/python" \
        "$TEST_INSTALL/cli/bash/commands/basectl/subcommands"
    cp "$BASE_REPO_ROOT/bin/basectl" "$TEST_INSTALL/bin/"
    cp "$BASE_REPO_ROOT/lib/bash/version/lib_version.sh" "$TEST_INSTALL/lib/bash/version/"
    cp "$BASE_REPO_ROOT/lib/base/"*runtime.sh "$TEST_INSTALL/lib/base/"
    cp "$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/version.sh" "$TEST_INSTALL/cli/bash/commands/basectl/subcommands/"
    cp -R "$BASE_REPO_ROOT/cli/python/base_version" "$TEST_INSTALL/cli/python/"
    printf '1.2.3\n' > "$TEST_INSTALL/VERSION"
    export HOME="$TEST_TMPDIR/home"
    mkdir -p "$HOME"
}

make_providers() {
    mkdir -p "$TEST_TMPDIR/base-cli/lib/python/base_cli" "$TEST_TMPDIR/base-bash-libs/lib/bash/std"
    printf 'raise RuntimeError("do not import")\n' > "$TEST_TMPDIR/base-cli/lib/python/base_cli/__init__.py"
    printf 'exit 99\n' > "$TEST_TMPDIR/base-bash-libs/lib/bash/std/lib_std.sh"
    printf '4.5.6\n' > "$TEST_TMPDIR/base-cli/VERSION"
    printf '2.3.4\n' > "$TEST_TMPDIR/base-bash-libs/VERSION"
}

@test "simple version survives absent providers and venv" {
    run "$TEST_INSTALL/bin/basectl" version
    [ "$status" -eq 0 ]
    [ "$output" = 'basectl 1.2.3' ]
    run "$TEST_INSTALL/bin/basectl" --version
    [ "$status" -eq 0 ]
    [ "$output" = 'basectl 1.2.3' ]
}

@test "detailed version reports siblings without executing providers" {
    make_providers
    run "$TEST_INSTALL/bin/basectl" version --all
    [ "$status" -eq 0 ]
    [[ "$output" == *'base-cli: 4.5.6'* ]]
    [[ "$output" == *'base-bash-libs: 2.3.4'* ]]
    [[ "$output" == *'source: sibling'* ]]
    [[ "$output" == *'(unavailable)'* ]]
}

@test "detailed JSON is a single partial report with missing providers" {
    run "$TEST_INSTALL/bin/basectl" version --json --all
    [ "$status" -eq 0 ]
    printf '%s' "$output" | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["schema_version"] == 1; assert r["status"] == "warn"; assert len(r["data"]["components"]) == 3; assert r["data"]["components"][1]["status"] == "unavailable"'
}

@test "explicit overrides win and paths with spaces are preserved" {
    make_providers
    mv "$TEST_TMPDIR/base-cli" "$TEST_TMPDIR/other cli"
    mv "$TEST_TMPDIR/base-bash-libs" "$TEST_TMPDIR/other libs"
    make_providers
    printf '8.8.8\n' > "$TEST_TMPDIR/other cli/VERSION"
    run env BASE_CLI_SOURCE_DIR="$TEST_TMPDIR/other cli/lib/python" \
        BASE_BASH_LIBS_DIR="$TEST_TMPDIR/other libs/lib/bash" \
        "$TEST_INSTALL/bin/basectl" version --all --json
    [ "$status" -eq 0 ]
    printf '%s' "$output" | python3 -c 'import json,sys; c=json.load(sys.stdin)["data"]["components"]; assert c[1]["source"] == c[2]["source"] == "explicit"; assert c[1]["version"] == "8.8.8"; assert "other cli" in c[1]["path"]'
}

@test "broken explicit overrides do not fall back to valid siblings" {
    make_providers
    run env BASE_CLI_SOURCE_DIR="$TEST_TMPDIR/missing" BASE_BASH_LIBS_DIR="$TEST_TMPDIR/missing" \
        "$TEST_INSTALL/bin/basectl" version --all --json
    [ "$status" -eq 0 ]
    printf '%s' "$output" | python3 -c 'import json,sys; c=json.load(sys.stdin)["data"]["components"]; assert c[1]["status"] == c[2]["status"] == "unavailable"; assert c[1]["version"] is None'
}

@test "broken sibling CLI does not fall back to installed metadata" {
    mkdir -p "$TEST_TMPDIR/base-cli"
    run "$TEST_INSTALL/bin/basectl" version --all --json
    [ "$status" -eq 0 ]
    printf '%s' "$output" | python3 -c 'import json,sys; c=json.load(sys.stdin)["data"]["components"]; assert c[1]["status"] == "unavailable"; assert "sibling" in c[1]["detail"]'
}

@test "version JSON requires all and unknown arguments fail" {
    run "$TEST_INSTALL/bin/basectl" version --json
    [ "$status" -eq 2 ]
    [[ "$output" == *'--json requires --all'* ]]
    run "$TEST_INSTALL/bin/basectl" version --all unexpected
    [ "$status" -eq 2 ]
    run "$TEST_INSTALL/bin/basectl" --version --all
    [ "$status" -eq 2 ]
}

@test "Homebrew layout uses the runtime Bash provider resolver" {
    local prefix="$TEST_TMPDIR/brew"
    mkdir -p "$prefix/opt/base" "$prefix/opt/base-bash-libs/libexec/lib/bash/std"
    mv "$TEST_INSTALL" "$prefix/opt/base/libexec"
    printf '2.9.0\n' > "$prefix/opt/base-bash-libs/libexec/VERSION"
    touch "$prefix/opt/base-bash-libs/libexec/lib/bash/std/lib_std.sh"
    run "$prefix/opt/base/libexec/bin/basectl" version --all --json
    [ "$status" -eq 0 ]
    printf '%s' "$output" | python3 -c 'import json,sys; c=json.load(sys.stdin)["data"]["components"][2]; assert c["source"] == "homebrew"; assert c["version"] == "2.9.0"'
}

@test "selected Python respects the Base setup venv override" {
    run env BASE_SETUP_VENV_DIR="$TEST_TMPDIR/custom venv" "$TEST_INSTALL/bin/basectl" version --all --json
    [ "$status" -eq 0 ]
    printf '%s' "$output" | python3 -c 'import json,sys; p=json.load(sys.stdin)["data"]["python"]; assert p["path"].endswith("custom venv/bin/python"); assert p["exists"] is False'
}

@test "working Base Python can report versions when PATH Python is broken" {
    local python_bin
    python_bin="$(command -v python3)"
    mkdir -p "$TEST_TMPDIR/venv/bin" "$TEST_TMPDIR/mockbin"
    ln -s "$python_bin" "$TEST_TMPDIR/venv/bin/python"
    printf '#!/bin/sh\nexit 91\n' > "$TEST_TMPDIR/mockbin/python3"
    chmod +x "$TEST_TMPDIR/mockbin/python3"
    make_providers
    run env BASE_SETUP_VENV_DIR="$TEST_TMPDIR/venv" PATH="$TEST_TMPDIR/mockbin:$PATH" \
        "$TEST_INSTALL/bin/basectl" version --all
    [ "$status" -eq 0 ]
    [[ "$output" == *'base-cli: 4.5.6'* ]]
}
