from __future__ import annotations

import os

from .checks import ArtifactCheck
from .manifest import BaseManifest


def check_required_env(manifest: BaseManifest) -> list[ArtifactCheck]:
    return [check_required_env_var(env_name) for env_name in manifest.health.required_env]


def check_required_env_var(env_name: str) -> ArtifactCheck:
    if os.environ.get(env_name, ""):
        return ArtifactCheck(
            name=env_name,
            ok=True,
            message=f"Environment variable '{env_name}' is set.",
            fix="",
            finding_id="BASE-H001",
        )
    return ArtifactCheck(
        name=env_name,
        ok=False,
        message=f"Environment variable '{env_name}' is not set or is empty.",
        fix=f"Set {env_name} in your shell, .env, or secrets manager.",
        finding_id="BASE-H001",
    )
