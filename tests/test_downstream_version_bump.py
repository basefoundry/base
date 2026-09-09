from pathlib import Path

import pytest

from base_release.downstream_version_bump import (
    DownstreamBumpError,
    update_base_demo_pins,
)


COMMIT = "a" * 40
CHECKSUM = "b" * 64


def write_fixture(root: Path) -> None:
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".ai-context").mkdir()
    (root / "docs").mkdir()
    (root / "tests").mkdir()
    (root / "install.sh").write_text(
        '\n'.join(
            [
                'BASE_RELEASE_REF="${BASE_RELEASE_REF:-v1.8.0}"',
                'BASE_RELEASE_COMMIT="${BASE_RELEASE_COMMIT:-' + COMMIT + '}"',
                'BASE_INSTALL_SHA256="${BASE_INSTALL_SHA256-' + CHECKSUM + '}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / ".github" / "workflows" / "tests.yml").write_text(
        "\n".join(
            [
                "# Base v1.8.0",
                "# Base v1.8.0",
                "git -C ../base fetch --depth 1 origin " + COMMIT,
                "git -C ../base fetch --depth 1 origin " + COMMIT,
                "git -C ../base fetch --depth 1 origin " + COMMIT,
                "git clone --depth 1 --branch v0.4.3 https://github.com/basefoundry/base-cli.git ../base-cli",
                "# base-bash-libs v2.0.0",
                "repository: basefoundry/base-bash-libs\n          ref: " + COMMIT,
                "repository: basefoundry/base-bash-libs\n          ref: " + COMMIT,
                "repository: basefoundry/base-bash-libs\n          ref: " + COMMIT,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "docs" / "release.md").write_text(
        "- Base installer: the versioned `v1.8.0` URL, SHA-256\n"
        f"  `{CHECKSUM}`, and\n  Base commit `{COMMIT}`;\n",
        encoding="utf-8",
    )
    (root / "docs" / "contracts.md").write_text(
        "Base v1.8.0 installer and published Base v1.8.0 contract\n"
        "base-bash-libs v2.0.0\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "base-cli==0.4.3\nbase-cli==0.4.3\n",
        encoding="utf-8",
    )
    (root / ".ai-context" / "overview.md").write_text("base-cli==0.4.3\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        'dependencies = ["base-cli==0.4.3"]\n',
        encoding="utf-8",
    )
    (root / "tests" / "validate.sh").write_text(
        "\n".join(
            [
                "git -C ../base fetch --depth 1 origin " + COMMIT,
                "git -C ../base fetch --depth 1 origin " + COMMIT,
                "v1.8.0 v1.8.0 v1.8.0",
                "base-cli==0.4.3 base-cli==0.4.3",
                "git clone --depth 1 --branch v0.4.3 https://github.com/basefoundry/base-cli.git ../base-cli",
                "ref: " + COMMIT,
                "ref: " + COMMIT,
                "v2.0.0 v2.0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "tests" / "install_test.bats").write_text(
        f'TEST_BASE_COMMIT="{COMMIT}"\nInstalling pinned Base release \'v1.8.0\'\n',
        encoding="utf-8",
    )


def test_base_bump_updates_all_immutable_inputs(tmp_path: Path) -> None:
    write_fixture(tmp_path)

    changed = update_base_demo_pins(tmp_path, "base", "1.9.0", "c" * 40, "d" * 64)

    assert Path("install.sh") in changed
    assert "v1.9.0" in (tmp_path / "install.sh").read_text(encoding="utf-8")
    assert "c" * 40 in (tmp_path / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )
    assert "d" * 64 in (tmp_path / "docs" / "release.md").read_text(encoding="utf-8")


def test_component_bumps_update_their_downstream_contracts(tmp_path: Path) -> None:
    write_fixture(tmp_path)

    update_base_demo_pins(tmp_path, "base-cli", "0.4.4", "c" * 40)
    update_base_demo_pins(tmp_path, "base-bash-libs", "2.1.0", "d" * 40)

    assert "base-cli==0.4.4" in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    workflow = (tmp_path / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "--branch v0.4.4" in workflow
    assert workflow.count("ref: " + "d" * 40) == 3
    validation = (tmp_path / "tests" / "validate.sh").read_text(encoding="utf-8")
    assert "v2.1.0" in validation


def test_bump_rejects_drift_before_writing(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    original = (tmp_path / "install.sh").read_text(encoding="utf-8")
    (tmp_path / "docs" / "contracts.md").write_text("drifted\n", encoding="utf-8")

    with pytest.raises(DownstreamBumpError, match="refusing a partial bump"):
        update_base_demo_pins(tmp_path, "base", "1.9.0", "c" * 40, "d" * 64)

    assert (tmp_path / "install.sh").read_text(encoding="utf-8") == original


def test_invalid_release_identity_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(DownstreamBumpError, match="full lowercase 40-character SHA"):
        update_base_demo_pins(tmp_path, "base-cli", "1.9.0", "not-a-commit")
