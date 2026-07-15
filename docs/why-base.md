# Why Base

Base is a local operating contract for developers and platform engineers whose
work spans multiple independent Git repositories. It makes a participating repo
set understandable and locally ready without forcing a monorepo or taking
project-specific behavior away from the repositories that own it.

The product outcome is:

```text
inventory -> prepare -> verify -> trust -> onboard -> hand off
```

Base is most useful when setup rules, readiness state, safe execution, and
handoff context would otherwise live in several READMEs, shell sessions, and one
maintainer's memory.

## What Deterministic Means Here

Base uses **deterministic** narrowly. Given declared repository contracts and
the local state Base can inspect, it should produce explicit ordering, stable
findings or machine-readable structures, and clear next actions. Read-only
commands stay read-only, and mutating commands use explicit entry points,
dry-run paths, or consent where appropriate.

It does not mean Base promises hermetic builds, byte-for-byte environments,
transactional updates across every repository, or reproducibility beyond the
external tools and project declarations it orchestrates.

## The Outcome Loop

| Outcome | Shipped evidence today |
|---|---|
| Inventory | `basectl projects list` shows participating repositories; workspace status adds expected, missing, optional, and local-only state; onboarding turns expected-repository state into first-day next actions. |
| Prepare | `basectl setup`, workspace init/clone/pull/configure, and project-owned adapters prepare the declared local state through explicit commands. |
| Verify | `basectl check` and `basectl doctor`, including workspace forms, report readiness with JSON where supported and stable doctor finding IDs. |
| Trust | `basectl trust` keeps manifest-declared project execution behind explicit local approval while leaving inspection paths available. |
| Onboard | `basectl onboard` guides first Base setup; `basectl workspace onboarding` gives a read-only first-day repo-set summary. |
| Hand off | Diagnostics, `basectl history --report`, `.ai-context/`, and `basectl export-context` provide inspectable local evidence for a manual handoff. |

The last step is not yet a single unified artifact. A workspace agent brief and
an issue-oriented handoff bundle are planned in
[#1561](https://github.com/basefoundry/base/issues/1561) and
[#1562](https://github.com/basefoundry/base/issues/1562). Base should not claim
those commands until they ship.

## Product Responsibility Layers

The layers below describe product responsibility, not separately installed
packages:

- **Core outcome:** deterministic local readiness and handoff across independent
  Git repositories.
- **Enabling execution contract:** `base_manifest.yaml`, `basectl`,
  `base-wrapper`, explicit activation, and declared setup/check/test/run/demo/
  build behavior make the outcome executable.
- **Supporting workflow packs:** repository baselines, GitHub issue/branch/PR/
  Project conventions, and guarded release commands support repeatable delivery
  but are not the primary product category.
- **Adapters:** Homebrew, `mise`, uv, IDEs, Dev Containers, Docker, Nix/devenv,
  and AI tools keep ownership of their domains. Base detects, checks, invokes,
  previews, or exports context to them through explicit boundaries.

## What Base Gives You

- A small opt-in contract for independent repositories through
  `base_manifest.yaml`.
- Inventory and workspace onboarding views that do not require cloning or setup
  to inspect repo-set state.
- Human-readable and machine-readable readiness checks through `check`,
  `doctor`, workspace reports, and stable finding IDs.
- Explicit manifest-command trust instead of silently executing project-owned
  command strings.
- A consistent execution surface for setup, test, run, demo, build, and
  activation while each repository keeps its own implementation details.
- Local onboarding, history, and provider-neutral context evidence that another
  person or coding agent can inspect.
- Optional GitHub/repository and release workflow packs for teams that choose
  Base's delivery conventions.
- A macOS-primary support contract with implemented Ubuntu/Debian
  source-checkout runtime and apt-backed setup paths.

For the complete shipped command surface, see the
[README](../README.md#product-layers-and-shipped-commands) and
[Command Quick Reference](command-reference.md).

## Comparison Matrix

| Need | Base's role | Prefer another tool when |
|---|---|---|
| Repo-set inventory and onboarding | Adds Base participation/readiness semantics and read-only workspace reports. | You only need generic repository checkout, sync, status, or command fan-out. |
| Local preparation | Sequences declared Base and project setup with explicit dry-run/consent boundaries. | You need a general machine-convergence, package, runtime, or dotfile system. |
| Readiness | Connects local prerequisites, project contracts, stable findings, and workspace summaries. | A single tool's own health check fully describes the problem. |
| Trusted execution | Requires local approval before manifest-declared project commands or activation sources execute. | You want automatic directory-triggered environment changes or a sandboxed execution platform. |
| Project commands | Provides one umbrella contract while delegating detailed task logic to each repository. | You only need a rich task runner inside one repository. |
| Handoff | Provides current diagnostics, history reports, onboarding views, and context exports; unified brief/report artifacts remain planned. | You need a hosted agent runtime, live session transfer, or provider-specific collaboration service. |
| Repository and release workflow | Offers optional GitHub-primary conventions and guarded release support. | Another forge or delivery system already owns the workflow. |
| Environment isolation | Integrates with project-selected substrates. | Hermetic shells, containers, or reproducible build graphs are the primary outcome. |

## Target Users

Base is a strong fit when:

- your daily work crosses several independent Git repositories;
- each repository should keep owning its code, tests, services, and setup
  details;
- you need explicit local readiness and next-action evidence before work starts;
- work moves between maintainers, teammates, or coding agents and private
  context is a recurring risk;
- you prefer explicit activation and trust over hidden shell changes;
- Base's optional GitHub/release conventions reduce repeated delivery judgment.

Base is not the first tool to choose when:

- you work in one simple repository with no recurring handoff problem;
- a monorepo is the correct source and ownership model;
- generic multi-repo clone/sync/status is the whole requirement;
- language version pinning, dotfiles, or task execution is the whole
  requirement;
- a Nix-style environment, container platform, or hermetic build system is the
  primary product outcome;
- you need a hosted agent session manager, provider upload service, or live
  collaboration system;
- you require non-Git source control or broad Windows support today.

## How Base Fits With Existing Tools

Base is designed to compose with tools developers already use:

- Use Homebrew or the platform package manager for ordinary system packages.
- Use [`mise`](https://mise.jdx.dev/bootstrap.html) when declarative machine or
  project bootstrap is the main outcome, including packages, repositories,
  dotfiles, shell activation, services, tools, environment, and tasks.
- Use [`mani`](https://manicli.com/) for a declarative Git repository inventory,
  synchronization, worktrees, filtering, cross-repo tasks, or a TUI.
- Use [`gita`](https://github.com/nosarthur/gita) for a lightweight personal Git
  registry, status dashboard, and batch Git or shell commands.
- Use [`vcs2l`](https://ros-infrastructure.github.io/vcs2l/) for multiple VCS
  types or reproducible ROS-style repository-set import and export.
- Use [Android Repo](https://source.android.com/docs/setup/reference/repo) for a
  manifest-controlled, revision-synchronized source tree or Gerrit workflow.
- Use [`west`](https://docs.zephyrproject.org/latest/develop/west/index.html) for
  Zephyr-style manifest workspaces, revisions, groups, and domain extensions.
- Use uv for Python dependency resolution, lockfiles, and project-local
  environments when the project chooses it.
- Use [`direnv`](https://direnv.net/) when automatic directory-based environment
  loading is the desired local convenience.
- Use [Devbox](https://www.jetify.com/docs/devbox),
  [Nix](https://nix.dev/), [devenv](https://devenv.sh/), or
  [Dev Containers](https://containers.dev/overview) when stronger environment
  reproducibility or containerized development is the center of the problem.
- Use [`just`](https://just.systems/man/en/), [Task](https://taskfile.dev/),
  Make, or language-native scripts for detailed task definitions.
- Let IDEs and AI tools own editor behavior, live sessions, accounts,
  credentials, and provider policy. Base's adapters remain additive and
  provider-neutral.

These tools can materialize or manage repositories before Base inspects the
opted-in projects. Base ships no adapter or manifest import for `mani`, `gita`,
`vcs2l`, Android Repo, or `west` today; the external configuration remains
authoritative, and any future integration is a separate proposal.

Base's job is to read the participating repository contract, invoke the chosen
tool openly, report readiness in a Base-native way, and leave enough local
evidence for the next operator to continue safely.

For deeper ecosystem decisions, see [Tool Boundaries](tool-boundaries.md).
