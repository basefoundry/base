# Base AI Context Index

Recommended read order for an AI assistant:

1. `PROJECT.md` - start here for a compact understanding of Base.
2. `STATUS.md` - read next for current version and active development areas.
3. `ARCHITECTURE.md` - read when discussing design, boundaries, or runtime.
4. `COMMANDS.md` - read when discussing `basectl` behavior or command changes.
5. `WORKFLOWS.md` - read when doing repo work, PRs, validation, or releases.
6. `DECISIONS.md` - read when evaluating proposals against durable choices.
7. `README.md` - read when maintaining this context pack.

## Canonical Sources

These context files summarize the live repository. Prefer the canonical sources
below when precise detail matters:

- `README.md` - product front door and current command overview.
- `docs/README.md` - documentation map.
- `docs/product-requirements.md` - accepted product intent, target users,
  durable requirements, non-goals, and PRD maintenance rules.
- `docs/architecture.md` - product direction, command model, environment model,
  and repository conventions.
- `docs/execution-model.md` - `basectl` runtime and dispatch contract.
- `docs/runtime-environment.md` - Base-managed variables and mutability rules.
- `docs/tool-boundaries.md` - external tool boundary decisions.
- `docs/github-workflow.md` - issues, labels, milestones, Projects, branches,
  worktrees, PRs, and cleanup.
- `docs/testing.md` - validation layers and when to broaden tests.
- `docs/release-process.md` - release ceremony and Homebrew tap handoff.
- `CHANGELOG.md` - current release and unreleased changes.
- `AGENTS.md` - repo-specific instructions for AI coding agents.
