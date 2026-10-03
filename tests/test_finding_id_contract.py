from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FINDING_ID = re.compile(r"BASE-[A-Z][0-9]+")


def test_production_finding_ids_are_registered() -> None:
    registry = set(FINDING_ID.findall((REPO_ROOT / "docs/doctor-findings.md").read_text(encoding="utf-8")))
    emitted: set[str] = set()
    for root in (REPO_ROOT / "cli/python", REPO_ROOT / "cli/bash", REPO_ROOT / "bin"):
        for path in root.rglob("*"):
            if not path.is_file() or "tests" in path.parts:
                continue
            emitted.update(FINDING_ID.findall(path.read_text(encoding="utf-8", errors="ignore")))

    assert emitted <= registry, sorted(emitted - registry)
