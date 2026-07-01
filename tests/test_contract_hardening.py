from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DOC = REPO_ROOT / "docs" / "contracts.md"
CONTRACT_RUNNER = REPO_ROOT / "tests" / "contracts" / "run.sh"
PYTEST_CONFIG = REPO_ROOT / "pytest.ini"
ACTIVE_WORKFLOW_GUIDANCE_FILES = (
    REPO_ROOT / ".ai-context" / "WORKFLOWS.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "CONTRIBUTING.md",
)
GITHUB_WORKFLOW_DOC = REPO_ROOT / "docs" / "github-workflow.md"


def contract_registry_rows() -> list[dict[str, str]]:
    text = CONTRACTS_DOC.read_text(encoding="utf-8")
    headers: list[str] = []
    rows: list[dict[str, str]] = []
    in_registry = False

    for line in text.splitlines():
        if line == "## Contract Registry":
            in_registry = True
            continue
        if in_registry and line.startswith("## ") and rows:
            break
        if not in_registry or not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not headers:
            headers = cells
            continue
        if all(set(cell) <= {"-"} for cell in cells):
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))

    return rows


def pytest_testpaths() -> list[str]:
    lines = PYTEST_CONFIG.read_text(encoding="utf-8").splitlines()
    testpaths: list[str] = []
    in_testpaths = False

    for line in lines:
        stripped = line.strip()
        if stripped == "testpaths =":
            in_testpaths = True
            continue
        if not in_testpaths:
            continue
        if line.startswith((" ", "\t")) and stripped:
            testpaths.append(stripped)
            continue
        if stripped:
            break

    return testpaths


def test_default_pytest_discovery_includes_top_level_contract_tests() -> None:
    assert "tests" in pytest_testpaths()


def test_active_project_guidance_uses_repo_named_project_language() -> None:
    for path in ACTIVE_WORKFLOW_GUIDANCE_FILES:
        text = path.read_text(encoding="utf-8")
        assert "Base Roadmap" not in text
        assert "repo-named Project" in text

    issue_metadata_section = GITHUB_WORKFLOW_DOC.read_text(encoding="utf-8").split(
        "## Issue Project Metadata", maxsplit=1
    )[1].split("\n## ", maxsplit=1)[0]
    assert "When an issue is tracked in the `Base Roadmap` Project" not in issue_metadata_section
    assert "repo-named Project" in issue_metadata_section
    assert "use that title only as the migration source" in issue_metadata_section


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


def test_contract_registry_rows_have_complete_enforcement_metadata() -> None:
    rows = contract_registry_rows()

    assert {row["Contract"] for row in rows} == {
        "GitHub workflow policy",
        "Workspace manifest repository URL policy",
        "Workspace manifest source policy",
        "Project installer template integrity",
        "CLI local log file privacy",
        "CLI docs, help, and completion drift",
        "Project metadata defaults",
    }
    for row in rows:
        assert row["Source of truth"], row
        assert row["Enforced by"], row
        assert row["Failure mode"], row
        assert row["Area"], row


def test_contract_runner_composes_existing_policy_checks() -> None:
    text = CONTRACT_RUNNER.read_text(encoding="utf-8")

    expected_commands = [
        "tests/test_github_workflows.py",
        "cli/python/base_projects/tests/test_workspace_manifest.py",
        "cli/python/base_projects/tests/test_workspace_pull.py",
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


def test_bats_tests_do_not_embed_personal_base_bash_libs_path() -> None:
    demo_bats = REPO_ROOT / "cli" / "bash" / "commands" / "basectl" / "tests" / "demo.bats"

    assert "/Users/rameshhp/work/base-bash-libs" not in demo_bats.read_text(encoding="utf-8")


def test_contract_runner_reenters_repo_root_for_each_step() -> None:
    text = CONTRACT_RUNNER.read_text(encoding="utf-8")

    assert '(\n        cd "$REPO_ROOT"\n        "$@"\n    )' in text


def test_contract_runner_is_executable() -> None:
    assert CONTRACT_RUNNER.exists()
    assert CONTRACT_RUNNER.stat().st_mode & 0o111
