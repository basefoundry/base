from __future__ import annotations

import subprocess
import venv
from pathlib import Path

import pytest

from base_setup.errors import ArtifactError
from base_setup.manifest import read_manifest
from base_setup.python_artifacts import python_artifact_installed
from base_setup.test_requirements import check_test_requirements
from base_setup.test_requirements import read_test_requirements


@pytest.mark.parametrize("requirement", [
    "local-fixture[feature]",
    "local-fixture[feature]==1.0",
    "local-fixture[feature,other]==1.0",
])
def test_extras_are_rejected_when_only_base_distribution_is_installed(tmp_path, monkeypatch, requirement):
    for variable in ("BASE_PROJECT", "BASE_PROJECT_ROOT", "BASE_PROJECT_MANIFEST", "BASE_PROJECT_VENV_DIR"):
        monkeypatch.delenv(variable, raising=False)
    manifest_path = tmp_path / "base_manifest.yaml"
    manifest_path.write_text(
        "project:\n  name: demo\ntest:\n  command: pytest\n  requirements: requirements.txt\nartifacts: []\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(requirement + "\n", encoding="utf-8")
    venv.EnvBuilder(with_pip=True).create(tmp_path / ".venv")
    python_bin = tmp_path / ".venv" / "bin" / "python"
    site_packages = Path(subprocess.check_output(
        [str(python_bin), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], text=True,
    ).strip())
    metadata = site_packages / "local_fixture-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: local-fixture\nVersion: 1.0\nProvides-Extra: feature\n"
        'Requires-Dist: absent-extra-fixture==9.9; extra == "feature"\n',
        encoding="utf-8",
    )
    assert python_artifact_installed(python_bin, "local-fixture", "1.0")
    assert not python_artifact_installed(python_bin, "absent-extra-fixture", "latest")
    manifest = read_manifest(manifest_path)

    check = check_test_requirements(manifest)

    assert check is not None
    assert not check.ok
    assert check.finding_id == "BASE-P180"
    assert "unsupported requirement syntax" in check.message
    assert "direct package names" in check.message
    assert "Review test.requirements" in check.fix
    with pytest.raises(ArtifactError, match="unsupported requirement syntax"):
        read_test_requirements(manifest)
