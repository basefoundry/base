from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_cli.history import build_finished_record
from base_cli.testing import invoke


def write_manifest(project_root: Path, name: str = "demo", command: str | None = "pytest tests/") -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    manifest_path = project_root / "base_manifest.yaml"
    lines = ["project:", f"  name: {name}"]
    if command is not None:
        lines.extend(["test:", f"  command: {command}"])
    lines.append("artifacts: []")
    manifest_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def write_all_command_surfaces_manifest(project_root: Path, name: str = "demo") -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    manifest_path = project_root / "base_manifest.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "test:",
                "  command: pytest tests/",
                "commands:",
                "  lint: ruff check .",
                "build:",
                "  targets:",
                "    api:",
                "      command: go build ./...",
                "demo:",
                "  script: demo.sh",
                "activate:",
                "  source:",
                "    - .base/activate.sh",
                "artifacts: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def init_git_repo(project_root: Path, origin: str) -> str:
    subprocess.run(["git", "init"], cwd=project_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "base@example.invalid"],
        cwd=project_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "config", "user.name", "Base Tests"],
        cwd=project_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(["git", "add", "base_manifest.yaml"], cwd=project_root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add manifest"],
        cwd=project_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(["git", "remote", "add", "origin", origin], cwd=project_root, check=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


class ManifestCommandTrustTests(unittest.TestCase):
    def test_require_explicit_manifest_populates_history_project_metadata(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            project_root = root / "work" / "demo"
            manifest_path = write_manifest(project_root)
            outside = root / "outside"
            outside.mkdir()
            captured: list[tuple[object, ...]] = []

            with mock.patch(
                "base_cli.app.write_finished_record",
                side_effect=lambda *args: captured.append(args),
            ):
                result = invoke(
                    engine.app,
                    ["require", "demo", "--manifest", str(manifest_path)],
                    home=home,
                    cwd=outside,
                    env={"BASE_HOME": str(root / "base")},
                )

            self.assertEqual(result.exit_code, 0)
            self.assertIn("Manifest-declared commands are not allowed", result.stderr)
            self.assertEqual(len(captured), 1)
            record = build_finished_record(*captured[0])

        self.assertEqual(record["project"], "demo")
        self.assertEqual(record["project_root"], str(project_root.resolve()))
        self.assertEqual(record["manifest"], str(manifest_path.resolve()))

    def test_engine_reexports_trust_store_helpers(self) -> None:
        from base_trust import engine, trust_store

        expected_names = (
            "ALLOWED_COMMANDS",
            "ManifestCommandTrustIdentity",
            "ManifestCommandTrustStore",
            "SCHEMA_VERSION",
            "TRUST_RELATIVE_ROOT",
            "TrustStatus",
            "compute_identity_key",
            "compute_trust_identity_for_manifest",
            "git_head",
            "git_origin",
            "git_repository_root",
            "identity_key_from_record",
            "manifest_command_surfaces",
            "sha256_file",
            "write_json_atomic",
        )

        for name in expected_names:
            with self.subTest(name=name):
                self.assertIs(getattr(engine, name), getattr(trust_store, name))

    def test_compute_trust_identity_includes_manifest_digest_and_sanitized_git_metadata(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "work" / "demo"
            manifest_path = write_manifest(project_root)
            head = init_git_repo(project_root, "https://user:secret@github.com/example/demo.git")
            expected_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

            identity = engine.compute_trust_identity_for_manifest(manifest_path)

        self.assertEqual(identity.project_name, "demo")
        self.assertEqual(identity.project_root, project_root.resolve())
        self.assertEqual(identity.manifest_path, manifest_path.resolve())
        self.assertEqual(identity.manifest_sha256, expected_digest)
        self.assertEqual(identity.git_root, project_root.resolve())
        self.assertEqual(identity.origin, "https://github.com/example/demo.git")
        self.assertEqual(identity.head, head)
        self.assertNotIn("secret", identity.identity_key)

    def test_manifest_command_surfaces_classifies_only_executable_manifest_fields(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            all_surfaces = write_all_command_surfaces_manifest(root / "all")
            no_surfaces = write_manifest(root / "none", name="none", command=None)

            self.assertEqual(
                engine.manifest_command_surfaces(all_surfaces),
                ("test", "run", "build", "demo", "activate"),
            )
            self.assertEqual(engine.manifest_command_surfaces(no_surfaces), ())

    def test_trust_store_writes_allow_record_under_base_state_with_schema_version_one(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            project_root = root / "work" / "demo"
            manifest_path = write_manifest(project_root)
            identity = engine.compute_trust_identity_for_manifest(manifest_path)
            store = engine.ManifestCommandTrustStore(home=home)

            record_path = store.allow(identity, base_version="9.9.9", allowed_at="2026-07-03T12:00:00Z")

            self.assertTrue(record_path.is_file())
            self.assertEqual(record_path.parent, home / ".base.d" / "trust" / "manifest-commands")
            self.assertFalse((project_root / ".base.d").exists())
            payload = json.loads(record_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["allowed_at"], "2026-07-03T12:00:00Z")
        self.assertEqual(payload["allowed_by"], "local-user")
        self.assertEqual(payload["base_version"], "9.9.9")
        self.assertEqual(payload["project"]["name"], "demo")
        self.assertEqual(payload["project"]["root"], str(project_root.resolve()))
        self.assertEqual(payload["project"]["manifest"], str(manifest_path.resolve()))
        self.assertEqual(payload["project"]["manifest_sha256"], identity.manifest_sha256)
        self.assertEqual(payload["allowed_commands"], ["test", "run", "build", "demo", "activate"])

    def test_status_json_reports_blocked_project_and_allow_command(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            manifest_path = write_manifest(workspace / "demo")
            expected_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

            result = invoke(
                engine.app,
                ["status", "demo", "--workspace", str(workspace), "--format", "json"],
                home=home,
                env={"BASE_HOME": str(workspace / "base")},
            )

        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["reason"], "not_allowed")
        self.assertEqual(payload["project"]["name"], "demo")
        self.assertEqual(payload["project"]["manifest_sha256"], expected_digest)
        self.assertEqual(
            payload["allow_command"],
            f"basectl trust allow demo --manifest-sha256 {expected_digest}",
        )

    def test_workspace_status_reports_only_projects_with_executable_manifest_surfaces(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            write_manifest(workspace / "fresh", name="fresh")
            allowed_manifest = write_manifest(workspace / "allowed", name="allowed")
            changed_manifest = write_manifest(workspace / "changed", name="changed")
            write_manifest(workspace / "metadata-only", name="metadata-only", command=None)
            store = engine.ManifestCommandTrustStore(home=home)
            store.allow(
                engine.compute_trust_identity_for_manifest(allowed_manifest),
                base_version="9.9.9",
            )
            store.allow(
                engine.compute_trust_identity_for_manifest(changed_manifest),
                base_version="9.9.9",
            )
            changed_manifest.write_text(
                changed_manifest.read_text(encoding="utf-8").replace("pytest tests/", "pytest -q"),
                encoding="utf-8",
            )

            result = invoke(
                engine.app,
                ["status", "--workspace", str(workspace), "--format", "json"],
                home=home,
                env={"BASE_HOME": str(workspace / "base")},
            )
            text_result = invoke(
                engine.app,
                ["status", "--workspace", str(workspace)],
                home=home,
                env={"BASE_HOME": str(workspace / "base")},
            )

        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual([item["project"]["name"] for item in payload["projects"]], ["allowed", "changed", "fresh"])
        self.assertEqual(
            {item["project"]["name"]: item["status"] for item in payload["projects"]},
            {"allowed": "allowed", "changed": "blocked", "fresh": "blocked"},
        )
        self.assertEqual(
            next(item for item in payload["projects"] if item["project"]["name"] == "changed")["reason"],
            "manifest_changed",
        )
        self.assertNotIn("metadata-only", result.stdout)
        self.assertEqual(text_result.exit_code, 0, text_result.output)
        self.assertIn("allowed\tallowed\tallowed", text_result.stdout)
        self.assertIn("changed\tblocked\tmanifest_changed", text_result.stdout)
        self.assertIn("fresh\tblocked\tnot_allowed", text_result.stdout)
        self.assertNotIn("metadata-only", text_result.stdout)

    def test_status_for_project_without_commands_keeps_json_v1_and_omits_text_guidance(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            write_manifest(workspace / "docs", name="docs", command=None)

            result = invoke(
                engine.app,
                ["status", "docs", "--workspace", str(workspace), "--format", "json"],
                home=home,
                env={"BASE_HOME": str(workspace / "base")},
            )
            text_result = invoke(
                engine.app,
                ["status", "docs", "--workspace", str(workspace)],
                home=home,
                env={"BASE_HOME": str(workspace / "base")},
            )

        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["reason"], "not_allowed")
        self.assertIn("allow_command", payload)
        self.assertEqual(text_result.exit_code, 0, text_result.output)
        self.assertIn("docs\tblocked\tnot_allowed", text_result.stdout)
        self.assertNotIn("trust allow", text_result.stdout)

    def test_workspace_status_adds_context_projects_only_for_implicit_workspace(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "configured-workspace"
            base_home = root / "installed-base"
            active_root = root / "active"
            write_manifest(workspace / "scoped", name="scoped")
            write_manifest(base_home, name="base")
            active_manifest = write_manifest(active_root, name="active")
            config_path = home / ".base.d" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(f"workspace:\n  root: {workspace}\n", encoding="utf-8")

            implicit_result = invoke(
                engine.app,
                ["status", "--format", "json"],
                home=home,
                env={
                    "BASE_HOME": str(base_home),
                    "BASE_PROJECT": "base",
                    "BASE_PROJECT_MANIFEST": str(active_manifest),
                    "BASE_TRUST_ACTIVE_PROJECT": "active",
                    "BASE_TRUST_ACTIVE_PROJECT_MANIFEST": str(active_manifest),
                },
            )
            explicit_result = invoke(
                engine.app,
                ["status", "--workspace", str(workspace), "--format", "json"],
                home=home,
                env={
                    "BASE_HOME": str(base_home),
                    "BASE_PROJECT": "base",
                    "BASE_PROJECT_MANIFEST": str(active_manifest),
                    "BASE_TRUST_ACTIVE_PROJECT": "active",
                    "BASE_TRUST_ACTIVE_PROJECT_MANIFEST": str(active_manifest),
                },
            )

        self.assertEqual(implicit_result.exit_code, 0, implicit_result.output)
        implicit_payload = json.loads(implicit_result.stdout)
        self.assertEqual(
            [item["project"]["name"] for item in implicit_payload["projects"]],
            ["active", "base", "scoped"],
        )
        self.assertEqual(explicit_result.exit_code, 0, explicit_result.output)
        explicit_payload = json.loads(explicit_result.stdout)
        self.assertEqual(
            [item["project"]["name"] for item in explicit_payload["projects"]],
            ["scoped"],
        )

    def test_require_blocks_unapproved_manifest_with_review_guidance(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            manifest_path = write_manifest(workspace / "demo")
            expected_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "BASE_CACHE_DIR": str(home / ".cache" / "base"),
                    "BASE_HOME": str(workspace / "base"),
                },
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    status = engine.main(["require", "demo", "--manifest", str(manifest_path)])

        self.assertEqual(status, 1, stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Manifest-declared commands are not allowed for project 'demo'", stderr.getvalue())
        self.assertIn(f"Manifest SHA-256: {expected_digest}", stderr.getvalue())
        self.assertIn("Review first:", stderr.getvalue())
        self.assertIn("  basectl test demo --dry-run", stderr.getvalue())
        self.assertNotIn("  basectl run demo --list", stderr.getvalue())
        self.assertIn("Allow after review:", stderr.getvalue())
        self.assertIn(f"  basectl trust allow demo --manifest-sha256 {expected_digest}", stderr.getvalue())

    def test_status_guidance_covers_demo_and_manifest_backed_activation(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            manifest_path = write_all_command_surfaces_manifest(workspace / "demo")

            with mock.patch("base_cli.is_terminal", return_value=True):
                result = invoke(
                    engine.app,
                    ["status", "demo", "--workspace", str(workspace)],
                    home=home,
                    env={"BASE_HOME": str(workspace / "base")},
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Manifest command trust is blocked for project 'demo'.", result.stdout)
        self.assertIn("basectl run demo --list", result.stdout)
        self.assertIn("basectl build demo --list", result.stdout)
        self.assertIn("basectl test demo --dry-run", result.stdout)
        self.assertIn("basectl demo demo --dry-run", result.stdout)
        self.assertIn(f"Inspect activate.source entries in {manifest_path.resolve()}", result.stdout)
        self.assertIn("basectl trust allow demo --manifest-sha256", result.stdout)

    def test_changed_manifest_status_shows_recorded_digest_and_reapproval_guidance(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            manifest_path = write_manifest(workspace / "demo")
            identity = engine.compute_trust_identity_for_manifest(manifest_path)
            engine.ManifestCommandTrustStore(home=home).allow(identity, base_version="9.9.9")
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8").replace("pytest tests/", "pytest -q"),
                encoding="utf-8",
            )
            current_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

            with mock.patch("base_cli.is_terminal", return_value=True):
                result = invoke(
                    engine.app,
                    ["status", "demo", "--workspace", str(workspace)],
                    home=home,
                    env={"BASE_HOME": str(workspace / "base")},
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Manifest command trust is blocked for project 'demo': manifest changed.", result.stdout)
        self.assertIn(f"Recorded Manifest SHA-256: {identity.manifest_sha256}", result.stdout)
        self.assertIn(f"Manifest SHA-256: {current_digest}", result.stdout)
        self.assertIn("basectl test demo --dry-run", result.stdout)
        self.assertIn(
            f"basectl trust allow demo --manifest-sha256 {current_digest}",
            result.stdout,
        )

    def test_require_allows_matching_trust_record_for_manifest_path(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            manifest_path = write_manifest(workspace / "demo")
            identity = engine.compute_trust_identity_for_manifest(manifest_path)
            engine.ManifestCommandTrustStore(home=home).allow(identity, base_version="9.9.9")

            result = invoke(
                engine.app,
                ["require", "demo", "--manifest", str(manifest_path)],
                home=home,
                env={"BASE_HOME": str(workspace / "base")},
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_allow_rejects_manifest_sha256_mismatch_without_writing_record(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            write_manifest(workspace / "demo")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "BASE_CACHE_DIR": str(home / ".cache" / "base"),
                    "BASE_HOME": str(workspace / "base"),
                },
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    status = engine.main(
                        [
                            "allow",
                            "demo",
                            "--workspace",
                            str(workspace),
                            "--manifest-sha256",
                            "0" * 64,
                        ]
                    )

            trust_root = home / ".base.d" / "trust" / "manifest-commands"

        self.assertEqual(status, 2, stderr.getvalue())
        self.assertIn("does not match current manifest SHA-256", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(trust_root.exists())

    def test_allow_and_revoke_update_status(self) -> None:
        from base_trust import engine

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "work"
            manifest_path = write_manifest(workspace / "demo")
            expected_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            env = {"BASE_HOME": str(workspace / "base")}

            allow_result = invoke(
                engine.app,
                ["allow", "demo", "--workspace", str(workspace), "--manifest-sha256", expected_digest],
                home=home,
                env=env,
            )
            allowed_status = invoke(
                engine.app,
                ["status", "demo", "--workspace", str(workspace), "--format", "json"],
                home=home,
                env=env,
            )
            revoke_result = invoke(engine.app, ["revoke", "demo", "--workspace", str(workspace)], home=home, env=env)
            revoked_status = invoke(
                engine.app,
                ["status", "demo", "--workspace", str(workspace), "--format", "json"],
                home=home,
                env=env,
            )

        self.assertEqual(allow_result.exit_code, 0, allow_result.output)
        self.assertIn("Allowed manifest commands for project 'demo'.", allow_result.output)
        self.assertEqual(json.loads(allowed_status.stdout)["status"], "allowed")
        self.assertEqual(revoke_result.exit_code, 0, revoke_result.output)
        self.assertIn("Revoked manifest command trust for project 'demo'.", revoke_result.output)
        self.assertEqual(json.loads(revoked_status.stdout)["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
