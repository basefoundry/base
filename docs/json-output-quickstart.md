# JSON output quickstart

Use `--format json` when a script needs to inspect Base readiness. The command
is read-only, emits one JSON document on stdout, and keeps logs and diagnostics
on stderr. This small example uses the source-checkout launcher and does not
depend on a project-specific private path.

## Capture one readiness report

From the root of a prepared Base source checkout:

```bash
./bin/basectl check --format json > /tmp/base-check.json
```

The command's exit status remains the readiness result. A successful check can
still contain warnings, so inspect both the status and the diagnostic items:

```bash
jq -r '.status, (.checks[]? | [.id, .status, .name] | @tsv)' /tmp/base-check.json
```

The top-level `status` is the aggregate `ok`, `warn`, or `error` result. Each
item in `checks` has stable `id`, `status`, `name`, `message`, and `fix` fields.
Match automation on the finding `id`, not on human-readable message text.

For example, a consumer can fail its own gate on blocking findings while
preserving the complete report for a support request:

```bash
if ! jq -e '.status != "error"' /tmp/base-check.json >/dev/null; then
  jq -r '.checks[]? | select(.status == "error") | [.id, .message, .fix] | @tsv' \
    /tmp/base-check.json >&2
  exit 1
fi
```

This is an inspection payload, not the success/error lifecycle envelope used by
`base-cli` applications. See [Output Formats](output-formats.md) for the
shared rendering rules and [Doctor Finding IDs](doctor-findings.md) for the
stable diagnostic fields and exit-status boundary. Use
`./bin/basectl doctor --format json` when you need the more detailed
`findings`, `profile_findings`, or `project_findings` arrays.

Do not assume that fields outside the documented contract are stable. Keep the
complete JSON document with the Base version or full source-checkout commit
when reporting a compatibility problem, and redact credentials or private
paths before sharing it publicly.
