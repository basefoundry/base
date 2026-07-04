from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
BOOTSTRAP_DOC = REPO_ROOT / "docs" / "bootstrap.md"


def section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def test_readme_first_mile_section_surfaces_verified_homebrew_installer_path() -> None:
    text = README.read_text(encoding="utf-8")
    first_mile = section(text, "### New Or Uncertain Machine?", "### Team Or Security-Conscious Rollout")

    assert "curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash" in first_mile
    assert "BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL" in first_mile
    assert "BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256" in first_mile
    assert "BASE_HOMEBREW_INSTALLER_URL" in first_mile
    assert "BASE_HOMEBREW_INSTALLER_SHA256" in first_mile


def test_bootstrap_quick_start_surfaces_verified_homebrew_installer_path() -> None:
    text = BOOTSTRAP_DOC.read_text(encoding="utf-8")
    quick_start = section(text, "## Quick Start", "## Install Mode")

    assert "curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash" in quick_start
    assert "BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL" in quick_start
    assert "BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256" in quick_start
    assert "BASE_HOMEBREW_INSTALLER_URL" in quick_start
    assert "BASE_HOMEBREW_INSTALLER_SHA256" in quick_start
