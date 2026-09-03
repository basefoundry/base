from configparser import ConfigParser
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
COVERAGE_CONFIG = REPO_ROOT / ".coveragerc"
DEV_REQUIREMENTS = REPO_ROOT / "requirements-dev.txt"
TESTS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "tests.yml"
TESTING_DOC = REPO_ROOT / "docs" / "testing.md"
PYTHON_COVERAGE_FLOOR = 85
PYTHON_BRANCH_COVERAGE_FLOOR = 76
PYTHON_COMBINED_COVERAGE_FLOOR = 84
CANONICAL_POSITIONING_DOCS = tuple(
    REPO_ROOT / relative_path
    for relative_path in (
        "AGENTS.md",
        ".github/copilot-instructions.md",
        "CONTRIBUTING.md",
        "skills.md",
        "FAQ.md",
        "docs/README.md",
        "docs/technical-overview.md",
        "docs/base-bash-libs.md",
        "docs/presentations/README.md",
        "docs/presentations/base-newcomer-orientation.md",
    )
)
LOOP_POSITIONING_DOCS = tuple(
    REPO_ROOT / relative_path
    for relative_path in (
        "AGENTS.md",
        ".github/copilot-instructions.md",
        "CONTRIBUTING.md",
        "FAQ.md",
        "docs/README.md",
        "docs/technical-overview.md",
        "docs/presentations/base-newcomer-orientation.md",
    )
)
RETIRED_POSITIONING_TERMS = ("workspace control plane",)
CURRENT_POSITIONING_PHRASE = "local operating contract"
PRODUCT_LOOP = "inventory -> prepare -> verify -> trust -> onboard -> hand off"


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


def pytest_config_list(option: str) -> list[str]:
    parser = ConfigParser()
    parser.read(PYTEST_CONFIG, encoding="utf-8")
    return [line.strip() for line in parser.get("pytest", option).splitlines() if line.strip()]


def test_default_pytest_discovery_includes_top_level_contract_tests() -> None:
    assert "tests" in pytest_config_list("testpaths")


def test_default_pytest_pythonpath_includes_base_package_roots() -> None:
    assert pytest_config_list("pythonpath") == ["lib/python", "cli/python"]


def test_python_coverage_policy_is_wired_and_documented() -> None:
    requirements = DEV_REQUIREMENTS.read_text(encoding="utf-8")
    workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
    coverage_config = COVERAGE_CONFIG.read_text(encoding="utf-8")
    testing_doc = TESTING_DOC.read_text(encoding="utf-8")

    assert "pytest-cov==7.1.0" in requirements
    assert "--cov=cli/python" in workflow
    assert "--cov-report=term-missing" in workflow
    assert "--cov-report=json:coverage.json" in workflow
    assert "python -m tests.coverage_gate coverage.json" in workflow
    assert "branch = True" in coverage_config
    assert "source =\n    cli/python" in coverage_config
    assert "cli/python/**/tests/*" in coverage_config
    assert f"{PYTHON_COVERAGE_FLOOR}% statements" in testing_doc
    assert f"{PYTHON_BRANCH_COVERAGE_FLOOR}% branches" in testing_doc
    assert f"{PYTHON_COMBINED_COVERAGE_FLOOR}% combined" in testing_doc
    assert "python -m tests.coverage_gate coverage.json" in testing_doc
    assert "command-focused BATS regression coverage" in testing_doc


def test_python_test_docs_and_ci_use_the_standalone_base_cli_source_contract() -> None:
    workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
    testing_doc = TESTING_DOC.read_text(encoding="utf-8")
    contributor_doc = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    workflow_guidance = (REPO_ROOT / ".ai-context" / "WORKFLOWS.md").read_text(
        encoding="utf-8"
    )
    skills_doc = (REPO_ROOT / "skills.md").read_text(encoding="utf-8")
    supply_chain_doc = (REPO_ROOT / "docs" / "ci-supply-chain-policy.md").read_text(
        encoding="utf-8"
    )

    source_path = "../base-cli/lib/python"
    pythonpath = f"{source_path}:lib/python:cli/python"

    assert (
        "BASE_CLI_SOURCE_DIR: ${{ github.workspace }}/.dependencies/base-cli/lib/python"
        in workflow
    )
    assert (
        "PYTHONPATH: .dependencies/base-cli/lib/python:lib/python:cli/python"
        in workflow
    )
    for text in (
        testing_doc,
        contributor_doc,
        workflow_guidance,
        skills_doc,
        supply_chain_doc,
    ):
        assert f"BASE_CLI_SOURCE_DIR={source_path}" in text
        assert f"PYTHONPATH={pythonpath}" in text

    for text in (
        testing_doc,
        contributor_doc,
        workflow_guidance,
        skills_doc,
        supply_chain_doc,
    ):
        assert "PYTHONPATH=cli/python" not in text


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


def test_canonical_positioning_docs_keep_current_thesis_and_loop() -> None:
    for path in CANONICAL_POSITIONING_DOCS:
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        label = path.relative_to(REPO_ROOT)

        assert CURRENT_POSITIONING_PHRASE in text, label
        for retired_term in RETIRED_POSITIONING_TERMS:
            assert retired_term not in text, f"{label} reintroduced {retired_term!r}"

    for path in LOOP_POSITIONING_DOCS:
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        assert PRODUCT_LOOP in text, path.relative_to(REPO_ROOT)


def test_superseded_pr_cleanup_guidance_is_shared_across_ai_tools() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    skills = (REPO_ROOT / "skills.md").read_text(encoding="utf-8")
    workflow = GITHUB_WORKFLOW_DOC.read_text(encoding="utf-8")
    ai_context = (REPO_ROOT / ".ai-context" / "WORKFLOWS.md").read_text(encoding="utf-8")
    copilot = (REPO_ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")

    normalized = {
        "agents": " ".join(agents.split()),
        "skills": " ".join(skills.split()),
        "workflow": " ".join(workflow.split()),
        "ai_context": " ".join(ai_context.split()),
    }
    for name in ("agents", "skills", "ai_context"):
        assert "docs/github-workflow.md" in normalized[name]
        assert "superseded-pull-requests" in normalized[name]
        assert "cleanup" in normalized[name]

    assert "replacement" in normalized["workflow"]
    assert "closing comment" in normalized["workflow"]
    assert "remote head ref" in normalized["workflow"]
    assert "user-owned or dirty worktree" in normalized["workflow"]
    assert "cleanup step fails" in normalized["workflow"]
    assert "gh pr close <number>" in normalized["workflow"]
    assert "gh api --method DELETE" in normalized["workflow"]

    assert "superseded-PR close-and-cleanup rule in `AGENTS.md`" in copilot


def test_contract_registry_maps_initial_review_contracts_to_enforcement() -> None:
    text = CONTRACTS_DOC.read_text(encoding="utf-8")

    expected_entries = {
        "GitHub workflow policy": "tests/test_github_workflows.py",
        "Workspace manifest repository URL policy": "cli/python/base_projects/tests/test_workspace_manifest.py",
        "Project installer template integrity": "cli/bash/commands/basectl/tests/repo.bats",
        "Base-owned remote shell installer policy": "tests/test_remote_installer_policy.py",
        "CLI docs, help, and completion drift": "cli/bash/commands/basectl/tests/completions.bats",
        "CLI local log file privacy": "base-cli/tests/test_logging.py",
        "Canonical positioning documentation": "tests/test_contract_hardening.py",
        "Workspace agent-brief JSON schema": "tests/contracts/test_workspace_agent_brief_schema.py",
        "Workspace update JSON schema": "tests/contracts/test_workspace_update_schema.py",
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
        "Base-owned remote shell installer policy",
        "CLI local log file privacy",
        "CLI docs, help, and completion drift",
        "Public command and JSON stability tiers",
        "Read-only inspection JSON",
        "Project metadata defaults",
        "Canonical positioning documentation",
        "Workspace agent-brief JSON schema",
        "Workspace update JSON schema",
        "Native Windows support boundary",
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
        "tests/test_remote_installer_policy.py",
        "cli/python/base_setup/tests/test_remote_installers.py",
        "cli/python/base_projects/tests/test_workspace_manifest.py",
        "cli/python/base_projects/tests/test_workspace_pull.py",
        "tests/contracts/test_workspace_agent_brief_schema.py",
        "tests/contracts/test_workspace_update_schema.py",
        "cli/python/base_release/tests/test_engine.py",
        "cli/bash/commands/basectl/tests/inspection-json.bats",
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
