from __future__ import annotations

import os
import socket

from .checks import ArtifactCheck
from .manifest import BaseManifest
from .manifest import PortHealthConfig


def check_required_env(manifest: BaseManifest) -> list[ArtifactCheck]:
    return [check_required_env_var(env_name) for env_name in manifest.health.required_env]


def check_required_ports(manifest: BaseManifest) -> list[ArtifactCheck]:
    return [check_required_port(port_config) for port_config in manifest.health.required_ports]


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


def check_required_port(port_config: PortHealthConfig) -> ArtifactCheck:
    label = port_config.name or f"{port_config.host}:{port_config.port}"
    endpoint = f"{port_config.host}:{port_config.port}"
    listening = tcp_port_is_listening(port_config.host, port_config.port)

    if port_config.state == "listening":
        if listening:
            return ArtifactCheck(
                name=label,
                ok=True,
                message=f"TCP port '{label}' is listening on {endpoint}.",
                fix="",
                finding_id="BASE-H002",
            )
        return ArtifactCheck(
            name=label,
            ok=False,
            message=f"TCP port '{label}' is not listening on {endpoint}.",
            fix=f"Start the service that should listen on {endpoint}.",
            finding_id="BASE-H002",
        )

    if not listening:
        return ArtifactCheck(
            name=label,
            ok=True,
            message=f"TCP port '{label}' is free on {endpoint}.",
            fix="",
            finding_id="BASE-H002",
        )
    return ArtifactCheck(
        name=label,
        ok=False,
        message=f"TCP port '{label}' is already listening on {endpoint}.",
        fix=f"Stop the process using {endpoint} or choose a different project port.",
        finding_id="BASE-H002",
    )


def tcp_port_is_listening(host: str, port: int, timeout_seconds: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False
