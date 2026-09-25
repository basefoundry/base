from __future__ import annotations

import sys
from pathlib import Path

from base_setup.manifest import ManifestError
from base_setup.manifest import read_manifest


def repository_baseline_validation_file_for_manifest(manifest_path: Path) -> str:
    """Return the validation file selected by the repository baseline contract."""
    manifest = read_manifest(manifest_path)
    if manifest.project_name != "base":
        raise ManifestError(
            f"repository baseline validation is only defined for project.name 'base', got '{manifest.project_name}'"
        )
    if manifest.test is not None and manifest.test.command == "./bin/base-test":
        return "bin/base-test"
    return "tests/validate.sh"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: base_projects.manifest_contract <base_manifest.yaml>", file=sys.stderr)
        return 2
    try:
        print(repository_baseline_validation_file_for_manifest(Path(sys.argv[1])))
    except (ManifestError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
