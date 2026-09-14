"""Machine-local key validation must remain usable through the public diagnostics."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from base_cli import ConfigurationError
from base_cli.testing import invoke
from base_cli_adapters.config import read_user_config, user_config_path
from base_config import engine


SECTIONS = ("workspace", "github", "ide", "ide.vscode")
INVALID_MAPPINGS = (
    pytest.param({1: "value"}, id="numeric"),
    pytest.param({True: "value"}, id="boolean"),
    pytest.param({None: "value"}, id="null"),
    pytest.param({1: "value", "unexpected": "value"}, id="mixed"),
    pytest.param({"": "value"}, id="empty-string"),
    pytest.param({"  ": "value"}, id="blank-string"),
)


def write_config(home: Path, section: str, mapping: dict) -> Path:
    payload = {"ide": {"vscode": mapping}} if section == "ide.vscode" else {section: mapping}
    path = user_config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


@pytest.mark.parametrize("section", SECTIONS)
@pytest.mark.parametrize("mapping", INVALID_MAPPINGS)
def test_reader_and_doctor_reject_malformed_keys_without_rewriting(
    tmp_path, monkeypatch, capsys, section, mapping,
):
    path = write_config(tmp_path, section, mapping)
    original = path.read_bytes()
    message = f"{section} keys must be non-empty strings"
    with pytest.raises(ConfigurationError) as failure:
        read_user_config(tmp_path)
    assert str(path) in str(failure.value)
    assert message in str(failure.value)

    monkeypatch.setenv("HOME", str(tmp_path))
    assert engine.doctor_config_command() == 1
    captured = capsys.readouterr()
    assert message in captured.out
    assert "Traceback" not in captured.out + captured.err

    result = invoke(engine.app, ["doctor"], home=tmp_path)
    assert result.exit_code != 0
    assert message in result.output
    assert str(path) in result.output
    assert "Traceback" not in result.output
    assert "TypeError" not in result.output
    assert path.read_bytes() == original


@pytest.mark.parametrize("section", SECTIONS)
def test_unknown_string_keys_keep_precise_sorted_errors(tmp_path, section):
    path = write_config(tmp_path, section, {"zeta": "value", "alpha": "value"})
    original = path.read_bytes()
    with pytest.raises(ConfigurationError) as failure:
        read_user_config(tmp_path)
    message = str(failure.value)
    assert str(path) in message
    assert "unsupported" in message
    assert "alpha, zeta" in message
    assert path.read_bytes() == original


def test_absent_config_keeps_empty_defaults_and_remains_absent(tmp_path):
    config = read_user_config(tmp_path)
    assert config.workspace.root is None
    assert config.github.default_owner is None
    assert not config.ide.preferences
    result = invoke(engine.app, ["doctor"], home=tmp_path)
    assert result.exit_code == 0, result.output
    assert not user_config_path(tmp_path).exists()


@pytest.mark.parametrize("symlink", [False, True])
def test_valid_mapping_and_symlink_semantics_are_preserved(tmp_path, symlink):
    workspace = tmp_path / "work"
    workspace.mkdir()
    payload = {
        "workspace": {"root": str(workspace), "manifest": None},
        "github": {"default_owner": "example", "clone_protocol": "https"},
        "ide": {"vscode": {"enabled": False, "install": None, "settings": {"editor.fontSize": 14}}},
    }
    path = user_config_path(tmp_path)
    path.parent.mkdir()
    target = tmp_path / "synced-config.yaml" if symlink else path
    original = yaml.safe_dump(payload).encode()
    target.write_bytes(original)
    if symlink:
        path.symlink_to(target)

    config = read_user_config(tmp_path)
    assert config.workspace.root == workspace.resolve()
    assert config.workspace.manifest is None
    assert config.github.default_owner == "example"
    assert config.github.clone_protocol == "https"
    assert config.ide.preferences["vscode"].enabled is False
    assert config.ide.preferences["vscode"].install is None
    assert config.ide.preferences["vscode"].settings == {"editor.fontSize": 14}
    result = invoke(engine.app, ["doctor"], home=tmp_path)
    assert result.exit_code == 0, result.output
    assert path.is_symlink() == symlink
    assert target.read_bytes() == original
