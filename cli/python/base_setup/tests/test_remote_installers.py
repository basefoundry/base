from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import remote_installers
from base_setup.errors import ArtifactError
from base_setup.tests.helpers import fake_context


class RemoteInstallerTests(unittest.TestCase):
    def test_registry_contains_every_python_owned_remote_shell_installer(self) -> None:
        self.assertEqual(
            {spec.name: spec.default_url for spec in remote_installers.PYTHON_REMOTE_INSTALLERS},
            {
                "codex": "https://chatgpt.com/codex/install.sh",
                "claude": "https://claude.ai/install.sh",
                "uv": "https://astral.sh/uv/install.sh",
                "mise": "https://mise.run",
            },
        )

    def test_rejects_unregistered_installer(self) -> None:
        spec = remote_installers.RemoteInstallerSpec(
            name="unknown",
            display_name="Unknown",
            default_url="https://example.invalid/install.sh",
            interpreter="sh",
            trigger="test",
            consent="test",
        )

        with self.assertRaisesRegex(ArtifactError, "is not registered"):
            remote_installers.resolve_remote_installer_source(spec, environ={})

    def test_default_source_is_explicitly_unverified(self) -> None:
        source = remote_installers.resolve_remote_installer_source(
            remote_installers.UV_REMOTE_INSTALLER,
            environ={},
        )

        self.assertEqual(source.location, remote_installers.UV_REMOTE_INSTALLER.default_url)
        self.assertIsNone(source.expected_sha256)
        self.assertFalse(source.managed)

    def test_override_url_and_sha256_must_be_paired(self) -> None:
        spec = remote_installers.UV_REMOTE_INSTALLER
        with self.assertRaisesRegex(ArtifactError, "must be set together"):
            remote_installers.resolve_remote_installer_source(
                spec,
                environ={spec.url_env: "/tmp/uv-install.sh"},
            )
        with self.assertRaisesRegex(ArtifactError, "must be set together"):
            remote_installers.resolve_remote_installer_source(
                spec,
                environ={spec.sha256_env: "0" * 64},
            )

    def test_override_rejects_malformed_sha256_and_unsafe_scheme(self) -> None:
        spec = remote_installers.MISE_REMOTE_INSTALLER
        with self.assertRaisesRegex(ArtifactError, "exactly 64 hexadecimal"):
            remote_installers.resolve_remote_installer_source(
                spec,
                environ={spec.url_env: "/tmp/mise-install.sh", spec.sha256_env: "not-a-digest"},
            )
        with self.assertRaisesRegex(ArtifactError, "local path, file:// URL, or HTTPS URL"):
            remote_installers.resolve_remote_installer_source(
                spec,
                environ={spec.url_env: "http://example.test/install.sh", spec.sha256_env: "0" * 64},
            )

    def test_dry_run_discloses_mutable_default_without_fetching(self) -> None:
        ctx = fake_context()
        with mock.patch("base_setup.remote_installers.process.run_command") as run_command:
            remote_installers.run_remote_installer(
                ctx,
                remote_installers.UV_REMOTE_INSTALLER,
                dry_run=True,
                environ={},
            )

        run_command.assert_not_called()
        messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertTrue(any("official mutable installer" in message for message in messages))
        self.assertTrue(any("without checksum verification" in message for message in messages))
        self.assertTrue(any("fetch" in message and "same bytes" in message for message in messages))

    def test_matching_local_override_executes_verified_bytes_once_and_cleans_up(self) -> None:
        ctx = fake_context()
        payload = b"#!/bin/sh\nprintf 'managed uv installer\\n'\n"
        expected_sha256 = hashlib.sha256(payload).hexdigest()
        executed_payloads: list[bytes] = []
        executed_paths: list[Path] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "uv-install.sh"
            source.write_bytes(payload)

            def inspect_execution(_ctx: object, command: list[str]) -> None:
                self.assertEqual(command[0], "sh")
                installer_path = Path(command[1])
                executed_paths.append(installer_path)
                executed_payloads.append(installer_path.read_bytes())

            with mock.patch(
                "base_setup.remote_installers.process.run_command",
                side_effect=inspect_execution,
            ) as run_command:
                remote_installers.run_remote_installer(
                    ctx,
                    remote_installers.UV_REMOTE_INSTALLER,
                    dry_run=False,
                    environ={
                        "BASE_SETUP_UV_INSTALLER_URL": str(source),
                        "BASE_SETUP_UV_INSTALLER_SHA256": expected_sha256,
                    },
                )

        run_command.assert_called_once()
        self.assertEqual(executed_payloads, [payload])
        self.assertEqual(len(executed_paths), 1)
        self.assertFalse(executed_paths[0].exists())

    def test_file_url_override_is_supported(self) -> None:
        ctx = fake_context()
        payload = b"#!/bin/sh\nexit 0\n"
        expected_sha256 = hashlib.sha256(payload).hexdigest()

        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "mise installer.sh"
            source.write_bytes(payload)
            with mock.patch("base_setup.remote_installers.process.run_command") as run_command:
                remote_installers.run_remote_installer(
                    ctx,
                    remote_installers.MISE_REMOTE_INSTALLER,
                    dry_run=False,
                    environ={
                        "BASE_SETUP_MISE_INSTALLER_URL": source.as_uri(),
                        "BASE_SETUP_MISE_INSTALLER_SHA256": expected_sha256,
                    },
                )

        run_command.assert_called_once()
        self.assertEqual(run_command.call_args.args[1][0], "sh")

    def test_checksum_mismatch_fails_before_execution(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "uv-install.sh"
            source.write_text("#!/bin/sh\n", encoding="utf-8")
            with mock.patch("base_setup.remote_installers.process.run_command") as run_command:
                with self.assertRaisesRegex(ArtifactError, "SHA-256 mismatch.*not executed"):
                    remote_installers.run_remote_installer(
                        ctx,
                        remote_installers.UV_REMOTE_INSTALLER,
                        dry_run=False,
                        environ={
                            "BASE_SETUP_UV_INSTALLER_URL": str(source),
                            "BASE_SETUP_UV_INSTALLER_SHA256": "0" * 64,
                        },
                    )

        run_command.assert_not_called()

    def test_https_override_uses_argv_fetch_and_executes_the_fetched_file(self) -> None:
        ctx = fake_context()
        payload = b"#!/bin/sh\nexit 0\n"
        expected_sha256 = hashlib.sha256(payload).hexdigest()
        commands: list[list[str]] = []

        def fake_command(_ctx: object, command: list[str]) -> None:
            commands.append(command)
            if command[0] == "curl":
                Path(command[command.index("-o") + 1]).write_bytes(payload)
                return
            self.assertEqual(Path(command[1]).read_bytes(), payload)

        with mock.patch("base_setup.remote_installers.process.run_command", side_effect=fake_command):
            remote_installers.run_remote_installer(
                ctx,
                remote_installers.MISE_REMOTE_INSTALLER,
                dry_run=False,
                environ={
                    "BASE_SETUP_MISE_INSTALLER_URL": "https://mirror.example.test/mise-install.sh",
                    "BASE_SETUP_MISE_INSTALLER_SHA256": expected_sha256,
                },
            )

        self.assertEqual(commands[0][0:5], ["curl", "--proto", "=https", "--tlsv1.2", "-fsSL"])
        self.assertEqual(commands[0][-1], "https://mirror.example.test/mise-install.sh")
        self.assertEqual(commands[1][0], "sh")
        self.assertNotIn("sh -c", " ".join(commands[0]))


if __name__ == "__main__":
    unittest.main()
