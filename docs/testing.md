# Testing

Base uses three test layers. Prefer the narrowest layer that proves the behavior,
then broaden when a change crosses command or runtime boundaries.

The `Tests` GitHub Actions workflow runs for every pull request and for pushes
to `main`. Feature-branch pushes do not start a second copy of the pull-request
workflow. Concurrency is scoped to the pull-request number, or to the Git ref
for default-branch runs, so a newer commit cancels only the superseded run for
the same change.

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
shell commands. Monorepo-wide contract checks that inspect `STANDARDS.md`,
scan all production packages, or invoke shell files live under the top-level
`tests/` directory so they are not mistaken for tests of an installed Python
distribution.

From a Base source checkout with the standalone `base-cli` checkout next to it,
run the Python suite with the same source roots used by CI:

```bash
BASE_CLI_SOURCE_DIR=../base-cli/lib/python \
PYTHONPATH=../base-cli/lib/python:lib/python:cli/python \
python -m pytest
```

If `base-cli` is not at `../base-cli`, replace that path in both assignments
with the absolute path to its `lib/python` directory. `BASE_CLI_SOURCE_DIR`
must point at a directory containing `base_cli/__init__.py`. The pinned
`base-cli` package installed from `requirements-dev.txt` is useful for package
metadata and tooling, but it is not a substitute for this source checkout:
the documented suite imports source-level APIs that the package does not
provide.

The Python CI job also measures coverage for production code under
`cli/python`:

```bash
BASE_CLI_SOURCE_DIR=../base-cli/lib/python \
PYTHONPATH=../base-cli/lib/python:lib/python:cli/python \
python -m pytest \
  --cov=cli/python \
  --cov-report=term-missing \
  --cov-report=json:coverage.json
python -m tests.coverage_gate coverage.json
```

The shared [coverage configuration](../.coveragerc) excludes Python test
modules, package initializers, and `__main__.py` entrypoints from the measured
source set and enables branch measurement. The ratchet checks the JSON report
separately at 85% statements, 76% branches, and 84% combined coverage. These
whole-point floors preserve the existing statement gate and leave a small
cross-version margin below the measured 87.51%, 76.99%, and 84.94% baseline.
The terminal report keeps per-file missing lines and partial branches visible,
while the ratchet prints every metric and names any failed threshold.

This is a regression guard, not a claim that every module has ideal behavioral
coverage. Raise a floor deliberately as lower-covered areas gain focused tests;
do not lower one merely to make a change pass. To prove the failure behavior
locally without changing production code, run
`python -m pytest tests/test_coverage_gate.py -k fails`.

## Bash Command And Runtime Tests

BATS tests next to Bash commands and Base runtime helpers cover shell parsing,
dispatch, small command contracts, and failure messages. Keep these focused on
one command or helper at a time. Reusable Bash library tests live in the
standalone `base-bash-libs` repository.

Before running source-checkout BATS tests for the first time, clone the reusable
Bash library and shared Python framework checkouts next to Base:

```bash
git clone https://github.com/basefoundry/base-bash-libs.git ~/work/base-bash-libs
git clone https://github.com/basefoundry/base-cli.git ~/work/base-cli
```

From a source checkout, run the full command/library suite through:

```bash
env -u BASE_HOME ./bin/base-test
```

`bin/base-test` preflights the Bash dependency before starting the
source-checkout BATS suite. The full suite expects Base to resolve the external
reusable Bash libraries and the standalone `base-cli` package. A normal
`~/work/base` checkout uses sibling `~/work/base-bash-libs` and
`~/work/base-cli`
automatically. A linked issue worktree under `~/work/base-worktrees/<slug>` is a
nonstandard layout because the sibling lookup would search
`~/work/base-worktrees/base-bash-libs` and `~/work/base-worktrees/base-cli`.
For the standard contributor checkout shape, point Base at the reusable Bash
library explicitly and either place `base-cli` at the expected sibling path or
set `BASE_CLI_SOURCE_DIR`:

```bash
BASE_BASH_LIBS_DIR=~/work/base-bash-libs/lib/bash \
BASE_CLI_SOURCE_DIR=~/work/base-cli/lib/python \
env -u BASE_HOME ./bin/base-test
```

`basectl test base` delegates to the same runner when the `base` project
resolves to a source checkout. In a packaged install such as Homebrew,
`basectl test base` is package-aware: it runs the packaged Python test layer and
skips source-checkout-only BATS and integration tests with a message pointing
back to the source checkout command above.

### Declared test requirements

A project can declare a repository-local Python requirements file alongside its
test command:

```yaml
test:
  command: pytest tests/
  requirements: requirements-dev.txt
```

Base supports direct package names with optional exact `==` versions in this
file. `basectl setup <project>` installs the file into the routed project
virtual environment. `basectl check <project>` and `basectl doctor <project>`
report missing packages as `BASE-P181`, while `basectl test <project>` performs
the same read-only preflight and does not execute the test command until the
environment is ready. Paths outside the project root, unsupported requirement
syntax, and uv-managed projects using this field fail closed; uv projects
should declare test dependencies in `pyproject.toml` and use `uv sync`.

Base deliberately uses command-focused BATS regression coverage plus ShellCheck
as the Bash equivalent instead of a line percentage. Contributors changing a
public command or runtime branch must add or update a focused BATS assertion,
then run that test and the full `bin/base-test` suite. Linux CI runs the complete
BATS command matrix and ShellCheck on tracked shell files, so missing behavioral
coverage or unsafe shell changes block the pull request.

This policy avoids adding `kcov` or `bashcov`, whose tracing and platform
requirements would make the macOS/Linux signal inconsistent and whose sourced
shell-line percentages do not establish command behavior. Revisit the decision
if a portable tool can report command-path coverage without changing Base's
runtime behavior; until then, command-focused tests are the reviewed coverage
unit and the required CI signal.

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

## External Base Demo E2E

The [Base Demo E2E workflow](../.github/workflows/base-demo-e2e.yml) runs the
macOS product loop against the real `basefoundry/base-demo` repository on a
nightly schedule and through `workflow_dispatch`. It sets up and checks the
demo, approves its reviewed manifest, then runs the declared test and
non-interactive demo commands. Use the workflow input to validate a specific
`base-demo` branch, tag, or commit.

This job is intentionally separate from Base's own test matrix because it
validates an external manifest and project contract. Its grouped CI output
labels the likely owner as either `Base bug` or `base-demo manifest needs
updating`, while keeping a per-command temporary log path available during the
runner for triage.

Run only integration tests with:

```bash
BASE_INTEGRATION_PYTHON="$HOME/.base.d/base/.venv/bin/python" \
  bats tests/integration/base_workflows.bats
```

## Contract Checks

Contract checks are the narrow review-hardening layer for documented behavior
that has drifted in past reviews: workflow policy, workspace manifest URL
policy, project installer integrity, and CLI docs/help/completion alignment.
They are mapped in [Base Contracts](contracts.md).

Run the current contract slice with:

```bash
tests/contracts/run.sh
```

Use this runner before or during large review-batch triage, and for PRs that
edit the mapped contract areas. It composes existing focused tests and should
stay smaller than the full source-checkout suite.
