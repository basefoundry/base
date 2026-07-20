# basectl output formats

Base report commands share one output contract. The contract applies to
`basectl projects list`, workspace reports, lifecycle listings, trust status,
release checks, and the `history` and `logs last` reports.

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
| `logs last` | `TIME`, `COMMAND`, `PROJECT`, `STATUS`, `EXIT`, `RUN ID`, `LOG` |

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

## `basectl projects list`

The table and delimited forms use the columns `PROJECT` then `PATH`. CSV and
TSV contain those two fields without a header. JSON and YAML contain a list of
objects with `name` and `path` keys, preserving the existing JSON shape.
