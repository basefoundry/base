"""Stdlib-only bootstrap inspection; never import the providers being diagnosed."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

# Bootstrap inspection cannot import base_cli.ExitCode.
SUCCESS = 0


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def first_line(path: Path) -> str | None:
    lines = read_text(path).splitlines()
    return (lines[0].strip() or None) if lines else None


def git_identity(root: Path) -> dict:
    """Do not accidentally report an enclosing workspace repository's identity."""
    result = {"revision": None, "dirty": None}
    if not (root / ".git").exists():
        return result
    try:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env["GIT_OPTIONAL_LOCKS"] = "0"
        revision = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, timeout=5, env=env, check=False,
        )
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, timeout=5, env=env, check=False,
        )
        if revision.returncode == 0:
            result["revision"] = revision.stdout.strip()
        if status.returncode == 0:
            result["dirty"] = bool(status.stdout)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def component(name: str, source: str, path: str | None, version: str | None = None) -> dict:
    return {"name": name, "source": source, "path": path, "version": version,
            "revision": None, "dirty": None, "status": "unknown", "detail": None}


def source_identity(record: dict, root: Path) -> dict:
    record["version"] = first_line(root / "VERSION")
    record.update(git_identity(root))
    record["status"] = "available" if record["version"] else "unknown"
    if not record["version"]:
        record["detail"] = "Selected source has no readable VERSION; installed metadata is not used."
    return record


def probe_installed(base_home: str) -> dict:
    # Match base-wrapper's isolated control-plane path without importing base_cli.
    sys.path.insert(0, str(Path(base_home) / "cli/python"))
    spec = importlib.util.find_spec("base_cli")
    if spec is None or not spec.origin:
        return {"path": None, "version": None, "detail": "base_cli is not discoverable in the selected Python environment."}
    origin = Path(spec.origin).resolve()
    version = None
    try:
        distribution = importlib.metadata.distribution("base-cli")
        # Metadata from a shadowed wheel must never identify another source tree.
        if Path(distribution.locate_file("base_cli/__init__.py")).resolve() == origin:
            version = distribution.version
    except importlib.metadata.PackageNotFoundError:
        pass
    return {"path": str(origin), "version": version, "detail": None}


def python_component(base_home: Path, python: str, kind: str, source: str, error: str) -> dict:
    record = component("base-cli", kind, str(Path(source).resolve()) if source else None)
    if error:
        record.update(status="unavailable", detail=error)
        return record
    if source:
        root = Path(source).resolve()
        record["path"] = str((root / "base_cli/__init__.py").resolve())
        # Only the documented lib/python layout has an unambiguous repo VERSION.
        if root.name == "python" and root.parent.name == "lib":
            return source_identity(record, root.parent.parent)
        record["detail"] = "Selected source has no recognized package metadata layout."
        return record
    try:
        process = subprocess.run(
            [python, "-I", str(Path(__file__).resolve()), "--probe", str(base_home)],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if process.returncode != 0:
            record.update(status="unavailable", detail="Selected Python could not inspect base-cli.")
            return record
        observed = json.loads(process.stdout)
        record.update(observed)
        if not record["path"]:
            record["status"] = "unavailable"
        else:
            package = Path(record["path"]).parent
            if package.parent.name == "python" and package.parent.parent.name == "lib":
                record["source"] = "installed-editable"
                source_identity(record, package.parents[2])
            else:
                record["status"] = "available" if record["version"] else "unknown"
                if not record["version"]:
                    record["detail"] = "Import location has no matching base-cli distribution metadata."
    except (OSError, subprocess.TimeoutExpired, ValueError):
        record.update(status="unavailable", detail="Selected Python is missing, unusable, or did not return a valid inspection.")
    return record


def bash_component(kind: str, source: str, error: str) -> dict:
    record = component("base-bash-libs", kind, str(Path(source).resolve()) if source else None)
    if error or not source:
        record.update(status="unavailable", detail=error or "No Bash provider was selected.")
        return record
    # Follow a symlinked stdlib just as base-bash-libs does when locating metadata.
    stdlib = (Path(source) / "std/lib_std.sh").resolve()
    if len(stdlib.parents) < 4:
        record["detail"] = "Selected stdlib has no package root metadata layout."
        return record
    root = stdlib.parents[3]
    source_identity(record, root)
    metadata = {}
    for line in read_text(stdlib.parents[1] / "base-bash-libs.release").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            metadata[key] = value
    if not os.access(root / "VERSION", os.R_OK):
        record["version"] = metadata.get("version") or None
    if record["revision"] is None:
        record["revision"] = metadata.get("commit") if metadata.get("commit") != "unknown" else None
        record["dirty"] = {"clean": False, "dirty": True}.get(metadata.get("dirty_state"))
    if record["version"]:
        record.update(status="available", detail=None)
    return record


def build_report(arguments: list[str]) -> dict:
    home, version, _, python, cli_kind, cli_root, cli_error, bash_kind, bash_root, bash_error = arguments
    base = component("base", "checkout" if (Path(home) / ".git").exists() else "installation", str(Path(home).resolve()), version if version != "unknown" else None)
    base.update(git_identity(Path(home)))
    base["status"] = "available" if version != "unknown" else "unknown"
    components = [base, python_component(Path(home), python, cli_kind, cli_root, cli_error),
                  bash_component(bash_kind, bash_root, bash_error)]
    python_available = os.access(python, os.X_OK)
    return {"schema_version": 1, "command": "version", "status": "ok" if python_available and all(
        item["status"] == "available" for item in components) else "warn",
        "data": {"python": {"path": str(Path(python).absolute()), "exists": python_available},
                 "components": components}, "error": None}


def render_component(item: dict) -> str:
    identity = item["version"] or item["status"]
    if item["revision"]:
        identity += f" (git {item['revision'][:12]}"
        if item["dirty"] is not None:
            identity += ", dirty" if item["dirty"] else ", clean"
        identity += ")"
    lines = [f"{item['name']}: {identity}",
             f"  source: {item['source']}  path: {item['path'] or 'unavailable'}"]
    if item["detail"]:
        lines.append(f"  {item['detail']}")
    return "\n".join(lines)


def render_text(report: dict) -> str:
    lines = [render_component(item) for item in report["data"]["components"]]
    python = report["data"]["python"]
    lines.append(f"Python: {python['path']}" + ("" if python["exists"] else " (unavailable)"))
    return "\n".join(lines)


def main(arguments: list[str]) -> int:
    if len(arguments) == 3 and arguments[0] == "--bash-summary":
        item = bash_component(arguments[1], arguments[2], "")
        print(render_component(item).splitlines()[0])
        return SUCCESS
    if len(arguments) == 2 and arguments[0] == "--probe":
        print(json.dumps(probe_installed(arguments[1]), sort_keys=True))
        return SUCCESS
    report = build_report(arguments)
    print(json.dumps(report, sort_keys=True) if arguments[2] == "json" else render_text(report))
    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
