# Forge Support Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document Base's Git-only and GitHub-primary support contract so non-GitHub Git users get predictable guidance instead of implicit assumptions.

**Architecture:** Add one canonical support-boundary page and link existing command and workspace docs to it. Keep this PR documentation-focused; defer provider adapters or new GitLab/Bitbucket behavior until GitHub-first adoption proves the need.

**Tech Stack:** Markdown, existing docs map, existing Base validation commands.

---

### Task 1: Add The Canonical Support Contract

**Files:**
- Create: `docs/source-control-and-forge-support.md`
- Modify: `docs/README.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Create the support-boundary page**

Add `docs/source-control-and-forge-support.md` with these sections:

```markdown
# Source Control And Forge Support

## Support Contract

## Command Compatibility

## Non-GitHub Git Workspaces

## Future Forge Support

## Clean Failure Expectations
```

The page must state that Git is required, non-Git SCMs are out of scope, GitHub is first-class today, and GitLab/Bitbucket support is deferred until adoption proves the need.

- [ ] **Step 2: Link the page from the docs map**

Add a Core Documents or Feature And Boundary Documents bullet in `docs/README.md` pointing to the new page.

- [ ] **Step 3: Update architecture wording**

Modify `docs/architecture.md` so the overview keeps the GitHub-primary product loop but points readers to the support-boundary page for exact non-GitHub behavior.

### Task 2: Correct Command And Workspace Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/command-reference.md`
- Modify: `docs/workspace-manifest.md`

- [ ] **Step 1: Add the product-front-door summary**

Add a short README section explaining that Base is Git-based, GitHub-primary, and still useful for local non-GitHub Git projects through the local command loop.

- [ ] **Step 2: Clarify command-reference categories**

Add a short compatibility note near the command tables in `docs/command-reference.md`, and make GitHub-only commands explicit where the table could otherwise imply forge independence.

- [ ] **Step 3: Fix workspace manifest clone wording**

Adjust `docs/workspace-manifest.md` so `repos[].url` remains generic metadata for reporting, while current `basectl workspace clone` support is documented as GitHub-only when materializing missing repositories.

### Task 3: Validate And Publish

**Files:**
- Validate all touched docs and existing tests.

- [ ] **Step 1: Run focused docs validation**

Run:

```bash
env -u BASE_HOME PYTHONPATH=lib/python:cli/python \
  "$HOME/.base.d/base/.venv/bin/python" -m pytest \
  tests/test_base_cli_docs.py tests/test_contract_hardening.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full Base validation**

Run:

```bash
env -u BASE_HOME BASE_BASH_LIBS_DIR=/Users/rameshhp/work/base-bash-libs/lib/bash BASE_CACHE_DIR=/private/tmp/base-1344-final ./bin/base-test
```

Expected: Python suite and Bats/source suite pass.

- [ ] **Step 3: Commit and open the PR**

Commit with:

```bash
git add README.md docs/README.md docs/architecture.md docs/command-reference.md docs/source-control-and-forge-support.md docs/workspace-manifest.md docs/superpowers/plans/2026-07-01-forge-support-boundaries.md
git commit -m "Document forge support boundaries"
```

Push `documentation/1344-20260701-forge-support-boundaries` and open a PR linked to issue `#1344`.
