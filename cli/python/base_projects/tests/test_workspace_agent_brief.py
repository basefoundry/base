from __future__ import annotations

import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine
from base_projects.workspace_agent_brief import REPO_AGENT_GUIDANCE_FILES
from base_projects.workspace_agent_brief import REPO_BASELINE_FILES


REPO_ROOT = Path(__file__).resolve().parents[4]


def write_workspace_manifest(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workspace:",
                "  name: agent-suite",
                "repos:",
                "  - name: ready",
                "    url: git@github.com:example/ready.git",
                "  - name: partial",
                "  - name: missing",
                "    url: https://agent:supersecret@github.com/example/missing.git",
                "  - name: optional",
                "    url: git@github.com:example/optional.git",
                "    required: false",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_project_manifest(project_root: Path, name: str, test_command: str | None = None) -> None:
    project_root.mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  name: {name}"]
    if test_command is not None:
        lines.extend(["test:", f"  command: {test_command}"])
    lines.extend(["python: {}", "artifacts: []", ""])
    (project_root / "base_manifest.yaml").write_text("\n".join(lines), encoding="utf-8")


def write_repo_contract(project_root: Path, name: str, *, context: bool = True) -> None:
    write_project_manifest(project_root, name)
    for relative_path in REPO_BASELINE_FILES:
        path = project_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative_path == "base_manifest.yaml":
            continue
        path.write_text(f"fixture for {relative_path}\n", encoding="utf-8")
    validation_script = project_root / "tests" / "validate.sh"
    validation_script.chmod(0o755)

    for relative_path in REPO_AGENT_GUIDANCE_FILES:
        path = project_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(f"fixture for {relative_path}\n", encoding="utf-8")
    if context:
        context_readme = project_root / ".ai-context" / "README.md"
        context_readme.parent.mkdir(parents=True)
        context_readme.write_text("# Context\n", encoding="utf-8")


def write_ready_python(project_root: Path, home: Path, project: str) -> None:
    if project == "base":
        python_bin = home / ".base.d" / project / ".venv" / "bin" / "python"
    else:
        python_bin = project_root / ".venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_bin.chmod(0o755)


class TerminalStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


def invoke_engine(
    args: list[str],
    base_home: Path,
    home: Path,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    stdout = TerminalStringIO()
    stderr = io.StringIO()
    env = {
        "HOME": str(home),
        "BASE_HOME": str(base_home),
        "BASE_PROJECT": "",
        "BASE_PROJECT_MANIFEST": "",
    }
    if extra_env is not None:
        env.update(extra_env)
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


def shell_array_values(source: str, name: str) -> tuple[str, ...]:
    match = re.search(rf"^{name}=\(\n(?P<body>.*?)^\)$", source, flags=re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"Unable to find shell array {name}")
    return tuple(line.strip() for line in match.group("body").splitlines() if line.strip())


class WorkspaceAgentBriefTests(unittest.TestCase):
    def test_json_reports_ready_missing_optional_and_local_only_repositories(  # pylint: disable=too-many-statements
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_repo_contract(workspace / "ready", "ready")
            write_ready_python(workspace / "ready", home, "ready")
            (workspace / "partial").mkdir(parents=True)
            (workspace / "partial" / "AGENTS.md").write_text("# Local instructions\n", encoding="utf-8")
            partial_validation = workspace / "partial" / "tests" / "validate.sh"
            partial_validation.parent.mkdir(parents=True)
            partial_validation.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            partial_validation.chmod(0o755)
            write_repo_contract(workspace / "local-tool", "local-tool", context=False)
            write_ready_python(workspace / "local-tool", home, "local-tool")

            status, stdout, stderr = invoke_engine(
                [
                    "agent-brief",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--format",
                    "json",
                ],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        repositories = {item["repository"]: item for item in payload["repositories"]}
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["workspace_manifest"]["name"], "agent-suite")
        self.assertEqual(payload["repository_count"], 5)
        self.assertEqual(repositories["ready"]["handoff_status"], "ready")
        self.assertEqual(repositories["ready"]["signals"]["baseline"]["status"], "complete")
        self.assertEqual(repositories["ready"]["signals"]["agent_guidance"]["status"], "complete")
        self.assertEqual(repositories["ready"]["signals"]["ai_context"]["status"], "present")
        self.assertEqual(repositories["ready"]["signals"]["validation"]["source"], "repo_baseline")
        self.assertEqual(repositories["ready"]["url"], "git@github.com:example/ready.git")
        self.assertEqual(repositories["partial"]["handoff_status"], "unmanaged")
        self.assertFalse(repositories["partial"]["base_managed"])
        self.assertIsNone(repositories["partial"]["project"])
        self.assertEqual(repositories["partial"]["signals"]["baseline"]["status"], "not_applicable")
        self.assertEqual(repositories["partial"]["signals"]["agent_guidance"]["status"], "partial")
        self.assertEqual(repositories["partial"]["signals"]["validation"]["source"], "repo_baseline")
        self.assertEqual(repositories["partial"]["next_actions"], [])
        self.assertEqual(repositories["missing"]["handoff_status"], "missing_required")
        self.assertIsNone(repositories["missing"]["project"])
        self.assertEqual(repositories["missing"]["url"], "https://[REDACTED]@github.com/example/missing.git")
        self.assertNotIn("supersecret", stdout)
        self.assertIn("https://[REDACTED]@github.com/example/missing.git", repositories["missing"]["next_actions"][0])
        self.assertEqual(repositories["missing"]["signals"]["baseline"]["status"], "unavailable")
        self.assertEqual(repositories["optional"]["handoff_status"], "missing_optional")
        self.assertEqual(repositories["local-tool"]["scope"], "local_only")
        self.assertFalse(repositories["local-tool"]["expected"])
        self.assertEqual(repositories["local-tool"]["handoff_status"], "ready")
        self.assertEqual(repositories["local-tool"]["signals"]["ai_context"]["status"], "missing")
        self.assertEqual(
            set(repositories["partial"]),
            {
                "repository",
                "project",
                "path",
                "expected",
                "required",
                "base_managed",
                "scope",
                "discovery_status",
                "manifest_path",
                "manifest",
                "venv",
                "handoff_status",
                "signals",
                "next_actions",
            },
        )
        self.assertEqual(
            set(repositories["partial"]["signals"]),
            {"baseline", "agent_guidance", "ai_context", "validation"},
        )
        self.assertEqual(
            set(repositories["partial"]["signals"]["baseline"]),
            {"status", "missing_files", "not_executable_files"},
        )
        self.assertEqual(
            set(repositories["partial"]["signals"]["validation"]),
            {"status", "command", "source"},
        )

    def test_redacts_repository_url_secrets_in_json_and_clone_actions(self) -> None:
        cases = (
            (
                "scp userinfo",
                "oauth2:topsecret@gitlab.com:example/private.git",
                "[REDACTED]@gitlab.com:example/private.git",
                ("topsecret",),
            ),
            (
                "query and fragment",
                "https://gitlab.com/example/private.git?private_token=querysecret&password=passwordsecret"
                "&client_secret=clientsecret&api_key=apikeysecret&authorization=authsecret"
                "&ref=main#access_token=fragmentsecret",
                "https://gitlab.com/example/private.git?private_token=[REDACTED]&password=[REDACTED]"
                "&client_secret=[REDACTED]&api_key=[REDACTED]&authorization=[REDACTED]"
                "&ref=main#access_token=[REDACTED]",
                (
                    "querysecret",
                    "passwordsecret",
                    "clientsecret",
                    "apikeysecret",
                    "authsecret",
                    "fragmentsecret",
                ),
            ),
            (
                "malformed URL",
                "https://[malformed/private.git?token=malformedsecret",
                "[REDACTED]",
                ("malformedsecret",),
            ),
            (
                "missing network authority",
                "https:///oauth2:authoritysecret@gitlab.com/example/private.git",
                "[REDACTED]",
                ("authoritysecret",),
            ),
            (
                "invalid network port",
                "https://gitlab.com:invalid/example/private.git?token=portsecret",
                "[REDACTED]",
                ("portsecret",),
            ),
            (
                "network URL control character",
                "https://gitlab.com/example/private.git?token=controlsecret\nignored",
                "[REDACTED]",
                ("controlsecret",),
            ),
        )
        for label, url, expected_url, secrets in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    home = root / "home"
                    workspace = root / "workspace"
                    base_home = root / "base"
                    manifest_path = root / "workspace.yaml"
                    home.mkdir()
                    base_home.mkdir()
                    workspace.mkdir()
                    manifest_path.write_text(
                        "\n".join(
                            [
                                "schema_version: 1",
                                "workspace:",
                                "  name: private-suite",
                                "repos:",
                                "  - name: private",
                                f"    url: {json.dumps(url)}",
                                "",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    status, stdout, stderr = invoke_engine(
                        [
                            "agent-brief",
                            "--workspace",
                            str(workspace),
                            "--manifest",
                            str(manifest_path),
                            "--format",
                            "json",
                        ],
                        base_home,
                        home,
                    )

                payload = json.loads(stdout)
                private = payload["repositories"][0]
                self.assertEqual(status, 0)
                self.assertEqual(stderr, "")
                self.assertEqual(private["url"], expected_url)
                self.assertIn(expected_url, private["next_actions"][0])
                for secret in secrets:
                    self.assertNotIn(secret, stdout)

    def test_manifest_validation_is_recommended_through_basectl_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_project_manifest(workspace / "ready", "ready", "printf raw-manifest-command")

            status, stdout, stderr = invoke_engine(
                [
                    "agent-brief",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--format",
                    "json",
                ],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        ready = next(item for item in payload["repositories"] if item["repository"] == "ready")
        validation = ready["signals"]["validation"]
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(validation["status"], "available")
        self.assertEqual(validation["source"], "manifest_test")
        self.assertEqual(validation["command"], f"cd {(workspace / 'ready').resolve()} && basectl test")
        self.assertNotIn("raw-manifest-command", stdout)
        self.assertEqual(ready["handoff_status"], "needs_baseline")
        self.assertEqual(
            ready["next_actions"],
            [
                f"basectl repo init ready --path {(workspace / 'ready').resolve()} --agent-ready",
                f"cd {(workspace / 'ready').resolve()} && basectl setup",
                f"cd {(workspace / 'ready').resolve()} && basectl test",
            ],
        )
        self.assertFalse(any("agent-guidance" in action for action in ready["next_actions"]))

    def test_agent_brief_does_not_execute_repo_local_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            marker_path = root / "repo-python-executed"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_repo_contract(workspace / "ready", "ready")
            python_bin = workspace / "ready" / ".venv" / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text(
                "#!/bin/sh\n: > \"${BASE_TEST_AGENT_BRIEF_EXECUTED:?}\"\nexit 0\n",
                encoding="utf-8",
            )
            python_bin.chmod(0o755)

            with mock.patch(
                "base_projects.workspace_report_common.subprocess.run",
                side_effect=AssertionError("workspace agent brief must not run subprocesses"),
            ) as subprocess_run:
                status, stdout, stderr = invoke_engine(
                    [
                        "agent-brief",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest_path),
                        "--format",
                        "json",
                    ],
                    base_home,
                    home,
                    {"BASE_TEST_AGENT_BRIEF_EXECUTED": str(marker_path)},
                )

            subprocess_run.assert_not_called()

        payload = json.loads(stdout)
        ready = next(item for item in payload["repositories"] if item["repository"] == "ready")
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertFalse(marker_path.exists())
        self.assertEqual(ready["venv"], "present_unverified")
        self.assertEqual(ready["handoff_status"], "ready")
        self.assertEqual(
            ready["next_actions"],
            [
                f"basectl repo check {(workspace / 'ready').resolve()} --agent-ready",
                f"cd {(workspace / 'ready').resolve()} && ./tests/validate.sh",
            ],
        )

    def test_complete_baseline_with_missing_guidance_recommends_guidance_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_repo_contract(workspace / "ready", "ready")
            (workspace / "ready" / "AGENTS.md").unlink()
            write_ready_python(workspace / "ready", home, "ready")

            status, stdout, stderr = invoke_engine(
                [
                    "agent-brief",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--format",
                    "json",
                ],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        ready = next(item for item in payload["repositories"] if item["repository"] == "ready")
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(ready["handoff_status"], "needs_agent_guidance")
        self.assertEqual(ready["signals"]["baseline"]["status"], "complete")
        self.assertEqual(ready["signals"]["agent_guidance"]["missing_files"], ["AGENTS.md"])
        self.assertEqual(
            ready["next_actions"],
            [
                f"basectl repo agent-guidance {(workspace / 'ready').resolve()}",
                f"cd {(workspace / 'ready').resolve()} && ./tests/validate.sh",
            ],
        )
        self.assertFalse(any("repo init" in action for action in ready["next_actions"]))

    def test_non_executable_repo_local_python_needs_setup_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_repo_contract(workspace / "ready", "ready")
            python_bin = workspace / "ready" / ".venv" / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("not executable\n", encoding="utf-8")
            python_bin.chmod(0o644)

            with mock.patch(
                "base_projects.workspace_report_common.subprocess.run",
                side_effect=AssertionError("workspace agent brief must not run subprocesses"),
            ) as subprocess_run:
                status, stdout, stderr = invoke_engine(
                    [
                        "agent-brief",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest_path),
                        "--format",
                        "json",
                    ],
                    base_home,
                    home,
                )

            subprocess_run.assert_not_called()

        payload = json.loads(stdout)
        ready = next(item for item in payload["repositories"] if item["repository"] == "ready")
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(ready["venv"], "missing")
        self.assertEqual(ready["handoff_status"], "needs_setup")
        self.assertIn(f"cd {(workspace / 'ready').resolve()} && basectl setup", ready["next_actions"])

    def test_invalid_manifest_and_non_executable_validation_are_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_repo_contract(workspace / "ready", "ready")
            (workspace / "ready" / "base_manifest.yaml").write_text("project: [\n", encoding="utf-8")
            (workspace / "ready" / "tests" / "validate.sh").chmod(0o644)

            status, stdout, stderr = invoke_engine(
                [
                    "agent-brief",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--format",
                    "json",
                ],
                base_home,
                home,
            )

        payload = json.loads(stdout)
        ready = next(item for item in payload["repositories"] if item["repository"] == "ready")
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(ready["handoff_status"], "needs_manifest_repair")
        self.assertIsNone(ready["project"])
        self.assertEqual(ready["signals"]["baseline"]["status"], "incomplete")
        self.assertEqual(ready["signals"]["baseline"]["not_executable_files"], ["tests/validate.sh"])
        self.assertEqual(ready["signals"]["validation"]["status"], "unavailable")

    def test_text_summary_reports_readiness_basis_and_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            write_workspace_manifest(manifest_path)
            write_repo_contract(workspace / "ready", "ready")
            write_ready_python(workspace / "ready", home, "ready")

            status, stdout, stderr = invoke_engine(
                ["agent-brief", "--workspace", str(workspace), "--manifest", str(manifest_path)],
                base_home,
                home,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"Workspace agent brief: {workspace.resolve()} (agent-suite)", stdout)
        self.assertIn("ready                required     ready", stdout)
        self.assertIn("GUIDANCE    VENV               VALIDATION", stdout)
        self.assertIn("complete    present_unverified available", stdout)
        self.assertIn("Ready for agent handoff: 1 of 3 required repositories.", stdout)
        self.assertIn("Readiness is structural and based on non-executing", stdout)
        self.assertIn(".ai-context is reported but is not required", stdout)
        self.assertIn(f"basectl repo check {(workspace / 'ready').resolve()} --agent-ready", stdout)
        self.assertIn(f"cd {(workspace / 'ready').resolve()} && ./tests/validate.sh", stdout)

    def test_python_readiness_file_contract_matches_shell_repo_check(self) -> None:
        repo_source = (REPO_ROOT / "cli/bash/commands/basectl/subcommands/repo.sh").read_text(encoding="utf-8")

        self.assertEqual(shell_array_values(repo_source, "BASE_REPO_BASELINE_FILES"), REPO_BASELINE_FILES)
        self.assertEqual(
            shell_array_values(repo_source, "BASE_REPO_AGENT_GUIDANCE_FILES"),
            REPO_AGENT_GUIDANCE_FILES,
        )


if __name__ == "__main__":
    unittest.main()
