from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from base_setup import delegates, engine, remote_installers
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


def trusted_mise_check(project_root: Path, mise_bin: Path = Path("mise")) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        [str(mise_bin), "trust", "--show"],
        0,
        stdout=f"{project_root.resolve()}: trusted",
        stderr="",
    )


class MiseTests(unittest.TestCase):
    def test_delegates_reexports_mise_helpers(self) -> None:
        from base_setup import mise_delegate

        expected_names = (
            "check_mise",
            "check_mise_missing_tools",
            "check_mise_trust",
            "command_text",
            "ensure_mise_available",
            "mise_config_untrusted",
            "mise_details",
            "mise_executable",
            "missing_tool_names",
            "reconcile_mise",
            "require_mise_trusted_for_setup",
            "resolve_mise_path",
        )

        for name in expected_names:
            with self.subTest(name=name):
                self.assertIs(getattr(delegates, name), getattr(mise_delegate, name))

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

            with mock.patch("base_setup.mise_delegate.mise_executable", return_value=Path("mise")):
                delegates.reconcile_mise(ctx, manifest, dry_run=True)

        info_messages = [call.args[0] % call.args[1:] for call in ctx.log.info.call_args_list]
        self.assertIn(f"[DRY-RUN] Would run in '{project_root.resolve()}': mise install", info_messages)



    def test_mise_dry_run_plans_linux_debian_bootstrap_when_missing(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = make_manifest(project_root)

            with (
                mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian"}),
                mock.patch("base_setup.mise_delegate.mise_executable", return_value=None),
                mock.patch("base_setup.mise_delegate.remote_installers.run_remote_installer") as run_installer,
            ):
                delegates.reconcile_mise(ctx, manifest, dry_run=True)

        run_installer.assert_called_once_with(ctx, remote_installers.MISE_REMOTE_INSTALLER, dry_run=True)
        ctx.log.info.assert_any_call("[DRY-RUN] Would run in '%s': %s", project_root.resolve(), "mise install")

    def test_mise_bootstraps_on_linux_debian_with_yes(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = make_manifest(project_root)
            mise_path = Path(tmpdir) / ".local" / "bin" / "mise"

            with (
                mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian", "BASE_SETUP_YES": "true"}),
                mock.patch("base_setup.mise_delegate.mise_executable", side_effect=[None, mise_path]),
                mock.patch("base_setup.mise_delegate.remote_installers.run_remote_installer") as run_installer,
                mock.patch("base_setup.delegates.process.run_capture", return_value=trusted_mise_check(project_root)),
                mock.patch("base_setup.delegates.process.run_command") as run_command,
            ):
                delegates.reconcile_mise(ctx, manifest, dry_run=False)

        run_installer.assert_called_once_with(ctx, remote_installers.MISE_REMOTE_INSTALLER, dry_run=False)
        run_command.assert_called_once_with(ctx, [str(mise_path), "install"], cwd=project_root.resolve())

    def test_mise_requires_yes_before_linux_debian_bootstrap(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = make_manifest(project_root)

            with (
                mock.patch.dict(os.environ, {"BASE_PLATFORM": "linux-debian"}, clear=False),
                mock.patch("base_setup.mise_delegate.mise_executable", return_value=None),
            ):
                with self.assertRaisesRegex(RuntimeError, "Run 'basectl setup demo --dry-run'.*'--yes'"):
                    delegates.reconcile_mise(ctx, manifest, dry_run=False)

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

            with mock.patch("base_setup.mise_delegate.mise_executable", return_value=Path("mise")), mock.patch(
                "base_setup.process.run_command"
            ) as run_command, mock.patch(
                "base_setup.delegates.process.run_capture",
                return_value=trusted_mise_check(project_root),
            ):
                delegates.reconcile_mise(ctx, manifest, dry_run=False)

        run_command.assert_called_once_with(ctx, ["mise", "install"], cwd=project_root.resolve())

    def test_mise_setup_refuses_untrusted_project_config_before_install(self) -> None:
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = make_manifest(project_root)
            mise_bin = Path("mise")
            trust_check = subprocess.CompletedProcess(
                [str(mise_bin), "trust", "--show"],
                0,
                stdout=f"{project_root.resolve()}: untrusted",
                stderr="",
            )

            with (
                mock.patch("base_setup.mise_delegate.mise_executable", return_value=mise_bin),
                mock.patch("base_setup.delegates.process.run_capture", return_value=trust_check),
                mock.patch("base_setup.delegates.process.run_command") as run_command,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    f"mise config '{project_root.resolve() / '.mise.toml'}' is not trusted by mise",
                ):
                    delegates.reconcile_mise(ctx, manifest, dry_run=False)

        run_command.assert_not_called()


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

    def test_mise_check_warns_when_tool_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            manifest = make_manifest(project_root)

            with mock.patch("base_setup.mise_delegate.mise_executable", return_value=None):
                check = delegates.check_mise(manifest)

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertEqual(check.finding_id, "BASE-P021")
        self.assertIn("mise is not available", check.message)
        self.assertIn("basectl setup demo --dry-run", check.fix)
        self.assertIn("--yes", check.fix)


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
                mock.patch("base_setup.mise_delegate.mise_executable", return_value=Path("mise")),
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
                mock.patch("base_setup.mise_delegate.mise_executable", return_value=Path("mise")),
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
