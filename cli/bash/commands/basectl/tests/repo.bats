#!/usr/bin/env bats

load ./basectl_helpers.bash


@test "basectl repo prints help" {
    run_basectl repo --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo init <name>"* ]]
    [[ "$output" == *"basectl repo check [path]"* ]]
    [[ "$output" == *"basectl repo configure [path]"* ]]
    [[ "$output" == *"basectl repo agent-guidance [path]"* ]]
    [[ "$output" == *"basectl repo installer-template [path]"* ]]
}

@test "basectl repo installer-template prints the maintained template" {
    run_basectl repo installer-template

    [ "$status" -eq 0 ]
    [[ "$output" == *'PROJECT_NAME="${PROJECT_NAME:-example-project}"'* ]]
    [[ "$output" == *'PROJECT_REPO_URL="${PROJECT_REPO_URL:-https://github.com/example/example-project.git}"'* ]]
    [[ "$output" == *'basectl" setup --manifest "$PROJECT_DIR/base_manifest.yaml" "$PROJECT_NAME"'* ]]
    [[ "$output" == *"Explicit error handling is used instead of set -e"* ]]
    [[ "$output" == *'run git -C "$BASE_DIR" pull --ff-only || die'* ]]
    [[ "$output" != *"set -euo pipefail"* ]]
}

@test "basectl repo installer-template writes an executable template" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo installer-template "$repo_dir/install.sh"

    [ "$status" -eq 0 ]
    [ -x "$repo_dir/install.sh" ]
    grep -Fq 'PROJECT_NAME="${PROJECT_NAME:-example-project}"' "$repo_dir/install.sh"
}

@test "basectl repo installer-template leaves existing files unchanged" {
    local repo_dir="$TEST_TMPDIR/custom"

    mkdir -p "$repo_dir"
    printf 'custom\n' > "$repo_dir/install.sh"

    run_basectl repo installer-template "$repo_dir/install.sh"

    [ "$status" -eq 0 ]
    [ "$(cat "$repo_dir/install.sh")" = "custom" ]
}

@test "basectl repo installer-template dry-run reports executable creation" {
    local repo_dir="$TEST_TMPDIR/dry-run"

    run_basectl repo installer-template "$repo_dir/install.sh" --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create executable '$repo_dir/install.sh'."* ]]
    [ ! -e "$repo_dir/install.sh" ]
}

@test "basectl repo agent-guidance dry-run reports guidance files" {
    local repo_dir="$TEST_TMPDIR/agent-demo"

    run_basectl repo agent-guidance "$repo_dir" --repo-name base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/AGENTS.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/skills.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/.github/pull_request_template.md'."* ]]
    [ ! -e "$repo_dir" ]
}

@test "basectl repo agent-guidance prints command-specific help" {
    run_basectl repo agent-guidance --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo agent-guidance [path] [options]"* ]]
    [[ "$output" == *"--repo-name <name>"* ]]
    [[ "$output" == *"--default-branch <name>"* ]]
    [[ "$output" == *"--validation-command <cmd>"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" != *"--repo <owner/name>"* ]]
    [[ "$output" != *"--private"* ]]
    [[ "$output" != *"--public"* ]]
}

@test "basectl repo agent-guidance defaults to current directory name" {
    local repo_dir="$TEST_TMPDIR/current-demo"

    mkdir -p "$repo_dir"

    cd "$repo_dir"
    run_basectl repo agent-guidance

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/AGENTS.md" ]
    [ -f "$repo_dir/skills.md" ]
    [ -f "$repo_dir/.github/pull_request_template.md" ]
    grep -Fq "# Agent Instructions for current-demo" "$repo_dir/AGENTS.md"
    grep -Fq "# Project Skills for current-demo" "$repo_dir/skills.md"
}

@test "basectl repo agent-guidance creates optional guidance baseline" {
    local repo_dir="$TEST_TMPDIR/agent-demo"

    run_basectl repo agent-guidance "$repo_dir" \
        --repo-name base-demo \
        --default-branch master \
        --validation-command "env -u BASE_HOME ./bin/base-test"

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/AGENTS.md" ]
    [ -f "$repo_dir/skills.md" ]
    [ -f "$repo_dir/.github/pull_request_template.md" ]
    grep -Fq "# Agent Instructions for base-demo" "$repo_dir/AGENTS.md"
    grep -Fq "git worktree add -b <branch> ../base-demo-worktrees/<slug> origin/master" "$repo_dir/AGENTS.md"
    grep -Fq "env -u BASE_HOME ./bin/base-test" "$repo_dir/AGENTS.md"
    grep -Fq '`bug`, `enhancement`, `documentation`,' "$repo_dir/AGENTS.md"
    grep -Fq '`ci`, or `security`.' "$repo_dir/AGENTS.md"
    grep -Fq "# Project Skills for base-demo" "$repo_dir/skills.md"
    grep -Fq "Closes #" "$repo_dir/.github/pull_request_template.md"
}

@test "basectl repo agent-guidance leaves existing files unchanged" {
    local repo_dir="$TEST_TMPDIR/custom-guidance"

    mkdir -p "$repo_dir/.github"
    printf 'custom agents\n' > "$repo_dir/AGENTS.md"
    printf 'custom skills\n' > "$repo_dir/skills.md"
    printf 'custom pr\n' > "$repo_dir/.github/pull_request_template.md"

    run_basectl repo agent-guidance "$repo_dir" --repo-name custom-guidance

    [ "$status" -eq 0 ]
    [ "$(cat "$repo_dir/AGENTS.md")" = "custom agents" ]
    [ "$(cat "$repo_dir/skills.md")" = "custom skills" ]
    [ "$(cat "$repo_dir/.github/pull_request_template.md")" = "custom pr" ]
}

@test "basectl repo init dry-run prints baseline and configuration plan" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/README.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/.github/pull_request_template.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create executable '$repo_dir/tests/validate.sh'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create private GitHub repository 'codeforester/base-demo' if it does not already exist."* ]]
    [[ "$output" == *"gh repo edit codeforester/base-demo"* ]]
    [[ "$output" == *"gh label create bug"* ]]
    [[ "$output" == *'--description "Something is not working"'* ]]
    [[ "$output" != *'Something\ is\ not\ working'* ]]
    [ ! -e "$repo_dir" ]
}

@test "basectl repo init defaults to configured workspace root" {
    local nested_dir="$TEST_TMPDIR/nested/current"
    local workspace_root="$TEST_TMPDIR/workspace-root"
    local repo_dir="$workspace_root/base-demo"

    mkdir -p "$TEST_HOME/.base.d" "$nested_dir" "$workspace_root"
    printf 'workspace:\n  root: %s\n' "$workspace_root" > "$TEST_HOME/.base.d/config.yaml"

    cd "$nested_dir"
    run_basectl repo init base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/README.md'."* ]]
    [[ "$output" != *"$nested_dir/base-demo"* ]]
    [[ "$output" == *"[DRY-RUN] Would not create or configure a GitHub repository because no GitHub repo was provided or inferred."* ]]
    [ ! -e "$repo_dir" ]
}

@test "basectl repo init falls back to BASE_HOME parent when workspace root is not configured" {
    local nested_dir="$TEST_TMPDIR/nested/current"
    local repo_name="base-fallback-${BATS_TEST_NUMBER}"
    local workspace_root
    local repo_dir

    workspace_root="$(cd "$BASE_REPO_ROOT/.." && pwd -P)"
    repo_dir="$workspace_root/$repo_name"
    mkdir -p "$nested_dir"

    cd "$nested_dir"
    run_basectl repo init "$repo_name" --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/README.md'."* ]]
    [[ "$output" != *"$nested_dir/base-demo"* ]]
    [[ "$output" == *"[DRY-RUN] Would not create or configure a GitHub repository because no GitHub repo was provided or inferred."* ]]
}

@test "basectl repo init creates the standard repository baseline" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/README.md" ]
    [ -f "$repo_dir/VERSION" ]
    [ -f "$repo_dir/CHANGELOG.md" ]
    [ -f "$repo_dir/CONTRIBUTING.md" ]
    [ -f "$repo_dir/.github/pull_request_template.md" ]
    [ -f "$repo_dir/LICENSE" ]
    [ -f "$repo_dir/.gitignore" ]
    [ -f "$repo_dir/base_manifest.yaml" ]
    [ -x "$repo_dir/tests/validate.sh" ]
    [ -f "$repo_dir/.github/workflows/tests.yml" ]
    grep -Fqx "0.1.0" "$repo_dir/VERSION"
    grep -Fq "name: base-demo" "$repo_dir/base_manifest.yaml"
    grep -Fq "command: ./tests/validate.sh" "$repo_dir/base_manifest.yaml"
    grep -Fq "<category>/<issue>-<YYYYMMDD>-<slug>" "$repo_dir/CONTRIBUTING.md"
    grep -Fq "git worktree add -b <branch> ../base-demo-worktrees/<slug> origin/<default-branch>" "$repo_dir/CONTRIBUTING.md"
    grep -Fq 'Update `CHANGELOG.md` only for notable user-visible or release-worthy' "$repo_dir/CONTRIBUTING.md"
    grep -Fq "## Checklist" "$repo_dir/.github/pull_request_template.md"
    grep -Fq "CHANGELOG is updated for notable user-visible or release-worthy changes." "$repo_dir/.github/pull_request_template.md"
    ! grep -Fq "Demo Impact" "$repo_dir/.github/pull_request_template.md"

    run bash -c 'cd "$1" && ./tests/validate.sh' _ "$repo_dir"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository baseline is present."* ]]
}

@test "basectl repo init defaults copyright holder to git user name" {
    local repo_dir="$TEST_TMPDIR/git-owner"

    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "config" && "${2:-}" == "--global" && "${3:-}" == "user.name" ]]; then
    printf 'Ada Lovelace\n'
    exit 0
fi
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/git"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo init git-owner --path "$repo_dir" --no-configure

    [ "$status" -eq 0 ]
    grep -Fq "Copyright (c) $(date +%Y) Ada Lovelace" "$repo_dir/LICENSE"
}

@test "basectl repo init falls back to system username for copyright holder" {
    local repo_dir="$TEST_TMPDIR/system-owner"
    local username

    cat > "$TEST_MOCKBIN/git" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/git"
    username="$(id -un)"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo init system-owner --path "$repo_dir" --no-configure

    [ "$status" -eq 0 ]
    grep -Fq "Copyright (c) $(date +%Y) $username" "$repo_dir/LICENSE"
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

@test "basectl repo init reports baseline parent directory creation failures" {
    local blocked_parent="$TEST_TMPDIR/blocked"
    local repo_dir="$blocked_parent/base-demo"

    printf 'not a directory\n' > "$blocked_parent"

    run --separate-stderr env \
        HOME="$TEST_HOME" \
        PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo --path "$repo_dir" --no-configure

    [ "$status" -eq 1 ]
    [[ "${output:-}${stderr:-}" == *"Failed to create parent directory '$repo_dir'."* ]]
    [ ! -e "$repo_dir/README.md" ]
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

@test "basectl repo check reports missing agent guidance only when opted in" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]

    run_basectl repo check "$repo_dir" --agent-guidance

    [ "$status" -eq 1 ]
    [[ "$output" == *"Missing agent guidance file 'AGENTS.md'."* ]]
    [[ "$output" == *"Missing agent guidance file 'skills.md'."* ]]
    [[ "$output" == *"Agent guidance baseline check found missing requirements."* ]]
}

@test "basectl repo check passes with generated agent guidance when opted in" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]
    run_basectl repo agent-guidance "$repo_dir" --repo-name base-demo
    [ "$status" -eq 0 ]

    run_basectl repo check "$repo_dir" --agent-guidance

    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository baseline check passed."* ]]
    [[ "$output" == *"Agent guidance baseline check passed."* ]]
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
    [[ "$output" == *'--description "Change should update a project demo"'* ]]
    [[ "$output" != *'Change\ should\ update\ a\ project\ demo'* ]]
}

@test "basectl repo configure applies GitHub settings through gh" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "repo view codeforester/base-demo" ]]; then
    exit 1
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
if [[ "$*" == "repo view codeforester/base-demo" ]]; then
    exit 1
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
    grep -Fq "repo create codeforester/base-demo --private --description Base-managed project base-demo." "$TEST_STATE_DIR/gh-args"
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    ! grep -Fq "pr create" "$TEST_STATE_DIR/gh-args"
}

@test "basectl repo init --pr opens a baseline pull request" {
    local commit_files
    local remote_dir="$TEST_TMPDIR/origin.git"
    local repo_dir="$TEST_TMPDIR/base-demo"

    init_git_repo "$repo_dir"
    printf '# Existing project\n' > "$repo_dir/README.md"
    mkdir -p "$repo_dir/src"
    printf 'app\n' > "$repo_dir/src/app.txt"
    commit_all "$repo_dir" "Initial commit"
    git init --bare "$remote_dir" >/dev/null 2>&1
    git -C "$repo_dir" remote add origin "$remote_dir"
    git -C "$repo_dir" push -u origin master >/dev/null 2>&1

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "repo view codeforester/base-demo --json defaultBranchRef --jq .defaultBranchRef.name" ]]; then
    printf 'master\n'
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
body_file=""
while (($#)); do
    if [[ "$1" == "--body-file" ]]; then
        body_file="$2"
        break
    fi
    shift
done
[[ -n "$body_file" ]] && cat "$body_file" > "${BASE_REPO_TEST_STATE_DIR:?}/pr-body"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --pr

    [ "$status" -eq 0 ]
    [ "$(git -C "$repo_dir" branch --show-current)" = "base/repo-baseline-base-demo" ]
    [ "$(git -C "$repo_dir" log -1 --pretty=%s)" = "Add Base repository baseline" ]
    git --git-dir="$remote_dir" show-ref --verify --quiet refs/heads/base/repo-baseline-base-demo
    commit_files="$(git -C "$repo_dir" show --name-only --pretty=format: HEAD)"
    [[ "$commit_files" == *"VERSION"* ]]
    [[ "$commit_files" == *"base_manifest.yaml"* ]]
    [[ "$commit_files" != *"src/app.txt"* ]]
    grep -Fq "pr create --repo codeforester/base-demo --base master --head base/repo-baseline-base-demo --title Add Base repository baseline --body-file" "$TEST_STATE_DIR/gh-args"
    ! grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    grep -Fq "Add Base-managed repository baseline files." "$TEST_STATE_DIR/pr-body"
    grep -Fq "basectl repo init base-demo --path" "$TEST_STATE_DIR/pr-body"
}

@test "basectl repo init --pr requires a clean target worktree" {
    local repo_dir="$TEST_TMPDIR/dirty-demo"

    init_git_repo "$repo_dir"
    printf '# Dirty demo\n' > "$repo_dir/README.md"
    commit_all "$repo_dir" "Initial commit"
    printf 'draft\n' > "$repo_dir/notes.txt"

    run_basectl repo init dirty-demo --path "$repo_dir" --repo codeforester/dirty-demo --pr

    [ "$status" -eq 1 ]
    [[ "$output" == *"repo init --pr requires a clean Git worktree"* ]]
    [ ! -f "$repo_dir/base_manifest.yaml" ]
}

@test "basectl repo init can create a public GitHub repo when requested" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "repo view codeforester/base-demo" ]]; then
    exit 1
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --public

    [ "$status" -eq 0 ]
    grep -Fq "repo create codeforester/base-demo --public --description Base-managed project base-demo." "$TEST_STATE_DIR/gh-args"
}

@test "basectl repo init rejects conflicting GitHub repo visibility flags" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --private --public

    [ "$status" -eq 2 ]
    [[ "$output" == *"Options '--private' and '--public' cannot be used together."* ]]
    [ ! -e "$repo_dir" ]
}

@test "basectl repo configure can infer GitHub repo from origin remote" {
    local repo_dir="$TEST_TMPDIR/repo"

    init_git_repo "$repo_dir"
    git -C "$repo_dir" remote add origin git@github.com:codeforester/base-demo.git

    run_basectl repo configure "$repo_dir" --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"gh repo edit codeforester/base-demo"* ]]
}
