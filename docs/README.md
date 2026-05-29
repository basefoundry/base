# Base Documentation

This directory holds design, architecture, and operational documentation for
Base. The top-level [README](../README.md) is the product front door; this page
is the documentation map.

## Naming Convention

Use stable topic names for documentation files:

- `architecture.md` for the broad product and system architecture.
- `<feature>.md` for focused feature designs such as `ide-bootstrapping.md`.
- `<domain>-<topic>.md` when a shorter topic name would be ambiguous.
- Avoid generic names such as `design.md` once the subject is known.

Document titles can still say whether a page is a design, model, boundary, or
reference. The filename should answer "what is this about?"

## Core Documents

- [Architecture](architecture.md) describes Base's product direction, command
  model, environment model, manifest shape, and repository conventions.
- [Execution Model](execution-model.md) documents the current `basectl` runtime,
  dispatch order, public launchers, and runtime shell behavior.
- [Linux Support](linux-support.md) defines the first Ubuntu/Debian runtime
  support plan and bootstrap boundaries.
- [Tool Boundaries](tool-boundaries.md) records ecosystem decisions for tools
  such as `mise`, `direnv`, Homebrew, IDEs, Docker, and dotfile managers.

## Feature And Boundary Documents

- [IDE Bootstrapping](ide-bootstrapping.md) covers project IDE manifests,
  supported IDEs, extensions, additive settings, and diagnostics.
- [Local Config](local-config.md) covers user-local Base config, precedence,
  sync guidance, and the user/project boundary.
- [Project Installers](project-installers.md) defines how project-owned
  installers should use Base without moving product-specific logic into Base.
- [`basectl onboard`](basectl-onboard.md) captures the guided setup experience
  and its relationship to project installers.
- [`basectl ci`](basectl-ci.md) defines the future non-interactive CI entry
  point and its relationship to Linux support.
- [`basectl check` parallelism](check-parallelism.md) records the evaluation and
  implementation constraints for parallel check probes.
- [Base-managed demo project](base-managed-demo-project.md) defines the proof
  project criteria for showing Base's complete workspace workflow.
- [base_cli Runtime Package](base-cli.md) describes the Python CLI foundation
  used by Base and Base-supported project CLIs.
