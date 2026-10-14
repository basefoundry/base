from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from base_release import engine, release_publish
from base_release.release_model import ReleaseContext, ReleaseError


def release_context(tmp_path: Path) -> ReleaseContext:
    manifest_path = tmp_path / "base_manifest.yaml"
    manifest_path.write_text("manifest\n", encoding="utf-8")
    notes_path = tmp_path / "release-notes.md"
    notes_path.write_text("release notes\n", encoding="utf-8")
    return ReleaseContext(
        manifest_path=manifest_path,
        manifest=SimpleNamespace(project_name="base"),
        release=SimpleNamespace(
            github=SimpleNamespace(repository="basefoundry/base", release_title="Base v{version}"),
            bom=SimpleNamespace(required=True),
            homebrew=None,
        ),
        version="1.2.3",
        tag_name="v1.2.3",
        version_file=tmp_path / "VERSION",
        changelog=tmp_path / "CHANGELOG.md",
    )


def test_readback_retries_rate_limited_reads_with_bounded_backoff(monkeypatch) -> None:
    failures = [
        ReleaseError("GitHub API rate limit exceeded"),
        ReleaseError("GitHub secondary rate limit"),
    ]
    calls = []

    def capture(command, **_):
        calls.append(command)
        if failures:
            raise failures.pop(0)
        return "ok"

    monkeypatch.setattr(release_publish, "capture_release_step", capture)
    with mock.patch.object(release_publish.time, "sleep") as sleep:
        assert release_publish.capture_github_step(["gh", "api", "endpoint"]) == "ok"

    assert len(calls) == 3
    assert sleep.call_args_list == [mock.call(1), mock.call(2)]


def test_create_draft_recovers_rate_limited_post_without_duplicate_creation(tmp_path, monkeypatch) -> None:
    ctx = release_context(tmp_path)
    notes_path = tmp_path / "release-notes.md"
    calls = []
    states = iter([("absent", None), ("draft", 42)])

    def capture(command, **_):
        calls.append(command)
        raise ReleaseError("GitHub API rate limit exceeded")

    monkeypatch.setattr(release_publish, "capture_release_step", capture)
    monkeypatch.setattr(release_publish, "github_release_state", lambda _: next(states))
    with mock.patch.object(release_publish.time, "sleep") as sleep:
        assert release_publish.create_or_resume_draft_release(ctx, "Base v1.2.3", notes_path) == 42

    assert len(calls) == 1
    assert calls[0][:5] == ["gh", "api", "repos/basefoundry/base/releases", "--method", "POST"]
    sleep.assert_not_called()


def test_upload_accepts_a_response_lost_after_server_stored_asset(tmp_path, monkeypatch) -> None:
    ctx = release_context(tmp_path)
    asset = tmp_path / "release-bom.json"
    asset.write_bytes(b"reviewed BOM")
    names = iter([set(), {asset.name}])
    uploaded = []

    def capture(command, **_):
        uploaded.append(command)
        raise ReleaseError("upload connection closed")

    monkeypatch.setattr(release_publish, "capture_release_step", capture)
    monkeypatch.setattr(release_publish, "github_release_asset_names", lambda *_: next(names))
    verified = []
    monkeypatch.setattr(release_publish, "verify_release_assets", lambda _ctx, _id, assets: verified.extend(assets))

    release_publish.upload_and_verify_release_assets(ctx, 42, (asset,))

    assert len(uploaded) == 1
    assert uploaded[0][:3] == ["gh", "release", "upload"]
    assert verified == [asset]


def test_asset_readback_rejects_different_downloaded_bytes(tmp_path, monkeypatch) -> None:
    ctx = release_context(tmp_path)
    asset = tmp_path / "release-bom.json"
    asset.write_bytes(b"reviewed BOM")

    def download(command, **_):
        directory = Path(command[command.index("--dir") + 1])
        (directory / asset.name).write_bytes(b"tampered BOM")
        return ""

    monkeypatch.setattr(release_publish, "capture_github_step", download)
    with pytest.raises(ReleaseError, match="differs from the reviewed staged bytes"):
        release_publish.verify_downloaded_release_asset(ctx, asset)


def test_publish_draft_rechecks_state_and_publishes_successfully(tmp_path, monkeypatch) -> None:
    ctx = release_context(tmp_path)
    states = iter([("draft", 42), ("published", 42)])
    commands = []
    monkeypatch.setattr(release_publish, "github_release_state", lambda _: next(states))
    monkeypatch.setattr(release_publish, "capture_release_step", lambda command, **_: commands.append(command) or "")

    release_publish.publish_draft_release(ctx, 42)

    assert commands == [[
        "gh",
        "api",
        "repos/basefoundry/base/releases/42",
        "--method",
        "PATCH",
        "--field",
        "draft=false",
    ]]


def test_publish_recovery_reuses_existing_exact_local_and_remote_tags(tmp_path, monkeypatch) -> None:
    ctx = release_context(tmp_path)
    notes_path = tmp_path / "release-notes.md"
    publish = mock.Mock()
    run_step = mock.Mock()
    monkeypatch.setattr(engine, "local_tag_ref_exists", lambda *_: True)
    monkeypatch.setattr(engine, "verify_local_annotated_tag", mock.Mock())
    monkeypatch.setattr(engine, "inspect_remote_annotated_tag", lambda *_: "intended")
    monkeypatch.setattr(engine, "verify_remote_annotated_tag", mock.Mock())
    monkeypatch.setattr(engine, "run_release_step", run_step)
    monkeypatch.setattr(engine, "publish_and_verify_github_release", publish)

    engine.publish_release_from_staged_files(ctx, "Base v1.2.3", notes_path, "a" * 40, None)

    run_step.assert_not_called()
    publish.assert_called_once_with(ctx, "Base v1.2.3", notes_path, "a" * 40, None)
