"""Check Base's documented Stable contracts for incompatible changes.

The checked-in ``current.json`` file is the accepted compatibility baseline.
Command flags are read from the source-owned ``basectl --help`` output;
Markdown command prose is not parsed as a contract. Additive commands, flags,
fields, enum values, and finding IDs are allowed. Removing or changing an
existing contract requires updating that fixture and adding a
``Stability compatibility:`` migration entry to ``CHANGELOG.md``.

``v1.8.0.json`` records the release chosen as the initial provenance point.
The checker uses only the Python standard library so it can run before Base's
optional runtime dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_MARKER = "Stability compatibility:"

_FINDING_ID_RE = re.compile(r"`(?P<id>BASE-[A-Z][0-9]+)`")
_SCHEMA_RE = re.compile(r"schemas/(?P<name>[A-Za-z0-9_.-]+\.json)")
_HELP_OPTION_RE = re.compile(
    r"^\s{2,4}(?P<options>(?:--[A-Za-z0-9][\w-]*|-[A-Za-z])"
    r"(?:\s*,\s*(?:--[A-Za-z0-9][\w-]*|-[A-Za-z]))*)"
    r"(?:\s+(?P<value><[^>]+>|\[[^\]]+\]))?"
)

# ``gh pr`` exposes several pass-through subcommands under one documented
# row. Probe each implementation and union their source-owned options.
_COMMAND_PROBE_OVERRIDES: dict[str, tuple[tuple[str, ...], ...]] = {
    "basectl gh pr create/status/checks/ready/merge": (
        ("gh", "pr", "create"),
        ("gh", "pr", "status"),
        ("gh", "pr", "checks"),
        ("gh", "pr", "ready"),
        ("gh", "pr", "merge"),
    ),
}


# Stable JSON families that do not yet have a standalone JSON Schema file.
# These definitions deliberately describe only compatibility-bearing fields;
# additive keys and records remain allowed.
_JSON_CONTRACTS: dict[str, dict[str, Any]] = {
    "diagnostic-v1": {
        "type": "object",
        "required": ["schema_version", "status"],
        "properties": {
            "schema_version": {"const": 1},
            "status": {"type": "string", "enum": ["ok", "warn", "error"]},
            "project": {"type": "string"},
            "checks": {"type": "array", "items": {"$ref": "#/$defs/diagnostic-item"}},
            "findings": {"type": "array", "items": {"$ref": "#/$defs/diagnostic-item"}},
        },
        "$defs": {
            "diagnostic-item": {
                "type": "object",
                "required": ["id", "status", "name", "message", "fix"],
                "properties": {
                    "id": {"type": "string"},
                    "status": {"type": "string", "enum": ["ok", "warn", "error"]},
                    "name": {"type": "string"},
                    "message": {"type": "string"},
                    "fix": {"type": "string"},
                    "details": {"type": "object"},
                },
            }
        },
    },
    "inspection-v1": {
        "type": "object",
        "required": ["schema_version", "command", "status", "data", "error"],
        "properties": {
            "schema_version": {"const": 1},
            "command": {
                "type": "string",
                "enum": [
                    "repo check",
                    "release check",
                    "gh issue readiness",
                    "gh branch stale",
                ]
            },
            "status": {"type": "string", "enum": ["ok", "warn", "error"]},
            "data": {"type": "object"},
            "error": {
                "type": ["null", "object"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "usage_error",
                            "environment_error",
                            "upstream_error",
                            "execution_error",
                        ]
                    },
                    "message": {"type": "string"},
                    "details": {"type": "object"},
                },
            },
        },
    },
}


def _split_markdown_row(line: str) -> list[str]:
    escaped_pipe = "\x00"
    protected = line.replace(r"\|", escaped_pipe)
    return [cell.replace(escaped_pipe, "|").strip() for cell in protected.strip().strip("|").split("|")]


def _normalize_option(value: str | None) -> dict[str, Any]:
    if value is None:
        return {"takes_value": False}
    descriptor = value[1:-1].strip()
    enum_values = [item.strip() for item in descriptor.split("|") if item.strip()]
    result: dict[str, Any] = {"takes_value": True}
    if len(enum_values) > 1:
        result["enum"] = enum_values
    return result


def _placeholder_value(token: str) -> str:
    if token == "<version>":
        return "1.8.0"
    if token == "<number>":
        return "1"
    if token == "<finding-id>":
        return "BASE-D001"
    return "example"


def _command_probe_arguments(command: str) -> tuple[str, ...]:
    tokens = shlex.split(command)
    if not tokens or tokens[0] != "basectl":
        raise ValueError(f"stable command must start with basectl: {command}")
    arguments: list[str] = []
    option_needing_value = False
    for token in tokens[1:]:
        if token.startswith("[") and token.endswith("]"):
            continue
        if token.startswith("<") and token.endswith(">"):
            if option_needing_value:
                arguments.append(_placeholder_value(token))
            option_needing_value = False
            continue
        arguments.append(token)
        option_needing_value = token.startswith("--") and token not in {"--help"}
    return tuple(arguments)


def _parse_help_options(output: str) -> dict[str, dict[str, Any]]:
    options: dict[str, dict[str, Any]] = {}
    in_options = False
    for line in output.splitlines():
        if line.strip() == "Options:":
            in_options = True
            continue
        if not in_options:
            continue
        if line and not line[0].isspace():
            break
        match = _HELP_OPTION_RE.match(line)
        if not match:
            continue
        normalized = _normalize_option(match.group("value"))
        option_tokens = re.findall(r"--[A-Za-z0-9][\w-]*|-[A-Za-z]", match.group("options"))
        for option in option_tokens:
            existing = options.get(option)
            if existing is None:
                options[option] = dict(normalized)
                continue
            existing["takes_value"] = existing["takes_value"] or normalized["takes_value"]
            if "enum" in normalized:
                existing["enum"] = sorted(set(existing.get("enum", [])) | set(normalized["enum"]))
    return options


def runtime_command_contract(root: Path, command_names: list[str]) -> dict[str, dict[str, Any]]:
    """Read stable command flags from the command implementations' help output."""

    basectl = root / "bin" / "basectl"
    if not basectl.is_file():
        raise RuntimeError(f"basectl entrypoint is missing: {basectl}")
    environment = os.environ.copy()
    bash_libs = environment.get("BASE_BASH_LIBS_DIR", "")
    if not bash_libs:
        candidate = root.parent / "base-bash-libs" / "lib" / "bash"
        if candidate.is_dir():
            bash_libs = str(candidate)
    if not bash_libs or not Path(bash_libs).is_dir():
        raise RuntimeError("BASE_BASH_LIBS_DIR must point to a compatible base-bash-libs checkout")
    environment["BASE_BASH_LIBS_DIR"] = bash_libs
    commands: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="base-stability-compatibility-") as cache_dir:
        environment["BASE_CACHE_DIR"] = cache_dir
        for command_name in command_names:
            probes = _COMMAND_PROBE_OVERRIDES.get(command_name)
            if probes is None:
                probes = (_command_probe_arguments(command_name),)
            flags: dict[str, dict[str, Any]] = {}
            for probe in probes:
                result = subprocess.run(
                    [str(basectl), *probe, "--help"],
                    cwd=root,
                    env=environment,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode != 0:
                    detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
                    raise RuntimeError(f"help probe failed for {command_name!r}: {detail}")
                for option, contract in _parse_help_options(result.stdout or result.stderr).items():
                    existing = flags.get(option)
                    if existing is None:
                        flags[option] = contract
                    else:
                        existing["takes_value"] = existing["takes_value"] or contract["takes_value"]
                        if "enum" in contract:
                            existing["enum"] = sorted(set(existing.get("enum", [])) | set(contract["enum"]))
            commands[command_name] = {"flags": flags}
    return commands


def extract_findings(root: Path) -> dict[str, str]:
    path = root / "docs" / "doctor-findings.md"
    findings: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|") or "---" in line:
            continue
        cells = _split_markdown_row(line)
        if len(cells) < 2:
            continue
        match = _FINDING_ID_RE.fullmatch(cells[0].strip())
        if match:
            findings[match.group("id")] = " ".join(cells[1].split())
    return findings


def _normalize_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [_normalize_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    keywords = {
        "$defs",
        "$ref",
        "additionalProperties",
        "const",
        "enum",
        "items",
        "oneOf",
        "anyOf",
        "properties",
        "required",
        "type",
    }
    result: dict[str, Any] = {}
    for key in sorted(value):
        if key not in keywords:
            continue
        if key in {"$defs", "properties"} and isinstance(value[key], dict):
            result[key] = {name: _normalize_schema(child) for name, child in sorted(value[key].items())}
        else:
            normalized = _normalize_schema(value[key])
            if key in {"type", "required", "enum", "oneOf", "anyOf"} and isinstance(normalized, list):
                result[key] = sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
            else:
                result[key] = normalized
    return result


def extract_schemas(root: Path) -> dict[str, Any]:
    stability_doc = (root / "docs" / "stability-tiers.md").read_text(encoding="utf-8")
    schemas: dict[str, Any] = {}
    names = sorted({match.group("name") for match in _SCHEMA_RE.finditer(stability_doc)})
    for name in names:
        path = root / "docs" / "schemas" / name
        if not path.is_file():
            raise ValueError(f"stable schema is referenced but missing: docs/schemas/{name}")
        schemas[name] = _normalize_schema(json.loads(path.read_text(encoding="utf-8")))
    return schemas


def snapshot(root: Path, baseline_version: str, commands: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "format_version": 1,
        "baseline_version": baseline_version,
        "commands": commands,
        "findings": extract_findings(root),
        "json_contracts": _JSON_CONTRACTS,
        "schemas": extract_schemas(root),
    }


# pylint: disable=too-many-branches,too-many-statements
def _compare_schema(reference: Any, actual: Any, path: str, errors: list[str]) -> None:
    if isinstance(reference, dict):
        if not isinstance(actual, dict):
            errors.append(f"{path}: schema node changed from object to {type(actual).__name__}")
            return
        for key in ("type", "const", "$ref"):
            reference_value = reference.get(key)
            actual_value = actual.get(key)
            if key == "type" and isinstance(reference_value, list) and isinstance(actual_value, list):
                changed = sorted(reference_value) != sorted(actual_value)
            else:
                changed = key in reference and actual_value != reference_value
            if changed:
                errors.append(f"{path}.{key}: changed from {reference[key]!r} to {actual.get(key)!r}")
        if "additionalProperties" in reference:
            reference_additional = reference["additionalProperties"]
            actual_additional = actual.get("additionalProperties", True)
            if isinstance(reference_additional, bool) and isinstance(actual_additional, bool):
                if reference_additional and not actual_additional:
                    errors.append(f"{path}.additionalProperties: changed from true to false")
            elif isinstance(reference_additional, bool):
                errors.append(
                    f"{path}.additionalProperties: changed from {reference_additional!r} "
                    f"to {actual_additional!r}"
                )
            elif isinstance(reference_additional, dict):
                if "additionalProperties" not in actual:
                    errors.append(f"{path}.additionalProperties: removed stable value")
                else:
                    _compare_schema(
                        reference_additional,
                        actual_additional,
                        f"{path}.additionalProperties",
                        errors,
                    )
        if "enum" in reference:
            actual_values = set(actual.get("enum", []))
            missing = [value for value in reference["enum"] if value not in actual_values]
            if missing:
                errors.append(f"{path}.enum: removed stable values {missing!r}")
        for required in reference.get("required", []):
            if required not in actual.get("required", []):
                errors.append(f"{path}.required: removed stable field {required!r}")
        for key, reference_property in reference.get("properties", {}).items():
            actual_properties = actual.get("properties", {})
            if key not in actual_properties:
                errors.append(f"{path}.properties: removed stable field {key!r}")
            else:
                _compare_schema(reference_property, actual_properties[key], f"{path}.{key}", errors)
        for key, reference_definition in reference.get("$defs", {}).items():
            actual_definitions = actual.get("$defs", {})
            if key not in actual_definitions:
                errors.append(f"{path}.$defs: removed stable definition {key!r}")
            else:
                _compare_schema(reference_definition, actual_definitions[key], f"{path}.$defs.{key}", errors)
        if "items" in reference:
            if "items" not in actual:
                errors.append(f"{path}: removed stable array item contract")
            else:
                _compare_schema(reference["items"], actual["items"], f"{path}.items", errors)
        for key in ("oneOf", "anyOf"):
            if key in reference:
                if key not in actual:
                    errors.append(f"{path}: removed stable {key} contract")
                else:
                    _compare_schema(reference[key], actual[key], f"{path}.{key}", errors)
    elif reference != actual:
        errors.append(f"{path}: changed from {reference!r} to {actual!r}")


# pylint: disable=too-many-branches
def compare_snapshots(reference: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for command, reference_command in reference.get("commands", {}).items():
        actual_command = actual.get("commands", {}).get(command)
        if actual_command is None:
            errors.append(f"commands: removed stable command {command!r}")
            continue
        for option, reference_option in reference_command.get("flags", {}).items():
            actual_option = actual_command.get("flags", {}).get(option)
            if actual_option is None:
                errors.append(f"commands.{command}.flags: removed stable option {option!r}")
                continue
            if actual_option.get("takes_value") != reference_option.get("takes_value"):
                errors.append(f"commands.{command}.flags.{option}: changed value-taking contract")
            reference_enum = reference_option.get("enum", [])
            if "enum" in actual_option:
                actual_enum = set(actual_option.get("enum", []))
                missing_enum = [value for value in reference_enum if value not in actual_enum]
                if missing_enum:
                    errors.append(f"commands.{command}.flags.{option}: removed enum values {missing_enum!r}")

    for finding_id, reference_meaning in reference.get("findings", {}).items():
        actual_meaning = actual.get("findings", {}).get(finding_id)
        if actual_meaning is None:
            errors.append(f"findings: removed stable finding ID {finding_id}")
        elif actual_meaning != reference_meaning:
            errors.append(f"findings: reused or changed meaning for {finding_id}")

    for contract_name, reference_contract in reference.get("json_contracts", {}).items():
        actual_contract = actual.get("json_contracts", {}).get(contract_name)
        if actual_contract is None:
            errors.append(f"json_contracts: removed stable contract {contract_name!r}")
        else:
            _compare_schema(reference_contract, actual_contract, f"json_contracts.{contract_name}", errors)

    for schema_name, reference_schema in reference.get("schemas", {}).items():
        actual_schema = actual.get("schemas", {}).get(schema_name)
        if actual_schema is None:
            errors.append(f"schemas: removed stable schema {schema_name!r}")
        else:
            _compare_schema(reference_schema, actual_schema, f"schemas.{schema_name}", errors)
    return errors


def compare_provenance(
    provenance: dict[str, Any], current: dict[str, Any]
) -> list[str]:
    """Compare v1.8.0 with the accepted current fixture and honor only explicit exceptions."""

    differences = compare_snapshots(provenance, current)
    matched: set[str] = set()
    errors: list[str] = []
    exceptions = current.get("baseline_exceptions", [])
    if not isinstance(exceptions, list):
        return ["baseline_exceptions must be a list"]

    for exception in exceptions:
        if not isinstance(exception, dict):
            errors.append("baseline_exceptions entries must be objects")
            continue
        reason = exception.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append("baseline_exceptions entries require a non-empty reason")
        kind = exception.get("kind")
        if kind == "command_option_removed":
            command = exception.get("command")
            option = exception.get("option")
            expected = f"commands.{command}.flags: removed stable option {option!r}"
        elif kind == "finding_meaning_changed":
            finding_id = exception.get("finding_id")
            expected = f"findings: reused or changed meaning for {finding_id}"
        else:
            errors.append(f"unsupported baseline exception kind: {kind!r}")
            continue
        if expected not in differences:
            errors.append(f"stale baseline exception: {expected}")
        else:
            matched.add(expected)

    errors.extend(
        f"v1.8.0 provenance: unapproved compatibility change: {difference}"
        for difference in differences
        if difference not in matched
    )
    return errors


# pylint: disable=too-many-return-statements
def _json_shape(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if value is None:
        return {"type": "null"}
    if isinstance(value, list):
        items = [_json_shape(item) for item in value]
        return {"type": "array", "items": _merge_shapes(items) if items else {}}
    return {
        "type": "object",
        "properties": {key: _json_shape(item) for key, item in value.items()},
    }


def _merge_shapes(shapes: list[dict[str, Any]]) -> dict[str, Any]:
    if not shapes:
        return {}
    types = {shape.get("type") for shape in shapes}
    result: dict[str, Any] = {"type": next(iter(types)) if len(types) == 1 else sorted(types)}
    if result["type"] == "object":
        properties: dict[str, list[dict[str, Any]]] = {}
        for shape in shapes:
            for key, value in shape.get("properties", {}).items():
                properties.setdefault(key, []).append(value)
        result["properties"] = {key: _merge_shapes(values) for key, values in properties.items()}
    if result["type"] == "array":
        result["items"] = _merge_shapes([shape["items"] for shape in shapes if "items" in shape])
    return result


def _resolve_contract_ref(reference: dict[str, Any], root_contract: dict[str, Any]) -> dict[str, Any]:
    ref = reference.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        return reference
    name = ref.removeprefix("#/$defs/")
    resolved = root_contract.get("$defs", {}).get(name)
    return resolved if isinstance(resolved, dict) else reference


def validate_runtime_shape(
    reference: dict[str, Any],
    observed: dict[str, Any],
    path: str,
    errors: list[str],
    root_contract: dict[str, Any],
) -> None:
    reference = _resolve_contract_ref(reference, root_contract)
    reference_type = reference.get("type")
    observed_type = observed.get("type")
    accepted_types = reference_type if isinstance(reference_type, list) else [reference_type]
    if reference_type is None and "const" in reference:
        accepted_types = [_json_shape(reference["const"])["type"]]
    if observed_type not in accepted_types:
        errors.append(f"{path}: runtime type changed to {observed_type!r}; expected {accepted_types!r}")
        return
    if observed_type == "object":
        reference_properties = reference.get("properties", {})
        for key, observed_property in observed.get("properties", {}).items():
            if key in reference_properties:
                validate_runtime_shape(
                    reference_properties[key], observed_property, f"{path}.{key}", errors, root_contract
                )
        for required in reference.get("required", []):
            if required not in observed.get("properties", {}):
                errors.append(f"{path}: runtime output omitted required field {required!r}")
    elif observed_type == "array" and "items" in reference and observed.get("items"):
        validate_runtime_shape(reference["items"], observed["items"], f"{path}[]", errors, root_contract)


def runtime_contracts(root: Path) -> dict[str, dict[str, Any]]:
    """Capture representative check/doctor JSON emitted by the current code."""

    environment = os.environ.copy()
    python_paths = [str(root / "lib" / "python"), str(root / "cli" / "python")]
    if environment.get("PYTHONPATH"):
        python_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    commands = (
        [
            sys.executable,
            "-m",
            "base_setup.diagnostics",
            "check-json",
            "--project",
            "sample",
            "--check",
            "baseline",
            "ok",
            "ready",
            "",
        ],
        [
            sys.executable,
            "-m",
            "base_setup.diagnostics",
            "doctor-json",
            "--project",
            "sample",
            "--finding",
            "baseline",
            "ok",
            "ready",
            "",
        ],
    )
    shapes: list[dict[str, Any]] = []
    for command in commands:
        result = subprocess.run(command, cwd=root, env=environment, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "diagnostic JSON probe failed")
        try:
            shapes.append(_json_shape(json.loads(result.stdout)))
        except json.JSONDecodeError as error:
            raise RuntimeError(f"diagnostic JSON probe was not valid JSON: {error}") from error
    return {"diagnostic-v1": _merge_shapes(shapes)}


def _git_diff(root: Path, base_ref: str, path: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--unified=0", f"{base_ref}...HEAD", "--", path],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or f"git diff failed for {path}")
    return result.stdout


def require_changelog_for_fixture_change(root: Path, base_ref: str) -> list[str]:
    fixture_diff = _git_diff(root, base_ref, "docs/stability-baseline/current.json")
    if not fixture_diff:
        return []
    changelog_diff = _git_diff(root, base_ref, "CHANGELOG.md")
    marker = re.compile(
        rf"^\+\s*[-*]\s*{re.escape(CHANGELOG_MARKER)}\s*(?P<detail>\S.*\S)\s*$",
        re.MULTILINE,
    )
    match = marker.search(changelog_diff)
    if not match or match.group("detail").strip().lower() in {"n/a", "none", "todo", "tbd"}:
        return [
            "docs/stability-baseline/current.json changed without a "
            f"'{CHANGELOG_MARKER}' entry in CHANGELOG.md; include migration guidance"
        ]
    return []


def run_check(root: Path, base_ref: str | None = None, runtime: bool = False) -> list[str]:
    provenance_path = root / "docs" / "stability-baseline" / "v1.8.0.json"
    if not provenance_path.is_file():
        return [f"missing v1.8.0 provenance fixture: {provenance_path.relative_to(root)}"]
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"could not load v1.8.0 provenance fixture: {error}"]
    if provenance.get("baseline_version") != "1.8.0":
        return ["v1.8.0 provenance fixture must identify baseline_version 1.8.0"]

    fixture_path = root / "docs" / "stability-baseline" / "current.json"
    if not fixture_path.is_file():
        return [f"missing compatibility fixture: {fixture_path.relative_to(root)}"]
    try:
        reference = json.loads(fixture_path.read_text(encoding="utf-8"))
        command_names = sorted(reference.get("commands", {}))
        commands = runtime_command_contract(root, command_names)
        actual = snapshot(root, str(reference.get("baseline_version", "")), commands)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"could not load stability contract: {error}"]
    except (RuntimeError, subprocess.SubprocessError) as error:
        return [f"could not capture source command contract: {error}"]
    errors: list[str] = []
    if reference.get("format_version") != 1:
        errors.append("compatibility fixture must use format_version 1")
    if reference.get("baseline_version") != "1.8.0":
        errors.append("compatibility fixture must retain v1.8.0 as its provenance baseline")
    errors.extend(compare_snapshots(reference, actual))
    errors.extend(compare_provenance(provenance, reference))
    if runtime:
        try:
            observed_contracts = runtime_contracts(root)
            observed = observed_contracts["diagnostic-v1"]
            reference_contract = reference["json_contracts"]["diagnostic-v1"]
            validate_runtime_shape(reference_contract, observed, "runtime.diagnostic-v1", errors, reference_contract)
        except (OSError, RuntimeError, KeyError) as error:
            errors.append(f"could not capture runtime JSON contract: {error}")
    if base_ref:
        try:
            errors.extend(require_changelog_for_fixture_change(root, base_ref))
        except RuntimeError as error:
            errors.append(str(error))
    return errors


def _write_snapshot(root: Path, output: Path, baseline_version: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if output.is_file():
        existing = json.loads(output.read_text(encoding="utf-8"))
    command_names = sorted(existing.get("commands", {}))
    commands = runtime_command_contract(root, command_names)
    result = snapshot(root, baseline_version, commands)
    if existing.get("baseline_exceptions"):
        result["baseline_exceptions"] = existing["baseline_exceptions"]
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check the repository against current.json")
    parser.add_argument("--base-ref", help="Git base ref used to enforce the changelog override path")
    parser.add_argument("--runtime", action="store_true", help="probe representative JSON output from the current code")
    parser.add_argument("--write", action="store_true", help="write a snapshot fixture")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root to inspect")
    parser.add_argument("--output", type=Path, help="fixture path for --write")
    parser.add_argument("--baseline-version", default="1.8.0")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.write:
        output = (args.output or root / "docs" / "stability-baseline" / "current.json").resolve()
        _write_snapshot(root, output, args.baseline_version)
        return 0
    if not args.check:
        parser.error("one of --check or --write is required")
    errors = run_check(root, args.base_ref, args.runtime)
    if errors:
        print("Stable compatibility check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Stable compatibility check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
