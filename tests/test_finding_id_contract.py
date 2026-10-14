from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FINDING_ID = re.compile(r"BASE-[A-Z][0-9]+")


def production_finding_ids(root: Path) -> set[str]:
    emitted: set[str] = set()
    for source_root in (root / "cli/python", root / "cli/bash", root / "bin"):
        for path in source_root.rglob("*"):
            if (
                not path.is_file()
                or "tests" in path.parts
                or "__pycache__" in path.parts
                or path.suffix.lower() in {".pyc", ".pyo"}
            ):
                continue
            emitted.update(FINDING_ID.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return emitted


def test_production_finding_ids_are_registered() -> None:
    registry = set(FINDING_ID.findall((REPO_ROOT / "docs/doctor-findings.md").read_text(encoding="utf-8")))
    emitted = production_finding_ids(REPO_ROOT)

    assert emitted <= registry, sorted(emitted - registry)


def test_generated_bytecode_cannot_add_finding_ids(tmp_path: Path) -> None:
    (tmp_path / "cli/python/pkg/__pycache__").mkdir(parents=True)
    (tmp_path / "cli/bash").mkdir(parents=True)
    (tmp_path / "bin").mkdir()
    (tmp_path / "cli/python/pkg/__pycache__/stale.pyc").write_bytes(b"BASE-D000")
    (tmp_path / "cli/python/pkg/source.py").write_text("BASE-P010\n", encoding="utf-8")

    assert production_finding_ids(tmp_path) == {"BASE-P010"}
