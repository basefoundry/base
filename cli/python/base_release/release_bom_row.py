from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
EXIT_SUCCESS = 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="bin/base-release-bom-row")
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--platform", action="append", dest="platforms", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not VERSION_RE.fullmatch(args.version):
        parser.error("--version must be a stable SemVer value")
    if not SHA_RE.fullmatch(args.commit):
        parser.error("--commit must be a lowercase full 40-character SHA")
    document = {
        "repository": "basefoundry/base",
        "version": args.version,
        "tag": f"v{args.version}",
        "commit": args.commit,
        "source_mode": "release",
        "api_schema_version": "manifest-1",
        "platforms": sorted(set(args.platforms)),
        "required": True,
        "result": "passed",
        "evidence": args.evidence,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
