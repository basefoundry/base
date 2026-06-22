from __future__ import annotations

from pathlib import Path

from base_pr_policy.engine import PrPolicyInputs, render_pr_body
from base_setup.github_manifest import GithubPrConfig, GithubPrRequiredSectionsConfig


def test_render_pr_body_uses_default_label_and_path_sections() -> None:
    policy = GithubPrConfig(
        template=None,
        required_sections=GithubPrRequiredSectionsConfig(
            default=("Summary", "Issue", "Validation"),
            labels={
                "needs-demo": ("Demo Impact",),
                "security": ("Security Notes",),
            },
            paths={
                "docs/**": ("Docs Impact",),
                "migrations/**": ("Migration Plan", "Rollback Plan"),
            },
        ),
    )

    body = render_pr_body(
        policy,
        PrPolicyInputs(
            issue_number=403,
            labels=("Needs-Demo",),
            paths=("docs/github-workflow.md", "migrations/001.sql"),
        ),
    )

    assert body == (
        "## Summary\n\n"
        "## Issue\n\n"
        "Fixes #403\n\n"
        "## Validation\n\n"
        "## Demo Impact\n\n"
        "## Docs Impact\n\n"
        "## Migration Plan\n\n"
        "## Rollback Plan\n"
    )


def test_render_pr_body_keeps_existing_template_sections_and_issue_link() -> None:
    policy = GithubPrConfig(
        template=".github/pull_request_template.md",
        required_sections=GithubPrRequiredSectionsConfig(
            default=("Summary", "Issue", "Validation"),
            labels={},
            paths={},
        ),
    )

    body = render_pr_body(
        policy,
        PrPolicyInputs(issue_number=403, template_body="## Summary\n\nDone.\n"),
    )

    assert body == "## Summary\n\nDone.\n\n## Issue\n\nFixes #403\n\n## Validation\n"


def test_render_pr_body_appends_issue_link_without_issue_section() -> None:
    policy = GithubPrConfig(
        template=None,
        required_sections=GithubPrRequiredSectionsConfig(
            default=("Summary",),
            labels={},
            paths={},
        ),
    )

    body = render_pr_body(policy, PrPolicyInputs(issue_number=403))

    assert body == "## Summary\n\nFixes #403\n"


def test_render_pr_body_deduplicates_triggered_sections() -> None:
    policy = GithubPrConfig(
        template=None,
        required_sections=GithubPrRequiredSectionsConfig(
            default=("Summary", "Validation"),
            labels={"needs-demo": ("Validation", "Demo Impact")},
            paths={"demo/**": ("Demo Impact",)},
        ),
    )

    body = render_pr_body(
        policy,
        PrPolicyInputs(labels=("needs-demo",), paths=("demo/run.sh",)),
    )

    assert body == "## Summary\n\n## Validation\n\n## Demo Impact\n"


def test_template_body_from_policy_reads_relative_template(tmp_path: Path) -> None:
    template_path = tmp_path / ".github" / "pull_request_template.md"
    template_path.parent.mkdir()
    template_path.write_text("## Summary\n\nSeeded.\n", encoding="utf-8")
    policy = GithubPrConfig(
        template=".github/pull_request_template.md",
        required_sections=GithubPrRequiredSectionsConfig(default=(), labels={}, paths={}),
    )

    body = render_pr_body(policy, PrPolicyInputs(project_root=tmp_path))

    assert body == "## Summary\n\nSeeded.\n"
