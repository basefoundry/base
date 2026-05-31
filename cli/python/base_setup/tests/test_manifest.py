from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_setup.manifest import ManifestError, read_manifest

class ManifestParsingTests(unittest.TestCase):

    def test_reads_basic_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts:",
                        "  - type: tool",
                        "    name: terraform",
                        "    version: \"1.8.5\"",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.schema_version, 1)
        self.assertEqual(manifest.project_name, "demo")
        self.assertIsNone(manifest.brewfile)
        self.assertEqual(manifest.artifacts[0].artifact_type, "tool")
        self.assertEqual(manifest.artifacts[0].name, "terraform")
        self.assertEqual(manifest.artifacts[0].version, "1.8.5")
        self.assertFalse(manifest.artifacts[0].bootstrap)
        self.assertEqual(manifest.activate.source, ())



    def test_reads_manifest_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "",
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.schema_version, 1)



    def test_rejects_non_integer_manifest_schema_version(self) -> None:
        for schema_version in ("true", "1.5", "v1"):
            with self.subTest(schema_version=schema_version):
                with tempfile.TemporaryDirectory() as tmpdir:
                    manifest_path = Path(tmpdir) / "base_manifest.yaml"
                    manifest_path.write_text(
                        "\n".join(
                            [
                                f"schema_version: {schema_version}",
                                "",
                                "project:",
                                "  name: demo",
                                "",
                                "artifacts: []",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    with self.assertRaisesRegex(ManifestError, "schema_version must be an integer"):
                        read_manifest(manifest_path)



    def test_rejects_manifest_schema_version_below_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "schema_version: 0",
                        "",
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "schema_version must be greater than or equal to 1"):
                read_manifest(manifest_path)



    def test_rejects_newer_manifest_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "schema_version: 2",
                        "",
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "Upgrade Base to read this manifest"):
                read_manifest(manifest_path)



    def test_reads_manifest_required_environment_variables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "health:",
                        "  required_env:",
                        "    - DATABASE_URL",
                        "    - REDIS_URL",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.health.required_env, ("DATABASE_URL", "REDIS_URL"))



    def test_reads_manifest_activation_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "activate:",
                        "  source:",
                        "    - .base/activate.sh",
                        "    - scripts/local-env.sh",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.activate.source, (".base/activate.sh", "scripts/local-env.sh"))



    def test_rejects_invalid_manifest_activation_sources(self) -> None:
        invalid_values = {
            "scalar_activate": "activate: .base/activate.sh",
            "unknown_key": "activate:\n  run:\n    - .base/activate.sh",
            "scalar_source": "activate:\n  source: .base/activate.sh",
            "empty": "activate:\n  source:\n    - ''",
            "non_string": "activate:\n  source:\n    - 7",
            "duplicate": "activate:\n  source:\n    - .base/activate.sh\n    - .base/activate.sh",
            "newline": "activate:\n  source:\n    - \"scripts/env\\n.sh\"",
        }
        for name, activate_yaml in invalid_values.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    manifest_path = Path(tmpdir) / "base_manifest.yaml"
                    manifest_path.write_text(
                        "\n".join(
                            [
                                "project:",
                                "  name: demo",
                                activate_yaml,
                                "artifacts: []",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    with self.assertRaises(ManifestError):
                        read_manifest(manifest_path)



    def test_rejects_invalid_manifest_required_environment_variables(self) -> None:
        invalid_values = {
            "scalar": "health:\n  required_env: DATABASE_URL",
            "empty": "health:\n  required_env:\n    - ''",
            "non_string": "health:\n  required_env:\n    - 7",
            "invalid_name": "health:\n  required_env:\n    - DATABASE-URL",
            "duplicate": "health:\n  required_env:\n    - DATABASE_URL\n    - DATABASE_URL",
        }
        for name, health_yaml in invalid_values.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    manifest_path = Path(tmpdir) / "base_manifest.yaml"
                    manifest_path.write_text(
                        "\n".join(
                            [
                                "project:",
                                "  name: demo",
                                health_yaml,
                                "artifacts: []",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    with self.assertRaises(ManifestError):
                        read_manifest(manifest_path)



    def test_reads_manifest_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "commands:",
                        "  dev: uvicorn app:app --reload",
                        "  lint: ruff check .",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(
            manifest.commands,
            {
                "dev": "uvicorn app:app --reload",
                "lint": "ruff check .",
            },
        )



    def test_rejects_invalid_manifest_commands(self) -> None:
        invalid_values = {
            "scalar": "commands: pytest",
            "empty_name": "commands:\n  '': pytest",
            "invalid_name": "commands:\n  'bad command': pytest",
            "reserved_test": "commands:\n  test: pytest",
            "empty_command": "commands:\n  lint: ''",
            "non_string_command": "commands:\n  lint: 7",
        }
        for name, commands_yaml in invalid_values.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    manifest_path = Path(tmpdir) / "base_manifest.yaml"
                    manifest_path.write_text(
                        "\n".join(
                            [
                                "project:",
                                "  name: demo",
                                commands_yaml,
                                "artifacts: []",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    with self.assertRaises(ManifestError):
                        read_manifest(manifest_path)



    def test_reads_manifest_brewfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "brewfile: Brewfile",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.brewfile, "Brewfile")



    def test_reads_manifest_mise_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "mise: .mise.toml",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.mise, ".mise.toml")



    def test_reads_manifest_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  command: pytest tests/",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.test)
        self.assertEqual(manifest.test.command, "pytest tests/")
        self.assertIsNone(manifest.test.mise)



    def test_reads_manifest_test_mise_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  mise: test",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.test)
        self.assertIsNone(manifest.test.command)
        self.assertEqual(manifest.test.mise, "test")



    def test_rejects_invalid_manifest_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  command: \"\"",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "test.command must be a non-empty string"):
                read_manifest(manifest_path)



    def test_rejects_ambiguous_manifest_test_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  command: pytest",
                        "  mise: test",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "test must declare only one of command or mise"):
                read_manifest(manifest_path)



    def test_empty_artifact_list_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.project_name, "demo")
        self.assertEqual(manifest.artifacts, ())



class ManifestIdeParsingTests(unittest.TestCase):

    def test_reads_ide_manifest_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    install: true",
                        "    extensions:",
                        "      - ms-python.python",
                        "      - github.copilot",
                        "    settings:",
                        "      editor.formatOnSave: true",
                        "      editor.rulers: [100]",
                        "      python.defaultInterpreterPath: auto",
                        "  cursor:",
                        "    extensions:",
                        "      - ms-python.python",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(set(manifest.ide), {"vscode", "cursor"})
        self.assertTrue(manifest.ide["vscode"].install)
        self.assertEqual(
            manifest.ide["vscode"].extensions,
            ("ms-python.python", "github.copilot"),
        )
        self.assertEqual(
            manifest.ide["vscode"].settings,
            {
                "editor.formatOnSave": True,
                "editor.rulers": [100],
                "python.defaultInterpreterPath": "auto",
            },
        )
        self.assertFalse(manifest.ide["cursor"].install)
        self.assertEqual(manifest.ide["cursor"].extensions, ("ms-python.python",))
        self.assertEqual(manifest.ide["cursor"].settings, {})



    def test_rejects_unknown_ide_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  windows-notepad:",
                        "    extensions: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "unsupported IDE names: windows-notepad"):
                read_manifest(manifest_path)



    def test_rejects_invalid_ide_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    extensions:",
                        "      - ms-python.python",
                        "      - 123",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, r"ide.vscode.extensions\[2\] must be a non-empty string"):
                read_manifest(manifest_path)



    def test_rejects_non_boolean_ide_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    install: maybe",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "ide.vscode.install must be a boolean"):
                read_manifest(manifest_path)



    def test_rejects_unsupported_auto_ide_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "ide:",
                        "  vscode:",
                        "    settings:",
                        "      editor.defaultFormatter: auto",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "does not support the special value 'auto'"):
                read_manifest(manifest_path)
