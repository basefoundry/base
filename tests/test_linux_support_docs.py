from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LINUX_SUPPORT_DOC = REPO_ROOT / "docs" / "linux-support.md"


def linux_support_text() -> str:
    return LINUX_SUPPORT_DOC.read_text(encoding="utf-8")


def test_linux_support_docs_include_manual_ubuntu_bootstrap() -> None:
    text = linux_support_text()

    assert "## Manual Ubuntu Bootstrap" in text
    assert "basectl setup --dry-run" in text
    assert "sudo apt-get install -y bash git python3 python3-venv python3-pip bats shellcheck jq golang-go" in text
    assert "GitHub CLI Debian/Ubuntu apt" in text
    assert "under `~/work`, not under mounted macOS shared folders" in text


def test_linux_support_docs_include_final_acceptance_commands() -> None:
    text = linux_support_text()

    assert "./bin/basectl ci check base --format text" in text
    assert "./bin/basectl check base --format text" in text
    assert "./bin/basectl doctor base --format text" in text
    assert "env -u BASE_HOME ./bin/base-test" in text
    assert "base-bash-libs" in text
