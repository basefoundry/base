from __future__ import annotations

import io
import os
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_export_context import engine


def write_context_file(project_root: Path, relative_path: str, content: str) -> None:
    path = project_root / ".ai-context" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def invoke_engine(args: list[str], project_root: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    env = {
        "BASE_HOME": str(project_root),
        "HOME": str(project_root / "home"),
    }
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()


class ExportContextTests(unittest.TestCase):
    def test_main_reports_unknown_option_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()

            status, _stdout, stderr = invoke_engine(["--bad-option"], project_root)

        self.assertEqual(status, 2)
        self.assertIn("No such option", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_markdown_print_uses_index_order_then_remaining_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            write_context_file(
                project_root,
                "INDEX.md",
                "# Index\n\n1. `B.md`\n2. [A](A.md)\n3. `../README.md`\n",
            )
            write_context_file(project_root, "A.md", "Alpha\n")
            write_context_file(project_root, "B.md", "Bravo\n")
            write_context_file(project_root, "C.md", "Charlie")
            (project_root / "README.md").write_text("not context\n", encoding="utf-8")

            status, stdout, stderr = invoke_engine(
                [
                    "--project-name",
                    "demo",
                    "--project-root",
                    str(project_root),
                    "--print",
                ],
                project_root,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("# AI Context Export: demo\n", stdout)
        headings = [line for line in stdout.splitlines() if line.startswith("## `")]
        self.assertEqual(
            headings,
            [
                "## `.ai-context/B.md`",
                "## `.ai-context/A.md`",
                "## `.ai-context/C.md`",
                "## `.ai-context/INDEX.md`",
            ],
        )
        self.assertIn("Bravo\n", stdout)
        self.assertIn("Charlie\n", stdout)
        self.assertNotIn("not context", stdout)

    def test_list_files_prints_export_order_without_writing_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            write_context_file(project_root, "INDEX.md", "Read `PROJECT.md` first.\n")
            write_context_file(project_root, "PROJECT.md", "Project\n")
            write_context_file(project_root, "STATUS.md", "Status\n")

            status, stdout, stderr = invoke_engine(
                [
                    "--project-name",
                    "demo",
                    "--project-root",
                    str(project_root),
                    "--list-files",
                ],
                project_root,
            )

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            ".ai-context/PROJECT.md\n.ai-context/INDEX.md\n.ai-context/STATUS.md\n",
        )

    def test_output_writes_markdown_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            output_path = Path(tmpdir) / "bundle.md"
            write_context_file(project_root, "PROJECT.md", "Project\n")

            status, stdout, stderr = invoke_engine(
                [
                    "--project-name",
                    "demo",
                    "--project-root",
                    str(project_root),
                    "--output",
                    str(output_path),
                ],
                project_root,
            )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(stdout, f"Wrote Markdown AI context export for project 'demo' to {output_path}\n")
            self.assertIn("## `.ai-context/PROJECT.md`\n", output_path.read_text(encoding="utf-8"))

    def test_missing_context_directory_reports_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()

            status, stdout, stderr = invoke_engine(
                ["--project-name", "demo", "--project-root", str(project_root), "--print"],
                project_root,
            )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Project 'demo' does not have an .ai-context directory", stderr)
        self.assertIn("Add .ai-context/README.md", stderr)

    def test_zip_export_contains_context_files_only_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            project_root.mkdir()
            first_zip = Path(tmpdir) / "first.zip"
            second_zip = Path(tmpdir) / "second.zip"
            write_context_file(project_root, "INDEX.md", "Read `PROJECT.md` first.\n")
            write_context_file(project_root, "PROJECT.md", "Project\n")
            write_context_file(project_root, "notes/raw.txt", "Raw context\n")
            (project_root / "README.md").write_text("not context\n", encoding="utf-8")

            first_status, first_stdout, first_stderr = invoke_engine(
                [
                    "--project-name",
                    "demo",
                    "--project-root",
                    str(project_root),
                    "--format",
                    "zip",
                    "--output",
                    str(first_zip),
                ],
                project_root,
            )
            second_status, _, _ = invoke_engine(
                [
                    "--project-name",
                    "demo",
                    "--project-root",
                    str(project_root),
                    "--format",
                    "zip",
                    "--output",
                    str(second_zip),
                ],
                project_root,
            )

            self.assertEqual(first_status, 0)
            self.assertEqual(second_status, 0)
            self.assertEqual(first_stderr, "")
            self.assertEqual(first_stdout, f"Wrote Zip AI context export for project 'demo' to {first_zip}\n")
            self.assertEqual(first_zip.read_bytes(), second_zip.read_bytes())
            with zipfile.ZipFile(first_zip) as archive:
                self.assertEqual(
                    archive.namelist(),
                    ["PROJECT.md", "INDEX.md", "notes/raw.txt"],
                )
                for info in archive.infolist():
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))

    def test_zip_output_directory_uses_default_bundle_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            output_dir = Path(tmpdir) / "exports"
            project_root.mkdir()
            output_dir.mkdir()
            expected_zip = output_dir / "demo-ai-context.zip"
            write_context_file(project_root, "PROJECT.md", "Project\n")

            status, stdout, stderr = invoke_engine(
                [
                    "--project-name",
                    "demo",
                    "--project-root",
                    str(project_root),
                    "--format",
                    "zip",
                    "--output",
                    str(output_dir),
                ],
                project_root,
            )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(stdout, f"Wrote Zip AI context export for project 'demo' to {expected_zip}\n")
            self.assertTrue(expected_zip.is_file())
            with zipfile.ZipFile(expected_zip) as archive:
                self.assertEqual(archive.namelist(), ["PROJECT.md"])

    def test_zip_output_invalid_destination_reports_error_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "demo"
            parent_file = Path(tmpdir) / "not-a-directory"
            project_root.mkdir()
            parent_file.write_text("not a directory\n", encoding="utf-8")
            output_path = parent_file / "bundle.zip"
            write_context_file(project_root, "PROJECT.md", "Project\n")

            status, stdout, stderr = invoke_engine(
                [
                    "--project-name",
                    "demo",
                    "--project-root",
                    str(project_root),
                    "--format",
                    "zip",
                    "--output",
                    str(output_path),
                ],
                project_root,
            )

            self.assertEqual(status, 1)
            self.assertEqual(stdout, "")
            self.assertIn("Unable to write Zip AI context export", stderr)
            self.assertIn(str(output_path), stderr)
            self.assertNotIn("Traceback", stderr)


if __name__ == "__main__":
    unittest.main()
