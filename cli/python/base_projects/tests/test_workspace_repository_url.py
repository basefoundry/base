from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_projects.tests.workspace_cli_helpers import invoke_engine
from base_projects.workspace_agent_brief import agent_brief_repository_from_status
from base_projects.workspace_clone_command import clone_workspace_repo
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_onboarding import onboarding_repository_from_status
from base_projects.workspace_report_common import missing_repo_fix
from base_projects.workspace_report_common import workspace_repo_check_details
from base_projects.workspace_report_json import workspace_agent_brief_item_to_json
from base_projects.workspace_report_json import workspace_onboarding_item_to_json
from base_projects.workspace_report_json import workspace_status_item_to_json
from base_projects.workspace_repository_url import redact_repository_url
from base_projects.workspace_repository_url import redact_workspace_source
from base_projects.workspace_repository_url import repository_url_problem
from base_projects.workspace_statuses import WorkspaceProjectStatus


class WorkspaceRepositoryUrlTests(unittest.TestCase):
    def test_redact_workspace_source_removes_credentials_and_secret_parameters(self) -> None:
        cases = (
            (
                "https://user:secret@example.test/workspace.yaml?token=review-token&channel=stable",
                "https://[REDACTED]@example.test/workspace.yaml?token=[REDACTED]&channel=stable",
            ),
            (
                "http://user:secret@example.test/workspace.yaml?token=review-token",
                "http://[REDACTED]@example.test/workspace.yaml?token=[REDACTED]",
            ),
            (
                "/private/tmp/workspace.yaml?token=review-token&channel=stable",
                "/private/tmp/workspace.yaml?token=[REDACTED]&channel=stable",
            ),
            (
                "relative/workspace.yaml?api_key=review-key",
                "relative/workspace.yaml?api_key=[REDACTED]",
            ),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(redact_workspace_source(source), expected)
    def test_safe_repository_urls_are_unchanged(self) -> None:
        urls = (
            "https://github.com/basefoundry/base.git",
            "ssh://git@github.com/basefoundry/base.git",
            "git@github.com:basefoundry/base.git",
            "file:///private/tmp/base.git",
            "/private/tmp/base.git",
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(redact_repository_url(url), url)
                self.assertIsNone(repository_url_problem(url))

    def test_sanitizer_covers_userinfo_parameters_and_malformed_urls(self) -> None:
        cases = (
            (
                "https://user:USERINFO_SECRET@github.com/example/private.git",
                "https://[REDACTED]@github.com/example/private.git",
                "sensitive",
            ),
            (
                "oauth2:SCP_SECRET@gitlab.com:example/private.git",
                "[REDACTED]@gitlab.com:example/private.git",
                "sensitive",
            ),
            (
                "https://github.com/example/private.git?token=QUERY_SECRET&ref=main#password=FRAGMENT_SECRET",
                "https://github.com/example/private.git?token=[REDACTED]&ref=main#password=[REDACTED]",
                "sensitive",
            ),
            (
                "https://[malformed/private.git?token=MALFORMED_SECRET",
                "[REDACTED]",
                "invalid",
            ),
        )
        for url, expected, problem in cases:
            with self.subTest(url=url):
                self.assertEqual(redact_repository_url(url), expected)
                self.assertEqual(repository_url_problem(url), problem)
                self.assertNotIn("_SECRET", expected)

    def test_every_workspace_command_rejects_credentials_without_persisting_or_printing_them(self) -> None:
        sentinel = "WORKSPACE_SECRET_SENTINEL"
        invocations = (
            ("status text", ["status"]),
            ("status json", ["status", "--format", "json"]),
            ("check text", ["check"]),
            ("check json", ["check", "--format", "json"]),
            ("doctor text", ["doctor"]),
            ("doctor json", ["doctor", "--format", "json"]),
            ("onboarding text", ["onboarding"]),
            ("onboarding json", ["onboarding", "--format", "json"]),
            ("agent brief text", ["agent-brief"]),
            ("agent brief json", ["agent-brief", "--format", "json"]),
            ("clone plan", ["clone", "--dry-run"]),
        )
        for label, command in invocations:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    home = root / "home"
                    workspace = root / "workspace"
                    base_home = root / "base"
                    manifest_path = root / "workspace.yaml"
                    home.mkdir()
                    workspace.mkdir()
                    default_manifest = base_home / "lib" / "base" / "default_manifest.yaml"
                    default_manifest.parent.mkdir(parents=True)
                    default_manifest.write_text(
                        "project:\n  name: base-defaults\nartifacts: []\n",
                        encoding="utf-8",
                    )
                    manifest_path.write_text(
                        "\n".join(
                            (
                                "schema_version: 1",
                                "workspace:",
                                "  name: private-suite",
                                "repos:",
                                "  - name: private",
                                f"    url: https://user:{sentinel}@github.com/example/private.git",
                                "",
                            )
                        ),
                        encoding="utf-8",
                    )
                    args = command + ["--workspace", str(workspace), "--manifest", str(manifest_path)]

                    with mock.patch("base_projects.workspace_clone_command.run_project_command") as run_command:
                        status, stdout, stderr = invoke_engine(args, base_home, home)

                    run_command.assert_not_called()
                    self.assertEqual(status, 1)
                    self.assertNotIn(sentinel, stdout + stderr)
                    self.assertIn("Git credential helper or SSH configuration", stdout + stderr)
                    for path in home.rglob("*"):
                        if path.is_file():
                            self.assertNotIn(sentinel, path.read_text(encoding="utf-8", errors="replace"))

    def test_status_json_defensively_redacts_an_internal_unsafe_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = WorkspaceManifest(
                path=root / "workspace.yaml",
                name="private-suite",
                repos=(WorkspaceManifestRepo(name="private"),),
            )
            status = WorkspaceProjectStatus(
                name="private",
                root=root / "private",
                manifest_path=None,
                status="error",
                venv="unknown",
                manifest="unknown",
                issues=(),
                expected=True,
                required=True,
                repo="missing",
                repository="private",
                url="https://github.com/example/private.git?token=JSON_SECRET_SENTINEL",
            )

            payload = workspace_status_item_to_json(status, manifest)

        self.assertEqual(
            payload["url"],
            "https://github.com/example/private.git?token=[REDACTED]",
        )
        self.assertNotIn("JSON_SECRET_SENTINEL", str(payload))

    def test_every_internal_repository_url_consumer_defensively_sanitizes(self) -> None:
        sentinel = "INTERNAL_SECRET_SENTINEL"
        unsafe_url = f"https://user:{sentinel}@gitlab.com/example/private.git?token={sentinel}"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = WorkspaceManifestRepo(name="private", url=unsafe_url)
            manifest = WorkspaceManifest(
                path=root / "workspace.yaml",
                name="private-suite",
                repos=(repo,),
            )
            status = WorkspaceProjectStatus(
                name="private",
                root=root / "private",
                manifest_path=None,
                status="error",
                venv="unknown",
                manifest="unknown",
                issues=(),
                expected=True,
                required=True,
                repo="missing",
                repository="private",
                url=unsafe_url,
            )
            onboarding = onboarding_repository_from_status(status)
            agent_brief = agent_brief_repository_from_status(status)
            rendered_consumers = (
                workspace_repo_check_details(repo, status.root, present=False),
                missing_repo_fix(repo, status.root),
                workspace_status_item_to_json(status, manifest),
                workspace_onboarding_item_to_json(onboarding),
                workspace_agent_brief_item_to_json(agent_brief),
            )

            ctx = mock.Mock()
            result = clone_workspace_repo(
                ctx,
                root / "base" / "bin" / "basectl",
                repo,
                status.root,
                dry_run=True,
            )

        self.assertEqual(result.status, "failed")
        rendered_consumers += (result.detail,)
        for rendered in rendered_consumers:
            with self.subTest(rendered=rendered):
                self.assertNotIn(sentinel, str(rendered))
                self.assertIn("[REDACTED]", str(rendered))
