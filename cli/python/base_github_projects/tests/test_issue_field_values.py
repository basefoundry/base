from __future__ import annotations

from types import SimpleNamespace

from base_github_projects import issue_field_values


def test_run_issue_fields_api_pins_version_and_posts_json(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return SimpleNamespace(returncode=0, stdout="{}\n", stderr="")

    monkeypatch.setattr(issue_field_values.subprocess, "run", fake_run)

    result = issue_field_values.run_issue_fields_api(
        "repos/basefoundry/base/issues/42/issue-field-values",
        method="POST",
        payload={"issue_field_values": [{"issue_field_id": 12, "value": "High"}]},
    )

    assert result == {}
    assert calls == [
        {
            "command": [
                "gh",
                "api",
                "-H",
                "X-GitHub-Api-Version: 2026-03-10",
                "--method",
                "POST",
                "repos/basefoundry/base/issues/42/issue-field-values",
                "--input",
                "-",
            ],
            "input": '{"issue_field_values": [{"issue_field_id": 12, "value": "High"}]}',
            "text": True,
            "capture_output": True,
            "check": False,
            "timeout": 60,
        }
    ]


def test_issue_field_value_map_reads_single_select_and_date_values() -> None:
    values = issue_field_values.issue_field_value_map(
        {
            "issue_field_values": [
                {
                    "issue_field_name": "Priority",
                    "single_select_option": {"name": "Urgent"},
                },
                {"issue_field_name": "Start date", "value": "2026-11-24"},
            ]
        }
    )

    assert values == {"Priority": "Urgent", "Start date": "2026-11-24"}


def test_write_issue_field_values_uses_option_names_and_repository_owner(monkeypatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_api(path: str, *, method: str = "GET", payload=None):
        calls.append((path, method, payload))
        return {}

    monkeypatch.setattr(issue_field_values, "run_issue_fields_api", fake_api)

    issue_field_values.write_issue_field_values(
        "basefoundry",
        "basefoundry/base",
        42,
        {"Priority": "High", "Effort": "Small"},
        field_ids={"Priority": 1, "Effort": 2},
    )

    assert calls == [
        (
            "repos/basefoundry/base/issues/42/issue-field-values",
            "POST",
            {
                "issue_field_values": [
                    {"issue_field_id": 2, "value": "Small"},
                    {"issue_field_id": 1, "value": "High"},
                ]
            },
        )
    ]
