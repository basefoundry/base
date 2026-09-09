"""Update the known base-demo release pins for one Base ecosystem component."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


COMPONENTS = ("base", "base-cli", "base-bash-libs")
SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
CHECKSUM = re.compile(r"[0-9a-f]{64}\Z")
EXIT_SUCCESS = 0
EXIT_FAILURE = 1


class DownstreamBumpError(ValueError):
    """Raised when the expected downstream contract is not present."""


@dataclass
class _UpdateState:
    """Hold deferred file updates until every contract check succeeds."""

    updates: dict[Path, str]
    changed: set[Path]


@dataclass(frozen=True)
class _Replacement:
    """Describe one exact replacement contract."""

    pattern: str
    replacement: str
    expected: int
    flags: int = 0


def normalize_version(version: str) -> str:
    """Return a bare SemVer release version."""

    normalized = version.removeprefix("v")
    if not SEMVER.fullmatch(normalized):
        raise DownstreamBumpError(f"release version must be X.Y.Z, got {version!r}")
    return normalized


def _validate_commit(commit: str) -> None:
    if not COMMIT.fullmatch(commit):
        raise DownstreamBumpError("release commit must be a full lowercase 40-character SHA")


def _validate_checksum(checksum: str) -> None:
    if not CHECKSUM.fullmatch(checksum):
        raise DownstreamBumpError(
            "installer checksum must be a full lowercase 64-character SHA-256"
        )


def _replace(
    state: _UpdateState,
    path: Path,
    spec: _Replacement,
) -> None:
    """Replace an exact expected number of matches without partial writes."""

    source = state.updates.get(path)
    if source is None:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DownstreamBumpError(f"cannot read {path}: {exc}") from exc
    result, count = re.subn(
        spec.pattern,
        lambda _match: spec.replacement,
        source,
        flags=spec.flags,
    )
    if count != spec.expected:
        raise DownstreamBumpError(
            f"expected {spec.expected} matches in {path}, found {count}; refusing a partial bump"
        )
    state.updates[path] = result
    if result != source:
        state.changed.add(path)


def _replace_literal(
    state: _UpdateState,
    path: Path,
    old: str,
    new: str,
    *,
    expected: int,
) -> None:
    _replace(state, path, _Replacement(re.escape(old), new, expected))


def _replace_version(
    state: _UpdateState,
    path: Path,
    new_version: str,
    *,
    expected: int,
    prefix: str = "v",
) -> None:
    _replace(
        state,
        path,
        _Replacement(
            rf"{re.escape(prefix)}[0-9]+\.[0-9]+\.[0-9]+",
            f"{prefix}{new_version}",
            expected,
        ),
    )


def _base_updates(
    repo_dir: Path,
    state: _UpdateState,
    version: str,
    commit: str,
    installer_sha256: str | None,
) -> None:
    if installer_sha256 is None:
        raise DownstreamBumpError("base bumps require --installer-sha256")
    _validate_checksum(installer_sha256)

    install = repo_dir / "install.sh"
    install_source = install.read_text(encoding="utf-8")
    old_version_match = re.search(
        r'BASE_RELEASE_REF="\$\{BASE_RELEASE_REF:-v([0-9]+\.[0-9]+\.[0-9]+)\}"',
        install_source,
    )
    if old_version_match is None:
        raise DownstreamBumpError(f"could not find the current Base release ref in {install}")
    old_version = old_version_match.group(1)
    _replace(
        state,
        install,
        _Replacement(
            r'BASE_RELEASE_REF="\$\{BASE_RELEASE_REF:-v[0-9]+\.[0-9]+\.[0-9]+\}"',
            f'BASE_RELEASE_REF="${{BASE_RELEASE_REF:-v{version}}}"',
            1,
        ),
    )
    _replace(
        state,
        install,
        _Replacement(
            r'BASE_RELEASE_COMMIT="\$\{BASE_RELEASE_COMMIT:-[0-9a-f]{40}\}"',
            f'BASE_RELEASE_COMMIT="${{BASE_RELEASE_COMMIT:-{commit}}}"',
            1,
        ),
    )
    _replace(
        state,
        install,
        _Replacement(
            r'BASE_INSTALL_SHA256="\$\{BASE_INSTALL_SHA256-[0-9a-f]{64}\}"',
            f'BASE_INSTALL_SHA256="${{BASE_INSTALL_SHA256-{installer_sha256}}}"',
            1,
        ),
    )

    workflow = repo_dir / ".github" / "workflows" / "tests.yml"
    _replace(
        state,
        workflow,
        _Replacement(
            r"git -C \.\./base fetch --depth 1 origin [0-9a-f]{40}",
            f"git -C ../base fetch --depth 1 origin {commit}",
            3,
        ),
    )
    _replace_version(state, workflow, version, expected=2, prefix="Base v")

    release_doc = repo_dir / "docs" / "release.md"
    _replace(
        state,
        release_doc,
        _Replacement(
            r"- Base installer: the versioned `v[0-9]+\.[0-9]+\.[0-9]+` URL, SHA-256\n"
            r"  `[0-9a-f]{64}`, and\n"
            r"  Base commit `[0-9a-f]{40}`;",
            f"- Base installer: the versioned `v{version}` URL, SHA-256\n"
            f"  `{installer_sha256}`, and\n"
            f"  Base commit `{commit}`;",
            1,
        ),
    )

    contracts = repo_dir / "docs" / "contracts.md"
    _replace_version(state, contracts, version, expected=2, prefix="Base v")

    validation = repo_dir / "tests" / "validate.sh"
    _replace(
        state,
        validation,
        _Replacement(
            r"git -C \.\./base fetch --depth 1 origin [0-9a-f]{40}",
            f"git -C ../base fetch --depth 1 origin {commit}",
            2,
        ),
    )
    _replace_literal(state, validation, f"v{old_version}", f"v{version}", expected=3)

    install_tests = repo_dir / "tests" / "install_test.bats"
    _replace(
        state,
        install_tests,
        _Replacement(
            r'TEST_BASE_COMMIT="[0-9a-f]{40}"',
            f'TEST_BASE_COMMIT="{commit}"',
            1,
        ),
    )
    _replace_literal(
        state,
        install_tests,
        f"v{old_version}",
        f"v{version}",
        expected=1,
    )


def _base_cli_updates(
    repo_dir: Path,
    state: _UpdateState,
    version: str,
) -> None:
    pyproject = repo_dir / "pyproject.toml"
    pyproject_source = pyproject.read_text(encoding="utf-8")
    old_version_match = re.search(
        r"base-cli==([0-9]+\.[0-9]+\.[0-9]+)", pyproject_source
    )
    if old_version_match is None:
        raise DownstreamBumpError(f"could not find the current base-cli version in {pyproject}")
    old_version = old_version_match.group(1)
    _replace(
        state,
        pyproject,
        _Replacement(
            r"base-cli==[0-9]+\.[0-9]+\.[0-9]+",
            f"base-cli=={version}",
            1,
        ),
    )

    _replace(
        state,
        repo_dir / "README.md",
        _Replacement(re.escape(f"base-cli=={old_version}"), f"base-cli=={version}", 2),
    )
    _replace(
        state,
        repo_dir / ".ai-context" / "overview.md",
        _Replacement(re.escape(f"base-cli=={old_version}"), f"base-cli=={version}", 1),
    )

    workflow = repo_dir / ".github" / "workflows" / "tests.yml"
    clone_pattern = (
        r"git clone --depth 1 --branch v[0-9]+\.[0-9]+\.[0-9]+ "
        r"https://github\.com/basefoundry/base-cli\.git ../base-cli"
    )
    clone_replacement = (
        f"git clone --depth 1 --branch v{version} "
        "https://github.com/basefoundry/base-cli.git ../base-cli"
    )
    _replace(
        state,
        workflow,
        _Replacement(clone_pattern, clone_replacement, 1),
    )

    validation = repo_dir / "tests" / "validate.sh"
    _replace(
        state,
        validation,
        _Replacement(re.escape(f"base-cli=={old_version}"), f"base-cli=={version}", 2),
    )
    _replace(
        state,
        validation,
        _Replacement(clone_pattern, clone_replacement, 1),
    )


def _base_bash_libs_updates(
    repo_dir: Path,
    state: _UpdateState,
    version: str,
    commit: str,
) -> None:
    workflow = repo_dir / ".github" / "workflows" / "tests.yml"
    workflow_source = workflow.read_text(encoding="utf-8")
    old_version_match = re.search(
        r"base-bash-libs v([0-9]+\.[0-9]+\.[0-9]+)", workflow_source
    )
    if old_version_match is None:
        raise DownstreamBumpError(
            f"could not find the current base-bash-libs version in {workflow}"
        )
    old_version = old_version_match.group(1)
    _replace(
        state,
        workflow,
        _Replacement(
            r"repository: basefoundry/base-bash-libs\n          ref: [0-9a-f]{40}",
            f"repository: basefoundry/base-bash-libs\n          ref: {commit}",
            3,
        ),
    )
    _replace(
        state,
        workflow,
        _Replacement(r"base-bash-libs v[0-9]+\.[0-9]+\.[0-9]+", f"base-bash-libs v{version}", 1),
    )

    contracts = repo_dir / "docs" / "contracts.md"
    _replace(
        state,
        contracts,
        _Replacement(r"base-bash-libs v[0-9]+\.[0-9]+\.[0-9]+", f"base-bash-libs v{version}", 1),
    )

    validation = repo_dir / "tests" / "validate.sh"
    _replace(
        state,
        validation,
        _Replacement(r"ref: [0-9a-f]{40}", f"ref: {commit}", 2),
    )
    _replace_literal(state, validation, f"v{old_version}", f"v{version}", expected=2)


def update_base_demo_pins(
    repo_dir: Path,
    component: str,
    version: str,
    commit: str,
    installer_sha256: str | None = None,
) -> list[Path]:
    """Update one component's pins and return the changed paths.

    All expected matches are checked before any file is written. This makes a
    drifted downstream contract fail closed instead of producing a partial PR.
    """

    if component not in COMPONENTS:
        raise DownstreamBumpError(
            f"component must be one of {', '.join(COMPONENTS)}, got {component!r}"
        )
    version = normalize_version(version)
    _validate_commit(commit)
    repo_dir = repo_dir.resolve()
    if not repo_dir.is_dir():
        raise DownstreamBumpError(f"downstream checkout does not exist: {repo_dir}")

    state = _UpdateState(updates={}, changed=set())
    if component == "base":
        _base_updates(repo_dir, state, version, commit, installer_sha256)
    elif component == "base-cli":
        _base_cli_updates(repo_dir, state, version)
    else:
        _base_bash_libs_updates(repo_dir, state, version, commit)

    for path, text in state.updates.items():
        path.write_text(text, encoding="utf-8")
    return sorted(path.relative_to(repo_dir) for path in state.changed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=Path, required=True)
    parser.add_argument("--component", choices=COMPONENTS, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--installer-sha256")
    args = parser.parse_args(argv)

    try:
        changed = update_base_demo_pins(
            args.repo_dir,
            args.component,
            args.version,
            args.commit,
            args.installer_sha256,
        )
    except DownstreamBumpError as exc:
        print(f"downstream version bump: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    if not changed:
        print("No downstream pin changes required.")
    else:
        print("Updated downstream pins:")
        for path in changed:
            print(f"- {path}")
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
