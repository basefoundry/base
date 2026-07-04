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

from base_cli.testing import invoke


def write_manifest(project_root: Path, name: str = "demo", command: str = "pytest tests/") -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    manifest_path = project_root / "base_manifest.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "project:",
                f"  name: {name}",
                "test:",
                f"  command: {command}",
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
        self.assertIn("  basectl run demo --list", stderr.getvalue())
        self.assertIn("Allow after review:", stderr.getvalue())
        self.assertIn(f"  basectl trust allow demo --manifest-sha256 {expected_digest}", stderr.getvalue())

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
