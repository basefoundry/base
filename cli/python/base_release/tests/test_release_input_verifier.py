from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from base_release import release_input_verifier
from base_release.release_input_verifier import ReleaseInput
from base_release.release_input_verifier import ReleaseInputError
from base_release.release_input_verifier import resolve_release_tag_commit
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


def test_release_tag_authentication_failures_are_diagnostic(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_to_resolve(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["timeout"] == 30
        return subprocess.CompletedProcess(
            args[0] if args else [],
            128,
            stderr="fatal: Authentication failed for 'https://github.com/basefoundry/base-cli.git'",
        )

    monkeypatch.setattr(subprocess, "run", fail_to_resolve)

    with pytest.raises(ReleaseInputError, match="authentication or authorization failed"):
        resolve_release_tag_commit("https://github.com/basefoundry/base-cli.git", "v0.4.3")


def test_checkout_inspection_timeout_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def time_out(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["timeout"] == 30
        raise subprocess.TimeoutExpired(args[0] if args else [], 30)

    monkeypatch.setattr(subprocess, "run", time_out)

    with pytest.raises(ReleaseInputError, match="could not inspect Base release candidate checkout"):
        verify_release_inputs(
            ReleaseInput("basefoundry/base", "1.9.0", "a" * 40, tmp_path),
            (),
        )


def test_main_writes_verification_failures_to_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "base-release-inputs-verify",
            "--candidate-repository",
            "basefoundry/base",
            "--candidate-version",
            "1.9.0",
            "--candidate-commit",
            "a" * 40,
            "--candidate-checkout",
            ".",
            "--component",
            "basefoundry/base-cli",
            "0.4.3",
            "b" * 40,
            ".",
        ],
    )

    def fail_verification(*args: object, **kwargs: object) -> None:
        raise ReleaseInputError("verification failed")

    monkeypatch.setattr(release_input_verifier, "verify_release_inputs", fail_verification)

    assert release_input_verifier.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "release input verification: verification failed\n"


def test_main_verifies_multiple_evidence_documents_after_inputs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "base-release-inputs-verify",
            "--candidate-repository",
            "basefoundry/base",
            "--candidate-version",
            "1.9.0",
            "--candidate-commit",
            "a" * 40,
            "--candidate-checkout",
            ".",
            "--component",
            "basefoundry/base-cli",
            "0.4.3",
            "b" * 40,
            ".",
            "--evidence",
            "ubuntu.json",
            "--platform",
            "ubuntu-24.04",
            "--evidence",
            "macos.json",
            "--platform",
            "macos-14",
        ],
    )
    input_calls: list[tuple[object, ...]] = []
    evidence_calls: list[tuple[Path, str]] = []

    def record_inputs(*args: object, **_kwargs: object) -> None:
        input_calls.append(args)

    def record_evidence(path: Path, platform: str, inputs: tuple[ReleaseInput, ...]) -> None:
        del inputs
        evidence_calls.append((path, platform))

    monkeypatch.setattr(release_input_verifier, "verify_release_inputs", record_inputs)
    monkeypatch.setattr(release_input_verifier, "verify_platform_evidence", record_evidence)

    assert release_input_verifier.main() == 0
    assert len(input_calls) == 1
    assert evidence_calls == [(Path("ubuntu.json"), "ubuntu-24.04"), (Path("macos.json"), "macos-14")]


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
