# Contributing to Base

Base is a developer tooling repository. Contributions should keep the project
opinionated, testable, and useful as a shared workspace control plane.

## AI-Assisted Development

Coding agents should follow [AGENTS.md](AGENTS.md). It points to the same
workflow and standards in this guide while capturing Base-specific instructions
for issue-backed work, validation, and design-only sessions.

## Workflow

1. Create or choose a GitHub issue before starting implementation work.
2. Make sure the issue has one primary GitHub-style category label:
   - `bug` for defects, regressions, or correctness issues.
   - `enhancement` for new capabilities, product improvements, refactors, and
     most maintenance work.
   - `documentation` for documentation-only work.
   - `ci` for GitHub Actions, tests, release automation, or CI reliability.
   - `security` for security hardening, dependency pinning, static analysis, or
     permission tightening.
3. When the issue is tracked in the repo-named Project, set its Project
   `Status` to `In Progress` before branch or worktree work begins. Move it to
   `In Review` when the PR opens, and verify it is `Done` after merge/closure.
4. Create a branch from the issue using this convention:

   ```text
   <category>/<issue>-<YYYYMMDD>-<slug>
   ```

   Example:

   ```text
   enhancement/179-20260528-projects-list-json
   ```

   `basectl gh issue start <number>` can generate the branch name and matching
   `git worktree add` command from the issue label and title.

   This is a repository rule, not an AI-tool convention. Do not replace the
   category with `feat`, `agent`, `codex`, or another tool-specific prefix.
   Base-managed GitHub configuration enforces the pattern on every non-default
   remote branch, and `basectl gh pr create` rejects an invalid local branch.

5. Use an isolated Git worktree for each pull request:

   ```bash
   git fetch origin main
   git worktree add -b <branch> ~/work/base-worktrees/<slug> origin/main
   ```

6. Keep the PR scoped to the issue. Avoid unrelated refactors.
7. Link the PR back to the issue with `Fixes #<issue>` or `Closes #<issue>`.
8. Use the standard PR body and fill in Summary, Issue, Validation, Demo
   Impact, and Notes.
9. After merge, sync `main`, remove the worktree, and delete the local and
   remote branches:

   ```bash
   git -C ~/work/base pull --ff-only origin main
   git -C ~/work/base worktree remove ~/work/base-worktrees/<slug>
   git -C ~/work/base branch -d <branch>
   git -C ~/work/base push origin --delete <branch>
   ```

For the full policy, including milestone and GitHub Project guidance, see
[GitHub Workflow](docs/github-workflow.md).

## Contributor Setup

On a fresh macOS machine, use `bootstrap.sh` in source mode so the repository is
available for local edits:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source
git clone https://github.com/basefoundry/base-bash-libs.git ~/work/base-bash-libs
~/work/base/bin/basectl setup --profile dev
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

`bootstrap.sh` installs missing first-mile prerequisites such as Homebrew, Git,
and Bash 4.2+ before handing off to `basectl`. `basectl setup --profile dev`
installs developer prerequisites such as BATS, the GitHub CLI, and ShellCheck. See
[First-Mile Bootstrap](docs/bootstrap.md) for install modes and boundaries.

Base source development resolves reusable Bash libraries from the sibling
`~/work/base-bash-libs` checkout. If that checkout already exists, update it
instead of cloning a second copy.

## First External PR

Start with an open issue labeled `good first issue`. A good first contribution
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
For Python-only changes, run the focused pytest target with
`PYTHONPATH=lib/python:cli/python python -m pytest`. For shell command or
runtime changes, run the focused BATS test when one exists and broaden only
when the change crosses command boundaries.

When the full source-checkout suite is needed from a linked worktree under
`~/work/base-worktrees`, export the reusable Bash library path first:

```bash
BASE_BASH_LIBS_DIR=~/work/base-bash-libs/lib/bash env -u BASE_HOME ./bin/base-test
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
- Keep Python package code under `cli/python/` or `lib/python/` as appropriate.
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

- The branch name follows `<category>/<issue>-<YYYYMMDD>-<slug>`.
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
