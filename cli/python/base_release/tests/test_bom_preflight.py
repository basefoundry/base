"""Release BOM failures must be diagnosed before any publication mutation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from base_release import engine
from base_release.release_bom import canonical_bom_bytes, write_bom_digest_sidecar
from base_release.release_model import ReleaseContext, ReleaseError, ReleaseFinding
from base_release.release_parser import ReleaseArguments
from base_release.release_readiness import bom_finding
from base_release.tests._bom_fixtures import BASE_COMMIT, valid_bom_bytes
from base_release.tests.test_engine import run_engine


@pytest.fixture(name="publication")
def publication_fixture(tmp_path, monkeypatch):
    """Keep BOM validation real; isolate provenance, notes, and external writes."""
    bom = tmp_path / "candidate.json"
    bom.write_bytes(valid_bom_bytes("basefoundry/base", "1.9.0", BASE_COMMIT))
    write_bom_digest_sidecar(bom)
    ctx = ReleaseContext(
        manifest_path=tmp_path / "base_manifest.yaml",
        manifest=SimpleNamespace(project_name="base"),
        release=SimpleNamespace(
            github=SimpleNamespace(repository="basefoundry/base", release_title="Base v{version}"),
            bom=SimpleNamespace(required=True), homebrew=None,
        ),
        version="1.9.0", tag_name="v1.9.0", version_file=tmp_path / "VERSION",
        changelog=tmp_path / "CHANGELOG.md", bom_path=bom,
    )
    commands = []
    monkeypatch.setattr(engine, "release_findings", lambda context: (bom_finding(context, BASE_COMMIT),))
    monkeypatch.setattr(engine, "github_release_finding", lambda _: ReleaseFinding("ok", "github_release", "ready"))
    monkeypatch.setattr(engine, "require_release_provenance", lambda _: BASE_COMMIT)
    monkeypatch.setattr(engine, "extract_changelog_section", lambda *_: "Fixture release")
    monkeypatch.setattr(engine, "verify_local_annotated_tag", lambda *_: None)
    monkeypatch.setattr(engine, "verify_remote_annotated_tag", lambda *_: None)
    monkeypatch.setattr(engine, "verify_github_release", lambda *_, **__: None)
    monkeypatch.setattr(engine, "run_release_step", lambda command, **_: commands.append(command))
    monkeypatch.setattr("base_release.release_publish.run_release_step", lambda command, **_: commands.append(command))
    return ctx, commands


def invoke_mode(ctx, mode):
    if mode == "check":
        return engine.release_check_command(ctx, output_format="json")
    return engine.release_publish_command(ctx, ReleaseArguments(
        command="publish", version=ctx.version, manifest_path=ctx.manifest_path,
        bom_path=ctx.bom_path, yes=True, dry_run=mode == "dry-run",
    ))


@pytest.mark.parametrize("mode", ["check", "dry-run", "publish"])
@pytest.mark.parametrize("problem", [
    "digest_mismatch", "malformed_sidecar", "sidecar_encoding", "bom_encoding",
    "sidecar_directory", "bom_permission", "sidecar_permission", "dangling_sidecar",
])
def test_invalid_bom_pair_blocks_every_mode_before_mutation(publication, monkeypatch, capsys, mode, problem):
    ctx, commands = publication
    bom = ctx.bom_path
    sidecar = bom.with_suffix(".sha256")
    if problem == "digest_mismatch":
        sidecar.write_text(f"{'0' * 64}  {bom.name}\n", encoding="utf-8")
    elif problem == "malformed_sidecar":
        sidecar.write_text("not a digest\n", encoding="utf-8")
    elif problem == "sidecar_encoding":
        sidecar.write_bytes(b"\xff")
    elif problem == "bom_encoding":
        bom.write_bytes(b"\xff")
    elif problem == "sidecar_directory":
        sidecar.unlink()
        sidecar.mkdir()
    elif problem == "dangling_sidecar":
        sidecar.unlink()
        sidecar.symlink_to(sidecar.parent / "absent-digest")
    elif problem == "sidecar_permission":
        original_text = Path.read_text

        def denied_text(path, *args, **kwargs):
            if path == sidecar:
                raise PermissionError("fixture sidecar is unreadable")
            return original_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", denied_text)
    else:
        original = Path.read_bytes

        def denied_read(path):
            if path == bom:
                raise PermissionError("fixture BOM is unreadable")
            return original(path)

        monkeypatch.setattr(Path, "read_bytes", denied_read)

    assert invoke_mode(ctx, mode) == 1
    assert not commands
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out + captured.err
    if mode == "check":
        payload = json.loads(captured.out)
        assert payload["status"] == "error"
        assert payload["data"]["findings"][0]["name"] == "bom"


@pytest.mark.parametrize("mode", ["check", "dry-run", "publish"])
@pytest.mark.parametrize("sidecar_present", [True, False])
def test_valid_pair_and_legacy_bom_succeed(publication, mode, sidecar_present):
    ctx, commands = publication
    if not sidecar_present:
        ctx.bom_path.with_suffix(".sha256").unlink()
    assert invoke_mode(ctx, mode) == 0
    if mode != "publish":
        assert not commands
    else:
        assert commands[0][:3] == ["git", "tag", "-a"]
        assert commands[-1][:3] == ["gh", "release", "upload"]


def test_publish_uses_prevalidated_snapshot_after_input_disappears(publication, monkeypatch):
    ctx, commands = publication
    expected = ctx.bom_path.read_bytes()
    uploaded = {}

    def run_step(command, **_):
        commands.append(command)
        if command[:3] == ["git", "tag", "-a"]:
            ctx.bom_path.unlink()
            ctx.bom_path.with_suffix(".sha256").unlink()
        if command[:3] == ["gh", "release", "upload"]:
            uploaded.update({Path(path).name: Path(path).read_bytes() for path in command[4:6]})

    monkeypatch.setattr(engine, "run_release_step", run_step)
    monkeypatch.setattr("base_release.release_publish.run_release_step", run_step)
    assert invoke_mode(ctx, "publish") == 0
    assert uploaded["release-bom.json"] == expected
    assert uploaded["release-bom.sha256"] == (
        f"{hashlib.sha256(expected).hexdigest()}  release-bom.json\n".encode()
    )


def test_bom_staging_failure_is_a_domain_error_before_tagging(publication, monkeypatch):
    ctx, commands = publication
    original = Path.write_bytes

    def denied_write(path, content):
        if path.name == "release-bom.json":
            raise OSError("fixture staging disk is full")
        return original(path, content)

    monkeypatch.setattr(Path, "write_bytes", denied_write)
    with pytest.raises(ReleaseError, match="staging disk is full"):
        invoke_mode(ctx, "publish")
    assert not commands


def test_publish_revalidates_identity_after_readiness_before_tagging(publication, monkeypatch):
    ctx, commands = publication

    def final_provenance(_):
        document = json.loads(ctx.bom_path.read_bytes())
        document["release"]["commit"] = "c" * 40
        ctx.bom_path.write_bytes(canonical_bom_bytes(document))
        write_bom_digest_sidecar(ctx.bom_path)
        return BASE_COMMIT

    monkeypatch.setattr(engine, "require_release_provenance", final_provenance)
    with pytest.raises(ReleaseError, match="release.commit"):
        invoke_mode(ctx, "publish")
    assert not commands


def test_governed_release_recovery_requires_the_reviewed_asset_pair(publication, monkeypatch):
    ctx, _ = publication

    def failed_create(command, **_):
        if command[:3] == ["gh", "release", "create"]:
            raise ReleaseError("fixture release creation failed")

    monkeypatch.setattr(engine, "run_release_step", failed_create)
    with pytest.raises(ReleaseError) as failure:
        invoke_mode(ctx, "publish")
    assert "release-bom.json" in failure.value.guidance
    assert "release-bom.sha256" in failure.value.guidance
    assert "reviewed" in failure.value.guidance
    assert "verify" in failure.value.guidance.lower()


@pytest.mark.parametrize("mode", ["check", "dry-run", "publish"])
def test_public_command_reports_invalid_sidecar_without_traceback(
    tmp_path, manifest_factory, monkeypatch, mode,
):
    manifest_path = manifest_factory.write_release(tmp_path)
    bom = tmp_path / "candidate.json"
    bom.write_bytes(valid_bom_bytes("codeforester/demo", "1.2.3", BASE_COMMIT))
    bom.with_suffix(".sha256").write_bytes(b"\xff")
    commands = []
    monkeypatch.setattr(engine, "release_findings", lambda context: (bom_finding(context, BASE_COMMIT),))
    monkeypatch.setattr(engine, "run_release_step", lambda command, **_: commands.append(command))
    args = ["check", "--format", "json"] if mode == "check" else ["publish", "--yes"]
    if mode == "dry-run":
        args.append("--dry-run")
    status, stdout, stderr = run_engine(
        [*args, "--version", "1.2.3", "--manifest", str(manifest_path), "--bom", str(bom)], tmp_path,
    )
    assert status == 1
    assert not commands
    assert "Traceback" not in stdout + stderr
    assert "digest sidecar is invalid" in stdout
    if mode == "check":
        assert json.loads(stdout)["status"] == "error"
        assert stderr == ""
