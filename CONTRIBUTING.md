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
3. Create a branch from the issue using this convention:

   ```text
   <category>/<issue>-<YYYYMMDD>-<slug>
   ```

   Example:

   ```text
   enhancement/179-20260528-projects-list-json
   ```

4. Use an isolated Git worktree for each pull request:

   ```bash
   git fetch origin master
   git worktree add -b <branch> ~/work/base-worktrees/<slug> origin/master
   ```

5. Keep the PR scoped to the issue. Avoid unrelated refactors.
6. Link the PR back to the issue with `Fixes #<issue>` or `Closes #<issue>`.
7. Use the standard PR body and fill in Summary, Issue, Validation, Demo
   Impact, and Notes.
8. After merge, sync `master`, remove the worktree, and delete the local and
   remote branches:

   ```bash
   git -C ~/work/base pull --ff-only origin master
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
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash -s -- --source
~/work/base/bin/basectl setup --dev
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

`bootstrap.sh` installs missing first-mile prerequisites such as Homebrew, Git,
and Bash 4.2+ before handing off to `basectl`. `basectl setup --dev` installs
developer prerequisites such as BATS, the GitHub CLI, and ShellCheck. See
[First-Mile Bootstrap](docs/bootstrap.md) for install modes and boundaries.

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

Use `basectl setup --dev` to install developer prerequisites such as BATS, the
GitHub CLI, and ShellCheck. Use `basectl check --dev` or `basectl doctor --dev`
to diagnose missing developer tools.

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
cli/python/base_setup/registry.py
```

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
- The PR includes `Fixes #<issue>` when it should close the issue.
- `Demo Impact` is meaningful for `needs-demo` work, or explicitly says
  `None.` when no demo update is needed.
