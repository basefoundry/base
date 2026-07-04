# Base Internal Manifests

This directory contains Base-owned manifests that seed Base setup behavior.
They are not examples of project-local `base_manifest.yaml` files.

## Files

- `default_manifest.yaml`
  Defines bootstrap Python packages that Base installs before reconciling a
  project's remaining artifacts. These entries are part of Base's own runtime
  bootstrap contract.
- `dev_manifest.yaml`
  Defines the optional `dev` prerequisite profile for Base contributors, such
  as BATS, GitHub CLI, and ShellCheck.
- `sre_manifest.yaml`
  Defines the optional `sre` prerequisite profile for local operations and
  diagnostics tooling.
- `artifact-registry.yaml`
  Defines Base's bundled artifact registry using schema version `1`. The
  Python setup layer loads and validates this file before resolving built-in
  artifact definitions for setup, check, and doctor.

## Ownership

These manifests are maintained with Base because they describe Base's own setup
defaults and opt-in profiles. Project repositories should declare their own
tools, commands, tests, demos, activation hooks, and project-specific artifacts
in their own `base_manifest.yaml`.

The `ai` and `linux-lab` prerequisite profiles are code-backed because they
manage special host tool policies rather than manifest-declared Homebrew
artifacts.

Keep schema and behavior details in the canonical documentation instead of
duplicating them here:

- [Project manifest architecture](../../docs/architecture.md#project-manifest)
- [Python manifest section](../../docs/python-manifest.md)
- [Artifact adapter registry](../../docs/artifact-adapter-registry.md)
- [Base README setup notes](../../README.md)
