# Pyproject Diagnostics Design

Issue: #358

## Summary

Base should observe a project-local `pyproject.toml` during project diagnostics
without making it a Base configuration source. The first implementation reads
only a `pyproject.toml` file in the same directory as the active
`base_manifest.yaml`, reports a narrow set of metadata findings in
`basectl check` and `basectl doctor`, and does not change setup, activation,
test, run, or dependency reconciliation behavior.

`base_manifest.yaml` remains the explicit Base project contract. Future uv
delegation and the structured `python:` manifest contract remain part of issue
#359.

## Goals

- Detect `pyproject.toml` only beside the active `base_manifest.yaml`.
- Report whether the file is readable TOML.
- Summarize `[project].name` and `[project].requires-python` when present.
- Report that dependency metadata exists without reconciling or installing it.
- Warn when `[tool.base]` exists because Base does not support it in this slice.
- Emit findings through the existing `basectl check` and `basectl doctor`
  pipelines, including JSON output.

## Non-Goals

- Do not search the repository for additional `pyproject.toml` files.
- Do not treat `pyproject.toml` as an alternate manifest.
- Do not read or execute build backend hooks.
- Do not run uv or inspect uv sync state.
- Do not install packages from `[project].dependencies`,
  `[project].optional-dependencies`, or `[dependency-groups]`.
- Do not add a `python:` manifest section in this issue.

## Architecture

Add a small `base_setup.pyproject` module that owns TOML parsing and diagnostic
construction. The module should accept the already-read `BaseManifest`, derive
the candidate path with:

```python
manifest.path.parent / "pyproject.toml"
```

and return a tuple of existing `ArtifactCheck` objects. Keeping the new logic
outside `manifest.py` prevents the strict Base manifest parser from taking on
Python packaging semantics.

`base_setup.engine.manifest_checks()` appends the pyproject checks to the
existing check list. This lets `basectl check`, `basectl doctor`, JSON output,
and workspace-level project diagnostics reuse the current flow.

## Data Flow

When no same-directory `pyproject.toml` exists, Base emits no pyproject finding.
The absence of the file is valid because not every Base-managed project is a
Python package.

When the file exists, Base parses it with the standard TOML reader available in
the runtime. The parser should be isolated behind a helper so Python-version
compatibility can be adjusted later without changing diagnostics call sites.

For a readable file, Base reports:

- the file exists and is readable
- `[project].name` when it is a string
- `[project].requires-python` when it is a string
- whether `[project].dependencies`, `[project].optional-dependencies`, or
  top-level `[dependency-groups]` exists
- whether `[tool.base]` exists

The dependency finding is a warning-status diagnostic, not a failed check. It
should say that Base observed Python dependency metadata but does not reconcile
it yet. `basectl check` and `basectl doctor` should keep returning success when
the only pyproject findings are warnings.

## Error Handling

Malformed TOML is a warning finding, not a blocking failure. Since Base does
not use `pyproject.toml` as a source of truth in this slice, invalid TOML should
be visible and actionable without failing the whole Base manifest check.

Unexpected data shapes should not crash diagnostics. If `[project]` exists but
is not a mapping, Base should warn that project metadata is unreadable. If
individual fields have unsupported shapes, Base should ignore those fields or
report a conservative warning without interpreting values.

Diagnostics must not print secrets. The first slice should report the presence
of dependency metadata, not dump dependency URLs, indexes, or arbitrary tool
configuration.

## Finding IDs

Add stable project finding IDs in `docs/doctor-findings.md`:

- `BASE-P140`: pyproject presence and metadata summary; ok when readable
- `BASE-P141`: pyproject TOML readability; warn when malformed or unreadable
- `BASE-P142`: pyproject dependency metadata observed but not reconciled; warn
- `BASE-P143`: unsupported `[tool.base]`; warn

The exact human-readable messages may evolve, but these IDs should keep their
meaning once shipped.

## Documentation

Update the Python manifest documentation or README to explain:

- Base observes same-directory `pyproject.toml` during diagnostics.
- `base_manifest.yaml` remains the Base source of truth.
- Base does not install from `pyproject.toml` in issue #358.
- uv-managed Python projects and any explicit `python:` manifest shape belong
  to issue #359.

## Testing

Add focused Python tests for the new diagnostics:

- no same-directory `pyproject.toml` produces no pyproject findings
- valid `[project]` metadata reports name and `requires-python`
- malformed TOML produces a warning finding and does not fail the whole check
- dependency metadata is observed without reconciliation
- unsupported `[tool.base]` produces a warning finding
- `manifest_checks()` includes pyproject findings in the existing check flow
- doctor JSON uses the stable IDs and warning statuses

Tests should use temporary fixture files and should not invoke network access,
uv, build backends, or package installers.

## Implementation Boundaries

This change is intentionally read-only. It gives Base visibility into modern
Python project metadata without changing who owns environments, dependencies,
or commands. Any future behavioral integration must be explicit in
`base_manifest.yaml` and should be handled under issue #359 or a separate issue
for non-uv Base-owned Python manifest behavior.
