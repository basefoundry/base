import json
from pathlib import Path

import pytest

from base_release.downstream_version_bump import (
    DownstreamBumpError,
    update_base_demo_pins,
)


COMMIT = "a" * 40
CHECKSUM = "b" * 64


def test_current_demo_base_bump_and_clean_retry(tmp_path: Path) -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures/downstream/base-demo-6c050bd.json").read_text())
    for name, content in fixture["files"].items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    commit = "ac8d294421e1bfc14afa8c6a2a12f1affb5268ee"
    checksum = "f0522bf20b13e2f487767324f4688f1b1ed33b1c1bc1158a404f0e428ea3e993"
    changed = update_base_demo_pins(tmp_path, "base", "1.9.0", commit, checksum)
    assert Path(".release/release-bom.json") in changed
    bom = json.loads((tmp_path / ".release/release-bom.json").read_text())
    row = next(row for row in bom["components"] if row["repository"] == "basefoundry/base")
    assert (row["version"], row["tag"], row["commit"]) == ("1.9.0", "v1.9.0", commit)
    assert all(row["result"] == "not_tested" for row in bom["components"] + bom["combinations"])
    assert update_base_demo_pins(tmp_path, "base", "1.9.0", commit, checksum) == []


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
                ".github/workflows/tests.yml must pin every Base checkout to the immutable v1.8.0 release commit.",
                ".github/workflows/tests.yml does not pin the source compatibility job "
                "to the Base v1.8.0 release commit.",
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


def structured_fixture(root: Path) -> None:
    write_fixture(root)
    (root / ".github/workflows/tests.yml").write_text(
        ('git -C ../base fetch --depth 1 origin "${{ steps.dependencies.outputs.base_commit }}"\n' * 3)
        + ('ref: ${{ steps.dependencies.outputs.base_bash_libs_commit }}\n' * 3)
        + 'git -C ../base-cli fetch --depth 1 origin "${{ steps.dependencies.outputs.base_cli_commit }}"\n'
        + ('python3 bin/base-demo-dependencies --check --github-output\n' * 3)
    )
    (root / ".release").mkdir()
    document = {
        "schema_version": 1,
        "components": {
            "base": {"version": "1.8.0", "commit": COMMIT, "installer_sha256": CHECKSUM},
            "base-cli": {"version": "0.4.3", "commit": COMMIT},
            "base-bash-libs": {"version": "2.0.0", "commit": COMMIT},
        },
    }
    (root / ".release/supported-dependencies.json").write_text(json.dumps(document, indent=2) + "\n")


@pytest.mark.parametrize("component", ["base", "base-cli", "base-bash-libs"])
def test_structured_contract_and_noop(tmp_path: Path, component: str) -> None:
    structured_fixture(tmp_path)
    changed = update_base_demo_pins(tmp_path, component, "3.0.0", "c" * 40, "d" * 64)
    assert Path(".release/supported-dependencies.json") in changed
    document = json.loads((tmp_path / ".release/supported-dependencies.json").read_text())
    assert document["components"][component]["version"] == "3.0.0"
    assert document["components"][component]["commit"] == "c" * 40
    assert update_base_demo_pins(tmp_path, component, "3.0.0", "c" * 40, "d" * 64) == []


@pytest.mark.parametrize("drift", ["schema", "component", "commit", "checksum", "installer", "pyproject", "bom", "ci"])
def test_structured_drift_does_not_write_any_file(tmp_path: Path, drift: str) -> None:
    structured_fixture(tmp_path)
    path = tmp_path / ".release/supported-dependencies.json"
    document = json.loads(path.read_text())
    if drift == "schema":
        document["schema_version"] = True
    elif drift == "component":
        del document["components"]["base-cli"]
    elif drift in {"commit", "checksum"}:
        document["components"]["base"]["commit" if drift == "commit" else "installer_sha256"] = "invalid"
    elif drift == "installer":
        (tmp_path / "install.sh").write_text("drifted\n")
    elif drift == "pyproject":
        (tmp_path / "pyproject.toml").write_text('dependencies = ["base-cli==0.4.2"]\n')
    elif drift == "ci":
        (tmp_path / ".github/workflows/tests.yml").write_text("drifted\n")
    else:
        (tmp_path / ".release/release-bom.json").write_text('{"components":[],"combinations":[]}')
    path.write_text(json.dumps(document))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(DownstreamBumpError):
        update_base_demo_pins(tmp_path, "base", "1.9.0", "c" * 40, "d" * 64)
    assert before == {p: p.read_bytes() for p in before}
