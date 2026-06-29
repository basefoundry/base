# Base Product Requirements

Status: maintained product requirements document
Last reviewed: 2026-06-29
Base era reviewed: 1.3.0

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

Base is a macOS-first local workspace control plane for developers who keep
multiple Git repositories checked out side by side. It gives that peer-repo
workspace one consistent command surface for setup, diagnostics, project
discovery, activation, tests, demos, builds, repository workflow, release
support, and local AI context exports.

Base should make a multi-repo workspace understandable, repeatable,
diagnosable, and easier to onboard without turning the workspace into a
monorepo or replacing mature project-local tools.

The durable product loop is:

```text
discover -> setup -> activate -> run -> test -> doctor -> fix -> onboard
```

Major product work should strengthen that loop at the project or workspace
level. Work that does not strengthen that loop should remain outside Base core
unless real use proves that it needs Base's orchestration model.

## Target Users

Base is built first for developers whose real work spans multiple sibling
repositories under one workspace root. The strongest fit is:

- platform, infrastructure, SRE, internal developer platform, and tooling
  engineers;
- maintainers who need repeatable onboarding across several related
  repositories;
- developers who want explicit project activation instead of hidden
  directory-triggered environment changes;
- teams that want shared setup, check, doctor, test, demo, build, repo, and
  release entry points without forcing a monorepo.

Base is a weaker fit for developers who work in one simple repository, only
need language version pinning, primarily need a fully reproducible container or
Nix-style shell, want automatic environment changes on `cd`, or want a broad
dotfile manager.

## Core Jobs

Base should help a target user answer these questions quickly:

- Which repositories belong to this local workspace?
- What has each project declared through `base_manifest.yaml`?
- What is missing before this project can be set up, tested, run, demoed, or
  activated?
- Which setup or diagnostic command should I run next?
- How do I enter a controlled project shell without changing my parent shell?
- How do I run common project commands without relearning each repository?
- How do I apply Base's repository, issue, branch, PR, Project, and release
  workflow conventions?
- How do I export repo-visible AI context without depending on a
  provider-specific upload path?
- How do I render repo-owned prompts for review workflows without moving
  private prompt libraries into Base?

## Requirements

### Workspace Control Plane

- Base must discover participating peer repositories under a shared workspace
  root when they opt in with `base_manifest.yaml`.
- Base must provide one public control-plane command, `basectl`, for common
  workspace and project workflows.
- Base must keep project repositories independent. It must not require a
  monorepo or move product-specific application behavior into Base.
- Base must make dry-run, check, doctor, and JSON-capable output useful for
  humans and automation.

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
- a full reproducible package manager or environment solver;
- a local services platform;
- a container runtime;
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
- the product boundary stays clear as new integrations are added;
- the release, install, upgrade, and Homebrew paths are boring and repeatable;
- another contributor or AI-assisted agent can follow the docs, issues, tests,
  and context pack without needing private maintainer knowledge;
- repo-owned prompts and context exports make periodic product and workflow
  reviews repeatable without becoming hidden private process;
- external adoption evidence grows without widening Base into a catch-all
  developer tools bundle.

## Platform Scope

The current support contract is macOS-first. Linux support is a design target
and should advance through narrow, tested support slices before Base makes
broader platform claims. Windows support is not currently in scope.

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
