from __future__ import annotations

# pylint: disable=too-many-lines,too-many-public-methods

import tempfile
import unittest
from pathlib import Path

from base_setup.manifest import BaseManifest, ManifestError, read_manifest


class ManifestParsingTests(unittest.TestCase):

    @staticmethod
    def read_manifest_lines(*lines: str) -> BaseManifest:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text("\n".join(lines), encoding="utf-8")

            return read_manifest(manifest_path)

    def test_reads_basic_manifest(self) -> None:
        manifest = self.read_manifest_lines(
            "project:",
            "  name: demo",
            "",
            "artifacts:",
            "  - type: tool",
            "    name: terraform",
            "    version: \"1.8.5\"",
        )

        self.assertEqual(manifest.schema_version, 1)
        self.assertEqual(manifest.project_name, "demo")
        self.assertIsNone(manifest.brewfile)
        self.assertEqual(manifest.artifacts[0].artifact_type, "tool")
        self.assertEqual(manifest.artifacts[0].name, "terraform")
        self.assertEqual(manifest.artifacts[0].version, "1.8.5")
        self.assertFalse(manifest.artifacts[0].bootstrap)
        self.assertEqual(manifest.activate.source, ())
        self.assertIsNone(manifest.python.manager)
        self.assertIsNone(manifest.python.requires_python)

    def test_rejects_missing_manifest_path_with_manifest_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"

            with self.assertRaisesRegex(ManifestError, "unable to read manifest"):
                read_manifest(manifest_path)

    def test_reads_manifest_python_uv_manager(self) -> None:
        manifest = self.read_manifest_lines(
            "project:",
            "  name: demo",
            "",
            "python:",
            "  manager: uv",
            "",
            "artifacts: []",
        )

        self.assertEqual(manifest.python.manager, "uv")

    def test_reads_manifest_python_requirement(self) -> None:
        manifest = self.read_manifest_lines(
            "project:",
            "  name: demo",
            "",
            "python:",
            "  requires_python: '>=3.11,<3.14'",
            "",
            "artifacts: []",
        )

        self.assertEqual(manifest.python.requires_python, ">=3.11,<3.14")


    def test_reads_manifest_github_pr_policy(self) -> None:
        manifest = self.read_manifest_lines(
            "project:",
            "  name: demo",
            "",
            "github:",
            "  pr:",
            "    template: .github/pull_request_template.md",
            "    required_sections:",
            "      default:",
            "        - Summary",
            "        - Issue",
            "        - Validation",
            "      labels:",
            "        needs-demo:",
            "          - Demo Impact",
            "        security:",
            "          - Security Notes",
            "      paths:",
            "        docs/**:",
            "          - Docs Impact",
            "        migrations/**:",
            "          - Migration Plan",
            "          - Rollback Plan",
            "",
            "artifacts: []",
        )

        self.assertIsNotNone(manifest.github.pr)
        assert manifest.github.pr is not None
        self.assertEqual(manifest.github.pr.template, ".github/pull_request_template.md")
        required = manifest.github.pr.required_sections
        self.assertEqual(required.default, ("Summary", "Issue", "Validation"))
        self.assertEqual(required.labels["needs-demo"], ("Demo Impact",))
        self.assertEqual(required.labels["security"], ("Security Notes",))
        self.assertEqual(required.paths["docs/**"], ("Docs Impact",))
        self.assertEqual(required.paths["migrations/**"], ("Migration Plan", "Rollback Plan"))


    def test_rejects_invalid_manifest_github_pr_policy(self) -> None:
        invalid_values = {
            "scalar_github": "github: true",
            "unknown_github_key": "github:\n  issues: {}",
            "scalar_pr": "github:\n  pr: true",
            "unknown_pr_key": "github:\n  pr:\n    body: {}",
            "absolute_template": "github:\n  pr:\n    template: /tmp/pull_request_template.md",
            "parent_template": "github:\n  pr:\n    template: ../pull_request_template.md",
            "scalar_required_sections": "github:\n  pr:\n    required_sections: Summary",
            "scalar_default": "github:\n  pr:\n    required_sections:\n      default: Summary",
            "empty_default_section": "github:\n  pr:\n    required_sections:\n      default:\n        - ''",
            "duplicate_default_section": (
                "github:\n  pr:\n    required_sections:\n      default:\n        - Summary\n        - Summary"
            ),
            "scalar_labels": "github:\n  pr:\n    required_sections:\n      labels: needs-demo",
            "empty_label": (
                "github:\n  pr:\n    required_sections:\n      labels:\n        '':\n          - Demo Impact"
            ),
            "scalar_label_sections": (
                "github:\n  pr:\n    required_sections:\n      labels:\n        needs-demo: Demo Impact"
            ),
            "scalar_paths": "github:\n  pr:\n    required_sections:\n      paths: docs/**",
            "empty_path": "github:\n  pr:\n    required_sections:\n      paths:\n        '':\n          - Docs Impact",
            "unknown_required_sections_key": "github:\n  pr:\n    required_sections:\n      teams: {}",
        }
        for name, github_yaml in invalid_values.items():
            with self.subTest(name=name):
                with self.assertRaises(ManifestError):
                    self.read_manifest_lines(
                        "project:",
                        "  name: demo",
                        github_yaml,
                        "artifacts: []",
                    )


    def test_rejects_invalid_manifest_python_config(self) -> None:
        invalid_values = {
            "scalar": "python: uv",
            "unknown_key": "python:\n  manager: uv\n  version: '3.12'",
            "empty_manager": "python:\n  manager: ''",
            "non_string_manager": "python:\n  manager: 7",
            "unsupported_manager": "python:\n  manager: poetry",
            "empty_requires_python": "python:\n  requires_python: ''",
            "non_string_requires_python": "python:\n  requires_python: 7",
        }
        for name, python_yaml in invalid_values.items():
            with self.subTest(name=name):
                with self.assertRaises(ManifestError):
                    self.read_manifest_lines(
                        "project:",
                        "  name: demo",
                        python_yaml,
                        "artifacts: []",
                    )




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


    def test_rejects_path_unsafe_project_names(self) -> None:
        for project_name in ("../../etc", "../base", "demo/name", "demo name", ".hidden", "demo?"):
            with self.subTest(project_name=project_name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    manifest_path = Path(tmpdir) / "base_manifest.yaml"
                    manifest_path.write_text(
                        "\n".join(
                            [
                                "project:",
                                f"  name: {project_name}",
                                "",
                                "artifacts: []",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    with self.assertRaisesRegex(ManifestError, "project.name must be a valid name"):
                        read_manifest(manifest_path)


    def test_accepts_valid_project_name_characters(self) -> None:
        for project_name in ("demo", "demo.1", "demo-1", "demo_1", "demo:local", "2demo"):
            with self.subTest(project_name=project_name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    manifest_path = Path(tmpdir) / "base_manifest.yaml"
                    manifest_path.write_text(
                        "\n".join(
                            [
                                "project:",
                                f"  name: {project_name}",
                                "",
                                "artifacts: []",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    manifest = read_manifest(manifest_path)

                self.assertEqual(manifest.project_name, project_name)



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


    def test_reads_manifest_demo_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "demo:",
                        "  script: ./demo/demo.sh",
                        "  description: Interactive project walkthrough",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.demo)
        assert manifest.demo is not None
        self.assertEqual(manifest.demo.script, "./demo/demo.sh")
        self.assertEqual(manifest.demo.description, "Interactive project walkthrough")
        self.assertIsNone(manifest.demo.runner)


    def test_reads_manifest_demo_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "demo:",
                        "  script: ./demo/demo.sh",
                        "  runner: uv",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.demo)
        assert manifest.demo is not None
        self.assertEqual(manifest.demo.runner, "uv")


    def test_reads_manifest_release_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "release:",
                        "  version_file: VERSION",
                        "  changelog: CHANGELOG.md",
                        "  tag_prefix: v",
                        "  github:",
                        "    repository: basefoundry/base",
                        "    release_title: \"Base v{version}\"",
                        "  homebrew:",
                        "    required: true",
                        "    tap_repository: basefoundry/homebrew-base",
                        "    formula_path: Formula/base.rb",
                        "    package: basefoundry/base/base",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.release)
        assert manifest.release is not None
        self.assertEqual(manifest.release.version_file, "VERSION")
        self.assertEqual(manifest.release.changelog, "CHANGELOG.md")
        self.assertEqual(manifest.release.tag_prefix, "v")
        self.assertEqual(manifest.release.github.repository, "basefoundry/base")
        self.assertEqual(manifest.release.github.release_title, "Base v{version}")
        self.assertIsNone(manifest.release.runner)
        self.assertIsNotNone(manifest.release.homebrew)
        assert manifest.release.homebrew is not None
        self.assertTrue(manifest.release.homebrew.required)
        self.assertEqual(manifest.release.homebrew.tap_repository, "basefoundry/homebrew-base")
        self.assertEqual(manifest.release.homebrew.formula_path, "Formula/base.rb")
        self.assertEqual(manifest.release.homebrew.package, "basefoundry/base/base")

    def test_reads_manifest_release_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "release:",
                        "  runner: uv",
                        "  github:",
                        "    repository: codeforester/demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.release)
        assert manifest.release is not None
        self.assertEqual(manifest.release.runner, "uv")


    def test_reads_manifest_build_target_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "build:",
                        "  default:",
                        "    - package",
                        "  targets:",
                        "    package:",
                        "      command: python -m build",
                        "      runner: uv",
                        "      working_dir: services/api",
                        "      description: Build the Python package.",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.build)
        assert manifest.build is not None
        self.assertEqual(manifest.build.targets["package"].command, "python -m build")
        self.assertEqual(manifest.build.targets["package"].runner, "uv")



    def test_reads_manifest_release_config_without_homebrew(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "release:",
                        "  github:",
                        "    repository: codeforester/demo",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.release)
        assert manifest.release is not None
        self.assertEqual(manifest.release.version_file, "VERSION")
        self.assertEqual(manifest.release.changelog, "CHANGELOG.md")
        self.assertEqual(manifest.release.tag_prefix, "v")
        self.assertEqual(manifest.release.github.repository, "codeforester/demo")
        self.assertEqual(manifest.release.github.release_title, "{repository} v{version}")
        self.assertIsNone(manifest.release.homebrew)


    def test_rejects_invalid_manifest_release_config(self) -> None:
        invalid_values = {
            "scalar": "release: true",
            "unknown_key": "release:\n  github:\n    repository: basefoundry/base\n  package: base",
            "missing_github": "release:\n  version_file: VERSION",
            "github_scalar": "release:\n  github: basefoundry/base",
            "missing_repository": "release:\n  github:\n    release_title: Base",
            "invalid_repository": "release:\n  github:\n    repository: codeforester",
            "absolute_version_file": (
                "release:\n  version_file: /tmp/VERSION\n  github:\n    repository: basefoundry/base"
            ),
            "absolute_changelog": (
                "release:\n  changelog: /tmp/CHANGELOG.md\n  github:\n    repository: basefoundry/base"
            ),
            "empty_tag_prefix": "release:\n  tag_prefix: ''\n  github:\n    repository: basefoundry/base",
            "homebrew_scalar": "release:\n  github:\n    repository: basefoundry/base\n  homebrew: true",
            "homebrew_required_missing_tap": (
                "release:\n"
                "  github:\n"
                "    repository: basefoundry/base\n"
                "  homebrew:\n"
                "    required: true\n"
                "    formula_path: Formula/base.rb\n"
                "    package: basefoundry/base/base"
            ),
            "homebrew_absolute_formula": (
                "release:\n"
                "  github:\n"
                "    repository: basefoundry/base\n"
                "  homebrew:\n"
                "    required: true\n"
                "    tap_repository: basefoundry/homebrew-base\n"
                "    formula_path: /tmp/base.rb\n"
                "    package: basefoundry/base/base"
            ),
            "homebrew_invalid_package": (
                "release:\n"
                "  github:\n"
                "    repository: basefoundry/base\n"
                "  homebrew:\n"
                "    required: true\n"
                "    tap_repository: basefoundry/homebrew-base\n"
                "    formula_path: Formula/base.rb\n"
                "    package: base"
            ),
            "unsupported_runner": (
                "release:\n"
                "  runner: npm\n"
                "  github:\n"
                "    repository: basefoundry/base"
            ),
        }
        for name, release_yaml in invalid_values.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    manifest_path = Path(tmpdir) / "base_manifest.yaml"
                    manifest_path.write_text(
                        "\n".join(
                            [
                                "project:",
                                "  name: demo",
                                release_yaml,
                                "artifacts: []",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    with self.assertRaises(ManifestError):
                        read_manifest(manifest_path)



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


    def test_rejects_invalid_manifest_demo_config(self) -> None:
        invalid_values = {
            "scalar": "demo: ./demo/demo.sh",
            "unknown_key": "demo:\n  script: ./demo/demo.sh\n  shell: bash",
            "missing_script": "demo:\n  description: Interactive project walkthrough",
            "empty_script": "demo:\n  script: ''",
            "non_string_script": "demo:\n  script: 7",
            "newline_script": "demo:\n  script: \"demo\\n/demo.sh\"",
            "empty_description": "demo:\n  script: ./demo/demo.sh\n  description: ''",
            "non_string_description": "demo:\n  script: ./demo/demo.sh\n  description: 7",
            "unsupported_runner": "demo:\n  script: ./demo/demo.sh\n  runner: npm",
        }
        for name, demo_yaml in invalid_values.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    manifest_path = Path(tmpdir) / "base_manifest.yaml"
                    manifest_path.write_text(
                        "\n".join(
                            [
                                "project:",
                                "  name: demo",
                                demo_yaml,
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

        self.assertEqual(manifest.commands["dev"].command, "uvicorn app:app --reload")
        self.assertIsNone(manifest.commands["dev"].runner)
        self.assertEqual(manifest.commands["lint"].command, "ruff check .")
        self.assertIsNone(manifest.commands["lint"].runner)


    def test_reads_manifest_commands_with_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "commands:",
                        "  audit:",
                        "    command: pytest tests/audit",
                        "    runner: uv",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(manifest.commands["audit"].command, "pytest tests/audit")
        self.assertEqual(manifest.commands["audit"].runner, "uv")



    def test_rejects_invalid_manifest_commands(self) -> None:
        invalid_values = {
            "scalar": "commands: pytest",
            "empty_name": "commands:\n  '': pytest",
            "invalid_name": "commands:\n  'bad command': pytest",
            "reserved_test": "commands:\n  test: pytest",
            "empty_command": "commands:\n  lint: ''",
            "non_string_command": "commands:\n  lint: 7",
            "mapping_missing_command": "commands:\n  lint:\n    runner: uv",
            "mapping_empty_command": "commands:\n  lint:\n    command: ''",
            "mapping_unknown_key": "commands:\n  lint:\n    command: ruff check .\n    cwd: src",
            "unsupported_runner": "commands:\n  lint:\n    command: ruff check .\n    runner: npm",
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
        self.assertIsNone(manifest.test.runner)


    def test_reads_manifest_test_command_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  command: pytest tests/",
                        "  runner: uv",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertIsNotNone(manifest.test)
        assert manifest.test is not None
        self.assertEqual(manifest.test.command, "pytest tests/")
        self.assertEqual(manifest.test.runner, "uv")



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


    def test_rejects_invalid_manifest_test_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "test:",
                        "  command: pytest",
                        "  runner: npm",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "test.runner must be one of: uv"):
                read_manifest(manifest_path)


    def test_rejects_invalid_manifest_build_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "build:",
                        "  targets:",
                        "    package:",
                        "      command: python -m build",
                        "      runner: npm",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "build.targets.package.runner must be one of: uv"):
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


class HealthPortManifestParsingTests(unittest.TestCase):

    def test_reads_manifest_required_ports(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "base_manifest.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: demo",
                        "",
                        "health:",
                        "  required_ports:",
                        "    - name: postgres",
                        "      host: 127.0.0.1",
                        "      port: 5432",
                        "      state: listening",
                        "    - port: 8000",
                        "      state: free",
                        "",
                        "artifacts: []",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = read_manifest(manifest_path)

        self.assertEqual(len(manifest.health.required_ports), 2)
        self.assertEqual(manifest.health.required_ports[0].name, "postgres")
        self.assertEqual(manifest.health.required_ports[0].host, "127.0.0.1")
        self.assertEqual(manifest.health.required_ports[0].port, 5432)
        self.assertEqual(manifest.health.required_ports[0].state, "listening")
        self.assertEqual(manifest.health.required_ports[1].name, None)
        self.assertEqual(manifest.health.required_ports[1].host, "127.0.0.1")
        self.assertEqual(manifest.health.required_ports[1].port, 8000)
        self.assertEqual(manifest.health.required_ports[1].state, "free")


    def test_rejects_invalid_manifest_required_ports(self) -> None:
        invalid_values = {
            "scalar": "health:\n  required_ports: 5432",
            "integer_entry": "health:\n  required_ports:\n    - 5432",
            "unknown_key": (
                "health:\n"
                "  required_ports:\n"
                "    - port: 5432\n"
                "      state: listening\n"
                "      protocol: udp"
            ),
            "missing_port": "health:\n  required_ports:\n    - state: listening",
            "bool_port": "health:\n  required_ports:\n    - port: true\n      state: listening",
            "low_port": "health:\n  required_ports:\n    - port: 0\n      state: listening",
            "high_port": "health:\n  required_ports:\n    - port: 65536\n      state: listening",
            "missing_state": "health:\n  required_ports:\n    - port: 5432",
            "unsupported_state": (
                "health:\n"
                "  required_ports:\n"
                "    - port: 5432\n"
                "      state: occupied"
            ),
            "empty_name": (
                "health:\n"
                "  required_ports:\n"
                "    - name: ''\n"
                "      port: 5432\n"
                "      state: listening"
            ),
            "duplicate_name": (
                "health:\n"
                "  required_ports:\n"
                "    - name: db\n"
                "      port: 5432\n"
                "      state: listening\n"
                "    - name: db\n"
                "      port: 6379\n"
                "      state: listening"
            ),
            "empty_host": (
                "health:\n"
                "  required_ports:\n"
                "    - host: ''\n"
                "      port: 5432\n"
                "      state: listening"
            ),
            "duplicate_endpoint": (
                "health:\n"
                "  required_ports:\n"
                "    - port: 5432\n"
                "      state: listening\n"
                "    - port: 5432\n"
                "      state: free"
            ),
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
