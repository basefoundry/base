#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl repo prints help" {
    run_basectl repo --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo init <name>"* ]]
    [[ "$output" == *"basectl repo check [path]"* ]]
    [[ "$output" == *"basectl repo configure [path]"* ]]
}

@test "basectl repo init dry-run prints baseline and configuration plan" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/README.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create executable '$repo_dir/tests/validate.sh'."* ]]
    [[ "$output" == *"gh repo edit codeforester/base-demo"* ]]
    [[ "$output" == *"gh label create bug"* ]]
    [ ! -e "$repo_dir" ]
}

@test "basectl repo init creates the standard repository baseline" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/README.md" ]
    [ -f "$repo_dir/VERSION" ]
    [ -f "$repo_dir/CHANGELOG.md" ]
    [ -f "$repo_dir/CONTRIBUTING.md" ]
    [ -f "$repo_dir/LICENSE" ]
    [ -f "$repo_dir/.gitignore" ]
    [ -f "$repo_dir/base_manifest.yaml" ]
    [ -x "$repo_dir/tests/validate.sh" ]
    [ -f "$repo_dir/.github/workflows/tests.yml" ]
    grep -Fqx "0.1.0" "$repo_dir/VERSION"
    grep -Fq "name: base-demo" "$repo_dir/base_manifest.yaml"
    grep -Fq "command: ./tests/validate.sh" "$repo_dir/base_manifest.yaml"
}

@test "basectl repo init leaves existing files unchanged" {
    local repo_dir="$TEST_TMPDIR/custom"

    mkdir -p "$repo_dir"
    printf 'custom readme\n' > "$repo_dir/README.md"

    run_basectl repo init custom --path "$repo_dir" --no-configure

    [ "$status" -eq 0 ]
    [ "$(cat "$repo_dir/README.md")" = "custom readme" ]
    [ -f "$repo_dir/base_manifest.yaml" ]
}

@test "basectl repo check passes for a generated baseline" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]

    run_basectl repo check "$repo_dir"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository baseline check passed."* ]]
}

@test "basectl repo check reports missing baseline files" {
    local repo_dir="$TEST_TMPDIR/incomplete"

    mkdir -p "$repo_dir"
    printf '# Incomplete\n' > "$repo_dir/README.md"

    run_basectl repo check "$repo_dir"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Missing repository baseline file 'VERSION'."* ]]
    [[ "$output" == *"Repository baseline check found missing requirements."* ]]
}

@test "basectl repo configure dry-run prints GitHub settings and labels" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" --repo codeforester/base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"gh repo edit codeforester/base-demo"* ]]
    [[ "$output" == *"--enable-squash-merge"* ]]
    [[ "$output" == *"--delete-branch-on-merge"* ]]
    [[ "$output" == *"gh label create needs-demo"* ]]
}

@test "basectl repo configure applies GitHub settings through gh" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo

    [ "$status" -eq 0 ]
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    grep -Fq "label create bug --repo codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    grep -Fq "label create needs-demo --repo codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
}

@test "basectl repo init configures GitHub when repo is provided" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo --path "$repo_dir" --repo codeforester/base-demo

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/base_manifest.yaml" ]
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
}

@test "basectl repo configure can infer GitHub repo from origin remote" {
    local repo_dir="$TEST_TMPDIR/repo"

    init_git_repo "$repo_dir"
    git -C "$repo_dir" remote add origin git@github.com:codeforester/base-demo.git

    run_basectl repo configure "$repo_dir" --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"gh repo edit codeforester/base-demo"* ]]
}
