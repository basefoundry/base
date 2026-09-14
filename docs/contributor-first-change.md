# First External Change

This guide is for a technically adjacent contributor who wants to make one
small, reviewable change without learning the entire Base Foundry workspace.
Use the target repository's local contribution and security documents when they
are more specific. Do not put credentials, private data, or vulnerability
details in an issue, branch, log, or pull request.

## Before you start

Choose the smallest path that matches the change:

| Change | Checkout needed | First validation |
| --- | --- | --- |
| Documentation, fixture, or small public-guidance correction | One repository | `git diff --check` and any focused docs test |
| Focused base-cli change | `base-cli` only, plus the repository's Python environment | The affected pytest target |
| Focused base-bash-libs change | `base-bash-libs` only, plus Bash 4.2+, BATS, and ShellCheck | The affected BATS test or `./tests/validate.sh` |
| Full Base runtime or cross-repository change | Base plus the sibling `base-cli` and `base-bash-libs` checkouts | The affected test, then the required source-checkout suite |

Base's supported contributor platforms are macOS 14 or newer and Ubuntu/Debian
as documented by the repository. Native Windows is not yet a supported
contributor environment; the staged Windows work is planned for v1.11.0.

## Path 1: documentation-only

This is the lowest-prerequisite path. It needs Git and a text editor; it does
not need `basectl`, GitHub authentication, sibling repositories, a Python
environment, or a dedicated Git worktree for local editing.

1. Fork [Base](https://github.com/basefoundry/base) in GitHub, then clone your
   fork into a disposable directory:

   ```bash
   git clone https://github.com/YOUR-USER/base.git
   cd base
   ```

2. Create a branch using the repository's public naming convention. For an
   issue-backed change, use the issue number and a real calendar date:

   ```bash
   git switch -c documentation/2278-20260914-troubleshooting-decision-tree
   ```

   A repository-local issue branch policy remains authoritative. The example
   uses starter issue [#2278](https://github.com/basefoundry/base/issues/2278);
   choose an open issue that matches the work instead of claiming this one.

3. Make the smallest edit, then run the focused check:

   ```bash
   git diff --check
   ```

   If the page has a focused documentation test, run that test too. A
   documentation-only change does not require the full ecosystem test suite.

4. Push the branch to your fork and open a pull request from the GitHub web
   interface or with `gh pr create`. Include the issue link, what changed, and
   the exact validation result. The pull request targets `basefoundry/base` and
   `main`; it does not need write access to the upstream repository.

## Path 2: focused component change

Use one component checkout for a focused base-cli or base-bash-libs change. Do
not clone Base or unrelated demos unless the issue explicitly crosses that
boundary.

### base-cli

From a fresh `base-cli` fork or clone, create the issue-backed branch and install
the repository's development extras in its local environment:

```bash
git clone https://github.com/YOUR-USER/base-cli.git
cd base-cli
git switch -c documentation/344-20260914-public-consumer-recipe
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,typer,quality]"
.venv/bin/python -m pytest tests/test_app_run.py -q
```

Replace the test target with the smallest target that covers the issue. The
standalone component can be validated without a Base checkout. Use the current
`CONTRIBUTING.md` for broader quality checks.

### base-bash-libs

From a fresh `base-bash-libs` fork or clone, check the runtime before choosing a
test:

```bash
git clone https://github.com/YOUR-USER/base-bash-libs.git
cd base-bash-libs
git switch -c documentation/491-20260914-bash-support-quickstart
bash --version
./tests/validate.sh
```

The supported floor is Bash 4.2+. On macOS, use Homebrew Bash rather than the
system Bash when the focused test needs Bash 4.2 behavior. Install BATS and
ShellCheck according to the repository documentation; do not broaden the
change into a Base checkout unless the issue requires it.

## Path 3: full Base change

Use this path when the change touches Base runtime behavior, Base-owned GitHub
workflow, or a cross-repository contract. Start from an issue and use either a
normal fork branch or the maintainer worktree workflow. Full source-checkout
validation needs the sibling providers:

```bash
git clone https://github.com/YOUR-USER/base.git
git clone https://github.com/basefoundry/base-cli.git ../base-cli
git clone https://github.com/basefoundry/base-bash-libs.git ../base-bash-libs
cd base
git switch -c enhancement/1234-20260914-focused-change
BASE_BASH_LIBS_DIR=../base-bash-libs/lib/bash \
BASE_CLI_SOURCE_DIR=../base-cli/lib/python \
env -u BASE_HOME ./bin/base-test
```

Run the narrowest affected test first. The full source-checkout suite is a
release or cross-boundary gate, not a prerequisite for every documentation or
component contribution.

## Pull request and review

Use the public pull-request template. Include:

- the issue or a concise explanation for a repository-permitted small fix;
- the user-visible outcome;
- focused validation and any unavailable checks;
- documentation, demo, security, and compatibility impact; and
- a note when the change is intentionally limited to one component.

The upstream repository's issue-backed branch policy and review checks still
apply. No contributor needs internal `basectl`, a private Project token, or a
pre-existing worktree. Do not open a duplicate PR: search the issue and branch
before starting, and comment with your intended scope.

## Common recovery

- If a focused test cannot find a sibling provider, either clone the required
  provider at the documented relative path or choose a component-only issue.
- If a command reports a missing optional dependency, install only the extra
  named by that repository's documentation; do not copy the entire ecosystem
  setup.
- If the branch policy rejects a branch, compare its category, issue number,
  date, and slug with the repository's documented convention.
- If checks fail after a rebase, read the first failing job and update the PR
  with the new validation evidence rather than retrying blindly.

## Cleanup

After merge or supersession, remove the disposable clone when its contents are
no longer needed. Keep any patch or test evidence that is useful for the issue,
then close or update the issue according to the [community triage
policy](community-triage.md).
