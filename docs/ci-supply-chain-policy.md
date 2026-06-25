# CI Supply Chain Policy

Base keeps CI hardening practical and reviewable instead of trying to make
GitHub-hosted runners fully reproducible. The policy below applies to workflows
under `.github/workflows/`.

## GitHub Actions

- Use first-party `actions/*` actions when an action is needed.
- Pin first-party `actions/*` actions to a maintained major tag such as `v4` or
  to a full commit SHA.
- Pin non-GitHub third-party actions to a full 40-character commit SHA. Version
  tags are not enough for third-party actions.
- Prefer shell steps over adding a new action when the command is simple and the
  runner already has the required tool or installs it through an approved
  package manager.

`cli/python/base_setup/tests/test_ci_supply_chain_policy.py` enforces the
action-reference rule.

## Python Dependencies

- Keep developer and CI Python tools pinned in `requirements-dev.txt`.
- Install CI Python tools from `requirements-dev.txt`; do not install floating
  Python tools directly in workflow steps.
- Run `pip-audit` in the security job against `requirements-dev.txt` so pinned
  tool dependencies receive vulnerability coverage.
- Put the `pip-audit` cache under the runner temp directory so the audit does
  not depend on a writable user-home cache path.
- Hash-locked installs are not required for this repository yet. If Base starts
  publishing Python packages or accepting untrusted dependency input in CI, add
  hash locking or a lockfile as a separate reviewed change.

## OS Packages

- Keep OS package installs minimal and local to the jobs that need them.
- Ubuntu jobs may install `bats` and `shellcheck` from the GitHub-hosted
  runner's configured apt repositories.
- macOS jobs may install `bash` and `bats-core` from Homebrew on the
  GitHub-hosted runner.
- Do not add third-party apt repositories, curl-piped installers, or external
  package feeds in CI without documenting the trust boundary in this file.

## Existing Scanners

The security job must keep these checks:

- Bandit over `cli/python` and `lib/python`
- `pip-audit` over `requirements-dev.txt`
- ShellCheck errors over tracked shell entry points and scripts
- ShellCheck warnings as non-blocking signal
