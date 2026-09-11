from __future__ import annotations

from typing import Any

from base_release.release_bom import canonical_bom_bytes


BASE_COMMIT = "a" * 40


# pylint: disable=too-many-arguments
def valid_bom(
    *,
    repository: str = "basefoundry/base",
    version: str = "1.9.0",
    commit: str = BASE_COMMIT,
    component_evidence: str = "run://base/123",
    combination_name: str = "base-release-stack-ubuntu-24.04",
    combination_evidence: str | None = None,
) -> dict[str, Any]:
    if combination_evidence is None:
        combination_evidence = component_evidence
    return {
        "schema_version": 1,
        "release": {
            "repository": repository,
            "version": version,
            "tag": f"v{version}",
            "commit": commit,
        },
        "components": [
            {
                "repository": repository,
                "version": version,
                "tag": f"v{version}",
                "commit": commit,
                "source_mode": "release",
                "api_schema_version": "manifest-1",
                "platforms": ["macos-14", "ubuntu-24.04"],
                "required": True,
                "result": "passed",
                "evidence": component_evidence,
            },
            {
                "repository": "basefoundry/base-cli",
                "version": "0.4.3",
                "tag": "v0.4.3",
                "commit": "b" * 40,
                "source_mode": "release",
                "api_schema_version": "base-cli-api@0.4.3",
                "platforms": ["macos-14", "ubuntu-24.04"],
                "required": True,
                "result": "passed",
                "evidence": "run://base-cli/123",
            },
        ],
        "combinations": [
            {
                "name": combination_name,
                "participants": [repository, "basefoundry/base-cli"],
                "platform": "ubuntu-24.04",
                "required": True,
                "result": "passed",
                "evidence": combination_evidence,
            }
        ],
    }


def valid_bom_bytes(repository: str, version: str, commit: str) -> bytes:
    return canonical_bom_bytes(
        valid_bom(
            repository=repository,
            version=version,
            commit=commit,
            component_evidence="run://release/123",
            combination_name="release-stack-ubuntu-24.04",
            combination_evidence="run://release/123",
        )
    )
