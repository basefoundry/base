# Local Observability Model

> **STATUS** — `basectl history`, the local history index,
> `basectl history --report`, and `basectl logs last` are implemented as
> local-only slices.
> `basectl explain last-error`, a broader `basectl report` bundle, and history
> cleanup integration are tracked but not scheduled longer-term future work.

Tracker: [#396](https://github.com/basefoundry/base/issues/396)

Base currently exposes raw runtime logs through `basectl logs`, latest-failure
evidence through `basectl logs last`, structured local command metadata through
`basectl history`, and a redacted local activity summary through
`basectl history --report`. This document defines the local observability
layer: shipped command history and activity reports, future last-error
explanation, and broader future report generation.

## Goals

- Preserve `basectl logs` as the raw evidence surface.
- Add a local structured history index that makes recent command outcomes easy
  to scan without opening individual log files.
- Allow a future `basectl explain last-error` command to summarize the latest
  failed Base run from local evidence.
- Generate redacted local activity reports from history and log metadata for
  bug reports or support handoff.
- Allow a future broader `basectl report` command to create an explicit
  diagnostic bundle when Base has more local evidence surfaces to combine.
- Keep all data local by default, with no telemetry and no automatic upload.

## Non-Goals

- Do not add hosted telemetry.
- Do not upload logs, reports, history, or diagnostics automatically.
- Do not use network services or AI providers to explain failures.
- Do not make command history writes a reason for the primary command to fail.
- Do not replace raw log files with summaries.

## Current Surface

`basectl logs` scans the Base cache root, finds recent Python-layer runtime log
files, and prints a table with command, run id, status, and path. It also
supports opening, tailing, or printing the newest matching log path.

This is useful when the user already knows they need raw logs. It is less useful
when they want to answer questions such as:

- What did I run recently?
- Which project did the failure belong to?
- Which command failed most recently?
- What should I inspect first?
- What local evidence can I attach to a bug report?

Those questions need a structured index in addition to raw log discovery.

## History Index

Base writes a structured command history index under the Base cache root:

```text
<base-cache-root>/history/runs.jsonl
```

Each line is one JSON object. JSON Lines keeps writes append-only, easy to
inspect with ordinary tools, and easy to recover when one line is malformed.

History writes are best-effort:

- write a primary completion record for a public `basectl` command
- retain internal Python/helper completion records linked to that primary
  invocation
- never fail the user command because the history file cannot be written
- ignore malformed history lines while warning in debug output

The default `basectl history` view shows primary public-command records. Internal
records remain in the local index and can be inspected with
`basectl history --include-internal`.

## Record Shape

A history record should include:

```json
{
  "schema_version": 1,
  "run_id": "20260610T101500_ab12cd",
  "event": "finished",
  "scope": "primary",
  "command": "setup",
  "raw_command": "base_setup",
  "argv": ["basectl", "setup", "base"],
  "project": "base",
  "project_root": "~/work/base",
  "manifest": "~/work/base/base_manifest.yaml",
  "workspace_root": "~/work",
  "started_at": "2026-06-10T10:15:00Z",
  "ended_at": "2026-06-10T10:15:12Z",
  "duration_ms": 12000,
  "exit_code": 0,
  "status": "ok",
  "log_path": "~/Library/Caches/base/cli/base_setup/logs/20260610T101500_ab12cd.log",
  "base_version": "0.4.0",
  "os": "macos",
  "shell": "bash",
  "profiles": ["dev"]
}
```

Primary records use `scope: "primary"` and represent the command the user
invoked. Delegated records use `scope: "internal"` and carry that invocation's
`run_id` in `parent_run_id`.

Fields should be omitted when unknown instead of guessed.

The first implementation should not store:

- full environment variables
- raw command output
- secret values
- unbounded absolute paths
- package index URLs with credentials
- arbitrary shell history outside the Base command being run

Raw output remains in the log file. History stores metadata and a pointer to
the evidence.

## Redaction And Privacy

History and reports must be local by default. Users opt in to sharing by
copying, attaching, or otherwise sending a generated report themselves.

Before writing history or reports, Base should redact:

- URL credentials such as `https://user:secret@example.invalid/path`
- key/value fragments whose key looks like `token`, `password`, `secret`,
  `api-key`, `api_key`, or `authorization`
- shell arguments passed to options whose name looks secret-bearing
- home-directory paths by compacting them to `~/...`

The live terminal stream is not redacted by Base. Redaction protects persistent
metadata and generated reports.

## Retention

History belongs to the same local cache lifecycle as runtime logs. `basectl
clean` should eventually understand history records and remove or compact
records whose log files have been pruned.

The retention contract should be:

- `basectl clean --older-than <age>` removes history records older than the age
  when their corresponding logs are also eligible for removal.
- `basectl clean --keep-last <count>` keeps history records for the retained log
  files and prunes older records for that command family.
- Orphaned history records may remain temporarily when cleanup cannot match the
  log path safely, but `basectl history` should mark missing logs clearly.
- Durable user state under `~/.base.d` is never cleaned by history retention.

## Shipped Commands

### `basectl history`

`basectl history` reads the structured index and prints a compact table of
recent Base command runs:

```text
TIME                 COMMAND   PROJECT  STATUS  EXIT  LOG
2026-06-10 10:15:12  setup     base     ok      0     ~/Library/Caches/base/...
2026-06-10 10:10:03  check     demo     error   1     ~/Library/Caches/base/...
```

Expected options:

- `--project <name>` filters by Base project name.
- `--command <name>` filters by command.
- `--status <ok|warn|error>` filters by status.
- `--limit <count>` limits the number of rows.
- `--format json` prints structured records for scripts.
- `--report` prints a Markdown activity report by default.
- `--report --format json` prints the same report as deterministic JSON.
- `--include-internal` includes delegated resolver, routing, bootstrap, and
  trust-gate records linked to each primary command.
- `--oldest-first` reverses the selected window from newest-to-oldest to
  oldest-to-newest; the default remains newest-first.
- `--last <duration>` selects a relative window such as `30m`, `2h`, or `7d`.
- `--since <time>` and `--until <time>` select a bounded window. Values accept
  ISO-8601 or `YYYY-MM-DD[ HH:MM[:SS]]`; short values use the host timezone,
  while explicit offsets or `Z` take precedence. `--until` is exclusive.
- Text and Markdown timestamps are labeled `TIME (UTC)`/`Time (UTC)` by default.
  `--local-time` renders those views in the host's local timezone; JSON keeps
  canonical UTC timestamps for stable automation.

Time filters are applied before ordering and `--limit`. `--last` cannot be
combined with `--since` or `--until`, and invalid or reversed ranges are usage
errors.

`basectl logs` should remain the command for opening or tailing raw log files.
`basectl history` should point to logs, not replace them.

`basectl logs last` bridges those surfaces for the common failure case. It reads
the local history index, finds the latest failed run, prints command metadata,
and includes a bounded redacted tail of the recorded log when the log still
exists. It also supports `--format json` for local automation. If the log path
is missing or the file was cleaned, it still reports the available history
metadata and says that the recorded log file is missing.

The report mode summarizes selected recent history records with:

- total records, warnings, and failures
- status counts
- common failing command families
- recent command rows
- failure details with redacted argv values
- log file locations and missing-log markers

Report mode does not include raw log contents, upload data, or collect
background telemetry. It compacts home-directory paths to `~` and re-applies
secret-looking argument and URL credential redaction defensively before
rendering Markdown or JSON.

## Planned Commands

### `basectl explain last-error`

`basectl explain last-error` should build on the local evidence surfaced by
`basectl logs last`. It should find the latest failed history record, inspect
its linked log file if present, and print a deterministic local summary:

- command, project, exit code, and time
- likely failing subsystem when detectable
- the most relevant log tail
- suggested next commands such as `basectl logs --path` or `basectl doctor`

The explanation should be rule-based. It should not call external services.

If the history record is missing its log file, the command should still report
the metadata and explain that raw evidence has been cleaned or moved.

### Broader `basectl report`

A future broader `basectl report` should generate a local diagnostic artifact,
preferably a Markdown report by default with an optional JSON format for
automation.

The report should include:

- Base version and runtime environment summary
- recent command history summary
- selected doctor/check findings when requested
- paths to relevant logs
- redacted log excerpts when explicitly requested
- project manifest metadata, limited to non-secret fields

The command should write to an explicit output path or print to stdout. It
should never upload the report.

## Implementation Split

The shipped first slice is:

1. Add history recording and `basectl history`. **Shipped.**
2. Add `basectl history --report` for local history/log activity summaries.
   **Shipped.**
3. Add `basectl logs last` for latest-failure metadata and bounded redacted log
   tails. **Shipped.**

### Unscheduled Future Work

The following items remain tracked but are not scheduled:

- Add `basectl explain last-error` after history records exist.
- Add broader `basectl report` after history and explanation have stable local
  data.
- Extend `basectl clean` to compact or prune history records once the history
  format is stable.

That sequence keeps the data model and privacy boundary reviewable before Base
starts producing summaries or shareable diagnostic artifacts.

## First Slice Decisions

- The history writer lives in `base_cli.App`, so Python-backed commands share
  the same local metadata lifecycle as persistent logs.
- Shell-only commands are deferred until Base has a shell-side writer with the
  same redaction and best-effort guarantees.
- `basectl history` marks missing log files directly in text output and exposes
  `log_exists` in JSON output.
- `basectl history --report` does not include raw log excerpts; any future
  broader report mode should still require an explicit option before embedding
  raw log excerpts.
