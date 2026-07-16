#!/usr/bin/env bats

load ./basectl_helpers.bash

line_at() {
    local text="$1"
    local line_number="$2"

    printf '%s\n' "$text" | sed -n "${line_number}p"
}

current_branch_date() {
    local branch_date

    printf -v branch_date '%(%Y%m%d)T' -1
    printf '%s\n' "$branch_date"
}

write_repo_configure_gh_recorder() {
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$*" == "repo view codeforester/base-demo" && "${BASE_REPO_TEST_REPO_VIEW_MISSING:-}" == "1" ]]; then
    exit 1
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '%s\n' '{"workflow_runs":[{"id":77,"head_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","updated_at":"2999-01-01T00:00:00Z","head_branch":"main","event":"workflow_dispatch","path":".github/workflows/issue-branch-policy.yml","html_url":"https://github.com/codeforester/base-demo/actions/runs/77","head_repository":{"full_name":"codeforester/base-demo"}}]}'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "--paginate" && "$3" == "--slurp" && "$4" == "repos/codeforester/base-demo/commits/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/statuses?per_page=100" ]]; then
    printf '%s\n' '[[{"context":"base/issue-branch-policy","state":"success","description":"Issue branch policy workflow is ready","target_url":"https://github.com/codeforester/base-demo/actions/runs/77","creator":{"login":"github-actions[bot]"}}]]'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "/apps/github-actions" ]]; then
    printf '15368\n'
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
EOF
    chmod +x "$TEST_MOCKBIN/gh"
}

write_project_installer_template_mocks() {
    local real_bash="$1"
    local installer_body="$2"

    cat > "$TEST_MOCKBIN/curl" <<EOF
#!$real_bash
output=""
while ((\$#)); do
    case "\$1" in
        -o)
            output="\$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
[[ -n "\$output" ]] || exit 1
cat > "\$output" <<'INSTALLER'
$installer_body
INSTALLER
EOF
    chmod +x "$TEST_MOCKBIN/curl"

    cat > "$TEST_MOCKBIN/git" <<EOF
#!$real_bash
case "\${1:-}" in
    clone)
        target="\${@: -1}"
        mkdir -p "\$target/.git"
        printf 'project:\n  name: demo\nartifacts: []\n' > "\$target/base_manifest.yaml"
        ;;
    *)
        ;;
esac
EOF
    chmod +x "$TEST_MOCKBIN/git"

    cat > "$TEST_MOCKBIN/bash" <<EOF
#!$real_bash
printf 'bash %s\n' "\$*" >> "\${BASE_REPO_TEST_STATE_DIR:?}/bash.log"
base_dir=""
while ((\$#)); do
    case "\$1" in
        --dir)
            base_dir="\$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
[[ -n "\$base_dir" ]] || exit 1
mkdir -p "\$base_dir/.git" "\$base_dir/bin"
cat > "\$base_dir/bin/basectl" <<'BASECTL'
#!$real_bash
printf 'basectl %s\n' "\$*" >> "\${BASE_REPO_TEST_STATE_DIR:?}/basectl.log"
BASECTL
chmod +x "\$base_dir/bin/basectl"
EOF
    chmod +x "$TEST_MOCKBIN/bash"
}

run_repo_command_with_mocks() {
    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        BASE_REPO_TEST_REPO_VIEW_MISSING="${BASE_REPO_TEST_REPO_VIEW_MISSING:-}" \
        BASE_REPO_PROJECT_WRAPPER="${BASE_REPO_PROJECT_WRAPPER:-}" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo "$@"
}

@test "basectl repo imports reusable GitHub CLI helpers" {
    local bash_libs_dir

    bash_libs_dir="$(base_bash_libs_fixture_dir)"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_BASH_LIBS_DIR="$bash_libs_dir" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/repo.sh"
            [[ "$(type -t gh_require_cli)" == "function" ]]
            [[ "$(type -t gh_auth_status_diagnostics)" == "function" ]]
            [[ "$(type -t gh_run)" == "function" ]]
            [[ "$(type -t gh_infer_repo_from_origin)" == "function" ]]
            [[ "$(type -t git_detect_default_branch)" == "function" ]]
            [[ "$(type -t gh_repo_default_branch)" == "function" ]]
        '

    [ "$status" -eq 0 ]
}

@test "basectl repo GitHub helpers delegate to reusable gh helpers" {
    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/repo.sh"
            base_repo_require_gh() {
                return 0
            }
            gh_infer_repo_from_origin() {
                printf -v "$2" "%s" "owner/repo"
            }
            git_detect_default_branch() {
                printf -v "$2" "%s" "develop"
            }
            gh_repo_default_branch() {
                printf -v "$2" "%s" "trunk"
            }
            printf "repo=%s\n" "$(base_repo_infer_github_repo /tmp/repo)"
            printf "detected=%s\n" "$(base_repo_detect_default_branch /tmp/repo)"
            printf "remote=%s\n" "$(base_repo_default_branch_for_pr owner/repo)"
        '

    [ "$status" -eq 0 ]
    [[ "$output" == *"repo=owner/repo"* ]]
    [[ "$output" == *"detected=develop"* ]]
    [[ "$output" == *"remote=trunk"* ]]
}

@test "basectl repo prints help" {
    run_basectl repo --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo init <name>"* ]]
    [[ "$output" == *"basectl repo clone <name-or-owner/name>"* ]]
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
    [[ "$output" == *"--agent-ready"* ]]
    [[ "$output" == *"--language <csv>"* ]]
    [[ "$output" == *"--issue <number>"* ]]
    [[ "$output" == *"--category <name>"* ]]
    [[ "$output" == *"--pr"* ]]
    [[ "$output" == *"--release"* ]]
    [[ "$output" == *"--copy-project-fields-from <title>"* ]]
    [[ "$output" == *"Create a new public GitHub repo and configure it."* ]]
    [[ "$output" == *"basectl repo init base-demo --repo basefoundry/base-demo --public"* ]]
    [[ "$output" == *"Add or refresh the Base baseline in an existing checkout."* ]]
    [[ "$output" == *"basectl repo init bankbuddy --path . --repo codeforester/bankbuddy --issue 123 --category enhancement --pr"* ]]
    [[ "$output" == *"basectl repo init platform --language go,javascript --language typescript"* ]]
    [[ "$output" == *"For the current checkout, pass its repository name and --path ."* ]]
    [[ "$output" == *"Plain repo init writes local baseline files but does not commit or push them."* ]]
    [[ "$output" == *"With --pr, repo init requires --issue, commits baseline changes on the canonical"* ]]
    [[ "$output" == *"Safe to run against an existing repository"* ]]
    [[ "$output" == *"Safe to re-run: Base-managed settings are created or updated"* ]]
    [[ "$output" == *"creates it using --private/--public"* ]]
    [[ "$output" != *"--public --pr"* ]]
    [[ "$output" != *"basectl repo agent-guidance"* ]]
    [[ "$output" != *"--repo-name <name>"* ]]
    [[ "$output" != *"--agent-guidance"* ]]
}

@test "basectl repo clone prints command-specific help" {
    run_basectl repo clone --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo clone <name-or-owner/name> [options]"* ]]
    [[ "$output" == *"--owner <owner>"* ]]
    [[ "$output" == *"--path <path>"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" == *"basectl repo clone basefoundry/base --path ~/work/base"* ]]
    [[ "$output" != *"--copy-project-fields-from <title>"* ]]
}

@test "basectl repo clone dry-run resolves short names from user config" {
    local nested_dir="$TEST_TMPDIR/nested/current"
    local workspace_root="$TEST_TMPDIR/workspace-root"
    local repo_dir="$workspace_root/base-demo"

    mkdir -p "$TEST_HOME/.base.d" "$nested_dir" "$workspace_root"
    cat > "$TEST_HOME/.base.d/config.yaml" <<EOF
workspace:
  root: $workspace_root
github:
  default_owner: codeforester
  clone_protocol: ssh
EOF

    cd "$nested_dir"
    run_basectl repo clone base-demo --dry-run

    [ "$status" -eq 0 ]
    [ "$(line_at "$output" 1)" = "[DRY-RUN] Would clone codeforester/base-demo (git@github.com:codeforester/base-demo.git) into $repo_dir." ]
    [ "$(line_at "$output" 2)" = "[DRY-RUN] Would run: gh repo clone codeforester/base-demo $repo_dir" ]
    [[ "$output" != *"Repository:"* ]]
    [[ "$output" != *"Destination:"* ]]
    [[ "$output" != *"Tool:"* ]]
    [[ "$output" != *"Clone URL:"* ]]
    [ ! -e "$repo_dir" ]
}

@test "basectl repo clone trims user config values before applying them" {
    local nested_dir="$TEST_TMPDIR/nested/current"
    local workspace_root="$TEST_TMPDIR/workspace-root"
    local repo_dir="$workspace_root/base-demo"

    mkdir -p "$TEST_HOME/.base.d" "$nested_dir" "$workspace_root"
    cat > "$TEST_HOME/.base.d/config.yaml" <<EOF
workspace:
  root:   $workspace_root   # local workspace
github:
  default_owner:   codeforester   # repo owner
  clone_protocol:   ssh
EOF

    cd "$nested_dir"
    run_basectl repo clone base-demo --dry-run

    [ "$status" -eq 0 ]
    [ "$(line_at "$output" 1)" = "[DRY-RUN] Would clone codeforester/base-demo (git@github.com:codeforester/base-demo.git) into $repo_dir." ]
    [ "$(line_at "$output" 2)" = "[DRY-RUN] Would run: gh repo clone codeforester/base-demo $repo_dir" ]
}

@test "basectl repo clone supports explicit owner and path dry-run" {
    local repo_dir="$TEST_HOME/work/base-demo"

    run_basectl repo clone base-demo --owner codeforester --path "~/work/base-demo" --dry-run

    [ "$status" -eq 0 ]
    [ "$(line_at "$output" 1)" = "[DRY-RUN] Would clone codeforester/base-demo (git@github.com:codeforester/base-demo.git) into $repo_dir." ]
    [ "$(line_at "$output" 2)" = "[DRY-RUN] Would run: gh repo clone codeforester/base-demo $repo_dir" ]
    [ ! -e "$repo_dir" ]
}

@test "basectl repo clone supports explicit owner slash repo and https clone protocol" {
    local repo_dir="$TEST_TMPDIR/custom/bankbuddy"

    mkdir -p "$TEST_HOME/.base.d"
    cat > "$TEST_HOME/.base.d/config.yaml" <<'EOF'
github:
  default_owner: ignored
  clone_protocol: https
EOF

    run_basectl repo clone codeforester/bankbuddy --path "$repo_dir" --dry-run

    [ "$status" -eq 0 ]
    [ "$(line_at "$output" 1)" = "[DRY-RUN] Would clone codeforester/bankbuddy (https://github.com/codeforester/bankbuddy.git) into $repo_dir." ]
    [ "$(line_at "$output" 2)" = "[DRY-RUN] Would run: gh repo clone codeforester/bankbuddy $repo_dir" ]
}

@test "basectl repo clone requires an owner for short names" {
    run_basectl repo clone base-demo --dry-run

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: Repository owner is required for short repo names. Pass --owner <owner> or set github.default_owner in ~/.base.d/config.yaml." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl repo clone --help' for usage." ]
    [[ "$output" != *"Usage:"* ]]
    [[ "$output" != *"basectl repo clone <name-or-owner/name> [options]"* ]]
}

@test "basectl repo clone treats existing matching checkouts as satisfied" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    init_git_repo "$repo_dir"
    git -C "$repo_dir" remote add origin git@github.com:codeforester/base-demo.git

    run_basectl repo clone codeforester/base-demo --path "$repo_dir"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository 'codeforester/base-demo' already exists at '$repo_dir'."* ]]
    [[ "$output" == *"To update: git -C $repo_dir pull --ff-only"* ]]
    [[ "$output" != *"gh repo clone"* ]]

    git -C "$repo_dir" remote set-url origin git@github.com:codeforester/base-demo

    run_basectl repo clone codeforester/base-demo --path "$repo_dir"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository 'codeforester/base-demo' already exists at '$repo_dir'."* ]]
    [[ "$output" == *"To update: git -C $repo_dir pull --ff-only"* ]]
}

@test "basectl repo clone rejects conflicting existing checkouts" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    init_git_repo "$repo_dir"
    git -C "$repo_dir" remote add origin git@github.com:other/base-demo.git

    run_basectl repo clone codeforester/base-demo --path "$repo_dir"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Destination '$repo_dir' already points at GitHub repository 'other/base-demo'."* ]]
    [[ "$output" == *"Expected 'codeforester/base-demo'."* ]]
}

@test "basectl repo clone rejects existing non-git destinations" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    mkdir -p "$repo_dir"

    run_basectl repo clone codeforester/base-demo --path "$repo_dir"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Destination '$repo_dir' already exists but is not a matching Git checkout."* ]]
}

@test "basectl repo clone delegates to gh repo clone without Base baseline hint" {
    local repo_dir="$TEST_TMPDIR/workspace/base-demo"

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
if [[ "$1" == "repo" && "$2" == "clone" ]]; then
    mkdir -p "$4/.git"
    exit 0
fi
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo clone codeforester/base-demo --path "$repo_dir"

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "repo clone codeforester/base-demo $repo_dir" ]
    [[ "$output" == *"Cloning GitHub repository 'codeforester/base-demo' into '$repo_dir'."* ]]
    [[ "$output" == *"Cloned 'codeforester/base-demo' to '$repo_dir'."* ]]
    [[ "$output" != *"Base baseline"* ]]
    [[ "$output" != *"basectl repo check"* ]]
}

@test "basectl repo clone prints Base baseline hint for Base-managed repos" {
    local repo_dir="$TEST_TMPDIR/workspace/base-demo"

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
if [[ "$1" == "repo" && "$2" == "clone" ]]; then
    mkdir -p "$4/.git"
    touch "$4/base_manifest.yaml"
    exit 0
fi
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo clone codeforester/base-demo --path "$repo_dir"

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/gh-args")" = "repo clone codeforester/base-demo $repo_dir" ]
    [[ "$output" == *"Cloned 'codeforester/base-demo' to '$repo_dir'."* ]]
    [[ "$output" == *"Run 'basectl repo check $repo_dir' to verify the Base baseline."* ]]
}

@test "basectl repo configure prints command-specific help" {
    run_basectl repo configure --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo configure [path] [options]"* ]]
    [[ "$output" == *"--repo <owner/name>"* ]]
    [[ "$output" == *"--no-protect-default-branch"* ]]
    [[ "$output" == *"--copy-project-fields-from <title>"* ]]
    [[ "$output" == *"--replace-project"* ]]
    [[ "$output" == *"--release"* ]]
    [[ "$output" == *"basectl repo configure . --repo codeforester/bankbuddy"* ]]
    [[ "$output" == *"applies or repairs GitHub-side repository settings"* ]]
    [[ "$output" == *"Safe to re-run: Base-managed settings are created or updated"* ]]
    [[ "$output" == *"after a repo init --pr baseline PR is merged"* ]]
    [[ "$output" == *"It does not create the full local baseline"* ]]
    [[ "$output" != *"--pr                          "* ]]
    [[ "$output" != *"--private"* ]]
    [[ "$output" != *"--public"* ]]
    [[ "$output" != *"--description <text>"* ]]
}

@test "basectl repo init release profile writes the contract and process guide" {
    local repo_dir="$TEST_TMPDIR/release-profile"

    run_basectl repo init release-profile \
        --path "$repo_dir" \
        --repo codeforester/release-profile \
        --release \
        --no-configure

    [ "$status" -eq 0 ]
    grep -Fqx "release:" "$repo_dir/base_manifest.yaml"
    grep -Fqx "    repository: codeforester/release-profile" "$repo_dir/base_manifest.yaml"
    grep -Fq "basectl release check --version X.Y.Z" "$repo_dir/docs/release-process.md"
    grep -Fq "Homebrew" "$repo_dir/docs/release-process.md"

    run_basectl repo check "$repo_dir" --release

    [ "$status" -eq 0 ]
    [[ "$output" == *"Release contract: present."* ]]
}

@test "basectl repo configure release dry-run preserves a missing contract" {
    local repo_dir="$TEST_TMPDIR/release-configure-dry-run"

    run_basectl repo init release-configure-dry-run \
        --path "$repo_dir" \
        --repo codeforester/release-configure-dry-run \
        --no-configure

    [ "$status" -eq 0 ]

    run_basectl repo configure "$repo_dir" \
        --repo codeforester/release-configure-dry-run \
        --release \
        --no-project \
        --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would append the generic release contract"* ]]
    [[ "$output" == *"Would create '$repo_dir/docs/release-process.md'"* ]]
    ! grep -Fq "release:" "$repo_dir/base_manifest.yaml"
    [ ! -e "$repo_dir/docs/release-process.md" ]
}

@test "basectl repo check prints command-specific help" {
    run_basectl repo check --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo check [path] [options]"* ]]
    [[ "$output" == *"--agent-guidance"* ]]
    [[ "$output" == *"--agent-ready"* ]]
    [[ "$output" != *"--repo <owner/name>"* ]]
    [[ "$output" != *"--pr"* ]]
}

@test "basectl repo installer-template prints command-specific help" {
    run_basectl repo installer-template --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo installer-template [path] [options]"* ]]
    [[ "$output" == *"--print, --stdout"* ]]
    [[ "$output" == *"--repo <owner/name>"* ]]
    [[ "$output" == *"--issue <number>"* ]]
    [[ "$output" == *"--category <name>"* ]]
    [[ "$output" == *"--pr"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" == *"to ./install.sh"* ]]
    [[ "$output" == *"when path is omitted"* ]]
    [[ "$output" != *"--project <title>"* ]]
}

@test "basectl repo installer-template implementation is split from repo dispatcher" {
    local dispatcher="$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo.sh"
    local helper="$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo_installer_template.sh"

    [ -f "$helper" ]
    grep -Fq "repo_installer_template.sh" "$dispatcher"
    grep -Eq '^base_repo_installer_template\(\)' "$helper"
    ! grep -Eq '^base_repo_installer_template\(\)' "$dispatcher"
}

@test "repo pull request helpers require an issue number" {
    run_basectl repo init base-demo --path "$TEST_TMPDIR/init-missing-issue" --repo codeforester/base-demo --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--pr' requires --issue <positive integer>."* ]]

    run_basectl repo agent-guidance "$TEST_TMPDIR/agent-missing-issue" --repo-name base-demo --repo codeforester/base-demo --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--pr' requires --issue <positive integer>."* ]]

    run_basectl repo installer-template "$TEST_TMPDIR/installer-missing-issue/install.sh" --repo codeforester/base-demo --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--pr' requires --issue <positive integer>."* ]]
}

@test "repo pull request helpers reject non-positive issue numbers" {
    run_basectl repo init base-demo --path "$TEST_TMPDIR/init-invalid-issue" --repo codeforester/base-demo --issue 0 --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--issue' must be a positive integer."* ]]

    run_basectl repo agent-guidance "$TEST_TMPDIR/agent-invalid-issue" --repo-name base-demo --repo codeforester/base-demo --issue nope --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--issue' must be a positive integer."* ]]

    run_basectl repo installer-template "$TEST_TMPDIR/installer-invalid-issue/install.sh" --repo codeforester/base-demo --issue -1 --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--issue' must be a positive integer."* ]]
}

@test "repo pull request helper dry-runs require a valid category" {
    run_basectl repo init base-demo --path "$TEST_TMPDIR/init-missing-category" --repo codeforester/base-demo --issue 1 --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Options '--pr --dry-run' require --category <name>."* ]]

    run_basectl repo agent-guidance "$TEST_TMPDIR/agent-invalid-category" --repo-name base-demo --repo codeforester/base-demo --issue 2 --category feat --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--category' must be one of: bug, enhancement, documentation, ci, security."* ]]

    run_basectl repo installer-template "$TEST_TMPDIR/installer-missing-category/install.sh" --repo codeforester/base-demo --issue 3 --pr --dry-run

    [ "$status" -eq 2 ]
    [[ "$output" == *"Options '--pr --dry-run' require --category <name>."* ]]
}

@test "repo pull request helpers reject a category that disagrees with the issue" {
    local repo_dir="$TEST_TMPDIR/category-mismatch"

    init_git_repo "$repo_dir"
    printf '# Existing project\n' > "$repo_dir/README.md"
    commit_all "$repo_dir" "Initial commit"

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/issues/4" ]]; then
    printf 'issue\nenhancement\n'
    exit 0
fi
printf 'unexpected gh args: %s\n' "$*" >&2
exit 99
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        PATH="$TEST_MOCKBIN:$PATH" \
        "$BASE_REPO_ROOT/bin/basectl" repo installer-template "$repo_dir/install.sh" \
            --repo codeforester/base-demo \
            --issue 4 \
            --category documentation \
            --pr

    [ "$status" -eq 2 ]
    [[ "$output" == *"Option '--category documentation' does not match issue #4 category 'enhancement'."* ]]
    [[ "$output" != *"unexpected gh args"* ]]
    [ ! -e "$repo_dir/install.sh" ]
}

@test "basectl repo project-intake workflow is maintained as a template asset" {
    local dispatcher="$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo.sh"
    local template="$BASE_REPO_ROOT/templates/project-intake.yml"

    [ -f "$template" ]
    grep -Fq "templates/project-intake.yml" "$dispatcher"
    grep -Fq "name: Project Intake" "$template"
    grep -Fq "project_intake_gh()" "$template"
    if grep -Fq "project_intake_gh()" "$dispatcher"; then
        fail "repo dispatcher should not embed the Project Intake workflow program"
    fi
}

@test "basectl repo issue branch policy workflow is maintained as a template asset" {
    local dispatcher="$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo.sh"
    local template="$BASE_REPO_ROOT/templates/issue-branch-policy.yml"
    local workflow="$BASE_REPO_ROOT/.github/workflows/issue-branch-policy.yml"

    [ -f "$template" ]
    [ -f "$workflow" ]
    cmp "$template" "$workflow"
    grep -Fq "templates/issue-branch-policy.yml" "$dispatcher"
    grep -Fq "name: Issue Branch Policy" "$template"
    grep -Fq "pull_request_target:" "$template"
    grep -Fq "base/issue-branch-policy" "$template"
    if grep -Fq "publish_status()" "$dispatcher"; then
        fail "repo dispatcher should not embed the Issue Branch Policy workflow program"
    fi
}

@test "basectl repo agent-guidance implementation is split from repo dispatcher" {
    local dispatcher="$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo.sh"
    local helper="$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo_agent_guidance.sh"

    [ -f "$helper" ]
    grep -Fq "repo_agent_guidance.sh" "$dispatcher"
    grep -Eq '^base_repo_agent_guidance\(\)' "$helper"
    if grep -Eq '^base_repo_agent_guidance\(\)' "$dispatcher"; then
        fail "repo dispatcher should not define base_repo_agent_guidance"
    fi
}

@test "basectl repo GitHub settings implementation is split from repo dispatcher" {
    local dispatcher="$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo.sh"
    local helper="$BASE_REPO_ROOT/cli/bash/commands/basectl/subcommands/repo_github_settings.sh"

    [ -f "$helper" ]
    grep -Fq "repo_github_settings.sh" "$dispatcher"
    grep -Eq '^base_repo_configure_github\(\)' "$helper"
    grep -Eq '^base_repo_configure_default_branch_protection\(\)' "$helper"
    grep -Eq '^base_repo_configure_branch_naming\(\)' "$helper"
    grep -Eq '^base_repo_configure_project_metadata\(\)' "$helper"
    if grep -Eq '^base_repo_configure_github\(\)' "$dispatcher"; then
        fail "repo dispatcher should not define base_repo_configure_github"
    fi
    if grep -Eq '^base_repo_default_branch_ruleset_payload\(\)' "$dispatcher"; then
        fail "repo dispatcher should not define Base ruleset payload helpers"
    fi
    if grep -Eq '^base_repo_configure_project_metadata\(\)' "$dispatcher"; then
        fail "repo dispatcher should not define Project metadata delegation"
    fi
}

@test "basectl repo init missing name shows focused usage and example" {
    run_basectl repo init --repo codeforester/bankbuddy --pr

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: Repository name is required." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl repo init --help' for usage." ]
    [[ "$output" != *"Usage:"* ]]
    [[ "$output" != *"basectl repo init <name> [options]"* ]]
    [[ "$output" != *"basectl repo init bankbuddy --path . --repo codeforester/bankbuddy --pr"* ]]
    [[ "$output" != *"basectl repo agent-guidance"* ]]
    [[ "$output" != *"--repo-name <name>"* ]]
}

@test "basectl repo unknown command reports error before help hint" {
    run_basectl repo mystery

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: Unknown repo command 'mystery'." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl repo --help' for usage." ]
    [[ "$output" != *"Usage:"* ]]
    [[ "$output" != *"basectl repo init <name> [options]"* ]]
}

@test "basectl repo agent-guidance missing option argument reports error before help hint" {
    run_basectl repo agent-guidance --repo

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: Option '--repo' requires an argument." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl repo agent-guidance --help' for usage." ]
    [[ "$output" != *"Usage:"* ]]
    [[ "$output" != *"basectl repo agent-guidance [path] [options]"* ]]
}

@test "basectl repo check rejects a second positional path after dot" {
    local current_dir="$TEST_TMPDIR/current"
    local repo_dir="$TEST_TMPDIR/base-demo"

    mkdir -p "$current_dir"
    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]

    cd "$current_dir"
    run_basectl repo check . "$repo_dir"

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: The 'repo check' command accepts at most one path." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl repo check --help' for usage." ]
}

@test "basectl repo configure rejects a second positional path after dot" {
    local current_dir="$TEST_TMPDIR/current"
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$current_dir" "$repo_dir"

    cd "$current_dir"
    run_basectl repo configure . "$repo_dir" --repo codeforester/base-demo --dry-run --no-project

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: The 'repo configure' command accepts at most one path." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl repo configure --help' for usage." ]
}

@test "basectl repo agent-guidance rejects a second positional path after dot" {
    local current_dir="$TEST_TMPDIR/current"
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$current_dir" "$repo_dir"

    cd "$current_dir"
    run_basectl repo agent-guidance . "$repo_dir" --repo-name base-demo --dry-run

    [ "$status" -eq 2 ]
    [ "$(line_at "$output" 1)" = "ERROR: The 'repo agent-guidance' command accepts at most one path." ]
    [ "$(line_at "$output" 2)" = "Run 'basectl repo agent-guidance --help' for usage." ]
}

@test "basectl repo installer-template prints the maintained template" {
    run_basectl repo installer-template --print

    [ "$status" -eq 0 ]
    [[ "$output" == *'PROJECT_NAME="${PROJECT_NAME:-example-project}"'* ]]
    [[ "$output" == *'PROJECT_REPO_URL="${PROJECT_REPO_URL:-https://github.com/example/example-project.git}"'* ]]
    [[ "$output" == *'BASE_INSTALL_SHA256="${BASE_INSTALL_SHA256:-}"'* ]]
    [[ "$output" == *'basectl" setup --manifest "$PROJECT_DIR/base_manifest.yaml" "$PROJECT_NAME"'* ]]
    [[ "$output" == *"Explicit error handling is used instead of set -e"* ]]
    [[ "$output" == *'run git -C "$BASE_DIR" pull --ff-only || die'* ]]
    [[ "$output" != *"set -euo pipefail"* ]]
}

@test "project installer template rejects mismatched Base installer checksum before execution" {
    local real_bash
    local installer_body='printf "installer should not run\n"'

    real_bash="$(command -v bash)"
    write_project_installer_template_mocks "$real_bash" "$installer_body"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_INSTALL_SHA256="0000000000000000000000000000000000000000000000000000000000000000" \
        WORKSPACE_DIR="$TEST_TMPDIR/workspace" \
        PROJECT_NAME="demo" \
        "$real_bash" "$BASE_REPO_ROOT/templates/project-install.sh"

    [ "$status" -ne 0 ]
    [[ "$output" == *"Base installer checksum mismatch"* ]]
    [ ! -f "$TEST_STATE_DIR/bash.log" ]
}

@test "project installer template warns when Base installer checksum is not configured" {
    local real_bash
    local installer_body='printf "installer ok\n"'

    real_bash="$(command -v bash)"
    write_project_installer_template_mocks "$real_bash" "$installer_body"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        WORKSPACE_DIR="$TEST_TMPDIR/workspace" \
        PROJECT_NAME="demo" \
        "$real_bash" "$BASE_REPO_ROOT/templates/project-install.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"WARNING: BASE_INSTALL_SHA256 is empty; downloaded Base installer checksum verification was skipped."* ]]
    [ -f "$TEST_STATE_DIR/bash.log" ]
}

@test "project installer template verifies matching Base installer checksum" {
    local real_bash
    local installer_body='printf "installer ok\n"'
    local checksum

    real_bash="$(command -v bash)"
    checksum="$(printf '%s\n' "$installer_body" | shasum -a 256)"
    checksum="${checksum%% *}"
    write_project_installer_template_mocks "$real_bash" "$installer_body"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        BASE_INSTALL_SHA256="$checksum" \
        WORKSPACE_DIR="$TEST_TMPDIR/workspace" \
        PROJECT_NAME="demo" \
        "$real_bash" "$BASE_REPO_ROOT/templates/project-install.sh"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Verified Base installer SHA-256 $checksum."* ]]
    [ -f "$TEST_STATE_DIR/bash.log" ]
}

@test "basectl repo installer-template writes install.sh by default" {
    local physical_repo_dir
    local repo_dir="$TEST_TMPDIR/default-installer"

    mkdir -p "$repo_dir"
    cd "$repo_dir"
    physical_repo_dir="$(pwd -P)"

    run_basectl repo installer-template

    [ "$status" -eq 0 ]
    [ -x "$repo_dir/install.sh" ]
    grep -Fq 'PROJECT_NAME="${PROJECT_NAME:-example-project}"' "$repo_dir/install.sh"
    [[ "$output" == *"Created executable '$physical_repo_dir/install.sh'."* ]]
    [[ "$output" == *"Run git -C '$physical_repo_dir' status --short to review changes."* ]]
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

@test "basectl repo installer-template --pr dry-run reports branch and pull request plan" {
    local pr_branch="documentation/701-$(current_branch_date)-installer-template-base-demo"
    local repo_dir="$TEST_TMPDIR/installer-pr-demo"

    init_git_repo "$repo_dir"
    git -C "$repo_dir" remote add origin git@github.com:codeforester/base-demo.git

    run_basectl repo installer-template "$repo_dir/install.sh" --issue 701 --category documentation --pr --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create or use branch '$pr_branch' from default branch '<default branch>'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create executable '$repo_dir/install.sh'."* ]]
    [[ "$output" == *"[DRY-RUN] Would commit generated installer template file with message 'Add Base installer template'."* ]]
    [[ "$output" == *"[DRY-RUN] Would push branch '$pr_branch' to origin."* ]]
    [[ "$output" == *"[DRY-RUN] Would open a draft pull request in 'codeforester/base-demo' from '$pr_branch' to '<default branch>' with title 'Add Base installer template'."* ]]
    [ ! -e "$repo_dir/install.sh" ]
}

@test "basectl repo installer-template --pr dry-run defaults to install.sh" {
    local physical_repo_dir
    local pr_branch="security/702-$(current_branch_date)-installer-template-base-demo"
    local repo_dir="$TEST_TMPDIR/installer-pr-default"

    init_git_repo "$repo_dir"
    git -C "$repo_dir" remote add origin git@github.com:codeforester/base-demo.git

    cd "$repo_dir"
    physical_repo_dir="$(pwd -P)"
    run_basectl repo installer-template --issue 702 --category security --pr --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create or use branch '$pr_branch' from default branch '<default branch>'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create executable '$physical_repo_dir/install.sh'."* ]]
    [[ "$output" == *"[DRY-RUN] Would open a draft pull request in 'codeforester/base-demo' from '$pr_branch' to '<default branch>' with title 'Add Base installer template'."* ]]
    [ ! -e "$repo_dir/install.sh" ]
}

@test "basectl repo installer-template --pr opens a draft pull request" {
    local commit_files
    local pr_branch="documentation/703-$(current_branch_date)-installer-template-base-demo"
    local remote_dir="$TEST_TMPDIR/origin.git"
    local repo_dir="$TEST_TMPDIR/installer-pr-demo"

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
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/issues/703" ]]; then
    printf 'issue\ndocumentation\n'
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
        "$BASE_REPO_ROOT/bin/basectl" repo installer-template "$repo_dir/install.sh" \
            --repo codeforester/base-demo \
            --issue 703 \
            --pr

    [ "$status" -eq 0 ]
    [ "$(git -C "$repo_dir" branch --show-current)" = "$pr_branch" ]
    [ "$(git -C "$repo_dir" log -1 --pretty=%s)" = "Add Base installer template" ]
    git --git-dir="$remote_dir" show-ref --verify --quiet "refs/heads/$pr_branch"
    commit_files="$(git -C "$repo_dir" show --name-only --pretty=format: HEAD)"
    [[ "$commit_files" == *"install.sh"* ]]
    [[ "$commit_files" != *"src/app.txt"* ]]
    grep -Fq "pr create --repo codeforester/base-demo --base master --head $pr_branch --title Add Base installer template --draft --body-file" "$TEST_STATE_DIR/gh-args"
    grep -Fq "Add the maintained Base project installer template." "$TEST_STATE_DIR/pr-body"
    grep -Fq "Closes #703" "$TEST_STATE_DIR/pr-body"
    grep -Fq "basectl repo installer-template" "$TEST_STATE_DIR/pr-body"
    grep -Fq -- "--issue 703 --category documentation --pr" "$TEST_STATE_DIR/pr-body"
}

@test "basectl repo installer-template --pr requires a clean target worktree" {
    local physical_repo_dir
    local repo_dir="$TEST_TMPDIR/dirty-installer-demo"

    init_git_repo "$repo_dir"
    printf '# Dirty demo\n' > "$repo_dir/README.md"
    commit_all "$repo_dir" "Initial commit"
    printf 'draft\n' > "$repo_dir/notes.txt"
    physical_repo_dir="$(cd "$repo_dir" && pwd -P)"

    run_basectl repo installer-template "$repo_dir/install.sh" --repo codeforester/dirty-installer-demo --issue 704 --pr

    [ "$status" -eq 1 ]
    [[ "$output" == *"repo installer-template --pr requires a clean Git worktree"* ]]
    [[ "$output" == *"Uncommitted changes detected (1 file)."* ]]
    [[ "$output" == *"?? notes.txt"* ]]
    [[ "$output" == *"Fix: commit or stash your changes before running this command."* ]]
    [[ "$output" == *"git -C $physical_repo_dir status --short"* ]]
    [ ! -f "$repo_dir/install.sh" ]
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
    [[ "$output" == *"Agent guidance: 3 files created."* ]]
    [[ "$output" == *"Created:   AGENTS.md, skills.md, .github/pull_request_template.md"* ]]
    [[ "$output" == *"Run git -C '$repo_dir' status --short to review changes."* ]]
}

@test "basectl repo agent-guidance detects origin default branch" {
    local repo_dir="$TEST_TMPDIR/agent-demo"

    init_git_repo "$repo_dir"
    printf '# Agent demo\n' > "$repo_dir/README.md"
    commit_all "$repo_dir" "Initial commit"
    git -C "$repo_dir" checkout -B trunk >/dev/null 2>&1
    git -C "$repo_dir" update-ref refs/remotes/origin/trunk HEAD
    git -C "$repo_dir" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk

    run_basectl repo agent-guidance "$repo_dir" --repo-name base-demo

    [ "$status" -eq 0 ]
    grep -Fq "git worktree add -b <branch> ../base-demo-worktrees/<slug> origin/trunk" "$repo_dir/AGENTS.md"
    [[ "$output" != *"Could not detect default branch"* ]]
}

@test "basectl repo agent-guidance falls back to main when default branch is unknown" {
    local repo_dir="$TEST_TMPDIR/agent-demo"

    run_basectl repo agent-guidance "$repo_dir" --repo-name base-demo

    [ "$status" -eq 0 ]
    grep -Fq "git worktree add -b <branch> ../base-demo-worktrees/<slug> origin/main" "$repo_dir/AGENTS.md"
    [[ "$output" == *"Note: Could not detect default branch from origin; defaulting to 'main'."* ]]
    [[ "$output" == *"Pass --default-branch <name> to set it explicitly."* ]]
}

@test "basectl repo agent-guidance prints command-specific help" {
    run_basectl repo agent-guidance --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"basectl repo agent-guidance [path] [options]"* ]]
    [[ "$output" == *"--repo <owner/name>"* ]]
    [[ "$output" == *"--issue <number>"* ]]
    [[ "$output" == *"--category <name>"* ]]
    [[ "$output" == *"--repo-name <name>"* ]]
    [[ "$output" == *"--default-branch <name>"* ]]
    [[ "$output" == *"Defaults to detected branch, then main."* ]]
    [[ "$output" == *"--validation-command <cmd>"* ]]
    [[ "$output" == *"--pr"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" != *"--private"* ]]
    [[ "$output" != *"--public"* ]]
}

@test "basectl repo agent-guidance --pr dry-run reports branch and pull request plan" {
    local pr_branch="ci/801-$(current_branch_date)-agent-guidance-base-demo"
    local repo_dir="$TEST_TMPDIR/agent-pr-demo"

    init_git_repo "$repo_dir"
    git -C "$repo_dir" remote add origin git@github.com:codeforester/base-demo.git

    run_basectl repo agent-guidance "$repo_dir" --repo-name base-demo --issue 801 --category ci --pr --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create or use branch '$pr_branch' from default branch '<default branch>'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/AGENTS.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/skills.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/.github/pull_request_template.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would commit generated agent guidance files with message 'Add Base agent guidance'."* ]]
    [[ "$output" == *"[DRY-RUN] Would push branch '$pr_branch' to origin."* ]]
    [[ "$output" == *"[DRY-RUN] Would open a draft pull request in 'codeforester/base-demo' from '$pr_branch' to '<default branch>' with title 'Add Base agent guidance'."* ]]
    [ ! -e "$repo_dir/AGENTS.md" ]
}

@test "basectl repo agent-guidance --pr opens a draft pull request" {
    local commit_files
    local pr_branch="ci/802-$(current_branch_date)-agent-guidance-base-demo"
    local remote_dir="$TEST_TMPDIR/origin.git"
    local repo_dir="$TEST_TMPDIR/agent-pr-demo"

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
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/issues/802" ]]; then
    printf 'issue\nci\n'
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
        "$BASE_REPO_ROOT/bin/basectl" repo agent-guidance "$repo_dir" \
            --repo-name base-demo \
            --default-branch master \
            --validation-command "./tests/validate.sh" \
            --repo codeforester/base-demo \
            --issue 802 \
            --pr

    [ "$status" -eq 0 ]
    [ "$(git -C "$repo_dir" branch --show-current)" = "$pr_branch" ]
    [ "$(git -C "$repo_dir" log -1 --pretty=%s)" = "Add Base agent guidance" ]
    git --git-dir="$remote_dir" show-ref --verify --quiet "refs/heads/$pr_branch"
    commit_files="$(git -C "$repo_dir" show --name-only --pretty=format: HEAD)"
    [[ "$commit_files" == *"AGENTS.md"* ]]
    [[ "$commit_files" == *"skills.md"* ]]
    [[ "$commit_files" == *".github/pull_request_template.md"* ]]
    [[ "$commit_files" != *"src/app.txt"* ]]
    grep -Fq "pr create --repo codeforester/base-demo --base master --head $pr_branch --title Add Base agent guidance --draft --body-file" "$TEST_STATE_DIR/gh-args"
    grep -Fq "Add Base repo-local agent guidance files." "$TEST_STATE_DIR/pr-body"
    grep -Fq "Closes #802" "$TEST_STATE_DIR/pr-body"
    grep -Fq "basectl repo agent-guidance" "$TEST_STATE_DIR/pr-body"
    grep -Fq -- "--issue 802 --category ci --pr" "$TEST_STATE_DIR/pr-body"
}

@test "basectl repo agent-guidance --pr requires a clean target worktree" {
    local physical_repo_dir
    local repo_dir="$TEST_TMPDIR/dirty-agent-demo"

    init_git_repo "$repo_dir"
    printf '# Dirty demo\n' > "$repo_dir/README.md"
    commit_all "$repo_dir" "Initial commit"
    printf 'draft\n' > "$repo_dir/notes.txt"
    physical_repo_dir="$(cd "$repo_dir" && pwd -P)"

    run_basectl repo agent-guidance "$repo_dir" --repo-name dirty-agent-demo --repo codeforester/dirty-agent-demo --issue 803 --pr

    [ "$status" -eq 1 ]
    [[ "$output" == *"repo agent-guidance --pr requires a clean Git worktree"* ]]
    [[ "$output" == *"Uncommitted changes detected (1 file)."* ]]
    [[ "$output" == *"?? notes.txt"* ]]
    [[ "$output" == *"Fix: commit or stash your changes before running this command."* ]]
    [[ "$output" == *"git -C $physical_repo_dir status --short"* ]]
    [ ! -f "$repo_dir/AGENTS.md" ]
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
    grep -Fq '`bug`, `enhancement`,' "$repo_dir/AGENTS.md"
    grep -Fq '`documentation`, `ci`, or `security`.' "$repo_dir/AGENTS.md"
    grep -Fq "Use exactly one standard issue category label" "$repo_dir/AGENTS.md"
    grep -Fq "The category prefix must match the issue's single standard category label." "$repo_dir/AGENTS.md"
    grep -Fq "This branch shape is tool-independent" "$repo_dir/AGENTS.md"
    grep -Fq "# Project Skills for base-demo" "$repo_dir/skills.md"
    grep -Fq "The branch convention is tool-independent" "$repo_dir/skills.md"
    grep -Fq 'docs/release-process.md' "$repo_dir/skills.md"
    grep -Fq "Closes #" "$repo_dir/.github/pull_request_template.md"
    grep -Fq "its category prefix matches the issue's single standard category label" "$repo_dir/.github/pull_request_template.md"
}

@test "basectl repo agent-guidance summarizes mixed existing files" {
    local repo_dir="$TEST_TMPDIR/custom-guidance"

    mkdir -p "$repo_dir"
    printf 'custom agents\n' > "$repo_dir/AGENTS.md"
    printf 'custom skills\n' > "$repo_dir/skills.md"

    run_basectl repo agent-guidance "$repo_dir" --repo-name custom-guidance

    [ "$status" -eq 0 ]
    [ "$(cat "$repo_dir/AGENTS.md")" = "custom agents" ]
    [ "$(cat "$repo_dir/skills.md")" = "custom skills" ]
    [ -f "$repo_dir/.github/pull_request_template.md" ]
    [[ "$output" == *"Agent guidance: 1 file created, 2 files already existed and were left unchanged."* ]]
    [[ "$output" == *"Created:   .github/pull_request_template.md"* ]]
    [[ "$output" == *"Unchanged: AGENTS.md, skills.md"* ]]
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
    [[ "$output" == *"Agent guidance: all 3 files already exist and were left unchanged."* ]]
    [[ "$output" == *"To overwrite, remove the files first and re-run."* ]]
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
    [ -f "$repo_dir/.github/workflows/issue-branch-policy.yml" ]
    [ -f "$repo_dir/.github/workflows/project-intake.yml" ]
    grep -Fqx "0.1.0" "$repo_dir/VERSION"
    grep -Fq "name: base-demo" "$repo_dir/base_manifest.yaml"
    grep -Fq "Use exactly one standard issue category label" "$repo_dir/CONTRIBUTING.md"
    grep -Fq "The category prefix must match the issue's single standard category label." "$repo_dir/CONTRIBUTING.md"
    grep -Fq "This branch shape is tool-independent" "$repo_dir/CONTRIBUTING.md"
    grep -Fq 'feat/`, `agent/`, `codex/' "$repo_dir/CONTRIBUTING.md"
    grep -Fq "its category prefix matches the issue's single standard category label" "$repo_dir/.github/pull_request_template.md"
    grep -Fq "command: ./tests/validate.sh" "$repo_dir/base_manifest.yaml"
    grep -Fq "issue_defaults:" "$repo_dir/.github/base-project.yml"
    grep -Fq "status: Backlog" "$repo_dir/.github/base-project.yml"
    grep -Fq "priority: P2" "$repo_dir/.github/base-project.yml"
    grep -Fq "area: Product" "$repo_dir/.github/base-project.yml"
    grep -Fq "initiative: Adoption Polish" "$repo_dir/.github/base-project.yml"
    grep -Fq "size: S" "$repo_dir/.github/base-project.yml"
    grep -Fq "permissions:" "$repo_dir/.github/workflows/tests.yml"
    grep -Fq "contents: read" "$repo_dir/.github/workflows/tests.yml"
    grep -Fq "concurrency:" "$repo_dir/.github/workflows/tests.yml"
    grep -Fq 'group: ${{ github.workflow }}-${{ github.ref }}' "$repo_dir/.github/workflows/tests.yml"
    grep -Fq "cancel-in-progress: true" "$repo_dir/.github/workflows/tests.yml"
    grep -Fq "timeout-minutes: 10" "$repo_dir/.github/workflows/tests.yml"
    grep -Fq "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5" "$repo_dir/.github/workflows/tests.yml"
    if grep -Fq "actions/checkout@v4" "$repo_dir/.github/workflows/tests.yml"; then
        fail "tests workflow should pin checkout to the reviewed commit"
    fi
    cmp "$BASE_REPO_ROOT/templates/issue-branch-policy.yml" "$repo_dir/.github/workflows/issue-branch-policy.yml"
    grep -Fq "pull_request_target:" "$repo_dir/.github/workflows/issue-branch-policy.yml"
    grep -Fq "statuses: write" "$repo_dir/.github/workflows/issue-branch-policy.yml"
    grep -Fq "base/issue-branch-policy" "$repo_dir/.github/workflows/issue-branch-policy.yml"
    if grep -Fq "actions/checkout" "$repo_dir/.github/workflows/issue-branch-policy.yml"; then
        fail "issue branch policy workflow must not check out pull request code"
    fi
    grep -Fq "name: Project Intake" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "concurrency:" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq 'group: ${{ github.workflow }}-${{ github.event.issue.number || inputs.issue_number || github.run_id }}' "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "cancel-in-progress: true" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "timeout-minutes: 10" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_TOKEN" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq 'GH_TOKEN: ${{ secrets.BASE_PROJECT_TOKEN }}' "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_TOKEN secret is required for Project Intake." "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "project_intake_gh()" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "project_intake_is_retryable_api_failure()" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "project_intake_retry_delay_seconds()" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "Retry-After" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "x-ratelimit-reset" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "retrying once" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "Rotate BASE_PROJECT_TOKEN and rerun this workflow_dispatch" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq 'project_intake_gh "view issue" gh issue view' "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq 'project_intake_gh "set Project field $field_name" gh project item-edit' "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "gh project item-add" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "If this Project exists, set BASE_PROJECT_TOKEN" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "set_single_select_if_missing Priority priority" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_DEFAULT_AREA: Product" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_DEFAULT_INITIATIVE: Adoption Polish" "$repo_dir/.github/workflows/project-intake.yml"
    if grep -Fq "github.token" "$repo_dir/.github/workflows/project-intake.yml"; then
        fail "project-intake workflow should not fall back to github.token"
    fi
    grep -Fq "<category>/<issue>-<YYYYMMDD>-<slug>" "$repo_dir/CONTRIBUTING.md"
    grep -Fq "git worktree add -b <branch> ../base-demo-worktrees/<slug> origin/<default-branch>" "$repo_dir/CONTRIBUTING.md"
    grep -Fq 'Update `CHANGELOG.md` only for notable user-visible or release-worthy' "$repo_dir/CONTRIBUTING.md"
    grep -Fq "## Checklist" "$repo_dir/.github/pull_request_template.md"
    grep -Fq "CHANGELOG is updated for notable user-visible or release-worthy changes." "$repo_dir/.github/pull_request_template.md"
    if grep -Fq "Demo Impact" "$repo_dir/.github/pull_request_template.md"; then
        fail "pull request template should not include Demo Impact by default"
    fi
    grep -Fq "GNU Affero General Public License" "$repo_dir/LICENSE"
    run grep -F "Base - a workspace control plane" "$repo_dir/LICENSE"
    [ "$status" -eq 1 ]

    run bash -c 'cd "$1" && ./tests/validate.sh' _ "$repo_dir"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository baseline is present."* ]]
}

@test "basectl repo init writes normalized language metadata" {
    local repo_dir="$TEST_TMPDIR/polyglot"

    run_basectl repo init polyglot \
        --path "$repo_dir" \
        --language "go, javascript" \
        --language c++ \
        --language golang \
        --no-configure

    [ "$status" -eq 0 ]
    grep -Fqx "  languages:" "$repo_dir/base_manifest.yaml"
    grep -Fqx "    - go" "$repo_dir/base_manifest.yaml"
    grep -Fqx "    - javascript" "$repo_dir/base_manifest.yaml"
    grep -Fqx "    - cpp" "$repo_dir/base_manifest.yaml"
    ! grep -Fq "python:" "$repo_dir/base_manifest.yaml"
}

@test "basectl repo init selects the uv Python profile" {
    local repo_dir="$TEST_TMPDIR/python-project"

    run_basectl repo init python-project --path "$repo_dir" --language python --no-configure

    [ "$status" -eq 0 ]
    grep -Fqx "    - python" "$repo_dir/base_manifest.yaml"
    grep -Fqx "  manager: uv" "$repo_dir/base_manifest.yaml"
}

@test "basectl repo init rejects empty or unsupported language entries" {
    run_basectl repo init invalid-project --path "$TEST_TMPDIR/invalid" --language "go,,java" --no-configure

    [ "$status" -eq 2 ]
    [[ "$output" == *"must not contain empty entries"* ]]

    run_basectl repo init invalid-project --path "$TEST_TMPDIR/invalid" --language rust --no-configure

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unsupported language 'rust'"* ]]
}

@test "basectl repo init --agent-ready creates baseline and agent guidance" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --agent-ready --no-configure

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/README.md" ]
    [ -f "$repo_dir/.github/pull_request_template.md" ]
    [ -f "$repo_dir/AGENTS.md" ]
    [ -f "$repo_dir/skills.md" ]
    grep -Fq "Agent Instructions for base-demo" "$repo_dir/AGENTS.md"
    grep -Fq "Project Skills for base-demo" "$repo_dir/skills.md"
    [[ "$output" == *"Agent guidance: 2 files created, 1 file already existed and was left unchanged."* ]]
    [[ "$output" == *"Created:   AGENTS.md, skills.md"* ]]
    [[ "$output" == *"Unchanged: .github/pull_request_template.md"* ]]
}

@test "basectl repo init --agent-ready dry-run reports agent guidance files" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --agent-ready --no-configure --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/README.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/AGENTS.md'."* ]]
    [[ "$output" == *"[DRY-RUN] Would create '$repo_dir/skills.md'."* ]]
    [ ! -e "$repo_dir" ]
}

@test "basectl repo init explains when GitHub configuration is skipped" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir"

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/base_manifest.yaml" ]
    [[ "$output" == *"Baseline files written to '$repo_dir'."* ]]
    [[ "$output" == *"GitHub repository not configured (no --repo provided and no origin remote found)."* ]]
    [[ "$output" == *"To complete GitHub setup, run:"* ]]
    [[ "$output" == *"basectl repo configure $repo_dir --repo <owner/base-demo>"* ]]
    [[ "$output" == *"Or to create the GitHub repository and configure it now:"* ]]
    [[ "$output" == *"basectl repo init base-demo --path $repo_dir --repo <owner/base-demo>"* ]]
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

@test "base_repo_baseline_year uses bash time formatting without date command" {
    cat > "$TEST_MOCKBIN/date" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/date"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASH" -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/repo.sh"
            base_repo_baseline_year
        '

    [ "$status" -eq 0 ]
    [[ "$output" =~ ^[0-9]{4}$ ]]
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
    [[ "$output" == *"Repository baseline: all 13 required files present."* ]]
}

@test "basectl repo check reports missing baseline files" {
    local repo_dir="$TEST_TMPDIR/incomplete"

    mkdir -p "$repo_dir"
    printf '# Incomplete\n' > "$repo_dir/README.md"

    run_basectl repo check "$repo_dir"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Repository baseline: 12 of 13 required files missing."* ]]
    [[ "$output" == *"Missing: VERSION"* ]]
    [[ "$output" == *"Missing: base_manifest.yaml"* ]]
    [[ "$output" == *"Run 'basectl repo init incomplete --path $repo_dir' to create the missing files."* ]]
}

@test "basectl repo check prints fix hint for non-executable validation script" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]
    chmod -x "$repo_dir/tests/validate.sh"

    cd "$repo_dir"
    run_basectl repo check .

    [ "$status" -eq 1 ]
    [[ "$output" == *"Repository baseline: all 13 required files present, but some requirements failed."* ]]
    [[ "$output" == *"  Not executable: tests/validate.sh"* ]]
    [[ "$output" == *"  Fix: chmod +x tests/validate.sh"* ]]
}

@test "basectl repo check reports missing agent guidance only when opted in" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]

    run_basectl repo check "$repo_dir" --agent-guidance

    [ "$status" -eq 1 ]
    [[ "$output" == *"Repository baseline: all 13 required files present."* ]]
    [[ "$output" == *"Agent guidance: 2 of 3 files missing."* ]]
    [[ "$output" == *"Missing: AGENTS.md"* ]]
    [[ "$output" == *"Missing: skills.md"* ]]
    [[ "$output" == *"Run 'basectl repo agent-guidance $repo_dir' to create the missing files."* ]]
}

@test "basectl repo check passes with generated agent guidance when opted in" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]
    run_basectl repo agent-guidance "$repo_dir" --repo-name base-demo
    [ "$status" -eq 0 ]

    run_basectl repo check "$repo_dir" --agent-guidance

    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository baseline: all 13 required files present."* ]]
    [[ "$output" == *"Agent guidance: all 3 files present."* ]]
}

@test "basectl repo check --agent-ready reports missing agent-ready files" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --no-configure
    [ "$status" -eq 0 ]

    run_basectl repo check "$repo_dir" --agent-ready

    [ "$status" -eq 1 ]
    [[ "$output" == *"Repository baseline: all 13 required files present."* ]]
    [[ "$output" == *"Agent readiness: 2 of 3 files missing."* ]]
    [[ "$output" == *"Missing: AGENTS.md"* ]]
    [[ "$output" == *"Missing: skills.md"* ]]
    [[ "$output" == *"Run 'basectl repo init base-demo --path $repo_dir --agent-ready' to create the missing files."* ]]
    [[ "$output" == *"Existing files are left unchanged."* ]]
}

@test "basectl repo check --agent-ready passes after agent-ready init" {
    local repo_dir="$TEST_TMPDIR/base-demo"

    run_basectl repo init base-demo --path "$repo_dir" --agent-ready --no-configure
    [ "$status" -eq 0 ]

    run_basectl repo check "$repo_dir" --agent-ready

    [ "$status" -eq 0 ]
    [[ "$output" == *"Repository baseline: all 13 required files present."* ]]
    [[ "$output" == *"Agent readiness: all 3 files present."* ]]
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

@test "basectl repo configure explains GitHub origin inference failures" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" --dry-run --no-project

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unable to infer GitHub repository from '$repo_dir'."* ]]
    [[ "$output" == *"Inference requires a git remote named 'origin' that points to github.com."* ]]
    [[ "$output" == *"Pass --repo <owner/name> to configure explicitly, or run:"* ]]
    [[ "$output" == *"git -C $repo_dir remote -v"* ]]
    [[ "$output" == *"to inspect the current remotes."* ]]
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
    [[ "$output" == *"Base branch naming"* ]]
    [[ "$output" == *'"include":["~ALL"]'* ]]
    [[ "$output" == *'"exclude":["~DEFAULT_BRANCH"]'* ]]
    [[ "$output" == *'"type":"branch_name_pattern"'* ]]
    [[ "$output" == *'"operator":"regex"'* ]]
    [[ "$output" == *'^(bug|enhancement|documentation|ci|security)/'* ]]
    [[ "$output" != *'"type":"required_status_checks"'* ]]
}

@test "basectl repo configure dry-run requires issue branch policy when the workflow exists" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir/.github/workflows"
    cp "$BASE_REPO_ROOT/templates/issue-branch-policy.yml" \
        "$repo_dir/.github/workflows/issue-branch-policy.yml"

    run_basectl repo configure "$repo_dir" --repo codeforester/base-demo --dry-run --no-project

    [ "$status" -eq 0 ]
    [[ "$output" == *'"type":"required_status_checks"'* ]]
    [[ "$output" == *'"do_not_enforce_on_create":true'* ]]
    [[ "$output" == *'"context":"base/issue-branch-policy"'* ]]
    [[ "$output" == *'"integration_id":15368'* ]]
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
    [[ "$output" == *"Base branch naming"* ]]
    [[ "$output" == *"rulesets"* ]]
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
    [[ "$output" == *"Would verify GitHub Actions secret 'BASE_PROJECT_TOKEN' exists for 'codeforester/base-demo'."* ]]
    [[ "$output" == *"--schema base-project"* ]]
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

@test "basectl repo configure can replace a nonstandard project" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"

    run_basectl repo configure "$repo_dir" \
        --repo codeforester/base-demo \
        --replace-project \
        --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would replace nonstandard existing GitHub Project 'base-demo' from 'base-project-template'."* ]]
    [[ "$output" == *"--replace-project"* ]]
}

@test "basectl repo configure applies GitHub settings through gh" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    write_repo_configure_gh_recorder

    BASE_REPO_TEST_REPO_VIEW_MISSING=1 \
        run_repo_command_with_mocks configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    [[ "$output" == *"Configuring GitHub repository 'codeforester/base-demo'..."* ]]
    [[ "$output" == *"  Repository settings: applied."* ]]
    [[ "$output" == *"  Label: bug (created or updated)."* ]]
    [[ "$output" == *"  Labels: bug, enhancement, documentation, ci, security, needs-demo (6 applied)."* ]]
    [[ "$output" == *"  Branch protection: created 'Base default branch protection'."* ]]
    [[ "$output" == *"  Branch naming: created 'Base branch naming'."* ]]
    [[ "$output" == *"Configuration complete."* ]]
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    grep -Fq "label create bug --repo codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    grep -Fq "label create needs-demo --repo codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
}

@test "basectl repo configure warns when Homebrew-managed gh is outdated" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "list" && "$2" == "gh" ]]; then
    exit 0
fi
if [[ "$1" == "outdated" && "$2" == "gh" ]]; then
    printf 'gh\n'
    exit 0
fi
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/brew"
    write_repo_configure_gh_recorder

    run_repo_command_with_mocks configure "$repo_dir" \
        --repo codeforester/base-demo \
        --no-project

    [ "$status" -eq 0 ]
    [[ "$output" == *"GitHub CLI 'gh' is outdated; run 'basectl setup --profile dev' to upgrade Base-managed developer prerequisites."* ]]
    [[ "$output" == *"Configuration complete."* ]]
}

@test "basectl repo configure does not warn when Homebrew-managed gh is current" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "list" && "$2" == "gh" ]]; then
    exit 0
fi
if [[ "$1" == "outdated" && "$2" == "gh" ]]; then
    exit 0
fi
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/brew"
    write_repo_configure_gh_recorder

    run_repo_command_with_mocks configure "$repo_dir" \
        --repo codeforester/base-demo \
        --no-project

    [ "$status" -eq 0 ]
    [[ "$output" != *"GitHub CLI 'gh' is outdated"* ]]
    [[ "$output" == *"Configuration complete."* ]]
}

@test "basectl repo configure skips gh freshness warning when Homebrew cannot inspect gh" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/brew" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "list" && "$2" == "gh" ]]; then
    exit 1
fi
if [[ "$1" == "outdated" && "$2" == "gh" ]]; then
    printf 'gh\n'
    exit 0
fi
exit 1
EOF
    chmod +x "$TEST_MOCKBIN/brew"
    write_repo_configure_gh_recorder

    run_repo_command_with_mocks configure "$repo_dir" \
        --repo codeforester/base-demo \
        --no-project

    [ "$status" -eq 0 ]
    [[ "$output" != *"GitHub CLI 'gh' is outdated"* ]]
    [[ "$output" == *"Configuration complete."* ]]
}

@test "basectl repo configure applies project metadata through Base project engine" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir/.github"
    cat > "$repo_dir/.github/base-project.yml" <<'EOF'
project:
  areas:
    - Demo App
EOF
    write_repo_configure_gh_recorder
    cat > "$TEST_MOCKBIN/project-wrapper" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_REPO_TEST_STATE_DIR:?}/project-args"
EOF
    chmod +x "$TEST_MOCKBIN/project-wrapper"

    BASE_REPO_PROJECT_WRAPPER="$TEST_MOCKBIN/project-wrapper" \
        run_repo_command_with_mocks configure "$repo_dir" \
            --repo codeforester/base-demo \
            --copy-project-fields-from "Base Roadmap"

    [ "$status" -eq 0 ]
    [ -f "$repo_dir/.github/workflows/project-intake.yml" ]
    grep -Fq "name: Project Intake" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "BASE_PROJECT_TOKEN" "$repo_dir/.github/workflows/project-intake.yml"
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    [[ "$output" == *"Configuring GitHub Project 'base-demo' for 'codeforester/base-demo'."* ]]
    [[ "$output" == *"Running: $TEST_MOCKBIN/project-wrapper --project base base_github_projects project configure --project base-demo --owner codeforester --repo codeforester/base-demo --schema base-project --config $repo_dir/.github/base-project.yml --copy-fields-from \"Base Roadmap\""* ]]
    [[ "$output" == *"  GitHub Project 'base-demo': Status, Priority, Area, Size, Initiative fields configured."* ]]
    [[ "$output" == *"Configuration complete."* ]]
    [ "$(cat "$TEST_STATE_DIR/project-args")" = "--project base base_github_projects project configure --project base-demo --owner codeforester --repo codeforester/base-demo --schema base-project --config $repo_dir/.github/base-project.yml --copy-fields-from Base Roadmap" ]
}

@test "basectl repo configure warns when project metadata needs GitHub project scope" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '%s\n' '{"workflow_runs":[{"id":77,"head_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","updated_at":"2999-01-01T00:00:00Z","head_branch":"main","event":"workflow_dispatch","path":".github/workflows/issue-branch-policy.yml","html_url":"https://github.com/codeforester/base-demo/actions/runs/77","head_repository":{"full_name":"codeforester/base-demo"}}]}'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "--paginate" && "$3" == "--slurp" && "$4" == "repos/codeforester/base-demo/commits/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/statuses?per_page=100" ]]; then
    printf '%s\n' '[[{"context":"base/issue-branch-policy","state":"success","description":"Issue branch policy workflow is ready","target_url":"https://github.com/codeforester/base-demo/actions/runs/77","creator":{"login":"github-actions[bot]"}}]]'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "/apps/github-actions" ]]; then
    printf '15368\n'
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

@test "basectl repo configure warns when project intake token secret is missing" {
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
if [[ "$1" == "secret" && "$2" == "list" ]]; then
    printf 'OTHER_TOKEN\t2026-06-18T00:00:00Z\n'
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
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo

    [ "$status" -eq 0 ]
    [[ "$output" == *"Project Intake secret 'BASE_PROJECT_TOKEN' is not configured for 'codeforester/base-demo'."* ]]
    [[ "$output" == *"GitHub Actions default token cannot access user-level Projects."* ]]
    [[ "$output" == *"gh auth token | gh secret set BASE_PROJECT_TOKEN --repo codeforester/base-demo"* ]]
}

@test "basectl repo configure accepts existing project intake token secret" {
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
if [[ "$1" == "secret" && "$2" == "list" ]]; then
    printf 'BASE_PROJECT_TOKEN\t2026-06-18T00:00:00Z\n'
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
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo

    [ "$status" -eq 0 ]
    [[ "$output" != *"Project Intake secret 'BASE_PROJECT_TOKEN' is not configured"* ]]
    [[ "$output" == *"Configuration complete."* ]]
}

@test "basectl repo configure updates existing Base rulesets" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '%s\n' '{"workflow_runs":[{"id":77,"head_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","updated_at":"2999-01-01T00:00:00Z","head_branch":"main","event":"workflow_dispatch","path":".github/workflows/issue-branch-policy.yml","html_url":"https://github.com/codeforester/base-demo/actions/runs/77","head_repository":{"full_name":"codeforester/base-demo"}}]}'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "--paginate" && "$3" == "--slurp" && "$4" == "repos/codeforester/base-demo/commits/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/statuses?per_page=100" ]]; then
    printf '%s\n' '[[{"context":"base/issue-branch-policy","state":"success","description":"Issue branch policy workflow is ready","target_url":"https://github.com/codeforester/base-demo/actions/runs/999","creator":{"login":"github-actions[bot]"}},{"context":"base/issue-branch-policy","state":"success","description":"Issue branch policy workflow is ready","target_url":"https://github.com/codeforester/base-demo/actions/runs/77","creator":{"login":"github-actions[bot]"}}]]'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "/apps/github-actions" ]]; then
    printf '15368\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" ]]; then
    printf '%s\n' "api-list $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    printf '%s\n' "42"
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets/42" && "$*" != *"--method PUT"* ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets/42" && "$*" == *"--method PUT"* ]]; then
    printf '%s\n' "api-update $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    cat >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    printf '\n' >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
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
    grep -Fq '"name":"Base default branch protection"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"include":["~DEFAULT_BRANCH"]' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"pull_request"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"required_status_checks"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"context":"base/issue-branch-policy"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"integration_id":15368' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"deletion"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"non_fast_forward"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"name":"Base branch naming"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"include":["~ALL"]' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"exclude":["~DEFAULT_BRANCH"]' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"branch_name_pattern"' "$TEST_STATE_DIR/ruleset-payloads"
}

@test "basectl repo configure creates missing Base rulesets" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '%s\n' '{"workflow_runs":[{"id":77,"head_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","updated_at":"2999-01-01T00:00:00Z","head_branch":"main","event":"workflow_dispatch","path":".github/workflows/issue-branch-policy.yml","html_url":"https://github.com/codeforester/base-demo/actions/runs/77","head_repository":{"full_name":"codeforester/base-demo"}}]}'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "--paginate" && "$3" == "--slurp" && "$4" == "repos/codeforester/base-demo/commits/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/statuses?per_page=100" ]]; then
    printf '%s\n' '[[{"context":"base/issue-branch-policy","state":"success","description":"Issue branch policy workflow is ready","target_url":"https://github.com/codeforester/base-demo/actions/runs/77","creator":{"login":"github-actions[bot]"}}]]'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "/apps/github-actions" ]]; then
    printf '15368\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" != *"--method POST"* ]]; then
    printf '%s\n' "api-list $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" == *"--method POST"* ]]; then
    printf '%s\n' "api-create $*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
    cat >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    printf '\n' >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
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
    grep -Fq '"name":"Base default branch protection"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"include":["~DEFAULT_BRANCH"]' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"pull_request"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"required_status_checks"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"context":"base/issue-branch-policy"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"integration_id":15368' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"deletion"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"non_fast_forward"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"name":"Base branch naming"' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"include":["~ALL"]' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"exclude":["~DEFAULT_BRANCH"]' "$TEST_STATE_DIR/ruleset-payloads"
    grep -Fq '"type":"branch_name_pattern"' "$TEST_STATE_DIR/ruleset-payloads"
}

@test "basectl repo configure finds readiness behind a newer stale dispatch" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '%s\n' '{"workflow_runs":[{"id":88,"head_sha":"dddddddddddddddddddddddddddddddddddddddd","updated_at":"2999-01-02T00:00:00Z","head_branch":"main","event":"workflow_dispatch","path":".github/workflows/issue-branch-policy.yml","html_url":"https://github.com/codeforester/base-demo/actions/runs/88","head_repository":{"full_name":"codeforester/base-demo"}},{"id":77,"head_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","updated_at":"2999-01-01T00:00:00Z","head_branch":"main","event":"workflow_dispatch","path":".github/workflows/issue-branch-policy.yml","html_url":"https://github.com/codeforester/base-demo/actions/runs/77","head_repository":{"full_name":"codeforester/base-demo"}}]}'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "--paginate" && "$3" == "--slurp" && "$4" == repos/codeforester/base-demo/commits/*/statuses\?per_page=100 ]]; then
    printf '%s\n' "$4" >> "${BASE_REPO_TEST_STATE_DIR:?}/status-lookups"
    if [[ "$4" == *"/dddddddddddddddddddddddddddddddddddddddd/"* ]]; then
        printf '%s\n' '[[]]'
    else
        printf '%s\n' '[[{"context":"base/issue-branch-policy","state":"success","description":"Issue branch policy workflow is ready","target_url":"https://github.com/codeforester/base-demo/actions/runs/77","creator":{"login":"github-actions[bot]"}}]]'
    fi
    exit 0
fi
if [[ "$1" == "api" && "$2" == "/apps/github-actions" ]]; then
    printf '15368\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" != *"--method POST"* ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" == *"--method POST"* ]]; then
    cat >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    printf '\n' >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    exit 0
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    [ "$(line_at "$(cat "$TEST_STATE_DIR/status-lookups")" 1)" = "repos/codeforester/base-demo/commits/dddddddddddddddddddddddddddddddddddddddd/statuses?per_page=100" ]
    [ "$(line_at "$(cat "$TEST_STATE_DIR/status-lookups")" 2)" = "repos/codeforester/base-demo/commits/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/statuses?per_page=100" ]
    grep -Fq '"context":"base/issue-branch-policy","integration_id":15368' "$TEST_STATE_DIR/ruleset-payloads"
}

@test "basectl repo configure waits for a recent issue branch policy run" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '%s\n' '{"workflow_runs":[{"id":77,"head_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","updated_at":"2000-01-01T00:00:00Z","head_branch":"main","event":"workflow_dispatch","path":".github/workflows/issue-branch-policy.yml","html_url":"https://github.com/codeforester/base-demo/actions/runs/77","head_repository":{"full_name":"codeforester/base-demo"}}]}'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" != *"--method POST"* ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" == *"--method POST"* ]]; then
    cat >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    printf '\n' >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    exit 0
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        EPOCHSECONDS=0 \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    [[ "$output" == *"Issue branch policy is not required for 'codeforester/base-demo' yet."* ]]
    grep -Fq '"name":"Base default branch protection"' "$TEST_STATE_DIR/ruleset-payloads"
    if grep -Fq '"type":"required_status_checks"' "$TEST_STATE_DIR/ruleset-payloads"; then
        fail "default branch ruleset should not require a never-successful workflow"
    fi
}

@test "basectl repo configure ignores successful policy runs from non-default branches" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '%s\n' '{"workflow_runs":[{"id":88,"head_sha":"dddddddddddddddddddddddddddddddddddddddd","updated_at":"2999-01-01T00:00:00Z","head_branch":"enhancement/99-20260714-untrusted","event":"workflow_dispatch","path":".github/workflows/issue-branch-policy.yml","html_url":"https://github.com/codeforester/base-demo/actions/runs/88","head_repository":{"full_name":"codeforester/base-demo"}}]}'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" != *"--method POST"* ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" == *"--method POST"* ]]; then
    cat >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    printf '\n' >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    exit 0
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    [[ "$output" == *"Issue branch policy is not required for 'codeforester/base-demo' yet."* ]]
    if grep -Fq '"type":"required_status_checks"' "$TEST_STATE_DIR/ruleset-payloads"; then
        fail "a feature-branch workflow run must not bootstrap the required policy"
    fi
}

@test "basectl repo configure preserves an existing trusted issue branch policy requirement" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" && "$*" != *"--method POST"* ]]; then
    printf '42\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets/42" && "$*" != *"--method PUT"* ]]; then
    printf '15368\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '{"workflow_runs":[]}\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets/42" && "$*" == *"--method PUT"* ]]; then
    cat >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    printf '\n' >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-payloads"
    exit 0
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 0 ]
    [[ "$output" == *"Preserving the existing Issue Branch Policy requirement"* ]]
    grep -Fq '"context":"base/issue-branch-policy","integration_id":15368' "$TEST_STATE_DIR/ruleset-payloads"
}

@test "basectl repo configure refuses to weaken or rebind an untrusted existing requirement" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets" ]]; then
    printf '42\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/rulesets/42" ]]; then
    printf '0\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'active\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo" ]]; then
    printf 'main\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml/runs?status=success&per_page=100" ]]; then
    printf '{"workflow_runs":[]}\n'
    exit 0
fi
if [[ "$1" == "api" && "$2" == repos/codeforester/base-demo/rulesets* && "$*" == *"--method"* ]]; then
    printf 'unexpected ruleset write\n' >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-writes"
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 1 ]
    [[ "$output" == *"Refusing to replace the existing unbound Issue Branch Policy requirement"* ]]
    [ ! -e "$TEST_STATE_DIR/ruleset-writes" ]
}

@test "basectl repo configure does not weaken rulesets after workflow lookup errors" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/actions/workflows/issue-branch-policy.yml" ]]; then
    printf 'gh: server error (HTTP 500)\n' >&2
    exit 1
fi
if [[ "$1" == "api" && "$2" == repos/codeforester/base-demo/rulesets* && "$*" == *"--method"* ]]; then
    printf 'unexpected ruleset write\n' >> "${BASE_REPO_TEST_STATE_DIR:?}/ruleset-writes"
    exit 0
fi
exit 0
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo --no-project

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unable to verify the Issue Branch Policy workflow on 'codeforester/base-demo'."* ]]
    [ ! -e "$TEST_STATE_DIR/ruleset-writes" ]
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
    [[ "$output" == *"Branch naming enforcement skipped"* ]]
    [[ "$output" == *"GitHub Pro"* ]]
    [[ "$output" == *"make this repository public"* ]]
}

@test "basectl repo configure warns when GitHub plan blocks ruleset writes" {
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
    cat >/dev/null
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
    grep -Fq "api-create api repos/codeforester/base-demo/rulesets --method POST" "$TEST_STATE_DIR/gh-args"
    [[ "$output" == *"Default branch protection skipped"* ]]
    [[ "$output" == *"Branch naming enforcement skipped"* ]]
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
    [[ "$output" == *"Unable to inspect current default branch protection for 'codeforester/base-demo'."* ]]
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
    [ "$(cat "$TEST_STATE_DIR/project-args")" = "--project base base_github_projects project configure --project base-demo --owner codeforester --repo codeforester/base-demo --schema base-project --config $repo_dir/.github/base-project.yml" ]
    ! grep -Fq "pr create" "$TEST_STATE_DIR/gh-args"
}

@test "basectl repo init --pr dry-run reports a canonical branch and pull request plan" {
    local pr_branch="bug/900-$(current_branch_date)-repo-baseline-base-demo"
    local repo_dir="$TEST_TMPDIR/base-demo-dry-run"

    init_git_repo "$repo_dir"
    git -C "$repo_dir" remote add origin git@github.com:codeforester/base-demo.git

    run_basectl repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --issue 900 --category bug --pr --dry-run

    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN] Would create or use branch '$pr_branch' from default branch '<default branch>'."* ]]
    [[ "$output" == *"[DRY-RUN] Would push branch '$pr_branch' to origin."* ]]
    [[ "$output" == *"[DRY-RUN] Would open a pull request in 'codeforester/base-demo' from '$pr_branch' to '<default branch>'"* ]]
}

@test "basectl repo init --pr opens a baseline pull request" {
    local commit_files
    local pr_branch="bug/901-$(current_branch_date)-repo-baseline-base-demo"
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
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/issues/901" ]]; then
    printf 'issue\nbug\n'
    exit 0
fi
if [[ "$*" == "repo view codeforester/base-demo --json defaultBranchRef --jq .defaultBranchRef.name" ]]; then
    printf 'master\n'
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
body_file=""
is_pr_create=0
if [[ "$1" == "pr" && "$2" == "create" ]]; then
    is_pr_create=1
fi
while (($#)); do
    if [[ "$1" == "--body-file" ]]; then
        body_file="$2"
        break
    fi
    shift
done
[[ -n "$body_file" ]] && cat "$body_file" > "${BASE_REPO_TEST_STATE_DIR:?}/pr-body"
if [[ "$is_pr_create" == "1" ]]; then
    printf 'https://github.com/codeforester/base-demo/pull/1\n'
fi
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --issue 901 --pr

    [ "$status" -eq 0 ]
    [ "$(git -C "$repo_dir" branch --show-current)" = "$pr_branch" ]
    [ "$(git -C "$repo_dir" log -1 --pretty=%s)" = "Add Base repository baseline" ]
    git --git-dir="$remote_dir" show-ref --verify --quiet "refs/heads/$pr_branch"
    commit_files="$(git -C "$repo_dir" show --name-only --pretty=format: HEAD)"
    [[ "$commit_files" == *"VERSION"* ]]
    [[ "$commit_files" == *".github/base-project.yml"* ]]
    [[ "$commit_files" == *"base_manifest.yaml"* ]]
    [[ "$commit_files" != *"src/app.txt"* ]]
    grep -Fq "pr create --repo codeforester/base-demo --base master --head $pr_branch --title Add Base repository baseline --body-file" "$TEST_STATE_DIR/gh-args"
    if grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"; then
        fail "repo init --pr should not configure GitHub when opening a baseline pull request"
    fi
    grep -Fq "Add Base-managed repository baseline files." "$TEST_STATE_DIR/pr-body"
    grep -Fq "Closes #901" "$TEST_STATE_DIR/pr-body"
    grep -Fq "basectl repo init base-demo --path" "$TEST_STATE_DIR/pr-body"
    grep -Fq -- "--issue 901 --category bug --pr" "$TEST_STATE_DIR/pr-body"
    [[ "$output" == *"Baseline PR opened: https://github.com/codeforester/base-demo/pull/1"* ]]
    [[ "$output" == *"Next steps:"* ]]
    [[ "$output" == *"Review and merge the pull request."* ]]
    [[ "$output" == *"basectl repo init base-demo --path"* ]]
    [[ "$output" == *"--repo codeforester/base-demo --issue 901 --category bug --pr"* ]]
}

@test "basectl repo init --agent-ready --pr includes agent guidance files" {
    local commit_files
    local remote_dir="$TEST_TMPDIR/origin.git"
    local repo_dir="$TEST_TMPDIR/base-demo"

    init_git_repo "$repo_dir"
    printf '# Existing project\n' > "$repo_dir/README.md"
    commit_all "$repo_dir" "Initial commit"
    git init --bare "$remote_dir" >/dev/null 2>&1
    git -C "$repo_dir" remote add origin "$remote_dir"
    git -C "$repo_dir" push -u origin master >/dev/null 2>&1

    cat > "$TEST_MOCKBIN/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "auth status -h github.com" ]]; then
    exit 0
fi
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/issues/902" ]]; then
    printf 'issue\nenhancement\n'
    exit 0
fi
if [[ "$*" == "repo view codeforester/base-demo --json defaultBranchRef --jq .defaultBranchRef.name" ]]; then
    printf 'master\n'
    exit 0
fi
printf '%s\n' "$*" >> "${BASE_REPO_TEST_STATE_DIR:?}/gh-args"
body_file=""
is_pr_create=0
if [[ "$1" == "pr" && "$2" == "create" ]]; then
    is_pr_create=1
fi
while (($#)); do
    if [[ "$1" == "--body-file" ]]; then
        body_file="$2"
        break
    fi
    shift
done
[[ -n "$body_file" ]] && cat "$body_file" > "${BASE_REPO_TEST_STATE_DIR:?}/pr-body"
if [[ "$is_pr_create" == "1" ]]; then
    printf 'https://github.com/codeforester/base-demo/pull/1\n'
fi
EOF
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        "$BASE_REPO_ROOT/bin/basectl" repo init base-demo --path "$repo_dir" --repo codeforester/base-demo --agent-ready --issue 902 --pr

    [ "$status" -eq 0 ]
    commit_files="$(git -C "$repo_dir" show --name-only --pretty=format: HEAD)"
    [[ "$commit_files" == *"AGENTS.md"* ]]
    [[ "$commit_files" == *"skills.md"* ]]
    grep -Fq "basectl repo init base-demo --path" "$TEST_STATE_DIR/pr-body"
    grep -Fq -- "--agent-ready" "$TEST_STATE_DIR/pr-body"
    grep -Fq -- "--issue 902 --category enhancement --pr" "$TEST_STATE_DIR/pr-body"
    [[ "$output" == *"--agent-ready"* ]]
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
if [[ "$1" == "api" && "$2" == "repos/codeforester/base-demo/issues/903" ]]; then
    printf 'issue\nenhancement\n'
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
            --issue 903 \
            --pr \
            --copy-project-fields-from "Base Roadmap"

    [ "$status" -eq 0 ]
    [[ "$output" == *"No repository baseline changes to commit; continuing with GitHub repository configuration."* ]]
    grep -Fq "repo edit codeforester/base-demo" "$TEST_STATE_DIR/gh-args"
    if grep -Fq "pr create" "$TEST_STATE_DIR/gh-args"; then
        fail "repo init --pr should not open a pull request when there are no baseline changes"
    fi
    [ "$(cat "$TEST_STATE_DIR/project-args")" = "--project base base_github_projects project configure --project base-demo --owner codeforester --repo codeforester/base-demo --schema base-project --config $repo_dir/.github/base-project.yml --copy-fields-from Base Roadmap" ]
}

@test "basectl repo init --pr requires a clean target worktree" {
    local physical_repo_dir
    local repo_dir="$TEST_TMPDIR/dirty-demo"

    init_git_repo "$repo_dir"
    printf '# Dirty demo\n' > "$repo_dir/README.md"
    commit_all "$repo_dir" "Initial commit"
    printf 'draft\n' > "$repo_dir/notes.txt"
    physical_repo_dir="$(cd "$repo_dir" && pwd -P)"

    run_basectl repo init dirty-demo --path "$repo_dir" --repo codeforester/dirty-demo --issue 904 --pr

    [ "$status" -eq 1 ]
    [[ "$output" == *"repo init --pr requires a clean Git worktree"* ]]
    [[ "$output" == *"Uncommitted changes detected (1 file)."* ]]
    [[ "$output" == *"?? notes.txt"* ]]
    [[ "$output" == *"Fix: commit or stash your changes before running this command."* ]]
    [[ "$output" == *"git -C $physical_repo_dir status --short"* ]]
    [ ! -f "$repo_dir/base_manifest.yaml" ]
}

@test "basectl repo init --pr explains repository root path mismatch" {
    local physical_repo_dir
    local physical_subdir
    local repo_dir="$TEST_TMPDIR/root-demo"
    local subdir="$repo_dir/subdir"

    init_git_repo "$repo_dir"
    printf '# Root demo\n' > "$repo_dir/README.md"
    commit_all "$repo_dir" "Initial commit"
    mkdir -p "$subdir"
    physical_repo_dir="$(cd "$repo_dir" && pwd -P)"
    physical_subdir="$(cd "$subdir" && pwd -P)"

    run_basectl repo init root-demo --path "$subdir" --repo codeforester/root-demo --issue 905 --pr

    [ "$status" -eq 1 ]
    [[ "$output" == *"repo init --pr expects --path to point at the repository root."* ]]
    [[ "$output" == *"Provided path: $physical_subdir"* ]]
    [[ "$output" == *"Repository root: $physical_repo_dir"* ]]
    [[ "$output" == *"Fix: pass --path $physical_repo_dir"* ]]
    [ ! -f "$subdir/base_manifest.yaml" ]
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
