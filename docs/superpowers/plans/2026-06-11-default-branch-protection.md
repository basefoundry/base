# Default Branch Protection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `basectl repo configure` apply a modest, idempotent default-branch protection policy by default, with an explicit opt-out.

**Architecture:** Extend the existing Bash `basectl repo` implementation in `repo.sh`. Keep repository settings and labels on the current `gh repo edit`/label path, and add a named Base-managed repository ruleset targeting `~DEFAULT_BRANCH` so repeated runs update the same policy instead of creating duplicates or clobbering unrelated manual branch protection.

**Tech Stack:** Bash, GitHub CLI `gh api`, GitHub repository rulesets API, BATS tests, Markdown docs.

---

### Task 1: Add Failing BATS Coverage

**Files:**
- Modify: `cli/bash/commands/basectl/tests/repo.bats`

- [ ] **Step 1: Add tests for default protection, opt-out, and idempotent update**

Add focused tests near the existing `basectl repo configure` tests. Use the existing mock `gh` pattern. The apply test should write `gh api` arguments and stdin payloads to `$TEST_STATE_DIR` so assertions can verify one lookup and one update/create path.

```bash
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

@test "basectl repo configure updates an existing Base ruleset" {
    local repo_dir="$TEST_TMPDIR/repo"

    mkdir -p "$repo_dir"
    cat > "$TEST_MOCKBIN/gh" <<'GH'
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
GH
    chmod +x "$TEST_MOCKBIN/gh"

    run env \
        HOME="$TEST_HOME" \
        BASE_REPO_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        "$BASE_REPO_ROOT/bin/basectl" repo configure "$repo_dir" --repo codeforester/base-demo

    [ "$status" -eq 0 ]
    grep -Fq "api-list api repos/codeforester/base-demo/rulesets" "$TEST_STATE_DIR/gh-args"
    grep -Fq "api-update api repos/codeforester/base-demo/rulesets/42 --method PUT" "$TEST_STATE_DIR/gh-args"
    grep -Fq '"name":"Base default branch protection"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"include":["~DEFAULT_BRANCH"]' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"pull_request"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"deletion"' "$TEST_STATE_DIR/ruleset-payload"
    grep -Fq '"type":"non_fast_forward"' "$TEST_STATE_DIR/ruleset-payload"
}
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

Expected: FAIL because `--no-protect-default-branch` is unknown and no ruleset output/API calls exist yet.

### Task 2: Implement Default Ruleset Management

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/repo.sh`

- [ ] **Step 1: Add usage text**

Update the top-level repo usage options:

```text
  --no-protect-default-branch  Skip Base-managed default branch protection during repo configure.
```

- [ ] **Step 2: Add a ruleset payload helper**

Add a helper near the existing GitHub configuration helpers:

```bash
base_repo_default_branch_ruleset_payload() {
    cat <<'JSON'
{"name":"Base default branch protection","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"allowed_merge_methods":["squash"],"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_approving_review_count":0,"required_review_thread_resolution":false}},{"type":"deletion"},{"type":"non_fast_forward"}]}
JSON
}
```

- [ ] **Step 3: Add ruleset upsert helper**

Add `base_repo_configure_default_branch_protection "$dry_run" "$repo"` that:

- prints dry-run lookup/upsert output including the ruleset name, `~DEFAULT_BRANCH`, and payload
- calls `base_repo_require_gh` in apply mode
- looks up a repository-owned ruleset named `Base default branch protection`
- `PUT`s `repos/$repo/rulesets/$id` when found
- `POST`s `repos/$repo/rulesets` when missing

- [ ] **Step 4: Thread the default through `repo configure` and `repo init`**

Change `base_repo_configure_github` to accept a third argument, `protect_default_branch`, and invoke the ruleset helper after labels when the value is `1`.

Parse `--no-protect-default-branch` in `base_repo_configure` and `base_repo_init`, defaulting `protect_default_branch=1`, and pass it through to `base_repo_configure_github`.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

Expected: PASS.

### Task 3: Update Docs and Validate

**Files:**
- Modify: `docs/repo-baseline.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Document the new default**

Update `docs/repo-baseline.md` GitHub Configuration to include:

- default branch protection is enabled by default
- `--no-protect-default-branch` opts out
- the default ruleset prevents force pushes/deletion and requires pull requests, without status-check or review-count requirements

- [ ] **Step 2: Update README command summary if needed**

Mention default branch protection in the existing repository baseline section near `basectl repo configure`.

- [ ] **Step 3: Add changelog entry**

Add an Unreleased entry:

```markdown
### Added

- Protected default branches by default during `basectl repo configure`, with
  `--no-protect-default-branch` for repositories that intentionally skip the
  Base-managed ruleset.
```

- [ ] **Step 4: Run validation**

Run:

```bash
bats cli/bash/commands/basectl/tests/repo.bats
git diff --check
env -u BASE_HOME ./bin/base-test
```

Expected: all pass.

- [ ] **Step 5: Open PR**

Commit the issue-backed change and open a PR with:

- Summary of default branch protection behavior
- Validation commands and results
- `.ai-context/` decision
- `Fixes #598`
