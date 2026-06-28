from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import delegates, engine
from base_setup.errors import ArtifactError
from base_setup.manifest import BaseManifest
from base_setup.tests.helpers import fake_context


def make_manifest(project_root: Path) -> BaseManifest:
    (project_root / ".mise.toml").write_text("[tools]\ngo = \"1.22\"\n", encoding="utf-8")
    return BaseManifest(
        path=project_root / "base_manifest.yaml",
        project_name="demo",
        brewfile=None,
        mise=".mise.toml",
        artifacts=(),
    )


def write_fake_mise(bin_dir: Path, log_path: Path, trust_output: str, missing_output: str) -> None:
    mise = bin_dir / "mise"
    mise.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                f"printf '%s\\n' \"$PWD $*\" >> {log_path}",
                "case \"$*\" in",
                "  'trust --show')",
                f"    printf '%s\\n' {trust_output!r}",
                "    ;;",
                "  'ls --missing --json')",
                f"    printf '%s\\n' {missing_output!r}",
                "    ;;",
                "  *)",
                "    printf 'unexpected mise args: %s\\n' \"$*\" >&2",
                "    exit 99",
                "    ;;",
                "esac",
                "",
            ]
        ),
        encoding="utf-8",
    )
    mise.chmod(0o755)


class MiseTests(unittest.TestCase):

    def test_mise_dry_run_invokes_mise_install_in_project_root(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / ".mise.toml").write_text("[tools]\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            delegates.reconcile_mise(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(f"[DRY-RUN] Would run in '{project_root.resolve()}': mise install", info_messages)



    def test_mise_invokes_install_in_project_root(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            (project_root / ".mise.toml").write_text("[tools]\n", encoding="utf-8")
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            with mock.patch("base_setup.process.command_exists", return_value=True), mock.patch(
                "base_setup.process.run_command"
            ) as run_command:
                delegates.reconcile_mise(ctx, manifest, dry_run=False)

        run_command.assert_called_once_with(ctx, ["mise", "install"], cwd=project_root.resolve())


    def test_mise_check_passes_when_trusted_and_no_tools_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "demo"
            project_root.mkdir()
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            log_path = tmp / "mise.log"
            manifest = make_manifest(project_root)
            write_fake_mise(bin_dir, log_path, f"{project_root.resolve()}: trusted", "{}")

            with mock.patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ['PATH']}"}):
                check = delegates.check_mise(manifest)
            log_lines = log_path.read_text(encoding="utf-8").splitlines()

        self.assertTrue(check.ok)
        self.assertEqual(check.status, "")
        self.assertIn("mise-managed tools are installed", check.message)
        self.assertEqual(check.fix, "")
        self.assertEqual(
            log_lines,
            [
                f"{project_root.resolve()} trust --show",
                f"{project_root.resolve()} ls --missing --json",
            ],
        )


    def test_mise_check_reports_untrusted_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "demo"
            project_root.mkdir()
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            log_path = tmp / "mise.log"
            manifest = make_manifest(project_root)
            write_fake_mise(bin_dir, log_path, f"{project_root.resolve()}: untrusted", "{}")

            with mock.patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ['PATH']}"}):
                check = delegates.check_mise(manifest)
            log_lines = log_path.read_text(encoding="utf-8").splitlines()

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "")
        self.assertIn("is not trusted by mise", check.message)
        self.assertEqual(check.fix, f"mise trust {project_root.resolve() / '.mise.toml'}")
        self.assertEqual(log_lines, [f"{project_root.resolve()} trust --show"])

    def test_mise_check_warns_when_trust_probe_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = make_manifest(project_root)

            with (
                mock.patch("base_setup.process.command_exists", return_value=True),
                mock.patch(
                    "base_setup.process.run_capture",
                    side_effect=subprocess.TimeoutExpired(
                        ["mise", "trust", "--show"],
                        delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
                    ),
                ) as run_capture,
            ):
                check = delegates.check_mise(manifest)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertEqual(check.finding_id, "BASE-P022")
        self.assertIn("timed out", check.message)
        self.assertEqual(check.fix, f"Retry 'mise trust --show' in '{project_root.resolve()}'.")
        run_capture.assert_called_once_with(
            ["mise", "trust", "--show"],
            cwd=project_root.resolve(),
            timeout_seconds=delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )


    def test_mise_check_reports_missing_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "demo"
            project_root.mkdir()
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            log_path = tmp / "mise.log"
            manifest = make_manifest(project_root)
            write_fake_mise(bin_dir, log_path, f"{project_root.resolve()}: trusted", '{"go":[{"version":"1.22"}]}')

            with mock.patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ['PATH']}"}):
                check = delegates.check_mise(manifest)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "")
        self.assertIn("mise-managed tools are missing", check.message)
        self.assertIn("go", check.message)
        self.assertEqual(check.fix, "basectl setup demo")


    def test_mise_check_warns_when_missing_tool_output_is_not_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "demo"
            project_root.mkdir()
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            log_path = tmp / "mise.log"
            manifest = make_manifest(project_root)
            write_fake_mise(bin_dir, log_path, f"{project_root.resolve()}: trusted", "not json")

            with mock.patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ['PATH']}"}):
                check = delegates.check_mise(manifest)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertIn("could not be parsed", check.message)
        self.assertEqual(check.fix, f"Run 'mise ls --missing --json' in '{project_root.resolve()}' for details.")

    def test_mise_check_warns_when_missing_tools_probe_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = make_manifest(project_root)
            trust_check = subprocess.CompletedProcess(
                ["mise", "trust", "--show"],
                0,
                stdout=f"{project_root.resolve()}: trusted",
                stderr="",
            )

            with (
                mock.patch("base_setup.process.command_exists", return_value=True),
                mock.patch(
                    "base_setup.process.run_capture",
                    side_effect=[
                        trust_check,
                        subprocess.TimeoutExpired(
                            ["mise", "ls", "--missing", "--json"],
                            delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
                        ),
                    ],
                ) as run_capture,
            ):
                check = delegates.check_mise(manifest)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertEqual(check.finding_id, "BASE-P022")
        self.assertIn("timed out", check.message)
        self.assertEqual(check.fix, f"Retry 'mise ls --missing --json' in '{project_root.resolve()}'.")
        self.assertEqual(
            run_capture.call_args_list[0].kwargs["timeout_seconds"],
            delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )
        self.assertEqual(
            run_capture.call_args_list[1].kwargs["timeout_seconds"],
            delegates.process.DIAGNOSTIC_TIMEOUT_SECONDS,
        )



    def test_mise_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise=".mise.toml",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "mise config '.mise.toml' does not exist"):
                delegates.resolve_mise_path(manifest)



    def test_mise_must_stay_inside_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = BaseManifest(
                path=project_root / "base_manifest.yaml",
                project_name="demo",
                brewfile=None,
                mise="../.mise.toml",
                artifacts=(),
            )

            with self.assertRaisesRegex(ArtifactError, "mise must stay inside the project root"):
                delegates.resolve_mise_path(manifest)



    def test_manifest_checks_include_mise_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "demo"
            project_root.mkdir()
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            log_path = tmp / "mise.log"
            default_manifest = BaseManifest(
                path=tmp / "default.yaml",
                project_name="base",
                brewfile=None,
                artifacts=(),
            )
            manifest = make_manifest(project_root)
            write_fake_mise(bin_dir, log_path, f"{project_root.resolve()}: trusted", "{}")

            with mock.patch.dict(os.environ, {"PATH": f"{bin_dir}:{os.environ['PATH']}"}):
                checks = engine.manifest_checks(default_manifest, manifest)

        self.assertIn("mise", [check.name for check in checks])
        mise_check = next(check for check in checks if check.name == "mise")
        self.assertTrue(mise_check.ok)
        self.assertEqual(mise_check.status, "")
        self.assertIn("mise-managed tools are installed", mise_check.message)
        self.assertEqual(mise_check.fix, "")
