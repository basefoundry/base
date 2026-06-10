# AI Context Pack Design

## Purpose

Base needs a small, durable context pack that an AI assistant can read before a
product or architecture conversation. The immediate user need is Claude voice
chat during walking or errands: Claude should understand Base's current product
shape without requiring repeated manual explanations.

This pack is not a replacement for Base's human documentation. It is an
AI-facing orientation layer that summarizes the current repo and points back to
canonical source documents.

## Shape

The context lives under `.ai-context/` at the repository root. The root location
makes it easy for tools and agents to discover, while the dot-directory name
signals that the files are AI-facing support material rather than normal user
docs.

The pack is split by topic:

- `README.md` explains purpose, audience, maintenance rules, and safety.
- `INDEX.md` gives the recommended read order.
- `PROJECT.md` gives the compact project summary for voice conversations.
- `ARCHITECTURE.md` summarizes product boundaries and runtime layers.
- `COMMANDS.md` summarizes the current command surface.
- `WORKFLOWS.md` summarizes contribution, validation, release, and PR flow.
- `DECISIONS.md` records durable product and architecture decisions.
- `STATUS.md` records current version, active areas, and recent major changes.

This avoids a single giant file and avoids duplicated summary/detail files that
can drift apart.

## Source Of Truth

The initial content is curated from current repository sources:

- `README.md`
- `docs/README.md`
- `docs/architecture.md`
- `docs/execution-model.md`
- `docs/runtime-environment.md`
- `docs/tool-boundaries.md`
- `docs/github-workflow.md`
- `docs/testing.md`
- `docs/release-process.md`
- `CHANGELOG.md`
- `AGENTS.md`
- `basectl --help`

The `.ai-context/` files should summarize those sources and link to them. When
there is a disagreement, the canonical docs win and `.ai-context/` should be
updated.

## Maintenance

Every meaningful PR should evaluate whether `.ai-context/` needs an update.
Updates are expected for new commands, architecture changes, workflow changes,
manifest schema changes, release/status changes, and durable product decisions.
Typo-only, formatting-only, and test-only changes normally do not need updates.

The PR template should ask authors to state whether AI context was updated or
not applicable. This starts as a human/agent workflow rule, not a hard CI gate.

## Out Of Scope

This issue does not implement provider upload, `basectl export-context`, or
automatic context generation.
