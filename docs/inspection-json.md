# Inspection JSON

Base exposes stable, versioned JSON for read-only control-plane inspections
that are useful in CI, release gates, agent handoffs, and dashboards. Use
`--format json` with:

- `basectl repo check`
- `basectl release check`
- `basectl gh issue readiness`
- `basectl gh branch stale`

Text remains the default. JSON mode writes exactly one JSON document to stdout
and never mixes ANSI formatting or human prose into that stream. Upstream tools
may still write diagnostics to stderr.

## Stable V1 Envelope

Every command uses the same top-level object:

```json
{
  "schema_version": 1,
  "command": "repo check",
  "status": "ok",
  "data": {},
  "error": null
}
```

The five top-level keys and their types are stable:

- `schema_version` is the integer `1` for this payload family.
- `command` is one of `repo check`, `release check`,
  `gh issue readiness`, or `gh branch stale`.
- `status` is `ok`, `warn`, or `error`.
- `data` is a command-specific object.
- `error` is `null` for a completed inspection. A controlled usage,
  environment, or upstream execution failure uses an object with stable
  `type`, `message`, and `details` fields.

An inspection finding is not an execution failure. For example, missing repo
files or release blockers produce `status: "error"` with `error: null` and
the findings in `data`. Invalid input selected with `--format json` produces:

```json
{
  "schema_version": 1,
  "command": "repo check",
  "status": "error",
  "data": {},
  "error": {
    "type": "usage_error",
    "message": "Unknown repo check option '--unknown'.",
    "details": {}
  }
}
```

`error.type` currently includes `usage_error`, `environment_error`,
`upstream_error`, and `execution_error`. Consumers must allow additive keys in
`data`, `error.details`, and command-specific records. They must not infer
success from `error` alone; use both the process exit status and the documented
command result.

## Exit Status

Serialization does not change command policy or exit status:

- `repo check` and `release check` return nonzero for blocking findings.
- `gh issue readiness` returns nonzero for both partial and not-ready results.
- `gh branch stale` returns zero when stale branches are findings; its payload
  uses `status: "warn"` when the result list is non-empty.
- controlled usage errors return `2`; environment and upstream failures retain
  their command failure status.

This means `status: "warn"` does not imply one universal exit code. It
describes the inspection result; the command's documented policy owns the exit
status.

## `repo check`

`data.path` is the resolved repository path. `data.summary` contains stable
integer `checks`, `passed`, and `failed` counts. `data.checks` is ordered and
contains the baseline plus only the optional checks requested by flags.

```json
{
  "schema_version": 1,
  "command": "repo check",
  "status": "error",
  "data": {
    "path": "/work/example",
    "summary": {"checks": 1, "passed": 0, "failed": 1},
    "checks": [
      {
        "name": "baseline",
        "status": "error",
        "required_count": 13,
        "present_count": 12,
        "missing_files": ["VERSION"],
        "not_executable_files": []
      }
    ]
  },
  "error": null
}
```

Stable check names are `baseline`, `release`, `agent_guidance`, and
`agent_readiness`. All records have stable `name` and `status` fields. The
baseline record keeps `required_count`, `present_count`, `missing_files`, and
`not_executable_files`. Agent records keep `required_count`, `present_count`,
and `missing_files`. The release record reports `manifest_path`, `manifest_declared`,
`process_document_path`, and `process_document_present`.

## `release check`

`data` includes stable `project`, `version`, `tag_name`, `manifest_path`, and
`findings` fields. Each finding has stable `status`, `name`, and `message`
fields. Finding names and messages follow the existing release readiness
policy; consumers should branch on `status` and `name`, not prose.

```json
{
  "schema_version": 1,
  "command": "release check",
  "status": "ok",
  "data": {
    "project": "base",
    "version": "1.7.0",
    "tag_name": "v1.7.0",
    "manifest_path": "/work/base/base_manifest.yaml",
    "findings": [
      {"status": "ok", "name": "version_file", "message": "VERSION matches 1.7.0."}
    ]
  },
  "error": null
}
```

## `gh issue readiness`

`data` includes stable `issue_number`, `repository`, `readiness`, `body`,
`project`, `labels`, and `assignees` fields. `readiness` is `ready`, `partial`,
or `not_ready`. Empty labels or assignees are empty arrays, never the text
sentinel `none`.

The body record has `status` and `missing_sections`. The project record has
`requested`, `status`, `owner`, `number`, `missing_fields`, and `fields`.
Project `status` is `ok`, `error`, or `skipped`; unrequested coordinates and
field values are `null`.

```json
{
  "schema_version": 1,
  "command": "gh issue readiness",
  "status": "warn",
  "data": {
    "issue_number": 1646,
    "repository": "basefoundry/base",
    "readiness": "partial",
    "body": {"status": "ok", "missing_sections": []},
    "project": {
      "requested": false,
      "status": "skipped",
      "owner": null,
      "number": null,
      "missing_fields": [],
      "fields": {"status": null, "priority": null, "size": null, "area": null, "initiative": null}
    },
    "labels": ["enhancement"],
    "assignees": []
  },
  "error": null
}
```

## `gh branch stale`

`data.days` is the requested threshold, `data.inspected_at_unix` is the
inspection timestamp, and `data.branches` is an ordered array. Empty results
use `[]`. Each branch has stable `name`, `scope`, `age_days`, `last_commit`,
and `last_commit_unix` fields. `scope` is `local` or `remote`.

```json
{
  "schema_version": 1,
  "command": "gh branch stale",
  "status": "warn",
  "data": {
    "days": 30,
    "inspected_at_unix": 1784232000,
    "branches": [
      {
        "name": "enhancement/1646-inspection-json",
        "scope": "local",
        "age_days": 31,
        "last_commit": "2026-06-15",
        "last_commit_unix": 1781510400
      }
    ]
  },
  "error": null
}
```

## Compatibility

These payloads are Stable under [Base Stability Tiers](stability-tiers.md).
Within schema version 1, Base may add object keys, finding records, check
records, or enum values where this page identifies an extension point. Base
will not remove or rename stable fields, change their types, or change existing
enum meanings without a new schema version and migration guidance.

The Ubuntu source-checkout CI job consumes `gh branch stale` with `jq` and
asserts the envelope and empty-result fields directly. That smoke path
intentionally does not parse the text renderer.
