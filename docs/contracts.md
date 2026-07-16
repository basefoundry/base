# Base Contracts

Base contracts are documented promises that should fail loudly when behavior,
docs, tests, generated guidance, or workflow policy drift apart. This registry
maps the first high-value contracts to their source of truth and executable
enforcement.

Use this page during product reviews and large review-batch triage. If a
finding says "the docs say X but the code does Y", add or update a contract row
before treating the fix as complete.

## Contract Registry

| Contract | Source of truth | Enforced by | Failure mode | Area |
| --- | --- | --- | --- | --- |
| GitHub workflow policy | [GitHub Workflow](github-workflow.md), [CI Supply Chain Policy](ci-supply-chain-policy.md), `.github/workflows/*.yml` | `tests/test_github_workflows.py` | Workflow permissions, concurrency, timeout, token, supported Python, or generated-guidance policy drift | CI |
| Workspace manifest repository URL policy | [Workspace Manifest](workspace-manifest.md), `cli/python/base_projects/workspace_manifest.py` | `cli/python/base_projects/tests/test_workspace_manifest.py` | A documented accepted URL form is rejected, or an insecure `http://` repository URL passes silently | Workspace |
| Workspace manifest source policy | [Workspace Manifest](workspace-manifest.md), `cli/python/base_projects/workspace_pull.py` | `cli/python/base_projects/tests/test_workspace_pull.py` | `workspace.manifest_source` accepts cleartext HTTP or overwrites a local manifest after an invalid fetch | Workspace |
| Project installer template integrity | [Project Installers](project-installers.md), `templates/project-install.sh` | `cli/bash/commands/basectl/tests/repo.bats` | The maintained installer template downloads and executes a Base installer without honoring configured SHA-256 verification | Security |
| Base-owned remote shell installer policy | [Remote Installer Policy](remote-installer-policy.md), `cli/python/base_setup/remote_installers.py`, standalone Homebrew entry points | `tests/test_remote_installer_policy.py`, `cli/python/base_setup/tests/test_remote_installers.py`, focused Homebrew BATS tests | A Base-owned installer bypasses the registry, its documented URL drifts, or a managed uv/mise override executes unverified or different bytes | Security |
| CLI local log file privacy | [Local Observability](observability.md), `lib/python/base_cli/logging.py` | `lib/python/base_cli/tests/test_logging.py` | Persistent CLI log files are created with permissive permissions, exposing command details before Base can restrict them | Security |
| CLI docs, help, and completion drift | [Command Quick Reference](command-reference.md), `.ai-context/COMMANDS.md`, `bin/basectl`, shell completion scripts | `cli/bash/commands/basectl/tests/docs.bats`, `cli/bash/commands/basectl/tests/help.bats`, `cli/bash/commands/basectl/tests/completions.bats` | Public help, docs shortcut behavior, command reference, AI context, or completions no longer match the shipped command surface | CLI |
| Public command and JSON stability tiers | [Stability Tiers](stability-tiers.md), [Command Quick Reference](command-reference.md), [Doctor Finding IDs](doctor-findings.md) | `tests/test_stability_tiers_docs.py` | Public command tiers, JSON compatibility rules, or stable finding ID guarantees become undocumented or drift from command docs | Product |
| Read-only inspection JSON | [Inspection JSON](inspection-json.md), [Command Quick Reference](command-reference.md) | `cli/bash/commands/basectl/tests/inspection-json.bats`, `cli/python/base_release/tests/test_engine.py`, `lib/python/base_cli/tests/test_inspection.py`, `tests/test_stability_tiers_docs.py` | A scoped command emits prose or invalid JSON, changes the v1 envelope, loses finding/error semantics, or diverges from text-mode exit policy | CLI |
| Project metadata defaults | `.github/base-project.yml`, [GitHub Workflow](github-workflow.md), [Repository Baseline](repo-baseline.md) | `cli/python/base_github_projects/tests/`, `cli/bash/commands/basectl/tests/gh.bats`, `cli/bash/commands/basectl/tests/repo.bats` | Issue defaults, Project field options, or repo-visible Project configuration drift from the Base Project schema | Product |

## Contract Check Runner

Default Python validation includes the top-level Python contract tests. That
means `python -m pytest` in CI and `./bin/base-test` in a source checkout fail
when GitHub workflow policy or the contract registry drifts.

Run the focused cross-surface contract slice with:

```bash
tests/contracts/run.sh
```

The runner intentionally composes existing focused tests. It is not a
replacement for the full suite. Use it when:

- a review batch reports docs/implementation drift;
- a change edits workflow policy, public command docs, generated guidance,
  workspace manifest policy, or project installer behavior;
- a PR needs a fast contract-focused signal before broader validation.

## Review Finding Taxonomy

Classify future review findings before opening issues:

- `implementation bug`: shipped behavior is wrong even if docs are silent.
- `docs/implementation drift`: docs and behavior disagree.
- `missing regression test`: a fixed bug has no focused test.
- `missing policy test`: a documented policy has no executable guard.
- `duplicated helper/API drift`: parallel helpers disagree or invite inconsistent fixes.
- `stale generated artifact`: generated guidance, completions, or exported context is out of date.

This classification should appear in issue bodies for review-driven findings.
It keeps future passes focused on the failure mode instead of producing another
undifferentiated backlog.
