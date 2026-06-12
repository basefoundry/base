# GitHub Project Roadmap Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `basectl repo init` and `basectl repo configure` land the
standard Base GitHub repository and Project metadata configuration, and fix
Base docs so `Status`, `Priority`, `Area`, `Size`, and `Initiative` are the
standard issue Project fields.

**Architecture:** Keep `basectl repo` as the user-facing onboarding entry
point. Add a lower-level `basectl gh project` surface and focused Python module
for GitHub Projects V2 GraphQL payloads, field matching, option matching, and
dry-run reporting; `repo init` and `repo configure` delegate to that same
Project engine after repository settings, labels, and branch protection. The
feature is idempotent: schema configuration finds or creates the named Project,
creates or updates the named fields and required options, preserves unrelated
fields/options, and issue-field commands update only the explicit fields passed
by the caller.

**Tech Stack:** Bash command dispatch, Python `base_cli`, GitHub CLI
`gh api graphql`, GitHub Projects V2 GraphQL API, BATS, pytest, ShellCheck,
Zsh syntax checks, and Markdown docs.

---

## File Structure

- Modify `docs/github-workflow.md`: document the canonical Project attributes
  and synchronized option sets, including `Initiative`.
- Modify `cli/bash/commands/basectl/subcommands/repo.sh`: add Project metadata
  options to `repo init` and `repo configure`, default Project setup on, and
  call the Project engine after repository GitHub settings.
- Modify `cli/bash/commands/basectl/tests/repo.bats`: add default Project
  configuration, opt-out, dry-run, and warning tests.
- Modify `cli/bash/commands/basectl/subcommands/gh.sh`: add `project` to usage
  and dispatch it to the Python engine through `base-wrapper`.
- Create `cli/python/base_github_projects/__init__.py`: package marker.
- Create `cli/python/base_github_projects/__main__.py`: module entry point.
- Create `cli/python/base_github_projects/engine.py`: parse commands, run
  GraphQL through `gh api graphql`, inspect/configure Project fields, add issue
  items to Projects, and update single-select issue metadata.
- Create `cli/python/base_github_projects/tests/test_engine.py`: unit tests for
  argument parsing, schema comparison, dry-run output, GraphQL command building,
  and item field update sequencing.
- Modify `cli/bash/commands/basectl/tests/gh.bats`: add Bash dispatch and help
  tests for `basectl gh project`.
- Modify `cli/bash/commands/basectl/tests/completions.bats`: assert Bash
  completion includes the new area and options.
- Modify `lib/shell/completions/basectl_completion.sh`: complete
  `gh project`, its subcommands, and supported options.
- Modify `lib/shell/completions/basectl_completion.zsh`: add matching Zsh
  completions.
- Modify `cli/bash/commands/basectl/README.md`, `README.md`,
  `.ai-context/COMMANDS.md`, and `.ai-context/WORKFLOWS.md`: document the
  command surface and the repo/project boundary.
- Modify `CHANGELOG.md`: add the user-visible command and documentation fix.

## Canonical Schema

Use this schema for `--schema base-roadmap`. Project-specific `Initiative`
options are allowed, but the field itself is always required.

```text
Status:
  Triage        GRAY    Needs clarification or initial classification.
  Backlog       BLUE    Accepted but not yet scheduled.
  Ready         GREEN   Scoped enough to pick up.
  In Progress   YELLOW  Actively being worked on.
  In Review     ORANGE  Pull request open, waiting on checks or review.
  Done          PURPLE  Completed or no further work remains.

Priority:
  P0            RED     Urgent or blocking.
  P1            ORANGE  High priority.
  P2            YELLOW  Normal priority.
  P3            BLUE    Low priority or opportunistic.

Area:
  CLI           GRAY    Command surface and user-facing CLI behavior.
  Setup         GRAY    Installation, setup, check, and doctor behavior.
  Workspace     GRAY    Workspace discovery and workspace-level commands.
  Manifest      GRAY    Manifest schema and project contract handling.
  Runtime       GRAY    Activation, shell runtime, and environment behavior.
  Shell         GRAY    Shell libraries, completions, and startup files.
  Python        GRAY    Python command packages and shared Python helpers.
  Docs          GRAY    Documentation and AI context.
  CI            GRAY    Continuous integration and validation automation.
  Packaging     GRAY    Release, Homebrew, installer, and distribution work.
  Security      GRAY    Permission, secret-handling, and hardening work.
  Product       GRAY    Product direction, roadmap, and adoption work.

Size:
  S             GREEN   Small, focused change.
  M             YELLOW  Medium change with multiple files or interactions.
  L             ORANGE  Large change that should be split if possible.

Initiative:
  Field required. Options are project-owned. For Base Roadmap, seed:
  BanyanLabs Dogfood, Workspace Handling, pyproject/uv, v1.0 Readiness,
  Adoption Polish.
```

## Command Surface

```bash
basectl repo init bankbuddy --repo codeforester/bankbuddy
basectl repo configure ~/work/bankbuddy --repo codeforester/bankbuddy
basectl repo configure ~/work/bankbuddy --repo codeforester/bankbuddy --project "BankBuddy Roadmap" --initiative-option MVP --initiative-option Imports
basectl repo configure ~/work/bankbuddy --repo codeforester/bankbuddy --no-project
basectl gh project doctor --project "Base Roadmap" --owner codeforester
basectl gh project configure --project "Base Roadmap" --owner codeforester --schema base-roadmap
basectl gh project configure --project "BankBuddy Roadmap" --owner codeforester --schema base-roadmap --initiative-option MVP --initiative-option Imports
basectl gh project issue set-fields 600 --repo codeforester/base --project "Base Roadmap" --owner codeforester --status Backlog --priority P2 --area CLI --initiative "v1.0 Readiness" --size M
```

Rules:

- `repo init` and `repo configure` enable standard Project metadata by default
  when a GitHub repository is known.
- `--no-project` skips Project V2 configuration.
- `--project <title>` overrides the default Project title. The default is
  `<RepositoryName> Roadmap`, except the Base repository uses `Base Roadmap`.
- `--project-owner <login>` overrides the GitHub Project owner. The default is
  the owner from `--repo <owner/name>` or the inferred `origin` repository.
- `--project-schema base-roadmap` is the only schema in the first release.
- `--initiative-option <name>` can be passed more than once and seeds
  project-specific Initiative options.
- If Project V2 access is missing during `repo init` or `repo configure`, log a
  warning with `gh auth refresh -h github.com -s project` and keep the supported
  repository settings in place.
- `--project` is required for `doctor`, `configure`, and `issue set-fields`.
- `--owner` defaults to the owner inferred from the current Git remote when
  available; otherwise it is required.
- `--repo <owner/name>` is required for `issue set-fields` unless the current
  Git remote can infer it.
- `configure` accepts `--dry-run` and prints the exact field/option changes it
  would make.
- `configure` creates missing `SINGLE_SELECT` fields. If a required field exists
  with a different type, it fails and reports the mismatch.
- `configure` updates required single-select options by name, preserving
  unrelated options on the field.
- `issue set-fields` adds the issue to the Project if needed, then updates only
  the fields explicitly provided.
- `issue set-fields` fails when a requested option is not present; it tells the
  user to run `basectl gh project configure` with the needed
  `--initiative-option` when the missing value is an Initiative.

## Task 1: Fix The Documentation Contract

**Files:**
- Modify: `docs/github-workflow.md`
- Modify: `.ai-context/WORKFLOWS.md`
- Modify: `CHANGELOG.md`

- [ ] Update `docs/github-workflow.md` so the Projects section lists all five
  canonical attributes: `Status`, `Priority`, `Area`, `Size`, and `Initiative`.
- [ ] Replace the current partial `Area` option list with the schema above.
- [ ] Add the Base Roadmap Initiative options from the schema above.
- [ ] Update `.ai-context/WORKFLOWS.md` to say Project metadata uses those five
  fields and that PRs should not be duplicate Project items.
- [ ] Add a `CHANGELOG.md` Unreleased documentation entry:

```markdown
### Changed

- Clarified that Base Roadmap Project metadata standardizes `Status`,
  `Priority`, `Area`, `Size`, and `Initiative` fields.
```

- [ ] Run whitespace validation.

```bash
git diff --check
```

Expected: exit 0.

## Task 2: Add RED Repo Entry-Point Tests

**Files:**
- Modify: `cli/bash/commands/basectl/tests/repo.bats`
- Modify: `cli/bash/commands/basectl/tests/completions.bats`

- [ ] Add a `repo configure --dry-run` test that expects Project metadata to be
  configured by default:

```bash
[[ "$output" == *"Would configure GitHub Project 'Base Demo Roadmap' for 'codeforester/base-demo'."* ]]
[[ "$output" == *"Status, Priority, Area, Size, Initiative"* ]]
```

- [ ] Add a `repo configure --no-project --dry-run` test that expects no
  Project output.
- [ ] Add a `repo configure --project "BankBuddy Roadmap" --project-owner
  codeforester --initiative-option MVP --dry-run` test that expects those
  values to be passed to the Project engine.
- [ ] Add an apply-mode test that mocks `bin/base-wrapper` and expects:

```text
--project base base_github_projects project configure --project Base Demo Roadmap --owner codeforester --schema base-roadmap --repo codeforester/base-demo
```

- [ ] Add a Project-scope failure test where the Project engine returns exit 3
  and stderr contains `gh auth refresh -h github.com -s project`; `repo
  configure` should return success after warning because repository settings
  still landed.
- [ ] Add repo completion assertions for `--project`, `--project-owner`,
  `--project-schema`, `--initiative-option`, and `--no-project`.
- [ ] Run focused BATS and verify RED.

```bash
bats cli/bash/commands/basectl/tests/repo.bats cli/bash/commands/basectl/tests/completions.bats
```

Expected: failure because repo Project options and Project engine delegation do
not exist.

## Task 3: Add RED Bash Dispatch And Completion Tests

**Files:**
- Modify: `cli/bash/commands/basectl/tests/gh.bats`
- Modify: `cli/bash/commands/basectl/tests/completions.bats`

- [ ] Add a help assertion to the existing `basectl gh prints help` test:

```bash
[[ "$output" == *"basectl gh project doctor --project <title>"* ]]
[[ "$output" == *"basectl gh project configure --project <title>"* ]]
[[ "$output" == *"basectl gh project issue set-fields <number>"* ]]
```

- [ ] Add a dispatch test that mocks `bin/base-wrapper` with a temporary wrapper
  in `PATH` and expects `--project base base_github_projects project doctor`.

```bash
@test "basectl gh project dispatches to Python engine" {
    cat > "$TEST_MOCKBIN/base-wrapper" <<'WRAPPER'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${BASE_GH_TEST_STATE_DIR:?}/wrapper-args"
WRAPPER
    chmod +x "$TEST_MOCKBIN/base-wrapper"

    run env \
        HOME="$TEST_HOME" \
        BASE_HOME="$BASE_REPO_ROOT" \
        BASE_GH_TEST_STATE_DIR="$TEST_STATE_DIR" \
        PATH="$TEST_MOCKBIN:$PATH" \
        bash -c '
            source "$BASE_HOME/base_init.sh"
            source "$BASE_HOME/cli/bash/commands/basectl/subcommands/gh.sh"
            base_gh_subcommand_main project doctor --project "Base Roadmap" --owner codeforester
        '

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_STATE_DIR/wrapper-args")" = "--project base base_github_projects project doctor --project Base Roadmap --owner codeforester" ]
}
```

- [ ] Add completion assertions for `project`, `doctor`, `configure`,
  `issue`, `set-fields`, `--project`, `--owner`, `--schema`, `--dry-run`,
  `--repo`, `--status`, `--priority`, `--area`, `--initiative`, and `--size`.
- [ ] Run focused BATS and verify RED.

```bash
bats cli/bash/commands/basectl/tests/gh.bats cli/bash/commands/basectl/tests/completions.bats
```

Expected: failure because `gh project` dispatch and completions do not exist.

## Task 4: Add Thin Bash Dispatch And Completions

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/gh.sh`
- Modify: `lib/shell/completions/basectl_completion.sh`
- Modify: `lib/shell/completions/basectl_completion.zsh`
- Modify: `cli/bash/commands/basectl/README.md`

- [ ] Update `base_gh_usage()` with:

```text
  basectl gh project doctor --project <title> [--owner <login>] [--schema base-roadmap]
  basectl gh project configure --project <title> [--owner <login>] [--schema base-roadmap] [--initiative-option <name>] [--dry-run]
  basectl gh project issue set-fields <number> --project <title> [--owner <login>] [--repo <owner/name>] [field options...]
```

- [ ] Add a `base_gh_do_project()` helper:

```bash
base_gh_do_project() {
    local wrapper="$BASE_HOME/bin/base-wrapper"

    [[ -x "$wrapper" ]] || {
        base_gh_error "Base Python wrapper '$wrapper' is missing or is not executable."
        return 1
    }
    "$wrapper" --project base base_github_projects project "$@"
}
```

- [ ] Add `project) base_gh_do_project "$@" ;;` to
  `base_gh_subcommand_main()`.
- [ ] Update Bash and Zsh completions for the command surface in Task 2.
- [ ] Update `cli/bash/commands/basectl/README.md` to mention Project metadata
  support.
- [ ] Run focused Bash/completion tests.

```bash
bats cli/bash/commands/basectl/tests/gh.bats cli/bash/commands/basectl/tests/completions.bats
zsh -n lib/shell/completions/basectl_completion.zsh
```

Expected: Bash dispatch/completion tests pass; Python command tests still do not
exist until Task 4.

## Task 5: Add Python Project Schema Engine Tests

**Files:**
- Create: `cli/python/base_github_projects/__init__.py`
- Create: `cli/python/base_github_projects/__main__.py`
- Create: `cli/python/base_github_projects/engine.py`
- Create: `cli/python/base_github_projects/tests/test_engine.py`

- [ ] Create the package files with a minimal `main()` that returns 0 for help.
- [ ] Add tests for `parse_args()`:
  - `project doctor --project "Base Roadmap" --owner codeforester`
  - `project configure --project "Base Roadmap" --owner codeforester --schema base-roadmap --dry-run`
  - `project issue set-fields 600 --repo codeforester/base --project "Base Roadmap" --owner codeforester --status Backlog --priority P2 --area CLI --initiative "v1.0 Readiness" --size M`
- [ ] Add tests for `compare_schema(project, schema)`:
  - missing fields produce missing-field findings
  - wrong field type produces an error finding
  - missing options produce missing-option findings
  - extra options are preserved and do not fail doctor
- [ ] Add tests for dry-run configure output:

```text
[DRY-RUN] Would create Project field Status as SINGLE_SELECT.
[DRY-RUN] Would add Project option Area=CLI.
[DRY-RUN] Would add Project option Initiative=v1.0 Readiness.
```

- [ ] Add tests for issue field update sequencing:
  - resolve Project by owner/title
  - resolve issue by repo/number
  - add issue item to Project when missing
  - update only provided fields
  - fail when a provided option name is absent
- [ ] Run pytest and verify RED.

```bash
PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_github_projects/tests -q
```

Expected: failure because the engine is only a stub.

## Task 6: Implement Project Schema Discovery And Doctor

**Files:**
- Modify: `cli/python/base_github_projects/engine.py`
- Modify: `cli/python/base_github_projects/tests/test_engine.py`

- [ ] Define dataclasses:

```python
@dataclass(frozen=True)
class SelectOption:
    name: str
    color: str
    description: str
    option_id: str | None = None

@dataclass(frozen=True)
class SelectFieldSpec:
    name: str
    options: tuple[SelectOption, ...]

@dataclass(frozen=True)
class ProjectField:
    field_id: str
    name: str
    data_type: str
    options: tuple[SelectOption, ...] = ()
```

- [ ] Encode the canonical schema from this plan as `BASE_ROADMAP_SCHEMA`.
- [ ] Add `run_gh_graphql(query: str, variables: dict[str, str]) -> dict`.
  It should run:

```python
subprocess.run(
    ["gh", "api", "graphql"],
    input=json.dumps({"query": query, "variables": variables}),
    text=True,
    capture_output=True,
    check=False,
)
```

- [ ] Add `find_project(owner: str, title: str)` that queries both
  `user(login: $owner)` and `organization(login: $owner)` with
  `projectsV2(first: 100)`, then matches `title` locally.
- [ ] Add `fetch_project_fields(project_id: str)` using:

```graphql
query($id: ID!) {
  node(id: $id) {
    ... on ProjectV2 {
      id
      title
      fields(first: 50) {
        nodes {
          __typename
          ... on ProjectV2Field { id name dataType }
          ... on ProjectV2SingleSelectField {
            id
            name
            dataType
            options { id name color description }
          }
        }
      }
    }
  }
}
```

- [ ] Add `doctor` command rendering:

```text
OK      Status
MISSING Initiative
ERROR   Area exists with type TEXT; expected SINGLE_SELECT.
```

- [ ] Run tests.

```bash
PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_github_projects/tests -q
```

Expected: pass for parser, schema comparison, and doctor tests.

## Task 7: Implement Idempotent Project Configure

**Files:**
- Modify: `cli/python/base_github_projects/engine.py`
- Modify: `cli/python/base_github_projects/tests/test_engine.py`

- [ ] Add `create_single_select_field(project_id, field_spec)` using:

```graphql
mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
  createProjectV2Field(input: {
    projectId: $projectId,
    dataType: SINGLE_SELECT,
    name: $name,
    singleSelectOptions: $options
  }) {
    projectV2Field {
      ... on ProjectV2SingleSelectField { id name }
    }
  }
}
```

- [ ] Add `update_single_select_field(field, field_spec)` using
  `updateProjectV2Field`. Build the option list as existing options by name
  plus required missing options. Preserve existing option ids for existing
  options.
- [ ] For `Initiative`, combine existing options, Base defaults for
  `"Base Roadmap"`, and any repeated `--initiative-option <name>` values.
- [ ] In dry-run mode, print planned creates/updates and perform no mutations.
- [ ] In apply mode, fail on wrong field types before making mutations.
- [ ] Run tests.

```bash
PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_github_projects/tests -q
```

Expected: pass.

## Task 8: Implement Issue Field Updates

**Files:**
- Modify: `cli/python/base_github_projects/engine.py`
- Modify: `cli/python/base_github_projects/tests/test_engine.py`

- [ ] Add issue lookup by repository and issue number:

```graphql
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) { id number title }
  }
}
```

- [ ] Add project item lookup by content id:

```graphql
query($projectId: ID!, $contentId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100) {
        nodes {
          id
          content { ... on Issue { id } }
        }
      }
    }
  }
}
```

- [ ] Add missing issue item through:

```graphql
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}
```

- [ ] Add field updates through:

```graphql
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId,
    itemId: $itemId,
    fieldId: $fieldId,
    value: {singleSelectOptionId: $optionId}
  }) {
    projectV2Item { id }
  }
}
```

- [ ] Validate every provided option name before mutating. If `--initiative
  "New Theme"` is not present, return:

```text
ERROR: Initiative option 'New Theme' was not found in Project 'Base Roadmap'. Run `basectl gh project configure --project "Base Roadmap" --initiative-option "New Theme"` first.
```

- [ ] Run tests.

```bash
PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_github_projects/tests -q
```

Expected: pass.

## Task 9: Wire Repo Entry Point

**Files:**
- Modify: `cli/bash/commands/basectl/subcommands/repo.sh`
- Modify: `cli/bash/commands/basectl/tests/repo.bats`
- Modify: `lib/shell/completions/basectl_completion.sh`
- Modify: `lib/shell/completions/basectl_completion.zsh`

- [ ] Add usage text for:

```text
  --project <title>             GitHub Project title to configure. Defaults to <repo-name> Roadmap.
  --project-owner <login>       GitHub Project owner. Defaults to the repository owner.
  --project-schema <schema>     Project metadata schema. Defaults to base-roadmap.
  --initiative-option <name>    Initiative option to seed; may be repeated.
  --no-project                  Skip GitHub Project metadata configuration.
```

- [ ] Parse these options in `base_repo_init()` and `base_repo_configure()`.
- [ ] Add `base_repo_project_title "$repo"` that returns `Base Roadmap` for
  `codeforester/base` and `<Title Case Repo Name> Roadmap` for other
  repositories.
- [ ] Add `base_repo_configure_project_metadata()` that calls:

```bash
"$BASE_HOME/bin/base-wrapper" --project base base_github_projects project configure \
  --project "$project_title" \
  --owner "$project_owner" \
  --repo "$repo" \
  --schema "$project_schema" \
  "${initiative_options[@]/#/--initiative-option }"
```

- [ ] Build the repeated `--initiative-option <name>` arguments with an array
  instead of string concatenation.
- [ ] Treat Project engine exit code 3 as a warning in `repo init` and
  `repo configure`, logging the engine output and continuing. Treat all other
  nonzero exit codes as failures.
- [ ] Include Project configuration in dry-run output after branch protection.
- [ ] Run focused repo tests.

```bash
bats cli/bash/commands/basectl/tests/repo.bats
```

Expected: pass.

## Task 10: Docs, Help, And Validation

**Files:**
- Modify: `README.md`
- Modify: `docs/github-workflow.md`
- Modify: `cli/bash/commands/basectl/README.md`
- Modify: `.ai-context/COMMANDS.md`
- Modify: `.ai-context/WORKFLOWS.md`
- Modify: `CHANGELOG.md`

- [ ] Add examples for:

```bash
basectl gh project doctor --project "Base Roadmap" --owner codeforester
basectl gh project configure --project "Base Roadmap" --owner codeforester --schema base-roadmap
basectl gh project issue set-fields 600 --repo codeforester/base --project "Base Roadmap" --status Backlog --priority P2 --area CLI --initiative "v1.0 Readiness" --size M
```

- [ ] State that `basectl repo init` and `basectl repo configure` are the
  standard entry points for repository and Project V2 metadata setup, while
  `basectl gh project` is the lower-level direct surface.
- [ ] State that PRs are not added as duplicate Project items by default; the
  issue owns Project metadata.
- [ ] Add `CHANGELOG.md` Unreleased entries for the new command.
- [ ] Run focused tests:

```bash
bats cli/bash/commands/basectl/tests/gh.bats cli/bash/commands/basectl/tests/completions.bats
PYTHONPATH=lib/python:cli/python python -m pytest cli/python/base_github_projects/tests -q
```

Expected: pass.

- [ ] Run shell checks and syntax checks:

```bash
shellcheck --severity=error cli/bash/commands/basectl/subcommands/gh.sh lib/shell/completions/basectl_completion.sh
zsh -n lib/shell/completions/basectl_completion.zsh
git diff --check
```

Expected: all exit 0.

- [ ] Run full Base validation:

```bash
env -u BASE_HOME ./bin/base-test
```

Expected: full test suite passes.

## Task 11: Publish Through The Base Train

- [ ] Create a Base GitHub issue titled
  `Add Base-managed GitHub Project roadmap metadata`.
- [ ] Assign it to `codeforester`, label it `enhancement`, and add it to Base
  Roadmap.
- [ ] Set Project `Status` to `In Progress`.
- [ ] Create branch
  `enhancement/<issue>-20260611-github-project-roadmap-metadata` in a dedicated
  worktree under `/Users/rameshhp/work/base-worktrees/`.
- [ ] Implement the tasks above with focused commits.
- [ ] Open a PR with `Fixes #<issue>`.
- [ ] Set Project `Status` to `In Review`.
- [ ] Watch CI and fix failures.
- [ ] Squash merge when checks are green.
- [ ] Verify issue closed and Project `Status` is `Done`.
- [ ] Sync `/Users/rameshhp/work/base` with `git pull --ff-only`.
- [ ] Run `git fetch --prune`.
- [ ] Remove the task worktree and delete the local branch.

## Self-Review

- Spec coverage: the plan covers the documentation inconsistency, the explicit
  `basectl gh project` command surface, reusable schema management, Base
  Roadmap Initiative support, issue field updates, completions, docs, and full
  validation.
- Placeholder scan: no deferred implementation markers remain; each task has
  concrete files, commands, or expected behavior.
- Type consistency: command names, schema field names, and option names are
  consistent across the command surface, tests, docs, and Python engine tasks.
