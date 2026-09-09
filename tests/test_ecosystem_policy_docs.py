from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "docs" / "ecosystem-policy.md"
README = REPO_ROOT / "README.md"
DOCS_README = REPO_ROOT / "docs" / "README.md"
RELEASE_PROCESS = REPO_ROOT / "docs" / "release-process.md"


def test_ecosystem_policy_is_canonical_and_covers_required_boundaries() -> None:
    text = POLICY.read_text(encoding="utf-8")

    for required in (
        "Ownership and dependency direction",
        "Platform boundaries",
        "License history",
        "Release and artifact immutability",
        "`ubuntu-24.04`",
        "`macos-14`",
        "Base is Apache-2.0 starting with `v1.9.0`",
        "base-demo` remains MIT",
        "must fail closed",
        "moving source",
    ):
        assert required in text


def test_public_base_docs_link_to_the_canonical_ecosystem_policy() -> None:
    assert "docs/ecosystem-policy.md" in README.read_text(encoding="utf-8")
    assert "ecosystem-policy.md" in DOCS_README.read_text(encoding="utf-8")
    assert "ecosystem-policy.md" in RELEASE_PROCESS.read_text(encoding="utf-8")


def test_base_license_and_platform_summary_are_version_qualified() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "Windows is out of scope for Base." in readme
    assert "read-only/development guidance" in readme
    assert "Apache-2.0 starting with v1.9.0" in readme
    assert "Earlier releases retain" in readme
