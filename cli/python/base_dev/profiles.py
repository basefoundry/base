from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_setup.artifacts import resolve_artifact_definitions
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError
from base_setup.manifest_model import BaseManifest
from base_setup.registry import ArtifactDefinition

SUPPORTED_PROFILES = ("dev", "sre", "ai", "linux-lab")


@dataclass(frozen=True)
class ProfileManifest:
    name: str
    manifest: BaseManifest
    definitions: tuple[ArtifactDefinition, ...]


@dataclass(frozen=True)
class ProfileRuntime:
    profile: str
    project: str


class ProfileError(ValueError):
    pass


def normalize_profiles(profiles: tuple[str, ...]) -> tuple[str, ...]:
    if not profiles:
        return ("dev",)

    normalized: list[str] = []
    for profile_list in profiles:
        for raw_profile in profile_list.split(","):
            profile = raw_profile.strip().lower()
            if not profile:
                raise ProfileError("Profile list must not contain empty entries.")
            if profile not in SUPPORTED_PROFILES:
                display_profile = raw_profile.strip() or raw_profile
                raise ProfileError(
                    f"Unsupported profile '{display_profile}'. Expected one of: {', '.join(SUPPORTED_PROFILES)}."
                )
            if profile not in normalized:
                normalized.append(profile)
    return tuple(normalized)


def read_profile_manifests(ctx: base_cli.Context, profiles: tuple[str, ...]) -> tuple[ProfileManifest, ...]:
    profile_manifests: list[ProfileManifest] = []
    for profile in profiles:
        if profile in {"ai", "linux-lab"}:
            continue
        manifest = read_profile_manifest(ctx, profile)
        definitions = resolve_artifact_definitions(manifest.artifacts)
        profile_manifests.append(ProfileManifest(profile, manifest, definitions))
    return tuple(profile_manifests)


def read_profile_manifest(ctx: base_cli.Context, profile: str) -> BaseManifest:
    if ctx.base_home is None:
        raise ManifestError("BASE_HOME is required to load Base's prerequisite profile manifests.")
    return read_manifest(profile_manifest_path(ctx.base_home, profile))


def read_dev_manifest(ctx: base_cli.Context) -> BaseManifest:
    if ctx.base_home is None:
        raise ManifestError("BASE_HOME is required to load Base's developer prerequisite manifest.")
    return read_profile_manifest(ctx, "dev")


def dev_manifest_path(base_home: Path) -> Path:
    return base_home / "lib" / "base" / "dev_manifest.yaml"


def profile_manifest_path(base_home: Path, profile: str) -> Path:
    if profile == "dev":
        return dev_manifest_path(base_home)
    return base_home / "lib" / "base" / f"{profile}_manifest.yaml"
