# GitHub Copilot Instructions

Use `AGENTS.md` as the canonical workflow guidance for Base. These instructions
exist to point Copilot at the same repository-owned rules used by other coding
agents; they do not replace `AGENTS.md`, `CONTRIBUTING.md`, `STANDARDS.md`, or
the `.ai-context/` orientation files.

Keep Base focused as the shared developer workspace control plane. Project
application code, project-specific setup, service behavior, and one-off local
machine preferences belong in the owning project unless Base is explicitly the
right shared layer.

For implementation work, use Base's issue-backed workflow:

- choose or create the GitHub issue before editing;
- use the branch shape `<category>/<issue>-<YYYYMMDD>-<slug>`;
- link pull requests with `Fixes #<issue>` or `Closes #<issue>`;
- keep Project metadata updated as described in `AGENTS.md`;
- update `.ai-context/` when a change affects Base's product shape,
  architecture, command surface, manifest model, release status, or durable
  workflow guidance.

Follow `CONTRIBUTING.md` for contribution flow and `STANDARDS.md` for coding
standards. Prefer existing Base helpers, structured parsers, and local command
patterns over new one-off conventions.

Use the narrowest relevant validation first:

- documentation-only changes: `git diff --check`;
- Python changes: run the focused pytest target with `PYTHONPATH=lib/python:cli/python`;
- Bash command changes: run the focused BATS tests;
- general Base changes: run `env -u BASE_HOME ./bin/base-test` when practical.

Copilot cloud-agent sessions may run `.github/workflows/copilot-setup-steps.yml`
before work starts. That workflow is only a lightweight environment guardrail;
pull requests still need the focused validation above and normal CI review.

Do not require GitHub Copilot for Base development, add personal Copilot or
Codex settings, store credentials, or introduce third-party agent methodology as
a repo requirement. Translate useful external workflow ideas into smaller
Base-native guidance.
