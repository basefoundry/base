from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def workflow_files() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def load_workflow(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} did not parse as a YAML mapping"
    return payload


def test_all_workflows_cancel_superseded_runs() -> None:
    missing = [path.name for path in workflow_files() if "concurrency" not in load_workflow(path)]

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
