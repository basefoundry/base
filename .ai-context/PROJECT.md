# Base Project Context

## Identity

- Name: Base
- Repository: `github.com/basefoundry/base`
- Current release: `1.6.1`
- Primary platform: macOS
- Linux posture: Ubuntu/Debian runtime support, source-checkout validation, and
  apt-backed setup are implemented and tested; broader Linux distribution
  support remains tracked in `docs/linux-support.md`.
- Windows support is not currently in scope.

Base is a local operating contract for developers and platform engineers who
work across multiple independent Git repositories. Its core outcome is
deterministic local readiness and handoff without turning the repo set into a
monorepo.

## Why It Exists

Real engineering work often spans several peer repositories, while readiness
rules and handoff context are scattered across docs, shell state, and maintainer
memory. Base makes participation, local state, trusted execution, onboarding,
and next actions inspectable while each repository keeps ownership of its code,
tests, services, and project-specific setup.

Deterministic is a narrow claim: declared inputs and inspectable local state
should produce explicit ordering, stable findings or machine-readable
structures, and clear next actions. Base does not promise hermetic builds,
byte-for-byte environments, or transactional multi-repository updates.

## Product Loop

Base's coherent loop is:

```text
inventory -> prepare -> verify -> trust -> onboard -> hand off
```

The `base_manifest.yaml`/`basectl` execution contract enables the loop.
Repository/GitHub/release commands are supporting workflow packs;
environment/IDE/container/AI behavior stays in adapter or export lanes.

## Current Shape

Base exposes `basectl` as the public control-plane command. `basectl` dispatches
to Bash command modules and delegates structured project logic to Python through
`base-wrapper`.

Participating projects declare `base_manifest.yaml`. Base discovers projects
under a shared workspace root, reads manifests, and orchestrates setup, checks,
activation, declared test commands, build targets, run commands, demos, and
workspace reports.

Repository discovery, clone or synchronization, status, and command fan-out are
shared ecosystem primitives rather than Base's differentiation. Base adds
participation semantics, readiness findings, explicit execution trust,
lifecycle guidance, onboarding, and portable handoff evidence.

Manifest-declared commands are treated as project-owned code. Base keeps
read-only inspection paths available, but requires explicit local
manifest-command trust before executing declared project commands or activation
sources from an unfamiliar or changed manifest.

Current onboarding, check/doctor findings, `history --report`, and
`export-context` provide evidence for a manual handoff. Unified workspace and
issue handoff artifacts remain planned in open issues #1561 and #1562; they are
not shipped commands.

## Peer Projects

- `banyanlabs` - a realistic platform engineering learning environment that
  uses Base-managed setup and validation.
- `base-demo` - reference demo project for proving Base-managed workflows.
- `base-platform-tools` - optional sibling utilities repository. Base can add
  its `bin/` directory to PATH when present, but it is not required.
