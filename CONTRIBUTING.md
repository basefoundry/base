# Contributing to Base

Base is a developer tooling repository. Contributions should keep the project
opinionated, testable, and useful as a local operating contract for deterministic
readiness and handoff across independent Git repositories. The durable product
loop is inventory -> prepare -> verify -> trust -> onboard -> hand off.

## License

Base is distributed under Apache-2.0 starting with v1.9.0. Earlier releases
retain the license stated in their release documentation. Unless a separate
written agreement says otherwise, contributions submitted for inclusion in Base
are accepted under the Apache-2.0 terms.

## AI-Assisted Development

Coding agents should follow [AGENTS.md](AGENTS.md). It points to the same
workflow and standards in this guide while capturing Base-specific instructions
for issue-backed work, validation, and design-only sessions.

## Workflow

Use the [GitHub Workflow](docs/github-workflow.md) for the complete
issue-backed workflow, including labels, repo-named Project status, branch and
worktree rules, PR linking, review, supersession, and cleanup. In brief, start
from an issue, implement off `main` in a dedicated worktree, keep the PR scoped
to that issue, and clean up after merge.

New contributors should start with the [First External
Change](docs/contributor-first-change.md) guide. It uses ordinary fork, clone,
branch, focused-test, and pull-request commands; the internal `basectl` and
dedicated-worktree workflow remains available for deeper maintainer work.

## Contributor Setup

On a fresh macOS machine, use `bootstrap.sh` in source mode so the repository is
available for local edits:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source
git clone https://github.com/basefoundry/base-bash-libs.git ~/work/base-bash-libs
git clone https://github.com/basefoundry/base-cli.git ~/work/base-cli
~/work/base/bin/basectl setup --profile dev
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

`bootstrap.sh` installs missing first-mile prerequisites such as Homebrew, Git,
and Bash 4.2+ before handing off to `basectl`. `basectl setup --profile dev`
installs developer prerequisites such as BATS, the GitHub CLI, and ShellCheck. See
[First-Mile Bootstrap](docs/bootstrap.md) for install modes and boundaries.

Base source development resolves reusable Bash libraries from the sibling
`~/work/base-bash-libs` checkout and the standalone Python framework from the
`~/work/base-cli` checkout. If either checkout already exists, update it instead
of cloning a second copy. The Bash checkout is required by the source-checkout
suite; the `base-cli` checkout is also required by the Python test command
shown below.

## First External PR

For the complete public fork path and the distinction between documentation,
focused component, and full Base contributions, see [First External
Change](docs/contributor-first-change.md). Start with an open issue labeled
`good first issue` when the change is issue-backed. A good first contribution
should be real Base work, but it should also be small enough to review without
private maintainer context: documentation corrections, narrow test coverage,
small fixture updates, or tightly scoped command-output polish are usually good
fits.

Before opening the PR:

1. Read the issue acceptance notes and ask for clarification on the issue when
   the expected result is not explicit.
2. Create an issue branch and worktree using the workflow above.
3. Make the smallest change that satisfies the issue.
4. Run the narrowest validation command that proves the change.

For documentation-only starter issues, `git diff --check` is usually enough.
For Python-only changes, run the focused pytest target with the standalone
`base-cli` source path used by CI:

```bash
BASE_CLI_SOURCE_DIR=../base-cli/lib/python \
PYTHONPATH=../base-cli/lib/python:lib/python:cli/python \
python -m pytest
```

For shell command or runtime changes, run the focused BATS test when one exists
and broaden only when the change crosses command boundaries.

When the full source-checkout suite is needed from a linked worktree under
`~/work/base-worktrees`, export the reusable Bash library path first:

```bash
BASE_BASH_LIBS_DIR=~/work/base-bash-libs/lib/bash \
BASE_CLI_SOURCE_DIR=~/work/base-cli/lib/python \
env -u BASE_HOME ./bin/base-test
```

## Running Tests

Run the narrowest relevant checks first, then broaden when the change touches
shared behavior.

Common checks:

```bash
basectl test base
git diff --check
```

Use the integration suite when a change affects cross-command workflows,
workspace discovery, setup/check/doctor behavior, shell profile wiring, or
installation layout assumptions. See [Testing](docs/testing.md) for the testing
layers and integration-test boundaries.

Use `basectl setup --profile dev` to install developer prerequisites such as
BATS, the GitHub CLI, and ShellCheck. Use `basectl check --profile dev` or
`basectl doctor --profile dev` to diagnose missing developer tools.

Shell files should pass ShellCheck. Python changes should pass the existing
Python tests and lint workflows.

## Code Standards

Follow [STANDARDS.md](STANDARDS.md). In particular:

- Keep Bash control flow explicit. Do not rely on `set -e`.
- Keep command implementations under `cli/bash/commands/<command>/`.
- Keep Base-owned Python package code under `cli/python/` or `lib/python/` as
  appropriate. The reusable `base_cli` framework is maintained in the
  standalone `base-cli` repository.
- Put tests next to the command, library, or package they validate.
- Keep public command launchers in `bin/` thin.

## Artifact Registry Changes

Base's curated tool artifact registry lives in:

```text
lib/base/artifact-registry.yaml
cli/python/base_setup/registry.py
```

`lib/base/artifact-registry.yaml` is the registry data file where built-in tool
artifact definitions are declared. `cli/python/base_setup/registry.py` is the
Python loader that validates and exposes that YAML data to setup and check
code.

Python package artifacts are pass-through PyPI package names; they do not need
registry entries unless Base needs special handling for them.

When adding or changing a built-in tool artifact:

- Add or update the registry entry.
- Add tests for lookup and setup/check behavior.
- Keep ordinary Homebrew tools in project `Brewfile` delegation when Base does
  not need to manage the artifact directly.
- Keep project-specific setup logic in the project repository, not in Base.

## Pull Request Checklist

Before opening a PR:

- The branch name follows `<category>/<issue>-<YYYYMMDD>-<slug>`, and its
  category prefix matches the issue's single standard category label.
- The PR is scoped to one issue, unless a documented multi-issue exception
  applies.
- The PR body explains what changed and how it was validated.
- Relevant BATS and Python tests pass.
- Documentation is updated when behavior or user-facing commands change.
- `.ai-context/` is updated when the change affects Base's product shape,
  architecture, command surface, manifest model, workflows, or release status.
- The PR includes `Fixes #<issue>` when it should close the issue.
- `Demo Impact` is meaningful for `needs-demo` work, or explicitly says
  `None.` when no demo update is needed.
