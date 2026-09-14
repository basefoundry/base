#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl uninstall prints focused help without Python runtime" {
    run_basectl uninstall --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"basectl uninstall <project> [options]"* ]]
    [[ "$output" == *"basectl uninstall --all [options]"* ]]
    [[ "$output" == *"--verify"* ]]
    [[ "$output" == *"The project checkout and its manifest are"* ]]
    [[ "$output" == *"never deleted."* ]]
}

@test "basectl uninstall requires an explicit project or --all" {
    run_basectl uninstall

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Provide a project name or use '--all'."* ]]

    run_basectl uninstall demo --all

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Option '--all' cannot be combined with a project name."* ]]

    run_basectl uninstall --all --yes --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"ERROR: Options '--dry-run' and '--yes' cannot be used together."* ]]
}

@test "basectl uninstall forwards the plan to the Python layer" {
    local python_bin="$TEST_HOME/.base.d/base/.venv/bin/python"

    mkdir -p "$(dirname "$python_bin")"
    cat > "$python_bin" <<'EOF'
#!/usr/bin/env bash
printf 'python=%s\n' "$*"
exit 0
EOF
    chmod +x "$python_bin"
    printf '%s\n' '# >>> base: bashrc managed >>>' '# <<< base: bashrc managed <<<' > "$TEST_HOME/.bashrc"

    run_basectl uninstall --all --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"python=-m base_uninstall --all --dry-run"* ]]
    [[ "$output" == *"Would remove section 'bashrc' from '$TEST_HOME/.bashrc'."* ]]
}
