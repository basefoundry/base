# basectl output formats

Base report commands share one output contract.

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

## `basectl projects list`

The table and delimited forms use the columns `PROJECT` then `PATH`. CSV and
TSV contain those two fields without a header. JSON and YAML contain a list of
objects with `name` and `path` keys, preserving the existing JSON shape.

The internal `command-protocol` format is a private Base-to-Base interface and
is not part of the public output-format choices. Artifact-producing commands,
such as `export-context --format markdown|zip`, keep their command-specific
format semantics.
