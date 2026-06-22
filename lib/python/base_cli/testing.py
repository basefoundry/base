from __future__ import annotations

import inspect
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any


# pylint: disable=too-many-arguments
def invoke(
    app: Any,
    args: list[str] | None = None,
    home: Path | None = None,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    *,
    manifest: Mapping[str, Any] | None = None,
):
    cwd_path = Path(cwd) if cwd is not None else None
    if manifest is not None:
        if cwd_path is None:
            raise ValueError("manifest requires cwd so base_manifest.yaml has a target directory.")
        _write_manifest_fixture(cwd_path, manifest)

    try:
        from click.testing import CliRunner
    except ImportError as exc:
        raise RuntimeError("Click is required for base_cli.testing. Run 'basectl setup' to install it.") from exc

    invoke_env = dict(env or {})
    if home is not None:
        invoke_env.setdefault("HOME", str(home))
        invoke_env.setdefault("BASE_CACHE_DIR", str(home / ".cache" / "base"))
    runner_kwargs = {}
    if "mix_stderr" in inspect.signature(CliRunner).parameters:
        runner_kwargs["mix_stderr"] = False
    runner = CliRunner(**runner_kwargs)
    original_cwd = Path.cwd()
    if cwd_path is not None:
        os.chdir(cwd_path)
    try:
        return runner.invoke(app.click_command, args or [], env=invoke_env)
    finally:
        if cwd_path is not None:
            os.chdir(original_cwd)


def _write_manifest_fixture(cwd: Path, manifest: Mapping[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to write base_cli.testing manifest fixtures.") from exc

    (cwd / "base_manifest.yaml").write_text(
        yaml.safe_dump(dict(manifest), sort_keys=False),
        encoding="utf-8",
    )
