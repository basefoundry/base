from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "docs" / "ecosystem-policy.md"
README = REPO_ROOT / "README.md"
DOCS_README = REPO_ROOT / "docs" / "README.md"
RELEASE_PROCESS = REPO_ROOT / "docs" / "release-process.md"
STABILIZATION_POLICY = REPO_ROOT / "docs" / "release-stabilization-policy.md"
WORKFLOWS_CONTEXT = REPO_ROOT / ".ai-context" / "WORKFLOWS.md"
DECISIONS_CONTEXT = REPO_ROOT / ".ai-context" / "DECISIONS.md"
BOOTSTRAP = REPO_ROOT / "docs" / "bootstrap.md"
CONTRIBUTOR_GUIDE = REPO_ROOT / "docs" / "contributor-first-change.md"
ECOSYSTEM_MAP = REPO_ROOT / "docs" / "ecosystem-map.md"
DOWNSTREAM_SMOKE_TEST = REPO_ROOT / "docs" / "downstream-release-smoke-test.md"


def test_ecosystem_policy_is_canonical_and_covers_required_boundaries() -> None:
    text = POLICY.read_text(encoding="utf-8")

    for required in (
        "Ownership and dependency direction",
        "Platform boundaries",
        "License history",
        "Release and artifact immutability",
        "`ubuntu-24.04`",
        "`macos-14`",
        "`macos-15`",
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


def test_release_process_links_to_the_stabilization_policy() -> None:
    policy = STABILIZATION_POLICY.read_text(encoding="utf-8")
    release_process = RELEASE_PROCESS.read_text(encoding="utf-8")

    for required in (
        "Release classes",
        "High-impact change checklist",
        "Review and waiver rules",
        "Urgent security or availability patch",
        "candidate",
        "independent review",
    ):
        assert required in policy
    assert "release-stabilization-policy.md" in release_process


def test_base_license_and_platform_summary_are_version_qualified() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "Windows is out of scope for Base." in readme
    assert "read-only/development guidance" in readme
    assert "Apache-2.0 starting with v1.9.0" in readme
    assert "Earlier releases retain" in readme


def test_release_and_platform_guidance_matches_current_baselines() -> None:
    workflows = WORKFLOWS_CONTEXT.read_text(encoding="utf-8")
    decisions = DECISIONS_CONTEXT.read_text(encoding="utf-8")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    contributor = CONTRIBUTOR_GUIDE.read_text(encoding="utf-8")
    ecosystem_map = ECOSYSTEM_MAP.read_text(encoding="utf-8")
    downstream = DOWNSTREAM_SMOKE_TEST.read_text(encoding="utf-8")

    assert "release-pinned base-cli v0.5.1" in workflows
    assert "release-pinned base-cli v0.4.3" not in workflows
    assert "1.11.0-dev+g<short-sha>" in bootstrap
    assert "1.10.0-dev+g<short-sha>" not in bootstrap
    assert decisions.count("1.12.0") >= 1
    assert "planned for v1.12.0" in contributor
    assert "v1.12.0 Windows milestone" in ecosystem_map
    assert "release_tag=v1.10.0" in downstream
    assert "expected_commit=167947add351b8d609b5ab17342425e9a337acbb" in downstream
