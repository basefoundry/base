from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs" / "downstream-release-smoke-test.md"
DOCS_README = ROOT / "docs" / "README.md"


def test_downstream_release_smoke_test_is_linked_from_the_docs_map() -> None:
    assert "downstream-release-smoke-test.md" in DOCS_README.read_text(encoding="utf-8")


def test_downstream_release_smoke_test_binds_identity_before_the_read_only_check() -> None:
    text = DOC.read_text(encoding="utf-8")

    for required in (
        "release_tag=v1.10.0",
        "expected_commit=167947add351b8d609b5ab17342425e9a337acbb",
        "expected_install_sha256=94840a0e37b993065781fac3efa86ed692f974917d57a77170dae29efff539ca",
        "bash -n",
        "--detach",
        "basectl\" check --format json",
        "release-bom.md",
        "SECURITY.md",
    ):
        assert required in text
