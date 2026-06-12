#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl activate resolves a project and execs a project subshell" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local project_activate="$TEST_HOME/.base.d/demo/.venv/bin/activate"
    local workspace="$TEST_TMPDIR/workspace"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'args=%s\n' "$*"
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_ROOT=%s\n' "$BASE_PROJECT_ROOT"
printf 'BASE_PROJECT_MANIFEST=%s\n' "$BASE_PROJECT_MANIFEST"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
printf 'PWD=%s\n' "$PWD"
EOF
    printf '#!/usr/bin/env bash\n' > "$project_python"
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$TEST_HOME/.base.d/demo/.venv" > "$project_activate"
    chmod +x "$base_python" "$project_python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" != *"BASE_SHELL: readonly variable"* ]]
    [[ "$output" == *"args=--rcfile $BASE_REPO_ROOT/lib/bash/runtime/bashrc"* ]]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$workspace/demo"* ]]
    [[ "$output" == *"BASE_PROJECT_MANIFEST=$workspace/demo/base_manifest.yaml"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$TEST_HOME/.base.d/demo/.venv"* ]]
    [[ "$output" == *"PWD=$workspace/demo"* ]]
}

@test "basectl activate honors BASE_PROJECT_VENV_DIR override" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_python="$TEST_TMPDIR/custom-venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
EOF
    printf '#!/usr/bin/env bash\n' > "$project_python"
    chmod +x "$base_python" "$project_python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_PROJECT_VENV_DIR="$TEST_TMPDIR/custom-venv" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$TEST_TMPDIR/custom-venv"* ]]
}

@test "basectl activate prefers uv project .venv when uv lockfile is present" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$workspace/demo/.venv/bin"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_VENV_DIR=%s\n' "$BASE_PROJECT_VENV_DIR"
EOF
    printf '#!/usr/bin/env bash\n' > "$workspace/demo/.venv/bin/python"
    chmod +x "$base_python" "$workspace/demo/.venv/bin/python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    printf '[project]\nname = "demo"\n' > "$workspace/demo/pyproject.toml"
    printf 'version = 1\n' > "$workspace/demo/uv.lock"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_ACTIVATE_SHELL="$fake_bash" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_VENV_DIR=$workspace/demo/.venv"* ]]
}

@test "basectl activate guides uv projects to create the uv environment" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local workspace="$TEST_TMPDIR/workspace"

    mkdir -p "$(dirname "$base_python")" "$workspace/demo"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    chmod +x "$base_python"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    printf '[project]\nname = "demo"\n' > "$workspace/demo/pyproject.toml"
    printf 'version = 1\n' > "$workspace/demo/uv.lock"
    workspace="$(cd "$workspace" && pwd -P)"

    run env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_TEST_PROJECT_ROOT="$workspace/demo" \
        "$BASE_REPO_ROOT/bin/basectl" activate demo

    [ "$status" -ne 0 ]
    [[ "$output" == *"Project virtual environment Python was not found at '$workspace/demo/.venv/bin/python'."* ]]
    [[ "$output" == *"Run 'uv sync' in '$workspace/demo' first."* ]]
    [[ "$output" != *"Run 'basectl setup demo' first."* ]]
}

@test "basectl default runtime shell preserves caller working directory" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_activate="$TEST_HOME/.base.d/base/.venv/bin/activate"
    local workspace="$TEST_TMPDIR/workspace"
    local caller="$TEST_TMPDIR/caller"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$workspace/base" "$caller"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "base" ]]; then
    printf 'base\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_ROOT=%s\n' "$BASE_PROJECT_ROOT"
printf 'PWD=%s\n' "$PWD"
EOF
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$TEST_HOME/.base.d/base/.venv" > "$project_activate"
    chmod +x "$base_python" "$fake_bash"
    printf 'project:\n  name: base\nartifacts: []\n' > "$workspace/base/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"
    caller="$(cd "$caller" && pwd -P)"

    run bash -c 'cd "$1" || exit 1; shift; exec "$@"' _ "$caller" \
        env \
            HOME="$TEST_HOME" \
            PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
            BASE_ACTIVATE_PRESERVE_CWD=1 \
            BASE_ACTIVATE_SHELL="$fake_bash" \
            BASE_TEST_PROJECT_ROOT="$workspace/base" \
            "$BASE_REPO_ROOT/bin/basectl" activate base

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=base"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$workspace/base"* ]]
    [[ "$output" == *"PWD=$caller"* ]]
}

@test "basectl activate --no-cd preserves caller working directory" {
    local base_python="$TEST_HOME/.base.d/base/.venv/bin/python"
    local project_python="$TEST_HOME/.base.d/demo/.venv/bin/python"
    local project_activate="$TEST_HOME/.base.d/demo/.venv/bin/activate"
    local workspace="$TEST_TMPDIR/workspace"
    local caller="$TEST_TMPDIR/caller"
    local fake_bash="$TEST_TMPDIR/fake-bash"

    mkdir -p "$(dirname "$base_python")" "$(dirname "$project_python")" "$workspace/demo" "$caller"
    cat > "$base_python" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "base_projects" && "${3:-}" == "resolve" && "${4:-}" == "demo" ]]; then
    printf 'demo\t%s\t%s\n' "${BASE_TEST_PROJECT_ROOT:?}" "${BASE_TEST_PROJECT_ROOT:?}/base_manifest.yaml"
    exit 0
fi
printf 'unexpected activate resolver args: %s\n' "$*" >&2
exit 1
EOF
    cat > "$fake_bash" <<'EOF'
#!/usr/bin/env bash
printf 'BASE_PROJECT=%s\n' "$BASE_PROJECT"
printf 'BASE_PROJECT_ROOT=%s\n' "$BASE_PROJECT_ROOT"
printf 'PWD=%s\n' "$PWD"
EOF
    printf 'VIRTUAL_ENV=%s\nexport VIRTUAL_ENV\n' "$TEST_HOME/.base.d/demo/.venv" > "$project_activate"
    printf '#!/usr/bin/env bash\n' > "$project_python"
    chmod +x "$base_python" "$project_python" "$fake_bash"
    printf 'project:\n  name: demo\nartifacts: []\n' > "$workspace/demo/base_manifest.yaml"
    workspace="$(cd "$workspace" && pwd -P)"
    caller="$(cd "$caller" && pwd -P)"

    run bash -c 'cd "$1" || exit 1; shift; exec "$@"' _ "$caller" \
        env \
            HOME="$TEST_HOME" \
            PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
            BASE_ACTIVATE_SHELL="$fake_bash" \
            BASE_TEST_PROJECT_ROOT="$workspace/demo" \
            "$BASE_REPO_ROOT/bin/basectl" activate demo --no-cd

    [ "$status" -eq 0 ]
    [[ "$output" == *"BASE_PROJECT=demo"* ]]
    [[ "$output" == *"BASE_PROJECT_ROOT=$workspace/demo"* ]]
    [[ "$output" == *"PWD=$caller"* ]]
}

@test "basectl activate prints help without requiring the Base Python venv" {
    run_basectl activate --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl activate <project> [options]"* ]]
    [[ "$output" == *"--no-cd"* ]]
}

@test "basectl activate reports missing project as a usage error" {
    run_basectl activate

    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"ERROR: Project name is required."* ]]
    [[ "$output" != *"FATAL"* ]]
    [[ "$output" != *"Encountered a fatal error"* ]]
}

@test "basectl activate reports invalid arguments as usage errors" {
    run_basectl activate --workspace
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--workspace' requires an argument."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl activate --unknown demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Unknown activate option '--unknown'."* ]]
    [[ "$output" != *"FATAL"* ]]

    run_basectl activate demo extra
    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: The 'activate' command accepts exactly one project name."* ]]
    [[ "$output" != *"FATAL"* ]]
}
