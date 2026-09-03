from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_DOC = REPO_ROOT / "docs" / "windows-support.md"
README = REPO_ROOT / "README.md"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "windows-contract.yml"


def test_windows_contract_is_explicitly_provisional() -> None:
    document = WINDOWS_DOC.read_text(encoding="utf-8")

    assert "Status: proposal and implementation boundary" in document
    assert "native Windows is not supported" in document
    assert "Git Bash" in document
    assert "WSL2" in document
    assert "PowerShell 7.4" in document
    assert "%LOCALAPPDATA%\\Base" in document


def test_windows_contract_defers_features_without_adapters() -> None:
    document = WINDOWS_DOC.read_text(encoding="utf-8")

    for feature in (
        "basectl activate",
        "project `run`, `test`, `build`, and `demo` execution",
        "IDE installation",
        "Bash completion",
        "Homebrew and apt-backed artifacts",
    ):
        assert feature in document


def test_public_surfaces_link_to_the_windows_contract_without_claiming_support() -> None:
    document = WINDOWS_DOC.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Native Windows Support Contract" in readme
    assert "planned but not supported yet" in readme
    assert "runs-on: windows-latest" in workflow
    assert "Phase 0" in workflow
    assert "mistaken for full" in document
