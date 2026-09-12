from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from base_cli.testing import invoke
from base_trust import engine


@pytest.mark.parametrize("revision", ["manifest", "requirements"])
def test_project_revoke_removes_all_contract_revisions(
    tmp_path: Path, manifest_factory, revision: str,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    manifest = manifest_factory.write(workspace / "demo")
    manifest.write_text(manifest.read_text().replace(
        "  command: pytest tests/", "  requirements: requirements.txt\n  command: pytest tests/",
    ))
    requirements = manifest.parent / "requirements.txt"
    original = manifest.read_text()
    store = engine.ManifestCommandTrustStore(home)
    contracts = []
    for index in range(4):
        manifest.write_text(original + (f"# revision {index}\n" if revision == "manifest" else ""))
        requirements.write_text(f"fixture=={index if revision == 'requirements' else 0}.0\n")
        identity = engine.compute_trust_identity_for_manifest(manifest)
        store.allow(identity, base_version="fixture")
        contracts.append((manifest.read_text(), requirements.read_text(), identity))

    unrelated = engine.compute_trust_identity_for_manifest(
        manifest_factory.write(tmp_path / "other-workspace" / "demo"),
    )
    store.allow(unrelated, base_version="fixture")
    result = invoke(engine.app, ["revoke", "demo", "--workspace", str(workspace)], home=home)
    assert result.exit_code == 0, result.output
    assert "Revoked manifest command trust" in result.stdout
    for manifest_text, requirements_text, identity in contracts:
        manifest.write_text(manifest_text)
        requirements.write_text(requirements_text)
        assert not store.status(identity).is_allowed
        result = invoke(engine.app, ["require", "demo", "--manifest", str(manifest)], home=home)
        assert result.exit_code == 1, result.output
    assert store.status(unrelated).is_allowed
    assert not store.revoke(contracts[-1][2])


def test_revoke_preserves_unidentified_records_and_external_symlink_target(
    tmp_path: Path, manifest_factory,
) -> None:
    identity = engine.compute_trust_identity_for_manifest(manifest_factory.write(tmp_path / "demo"))
    store = engine.ManifestCommandTrustStore(tmp_path / "home")
    record = store.allow(identity, base_version="fixture")
    external = tmp_path / "external.json"
    external.write_bytes(record.read_bytes())
    alias = store.root / "alias.json"
    alias.symlink_to(external)
    invalid_records = [b"[]", b"null", b"{", b"\xff", b'{"schema_version":1,"project":[]}']
    invalid_paths = []
    for index, data in enumerate(invalid_records):
        path = store.root / f"invalid-{index}.json"
        path.write_bytes(data)
        invalid_paths.append(path)
    assert store.revoke(identity)
    assert not record.exists()
    assert not alias.is_symlink()
    assert external.is_file()
    assert all(path.is_file() for path in invalid_paths)


def test_malformed_identity_record_cannot_remain_an_effective_approval(
    tmp_path: Path, manifest_factory,
) -> None:
    identity = engine.compute_trust_identity_for_manifest(manifest_factory.write(tmp_path / "demo"))
    store = engine.ManifestCommandTrustStore(tmp_path / "home")
    record = store.allow(identity, base_version="fixture")
    record.write_text(json.dumps({"schema_version": 1, "project": {"root": "unknown"}}))
    assert not store.status(identity).is_allowed


@pytest.mark.parametrize("operation", ["delete", "list", "read"])
def test_revoke_reports_store_errors_without_claiming_success(
    tmp_path: Path, manifest_factory, monkeypatch: pytest.MonkeyPatch, operation: str,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    identity = engine.compute_trust_identity_for_manifest(manifest_factory.write(workspace / "demo"))
    store = engine.ManifestCommandTrustStore(home)
    record = store.allow(identity, base_version="fixture")
    owner, method = (os, "scandir") if operation == "list" else (
        Path, "unlink" if operation == "delete" else "read_text",
    )
    original = getattr(owner, method)
    denied = store.root if operation == "list" else record

    def refuse_record(path, *args, **kwargs):
        if str(path) == str(denied):
            raise PermissionError("fixture store access denied")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(owner, method, refuse_record)
        result = invoke(engine.app, ["revoke", "demo", "--workspace", str(workspace)], home=home)
    assert result.exit_code == 1
    assert "Unable to revoke" in result.stderr
    assert "fixture store access denied" in result.stderr
    assert "Revoked manifest command trust" not in result.stdout
    assert store.status(identity).is_allowed
