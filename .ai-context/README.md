# AI Context Directory

This directory contains AI-facing project context for Base. It is meant to help
assistants such as Claude, Codex, ChatGPT, and future AI tools orient quickly
before product, architecture, maintenance, or workflow conversations.

The files are curated Markdown, not generated truth. They summarize the current
repo and point back to canonical human documentation when deeper detail is
needed.

## Audience

Use this directory when an AI assistant needs to understand Base without
re-reading the whole repository. The most important current use case is loading
Base context into Claude before voice-based product and architecture
conversations.

## Files

- `INDEX.md` - recommended read order and file map.
- `PROJECT.md` - compact project summary and current identity.
- `ARCHITECTURE.md` - architecture, boundaries, and runtime model.
- `COMMANDS.md` - `basectl` command surface.
- `WORKFLOWS.md` - issue, branch, PR, validation, release, and cleanup flow.
- `DECISIONS.md` - durable product and architecture decisions.
- `STATUS.md` - current version, active work, and recent changes.
- `prompts/` - repo-owned prompts that `basectl prompt` can render for
  AI-assisted Base workflows.

## Maintenance

Update this directory when a change alters Base's product shape, architecture,
command surface, workflows, manifest model, release status, or durable design
decisions.

Usually no update is needed for typo-only edits, formatting-only edits,
test-only changes with no product behavior impact, or internal refactors that
do not change public behavior or architecture.

## Safety

Do not put secrets, API keys, tokens, private local paths, private customer
details, or personal notes in this directory. Keep the content suitable for the
public Base repository.

Canonical docs remain the source of truth. If this directory disagrees with the
repo docs or code, update this directory.
