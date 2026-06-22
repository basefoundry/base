# Artifact Adapter Registry

> **DESIGN DOC** — As of Base 1.1.0, Base still uses
> `cli/python/base_setup/registry.py` for built-in artifact mappings. This
> document describes the planned future declarative registry; implementation is
> tracked in [#925](https://github.com/basefoundry/base/issues/925).

This design records how Base should evolve the current built-in artifact
mapping in `cli/python/base_setup/registry.py` without turning project setup
into arbitrary plugin execution.

Today, Base has two artifact behaviors:

- `python-package` artifacts resolve to pip packages installed in the
  Base-managed project virtual environment.
- `tool` artifacts resolve to Homebrew packages installed on the host system.

That behavior is useful but too implicit. The supported artifact list, manager
selection, package name, install target, and diagnostics are encoded in Python.
Adding another artifact family would require changing command code before Base
has a stable vocabulary for describing what it can manage.

## Goals

- Make supported artifacts visible as data before setup, check, doctor, and
  docs need to explain them.
- Keep artifact execution behind typed manager adapters that Base owns and
  tests.
- Let future Base versions support more artifact types without broad command
  rewrites.
- Improve diagnostics by reporting where an artifact definition came from and
  which manager/check path owns it.
- Preserve the current trust model: manifests request supported artifacts, but
  do not inject executable setup commands.

## Non-goals

- No arbitrary project-provided shell hooks.
- No third-party Python plugin loading during setup.
- No automatic remote registry download.
- No repo mutation as part of artifact resolution.
- No attempt to replace native package managers such as Homebrew, uv, npm, Go
  modules, Maven, or Gradle.

## Delegation Boundary

The registry should make Base's orchestration vocabulary more explicit, not
make Base responsible for every installer or dependency solver.

Base should continue to delegate:

- host packages to Homebrew or a project-owned Brewfile;
- Python environments to the current Base project venv path or a future
  structured `python:` contract such as uv;
- language dependencies to native files such as `go.mod`, `package.json`,
  `pom.xml`, or `build.gradle`;
- project tasks to explicit task runners such as mise, just, or repo-local
  scripts;
- container and machine images to tools such as devcontainers, Docker, and Nix.

Registry entries should describe artifacts Base can check and reconcile through
typed adapters. They should not absorb project-specific installers into Base.

## Recommended Shape

Base should introduce the registry in phases.

### Phase 1: Declarative Built-ins

Move the current hard-coded `_ARTIFACTS` table into a built-in declarative
registry bundled with Base, for example `lib/base/artifact-registry.yaml`.
Command behavior remains in Python manager adapters.

Example:

```yaml
version: 1
artifacts:
  - type: python-package
    name: pytest
    manager: pip
    package: pytest
    target: project-venv
    version_policy: requested
    check:
      kind: python_import
      module: pytest

  - type: tool
    name: kubectl
    manager: homebrew
    package: kubernetes-cli
    target: system
    version_policy: latest-only
    check:
      kind: homebrew_package
      package: kubernetes-cli
```

The Python API can stay close to the current code:

```python
@dataclass(frozen=True)
class ArtifactDefinition:
    name: str
    artifact_type: str
    manager: str
    package: str
    target: str
    version_policy: str
    registry_source: str
```

`get_artifact_definition(type, name)` should continue to return one
definition or `None`, so existing setup/check call sites can migrate without
changing their control flow.

### Phase 2: Workspace Overlay Registry

After the built-in registry is data-backed, Base can optionally support a
machine-local workspace overlay configured in `~/.base.d/config.yaml`.

Example:

```yaml
artifact_registry:
  overlays:
    - ~/work/base-artifacts.yaml
```

Overlay entries should be constrained to manager adapters Base already
implements. For example, an overlay can map `tool:internal-cli` to Homebrew
package `company/internal-cli`, but it cannot define a new executable install
script.

Overlay loading should be explicit in diagnostics and JSON output:

```json
{
  "artifact_type": "tool",
  "artifact": "internal-cli",
  "manager": "homebrew",
  "package": "company/internal-cli",
  "target": "system",
  "registry_source": "/Users/example/work/base-artifacts.yaml"
}
```

### Phase 3: Repo-local Registry, If Needed

Repo-local registry files should remain deferred until there is a proven need.
They are more convenient, but they change the trust model because cloning a repo
would also make new setup definitions available.

If Base adds this later, it should be opt-in from user-local config, not
automatic from `base_manifest.yaml`.

## Registry Schema

The first schema should be deliberately small:

| Field | Required | Meaning |
| --- | --- | --- |
| `type` | yes | Manifest artifact type, such as `tool` or `python-package`. |
| `name` | yes | Manifest-facing artifact name. |
| `manager` | yes | Base-owned adapter, such as `homebrew` or `pip`. |
| `package` | yes | Manager-facing package identifier. |
| `target` | yes | Install target, such as `system` or `project-venv`. |
| `version_policy` | yes | Supported version behavior, such as `requested` or `latest-only`. |
| `check.kind` | yes | Base-owned check implementation key. |
| `metadata` | no | Display-only or future extension data. |

Unknown fields should fail validation unless the schema version explicitly
allows them. That keeps typos from silently changing setup behavior.

## Adapter Contract

Registry data should describe artifacts. Manager adapters should own behavior.

Each adapter should provide:

- validation for definitions it can handle;
- check behavior for `basectl check` and `basectl doctor`;
- reconcile behavior for `basectl setup`;
- dry-run rendering;
- structured diagnostics fields.

The initial adapter set is the current behavior:

- `pip` installs into `target: project-venv`;
- `homebrew` installs `target: system` artifacts with `version_policy:
  latest-only`, reports installed-but-outdated packages during check/doctor, and
  upgrades outdated packages during setup.

Adding a new manager should require a Python adapter and tests. Registry data
alone should not be enough to execute new behavior.

## Command Behavior

Registry-backed artifacts should behave the same across setup, check, doctor,
dry-run, and JSON output.

`basectl setup` should resolve each manifest artifact through the registry, then
delegate reconciliation to the manager adapter. The registry selects the
adapter; it does not store shell commands to execute.

`basectl setup --dry-run` should render the adapter-owned action that would run,
including the manager, package, target, version policy, and registry source. A
malformed registry entry or unsupported manager should fail before rendering a
partial install plan.

`basectl check` should report whether each requested artifact is satisfied using
the registry-backed check definition and the manager adapter. Unsupported,
malformed, or policy-incompatible definitions should return actionable findings
instead of collapsing into a generic missing-artifact message.

`basectl doctor` should include the same finding IDs as `check`, plus enough
structured detail for automation to identify the registry entry, manager, and
package mapping that produced the finding.

JSON output should treat registry-backed fields as first-class data rather than
embedding them only in human-readable messages.

## Diagnostics

Artifact diagnostics should include the definition source and manager path
wherever the output is structured. Human messages can stay compact, but JSON
should make support triage possible:

- `artifact_type`
- `artifact`
- `manager`
- `package`
- `target`
- `version_policy`
- `registry_source`
- `finding_id`

Unsupported artifact errors should distinguish:

- no definition found;
- definition found but manager unsupported by this Base version;
- version policy mismatch;
- malformed registry entry.

## Migration Plan

1. Add the bundled registry file and parser.
2. Load the bundled registry in `base_setup.registry`.
3. Keep the current `python-package` fallback for one release if needed, but
   warn in diagnostics when a package resolves through fallback rather than an
   explicit definition.
4. Add registry validation tests for duplicate entries, unknown managers,
   invalid targets, unknown fields, and malformed files.
5. Add JSON diagnostics fields while preserving existing human output.
6. Document the registry surface in `README.md` and this docs map.
7. Only then consider workspace overlay support.

## First Shippable Slice

The smallest implementation that improves the product is Phase 1:

- built-in YAML registry;
- no overlay support;
- no repo-local registry;
- same manager behavior as today;
- focused parser/validation tests;
- unchanged manifest syntax.

That slice makes Base's supported artifacts inspectable while avoiding new
trust or execution risks.
