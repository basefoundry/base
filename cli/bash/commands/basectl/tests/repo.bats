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
    [[ "$output" == *"Run 'basectl repo <command> --help' for command-specific options."* ]]
    [[ "$output" != *"--no-protect-default-branch"* ]]
    [[ "$output" != *"--copy-project-fields-from"* ]]
    [[ "$output" != *"--repo-name <name>"* ]]
}

@test "basectl repo init prints command-specific help" {
    run_basectl repo init --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo init <name> [options]"* ]]
    [[ "$output" == *"--path <path>"* ]]
    [[ "$output" == *"--pr"* ]]
    [[ "$output" == *"--copy-project-fields-from <title>"* ]]
    [[ "$output" == *"basectl repo init bankbuddy --path . --repo codeforester/bankbuddy --pr"* ]]
    [[ "$output" != *"basectl repo agent-guidance"* ]]
    [[ "$output" != *"--repo-name <name>"* ]]
    [[ "$output" != *"--agent-guidance"* ]]
}

@test "basectl repo configure prints command-specific help" {
    run_basectl repo configure --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo configure [path] [options]"* ]]
    [[ "$output" == *"--repo <owner/name>"* ]]
    [[ "$output" == *"--no-protect-default-branch"* ]]
    [[ "$output" == *"--copy-project-fields-from <title>"* ]]
    [[ "$output" != *"--pr                          "* ]]
    [[ "$output" != *"--private"* ]]
    [[ "$output" != *"--public"* ]]
    [[ "$output" != *"--description <text>"* ]]
}

@test "basectl repo check prints command-specific help" {
    run_basectl repo check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo check [path] [options]"* ]]
    [[ "$output" == *"--agent-guidance"* ]]
    [[ "$output" != *"--repo <owner/name>"* ]]
    [[ "$output" != *"--pr"* ]]
}

@test "basectl repo installer-template prints command-specific help" {
    run_basectl repo installer-template --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo installer-template [path] [options]"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" != *"--repo <owner/name>"* ]]
    [[ "$output" != *"--project <title>"* ]]
}

@test "basectl repo init missing name shows focused usage and example" {
    run_basectl repo init --repo codeforester/bankbuddy --pr

    [ "$status" -eq 2 ]
    [[ "$output" == *"basectl repo init <name> [options]"* ]]
    [[ "$output" == *"basectl repo init bankbuddy --path . --repo codeforester/bankbuddy --pr"* ]]
    [[ "$output" == *"ERROR: Repository name is required."* ]]
    [[ "$output" != *"basectl repo agent-guidance"* ]]
    [[ "$output" != *"--repo-name <name>"* ]]
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

@test "basectl repo installer-template reports non-dry-run creation" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo installer-template "$repo_dir/install.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Created executable '$repo_dir/install.sh'."* ]]
    [[ "$output" == *"Run git -C '$repo_dir' status --short to review changes."* ]]
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

@test "basectl repo agent-guidance reports non-dry-run creation" {
    local repo_dir="$TEST_TMPDIR/agent-demo"

    run_basectl repo agent-guidance "$repo_dir" --repo-name base-demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"Created '$repo_dir/AGENTS.md'."* ]]
    [[ "$output" == *"Created '$repo_dir/skills.md'."* ]]
    [[ "$output" == *"Created '$repo_dir/.github/pull_request_template.md'."* ]]
    [[ "$output" == *"Run git -C '$repo_dir' status --short to review changes."* ]]
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
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/.github/base-project.yml'."* ]]
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
    [ -f "$repo_dir/.github/base-project.yml" ]
    [ -f "$repo_dir/LICENSE" ]
    [ -f "$repo_dir/.gitignore" ]
    [ -f "$repo_dir/base_manifest.yaml" ]
    [ -x "$repo_dir/tests/validate.sh" ]
    [ -f "$repo_dir/.github/workflows/tests.yml" ]
    [ -f "$repo_dir/.github/workflows/project-intake.yml" ]
    grep -Fqx "0.1.0" "$repo_dir/VERSION"
    grep -Fq "name: base-demo" "$repo_dir/base_manifest.yaml"
    grep -Fq "command: ./tests/validate.sh" "$repo_dir/base_manifest.yaml"
    grep -Fq "issue_defaults:" "$repo_dir/.github/base-project.yml"
    grep -Fq "status: Backlog" "$repo_dir/.github/base-project.yml"
    grep -Fq "priority: P2" "$repo_dir/.github/base-project.yml"
    grep -Fq "area: Product" "$repo_dir/.github/base-project.yml"
    grep -Fq "initiative: Adoption Polish" "$repo_dir/.github/base-project.yml"
    grep -Fq "size: S" "$repo_dir/.github/base-project.yml"
    grep -Fq "name: Project Intake" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_TOKEN" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "gh project item-add" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "set_single_select_if_missing Priority priority" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_DEFAULT_AREA: Product" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_DEFAULT_INITIATIVE: Adoption Polish" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "<category>/<issue>-<YYYYMMDD>-<slug>" "$repo_dir/CONTRIBUTING.md"
    grep -Fq "git worktree add -b <branch> ../base-demo-worktrees/<slug> origin/<default-branch>" "$repo_dir/CONTRIBUTING.md"
    grep -Fq 'Update `CHANGELOG.md` only for notable user-visible or release-worthy' "$repo_dir/CONTRIBUTING.md"
    grep -Fq "## Checklist" "$repo_dir/.github/pull_request_template.md"
    grep -Fq "CHANGELOG is updated for notable user-visible or release-worthy changes." "$repo_dir/.github/pull_request_template.md"
    ! grep -Fq "Demo Impact" "$repo_dir/.github/pull_request_template.md"
    grep -Fq "GNU Affero General Public License" "$repo_dir/LICENSE"
    run grep -F "Base - a workspace control plane" "$repo_dir/LICENSE"
    [ "$status" -eq 1 ]

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
    grep -Fq "Copyright (C) $(date +%Y) Ada Lovelace" "$repo_dir/LICENSE"
    grep -Fq "GNU Affero General Public License as published by" "$repo_dir/LICENSE"
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
    grep -Fq "Copyright (C) $(date +%Y) $username" "$repo_dir/LICENSE"
    grep -Fq "GNU Affero General Public License as published by" "$repo_dir/LICENSE"
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

@test "basectl repo configure dry-run protects the default branch by default" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" --repo codeforester/base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Base default branch protection"* ]]
    [[ "$output" == *"~DEFAULT_BRANCH"* ]]
    [[ "$output" == *"gh api repos/codeforester/base-demo/rulesets"* ]]
    [[ "$output" == *'"type":"pull_request"'* ]]
    [[ "$output" == *'"type":"deletion"'* ]]
    [[ "$output" == *'"type":"non_fast_forward"'* ]]
}

@test "basectl repo configure can skip default branch protection" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" \
        --repo codeforester/base-demo \
        --no-protect-default-branch \
        --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"gh repo edit codeforester/base-demo"* ]]
    [[ "$output" != *"Base default branch protection"* ]]
    [[ "$output" != *"rulesets"* ]]
}

@test "basectl repo configure dry-run configures project metadata by default" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" --repo codeforester/base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would configure GitHub Project 'base-demo' for 'codeforester/base-demo'."* ]]
    [[ "$output" == *"Would copy GitHub Project 'base-project-template' to 'base-demo' if missing."* ]]
    [[ "$output" == *"Would link GitHub Project 'base-demo' to repository 'codeforester/base-demo'."* ]]
    [[ "$output" == *"Would backfill issues from 'codeforester/base-demo' into GitHub Project 'base-demo'."* ]]
    [[ "$output" == *"--schema base-roadmap"* ]]
    [[ "$output" == *"Status, Priority, Area, Size, Initiative"* ]]
}

@test "basectl repo configure dry-run passes repo project config when present" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir/.github"
    cat > "$repo_dir/.github/base-project.yml" <<'EOF'
project:
  areas:
    - Demo App
  initiatives:
    - Repo Dashboard
EOF

    run_basectl repo configure "$repo_dir" --repo codeforester/base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would read GitHub Project config from '$repo_dir/.github/base-project.yml'."* ]]
    [[ "$output" == *"Would apply issue defaults from '$repo_dir/.github/base-project.yml' to missing Project item fields."* ]]
    [[ "$output" == *"--config $repo_dir/.github/base-project.yml"* ]]
}

@test "basectl repo configure dry-run reports missing project intake workflow" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir/.github"
    cat > "$repo_dir/.github/base-project.yml" <<'EOF'
project:
  issue_defaults:
    status: Backlog
    priority: P2
    size: S
EOF

    run_basectl repo configure "$repo_dir" --repo codeforester/base-demo --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/.github/workflows/project-intake.yml'."* ]]
    [ ! -e "$repo_dir/.github/workflows/project-intake.yml" ]
}

@test "basectl repo configure can skip project metadata" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" \
        --repo codeforester/base-demo \
        --no-project \
        --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"gh repo edit codeforester/base-demo"* ]]
    [[ "$output" != *"GitHub Project"* ]]
    [[ "$output" != *"base_github_projects"* ]]
}

@test "basectl repo configure accepts project metadata overrides" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" \
        --repo codeforester/bankbuddy \
        --project "BankBuddy Roadmap" \
        --project-owner codeforester \
        --initiative-option MVP \
        --initiative-option Imports \
        --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would configure GitHub Project 'BankBuddy Roadmap' for 'codeforester/bankbuddy'."* ]]
    [[ "$output" == *"--owner codeforester"* ]]
    [[ "$output" == *"--initiative-option MVP"* ]]
    [[ "$output" == *"--initiative-option Imports"* ]]
}

@test "basectl repo configure can copy project fields from a source project" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" \
        --repo codeforester/base \
        --copy-project-fields-from "Base Roadmap" \
        --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would copy missing Project item field values from 'Base Roadmap' into 'base'."* ]]
    [[ "$output" == *'--copy-fields-from "Base Roadmap"'* ]]
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
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    grep -Fq "label create bug --repo codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    grep -Fq "label create needs-demo --repo codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
}

@test "basectl repo configure applies project metadata through Base project engine" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir/.github"
    cat > "$repo_dir/.github/base-project.yml" <<'EOF'
project:
  areas:
    - Demo App
EOF
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" ]]; then
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_REPO_TEST_STATE_DIR:?}/project-args"
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_REPO_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" \
            --repo codeforester/base-demo \
            --copy-project-fields-from "Base Roadmap"

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/.github/workflows/project-intake.yml" ]
    grep -Fq "name: Project Intake" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_TOKEN" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    [[ "$output" == *"Configuring GitHub Project 'base-demo' for 'codeforester/base-demo'."* ]]
    [[ "$output" == *"Running: $TEST_MOCKBIN/project-wrapper --project base base_github_projects project configure --project base-demo --owner codeforester --repo codeforester/base-demo --schema base-roadmap --config $repo_dir/.github/base-project.yml --copy-fields-from \"Base Roadmap\""* ]]
    [ "$(cat "$TEST_STATE_DIR/project-args")" = "--project base base_github_projects project configure --project base-demo --owner codeforester --repo codeforester/base-demo --schema base-roadmap --config $repo_dir/.github/base-project.yml --copy-fields-from Base Roadmap" ]
}

@test "basectl repo configure warns when project metadata needs GitHub project scope" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" ]]; then
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf 'gh auth refresh -h github.com -s project\n' >&2
exit 3
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_REPO_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"GitHub Project metadata skipped for 'codeforester/base-demo'."* ]]
    [[ "$output" == *"gh auth refresh -h github.com -s project"* ]]
}

@test "basectl repo configure updates an existing Base ruleset" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" ]]; then
    printf '%s\n' "api-list $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    printf '%s\n' "42"
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets/42" ]]; then
    printf '%s\n' "api-update $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    cat > "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payload"
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    grep -Fq "api-list api repos/codeforester/base-demo/rulesets" "$TEST_STATE_DIR/gh-args"
    grep -Fq "api-update api repos/codeforester/base-demo/rulesets/42 --method PUT" "$TEST_STATE_DIR/gh-args"
    grep -Fq '"name":"Base default branch protection"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"include":["~DEFAULT_BRANCH"]' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"pull_request"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"deletion"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"non_fast_forward"' "$TEST_STATE_DIR/ruleset-payload"
}

@test "basectl repo configure creates a missing Base ruleset" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" != *"--method POST"* ]]; then
    printf '%s\n' "api-list $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" == *"--method POST"* ]]; then
    printf '%s\n' "api-create $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    cat > "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payload"
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    grep -Fq "api-list api repos/codeforester/base-demo/rulesets" "$TEST_STATE_DIR/gh-args"
    grep -Fq "api-create api repos/codeforester/base-demo/rulesets --method POST" "$TEST_STATE_DIR/gh-args"
    grep -Fq '"name":"Base default branch protection"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"include":["~DEFAULT_BRANCH"]' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"pull_request"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"deletion"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"non_fast_forward"' "$TEST_STATE_DIR/ruleset-payload"
}

@test "basectl repo configure warns when GitHub plan blocks rulesets" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" ]]; then
    printf '%s\n' "api-list $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    printf '%s\n' "gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403)" >&2
    exit 1
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    grep -Fq "api-list api repos/codeforester/base-demo/rulesets" "$TEST_STATE_DIR/gh-args"
    [[ "$output" == *"Default branch protection skipped"* ]]
    [[ "$output" == *"GitHub Pro"* ]]
    [[ "$output" == *"make this repository public"* ]]
}

@test "basectl repo configure fails for unexpected ruleset lookup errors" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" ]]; then
    printf '%s\n' "api-list $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    printf '%s\n' "gh: API rate limit exceeded. (HTTP 403)" >&2
    exit 1
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 1 ]
    grep -Fq "api-list api repos/codeforester/base-demo/rulesets" "$TEST_STATE_DIR/gh-args"
    [[ "$output" == *"Unable to inspect GitHub rulesets for 'codeforester/base-demo'."* ]]
    [[ "$output" != *"Default branch protection skipped"* ]]
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
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_REPO_TEST_STATE_DIR:?}/project-args"
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_REPO_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo --path "$repo_dir" --repo codeforester/base-demo

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/base_manifest.yaml" ]
    grep -Fq "repo create codeforester/base-demo --private --description Base-managed project base-demo." "$TEST_STATE_DIR/gh-args"
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    [ "$(cat "$TEST_STATE_DIR/project-args")" = "--project base base_github_projects project configure --project base-demo --owner codeforester --repo codeforester/base-demo --schema base-roadmap --config $repo_dir/.github/base-project.yml" ]
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
    [[ "$commit_files" == *".github/base-project.yml"* ]]
    [[ "$commit_files" == *"base_manifest.yaml"* ]]
    [[ "$commit_files" != *"src/app.txt"* ]]
    grep -Fq "pr create --repo codeforester/base-demo --base master --head base/repo-baseline-base-demo --title Add Base repository baseline --body-file" "$TEST_STATE_DIR/gh-args"
    ! grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    grep -Fq "Add Base-managed repository baseline files." "$TEST_STATE_DIR/pr-body"
    grep -Fq "basectl repo init base-demo --path" "$TEST_STATE_DIR/pr-body"
}

@test "basectl repo init --pr configures GitHub when baseline has no changes" {
    local remote_dir="$TEST_TMPDIR/origin.git"
    local repo_dir="$TEST_TMPDIR/base-demo"

    init_git_repo "$repo_dir"
    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]
    commit_all "$repo_dir" "Add Base baseline"
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
if [[ "$1" == "api" ]]; then
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_REPO_TEST_STATE_DIR:?}/project-args"
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_REPO_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        PATH="$TEST_MOCKBIN:$PATH" \
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo \
            --path "$repo_dir" \
            --repo codeforester/base-demo \
            --pr \
            --copy-project-fields-from "Base Roadmap"

    [ "$status" -eq 0 ]
    [[ "$output" == *"No repository baseline changes to commit; continuing with GitHub repository configuration."* ]]
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    ! grep -Fq "pr create" "$TEST_STATE_DIR/gh-args"
    [ "$(cat "$TEST_STATE_DIR/project-args")" = "--project base base_github_projects project configure --project base-demo --owner codeforester --repo codeforester/base-demo --schema base-roadmap --config $repo_dir/.github/base-project.yml --copy-fields-from Base Roadmap" ]
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
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --public --no-project

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
