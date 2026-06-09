# Check JSON Contract Implementation Plan

Issue: #507
Design: `docs/superpowers/specs/2026-06-08-check-json-contract-design.md`

## Goal

Normalize Base check JSON output to a v1 diagnostic contract before 1.0:

- Every diagnostic item has `id`, `status`, `name`, `message`, and `fix`.
- Check JSON no longer emits per-item `ok`.
- Object payloads include `schema_version: 1` and aggregate `status`.
- Project and profile check output embedded by `basectl check --format json`
  becomes an object payload rather than a bare array.
- Text output stays unchanged.

## Contract

Diagnostic item:

```json
{
  "id": "BASE-D001",
  "status": "ok",
  "name": "homebrew",
  "message": "Homebrew is installed.",
  "fix": ""
}
```

Check payload:

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": []
}
```

`basectl check demo --format json`:

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
  "status": "error",
  "checks": [],
  "profile_checks": {
    "schema_version": 1,
    "status": "error",
    "profiles": ["dev"],
    "checks": []
  }
}
```

Workspace check JSON keeps its existing workspace/project object shape, but adds
`schema_version: 1` and emits v1 items without `ok`.

## Implementation Steps

1. Add failing tests for the new contract.
   - Update `cli/bash/commands/basectl/tests/check.bats` JSON assertions:
     expect `schema_version`, aggregate `status`, item `id/status/fix`, no
     per-item `ok`, and nested object payloads for `profile_checks` and
     `project_checks`.
   - Update `cli/python/base_setup/tests/test_diagnostics.py`,
     `cli/python/base_dev/tests/test_engine.py`, and
     `cli/python/base_projects/tests/test_workspace_checks.py` to assert the v1
     check payload shape.
   - Keep doctor item tests intact except where object payloads gain
     `schema_version` and aggregate `status`.

2. Implement shared project diagnostic helpers in `cli/python/base_setup/checks.py`.
   - Add `DIAGNOSTIC_JSON_SCHEMA_VERSION = 1`.
   - Change `check_to_json()` to return the v1 item shape.
   - Keep `check_to_doctor_json()` as the same item shape for existing imports.
   - Add `checks_status(checks)` with error > warn > ok precedence.
   - Add `checks_payload_to_json(checks, **metadata)` returning
     `schema_version`, `status`, metadata, and `checks`.

3. Normalize project check JSON in `cli/python/base_setup/engine.py`.
   - `check_manifest(..., --format json)` prints
     `checks_payload_to_json(checks, project=manifest.project_name)`.
   - `doctor_manifest(..., --format json)` can keep its bare findings array
     because it is nested as doctor findings, not check payload.

4. Normalize profile check JSON in `cli/python/base_dev/engine.py`.
   - Change local `check_to_json()` to emit v1 items.
   - Add local payload helpers mirroring the shared status logic.
   - `print_check_results(..., --format json)` prints an object with
     `profiles` and `checks`.
   - Leave direct doctor JSON as a findings array of v1 items.

5. Normalize workspace check JSON in `cli/python/base_projects/engine.py`.
   - Import and reuse the shared `checks_status()`.
   - Add `schema_version: 1` to workspace check/doctor object payloads.
   - Make workspace check items use `check_to_json()` directly, with no `ok`.

6. Normalize Bash wrapper JSON in
   `cli/bash/commands/basectl/subcommands/setup_common.sh`.
   - Base check items use `BASE-D` IDs and `status`.
   - Top-level `basectl check --format json` emits `schema_version`, aggregate
     `status`, and `checks`.
   - Project virtualenv fallback check JSON emits a check payload object.
   - Nested `profile_checks` and `project_checks` are embedded as object
     payloads.
   - Aggregate status accounts for base checks and nested payload statuses.

7. Add matching schema metadata to object-shaped doctor JSON in
   `cli/bash/commands/basectl/subcommands/doctor.sh`.
   - Replace top-level `ok` with `schema_version` and aggregate `status`.
   - Keep `findings`, `profile_findings`, and `project_findings`.

8. Update tests fixtures/stubs.
   - Update `cli/bash/commands/basectl/tests/setup_helpers.bash` stubbed JSON
     emitted by fake Python layers.
   - Preserve text-mode stubs and assertions.

9. Update docs.
   - Add a v1 diagnostic JSON contract section to `docs/doctor-findings.md`.
   - Mention that the pre-1.0 check JSON shape is intentionally breaking and
     that `check` and `doctor` share diagnostic item fields.

10. Validate.
    - Run focused tests for changed Python modules.
    - Run Bats check/doctor tests.
    - Run `env -u BASE_HOME ./bin/base-test`.
    - Run `git diff --check`.

## Completion

Commit the implementation and open a PR that closes #507.
