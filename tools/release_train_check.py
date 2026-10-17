#!/usr/bin/env python3
"""Read-only preflight for the Base cross-repository release train.

The checker intentionally owns no GitHub mutations and never publishes an
artifact.  It validates the versioned train policy locally and, when
``--remote`` is supplied, reads hosted milestones and releases through ``gh``.
"""

# Keep the policy validation paths together so the JSON output stays easy to
# audit and consume from CI and agent harnesses.
# pylint: disable=too-many-branches,too-many-statements

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from . import version_consistency_check
except ImportError:  # Script execution from the repository root.
    import version_consistency_check

try:
    import yaml
except ImportError:  # pragma: no cover - the development contract installs PyYAML.
    yaml = None


SEMVER_RE = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class Finding:
    status: str
    name: str
    message: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Base checkout to inspect (default: the checkout containing this script).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Release-train JSON manifest (default: <root>/.release/release-train.json).",
    )
    parser.add_argument("--remote", action="store_true", help="Read hosted milestones and releases with gh.")
    parser.add_argument(
        "--release-prep",
        action="store_true",
        help="Require local release metadata to already name the target version.",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip the clean-worktree check (useful for isolated fixture tests).",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def finding(status: str, name: str, message: str) -> Finding:
    return Finding(status=status, name=name, message=message)


def load_manifest(path: Path) -> tuple[dict[str, Any] | None, list[Finding]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [finding("error", "manifest", f"Unable to read {path}: {exc}")]
    if not isinstance(data, dict):
        return None, [finding("error", "manifest", "The release-train manifest must be a JSON object.")]
    return data, []


def validate_manifest(data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if data.get("schema_version") != 1:
        findings.append(finding("error", "manifest_schema", "schema_version must be 1."))

    candidate = data.get("candidate")
    if not isinstance(candidate, dict):
        findings.append(finding("error", "candidate", "candidate must be an object."))
        candidate = {}
    candidate_repository = candidate.get("repository")
    if not isinstance(candidate_repository, str) or not re.fullmatch(r"[^/]+/[^/]+", candidate_repository):
        findings.append(finding("error", "candidate_repository", "candidate.repository must be owner/name."))
    candidate_version = candidate.get("target_version")
    candidate_milestone = candidate.get("milestone")
    valid_candidate_version = isinstance(candidate_version, str) and SEMVER_RE.fullmatch(candidate_version)
    if not valid_candidate_version:
        findings.append(
            finding("error", "candidate_version", "candidate.target_version must be SemVer X.Y.Z.")
        )
    if valid_candidate_version and candidate_milestone != f"v{candidate_version}":
        findings.append(
            finding(
                "error",
                "candidate_milestone",
                f"candidate.milestone must be v{candidate_version}; got {candidate_milestone!r}.",
            )
        )
    current_version = candidate.get("current_version")
    if not isinstance(current_version, str) or not SEMVER_RE.fullmatch(current_version):
        findings.append(finding("error", "current_version", "candidate.current_version must be SemVer X.Y.Z."))

    participants = data.get("participants")
    if not isinstance(participants, list) or not participants:
        findings.append(finding("error", "participants", "participants must be a non-empty list."))
        participants = []
    seen_repositories: set[str] = set()
    for index, participant in enumerate(participants):
        label = f"participant_{index + 1}"
        if not isinstance(participant, dict):
            findings.append(finding("error", label, "participant must be an object."))
            continue
        repository = participant.get("repository")
        version = participant.get("version")
        milestone = participant.get("milestone")
        ref = participant.get("resolved_ref")
        legacy_mutable = participant.get("legacy_mutable", False)
        if not isinstance(repository, str) or not re.fullmatch(r"[^/]+/[^/]+", repository):
            findings.append(finding("error", label, "repository must be owner/name."))
        elif repository in seen_repositories:
            findings.append(finding("error", label, f"duplicate participant repository: {repository}."))
        else:
            seen_repositories.add(repository)
        if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
            findings.append(finding("error", label, "version must be SemVer X.Y.Z."))
        if milestone != f"v{version}":
            findings.append(finding("error", label, f"milestone must be v{version}; got {milestone!r}."))
        if not isinstance(ref, str) or not SHA_RE.fullmatch(ref):
            findings.append(finding("error", label, "resolved_ref must be a full lowercase 40-character SHA."))
        if not isinstance(legacy_mutable, bool):
            findings.append(finding("error", label, "legacy_mutable must be a boolean when present."))

    gates = data.get("gates")
    if not isinstance(gates, dict):
        findings.append(finding("error", "gates", "gates must be an object."))
        gates = {}
    required_gates = ("empty_milestones", "immutable_releases", "public_readback")
    for gate in required_gates:
        if gates.get(gate) is not True:
            findings.append(finding("error", f"gate_{gate}", f"gates.{gate} must be true."))
    bom = gates.get("release_bom")
    if not isinstance(bom, dict) or not isinstance(bom.get("workflow"), str):
        findings.append(finding("error", "bom_workflow", "gates.release_bom.workflow is required."))
    if not isinstance(bom, dict) or bom.get("platforms") != ["ubuntu-24.04", "macos-14"]:
        findings.append(
            finding(
                "error",
                "bom_platforms",
                "gates.release_bom.platforms must require Ubuntu 24.04 and the macOS 14 support platform.",
            )
        )
    return findings


def check_local_identity(root: Path, data: dict[str, Any], release_prep: bool) -> list[Finding]:
    candidate = data["candidate"]
    target = candidate["target_version"]
    expected = target if release_prep else candidate["current_version"]
    checker_args = argparse.Namespace(
        root=root,
        config=root / ".release" / "version-consistency.json",
        version=expected,
        format="json",
    )
    return [
        finding(item.status, item.name, item.message)
        for item in version_consistency_check.run_check(checker_args)
    ]


def check_worktree(root: Path) -> Finding:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return finding("error", "git_worktree", f"Unable to inspect the Git worktree: {exc}")
    if result.returncode != 0:
        return finding("error", "git_worktree", result.stderr.strip() or "git status failed.")
    if result.stdout.strip():
        return finding("error", "git_worktree", "The release-prep worktree is not clean.")
    return finding("ok", "git_worktree", "The worktree is clean.")


def gh_api(path: str) -> tuple[Any | None, str | None]:
    try:
        result = subprocess.run(["gh", "api", path], check=False, capture_output=True, text=True)
    except OSError as exc:
        return None, str(exc)
    if result.returncode != 0:
        return None, result.stderr.strip() or f"gh api failed with exit code {result.returncode}."
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"gh returned invalid JSON: {exc}."


def resolve_tag_commit(repository: str, version: str) -> tuple[str | None, str | None]:
    ref, error = gh_api(f"repos/{repository}/git/ref/tags/v{version}")
    if error:
        return None, error
    tag_object = ref.get("object", {})
    if tag_object.get("type") == "commit":
        return tag_object.get("sha"), None
    if tag_object.get("type") != "tag":
        return None, f"v{version} has an unsupported Git object type: {tag_object.get('type')!r}."
    annotated, error = gh_api(f"repos/{repository}/git/tags/{tag_object.get('sha', '')}")
    if error:
        return None, error
    commit_object = annotated.get("object", {})
    if commit_object.get("type") != "commit":
        return None, f"v{version} annotated tag does not peel to a commit."
    return commit_object.get("sha"), None


def check_remote_state(root: Path, data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    candidate = data["candidate"]
    candidate_repository = candidate["repository"]
    milestone_path = f"repos/{candidate_repository}/milestones?state=all&per_page=100"
    milestones, error = gh_api(milestone_path)
    if error:
        findings.append(finding("error", "candidate_milestone", error))
    else:
        matching = [item for item in milestones if item.get("title") == candidate["milestone"]]
        if not matching:
            findings.append(finding("error", "candidate_milestone", f"{candidate['milestone']} does not exist."))
        elif matching[0].get("open_issues", 0):
            findings.append(
                finding(
                    "error",
                    "candidate_milestone",
                    f"{candidate['milestone']} has {matching[0]['open_issues']} open issue(s).",
                )
            )
        else:
            findings.append(finding("ok", "candidate_milestone", f"{candidate['milestone']} is empty."))

    for participant in data["participants"]:
        repository = participant["repository"]
        version = participant["version"]
        milestone_path = f"repos/{repository}/milestones?state=all&per_page=100"
        milestones, error = gh_api(milestone_path)
        if error:
            findings.append(finding("error", f"milestone_{repository}", error))
        else:
            matching = [item for item in milestones if item.get("title") == participant["milestone"]]
            if not matching:
                findings.append(
                    finding("error", f"milestone_{repository}", f"{participant['milestone']} does not exist.")
                )
            elif matching[0].get("open_issues", 0):
                findings.append(
                    finding(
                        "error",
                        f"milestone_{repository}",
                        f"{participant['milestone']} has {matching[0]['open_issues']} open issue(s).",
                    )
                )
            else:
                findings.append(finding("ok", f"milestone_{repository}", f"{participant['milestone']} is empty."))

        immutable_policy, policy_error = gh_api(f"repos/{repository}/immutable-releases")
        if policy_error:
            findings.append(finding("error", f"immutable_policy_{repository}", policy_error))
            immutable_enabled = False
        elif immutable_policy.get("enabled") is not True:
            findings.append(
                finding(
                    "error",
                    f"immutable_policy_{repository}",
                    "Repository-level immutable-release enforcement is not enabled.",
                )
            )
            immutable_enabled = False
        else:
            findings.append(
                finding(
                    "ok",
                    f"immutable_policy_{repository}",
                    "Repository-level immutable-release enforcement is enabled.",
                )
            )
            immutable_enabled = True

        release, error = gh_api(f"repos/{repository}/releases/tags/v{version}")
        if error:
            findings.append(finding("error", f"release_{repository}", error))
        elif release.get("draft") or release.get("prerelease"):
            findings.append(finding("error", f"release_{repository}", f"v{version} is draft or prerelease."))
        elif release.get("immutable") is True:
            findings.append(finding("ok", f"release_{repository}", f"v{version} is public and immutable."))
        elif participant.get("legacy_mutable") is True and immutable_enabled:
            findings.append(
                finding(
                    "warn",
                    f"release_{repository}",
                    f"v{version} is a declared pre-enforcement legacy release and remains mutable.",
                )
            )
        else:
            findings.append(
                finding("error", f"release_{repository}", f"v{version} is not reported immutable by GitHub.")
            )

        peeled_sha, error = resolve_tag_commit(repository, version)
        if error:
            findings.append(finding("error", f"tag_{repository}", error))
        elif peeled_sha != participant["resolved_ref"]:
            findings.append(
                finding(
                    "error",
                    f"tag_{repository}",
                    f"v{version} peels to {peeled_sha}; expected {participant['resolved_ref']}.",
                )
            )
        else:
            findings.append(finding("ok", f"tag_{repository}", f"v{version} peels to the selected commit."))

    bom = data["gates"]["release_bom"]
    workflow_path = root / ".github" / "workflows" / bom["workflow"]
    if yaml is None:
        findings.append(finding("error", "bom_defaults", "PyYAML is required to inspect the BOM workflow inputs."))
    else:
        try:
            workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
            dispatch = workflow.get(True) or workflow.get("on", {})
            inputs = dispatch.get("workflow_dispatch", {}).get("inputs", {})
            expected_inputs = bom.get("inputs", {})
            for name, expected in expected_inputs.items():
                actual = inputs.get(name, {}).get("default")
                if actual != expected:
                    findings.append(
                        finding(
                            "error",
                            f"bom_default_{name}",
                            f"BOM default {name}={actual!r}; expected {expected!r}.",
                        )
                    )
            if not expected_inputs:
                findings.append(finding("warn", "bom_defaults", "No BOM defaults are declared in the train manifest."))
            else:
                findings.append(finding("ok", "bom_defaults", "BOM workflow defaults match the train manifest."))
        except (OSError, AttributeError, TypeError, yaml.YAMLError) as exc:
            findings.append(finding("error", "bom_defaults", f"Unable to inspect {workflow_path}: {exc}"))
    return findings


def run_check(args: argparse.Namespace) -> list[Finding]:
    root = args.root.resolve()
    manifest_path = (args.manifest or root / ".release" / "release-train.json").resolve()
    data, findings = load_manifest(manifest_path)
    if data is None:
        return findings
    findings.extend(validate_manifest(data))
    if any(item.status == "error" for item in findings):
        return findings
    findings.extend(check_local_identity(root, data, args.release_prep))
    if not args.no_git:
        findings.append(check_worktree(root))
    if args.remote:
        findings.extend(check_remote_state(root, data))
    return findings


def render(findings: list[Finding], output_format: str) -> int:
    errors = [item for item in findings if item.status == "error"]
    warnings = [item for item in findings if item.status == "warn"]
    status = "error" if errors else "warn" if warnings else "ok"
    if output_format == "json":
        payload = {"schema_version": 1, "status": status, "findings": [asdict(item) for item in findings]}
        print(json.dumps(payload, indent=2))
    else:
        print(f"Release-train preflight: {status}")
        for item in findings:
            print(f"{item.status.upper():5} {item.name}: {item.message}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return render(run_check(args), args.format)


if __name__ == "__main__":
    raise SystemExit(main())
