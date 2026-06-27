# GitHub Bash Helper Boundary

Status: design note for #1138.
Last reviewed: 2026-06-27

Base has two GitHub-facing Bash surfaces:

- `basectl gh`, implemented in
  `cli/bash/commands/basectl/subcommands/gh.sh`.
- GitHub-backed parts of `basectl repo`, implemented in
  `cli/bash/commands/basectl/subcommands/repo.sh` and command helpers such as
  `repo_agent_guidance.sh` and `repo_installer_template.sh`.

Some of this code is generic `gh` command plumbing that could be reused by
Base-managed repositories. Most of it is Base product workflow and should stay
inside Base.

## Decision

Extract only thin, generic `gh` shell primitives to `base-bash-libs`.

The first reusable library should be small and dependency-free. It should not
know about Base projects, Base branch names, Base issue categories, Base
repository baselines, or GitHub Project metadata. Base should consume the
library as an external dependency, then keep its higher-level workflow policy in
`basectl gh`, `basectl repo`, or Python helpers.

## Reusable Candidates

These helpers are good candidates for a future `base-bash-libs` GitHub library:

| Current helper | Current location | Reusable shape |
|---|---|---|
| `base_gh_require_command` | `gh.sh` | Check that `gh` is installed and print a caller-provided install hint. |
| `base_gh_auth_status_diagnostics` | `gh.sh` | Run `gh auth status -h github.com`, echo bounded diagnostic lines, and print a caller-provided login hint. |
| `base_gh_report_command_failure` | `gh.sh` | Report a failed `gh` command and include auth diagnostics without assuming a Base command name. |
| `base_gh_run` | `gh.sh` | Run `gh "$@"` after command availability checks, with failure reporting as an opt-in wrapper. |
| `base_repo_require_gh` | `repo.sh` | Collapse into the same generic command/auth readiness helper. |

Possible later candidates:

- A generic `gh api` wrapper that preserves stdin input, command arguments, and
  exit status while adding optional diagnostics.
- A bounded retry helper for rate-limit or transient transport failures, if
  multiple Base commands need the same behavior and tests prove the retry
  contract.

## Keep In Base

The following behavior is Base-specific and should not move to
`base-bash-libs`:

- Issue categories, issue creation defaults, and `.github/base-project.yml`
  issue default handling.
- Branch naming, issue-start worktree paths, stale branch policy, branch prune,
  and worktree prune behavior.
- PR body generation from `base_manifest.yaml` and automatic `Fixes #<issue>`
  handling.
- `repo init`, `repo agent-guidance`, and `repo installer-template` generated
  file content and generated PR bodies.
- GitHub repository settings, labels, rulesets, branch protection, and
  repository baseline workflow.
- GitHub Project metadata, Project field defaults, and Project item updates.

Structured GitHub Project behavior should continue moving toward the
`base_github_projects` Python package. It needs schema-aware tests and JSON
payload construction more than another shell abstraction.

## Follow-Up Issue Split

If this extraction proceeds, split the work into two PR trains.

### `base-bash-libs`

Title: Add generic GitHub CLI shell helpers.

Scope:

- Add `lib/bash/gh/lib_gh.sh` with the stdlib guard used by existing libraries.
- Implement generic `gh` command availability, auth diagnostics, failure
  reporting, and command-run helpers.
- Add BATS tests with fake `gh` binaries for installed, missing, auth failure,
  command failure, and success cases.
- Document the library in `lib/bash/gh/README.md`.
- Keep the library free of Base command names, Base issue labels, Project
  fields, branch naming, and repo baseline assumptions.

### Base

Title: Consume reusable GitHub CLI shell helpers from `base-bash-libs`.

Scope:

- Import the new `gh` library through Base's existing `base-bash-libs`
  dependency path.
- Replace only generic command/auth/failure wrappers in `basectl gh` and
  `basectl repo`.
- Keep Base workflow functions, branch policy, Project behavior, generated PR
  bodies, and repo baseline behavior unchanged.
- Preserve BATS coverage for `basectl gh issue list`, `gh issue create`, `gh pr`
  wrappers, `repo configure`, `repo clone`, and generated PR flows.

## Non-Goals

- Do not move GitHub Project metadata semantics to `base-bash-libs`.
- Do not make `base-bash-libs` depend on Base.
- Do not introduce a large GitHub workflow framework before the thin helper
  proves reusable.
- Do not block command-local refactors such as `repo_agent_guidance.sh` while
  the generic helper extraction waits for its own train.
