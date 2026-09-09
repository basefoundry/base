import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_DOC = REPO_ROOT / "docs" / "windows-support.md"
README = REPO_ROOT / "README.md"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "windows-contract.yml"
PUBLIC_WINDOWS_SURFACES = tuple(
    REPO_ROOT / relative_path
    for relative_path in (
        "README.md",
        ".ai-context/PROJECT.md",
        ".ai-context/DECISIONS.md",
        "docs/architecture.md",
        "docs/product-requirements.md",
        "docs/product-assessment.md",
        "docs/technical-overview.md",
        "CHANGELOG.md",
    )
)
AFFIRMATIVE_NATIVE_WINDOWS_CLAIMS = (
    re.compile(
        r"\bBase\s+(?:now\s+)?(?:fully\s+)?supports\s+(?:native\s+)?Windows\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:native\s+)?Windows\s+is\s+(?:now\s+)?supported\b", re.IGNORECASE),
    re.compile(
        r"\b(?:native\s+)?Windows\s+support\s+is\s+(?:now\s+)?(?:available|complete|full|implemented|supported)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bNative Windows\s*\|\s*Supported\b", re.IGNORECASE),
)


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


def test_public_surfaces_reject_affirmative_native_windows_claims() -> None:
    violations: list[str] = []

    for path in PUBLIC_WINDOWS_SURFACES:
        text = path.read_text(encoding="utf-8")
        for pattern in AFFIRMATIVE_NATIVE_WINDOWS_CLAIMS:
            for match in pattern.finditer(text):
                line_number = text.count("\n", 0, match.start()) + 1
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_number}: {match.group(0)}")

    assert not violations, "Affirmative native-Windows support claims found:\n" + "\n".join(violations)


def test_validation_document_distinguishes_phase_zero_from_phase_one() -> None:
    document = WINDOWS_DOC.read_text(encoding="utf-8")

    assert "## Phase 0 Validation" in document
    assert "## Phase 1 Validation" in document
    assert "does not invoke a native Base launcher" in document
    assert "When the native launcher and read-only command subset land" in document


def test_phase_zero_workflow_enforces_documented_powershell_floor() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert '$minimumPowerShell = [version]"7.4"' in workflow
    assert "$PSVersionTable.PSVersion -lt $minimumPowerShell" in workflow
