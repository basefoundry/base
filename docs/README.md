# Base Documentation

This directory holds design, architecture, and operational documentation for
Base. The top-level [README](../README.md) is the product front door, and
[FAQ.md](../FAQ.md) answers common first-run and product questions. This page is
the documentation map.

For contribution workflow, branch naming, tests, and PR expectations, see
[CONTRIBUTING.md](../CONTRIBUTING.md).

For GitHub labels, milestones, Projects, issue assignment, branch names, and
worktree-based PR trains, see [GitHub Workflow](github-workflow.md).

For release preparation, tagging, GitHub Releases, and the Homebrew tap update,
see [Release Process](release-process.md).

For self-guided or live walkthrough material, see
[Presentations](presentations/README.md).

## Internal Planning Artifacts

The `docs/superpowers/` directory contains agent-written planning artifacts
such as implementation plans and feature specs. These files are useful for
understanding how a change was shaped, but they are not the canonical product
contract. Treat the mapped documents below, the top-level README, FAQ, and
CHANGELOG as the normative documentation for shipped Base behavior.

## Naming Convention

Use stable topic names for documentation files:

- `architecture.md` for the broad product and system architecture.
- `<feature>.md` for focused feature designs such as `ide-bootstrapping.md`.
- `<domain>-<topic>.md` when a shorter topic name would be ambiguous.
- Avoid generic names such as `design.md` once the subject is known.

Document titles can still say whether a page is a design, model, boundary, or
reference. The filename should answer "what is this about?"

## Core Documents

- [Why Base](why-base.md) is the concise evaluator page for why Base exists,
  what it gives a multi-repo workspace, and how it compares with adjacent
  developer-environment tools.
- [Product Assessment](product-assessment.md) records the maintained assessment
  of Base's originality, usefulness, adoption potential, and creator/engineering
  skill evidence.
- [Command Quick Reference](command-reference.md) is the one-page lookup table
  for the current `basectl` command surface and important flags.
- [Technical Overview](technical-overview.md) is the scannable product and
  technical reference: workspace shape, tech stack, three-layer architecture,
  manifest contract, command tables, and file locations.
- [Architecture](architecture.md) describes Base's product direction, command
  model, environment model, manifest shape, and repository conventions.
- [First-Mile Bootstrap](bootstrap.md) documents `bootstrap.sh`, install mode
  selection, handoff commands, and contributor setup.
- [Clean macOS Install Validation](macos-install-validation.md) defines the
  repeatable Homebrew and source checkout validation checklist.
- [Execution Model](execution-model.md) documents the current `basectl` runtime,
  dispatch order, public launchers, and runtime shell behavior.
- [Linux Support](linux-support.md) defines the first Ubuntu/Debian runtime
  support plan and bootstrap boundaries.
- [Runtime Environment](runtime-environment.md) is the canonical reference for
  Base-managed environment variables, `~/.baserc`, and mutability rules.
- [Base Bash Libraries](base-bash-libs.md) documents the standalone
  `base-bash-libs` package, Base's external reusable-library consumption path,
  Homebrew/core readiness path, and the post-migration boundary.
- [Local Observability](observability.md) defines the future local command
  history, last-error explanation, and report model beyond raw runtime logs.
- [Release Process](release-process.md) defines the Base release ceremony,
  version-file policy, GitHub Release flow, and Homebrew tap follow-up.
- [Homebrew Upgrade Rehearsal](homebrew-upgrade-rehearsal.md) defines the
  pre-1.0.0 consumer upgrade proof and records rehearsal results.
- [Testing](testing.md) explains Base's Python, BATS, and hermetic integration
  test layers.
- [Tool Boundaries](tool-boundaries.md) records ecosystem decisions for tools
  such as `mise`, `direnv`, Homebrew, IDEs, Docker, and dotfile managers.

## Presentations

- [Base Presentations](presentations/README.md) documents the presentation
  source-of-truth and export policy.
- [Base Newcomer Orientation](presentations/base-newcomer-orientation.md)
  introduces Base as a workspace control plane for multi-repo development.

## Feature And Boundary Documents

- [IDE Bootstrapping](ide-bootstrapping.md) covers project IDE manifests,
  supported IDEs, extensions, additive settings, and diagnostics.
- [Local Config](local-config.md) covers user-local Base config, precedence,
  sync guidance, and the user/project boundary.
- [Project Installers](project-installers.md) defines how project-owned
  installers should use Base without moving product-specific logic into Base.
- [Artifact Adapter Registry](artifact-adapter-registry.md) designs the
  declarative registry and adapter boundary for Base-managed artifacts.
- [Python Manifest Section](python-manifest.md) records the structured Python
  manifest shape, uv adoption paths, and its relationship to `python-package`
  artifacts.
- [Repository Baseline](repo-baseline.md) documents `basectl repo init`,
  `basectl repo check`, `basectl repo configure`, and the optional
  `basectl repo agent-guidance` layer for standardizing new Base-managed
  repositories.
- [Remote Installer Policy](remote-installer-policy.md) defines the allowed
  remote shell installer URLs, opt-in boundaries, dry-run behavior, and logging
  expectations for setup paths.
- [Workspace Manifest](workspace-manifest.md) defines the local team-shared
  repo-set contract and `basectl workspace --manifest` reporting behavior.
- [Setup Hooks Boundary](setup-hooks.md) records why Base does not support
  arbitrary manifest setup hooks yet.
- [`basectl setup` parallelism](setup-parallelism.md) records why setup stays
  serial for mutating installers and what planning/preflight work should come
  first.
- [`basectl onboard`](basectl-onboard.md) captures the guided setup experience
  and its relationship to project installers.
- [`basectl ci`](basectl-ci.md) defines the non-interactive CI entry point and
  its relationship to Linux runtime support.
- [`basectl check` parallelism](check-parallelism.md) records the evaluation and
  implementation constraints for parallel check probes.
- [Doctor Finding IDs](doctor-findings.md) is the stable reference for
  `BASE-D*`, `BASE-P*`, `BASE-H*`, and `BASE-W*` finding identifiers emitted by
  `basectl doctor --format json`.
- [Base-managed demo project](base-managed-demo-project.md) defines the proof
  project criteria for showing Base's complete workspace workflow.
- [Project Demo Workflow](project-demo-workflow.md) documents `demo.script`,
  `basectl demo`, Base's self-demo, and the `base-demo` reference repository.
- [Demo Maintenance](demo-maintenance.md) defines the `needs-demo` label and PR
  convention for keeping executable demos aligned with product changes.
- [base_cli Runtime Package](base-cli.md) describes the Python CLI foundation
  used by Base and Base-supported project CLIs.
- [GitHub Workflow](github-workflow.md) documents how Base uses GitHub Issues,
  labels, milestones, Projects, worktrees, and PR trains.
