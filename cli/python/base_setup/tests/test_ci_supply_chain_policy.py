from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
FULL_SHA_RE = re.compile(r"[a-f0-9]{40}")


def load_workflow(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def workflow_steps(path: Path) -> list[dict[str, Any]]:
    workflow = load_workflow(path)
    steps: list[dict[str, Any]] = []
    for job in workflow["jobs"].values():
        steps.extend(job.get("steps", ()))
    return steps


def workflow_step(path: Path, job: str, name: str) -> dict[str, Any]:
    workflow = load_workflow(path)
    for step in workflow["jobs"][job]["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"{path}: job '{job}' must include step '{name}'.")


def test_github_actions_references_are_pinned_to_full_shas() -> None:
    workflow_paths = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))

    for path in workflow_paths:
        for step in workflow_steps(path):
            uses = step.get("uses")
            if not uses:
                continue

            _action, separator, ref = uses.partition("@")
            assert separator, f"{path}: action reference '{uses}' must include an explicit ref."
            assert FULL_SHA_RE.fullmatch(ref), f"{path}: action '{uses}' must be pinned to a full SHA."


def test_base_bash_libs_ci_checkouts_are_pinned() -> None:
    workflow_paths = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
    checkouts: list[tuple[Path, str]] = []

    for path in workflow_paths:
        for step in workflow_steps(path):
            with_config = step.get("with", {})
            if isinstance(with_config, dict) and with_config.get("repository") == "basefoundry/base-bash-libs":
                ref = with_config.get("ref")
                checkouts.append((path, str(ref)))

    assert checkouts, "CI must explicitly check out basefoundry/base-bash-libs where shell tests need it."
    for path, ref in checkouts:
        assert FULL_SHA_RE.fullmatch(ref), f"{path}: base-bash-libs checkout must pin a full SHA."


def test_security_workflow_runs_python_dependency_audit() -> None:
    requirements = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert re.search(r"^pip-audit==", requirements, re.MULTILINE)

    security_steps = workflow_steps(REPO_ROOT / ".github" / "workflows" / "tests.yml")
    audit_steps = [step for step in security_steps if step.get("name") == "Run pip-audit"]

    assert audit_steps, "tests.yml security job must run pip-audit."
    audit_command = audit_steps[0].get("run", "")
    assert "--cache-dir" in audit_command
    assert "python -m pip_audit" in audit_command
    assert "-r requirements-dev.txt" in audit_command


def test_ci_bats_job_covers_base_test_source_suite() -> None:
    tests_workflow = REPO_ROOT / ".github" / "workflows" / "tests.yml"
    base_test = (REPO_ROOT / "bin" / "base-test").read_text(encoding="utf-8")
    bats_command = workflow_step(tests_workflow, "bats", "Run BATS tests").get("run", "")

    source_checkout_bats = (
        "tests/base_test.bats",
        "tests/base_init.bats",
        "tests/bootstrap.bats",
        "tests/install.bats",
        "tests/source_guards.bats",
    )
    for test_path in source_checkout_bats:
        assert test_path in base_test
        assert test_path in bats_command


def test_ci_includes_ubuntu_source_checkout_base_test_job() -> None:
    tests_workflow = REPO_ROOT / ".github" / "workflows" / "tests.yml"
    workflow = load_workflow(tests_workflow)
    ubuntu_job = workflow["jobs"].get("ubuntu-source-checkout")

    assert ubuntu_job is not None, "tests.yml must include an Ubuntu source-checkout job."
    assert ubuntu_job["runs-on"] == "ubuntu-latest"

    bash_libs_checkouts = [
        step
        for step in ubuntu_job["steps"]
        if step.get("with", {}).get("repository") == "basefoundry/base-bash-libs"
    ]
    assert bash_libs_checkouts, "Ubuntu source-checkout CI must fetch base-bash-libs."
    assert bash_libs_checkouts[0]["with"]["path"] == ".dependencies/base-bash-libs"

    steps = {step.get("name"): step for step in ubuntu_job["steps"]}
    sibling_command = steps["Expose reusable Bash library checkout as sibling"].get("run", "")
    assert ".dependencies/base-bash-libs" in sibling_command
    assert "../base-bash-libs" in sibling_command

    install_command = steps["Install Ubuntu source-checkout prerequisites"].get("run", "")
    for package in (
        "git",
        "curl",
        "build-essential",
        "ca-certificates",
        "python3-venv",
        "python3-pip",
        "bats",
        "shellcheck",
        "jq",
        "golang-go",
    ):
        assert package in install_command

    venv_command = steps["Prepare Base test virtual environment"].get("run", "")
    assert "$HOME/.base.d/base/.venv" in venv_command
    assert "-r requirements-dev.txt" in venv_command

    validation_command = steps["Run Ubuntu source-checkout validation"].get("run", "")
    assert "./bin/basectl ci check base --format json" in validation_command
    assert "env -u BASE_HOME ./bin/base-test" in validation_command


def test_shellcheck_covers_runtime_bashrc() -> None:
    tests_workflow = REPO_ROOT / ".github" / "workflows" / "tests.yml"
    for step_name in ("Run ShellCheck", "Run ShellCheck warnings"):
        shellcheck_command = workflow_step(tests_workflow, "security", step_name).get("run", "")
        assert "lib/bash/runtime/bashrc" in shellcheck_command
