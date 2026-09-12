from __future__ import annotations

from pathlib import Path
import venv

import pytest

from base_setup.manifest import read_manifest
from base_setup.test_requirements import reconcile_test_requirements
from base_setup.tests.helpers import fake_context


def snapshot(root: Path) -> dict[str, tuple[int, int, bytes | str | None]]:
    result = {}
    for path in root.rglob("*"):
        stat = path.lstat()
        content = str(path.readlink()) if path.is_symlink() else path.read_bytes() if path.is_file() else None
        result[str(path.relative_to(root))] = (stat.st_mode, stat.st_mtime_ns, content)
    return result


@pytest.mark.parametrize("state", ["missing", "existing", "recreate"])
def test_requirements_preview_preserves_real_filesystem(
    tmp_path: Path, manifest_factory, monkeypatch: pytest.MonkeyPatch, state: str,
) -> None:
    manifest_path = manifest_factory.write(tmp_path / "demo")
    manifest_path.write_text(manifest_path.read_text().replace(
        "  command:", "  requirements: requirements.txt\n  command:",
    ))
    (manifest_path.parent / "requirements.txt").write_text("fixture==1.0\n")
    venv_path = manifest_path.parent / ".venv"
    if state != "missing":
        venv.EnvBuilder(with_pip=False).create(venv_path)
        (venv_path / "keep.txt").write_text("preserve existing environment\n")
    for name in ("BASE_PROJECT", "BASE_PROJECT_VENV_DIR", "BASE_SETUP_RECREATE_PROJECT_VENV"):
        monkeypatch.delenv(name, raising=False)
    if state == "recreate":
        monkeypatch.setenv("BASE_SETUP_RECREATE_PROJECT_VENV", "true")
    before = snapshot(venv_path)

    reconcile_test_requirements(fake_context(), read_manifest(manifest_path), dry_run=True)

    assert snapshot(venv_path) == before
    assert venv_path.exists() == (state != "missing")
