# Check JSON Contract Design

Issue: #507

## Summary

Base should expose one stable diagnostic item shape across check and doctor JSON
output before 1.0. The current check JSON output mixes shapes across Bash base
environment checks, Python project checks, prerequisite profile checks, and
workspace checks. That makes automation brittle because callers cannot depend
on the same fields appearing everywhere.

Base is still pre-1.0 and has no external compatibility contract yet, so this
issue should make a clean breaking change instead of carrying legacy `ok` fields
forward indefinitely.

## Goals

- Define the v1 JSON contract for diagnostic check and doctor output.
- Use one diagnostic item shape everywhere: `id`, `status`, `name`, `message`,
  and `fix`.
- Normalize project and prerequisite-profile check JSON into object payloads
  instead of bare arrays.
- Keep top-level command payloads machine-readable with `schema_version`,
  `status`, and command-specific context.
- Preserve deterministic output ordering.
- Document that pre-1.0 JSON output may still change until Base declares the
  1.0 contract stable.

## Non-Goals

- Do not change text output.
- Do not change finding IDs or add new diagnostic meanings.
- Do not change check or doctor exit-status rules except where tests need to
  assert the current behavior explicitly.
- Do not add suppression, filtering, or JSON Schema files in this issue.
- Do not parallelize checks in this issue.

## Contract

Every diagnostic item emitted by check or doctor JSON should have this shape:

```json
{
  "id": "BASE-P050",
  "status": "error",
  "name": "project_virtualenv",
  "message": "Virtual environment is missing.",
  "fix": "Run 'basectl setup demo --recreate-venv'."
}
```

`status` is the machine-readable result and replaces per-item `ok`.

Allowed statuses:

- `ok`: the diagnostic passed
- `warn`: Base found a non-blocking or advisory issue
- `error`: Base found a failing requirement

`fix` should always be present. Use an empty string when no fix guidance applies.

## Top-Level Payloads

Object-shaped command payloads should include:

- `schema_version`: integer `1`
- `status`: aggregate status for the command payload

Aggregate status should be:

- `error` when any diagnostic item is `error`
- `warn` when there are no errors and at least one diagnostic item is `warn`
- `ok` when all diagnostic items are `ok`

`basectl check --format json`:

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": []
}
```

`basectl check <project> --format json`:

```json
{
  "schema_version": 1,
  "status": "ok",
  "project": "demo",
  "checks": [],
  "project_checks": {
    "schema_version": 1,
    "status": "ok",
    "project": "demo",
    "checks": []
  }
}
```

`basectl check --profile dev --format json`:

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": [],
  "profile_checks": {
    "schema_version": 1,
    "status": "ok",
    "profiles": ["dev"],
    "checks": []
  }
}
```

`basectl workspace check --format json` should keep its workspace-oriented
object shape and ensure each project diagnostic item uses the same v1 item
shape:

```json
{
  "schema_version": 1,
  "workspace": "/Users/example/work",
  "status": "error",
  "project_count": 1,
  "projects": [
    {
      "name": "demo",
      "status": "error",
      "path": "/Users/example/work/demo",
      "manifest_path": "/Users/example/work/demo/base_manifest.yaml",
      "manifest": "valid",
      "checks": []
    }
  ]
}
```

Doctor JSON should use the same diagnostic item shape. Existing doctor payloads
already mostly have the right item fields; this issue should align check output
with that model and add `schema_version` where the command returns an object.

## Architecture

Keep the existing `ArtifactCheck` and `DevCheck` data classes. Replace the
current split between `check_to_json()` and `check_to_doctor_json()` with shared
diagnostic-item serializers that produce the v1 item shape.

The Python project layer should expose object payload helpers for check output
so direct `python -m base_setup --action check --format json` invocations and
Bash-wrapped `basectl check <project> --format json` receive the same contract.

The prerequisite profile layer should do the same for `base_dev check
--format json`.

The Bash base-environment check path should stop hand-assembling a legacy item
shape. It can keep Bash JSON emission for now, but its JSON item helper should
accept `id`, `status`, `name`, `message`, and `fix`, then render the same v1
diagnostic object as the Python serializers.

Workspace check JSON should no longer patch `id` and `status` into legacy check
items. It should call the shared v1 item serializer directly.

## Compatibility

This is intentionally backward-incompatible:

- per-item `ok` is removed
- Python project check JSON changes from a bare array to an object
- prerequisite profile check JSON changes from a bare array to an object

This is acceptable because Base has not declared a 1.0 compatibility contract.
The documentation should call out that the v1 diagnostic JSON contract is the
target shape for 1.0, while pre-1.0 JSON may still change as Base hardens.

## Error Handling

JSON emission must remain valid when diagnostic messages include quotes,
backslashes, newlines, C0 control characters, or DEL. Existing Bash JSON escaping
tests should be updated to assert the new item fields, not just the old `ok`
field.

If a nested project or profile layer fails without producing JSON, the Bash
wrapper should preserve the current fallback behavior of reporting an empty
nested payload and failing the top-level check command. If the nested layer
does produce a valid object payload with `status`, the top-level status should
reflect that nested status.

## Documentation

Add a diagnostics JSON section to the docs, likely in `docs/doctor-findings.md`
or a dedicated diagnostics-output page linked from the docs map. The docs
should cover:

- v1 diagnostic item fields
- allowed statuses
- aggregate status rules
- the intentional pre-1.0 breaking change
- the relationship between check and doctor JSON

## Testing

Add or update tests for:

- `basectl check --format json` base-environment output
- `basectl check <project> --format json`
- `basectl check --profile dev --format json`
- direct `base_setup` project check JSON
- direct `base_dev` profile check JSON
- `basectl workspace check --format json`
- `basectl doctor --format json` remains aligned with the item shape
- JSON escaping for diagnostic strings with control characters

Run:

```bash
env -u BASE_HOME ./bin/base-test
git diff --check
```

## Implementation Notes

The implementation should happen in one PR for issue #507 because the public
contract needs to change coherently across Bash, project, profile, and workspace
surfaces. Keep the change focused on shape and tests; leave check parallelism
and workspace-manifest behavior to their own issues.
