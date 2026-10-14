#!/usr/bin/env python3
"""Check a repository's public version surfaces against its authoritative version.

The contract is intentionally configuration-driven so each independently
released repository can declare its own authoritative file and public surfaces
without copying repository-specific checks into the release workflow.
"""

# The contract validator keeps schema checks together so its file-specific
# findings remain easy to audit.
# pylint: disable=too-many-branches,too-many-statements,too-many-return-statements

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PureWindowsPath
from typing import Any


SEMVER_RE = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Finding:
    status: str
    name: str
    message: str


def finding(status: str, name: str, message: str) -> Finding:
    return Finding(status=status, name=name, message=message)


def safe_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = Path(value)
    return not path.is_absolute() and not PureWindowsPath(value).is_absolute() and ".." not in path.parts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository checkout to inspect (default: the checkout containing this script).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Contract JSON (default: <root>/.release/version-consistency.json).",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Expected SemVer; defaults to the authoritative version in the checkout.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def load_json(path: Path) -> tuple[Any | None, list[Finding]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as exc:
        return None, [finding("error", "config", f"Unable to read {path}: {exc}")]


def validate_config(data: Any) -> list[Finding]:
    if not isinstance(data, dict):
        return [finding("error", "config", "The version-consistency contract must be a JSON object.")]

    findings: list[Finding] = []
    if data.get("schema_version") != 1:
        findings.append(finding("error", "config_schema", "schema_version must be 1."))

    authority = data.get("authority")
    if not isinstance(authority, dict) or not safe_relative_path(authority.get("path")):
        findings.append(finding("error", "authority", "authority.path must be a repository-relative path."))

    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        findings.append(finding("error", "surfaces", "surfaces must be a non-empty list."))
    else:
        names: set[str] = set()
        for index, surface in enumerate(surfaces):
            label = f"surface_{index + 1}"
            if not isinstance(surface, dict):
                findings.append(finding("error", label, "surface must be an object."))
                continue
            name = surface.get("name")
            path = surface.get("path")
            contains = surface.get("must_contain")
            if not isinstance(name, str) or not name:
                findings.append(finding("error", label, "surface.name must be a non-empty string."))
            elif name in names:
                findings.append(finding("error", label, f"duplicate surface name: {name}."))
            else:
                names.add(name)
            if not safe_relative_path(path):
                findings.append(finding("error", label, "surface.path must be a relative path."))
            exception = surface.get("exception")
            if exception is not None and (not isinstance(exception, str) or not exception):
                findings.append(finding("error", label, "surface.exception must name an active exception."))
            if (
                not isinstance(contains, list)
                or not contains
                or not all(isinstance(item, str) for item in contains)
            ):
                findings.append(finding("error", label, "surface.must_contain must be a non-empty string list."))

    exceptions = data.get("exceptions", [])
    if not isinstance(exceptions, list):
        findings.append(finding("error", "exceptions", "exceptions must be a list when present."))
    else:
        names = set()
        today = dt.date.today()
        for index, exception in enumerate(exceptions):
            label = f"exception_{index + 1}"
            if not isinstance(exception, dict):
                findings.append(finding("error", label, "exception must be an object."))
                continue
            name = exception.get("name")
            path = exception.get("path")
            reason = exception.get("reason")
            expires = exception.get("expires")
            if not isinstance(name, str) or not name:
                findings.append(finding("error", label, "exception.name must be a non-empty string."))
            elif name in names:
                findings.append(finding("error", label, f"duplicate exception name: {name}."))
            else:
                names.add(name)
            if not safe_relative_path(path):
                findings.append(finding("error", label, "exception.path must be a relative path."))
            if not isinstance(reason, str) or not reason.strip():
                findings.append(finding("error", label, "exception.reason is required."))
            if not isinstance(expires, str) or not DATE_RE.fullmatch(expires):
                findings.append(finding("error", label, "exception.expires must be YYYY-MM-DD."))
            else:
                try:
                    if dt.date.fromisoformat(expires) < today:
                        findings.append(finding("error", label, f"exception {name!r} expired on {expires}."))
                except ValueError:
                    findings.append(finding("error", label, f"exception {name!r} has an invalid expiry date."))
        exception_names = {
            exception.get("name")
            for exception in exceptions
            if isinstance(exception, dict) and isinstance(exception.get("name"), str)
        }
        exception_paths = {
            exception.get("name"): exception.get("path")
            for exception in exceptions
            if isinstance(exception, dict) and isinstance(exception.get("name"), str)
        }
        surface_items = surfaces if isinstance(surfaces, list) else []
        referenced_names = {
            surface.get("exception")
            for surface in surface_items
            if isinstance(surface, dict) and surface.get("exception") is not None
        }
        for name in sorted(referenced_names - exception_names):
            findings.append(finding("error", "exceptions", f"surface references unknown exception {name!r}."))
        for surface in surface_items:
            if not isinstance(surface, dict) or surface.get("exception") not in exception_names:
                continue
            exception_name = surface["exception"]
            if exception_paths.get(exception_name) != surface.get("path"):
                findings.append(
                    finding(
                        "error",
                        "exceptions",
                        f"surface {surface.get('name')!r} and exception {exception_name!r} must name the same path.",
                    )
                )
    return findings


def read_authoritative_version(root: Path, data: dict[str, Any]) -> tuple[str | None, list[Finding]]:
    authority = data.get("authority")
    if not isinstance(authority, dict):
        return None, []
    path_value = authority.get("path")
    if not isinstance(path_value, str):
        return None, []
    path = root / path_value
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return None, [finding("error", "authority", f"Unable to read {path}: {exc}")]
    if not lines or not lines[0].strip():
        return None, [finding("error", "authority", f"{path} has no authoritative version on its first line.")]
    version = lines[0].strip()
    if not SEMVER_RE.fullmatch(version):
        return None, [finding("error", "authority", f"{path} does not contain a stable SemVer: {version!r}.")]
    return version, [finding("ok", "authority", f"{path} declares version {version}.")]


def check_surfaces(root: Path, data: dict[str, Any], version: str) -> list[Finding]:
    findings: list[Finding] = []
    surfaces = data.get("surfaces", [])
    if not isinstance(surfaces, list):
        return findings
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        name = surface.get("name")
        path_value = surface.get("path")
        required = surface.get("must_contain")
        if not isinstance(name, str) or not isinstance(path_value, str) or not isinstance(required, list):
            continue
        path = root / path_value
        exception_name = surface.get("exception")
        if isinstance(exception_name, str):
            exceptions = data.get("exceptions", [])
            exception = next(
                (
                    item for item in exceptions
                    if isinstance(item, dict) and item.get("name") == exception_name
                ),
                None,
            )
            if isinstance(exception, dict):
                if not path.is_file():
                    findings.append(finding("error", name, f"{path}: allowlisted version surface does not exist."))
                else:
                    findings.append(
                        finding(
                            "warn",
                            name,
                            f"{path} is allowlisted by {exception_name!r} until {exception['expires']}: "
                            f"{exception['reason']}",
                        )
                    )
                continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(finding("error", name, f"{path}: unable to read version surface: {exc}"))
            continue
        rendered = [item.format(version=version) for item in required]
        missing = [item for item, expected in zip(required, rendered) if expected not in text]
        if missing:
            details = ", ".join(repr(item) for item in missing)
            findings.append(finding("error", name, f"{path} is missing required version text: {details}."))
        else:
            findings.append(finding("ok", name, f"{path} contains the declared version {version}."))
    return findings


def run_check(args: argparse.Namespace) -> list[Finding]:
    root = args.root.resolve()
    config_path = (args.config or root / ".release" / "version-consistency.json").resolve()
    data, findings = load_json(config_path)
    if data is None:
        return findings
    findings.extend(validate_config(data))
    if any(item.status == "error" for item in findings):
        return findings
    if not isinstance(data, dict):
        return findings
    actual, authority_findings = read_authoritative_version(root, data)
    findings.extend(authority_findings)
    if actual is None:
        return findings
    expected = args.version or actual
    if not isinstance(expected, str) or not SEMVER_RE.fullmatch(expected):
        findings.append(
            finding("error", "expected_version", f"Expected version must be stable SemVer; got {expected!r}.")
        )
        return findings
    if expected != actual:
        findings.append(
            finding("error", "authority", f"Expected version {expected}; authoritative file declares {actual}.")
        )
        return findings
    findings.extend(check_surfaces(root, data, expected))
    return findings


def render(findings: list[Finding], output_format: str) -> int:
    errors = [item for item in findings if item.status == "error"]
    warnings = [item for item in findings if item.status == "warn"]
    status = "error" if errors else "warn" if warnings else "ok"
    if output_format == "json":
        print(
            json.dumps(
                {"schema_version": 1, "status": status, "findings": [asdict(item) for item in findings]},
                indent=2,
            )
        )
    else:
        print(f"Version-consistency check: {status}")
        for item in findings:
            print(f"{item.status.upper():5} {item.name}: {item.message}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return render(run_check(args), args.format)


if __name__ == "__main__":
    raise SystemExit(main())
