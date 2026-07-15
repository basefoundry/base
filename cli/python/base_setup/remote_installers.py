from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlparse

import base_cli

from . import process
from .errors import ArtifactError


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class RemoteInstallerSpec:
    name: str
    display_name: str
    default_url: str
    interpreter: str
    trigger: str
    consent: str
    url_env: str | None = None
    sha256_env: str | None = None


@dataclass(frozen=True)
class RemoteInstallerSource:
    location: str
    expected_sha256: str | None
    managed: bool


CODEX_REMOTE_INSTALLER = RemoteInstallerSpec(
    name="codex",
    display_name="Codex CLI",
    default_url="https://chatgpt.com/codex/install.sh",
    interpreter="sh",
    trigger="Codex CLI is missing from the explicit ai prerequisite profile",
    consent="basectl setup --profile ai",
)
CLAUDE_REMOTE_INSTALLER = RemoteInstallerSpec(
    name="claude",
    display_name="Claude Code",
    default_url="https://claude.ai/install.sh",
    interpreter="bash",
    trigger="Claude Code is missing from the explicit ai prerequisite profile",
    consent="basectl setup --profile ai",
)
UV_REMOTE_INSTALLER = RemoteInstallerSpec(
    name="uv",
    display_name="uv",
    default_url="https://astral.sh/uv/install.sh",
    interpreter="sh",
    trigger="a Linux Debian-family manifest requires uv and uv is missing",
    consent="explicit basectl setup <project> --yes; --dry-run only previews",
    url_env="BASE_SETUP_UV_INSTALLER_URL",
    sha256_env="BASE_SETUP_UV_INSTALLER_SHA256",
)
MISE_REMOTE_INSTALLER = RemoteInstallerSpec(
    name="mise",
    display_name="mise",
    default_url="https://mise.run",
    interpreter="sh",
    trigger="a Linux Debian-family manifest declares mise and mise is missing",
    consent="explicit basectl setup <project> --yes; --dry-run only previews",
    url_env="BASE_SETUP_MISE_INSTALLER_URL",
    sha256_env="BASE_SETUP_MISE_INSTALLER_SHA256",
)

PYTHON_REMOTE_INSTALLERS = (
    CODEX_REMOTE_INSTALLER,
    CLAUDE_REMOTE_INSTALLER,
    UV_REMOTE_INSTALLER,
    MISE_REMOTE_INSTALLER,
)
_PYTHON_REMOTE_INSTALLERS_BY_NAME = {spec.name: spec for spec in PYTHON_REMOTE_INSTALLERS}


def require_registered_remote_installer(spec: RemoteInstallerSpec) -> None:
    if _PYTHON_REMOTE_INSTALLERS_BY_NAME.get(spec.name) != spec:
        raise ArtifactError(f"Remote installer '{spec.name}' is not registered in Base's installer policy.")


def resolve_remote_installer_source(
    spec: RemoteInstallerSpec,
    environ: Mapping[str, str] | None = None,
) -> RemoteInstallerSource:
    require_registered_remote_installer(spec)
    if spec.url_env is None or spec.sha256_env is None:
        return RemoteInstallerSource(spec.default_url, None, False)

    values = os.environ if environ is None else environ
    override_url = values.get(spec.url_env)
    override_sha256 = values.get(spec.sha256_env)
    if override_url is None and override_sha256 is None:
        return RemoteInstallerSource(spec.default_url, None, False)
    if not override_url or not override_sha256:
        raise ArtifactError(
            f"{spec.url_env} and {spec.sha256_env} must be set together to override the {spec.display_name} installer."
        )
    if SHA256_RE.fullmatch(override_sha256) is None:
        raise ArtifactError(f"{spec.sha256_env} must be exactly 64 hexadecimal characters.")
    _validate_installer_location(override_url, spec.url_env)
    return RemoteInstallerSource(override_url, override_sha256.lower(), True)


def run_remote_installer(
    ctx: base_cli.Context,
    spec: RemoteInstallerSpec,
    dry_run: bool,
    environ: Mapping[str, str] | None = None,
) -> None:
    source = resolve_remote_installer_source(spec, environ=environ)
    safe_location = process.redact_command_output(source.location)
    if source.managed:
        ctx.log.info(
            "Remote installer policy: %s uses managed source %s with required SHA-256 verification.",
            spec.display_name,
            safe_location,
        )
    else:
        ctx.log.info(
            "Remote installer policy: %s uses allowlisted official mutable installer %s without checksum verification.",
            spec.display_name,
            safe_location,
        )

    if dry_run:
        ctx.log.info(
            "[DRY-RUN] Would fetch %s once, execute the same bytes with %s, then remove the temporary copy.",
            safe_location,
            spec.interpreter,
        )
        if source.expected_sha256 is not None:
            ctx.log.info("[DRY-RUN] Would require installer SHA-256 %s.", source.expected_sha256)
        return

    with tempfile.TemporaryDirectory(prefix=f"base-{spec.name}-installer-") as temp_dir:
        installer_path = Path(temp_dir) / "installer.sh"
        _fetch_installer(ctx, source.location, installer_path)
        installer_path.chmod(0o600)
        actual_sha256 = _file_sha256(installer_path)
        if source.expected_sha256 is not None and actual_sha256 != source.expected_sha256:
            raise ArtifactError(
                f"{spec.display_name} installer SHA-256 mismatch: expected {source.expected_sha256}, "
                f"received {actual_sha256}. The installer was not executed."
            )
        if source.expected_sha256 is not None:
            ctx.log.info("Verified %s installer SHA-256 %s.", spec.display_name, actual_sha256)
        process.run_command(ctx, [spec.interpreter, str(installer_path)])


def _validate_installer_location(location: str, variable_name: str) -> None:
    parsed = urlparse(location)
    if not parsed.scheme:
        return
    if parsed.scheme.lower() == "https" and parsed.netloc:
        return
    if (
        parsed.scheme.lower() == "file"
        and parsed.netloc in ("", "localhost")
        and not parsed.query
        and not parsed.fragment
    ):
        return
    raise ArtifactError(f"{variable_name} must be a local path, file:// URL, or HTTPS URL.")


def _fetch_installer(ctx: base_cli.Context, location: str, destination: Path) -> None:
    parsed = urlparse(location)
    if parsed.scheme.lower() == "https":
        process.run_command(
            ctx,
            ["curl", "--proto", "=https", "--tlsv1.2", "-fsSL", "-o", str(destination), location],
        )
    else:
        source_path = Path(unquote(parsed.path)) if parsed.scheme.lower() == "file" else Path(location)
        try:
            shutil.copyfile(source_path, destination)
        except OSError as exc:
            raise ArtifactError(f"Unable to copy remote installer source '{source_path}': {exc}") from exc
    if not destination.is_file():
        safe_location = process.redact_command_output(location)
        raise ArtifactError(f"Remote installer source '{safe_location}' did not produce a file.")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as installer:
        for chunk in iter(lambda: installer.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
