import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / "VERSION"

CURRENT_VERSION_REFERENCES = (
    (
        REPO_ROOT / "README.md",
        r"!\[Version\]\(https://img\.shields\.io/badge/version-([0-9]+\.[0-9]+\.[0-9]+)-blue\)",
    ),
    (
        REPO_ROOT / "README.md",
        r"Base `([0-9]+\.[0-9]+\.[0-9]+)` is the current release\.",
    ),
    (
        REPO_ROOT / "docs" / "technical-overview.md",
        r"Base \*\*([0-9]+\.[0-9]+\.[0-9]+)\*\* \([^)]+\) covers:",
    ),
)


def test_current_version_references_match_version_file() -> None:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    mismatches: list[str] = []

    for path, pattern in CURRENT_VERSION_REFERENCES:
        text = path.read_text(encoding="utf-8")
        match = re.search(pattern, text)
        if match is None:
            mismatches.append(f"{path.relative_to(REPO_ROOT)}: missing guarded current-version reference")
            continue
        documented_version = match.group(1)
        if documented_version != version:
            mismatches.append(
                f"{path.relative_to(REPO_ROOT)}: expected current version {version}, found {documented_version}"
            )

    assert not mismatches, "\n".join(mismatches)
