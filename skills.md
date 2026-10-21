# Skills

This file documents repeatable AI-assisted development workflows for Base.
Coding standards live in `STANDARDS.md`.

## GitHub Issue And PR Workflow

Use the [GitHub Workflow](docs/github-workflow.md) for the canonical issue,
Project, branch, worktree, pull request, and cleanup policy. Before editing,
complete its [pre-edit workflow gate](docs/github-workflow.md#pre-edit-workflow-gate)
and prefer `basectl gh` for supported operations; use the documented fallbacks
when necessary. Assign agent-created issues to `codeforester` when GitHub
allows it.

## Close a superseded pull request

When a replacement PR carries the work, follow the canonical [superseded PR
closure procedure](docs/github-workflow.md#superseded-pull-requests), including
the closing comment and branch/worktree cleanup. Do not apply it to an ordinary
closed PR without an established replacement.

## Debug and verify Base behavior

Use this workflow when investigating failed Base commands, broken setup/check/
doctor output, failed builds, project discovery surprises, runtime shell drift,
or CI failures.

- Read the full error output first, including stack traces, command output,
  finding IDs, and paths.
- Reproduce the symptom from a clean command line before fixing it. If the
  issue is not reproducible, gather more evidence instead of guessing.
- Check recent changes with `git status`, `git diff`, and relevant commit or PR
  context.
- Trace the bad value or failed state to its source. For cross-layer failures,
  inspect each boundary separately: public launcher, Bash command, Python
  helper, manifest parser, project command, environment variables, and working
  directory.
- Form one hypothesis, make the smallest change that tests it, and rerun the
  focused verification. Do not stack unrelated fixes.
- Keep `basectl check` and `basectl doctor` non-mutating. They should diagnose
  readiness, not repair local state.
- Before claiming completion, run the command that proves the claim in the
  current checkout or worktree and read the output. Report the command and the
  result in the PR and final summary.

For example, a `basectl doctor` bug should usually have both a focused unit
test around the finding logic and a smoke test that exercises the command or
Python entry point that emits the finding.

## Change behavior, fix bugs, or handle review feedback

Use this workflow when changing user-facing Base behavior, shared runtime
behavior, command output, JSON contracts, doctor findings, setup logic, or
public workflow docs.

- Start bug fixes with a failing test, fixture, or reproduction whenever
  practical. Prove it fails for the expected reason before relying on it.
- Keep test scope proportional to risk: focused BATS or pytest first, then
  `basectl test base` or integration checks when shared behavior is touched.
- When an automated test is not practical, document the manual reproduction and
  verification command clearly.
- For docs-only or configuration-only changes, `git diff --check` is usually
  enough unless the change affects CI validation or generated output.
- Evaluate review feedback against Base's product boundaries before
  implementing it. Base is the local operating contract for deterministic
  readiness and handoff; project-specific application behavior belongs in the
  owning project.
- If feedback suggests a larger design or product shift, stop and surface the
  decision instead of hiding it inside a small PR.

## Add or revise a Base agent workflow

Use this workflow when adding or changing reusable AI-assisted development
guidance such as this `skills.md` file, `AGENTS.md`, or workflow documentation.

- Put durable repo-local rules in `AGENTS.md`, `CONTRIBUTING.md`,
  `STANDARDS.md`, `skills.md`, or focused docs. Do not add personal Codex
  runtime settings to the repo.
- Prefer trigger-focused workflow names and descriptions. The first lines
  should make it clear when the workflow applies.
- Keep entries concise and Base-specific. Link to focused docs for longer
  policy instead of duplicating it.
- Align examples with Base conventions: `basectl gh`, `origin/main`,
  `<category>/<issue>-<YYYYMMDD>-<slug>`, and
  `~/work/base-worktrees/<slug>`.
- Review the workflow against likely pressure cases: time pressure, ambiguous
  review feedback, failing tests, dirty worktrees, and temptation to broaden
  Base beyond the workspace control-plane boundary.
- Validate documentation-only workflow changes with `git diff --check`. If a
  CI workflow validates the guidance, run or update that validation too.

## Add a basectl subcommand

Use this workflow when adding or changing a `basectl <command>` feature.

- Public entrypoint: `bin/basectl`
- Command implementation: `cli/bash/commands/basectl/`
- Subcommands: `cli/bash/commands/basectl/subcommands/`
- Tests: `cli/bash/commands/basectl/tests/`
- Update completions: `lib/shell/completions/basectl_completion.sh` and
  `lib/shell/completions/basectl_completion.zsh` — add the new command to the
  top-level command list, add a case block for its options, and keep changed
  flags synchronized.
- Follow shell standards in `STANDARDS.md`.
- Validate focused command behavior with:

```bash
bats cli/bash/commands/basectl/tests/help.bats
bats cli/bash/commands/basectl/tests/setup.bats
```

Swap `setup.bats` for the focused subcommand test file you changed.

## Add a Bash command

Use this workflow when adding a public Base-owned Bash command.

- Add the public launcher under `bin/`.
- Put implementation code under `cli/bash/commands/<command>/`.
- Keep command tests under `cli/bash/commands/<command>/tests/`.
- Prefer a launcher that delegates through `basectl` so the Base runtime owns
  path setup and library loading.
- Add or update the command README when user-facing behavior changes.

## Add a Bash library

Use this workflow when adding shared Bash behavior.

- Library path: `lib/bash/<name>/lib_<name>.sh`
- Module README: `lib/bash/<name>/README.md`
- Tests: `lib/bash/<name>/tests/`
- Use `import_base_lib` from Base runtime scripts.
- Do not use `set -e`; use explicit error handling.
- Validate the module's BATS tests directly before running the broader suite.

## Add a Python CLI feature

Use this workflow when adding or changing Python-backed Base behavior.

- Shared framework: the standalone `base-cli` repository
- Command packages: `cli/python/`
- Command execution wrapper: `bin/base-wrapper`
- Keep Base-owned tests under `cli/python/**/tests/`; framework tests live in
  the standalone `base-cli` repository.
- Run Base Python commands with the standalone `base-cli` source checkout:
  `BASE_CLI_SOURCE_DIR=../base-cli/lib/python` and
  `PYTHONPATH=../base-cli/lib/python:lib/python:cli/python`.
- Validate with:

```bash
BASE_CLI_SOURCE_DIR=../base-cli/lib/python \
PYTHONPATH=../base-cli/lib/python:lib/python:cli/python \
python -m pytest
```

## Add or change artifact setup

Use this workflow when changing `base_manifest.yaml`, default artifacts, or
setup behavior.

- Project manifest: `base_manifest.yaml`
- Default artifacts: `lib/base/default_manifest.yaml`
- Development artifacts: `lib/base/dev_manifest.yaml`
- Artifact registry: `cli/python/base_setup/registry.py`
- Prefer delegation to mature tools over expanding Base-owned setup logic.
- Keep `basectl check` and `basectl doctor` non-mutating.
- Include `tests/install.bats` when installer behavior or setup bootstrap
  behavior changes.

## Change shell startup behavior

Use this workflow when changing profile, rc, completion, or activation behavior.

- Startup snippets: `lib/shell/`
- Runtime shell entrypoint: `lib/bash/runtime/bashrc`
- Profile updater: `cli/bash/commands/basectl/subcommands/update_profile.sh`
- Managed login and interactive snippets must not source `base_init.sh`.
- Validate startup behavior with:

```bash
bats lib/bash/runtime/tests/runtime_bashrc.bats
bats cli/bash/commands/basectl/tests/setup.bats
```

## Release or Homebrew-facing changes

Use this workflow when changing installation, update, or public package
behavior.

- Standalone installer: `install.sh`
- User-facing install test coverage: `tests/install.bats`
- Homebrew tap repository: `https://github.com/basefoundry/homebrew-base`
- User-facing Homebrew install command: `brew install basefoundry/base/base`
- Follow the [Upgrade Contract](docs/upgrading.md) for Homebrew, mutable source,
  and stable tagged source installations. Prefer `basectl update` for Homebrew;
  a direct `brew upgrade` needs setup through the newly linked executable.
  Check version availability before recommending `update --release`.
- Validate with:

```bash
bats tests/install.bats
bin/basectl check
bin/basectl setup --dry-run
```
