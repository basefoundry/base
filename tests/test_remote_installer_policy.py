from __future__ import annotations

import re
from pathlib import Path

import pytest

from base_setup import remote_installers
from base_setup.manifest import ManifestError
from base_setup.manifest import read_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "docs" / "remote-installer-policy.md"
HOMEBREW_INSTALLER_URL = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
HOMEBREW_ENTRY_POINTS = (
    REPO_ROOT / "bootstrap.sh",
    REPO_ROOT / "install.sh",
    REPO_ROOT / "cli" / "bash" / "commands" / "basectl" / "subcommands" / "setup_macos_homebrew.sh",
)


def policy_installer_urls() -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in POLICY_PATH.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 4:
            continue
        match = re.search(r"`(https://[^`]+)`", cells[2])
        if match is not None:
            rows[cells[1]] = match.group(1)
    return rows


def test_policy_table_matches_registered_python_installers_and_homebrew() -> None:
    expected = {spec.display_name: spec.default_url for spec in remote_installers.PYTHON_REMOTE_INSTALLERS}
    expected["Homebrew"] = HOMEBREW_INSTALLER_URL

    assert policy_installer_urls() == expected


def test_python_installer_urls_have_one_code_definition() -> None:
    registry_path = REPO_ROOT / "cli" / "python" / "base_setup" / "remote_installers.py"
    package_roots = (
        REPO_ROOT / "cli" / "python" / "base_setup",
        REPO_ROOT / "cli" / "python" / "base_dev",
    )
    source_paths = tuple(
        path
        for package_root in package_roots
        for path in package_root.rglob("*.py")
        if "tests" not in path.relative_to(package_root).parts
    )

    for spec in remote_installers.PYTHON_REMOTE_INSTALLERS:
        assert registry_path.read_text(encoding="utf-8").count(spec.default_url) == 1
        for source_path in source_paths:
            if source_path == registry_path:
                continue
            assert spec.default_url not in source_path.read_text(encoding="utf-8"), source_path


def test_standalone_homebrew_entry_points_share_the_documented_default() -> None:
    for entry_point in HOMEBREW_ENTRY_POINTS:
        source = entry_point.read_text(encoding="utf-8")
        urls = set(re.findall(r"https://raw\.githubusercontent\.com/Homebrew/install/[^\"'\s]+", source))
        assert urls == {HOMEBREW_INSTALLER_URL}, entry_point


def test_uv_and_mise_do_not_embed_remote_shell_pipelines() -> None:
    for relative_path in (
        "cli/python/base_setup/uv.py",
        "cli/python/base_setup/mise_delegate.py",
    ):
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "curl " not in source
        assert "sh -c" not in source


def test_project_manifest_cannot_define_remote_installer_fields(tmp_path: Path) -> None:
    manifest_path = tmp_path / "base_manifest.yaml"
    manifest_path.write_text(
        "project:\n  name: demo\nremote_installers:\n  uv:\n    url: https://example.test/install.sh\n",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="unsupported top-level keys: remote_installers"):
        read_manifest(manifest_path)
