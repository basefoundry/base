from pathlib import Path


ROOT = Path(__file__).parents[1]
TEMPLATE_DIR = ROOT / ".github" / "ISSUE_TEMPLATE"


def test_community_issue_templates_are_local_and_unassigned() -> None:
    implementation = (TEMPLATE_DIR / "implementation.yml").read_text()

    assert "assignees:" not in implementation
    for name in ("bug_report.yml", "documentation.yml", "feature_request.yml", "support.yml"):
        text = (TEMPLATE_DIR / name).read_text()
        assert "validations:" in text
        assert "assignees:" not in text


def test_issue_chooser_routes_support_and_security_privately_or_publicly() -> None:
    config = (TEMPLATE_DIR / "config.yml").read_text()

    assert "https://github.com/orgs/basefoundry/discussions" in config
    assert "https://github.com/basefoundry/base/security/advisories/new" in config
