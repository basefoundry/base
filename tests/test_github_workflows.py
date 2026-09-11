import re
from pathlib import Path

import yaml

from tests.github_workflow_test_support import load_workflow, workflow_steps


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
COPILOT_INSTRUCTIONS = REPO_ROOT / ".github" / "copilot-instructions.md"
COPILOT_SETUP_WORKFLOW = WORKFLOW_DIR / "copilot-setup-steps.yml"
BASE_CHECK_WORKFLOW = WORKFLOW_DIR / "base-check.yml"
ECOSYSTEM_RELEASE_BOM_WORKFLOW = WORKFLOW_DIR / "ecosystem-release-bom.yml"
BASE_DEMO_E2E_WORKFLOW = WORKFLOW_DIR / "base-demo-e2e.yml"
DOWNSTREAM_VERSION_BUMPS_WORKFLOW = WORKFLOW_DIR / "downstream-version-bumps.yml"
TESTS_WORKFLOW = WORKFLOW_DIR / "tests.yml"
BASE_PROJECT_CONFIG = REPO_ROOT / ".github" / "base-project.yml"
IMPLEMENTATION_ISSUE_TEMPLATE = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "implementation.yml"
FULL_COMMIT_SHA_ACTION_REF = re.compile(r"^[^@]+@[0-9a-f]{40}$")
BASE_BASH_LIBS_GA_COMMIT = "36fec50c446dcea8c521a1ba3e7fee2394f169c0"


def workflow_files() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def load_yaml_mapping(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} did not parse as a YAML mapping"
    return payload


def workflow_action_references_without_full_sha() -> list[str]:
    unpinned: list[str] = []
    for path in workflow_files():
        for job_name, index, step in workflow_steps(path):
            uses = step.get("uses")
            if not isinstance(uses, str) or uses.startswith("./"):
                continue
            if not FULL_COMMIT_SHA_ACTION_REF.match(uses):
                unpinned.append(f"{path.name}:{job_name}:steps[{index}] uses {uses}")
    return unpinned


def workflow_step_by_name(job: dict, name: str) -> dict:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    matches = [step for step in steps if isinstance(step, dict) and step.get("name") == name]
    assert len(matches) == 1, f"Expected exactly one workflow step named {name!r}, found {len(matches)}."
    return matches[0]


def test_all_workflows_cancel_superseded_runs() -> None:
    missing = [path.name for path in workflow_files() if "concurrency" not in load_workflow(path)]

    assert not missing, missing


def test_all_workflows_declare_top_level_permissions() -> None:
    missing = [path.name for path in workflow_files() if "permissions" not in load_workflow(path)]

    assert not missing, missing


def test_all_workflow_jobs_have_timeouts() -> None:
    missing: list[str] = []
    for path in workflow_files():
        jobs = load_workflow(path).get("jobs")
        assert isinstance(jobs, dict), f"{path} jobs did not parse as a YAML mapping"
        for job_name, job in jobs.items():
            assert isinstance(job, dict), f"{path} job {job_name} did not parse as a YAML mapping"
            if "timeout-minutes" not in job:
                missing.append(f"{path.name}:{job_name}")

    assert not missing, missing


def test_all_workflow_action_uses_are_pinned_to_full_commit_sha() -> None:
    unpinned = workflow_action_references_without_full_sha()

    assert not unpinned, unpinned


def test_ecosystem_release_bom_workflow_owns_base_and_required_platform_matrix() -> None:
    workflow = load_workflow(ECOSYSTEM_RELEASE_BOM_WORKFLOW)
    triggers = workflow.get("on") or workflow.get(True)
    inputs = triggers["workflow_dispatch"]["inputs"]
    compatibility = workflow["jobs"]["compatibility"]
    assemble = workflow["jobs"]["assemble"]
    platforms = {item["platform"] for item in compatibility["strategy"]["matrix"]["include"]}
    compatibility_commands = "\n".join(
        step.get("run", "")
        for step in compatibility.get("steps", [])
        if isinstance(step, dict)
    )
    run_commands = "\n".join(
        step.get("run", "")
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if isinstance(step, dict)
    )

    assert workflow["name"] == "Ecosystem Release BOM"
    assert workflow["permissions"] == {"contents": "read"}
    assert platforms == {"ubuntu-24.04", "macos-14"}
    assert set(inputs) == {
        "base_version",
        "base_ref",
        "base_cli_version",
        "base_cli_ref",
        "base_bash_libs_version",
        "base_bash_libs_ref",
        "base_demo_version",
        "base_demo_ref",
    }
    assert assemble["needs"] == "compatibility"
    assert workflow["concurrency"]["group"] == (
        "${{ github.workflow }}-${{ inputs.base_version }}-${{ inputs.base_ref }}"
    )
    assert "base-release-bom assemble" in run_commands
    assert run_commands.count("base-release-bom-row") == 4
    assert "--repository basefoundry/base-cli" in run_commands
    assert "--repository basefoundry/base-bash-libs" in run_commands
    assert "--repository basefoundry/base-demo" in run_commands
    assert "release-bom.sha256" in run_commands
    assert "^\u005b0-9a-f\u005d{40}$" in run_commands
    assert "awk -F': '" not in run_commands
    assert all(
        any(step.get("with", {}).get("path") == ".dependencies/base-demo" for step in job["steps"])
        for job in (compatibility, assemble)
    )
    assert "yaml.safe_load" in run_commands and "Install BOM YAML parser" in str(assemble["steps"])
    assert "--format json --no-notify --yes" in compatibility_commands
    assert 'base_demo_commit="$(git -C "$GITHUB_WORKSPACE/../base-demo" rev-parse HEAD)"' in compatibility_commands
    assert 'printf \'  root: %s\\n\' "$GITHUB_WORKSPACE/.."' in compatibility_commands


def test_downstream_version_bumps_are_release_triggered_idempotent_and_review_gated() -> None:
    workflow = load_workflow(DOWNSTREAM_VERSION_BUMPS_WORKFLOW)
    triggers = workflow.get("on") or workflow.get(True)
    job = workflow["jobs"]["bump"]
    run_commands = "\n".join(
        step.get("run", "")
        for step in job.get("steps", [])
        if isinstance(step, dict)
    )

    assert workflow["name"] == "Downstream Version Bumps"
    assert set(triggers) == {"release", "repository_dispatch", "schedule", "workflow_dispatch"}
    assert triggers["release"] == {"types": ["published"]}
    assert triggers["repository_dispatch"] == {"types": ["base-release-published"]}
    assert triggers["schedule"] == [{"cron": "17 * * * *"}]
    assert workflow["permissions"] == {"contents": "read"}
    assert job["timeout-minutes"] == 20
    assert job["permissions"] == {"contents": "read"}
    assert job["env"]["GH_TOKEN"] == "${{ secrets.BASE_DOWNSTREAM_TOKEN }}"
    assert "BASE_DOWNSTREAM_TOKEN is required" in run_commands
    assert "gh auth setup-git" in run_commands
    assert "base-release-bump:" in run_commands
    assert "downloaded_installer_sha256=\"$(curl -fsSL" in run_commands
    assert "supplied $supplied_installer_sha256" in run_commands
    assert "installer_sha256=\"$downloaded_installer_sha256\"" in run_commands
    assert "gh issue create" in run_commands
    assert "repos/$TARGET_REPOSITORY/issues?state=all&per_page=100" in run_commands
    assert "gh issue reopen" in run_commands
    assert "gh issue comment" in run_commands
    assert "trap cleanup_issue_on_failure EXIT" in run_commands
    assert "gh pr create" in run_commands
    assert "uv lock --upgrade-package base-cli" in run_commands
    assert 'git -C "$clone_dir" push --set-upstream origin' in run_commands
    assert "gh pr merge" not in run_commands


def test_tests_workflow_runs_once_per_pr_commit_and_on_main() -> None:
    workflow = load_workflow(TESTS_WORKFLOW)
    triggers = workflow.get("on") or workflow.get(True)

    assert triggers == {
        "push": {"branches": ["main"]},
        "pull_request": None,
    }
    assert workflow["concurrency"] == {
        "group": "${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}",
        "cancel-in-progress": True,
    }
    assert {
        job["name"]
        for job in workflow["jobs"].values()
    } == {
        "Stable compatibility",
        "Python tests (${{ matrix.python-version }})",
        "BATS tests",
        "macOS smoke tests",
        "Integration tests",
        "Ubuntu source-checkout suite",
        "Security scanners",
    }


def test_tests_workflow_pins_all_base_bash_libs_checkouts_to_ga_revision() -> None:
    refs = [
        step.get("with", {}).get("ref")
        for _, _, step in workflow_steps(TESTS_WORKFLOW)
        if step.get("with", {}).get("repository") == "basefoundry/base-bash-libs"
    ]

    assert refs
    assert refs == [BASE_BASH_LIBS_GA_COMMIT] * len(refs)


def test_reusable_base_check_workflow_contract() -> None:
    workflow = load_workflow(BASE_CHECK_WORKFLOW)
    ci_docs = (REPO_ROOT / "docs" / "basectl-ci.md").read_text(encoding="utf-8")
    triggers = workflow.get("on") or workflow.get(True)
    workflow_call = triggers["workflow_call"]
    inputs = workflow_call["inputs"]
    job = workflow["jobs"]["base-check"]
    steps = job["steps"]
    run_commands = "\n".join(step.get("run", "") for step in steps if isinstance(step, dict))

    assert workflow["name"] == "Reusable Base Check"
    assert workflow["permissions"] == {"contents": "read"}
    assert "concurrency" in workflow
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == 20
    assert inputs["project"] == {
        "description": "Base project name to check.",
        "required": True,
        "type": "string",
    }
    assert inputs["manifest-path"]["default"] == "base_manifest.yaml"
    assert inputs["setup-mode"]["default"] == "source-checkout"
    assert inputs["base-ref"]["default"] == ""
    assert "base-bash-libs-ref" not in inputs
    assert inputs["output-format"]["default"] == "json"
    assert inputs["python-version"]["default"] == "3.13"
    assert "source-checkout|preinstalled" in run_commands
    assert "args=(check --ci \"$BASE_CHECK_PROJECT\" --format \"$BASE_CHECK_OUTPUT_FORMAT\")" in run_commands
    assert "BASE_BASH_LIBS_DIR" in run_commands
    assert "basefoundry/base-bash-libs" in str(steps)
    assert BASE_BASH_LIBS_GA_COMMIT in str(steps)
    assert "${{ inputs.base-ref || github.workflow_sha }}" in str(steps)
    assert "uses: basefoundry/base/.github/workflows/base-check.yml@<base-ref-or-sha>" in ci_docs
    assert "| `setup-mode` | `source-checkout` |" in ci_docs


def test_base_demo_e2e_workflow_covers_the_external_project_loop() -> None:
    workflow = load_workflow(BASE_DEMO_E2E_WORKFLOW)
    triggers = workflow.get("on") or workflow.get(True)
    job = workflow["jobs"]["base-demo-e2e"]
    steps = job["steps"]
    run_commands = "\n".join(step.get("run", "") for step in steps if isinstance(step, dict))

    assert workflow["name"] == "Base Demo E2E"
    assert triggers["schedule"] == [{"cron": "17 3 * * *"}]
    assert "workflow_dispatch" in triggers
    assert workflow["permissions"] == {"contents": "read"}
    assert "concurrency" in workflow
    assert job["runs-on"] == "macos-14"
    assert job["timeout-minutes"] == 45
    assert job["env"]["BASE_DEMO_ENV"] == "baseline"
    assert job["env"]["BASE_CLI_SOURCE_DIR"].endswith(".dependencies/base-cli/lib/python")

    checkout_repositories = [
        step.get("with", {}).get("repository")
        for step in steps
        if isinstance(step, dict) and step.get("uses", "").startswith("actions/checkout@")
        and step.get("with", {}).get("repository")
    ]
    assert checkout_repositories == [
        "basefoundry/base-cli",
        "basefoundry/base-bash-libs",
    ]
    assert BASE_BASH_LIBS_GA_COMMIT in str(steps)
    assert "v0.4.3" in str(steps)

    for command in (
        "basectl setup --ci base-demo",
        "basectl check --ci base-demo",
        "basectl test base-demo",
        "basectl demo base-demo",
    ):
        assert command in run_commands
    assert "basefoundry/base-demo.git" in run_commands
    assert "base-demo manifest needs updating" in run_commands
    assert "owner=\"Base bug\"" in run_commands
    assert "BASE_DEMO_ROOT/base_manifest.yaml" in run_commands
    assert "--non-interactive" in run_commands


def test_copilot_repository_instructions_stay_anchored_to_base_guidance() -> None:
    text = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

    assert "AGENTS.md" in text
    assert "CONTRIBUTING.md" in text
    assert "STANDARDS.md" in text
    assert ".ai-context/" in text
    assert "issue-backed" in text
    assert "Keep Base focused as the local operating contract for deterministic readiness" in text
    assert "Do not require GitHub Copilot" in text


def test_copilot_setup_steps_are_bounded_to_cloud_agent_setup() -> None:
    workflow = load_workflow(COPILOT_SETUP_WORKFLOW)
    triggers = workflow.get("on") or workflow.get(True)
    jobs = workflow["jobs"]
    setup_job = jobs["copilot-setup-steps"]

    assert workflow["name"] == "Copilot setup steps"
    assert triggers == {
        "workflow_dispatch": None,
        "push": {"paths": [".github/workflows/copilot-setup-steps.yml"]},
        "pull_request": {"paths": [".github/workflows/copilot-setup-steps.yml"]},
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert set(jobs) == {"copilot-setup-steps"}
    assert setup_job["runs-on"] == "ubuntu-latest"
    assert setup_job["timeout-minutes"] == 15

    run_commands = "\n".join(
        step.get("run", "")
        for step in setup_job["steps"]
        if isinstance(step, dict)
    )
    assert "python -m pip install -r requirements-dev.txt" in run_commands
    assert "python -m compileall -q cli/python lib/python tests" in run_commands
    assert (
        "python -m pytest tests/test_github_workflows.py "
        "tests/test_issue_branch_policy_workflow.py tests/test_bootstrap_docs.py -q"
    ) in run_commands
    assert "BASE_BASH_LIBS_DIR" not in run_commands
    assert "secrets." not in run_commands


def test_implementation_issue_template_is_copilot_ready_and_project_aligned() -> None:
    template = load_yaml_mapping(IMPLEMENTATION_ISSUE_TEMPLATE)
    project_config = load_yaml_mapping(BASE_PROJECT_CONFIG)["project"]
    fields = {
        field["id"]: field
        for field in template["body"]
        if isinstance(field, dict) and "id" in field
    }

    assert template["name"] == "Implementation issue"
    assert template["labels"] == ["enhancement"]
    assert template["assignees"] == ["codeforester"]
    assert {"goal", "background", "scope", "acceptance_criteria", "validation", "non_goals"} <= fields.keys()
    assert fields["priority"]["attributes"]["options"] == ["P0", "P1", "P2", "P3"]
    assert fields["size"]["attributes"]["options"] == ["T", "S", "M", "L"]
    assert fields["area"]["attributes"]["options"] == project_config["areas"]
    assert fields["initiative"]["attributes"]["options"] == project_config["initiatives"]
    assert "assign this issue to Copilot" in fields["agent_assignment"]["attributes"]["description"]


def test_agentic_coding_platform_initiative_is_documented() -> None:
    project_config = load_yaml_mapping(BASE_PROJECT_CONFIG)["project"]
    implementation_template = load_yaml_mapping(IMPLEMENTATION_ISSUE_TEMPLATE)
    workflow_docs = (REPO_ROOT / "docs" / "github-workflow.md").read_text(encoding="utf-8")
    workflow_context = (REPO_ROOT / ".ai-context" / "WORKFLOWS.md").read_text(encoding="utf-8")
    initiative_fields = [
        field
        for field in implementation_template["body"]
        if isinstance(field, dict) and field.get("id") == "initiative"
    ]

    assert "Agentic Coding Platform" in project_config["initiatives"]
    assert len(initiative_fields) == 1
    assert "Agentic Coding Platform" in initiative_fields[0]["attributes"]["options"]
    assert "Agentic Coding Platform" in workflow_docs
    assert "agent-ready repo baselines" in workflow_docs
    assert "agent-ready repo baselines" in workflow_context


def test_python_tests_run_on_supported_minor_versions() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    python_job = workflow["jobs"]["python"]

    assert python_job["strategy"]["matrix"]["python-version"] == [
        "3.10",
        "3.11",
        "3.12",
        "3.13",
    ]
    setup_steps = [
        step
        for step in python_job["steps"]
        if isinstance(step, dict) and step.get("uses", "").startswith("actions/setup-python@")
    ]

    assert len(setup_steps) == 1
    assert setup_steps[0]["name"] == "Set up Python"
    assert setup_steps[0]["with"] == {"python-version": "${{ matrix.python-version }}"}


def test_macos_smoke_tests_cover_shell_compatibility_surfaces() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    macos_job = workflow["jobs"]["macos"]
    run_commands = "\n".join(
        step.get("run", "")
        for step in macos_job["steps"]
        if isinstance(step, dict)
    )

    assert "lib/bash/version/tests/lib_version.bats" in run_commands
    assert "lib/shell/completions/tests/completions.bats" in run_commands


def test_macos_smoke_tests_cover_bootstrap_dry_run_routes() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    macos_job = workflow["jobs"]["macos"]
    bootstrap_step = workflow_step_by_name(macos_job, "Run bootstrap dry-run install-route checks")
    run_command = bootstrap_step["run"]

    assert "./bootstrap.sh --dry-run --brew" in run_command
    assert './bootstrap.sh --dry-run --source --install-dir "$GITHUB_WORKSPACE"' in run_command
    assert "basectl setup" in run_command
    assert "basectl update-profile" in run_command


def test_ubuntu_source_checkout_consumes_inspection_json() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    job = workflow["jobs"]["ubuntu-source-checkout"]
    validation_step = workflow_step_by_name(job, "Run Ubuntu source-checkout validation")
    run_command = validation_step["run"]

    assert './bin/basectl gh branch stale --days 999999 --format json' in run_command
    assert "jq -e" in run_command
    assert '.schema_version == 1' in run_command
    assert '.command == "gh branch stale"' in run_command
    assert '.data.branches == []' in run_command
    assert '.error == null' in run_command


def test_ubuntu_apt_jobs_remove_flaky_runner_third_party_sources() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "tests.yml")
    jobs = workflow["jobs"]

    for job_name in ("bats", "integration", "ubuntu-source-checkout", "security"):
        steps = jobs[job_name]["steps"]
        first_apt_update_index = next(
            index
            for index, step in enumerate(steps)
            if isinstance(step, dict) and "sudo apt-get update" in step.get("run", "")
        )
        setup_commands = "\n".join(
            step.get("run", "")
            for step in steps[:first_apt_update_index]
            if isinstance(step, dict)
        )

        assert "/etc/apt/sources.list.d/azure-cli.sources" in setup_commands
        assert "/etc/apt/sources.list.d/microsoft-prod.list" in setup_commands


def test_skills_workflow_generates_current_guidance_without_indent_stripping() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "skills.yml")
    create_steps = workflow["jobs"]["create"]["steps"]
    run_commands = "\n".join(step.get("run", "") for step in create_steps if isinstance(step, dict))

    assert "AI_CONTEXT.md" not in run_commands
    assert ".ai-context/README.md" in run_commands
    assert "sed -i 's/^" not in run_commands


def test_skills_workflow_create_pr_is_issue_backed() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "skills.yml")
    triggers = workflow.get("on") or workflow.get(True)
    create_job = workflow["jobs"]["create"]
    commit_step = next(
        step for step in create_job["steps"] if step.get("name") == "Commit and push starter file"
    )
    run_commands = "\n".join(
        step.get("run", "")
        for step in create_job["steps"]
        if isinstance(step, dict)
    )

    assert triggers["workflow_dispatch"]["inputs"]["issue_number"] == {
        "description": "Issue number the generated pull request will close (required with create_pr)",
        "required": False,
        "type": "string",
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert create_job["permissions"] == {
        "contents": "write",
        "issues": "read",
        "pull-requests": "write",
    }
    assert create_job["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert create_job["env"]["ISSUE_NUMBER"] == "${{ inputs.issue_number }}"
    assert '[[ ! "$ISSUE_NUMBER" =~ ^[1-9][0-9]*$ ]]' in run_commands
    assert 'gh issue view "$ISSUE_NUMBER"' in run_commands
    assert 'Issue #$ISSUE_NUMBER must have exactly one Base category label.' in run_commands
    assert 'date_stamp="$(date -u +%Y%m%d)"' in run_commands
    assert commit_step["env"]["ISSUE_CATEGORY"] == "${{ steps.issue.outputs.category }}"
    assert 'branch="${ISSUE_CATEGORY}/${ISSUE_NUMBER}-${date_stamp}-create-skills-md"' in run_commands
    assert "codex/create-skills-md" not in run_commands
    assert '"[codex] Add skills.md"' not in run_commands
    assert '--title "Add skills.md"' in run_commands
    assert "printf '\\nCloses #%s\\n' \"$ISSUE_NUMBER\" >> pr-body.md" in run_commands
    assert "${{ inputs.issue_number }}" not in run_commands
