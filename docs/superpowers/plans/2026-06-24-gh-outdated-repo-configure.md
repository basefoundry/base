# Gh Outdated Repo Configure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `basectl repo configure` surface the existing Base update path when the local Homebrew-managed `gh` package is outdated.

**Architecture:** Add a best-effort Bash helper near the existing `repo configure` GitHub CLI helpers. The helper checks Homebrew state without auto-updating, warns when `gh` is stale, and stays silent when Homebrew cannot determine state.

**Tech Stack:** Bash, Bats, Homebrew CLI.

---

### Task 1: Warn About Outdated Homebrew-Managed Gh

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/repo.sh`
- Modify: `cli/bash/commands/basectl/tests/repo.bats`

- [ ] **Step 1: Write the failing test**

Add a Bats test near the existing `repo configure` GitHub settings tests:

```bash
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

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" \
            --repo codeforester/base-demo \
            --no-project

    [ "$status" -eq 0 ]
    [[ "$output" == *"GitHub CLI 'gh' is outdated; run 'basectl setup --profile dev' to upgrade Base-managed developer prerequisites."* ]]
    [[ "$output" == *"Configuration complete."* ]]
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
env BASE_BASH_LIBS_DIR=/Users/rameshhp/work/base-bash-libs/lib/bash bats cli/bash/commands/basectl/tests/repo.bats --filter "warns when Homebrew-managed gh is outdated"
```

Expected: FAIL because `repo configure` does not yet check Homebrew `gh` staleness.

- [ ] **Step 3: Implement the minimal helper and call site**

Add helper functions near `base_repo_require_gh`:

```bash
base_repo_homebrew_gh_outdated() {
    local output=""

    command -v brew >/dev/null 2>&1 || return 1
    HOMEBREW_NO_AUTO_UPDATE=1 brew list gh >/dev/null 2>&1 || return 1
    output="$(HOMEBREW_NO_AUTO_UPDATE=1 brew outdated gh 2>/dev/null || true)"
    printf '%s\n' "$output" | awk '$1 == "gh" { found = 1 } END { exit found ? 0 : 1 }'
}

base_repo_warn_if_gh_outdated() {
    if base_repo_homebrew_gh_outdated; then
        log_warn "GitHub CLI 'gh' is outdated; run 'basectl setup --profile dev' to upgrade Base-managed developer prerequisites."
    fi
}
```

Call `base_repo_warn_if_gh_outdated` after `base_repo_require_gh` succeeds in the non-dry-run `repo configure` GitHub configuration path.

- [ ] **Step 4: Run the focused test to verify it passes**

Run:

```bash
env BASE_BASH_LIBS_DIR=/Users/rameshhp/work/base-bash-libs/lib/bash bats cli/bash/commands/basectl/tests/repo.bats --filter "warns when Homebrew-managed gh is outdated"
```

Expected: PASS.

- [ ] **Step 5: Run the repo Bats suite**

Run:

```bash
env BASE_BASH_LIBS_DIR=/Users/rameshhp/work/base-bash-libs/lib/bash bats cli/bash/commands/basectl/tests/repo.bats
```

Expected: PASS.
