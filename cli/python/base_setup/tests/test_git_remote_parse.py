from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_setup import git_remote, git_remote_parse


class GitRemoteParseModuleTests(unittest.TestCase):
    def test_git_remote_keeps_parser_compatibility_exports(self) -> None:
        expected_names = (
            "GITHUB_HOST",
            "RemoteInfo",
            "github_repository",
            "malformed_remote",
            "origin_remote_message",
            "parse_local_remote",
            "parse_origin_remote",
            "parse_scp_remote",
            "parse_url_remote",
            "remote_details",
        )

        for name in expected_names:
            with self.subTest(name=name):
                self.assertIs(getattr(git_remote, name), getattr(git_remote_parse, name))

    def test_parse_origin_remote_handles_github_https_without_credentials(self) -> None:
        remote_info = git_remote_parse.parse_origin_remote(
            "https://token:secret@github.com/basefoundry/base.git",
            Path.cwd(),
        )

        self.assertTrue(remote_info.valid)
        self.assertEqual(remote_info.provider, "github")
        self.assertEqual(remote_info.transport, "https")
        self.assertEqual(remote_info.repository, "basefoundry/base")
        self.assertEqual(remote_info.sanitized_url, "https://github.com/basefoundry/base.git")

    def test_parse_origin_remote_resolves_local_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            project_root.mkdir()
            remote_path = root / "remote.git"
            remote_path.mkdir()

            remote_info = git_remote_parse.parse_origin_remote("../remote.git", project_root)

        self.assertTrue(remote_info.valid)
        self.assertEqual(remote_info.provider, "local")
        self.assertEqual(remote_info.transport, "local_path")
        self.assertEqual(remote_info.local_path, remote_path.resolve())
        self.assertTrue(remote_info.reachable)
