# Lib Std Log And Path Splitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Completed on 2026-06-14. Issue #702 landed in PR #706, and issue #700 landed in PR #707. This file is retained as an implementation-plan archive.

**Goal:** Fix the newly opened lib_std-related shell issues #702 and #700 without folding in unrelated shell cleanup work.

**Architecture:** Use one PR per issue to keep review and rollback simple. First fix the direct `lib/bash/std/lib_std.sh` regression in #702, then align `bootstrap.sh` and `install.sh` PATH candidate splitting with the existing `lib_std.sh` idiom for #700.

**Tech Stack:** Bash 4.2+, BATS, ShellCheck, Base shell test harness.

---

## Scope

Included:

- #702: `bug: LOG_UTC support in _print_log introduced a subshell per log call`
- #700: `enhancement: unify PATH-splitting style in bootstrap.sh and install.sh`

Deferred as separate shell cleanup work:

- #698: `install.sh uses set -euo pipefail`
- #699: `replace eval with declare -n nameref in baserc_guard.sh`
- #701: `git_get_current_branch usage message names the wrong function`

## File Structure

- Modify `lib/bash/std/lib_std.sh`: remove timestamp command substitution from `_print_log`.
- Modify `lib/bash/std/tests/lib_std.bats`: add a source-structure regression test and keep existing timestamp behavior tests.
- Modify `bootstrap.sh`: replace manual `old_ifs` save/restore loops with `IFS=: read -ra`.
- Modify `install.sh`: replace manual `old_ifs` save/restore loops with `IFS=: read -ra`.
- Modify `tests/bootstrap.bats`: assert `bootstrap.sh` no longer uses `old_ifs` and has scoped colon splitting.
- Modify `tests/install.bats`: assert `install.sh` no longer uses `old_ifs` and has scoped colon splitting.
- Modify `CHANGELOG.md`: add one Unreleased entry per PR.

---

### Task 1: Fix #702, `_print_log` Timestamp Formatting Without Subshells

**Files:**

- Modify: `lib/bash/std/lib_std.sh`
- Modify: `lib/bash/std/tests/lib_std.bats`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Create a worktree for #702**

Run:

```bash
git fetch origin master
git worktree add -b bug/702-20260614-log-utc-no-subshell ../base-worktrees/702-log-utc-no-subshell origin/master
cd ../base-worktrees/702-log-utc-no-subshell
```

Expected: new clean worktree on `origin/master`.

- [ ] **Step 2: Write the failing source-structure test**

Add this test immediately after `_print_log requires a log level` in `lib/bash/std/tests/lib_std.bats`:

```bash
@test "_print_log formats timestamps without command substitution" {
    run grep -nE 'timestamp="\$\((TZ=UTC0 )?printf' "$STDLIB_PATH"

    [ "$status" -eq 1 ]
    [ "$output" = "" ]
}
```

- [ ] **Step 3: Run the focused RED test**

Run:

```bash
bats --print-output-on-failure --filter "_print_log formats timestamps without command substitution" lib/bash/std/tests/lib_std.bats
```

Expected: FAIL. Current source contains:

```bash
timestamp="$(TZ=UTC0 printf '%(%Y-%m-%d %H:%M:%S)T' -1)"
timestamp="$(printf '%(%Y-%m-%d %H:%M:%S)T' -1)"
```

- [ ] **Step 4: Replace timestamp command substitution with inline Bash builtin `printf`**

In `lib/bash/std/lib_std.sh`, replace this block:

```bash
local message timestamp
message="$(__join_message__ "$@")"
if [[ "${LOG_UTC:-}" == 1 ]]; then
    timestamp="$(TZ=UTC0 printf '%(%Y-%m-%d %H:%M:%S)T' -1)"
else
    timestamp="$(printf '%(%Y-%m-%d %H:%M:%S)T' -1)"
fi
{
    printf '%b' "$color"
    printf '%s %-7s %s ' "$timestamp" "$in_level" "${source_path}:${source_line}"
    printf '%s' "$message"
    printf '%b\n' "$COLOR_OFF"
} >&2
```

with:

```bash
local message
message="$(__join_message__ "$@")"
{
    printf '%b' "$color"
    if [[ "${LOG_UTC:-}" == 1 ]]; then
        TZ=UTC0 printf '%(%Y-%m-%d %H:%M:%S)T %-7s %s ' -1 "$in_level" "${source_path}:${source_line}"
    else
        printf '%(%Y-%m-%d %H:%M:%S)T %-7s %s ' -1 "$in_level" "${source_path}:${source_line}"
    fi
    printf '%s' "$message"
    printf '%b\n' "$COLOR_OFF"
} >&2
```

Rationale: `TZ=UTC0 printf ...` affects Bash builtin `%T` formatting for that invocation and does not persist into later calls.

- [ ] **Step 5: Add the changelog entry**

Under `[Unreleased]`, add:

```markdown
- Avoided subshell timestamp formatting in Bash `LOG_UTC` logging.
```

- [ ] **Step 6: Run focused GREEN checks**

Run:

```bash
bats --print-output-on-failure --filter "_print_log" lib/bash/std/tests/lib_std.bats
shellcheck --severity=error lib/bash/std/lib_std.sh
grep -nE 'timestamp="\$\((TZ=UTC0 )?printf' lib/bash/std/lib_std.sh
git diff --check
```

Expected:

- BATS passes.
- ShellCheck exits 0.
- `grep` exits 1 with no output.
- `git diff --check` exits 0.

- [ ] **Step 7: Run full shell and Base validation**

Run:

```bash
bats --print-output-on-failure lib/bash/std/tests/lib_std.bats
env -u BASE_HOME ./bin/base-test
```

Expected:

- `lib_std.bats` passes, except any existing intentional skips.
- `base-test` exits 0.

- [ ] **Step 8: Commit and open the PR**

Run:

```bash
git status --short
git add CHANGELOG.md lib/bash/std/lib_std.sh lib/bash/std/tests/lib_std.bats
git commit -m "Avoid subshell timestamp formatting in Bash logs"
git push -u origin bug/702-20260614-log-utc-no-subshell
```

Open a draft PR:

```bash
bin/basectl gh pr create \
  --repo codeforester/base \
  --base master \
  --head bug/702-20260614-log-utc-no-subshell \
  --title "Avoid subshell timestamp formatting in Bash logs" \
  --draft
```

PR body must include:

```markdown
Fixes #702

Validation:
- RED: `bats --print-output-on-failure --filter "_print_log formats timestamps without command substitution" lib/bash/std/tests/lib_std.bats`
- GREEN: `bats --print-output-on-failure --filter "_print_log" lib/bash/std/tests/lib_std.bats`
- GREEN: `shellcheck --severity=error lib/bash/std/lib_std.sh`
- GREEN: `grep -nE 'timestamp="\$\((TZ=UTC0 )?printf' lib/bash/std/lib_std.sh` exits 1
- GREEN: `git diff --check`
- GREEN: `bats --print-output-on-failure lib/bash/std/tests/lib_std.bats`
- GREEN: `env -u BASE_HOME ./bin/base-test`
```

---

### Task 2: Fix #700, Scoped Colon Splitting In Bootstrap And Install

**Files:**

- Modify: `bootstrap.sh`
- Modify: `install.sh`
- Modify: `tests/bootstrap.bats`
- Modify: `tests/install.bats`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Create a worktree for #700 after #702 merges**

Run after #702 is merged and local `master` is synced:

```bash
cd /Users/rameshhp/work/base
git pull --ff-only origin master
git worktree add -b enhancement/700-20260614-scoped-path-splitting ../base-worktrees/700-scoped-path-splitting origin/master
cd ../base-worktrees/700-scoped-path-splitting
```

Expected: new clean worktree on the current `origin/master`.

- [ ] **Step 2: Write the failing bootstrap regression test**

Add this test after `bootstrap avoids shell strict mode` in `tests/bootstrap.bats`:

```bash
@test "bootstrap uses scoped colon splitting for candidate lists" {
    run grep -n 'old_ifs' "$BASE_REPO_ROOT/bootstrap.sh"
    [ "$status" -eq 1 ]
    [ "$output" = "" ]

    run grep -c 'IFS=: read -ra' "$BASE_REPO_ROOT/bootstrap.sh"
    [ "$status" -eq 0 ]
    [ "$output" -eq 2 ]
}
```

- [ ] **Step 3: Write the failing installer regression test**

Add this test after `installer includes update-profile by default` in `tests/install.bats`:

```bash
@test "installer uses scoped colon splitting for candidate lists" {
    run grep -n 'old_ifs' "$BASE_REPO_ROOT/install.sh"
    [ "$status" -eq 1 ]
    [ "$output" = "" ]

    run grep -c 'IFS=: read -ra' "$BASE_REPO_ROOT/install.sh"
    [ "$status" -eq 0 ]
    [ "$output" -eq 2 ]
}
```

- [ ] **Step 4: Run the focused RED tests**

Run:

```bash
bats --print-output-on-failure --filter "scoped colon splitting" tests/bootstrap.bats tests/install.bats
```

Expected: FAIL. Current `bootstrap.sh` and `install.sh` contain `old_ifs` and no `IFS=: read -ra` candidate-list splitting.

- [ ] **Step 5: Update `bootstrap_find_brew`**

In `bootstrap.sh`, replace:

```bash
local candidate
local candidates="${BASE_BOOTSTRAP_BREW_CANDIDATES:-/opt/homebrew/bin/brew:/usr/local/bin/brew}"
local old_ifs
```

with:

```bash
local candidate
local candidates="${BASE_BOOTSTRAP_BREW_CANDIDATES:-/opt/homebrew/bin/brew:/usr/local/bin/brew}"
local -a candidate_paths
```

Replace the old loop:

```bash
old_ifs="$IFS"
IFS=:
for candidate in $candidates; do
    IFS="$old_ifs"
    [[ -x "$candidate" ]] || continue
    printf '%s\n' "$candidate"
    return 0
done
IFS="$old_ifs"
```

with:

```bash
IFS=: read -ra candidate_paths <<< "$candidates"
for candidate in "${candidate_paths[@]}"; do
    [[ -n "$candidate" ]] || continue
    [[ -x "$candidate" ]] || continue
    printf '%s\n' "$candidate"
    return 0
done
```

- [ ] **Step 6: Update `bootstrap_find_supported_bash`**

In `bootstrap.sh`, replace:

```bash
local candidate
local candidates="${BASE_BOOTSTRAP_BASH_CANDIDATES:-/opt/homebrew/bin/bash:/usr/local/bin/bash}"
local current_version
local old_ifs
```

with:

```bash
local candidate
local candidates="${BASE_BOOTSTRAP_BASH_CANDIDATES:-/opt/homebrew/bin/bash:/usr/local/bin/bash}"
local current_version
local -a candidate_paths
```

Replace the old `old_ifs` loop with:

```bash
IFS=: read -ra candidate_paths <<< "$candidates"
for candidate in "${candidate_paths[@]}"; do
    [[ -n "$candidate" ]] || continue
    [[ -x "$candidate" ]] || continue
    printf '%s\n' "$candidate"
    return 0
done
```

- [ ] **Step 7: Update `install_find_supported_bash`**

In `install.sh`, replace:

```bash
local candidate
local candidates="${BASE_INSTALL_BASH_CANDIDATES:-/opt/homebrew/bin/bash:/usr/local/bin/bash}"
local current_version
local old_ifs
```

with:

```bash
local candidate
local candidates="${BASE_INSTALL_BASH_CANDIDATES:-/opt/homebrew/bin/bash:/usr/local/bin/bash}"
local current_version
local -a candidate_paths
```

Replace the old `old_ifs` loop with:

```bash
IFS=: read -ra candidate_paths <<< "$candidates"
for candidate in "${candidate_paths[@]}"; do
    [[ -n "$candidate" ]] || continue
    [[ -x "$candidate" ]] || continue
    printf '%s\n' "$candidate"
    return 0
done
```

- [ ] **Step 8: Update `install_find_brew`**

In `install.sh`, replace:

```bash
local candidate
local candidates="${BASE_INSTALL_BREW_CANDIDATES:-/opt/homebrew/bin/brew:/usr/local/bin/brew}"
local old_ifs
```

with:

```bash
local candidate
local candidates="${BASE_INSTALL_BREW_CANDIDATES:-/opt/homebrew/bin/brew:/usr/local/bin/brew}"
local -a candidate_paths
```

Replace the old `old_ifs` loop with:

```bash
IFS=: read -ra candidate_paths <<< "$candidates"
for candidate in "${candidate_paths[@]}"; do
    [[ -n "$candidate" ]] || continue
    [[ -x "$candidate" ]] || continue
    printf '%s\n' "$candidate"
    return 0
done
```

- [ ] **Step 9: Add the changelog entry**

Under `[Unreleased]`, add:

```markdown
- Aligned bootstrap and installer candidate-list splitting with the scoped `IFS=: read -ra` Bash pattern.
```

- [ ] **Step 10: Run focused GREEN checks**

Run:

```bash
bats --print-output-on-failure --filter "scoped colon splitting" tests/bootstrap.bats tests/install.bats
shellcheck --severity=error bootstrap.sh install.sh
grep -n 'old_ifs' bootstrap.sh install.sh
git diff --check
```

Expected:

- Focused BATS passes.
- ShellCheck exits 0.
- `grep -n 'old_ifs' bootstrap.sh install.sh` exits 1 with no output.
- `git diff --check` exits 0.

- [ ] **Step 11: Run installer/bootstrap validation**

Run:

```bash
bats --print-output-on-failure tests/bootstrap.bats tests/install.bats
bash bootstrap.sh --dry-run
bash install.sh --dry-run
env -u BASE_HOME ./bin/base-test
```

Expected:

- Both BATS files pass.
- Both dry-run commands exit 0.
- `base-test` exits 0.

- [ ] **Step 12: Commit and open the PR**

Run:

```bash
git status --short
git add CHANGELOG.md bootstrap.sh install.sh tests/bootstrap.bats tests/install.bats
git commit -m "Use scoped colon splitting in bootstrap scripts"
git push -u origin enhancement/700-20260614-scoped-path-splitting
```

Open a draft PR:

```bash
bin/basectl gh pr create \
  --repo codeforester/base \
  --base master \
  --head enhancement/700-20260614-scoped-path-splitting \
  --title "Use scoped colon splitting in bootstrap scripts" \
  --draft
```

PR body must include:

```markdown
Fixes #700

Validation:
- RED: `bats --print-output-on-failure --filter "scoped colon splitting" tests/bootstrap.bats tests/install.bats`
- GREEN: `bats --print-output-on-failure --filter "scoped colon splitting" tests/bootstrap.bats tests/install.bats`
- GREEN: `shellcheck --severity=error bootstrap.sh install.sh`
- GREEN: `grep -n 'old_ifs' bootstrap.sh install.sh` exits 1
- GREEN: `git diff --check`
- GREEN: `bats --print-output-on-failure tests/bootstrap.bats tests/install.bats`
- GREEN: `bash bootstrap.sh --dry-run`
- GREEN: `bash install.sh --dry-run`
- GREEN: `env -u BASE_HOME ./bin/base-test`
```

---

## Execution Order

1. Implement and merge #702 first. It is the direct `lib_std.sh` regression and has the narrowest blast radius.
2. Implement and merge #700 second. It is mechanical but touches first-mile installer/bootstrap paths.
3. Re-check open shell sweep issues after both merge. Keep #698, #699, and #701 separate unless the user explicitly asks to extend the train.

## Self-Review

- Spec coverage: #702 acceptance criteria are covered by the new source-structure test, existing UTC/local timestamp tests, ShellCheck, and full `lib_std.bats`. #700 acceptance criteria are covered by source-structure tests, ShellCheck, dry-run smoke tests, and targeted bootstrap/install BATS.
- Placeholder scan: no TBD/TODO/fill-in steps remain.
- Type/signature consistency: all functions keep current public names and return behavior. New arrays are local Bash arrays and stay inside the affected functions.
