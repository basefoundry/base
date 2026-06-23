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

## Diagnostic Workflow

When a failure crosses Base boundaries, inspect current state before running
commands that intentionally change the checkout or machine. Start with narrow
diagnostics in this order:

```bash
basectl check <project>
basectl doctor <project>
basectl test <project>
```

`basectl check` and `basectl doctor` are non-mutating diagnostics. They should
not install dependencies, rewrite shell profiles, change manifests, or mutate
repositories.

Map each symptom to its likely ownership before changing code:

- Shell startup/profile changes: `lib/shell/` and
  `cli/bash/commands/basectl/subcommands/update_profile.sh`.
- Runtime shell behavior: `lib/bash/runtime/`.
- Public command dispatch and Bash command behavior: `bin/basectl`,
  `cli/bash/commands/basectl/`, and nearby BATS tests.
- Manifest and project-discovery behavior: `base_manifest.yaml`,
  `cli/python/`, `lib/python/`, and integration tests when multiple commands
  interact.
- Python CLI and helper behavior: `cli/python/` and `lib/python/`.

## Python Unit Tests

Python engine and helper behavior lives under `cli/python/**/tests/` and
`lib/python/**/tests/`. These tests should cover parsing, manifest merging,
artifact decisions, JSON output, and error handling without launching public
shell commands.

Run them with:

```bash
PYTHONPATH=lib/python:cli/python python -m pytest
```

## Bash Command And Runtime Tests

BATS tests next to Bash commands and Base runtime helpers cover shell parsing,
dispatch, small command contracts, and failure messages. Keep these focused on
one command or helper at a time. Reusable Bash library tests live in the
standalone `base-bash-libs` repository.

Before running source-checkout BATS tests for the first time, clone the reusable
Bash library checkout next to Base:

```bash
git clone https://github.com/basefoundry/base-bash-libs.git ~/work/base-bash-libs
```

From a source checkout, run the full command/library suite through:

```bash
env -u BASE_HOME ./bin/base-test
```

The full suite expects Base to resolve external reusable Bash libraries. A
normal `~/work/base` checkout uses sibling `~/work/base-bash-libs`
automatically. A linked issue worktree under `~/work/base-worktrees/<slug>` is a
nonstandard layout because the sibling lookup would search
`~/work/base-worktrees/base-bash-libs`. For the standard contributor checkout
shape, point Base at the reusable library checkout explicitly:

```bash
BASE_BASH_LIBS_DIR=~/work/base-bash-libs/lib/bash env -u BASE_HOME ./bin/base-test
```

`basectl test base` delegates to the same runner when the `base` project
resolves to a source checkout. In a packaged install such as Homebrew,
`basectl test base` is package-aware: it runs the packaged Python test layer and
skips source-checkout-only BATS and integration tests with a message pointing
back to the source checkout command above.

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
