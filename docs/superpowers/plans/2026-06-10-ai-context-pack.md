# AI Context Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the initial `.ai-context/` pack and PR maintenance guidance for issue #568.

**Architecture:** The context pack is a root-level Markdown directory split by topic. Each file summarizes the current repo and points back to canonical docs instead of replacing them.

**Tech Stack:** Markdown documentation, Base contributor guidance, GitHub PR template.

---

### Task 1: Add The Context Pack

**Files:**
- Create: `.ai-context/README.md`
- Create: `.ai-context/INDEX.md`
- Create: `.ai-context/PROJECT.md`
- Create: `.ai-context/ARCHITECTURE.md`
- Create: `.ai-context/COMMANDS.md`
- Create: `.ai-context/WORKFLOWS.md`
- Create: `.ai-context/DECISIONS.md`
- Create: `.ai-context/STATUS.md`

- [ ] **Step 1: Create topic files**

Create the eight Markdown files listed above.

- [ ] **Step 2: Populate from canonical docs**

Use `README.md`, `docs/architecture.md`, `docs/execution-model.md`, `docs/runtime-environment.md`, `docs/tool-boundaries.md`, `docs/github-workflow.md`, `docs/testing.md`, `docs/release-process.md`, `CHANGELOG.md`, and `basectl --help` as source material.

- [ ] **Step 3: Sanity-check scope**

Confirm the files are concise, AI-facing, human-reviewable, and free of secrets or local private details.

### Task 2: Add PR Maintenance Guidance

**Files:**
- Modify: `AGENTS.md`
- Modify: `.github/pull_request_template.md`

- [ ] **Step 1: Update agent guidance**

Add a small `AI Context Maintenance` section to `AGENTS.md` explaining when `.ai-context/` should be updated and when it can be left unchanged.

- [ ] **Step 2: Update the PR checklist**

Add one checklist item requiring the PR body to say whether AI context was updated or not applicable.

### Task 3: Validate

**Files:**
- Validate all files changed by this plan.

- [ ] **Step 1: Run whitespace validation**

Run:

```bash
git diff --check
```

Expected: no output and exit status 0.

- [ ] **Step 2: Inspect the final diff**

Run:

```bash
git diff --stat
git diff -- .ai-context AGENTS.md .github/pull_request_template.md docs/superpowers/specs/2026-06-10-ai-context-pack-design.md docs/superpowers/plans/2026-06-10-ai-context-pack.md
```

Expected: changes are limited to issue #568 documentation and guidance.
