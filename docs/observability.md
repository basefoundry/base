# Local Observability Model

Issue: #396

Base currently exposes raw runtime logs through `basectl logs`. This document
defines the next local observability layer: structured command history,
last-error explanation, and report generation. It is a design contract for
future implementation, not a statement that these commands exist today.

## Goals

- Preserve `basectl logs` as the raw evidence surface.
- Add a local structured history index that makes recent command outcomes easy
  to scan without opening individual log files.
- Allow a future `basectl explain last-error` command to summarize the latest
  failed Base run from local evidence.
- Allow a future `basectl report` command to create a redacted local diagnostic
  bundle for bug reports or support handoff.
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

Base should add a structured command history index under the Base cache root:

```text
<base-cache-root>/history/runs.jsonl
```

Each line is one JSON object. JSON Lines keeps writes append-only, easy to
inspect with ordinary tools, and easy to recover when one line is malformed.

History writes should be best-effort:

- write a start record when a command begins
- write a completion record when the command exits
- tolerate missing completion records
- never fail the user command because the history file cannot be written
- ignore malformed history lines while warning in debug output

The first implementation can either emit one final record per run or pair
`started` and `finished` events. If paired events are used, readers should
collapse them by `run_id` and prefer the latest completion event.

## Record Shape

A history record should include:

```json
{
  "schema_version": 1,
  "run_id": "20260610T101500_ab12cd",
  "event": "finished",
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

## Future Commands

### `basectl history`

`basectl history` should read the structured index and print a compact table of
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

`basectl logs` should remain the command for opening or tailing raw log files.
`basectl history` should point to logs, not replace them.

### `basectl explain last-error`

`basectl explain last-error` should find the latest failed history record,
inspect its linked log file if present, and print a deterministic local
summary:

- command, project, exit code, and time
- likely failing subsystem when detectable
- the most relevant log tail
- suggested next commands such as `basectl logs --path` or `basectl doctor`

The explanation should be rule-based. It should not call external services.

If the history record is missing its log file, the command should still report
the metadata and explain that raw evidence has been cleaned or moved.

### `basectl report`

`basectl report` should generate a local diagnostic artifact, preferably a
Markdown report by default with an optional JSON format for automation.

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

The commands should ship in separate, reviewable slices:

1. Add history recording and `basectl history`.
2. Add `basectl explain last-error` after history records exist.
3. Add `basectl report` after history and explanation have stable local data.
4. Extend `basectl clean` to compact or prune history records once the history
   format is stable.

This order keeps the data model and privacy boundary reviewable before Base
starts producing summaries or shareable diagnostic artifacts.

## Open Questions For Implementation

- Should shell-only commands record history before the Python layer starts, or
  should the first slice cover only Python-backed commands?
- Should the history writer live in `base_cli.App`, the Bash dispatcher, or a
  small shared module used by both?
- Should report generation include raw log excerpts by default, or require an
  explicit `--include-log-excerpts` option?
- Should missing logs be a warning row in `history`, or only visible with a
  verbose flag?

These questions should be answered in the first implementation issue before
writing the history recorder.
