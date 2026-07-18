from __future__ import annotations

from pathlib import Path
from unittest import mock

from base_cli.history import build_finished_record
from base_cli.testing import invoke
from base_pr_policy import engine
from base_pr_policy.engine import PrPolicyInputs, render_pr_body
from base_setup.github_manifest import GithubPrConfig, GithubPrRequiredSectionsConfig


def test_explicit_manifest_populates_history_project_metadata(tmp_path) -> None:
    project_root = tmp_path / "demo"
    project_root.mkdir()
    manifest_path = project_root / "base_manifest.yaml"
    manifest_path.write_text(
        "project:\n  name: demo\ngithub:\n  pr:\n    required_sections:\n      default: [Summary]\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    captured = []

    with mock.patch(
        "base_cli.app.write_finished_record",
        side_effect=lambda *args: captured.append(args),
    ):
        result = invoke(
            engine.app,
            ["body", "--manifest", str(manifest_path)],
            home=tmp_path / "home",
            cwd=outside,
            env={"BASE_HOME": str(project_root)},
        )

    assert result.exit_code == 0, result.output
    assert len(captured) == 1
    record = build_finished_record(*captured[0])
    assert record["project"] == "demo"
    assert record["project_root"] == str(project_root.resolve())
    assert record["manifest"] == str(manifest_path.resolve())


def test_main_rejects_equals_form_options(capsys) -> None:
    status = engine.main(["body", "--issue=403"])

    captured = capsys.readouterr()
    assert status == 2
    assert "Option '--issue' uses unsupported equals syntax." in captured.err


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
