# basectl output formats

Base report commands share one output contract. The contract applies to
`basectl projects list`, workspace reports, lifecycle listings, trust status,
release checks, and the `history` and `logs last-failed` reports.

When `--format` is omitted, or when `--format text` is selected, Base checks
whether stdout is an interactive terminal:

- terminal output is a human-readable table with column headers and a summary
  footer;
- redirected or piped output is tab-delimited rows with no header or footer.

Explicit machine-readable formats are independent of the terminal:

- `--format csv` emits comma-separated, headerless rows with CSV quoting;
- `--format tsv` emits tab-separated, headerless rows;
- `--format yaml` emits one YAML document;
- `--format json` emits one JSON document.

Delimited formats use the command's documented, stable column order. JSON and
YAML preserve the command's documented record shape and field names. Empty
results are represented as no rows for delimited output and an empty list for
JSON/YAML. Diagnostics and errors are written to stderr so that structured
stdout remains safe for automation.

The default is therefore convenient for both use cases:

```text
basectl workspace status                  # pretty table in a terminal
basectl workspace status | tee status.tsv # headerless TSV rows
basectl workspace status --format json   # one stable JSON document
```

The JSON document emitted by `basectl workspace status --format json` includes
a top-level aggregate `status` alongside `workspace`, `project_count`, and
`projects`. The aggregate uses `error` over `warn` over `ok` precedence; each
project record retains its existing `status` field.

`basectl workspace check --format json|yaml` also includes a top-level
`record_warnings` collection. Each warning names the affected project and
latest-check record path and supplies stable `status`, `message`, and `fix`
fields. The collection is empty when every record is saved. These optional
persistence warnings do not alter the diagnostic `status` or command exit code.

The terminal check is made on stdout, so redirecting stdout changes only the
default `text` presentation. An explicitly selected `--format text` follows
the same rule. Logging, warnings, and usage errors stay on stderr and never
become rows in a structured stdout stream.

## Stable report columns

Delimited output has no header row. Its fields always follow the command's
documented order:

| Report | Field order |
|---|---|
| `projects list` | `PROJECT`, `PATH` |
| `workspace status` | `PROJECT`, `STATUS`, `PATH`, `VENV`, `MANIFEST`, `LAST CHECK` |
| `workspace check` / `workspace doctor` | `PROJECT`, `STATUS`, `PATH`, `MANIFEST` |
| `workspace onboarding` | `REPOSITORY`, `REQUIRED`, `STATUS`, `PATH`, `VENV` |
| `workspace agent-brief` | `REPOSITORY`, `PROJECT`, `PATH`, `SCOPE`, `HANDOFF`, `VENV` |
| `run --list` | `PROJECT`, `COMMAND`, `COMMAND LINE`, `RUNNER` |
| `build --list` | `PROJECT`, `TARGET`, `WORKING DIR`, `COMMAND`, `DESCRIPTION`, `RUNNER` |
| `trust status` | `PROJECT`, `STATUS`, `REASON` |
| `release check` | `STATUS`, `NAME`, `MESSAGE` |
| `history` | `TIME`, `COMMAND`, `PROJECT`, `STATUS`, `EXIT`, `LOG` |
| `logs last-failed` | `TIME`, `COMMAND`, `PROJECT`, `STATUS`, `EXIT`, `RUN ID`, `LOG` |

CSV and TSV values are emitted in this order without a header. CSV applies
standard quoting when a value contains a comma, quote, or newline; TSV keeps
the same field order with tab delimiters. JSON and YAML retain each command's
documented record names and envelope shape rather than converting the table
headers into API keys. Existing JSON payloads remain backward compatible while
CSV/TSV provide a row-oriented view of the same records.

Empty reports emit no rows in CSV/TSV and an empty list (or the command's
existing empty document) in JSON/YAML.

## Help and completion

Every report using this contract lists its valid public values in `--help` and
shell completion: `text`, `csv`, `tsv`, `yaml`, and `json`. Completion also
preserves command-specific choices for non-contract commands, such as
`export-context --format markdown|zip` and legacy inspection commands that
support only `text|json`.

## Exceptions

`command-protocol` is an internal Base-to-Base transport used by wrappers and
completion. It is intentionally not a public completion or automation format.
`history --report` is a separate activity-report contract and continues to use
`--format markdown|json`; its Markdown output is intended for people, while its
JSON output is a report document rather than the row list from plain
`basectl history`. Artifact-producing commands, such as
`export-context --format markdown|zip`, keep their command-specific format
semantics. Setup, check, doctor, repository inspection, and GitHub inspection
commands likewise retain their existing `text|json` contracts until they are
individually migrated.
`release check` is not one of those exceptions: it supports all five shared
report formats, `text|csv|tsv|yaml|json`.

## `basectl release check`

`release check` uses the five-format contract above. Its `json` output is the
stable v1 inspection envelope documented in [Inspection JSON](inspection-json.md)
and its `yaml` output preserves the same object and field structure. Its
`csv` and `tsv` output flattens each `data.findings[]` record into one row, in
`STATUS`, `NAME`, `MESSAGE` order, from the finding's `status`, `name`, and
`message` fields. With the default `text` format, a terminal receives a
human-readable summary; redirected output remains headerless rows.

## `basectl projects list`

The table and delimited forms use the columns `PROJECT` then `PATH`. CSV and
TSV contain those two fields without a header. JSON and YAML contain a list of
objects with `name` and `path` keys, preserving the existing JSON shape.

## Focused JSON output example for new adopters

A new adopter can inspect Base's JSON output with a simple command:



This command emits one JSON document on stdout. Logs and errors go to stderr.

The JSON document has a top-level `status` field (one of `ok`, `warn`, `error`) and a `data` field
containing the command-specific result. For `basectl check`, the `data` field includes the project
name and version when run in a Base-managed project.

Example output:



For more details on the JSON contract, see [Inspection JSON](inspection-json.md).

Note: The `basectl check` command is safe to run in any Base-managed project and does not require
a specific project setup beyond having a `base_manifest.yaml`.

To quickly inspect the status field without depending on the project name or version, use jq:




## Focused JSON output example for new adopters

A new adopter can inspect Base's JSON output with a simple command:



This command emits one JSON document on stdout. Logs and errors go to stderr.

The JSON document has a top-level `status` field (one of `ok`, `warn`, `error`) and a `data` field
containing the command-specific result. For `basectl check`, the `data` field includes the project
name and version when run in a Base-managed project.

Example output:



For more details on the JSON contract, see [Inspection JSON](inspection-json.md).

Note: The `basectl check` command is safe to run in any Base-managed project and does not require
a specific project setup beyond having a `base_manifest.yaml`.

To quickly inspect the status field without depending on the project name or version, use jq:




## Focused JSON output example for new adopters

A new adopter can inspect Base's JSON output with a simple command:

```bash
basectl check --format json
```

This command emits one JSON document on stdout. Logs and errors go to stderr.

The JSON document has a top-level `status` field (one of `ok`, `warn`, `error`) and a `data` field
containing the command-specific result. For `basectl check`, the `data` field includes the project
name and version when run in a Base-managed project.

Example output:

```json
{
  "schema_version": 1,
  "command": "check",
  "status": "ok",
  "data": {
    "project": "demo",
    "version": "0.4.0"
  },
  "error": null
}
```

For more details on the JSON contract, see [Inspection JSON](inspection-json.md).

Note: The `basectl check` command is safe to run in any Base-managed project and does not require
a specific project setup beyond having a `base_manifest.yaml`.

To quickly inspect the status field without depending on the project name or version, use jq:

```bash
basectl check --format json | jq -r '.status'
```
