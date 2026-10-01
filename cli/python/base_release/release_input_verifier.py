from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
STABLE_VERSION_RE = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
EXIT_SUCCESS = 0
EXIT_FAILURE = 1


class ReleaseInputError(ValueError):
    """Raised when a release input cannot be proven to match its identity."""


@dataclass(frozen=True)
class ReleaseInput:
    repository: str
    version: str
    commit: str
    checkout: Path
    remote: str | None = None


def verify_release_inputs(
    candidate: ReleaseInput,
    released_components: tuple[ReleaseInput, ...],
    *,
    candidate_version_file: str = "VERSION",
) -> None:
    _validate_input_shape(candidate, role="Base release candidate")
    _verify_checkout(candidate, role="Base release candidate")
    version_path = candidate.checkout / candidate_version_file
    try:
        metadata_version = version_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise ReleaseInputError(f"could not read Base candidate version metadata {version_path}: {exc}") from exc
    if metadata_version != candidate.version:
        raise ReleaseInputError(
            f"Base candidate version metadata {version_path} is {metadata_version!r}, "
            f"not the supplied base version {candidate.version!r}"
        )

    seen_repositories = {candidate.repository.casefold()}
    for component in released_components:
        _validate_input_shape(component, role=f"Released component {component.repository}")
        repository_key = component.repository.casefold()
        if repository_key in seen_repositories:
            raise ReleaseInputError(f"release input repository is duplicated: {component.repository}")
        seen_repositories.add(repository_key)
        _verify_checkout(component, role=f"Released component {component.repository}")
        remote = component.remote or f"https://github.com/{component.repository}.git"
        tag_commit = resolve_release_tag_commit(remote, f"v{component.version}")
        if tag_commit != component.commit:
            raise ReleaseInputError(
                f"{component.repository} v{component.version} resolves to commit {tag_commit}, "
                f"not the supplied commit {component.commit}"
            )


def resolve_release_tag_commit(remote: str, tag: str) -> str:
    try:
        result = subprocess.run(
            ["git", "ls-remote", remote, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReleaseInputError(f"could not resolve release tag {tag!r} from {remote!r}: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip()
        raise ReleaseInputError(
            f"could not resolve release tag {tag!r} from {remote!r}"
            + (f": {detail}" if detail else "")
        )

    refs: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2 or not FULL_SHA_RE.fullmatch(parts[0]):
            raise ReleaseInputError(f"release tag lookup returned malformed provenance for {tag!r}")
        refs[parts[1]] = parts[0]
    direct_ref = f"refs/tags/{tag}"
    peeled_ref = f"{direct_ref}^{{}}"
    if direct_ref not in refs:
        raise ReleaseInputError(f"release tag {tag!r} is missing from {remote!r}")
    return refs.get(peeled_ref, refs[direct_ref])


def verify_platform_evidence(path: Path, platform: str, inputs: tuple[ReleaseInput, ...]) -> None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseInputError(f"could not read platform evidence {path}: {exc}") from exc
    if not isinstance(document, dict) or document.get("result") != "passed" or document.get("platform") != platform:
        raise ReleaseInputError(f"platform evidence {path} is not a passed {platform} result")
    components = document.get("components")
    if not isinstance(components, dict):
        raise ReleaseInputError(f"platform evidence {path} has no components object")
    for release_input in inputs:
        alias = release_input.repository.rsplit("/", 1)[-1]
        evidence = components.get(alias)
        if not isinstance(evidence, dict):
            raise ReleaseInputError(f"platform evidence {path} is missing component {alias!r}")
        if evidence.get("version") != release_input.version or evidence.get("commit") != release_input.commit:
            raise ReleaseInputError(
                f"platform evidence {path} does not match {release_input.repository} "
                f"{release_input.version}@{release_input.commit}"
            )


def _validate_input_shape(release_input: ReleaseInput, *, role: str) -> None:
    if not release_input.repository or "/" not in release_input.repository:
        raise ReleaseInputError(f"{role} repository must use owner/name format")
    if not STABLE_VERSION_RE.fullmatch(release_input.version):
        raise ReleaseInputError(f"{role} version must be a stable SemVer value: {release_input.version!r}")
    if not FULL_SHA_RE.fullmatch(release_input.commit):
        raise ReleaseInputError(f"{role} commit must be a lowercase full 40-character SHA")


def _verify_checkout(release_input: ReleaseInput, *, role: str) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(release_input.checkout), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ReleaseInputError(f"could not inspect {role} checkout {release_input.checkout}: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip()
        raise ReleaseInputError(
            f"could not inspect {role} checkout {release_input.checkout}"
            + (f": {detail}" if detail else "")
        )
    checkout_commit = result.stdout.strip()
    if checkout_commit != release_input.commit:
        raise ReleaseInputError(
            f"{role} checkout {release_input.checkout} is at {checkout_commit}, "
            f"not the supplied commit {release_input.commit}"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="base-release-inputs-verify")
    parser.add_argument("--candidate-repository", required=True)
    parser.add_argument("--candidate-version", required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--candidate-checkout", type=Path, required=True)
    parser.add_argument("--candidate-version-file", default="VERSION")
    parser.add_argument(
        "--component",
        action="append",
        nargs=4,
        metavar=("REPOSITORY", "VERSION", "COMMIT", "CHECKOUT"),
        required=True,
    )
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--platform")
    return parser


def main() -> int:
    args = _parser().parse_args()
    candidate = ReleaseInput(
        args.candidate_repository,
        args.candidate_version,
        args.candidate_commit,
        args.candidate_checkout,
    )
    components = tuple(
        ReleaseInput(repository, version, commit, Path(checkout))
        for repository, version, commit, checkout in args.component
    )
    try:
        verify_release_inputs(candidate, components, candidate_version_file=args.candidate_version_file)
        if args.evidence is not None:
            if not args.platform:
                _parser().error("--platform is required with --evidence")
            verify_platform_evidence(args.evidence, args.platform, (candidate, *components))
    except ReleaseInputError as exc:
        print(f"release input verification: {exc}")
        return EXIT_FAILURE
    print("release input verification passed")
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
