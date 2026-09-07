from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .release_bom import ReleaseBomError, bom_digest, load_bom, validate_bom

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


def assemble(args: argparse.Namespace) -> dict:
    try:
        components = [load_bom(path) for path in args.component]
        combinations = [json.loads(value) for value in args.combination]
    except (ReleaseBomError, json.JSONDecodeError) as exc:
        raise ReleaseBomError(f"cannot assemble BOM inputs: {exc}") from exc
    document = {
        "schema_version": 1,
        "release": {
            "repository": args.repository,
            "version": args.version,
            "tag": f"v{args.version}",
            "commit": args.commit,
        },
        "components": components,
        "combinations": combinations,
    }
    validate_bom(
        document,
        expected_repository=args.repository,
        expected_version=args.version,
        expected_commit=args.commit,
    )
    return document


def main() -> int:
    parser = argparse.ArgumentParser(prog="base-release-bom")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate a release BOM")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--repository")
    validate_parser.add_argument("--version")
    validate_parser.add_argument("--commit")
    digest_parser = subparsers.add_parser("digest", help="print the canonical BOM SHA-256")
    digest_parser.add_argument("path", type=Path)
    assemble_parser = subparsers.add_parser("assemble", help="assemble and validate a release BOM")
    assemble_parser.add_argument("--repository", required=True)
    assemble_parser.add_argument("--version", required=True)
    assemble_parser.add_argument("--commit", required=True)
    assemble_parser.add_argument("--component", action="append", type=Path, required=True)
    assemble_parser.add_argument(
        "--combination",
        action="append",
        required=True,
        help="JSON object describing one provider/consumer combination",
    )
    assemble_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            document = load_bom(args.path)
            validate_bom(
                document,
                expected_repository=args.repository,
                expected_version=args.version,
                expected_commit=args.commit,
            )
            print(f"release BOM is valid: {args.path}")
            print(f"sha256: {bom_digest(document)}")
        elif args.command == "digest":
            document = load_bom(args.path)
            print(bom_digest(document))
        else:
            assembled = assemble(args)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(assembled, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"release BOM assembled and validated: {args.output}")
            print(f"sha256: {bom_digest(assembled)}")
    except ReleaseBomError as exc:
        print(f"release BOM check: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
