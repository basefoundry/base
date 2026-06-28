from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DOC = REPO_ROOT / "docs" / "contracts.md"
CONTRACT_RUNNER = REPO_ROOT / "tests" / "contracts" / "run.sh"


def test_contract_registry_maps_initial_review_contracts_to_enforcement() -> None:
    text = CONTRACTS_DOC.read_text(encoding="utf-8")

    expected_entries = {
        "GitHub workflow policy": "tests/test_github_workflows.py",
        "Workspace manifest repository URL policy": "cli/python/base_projects/tests/test_workspace_manifest.py",
        "Project installer template integrity": "cli/bash/commands/basectl/tests/repo.bats",
        "CLI docs, help, and completion drift": "cli/bash/commands/basectl/tests/completions.bats",
        "CLI local log file privacy": "lib/python/base_cli/tests/test_logging.py",
    }
    for contract, enforcement in expected_entries.items():
        assert contract in text
        assert enforcement in text

    assert "Source of truth" in text
    assert "Enforced by" in text
    assert "Failure mode" in text


def test_contract_runner_composes_existing_policy_checks() -> None:
    text = CONTRACT_RUNNER.read_text(encoding="utf-8")

    expected_commands = [
        "tests/test_github_workflows.py",
        "cli/python/base_projects/tests/test_workspace_manifest.py",
        "lib/python/base_cli/tests/test_logging.py",
        'bats --filter "project installer template"',
        "cli/bash/commands/basectl/tests/docs.bats",
        "cli/bash/commands/basectl/tests/help.bats",
        "cli/bash/commands/basectl/tests/completions.bats",
    ]
    for command in expected_commands:
        assert command in text


def test_contract_runner_supports_base_worktree_library_layout() -> None:
    text = CONTRACT_RUNNER.read_text(encoding="utf-8")

    assert "../../base-bash-libs/lib/bash" in text


def test_contract_runner_is_executable() -> None:
    assert CONTRACT_RUNNER.exists()
    assert CONTRACT_RUNNER.stat().st_mode & 0o111
