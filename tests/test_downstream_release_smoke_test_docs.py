from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs" / "downstream-release-smoke-test.md"
DOCS_README = ROOT / "docs" / "README.md"


def test_downstream_release_smoke_test_is_linked_from_the_docs_map() -> None:
    assert "downstream-release-smoke-test.md" in DOCS_README.read_text(encoding="utf-8")


def test_downstream_release_smoke_test_binds_identity_before_the_read_only_check() -> None:
    text = DOC.read_text(encoding="utf-8")

    for required in (
        "release_tag=v1.9.0",
        "expected_commit=ac8d294421e1bfc14afa8c6a2a12f1affb5268ee",
        "expected_install_sha256=f0522bf20b13e2f487767324f4688f1b1ed33b1c1bc1158a404f0e428ea3e993",
        "bash -n",
        "--detach",
        "basectl\" check --format json",
        "release-bom.md",
        "SECURITY.md",
    ):
        assert required in text
