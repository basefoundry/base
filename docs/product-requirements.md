# Base Product Requirements

Status: maintained product requirements document
Last reviewed: 2026-07-14
Base era reviewed: 1.6.1 + Unreleased

This document is the product-facing source of truth for what Base is trying to
be, who it serves, which outcomes matter, and what boundaries should guide
future work. It records accepted product intent, not every brainstorm or
implementation detail.

For the concise evaluator page, see [Why Base](why-base.md). For system design,
see [Architecture](architecture.md). For ecosystem decisions, see
[Tool Boundaries](tool-boundaries.md). For candid product review, adoption
risks, and evidence quality, see [Product Assessment](product-assessment.md).
For execution tracking, use GitHub Issues and the workflow in
[GitHub Workflow](github-workflow.md).

## Product Thesis

Base is a local operating contract for developers and platform engineers who
work across multiple independent Git repositories. It should make the repo set
understandable, locally ready, explicitly trusted, onboardable, and transferable
without forcing a monorepo or taking project behavior away from its owning
repository.

The durable product loop is:

```text
inventory -> prepare -> verify -> trust -> onboard -> hand off
```

In this PRD, **deterministic** means declared inputs and inspectable local state
lead to explicit ordering, stable findings or machine-readable structures, and
clear next actions. Read-only commands stay read-only; mutation uses named
commands, dry-run paths, or consent where appropriate. It does not mean Base
promises hermetic builds, byte-for-byte environments, or transactional updates
across every repository and external tool.

Base remains macOS-primary. Ubuntu/Debian source-checkout runtime and apt-backed
setup support are implemented, while broader Linux distribution support remains
intentionally narrow and Windows is not currently in scope.

Major product work should improve the outcome loop. A broad command is not core
merely because Base can expose it.

## Product Responsibility Layers

These layers classify product responsibility; they are not separately installed
packages.

1. **Core outcome:** deterministic local readiness and handoff across
   independent Git repositories.
2. **Enabling execution contract:** `base_manifest.yaml`, `basectl`,
   `base-wrapper`, explicit activation, and project-declared setup/check/test/
   run/demo/build behavior make the core outcome executable.
3. **Supporting workflow packs:** repository baselines, GitHub issue/branch/PR/
   Project conventions, and guarded release behavior support delivery but do
   not define Base's primary category.
4. **Adapters:** environment managers, IDEs, containers, Nix/devenv, and AI
   tools keep ownership of their domains. Base may detect, check, invoke,
   preview, or export context through narrow adapters.

## Target Users

Base is built first for people whose real work spans independent Git
repositories under one workspace root and who repeatedly transfer that work or
its context. The strongest fit is:

- platform, infrastructure, SRE, internal developer platform, and tooling
  engineers;
- maintainers who need repeatable readiness, onboarding, and handoff across
  several related repositories;
- developers who want explicit project activation instead of hidden
  directory-triggered environment changes;
- teams that want a shared local contract without forcing a monorepo;
- human and AI-assisted implementers who need public, inspectable evidence
  instead of private maintainer context.

## Non-Target Users

Base is not the first tool for users who:

- work in one simple repository with no recurring readiness or handoff problem;
- should consolidate into a monorepo;
- only need generic repository clone/sync/status or command fan-out;
- only need language version pinning, task execution, or dotfile management;
- primarily need a hermetic build, fully reproducible Nix-style shell, or
  container platform;
- want automatic environment changes on `cd`;
- need a hosted agent runtime, live session transfer, or provider upload
  service;
- require non-Git source control or broad Windows support today.

## Core Jobs

Base should help a target user answer one question at each step:

- **Inventory:** Which repositories participate, which are expected, and what
  has each declared?
- **Prepare:** What explicit setup or materialization step is required?
- **Verify:** What is ready, what is missing, and which stable finding or next
  command explains it?
- **Trust:** Which project-owned commands or activation sources have been
  reviewed and approved locally?
- **Onboard:** Can a technically adjacent user understand the first-day state
  without private instructions?
- **Hand off:** What diagnostics, recent activity, context, validation guidance,
  and canonical instructions can the next human or agent inspect?

## Requirements

### Core Outcome

- Base must discover participating peer repositories under a shared workspace
  root when they opt in with `base_manifest.yaml`.
- Base must inventory discovered and manifest-expected repository state without
  requiring setup or mutation.
- Base must provide one public command, `basectl`, for the local operating
  contract.
- Base must keep project repositories independent. It must not require a
  monorepo or move product-specific application behavior into Base.
- Base must make dry-run, check, doctor, and JSON-capable output useful for
  humans and automation.
- Base must keep deterministic claims limited to its declared inputs,
  inspection order, findings, output contracts, and explicit next actions.

### Handoff

- Base must preserve current handoff evidence through onboarding views,
  diagnostics, stable finding IDs, privacy-conscious history reports, canonical
  repo guidance, and provider-neutral context exports.
- Base must distinguish the shipped workspace readiness brief from broader
  issue-oriented handoff packaging.
- `basectl workspace agent-brief` must remain a local, read-only text or stable
  JSON view over workspace manifest and filesystem evidence. It must include
  expected and extra Base-managed repositories and report unavailable evidence
  explicitly.
- The issue-oriented handoff bundle planned in
  [#1562](https://github.com/basefoundry/base/issues/1562) is accepted direction,
  not a current command claim.
- Handoff artifacts must remain local-first, deterministic enough for tests,
  redacted, provider-neutral, and explicit about unavailable evidence.

### Project Contract

- Base must keep the project manifest contract small, explicit, and
  inspectable.
- Project repositories must own their application code, service definitions,
  tests, and product-specific setup.
- Base may orchestrate project-declared setup, check, test, run, demo, build,
  activation, IDE, and release behavior, but it should not silently infer broad
  ownership from incidental files.
- Base must report manifest and runtime problems through stable diagnostics
  where durable automation depends on them.

### Activation And Runtime

- Base must keep ordinary shell startup separate from full Base runtime
  activation.
- Project activation must be explicit and reversible by exiting a subshell.
- Base must preserve a narrow user-local configuration surface and avoid
  becoming a general dotfile manager.
- Public launchers must stay thin, with Bash owning runtime orchestration and
  Python owning structured parsing, discovery, JSON output, and reusable CLI
  framework behavior.

### Tool Integration

- Tool integrations are adapters to the local operating contract, not equal
  product pillars.
- Base must orchestrate mature tools openly instead of hiding or replacing
  them.
- Integrations should detect relevance, check health, invoke the underlying
  tool transparently, report failures in Base-native diagnostics, and avoid
  owning the tool's full configuration model.
- Base should coexist strongly with tools such as Homebrew, `mise`, uv, Docker,
  IDEs, project task runners, Devbox, Nix, and Dev Containers where a project
  chooses them.
- Built-in artifact support may cover Base-managed artifacts with explicit
  manifest declarations. External artifact adapters should remain constrained
  and evidence-driven before becoming part of Base core.
- New tool-family support must remain explicit and opt-in until real usage
  proves a narrower Base-owned contract.

### Repository And Release Workflow

- Repository and release behavior is a supporting workflow pack, not the core
  product outcome.
- Base must use GitHub Issues as the durable product backlog and activity
  tracker.
- Base repository work should use issue-backed branches, dedicated worktrees,
  pull requests, validation, and Project metadata as documented in
  [GitHub Workflow](github-workflow.md).
- Base may render repo-declared pull request policy from project manifests, but
  issues, pull requests, milestones, and Projects remain the durable GitHub
  source of truth for execution state.
- Release support must remain guarded and explicit, with changelog, version,
  GitHub Release, and Homebrew tap handoff behavior documented in
  [Release Process](release-process.md).

### AI Context

- AI behavior is an adapter and handoff-support surface. Base does not own live
  agent execution.
- Base may maintain repo-visible `.ai-context/` files and repo-owned prompt
  templates as curated orientation and review surfaces for AI assistants.
- Canonical docs remain the source of truth. `.ai-context/` must summarize
  current repository state and must be updated when product shape,
  architecture, workflows, command surface, manifest model, or durable
  decisions change.
- Repo-owned prompts must stay inspectable, provider-neutral, and tied to
  current repository evidence. Private prompt libraries remain outside Base's
  public product contract.
- Base must not promise provider-specific AI upload support until official
  supported APIs and privacy boundaries are confirmed.

## Non-Goals

Base should not become:

- a general tool version manager;
- an automatic directory-based environment loader;
- a full dotfile manager;
- a generic task runner;
- a generic multi-repository checkout, sync, or command fan-out manager;
- a full reproducible package manager or environment solver;
- a local services platform;
- a container runtime;
- a hosted agent runtime, session-transfer service, or provider upload system;
- a replacement for GitHub CLI, IDEs, Homebrew, `mise`, uv, Docker, Nix,
  Devbox, Dev Containers, `just`, Taskfile, or project-owned build systems.

Base can learn from and integrate with those tools. It should not absorb their
complete domains.

## Success Criteria

Base is succeeding when:

- a target user can understand the product in a few minutes from `README.md`,
  [Why Base](why-base.md), and this PRD;
- a new Base-managed project can adopt a small manifest and immediately gain
  predictable setup, check, doctor, activation, test, run, demo, or build
  behavior;
- diagnostics reduce repeated human judgment by explaining missing local state
  before commands fail later;
- a target user can follow the inventory-to-handoff loop without mistaking
  Base for a generic repo manager, environment solver, or hosted agent runtime;
- the product boundary stays clear as new integrations are added;
- the release, install, upgrade, and Homebrew paths are boring and repeatable;
- another contributor or AI-assisted agent can follow the docs, issues, tests,
  and context pack without needing private maintainer knowledge;
- the shipped workspace agent brief is described separately from the
  issue-oriented handoff artifact still planned in #1562;
- repo-owned prompts and context exports make periodic product and workflow
  reviews repeatable without becoming hidden private process;
- external adoption evidence grows without widening Base into a catch-all
  developer tools bundle.

## Platform Scope

The current support contract is macOS-primary, with implemented Ubuntu/Debian
source-checkout runtime support and apt-backed setup for conservative Base
prerequisites. Broader Linux distribution support, WSL, and Windows are not part
of the current public support contract.

Any platform expansion must preserve Base's explicit orchestration model and
must update this PRD, the architecture docs, install docs, tests, and release
guidance together.

## Relationship To Other Planning Artifacts

Use this PRD for accepted product intent and durable requirements.

Use GitHub Issues for proposed work, execution tracking, and backlog
prioritization. An idea can start as an issue without being accepted product
direction. Once an issue changes Base's accepted product direction, this PRD
should change in the same pull request or in a clearly linked follow-up.

Use technical docs for implementation detail:

- [Architecture](architecture.md) owns system structure and product direction
  detail.
- [Execution Model](execution-model.md) owns `basectl` runtime and dispatch
  behavior.
- [Runtime Environment](runtime-environment.md) owns Base-managed variables and
  mutability rules.
- [Workspace Manifest](workspace-manifest.md) owns the team-shared repo-set
  contract.
- [Python Manifest Section](python-manifest.md) owns Python and uv manifest
  behavior.
- [Tool Boundaries](tool-boundaries.md) owns ecosystem integration decisions.
- [Product Assessment](product-assessment.md) owns candid assessment,
  adoption risks, and evidence quality.

## Maintenance Rules

Update this PRD when a change:

- changes Base's target user, product thesis, or supported platform contract;
- adds, removes, or materially changes a core user workflow;
- accepts a new Base-owned product responsibility;
- rejects or narrows an adjacent-tool responsibility in a durable way;
- changes the manifest, activation, workspace, repository workflow, release,
  or AI-context contract at the product level;
- would make this document misleading if left unchanged.

Do not update this PRD for isolated implementation details, refactors, tests,
or narrow docs edits that do not change product intent or durable
requirements.

Every product-direction pull request should answer: "Does this change affect
the PRD?" If yes, update this document in the same PR when practical. If not
practical, link a follow-up issue before merging the product change.

Review this PRD during each minor release line, before major product
repositioning, and after meaningful external user feedback.

## Decision Log

- 2026-07-15: Ship the local, read-only workspace agent brief from #1561 with
  text and stable JSON output. Keep `.ai-context` visible but optional, keep
  manifest-declared test execution behind `basectl test`, and leave
  issue-oriented artifact composition to #1562.
- 2026-07-14: Narrow Base's accepted position to a local operating contract for
  deterministic readiness and handoff across independent Git repositories.
  Adopt the `inventory -> prepare -> verify -> trust -> onboard -> hand off`
  outcome loop, classify execution, workflow packs, and adapters by their role,
  and keep unified workspace/issue handoff artifacts explicitly planned in
  #1561 and #1562 rather than claiming them as shipped.
- 2026-06-29: Reviewed for the 1.3.0 release line.
  The 1.3.0 release hardens Base's command lifecycle, documentation entry
  point, CI setup output, setup/install trust path, completions, and validation
  coverage without changing Base's target user, product thesis, or supported
  platform contract. The PRD remains unchanged aside from review metadata and
  this decision record.
- 2026-06-25: Reviewed for the 1.2.0 release line.
  The 1.2.0 release adds workspace initialization, repo-owned prompt rendering,
  local command history, manifest-declared PR policy, Python runtime
  requirements, and Base-managed artifact declarations without changing Base's
  target user or workspace-control-plane thesis.
- 2026-06-22: Add a maintained PRD for Base.
  Base already has product, architecture, boundary, and assessment docs, but
  needs one concise source for accepted product intent, requirements,
  non-goals, and PRD maintenance rules.
