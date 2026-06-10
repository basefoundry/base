# Testing

Base uses three test layers. Prefer the narrowest layer that proves the behavior,
then broaden when a change crosses command or runtime boundaries.

## Python Unit Tests

Python engine and helper behavior lives under `cli/python/**/tests/` and
`lib/python/**/tests/`. These tests should cover parsing, manifest merging,
artifact decisions, JSON output, and error handling without launching public
shell commands.

Run them with:

```bash
PYTHONPATH=lib/python:cli/python python -m pytest
```

## Bash Command And Library Tests

BATS tests next to Bash commands and libraries cover shell parsing, dispatch,
small command contracts, and failure messages. Keep these focused on one command
or library at a time.

Run the full command/library suite through:

```bash
basectl test base
```

## Reproducible debugging and completion checks

Before changing behavior, capture a reproducible failure path:

1. Save the exact failing command, args, and environment assumptions.
2. Re-run once with full command output visible.
3. Test one hypothesis at a time and stop when evidence confirms or rejects it.

Start with narrow diagnostics in this order:

```bash
basectl check <project>
basectl doctor <project>
basectl test <project>
```

`basectl check` and `basectl doctor` should be treated as read-only,
non-mutating diagnostics. They should not install dependencies, rewrite shell
profiles, change manifests, or mutate repositories. Use them to inspect the
current workspace state before running setup, cleanup, or other commands that
intentionally change it.

When failures cross boundaries, map each symptom to ownership:

- Shell startup/profile changes: `lib/bash/` and `cli/bash/`.
- Manifest and project-discovery behavior: `base_manifest.yaml`, `tests/integration/`, and command mapping code.
- Runtime orchestration changes: `bin/basectl` and `lib/bash/runtime/` for
  runtime shell code, plus `lib/shell/` only for shell startup/profile
  snippets.
- Python behavior changes: `cli/python/` and `lib/python/`.

Use this completion gate before marking a change complete:

- Run `git diff --check` and capture the command output.
- Run the narrowest validation commands for the changed layer and capture successful
  command transcripts in the PR.
- Re-run the repro command(s) that previously failed to show the fix.
- Record whether `basectl check` / `basectl doctor` output and exit status changed, and why.
- If checks cannot run in the current environment, call that out explicitly in the PR notes.

## Integration Tests

Integration tests live under `tests/integration/`. They run real `basectl`
launchers against a temporary `HOME`, temporary workspace, copied Base runtime,
and fake project repositories. External platform tools such as `brew` and
`xcode-select` are stubbed so the suite stays deterministic, network-free, and
safe for local machines and CI.

Add integration coverage when a change affects:

- workspace discovery across Base and project repositories
- `basectl setup`, `check`, `doctor`, or `test` working together
- shell profile update behavior
- installation layout assumptions, including Homebrew-style Base homes
- public command behavior that cannot be proven by a single command unit test

The default integration suite should not install real Homebrew packages, edit
real shell startup files, depend on network access, or mutate repositories
outside the temporary BATS workspace.

Run only integration tests with:

```bash
BASE_INTEGRATION_PYTHON="$HOME/.base.d/base/.venv/bin/python" \
  bats tests/integration/base_workflows.bats
```
