from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_workspace_update_docs_match_active_checkout_and_dry_run_contract() -> None:
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    command_reference = (REPO_ROOT / "docs" / "command-reference.md").read_text(
        encoding="utf-8"
    )
    manifest = (REPO_ROOT / "docs" / "workspace-manifest.md").read_text(encoding="utf-8")
    normalized_reference = " ".join(command_reference.split())

    assert "active `BASE_HOME` control-plane" in architecture
    assert "same read-only preflight checks" in command_reference
    assert "may invoke Git and contact the configured remote" in normalized_reference
    assert "never pull or mutate a checkout" in manifest
    assert "unsafe roots are" in manifest
    assert "When the manifest's `base` path is the active" in manifest
    assert "it is skipped to protect the control plane" not in manifest
