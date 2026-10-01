from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from base_release.release_input_verifier import ReleaseInput
from base_release.release_input_verifier import ReleaseInputError
from base_release.release_input_verifier import verify_platform_evidence
from base_release.release_input_verifier import verify_release_inputs


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def make_repo(path: Path, *, version: str | None = None) -> str:
    path.mkdir()
    subprocess.run(["git", "init", "--initial-branch=main", str(path)], check=True, capture_output=True)
    git(path, "config", "user.name", "Release verifier test")
    git(path, "config", "user.email", "release-verifier@example.test")
    if version is not None:
        (path / "VERSION").write_text(version + "\n", encoding="utf-8")
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    git(path, "add", ".")
    git(path, "commit", "-m", "initial")
    return git(path, "rev-parse", "HEAD")


def test_matching_annotated_release_tag_and_checkout_are_accepted(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate_commit = make_repo(candidate, version="1.9.0")
    component = tmp_path / "base-cli"
    component_commit = make_repo(component)
    git(component, "tag", "-a", "v0.4.3", "-m", "base-cli release")

    verify_release_inputs(
        ReleaseInput("basefoundry/base", "1.9.0", candidate_commit, candidate),
        (ReleaseInput("basefoundry/base-cli", "0.4.3", component_commit, component, str(component)),),
    )


def test_mismatched_release_tag_commit_is_rejected(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate_commit = make_repo(candidate, version="1.9.0")
    component = tmp_path / "base-cli"
    tagged_commit = make_repo(component)
    git(component, "tag", "v0.4.3")
    (component / "README.md").write_text("newer\n", encoding="utf-8")
    git(component, "add", "README.md")
    git(component, "commit", "-m", "newer source")
    newer_commit = git(component, "rev-parse", "HEAD")

    with pytest.raises(ReleaseInputError, match=f"resolves to commit {tagged_commit}"):
        verify_release_inputs(
            ReleaseInput("basefoundry/base", "1.9.0", candidate_commit, candidate),
            (ReleaseInput("basefoundry/base-cli", "0.4.3", newer_commit, component, str(component)),),
        )


def test_checkout_head_mismatch_is_rejected_before_release_lookup(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate_commit = make_repo(candidate, version="1.9.0")
    component = tmp_path / "base-cli"
    checkout_commit = make_repo(component)
    (component / "README.md").write_text("newer\n", encoding="utf-8")
    git(component, "add", "README.md")
    git(component, "commit", "-m", "newer source")
    supplied_commit = git(component, "rev-parse", "HEAD")
    git(component, "checkout", "--detach", checkout_commit)

    with pytest.raises(ReleaseInputError, match=f"checkout.*is at {checkout_commit}"):
        verify_release_inputs(
            ReleaseInput("basefoundry/base", "1.9.0", candidate_commit, candidate),
            (ReleaseInput("basefoundry/base-cli", "0.4.3", supplied_commit, component, str(component)),),
        )

    assert checkout_commit != supplied_commit


def test_missing_or_unavailable_release_tag_fails_closed(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate_commit = make_repo(candidate, version="1.9.0")
    component = tmp_path / "base-cli"
    component_commit = make_repo(component)

    with pytest.raises(ReleaseInputError, match="release tag 'v0.4.3' is missing"):
        verify_release_inputs(
            ReleaseInput("basefoundry/base", "1.9.0", candidate_commit, candidate),
            (ReleaseInput("basefoundry/base-cli", "0.4.3", component_commit, component, str(component)),),
        )

    with pytest.raises(ReleaseInputError, match="could not resolve release tag"):
        verify_release_inputs(
            ReleaseInput("basefoundry/base", "1.9.0", candidate_commit, candidate),
            (
                ReleaseInput(
                    "basefoundry/base-cli",
                    "0.4.3",
                    component_commit,
                    component,
                    str(tmp_path / "does-not-exist"),
                ),
            ),
        )


def test_candidate_version_metadata_must_match_without_a_candidate_tag(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate_commit = make_repo(candidate, version="1.9.0")
    with pytest.raises(ReleaseInputError, match="version metadata.*not the supplied base version"):
        verify_release_inputs(
            ReleaseInput("basefoundry/base", "1.10.0", candidate_commit, candidate),
            (),
        )


def test_platform_evidence_must_bind_versions_and_commits(tmp_path: Path) -> None:
    candidate = ReleaseInput("basefoundry/base", "1.9.0", "a" * 40, tmp_path)
    component = ReleaseInput("basefoundry/base-cli", "0.4.3", "b" * 40, tmp_path)
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "result": "passed",
                "platform": "ubuntu-24.04",
                "components": {
                    "base": {"version": "1.9.0", "commit": "a" * 40},
                    "base-cli": {"version": "0.4.3", "commit": "b" * 40},
                },
            }
        ),
        encoding="utf-8",
    )

    verify_platform_evidence(evidence, "ubuntu-24.04", (candidate, component))
    evidence.write_text(evidence.read_text(encoding="utf-8").replace("b" * 40, "c" * 40), encoding="utf-8")
    with pytest.raises(ReleaseInputError, match="does not match basefoundry/base-cli"):
        verify_platform_evidence(evidence, "ubuntu-24.04", (candidate, component))
