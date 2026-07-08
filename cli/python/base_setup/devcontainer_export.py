from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from base_setup.manifest_model import BaseManifest


@dataclass(frozen=True)
class DevcontainerFinding:
    field: str
    reason: str


@dataclass(frozen=True)
class DevcontainerExport:
    project: str
    manifest_path: Path
    target_path: Path
    target_exists: bool
    write: bool
    devcontainer: dict[str, Any]
    supported: tuple[str, ...]
    unsupported: tuple[DevcontainerFinding, ...]
    ambiguous: tuple[DevcontainerFinding, ...]


class DevcontainerExportError(RuntimeError):
    pass


def build_devcontainer_export(manifest: BaseManifest, *, write: bool = False) -> DevcontainerExport:
    target_path = manifest.path.parent / ".devcontainer" / "devcontainer.json"
    devcontainer: dict[str, Any] = {"name": manifest.project_name}
    supported = ["project.name"]
    unsupported: list[DevcontainerFinding] = []
    ambiguous: list[DevcontainerFinding] = []

    vscode = manifest.ide.get("vscode")
    if vscode is not None:
        vscode_customizations: dict[str, Any] = {}
        if vscode.extensions:
            vscode_customizations["extensions"] = list(vscode.extensions)
            supported.append("ide.vscode.extensions")
        if vscode.settings:
            vscode_customizations["settings"] = vscode.settings
            supported.append("ide.vscode.settings")
        if vscode_customizations:
            devcontainer["customizations"] = {"vscode": vscode_customizations}

    for ide_name in sorted(set(manifest.ide) - {"vscode"}):
        unsupported.append(
            DevcontainerFinding(
                field=f"ide.{ide_name}",
                reason="Devcontainer export currently maps VS Code customizations only.",
            )
        )

    add_unsupported_manifest_findings(manifest, unsupported)
    add_ambiguous_manifest_findings(manifest, ambiguous)

    return DevcontainerExport(
        project=manifest.project_name,
        manifest_path=manifest.path,
        target_path=target_path,
        target_exists=target_path.exists(),
        write=write,
        devcontainer=devcontainer,
        supported=tuple(supported),
        unsupported=tuple(unsupported),
        ambiguous=tuple(ambiguous),
    )


def write_devcontainer_export(export: DevcontainerExport) -> None:
    if export.target_path.exists():
        raise DevcontainerExportError(
            f"{export.target_path} already exists; refusing to replace project-owned devcontainer file."
        )
    export.target_path.parent.mkdir(parents=True, exist_ok=True)
    export.target_path.write_text(dumps_devcontainer_json(export.devcontainer), encoding="utf-8")


def add_unsupported_manifest_findings(manifest: BaseManifest, findings: list[DevcontainerFinding]) -> None:
    if manifest.brewfile is not None:
        findings.append(
            DevcontainerFinding(
                field="brewfile",
                reason="Brewfile installation is host-specific and is not translated to devcontainer features yet.",
            )
        )
    if manifest.mise is not None:
        findings.append(
            DevcontainerFinding(
                field="mise",
                reason=(
                    "Project-owned mise configuration remains project-owned and is "
                    "not embedded in devcontainer output."
                ),
            )
        )
    for index, artifact in enumerate(manifest.artifacts, start=1):
        findings.append(
            DevcontainerFinding(
                field=f"artifacts[{index}]",
                reason=(
                    f"Base artifact {artifact.artifact_type}/{artifact.name} "
                    "does not have a devcontainer feature mapping yet."
                ),
            )
        )
    if manifest.test is not None:
        findings.append(
            DevcontainerFinding(
                field="test",
                reason=(
                    "Project test commands remain Base/project commands and are not "
                    "added to devcontainer lifecycle hooks."
                ),
            )
        )
    if manifest.health.required_env:
        findings.append(
            DevcontainerFinding(
                field="health.required_env",
                reason="Required environment variables are diagnostics, not container secrets.",
            )
        )
    if manifest.health.required_ports:
        findings.append(
            DevcontainerFinding(
                field="health.required_ports",
                reason="Port health checks are diagnostics and are not translated to devcontainer port forwarding yet.",
            )
        )
    if manifest.commands:
        findings.append(
            DevcontainerFinding(
                field="commands",
                reason=(
                    "Project commands stay in Base/project manifests and are not "
                    "copied into devcontainer lifecycle hooks."
                ),
            )
        )
    if manifest.activate.source:
        findings.append(
            DevcontainerFinding(
                field="activate.source",
                reason=(
                    "Activation source scripts are interactive shell behavior and "
                    "are not run by devcontainer export."
                ),
            )
        )
    if manifest.build is not None:
        findings.append(
            DevcontainerFinding(
                field="build",
                reason="Build targets remain Base/project commands and are not translated to devcontainer tasks.",
            )
        )


def add_ambiguous_manifest_findings(manifest: BaseManifest, findings: list[DevcontainerFinding]) -> None:
    if manifest.python.manager is not None:
        findings.append(
            DevcontainerFinding(
                field="python.manager",
                reason="Python manager selection may affect image choice, features, or post-create commands.",
            )
        )
    if manifest.python.requires_python is not None:
        findings.append(
            DevcontainerFinding(
                field="python.requires_python",
                reason="Python version constraints require an explicit image or feature policy before export.",
            )
        )


def devcontainer_export_to_json(export: DevcontainerExport) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project": export.project,
        "manifest_path": str(export.manifest_path),
        "target_path": str(export.target_path),
        "target_exists": export.target_exists,
        "write": export.write,
        "devcontainer": export.devcontainer,
        "supported": list(export.supported),
        "unsupported": [finding_to_json(finding) for finding in export.unsupported],
        "ambiguous": [finding_to_json(finding) for finding in export.ambiguous],
    }


def finding_to_json(finding: DevcontainerFinding) -> dict[str, str]:
    return {"field": finding.field, "reason": finding.reason}


def dumps_devcontainer_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def dumps_export_json(export: DevcontainerExport) -> str:
    return dumps_devcontainer_json(devcontainer_export_to_json(export))


def print_devcontainer_export_text(export: DevcontainerExport) -> None:
    mode = "write" if export.write else "dry-run"
    print(f"Devcontainer export for project '{export.project}'")
    print(f"Manifest: {export.manifest_path}")
    print(f"Target: {export.target_path}")
    print(f"Mode: {mode}")
    print()
    if export.write:
        print("Wrote devcontainer JSON.")
    else:
        print("Dry run: no files were written.")
    print()
    print("Generated devcontainer.json:")
    print(dumps_devcontainer_json(export.devcontainer), end="")
    print_devcontainer_findings("Unsupported fields", export.unsupported)
    print_devcontainer_findings("Ambiguous fields", export.ambiguous)


def print_devcontainer_findings(label: str, findings: tuple[DevcontainerFinding, ...]) -> None:
    if not findings:
        return
    print()
    print(f"{label}:")
    for finding in findings:
        print(f"- {finding.field}: {finding.reason}")
