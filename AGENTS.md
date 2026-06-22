# Codex Guidance

This file gives coding agents the repository-specific rules for Base. It is a
navigation layer over the existing contributor docs, not a replacement for
them.

## Working Agreement

- Follow `CONTRIBUTING.md` for workflow and `STANDARDS.md` for code standards.
- Keep Base focused as the shared developer workspace control plane.
- Keep project-specific setup, service code, and application behavior in the
  owning project repository unless Base is explicitly the right shared layer.
- Adopt external agent workflow ideas only after translating them into
  Base-specific guidance. Do not vendor or require a third-party methodology
  when a smaller Base-native rule is enough.
- When the user explicitly says a session is design-only or asks for no code
  changes, stay in discussion mode and do not edit files.
- Surface unresolved product or architecture decisions instead of silently
  choosing defaults for broad changes.

## GitHub Workflow

- Create or choose a GitHub issue before implementation work.
- Use one primary category label: `bug`, `enhancement`, `documentation`, `ci`,
  or `security`.
- Do not create or apply `type:*` issue labels.
- Assign Codex-created Base repository issues to `codeforester` when GitHub
  allows it; `.github/base-project.yml` carries this repo-local default for
  `basectl gh issue create`.
- For issues tracked in Base Roadmap, set Project `Status` to `In Progress`
  before implementation starts, move it to `In Review` when the PR opens, and
  verify `Done` after merge/closure. If Project V2 access or item state
  prevents an update, mention that in the work summary.
- When creating issues, choose Project `Size` from actual scope: `T` for tiny
  obvious work, `S` for normal small work or unknown scope, `M` for interacting
  changes, and `L` only for work that should probably be split.
- Prefer `basectl gh` for supported issue, branch, PR, check, and cleanup
  operations.
- Fall back to the GitHub connector, raw `gh`, or `git` when `basectl gh` does
  not support the needed operation or local tooling is unavailable.
- Branch from `origin/main` with
  `<category>/<issue>-<YYYYMMDD>-<slug>`.
- Use a dedicated worktree under `~/work/base-worktrees/<slug>` for PR work.
- Before creating a worktree, check whether the current checkout is already a
  linked worktree for the intended issue.
- Link PRs with `Fixes #<issue>` or `Closes #<issue>` when merge should close
  the issue.
- After merge, sync `main`, remove the worktree, and delete local and remote
  branches.

See `docs/github-workflow.md` for the full policy, including PR body sections,
milestones, GitHub Projects, and cleanup rules.

## Validation

- Run the narrowest relevant checks first, then broaden when shared behavior is
  touched.
- For bug fixes, reproduce the symptom and identify the root cause before
  changing code. Prefer one focused hypothesis and one focused fix at a time.
- Do not claim work is fixed or complete without fresh verification output from
  the current checkout or worktree.
- For documentation-only changes, run `git diff --check`.
- For general Base changes, run `basectl test base` and `git diff --check`.
- For shell changes, include the relevant BATS tests and ShellCheck when
  available.
- For Python changes, run the relevant pytest target with Base's existing
  `PYTHONPATH` conventions.
- For setup, doctor, workspace discovery, profile, runtime shell, or
  cross-command behavior, run the matching integration checks described in
  `docs/testing.md`.
- If a required check cannot be run locally, say so in the PR and final
  summary.
- For review feedback, verify the suggestion against Base's architecture,
  product boundaries, and existing tests before implementing it.

## AI Context Maintenance

- Treat `.ai-context/` as the AI-facing orientation layer for Base.
- For every meaningful PR, decide whether `.ai-context/` needs an update and
  state the result in the PR body.
- Update `.ai-context/` when a change affects Base's product shape,
  architecture, command surface, workflows, manifest model, release status, or
  durable design decisions.
- Usually leave `.ai-context/` unchanged for typo-only edits, formatting-only
  edits, test-only changes with no product behavior impact, or internal
  refactors that do not change public behavior or architecture.
- Keep `.ai-context/` public-repo-safe: no secrets, API keys, tokens, private
  local paths, customer data, or personal notes.
- Canonical docs remain the source of truth. If `.ai-context/` disagrees with
  the repo docs or code, update `.ai-context/`.

## Change Boundaries

- Keep public launchers in `bin/` thin.
- Keep Bash command implementations under `cli/bash/commands/<command>/`.
- Keep Python framework code under `lib/python/` and command packages under
  `cli/python/`.
- Use structured parsers or existing Base helpers instead of ad hoc text
  manipulation when the repo provides one.
- Keep stdout for user or automation output; send logs and diagnostics to
  stderr.
- Do not rely on `set -e`, `set -u`, or `set -o pipefail` in Base shell code.
- Do not add repo-level Codex settings for personal model, approval, or sandbox
  defaults. Those belong in the user's Codex configuration unless the change is
  explicitly about shared repository runtime behavior.
