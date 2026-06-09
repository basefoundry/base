# Setup Output Logs Design

Issue: #508

## Goal

When Base runs external setup commands, users should still see live command
progress, and Base's persistent logs should contain enough stdout/stderr context
to debug failures without rerunning setup with shell redirection.

## Scope

This change is limited to the Python setup execution path centered on
`base_setup.process.run_command()`. That function is already used by project
artifact installs, Brewfile/mise delegates, IDE installs/extensions, and
developer prerequisite profile setup. Dry-run behavior and read-only check
commands are out of scope.

## Design

Replace the current `subprocess.run(..., stderr=PIPE)` call with a small
tee-style executor in `base_setup.process`.

The executor will:

- start the child process with stdout and stderr piped
- read stdout and stderr concurrently
- write stdout chunks to the current process stdout and stderr chunks to stderr
- log redacted stdout/stderr chunks through `ctx.log.debug(...)`
- retain a bounded redacted tail for each stream
- raise `ArtifactError` with the command, exit code, and available bounded
  stdout/stderr tails on failure
- keep the existing success debug message

Logging command output at debug level matches Base's existing persistent-log
model: normal terminal output remains the child process output, while file logs
record debug messages. If the user runs with `--debug`, debug log lines may also
be visible on stderr; the primary live progress stream remains unchanged.

## Redaction

The first implementation will redact obvious secret-shaped output before it
enters logs or failure messages:

- URL credentials such as `https://user:secret@example.invalid/path`
- key/value fragments whose key looks like `token`, `password`, `secret`,
  `api-key`, or `api_key`

The live terminal stream is not modified. Redaction is a safety net for
persistent logs and error summaries, not a substitute for tools avoiding secret
output.

## Failure Message

On nonzero exit, `ArtifactError` will include:

```text
Command failed with exit 17: installer --bad
stdout:
...
stderr:
...
```

Empty streams are omitted. Tails are bounded by characters, not by process
runtime, so large installer logs do not explode the error message.

## Tests

Add focused unit tests in `cli/python/base_setup/tests/test_artifacts.py` for:

- stdout and stderr are streamed to the caller and logged
- failure messages include bounded stdout and stderr tails
- sensitive output is redacted from logs and failure messages

Run the focused test file first, then the full `env -u BASE_HOME ./bin/base-test`
suite.
