# Testing

Base uses three test layers. Prefer the narrowest layer that proves the behavior,
then broaden when a change crosses command or runtime boundaries.

## Regression And Completion Evidence

Bug fixes should start with a failing test, fixture, or reproduction whenever
practical. The useful proof is not just that the final test passes, but that the
test or reproduction failed for the expected reason before the fix.

Use this order for behavior changes and bug fixes:

1. Reproduce the symptom with the narrowest command or test.
2. Identify the root cause before changing code.
3. Add or update the focused test, fixture, or reproduction.
4. Verify the test fails for the expected reason.
5. Implement the smallest fix that addresses the root cause.
6. Rerun the focused verification, then broaden only when shared behavior is
   touched.

If an automated regression test is not practical, record the manual reproduction
and the final verification command in the PR. Do not claim a bug is fixed,
tests pass, or a contract is preserved without fresh output from the current
checkout or worktree.

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
