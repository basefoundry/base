from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LINUX_SUPPORT_DOC = REPO_ROOT / "docs" / "linux-support.md"


def linux_support_text() -> str:
    return LINUX_SUPPORT_DOC.read_text(encoding="utf-8")


def test_linux_support_docs_include_apt_backed_ubuntu_bootstrap() -> None:
    text = linux_support_text()

    assert "# Linux support" in text
    assert "## Supported Ubuntu/Debian Contract" in text
    assert "source-checkout support contract" in text
    assert "Base does not ship a Debian package" in text
    assert "## Source-Checkout Smoke Checklist" in text
    assert "Expected result:" in text
    assert "## Ubuntu Bootstrap" in text
    assert "basectl setup --dry-run" in text
    assert "basectl setup --yes" in text
    assert "`--yes` means non-interactive consent for unattended setup" in text
    assert "Red Hat, CentOS, Windows" in text
    assert "sudo apt-get install -y bash git python3 python3-venv python3-pip bats shellcheck jq golang-go" in text
    assert "sudo apt-get install -y bash git gh python3" not in text
    assert "https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian" in text
    assert "signed apt repository/keyring" in text
    assert "`basectl setup --profile dev` does not install" in text
    assert "`gh` from default apt repositories" in text
    assert "then installs `gh` from that" in text
    assert "`gh` maps to" not in text
    assert "GitHub CLI authentication" in text
    assert "gh auth login --web --git-protocol https" in text
    assert "gh auth login --web --git-protocol https --insecure-storage" in text
    assert "plain text" in text
    assert "Base does not store GitHub tokens" in text
    assert "under `~/work`, not under mounted macOS shared folders" in text


def test_linux_support_docs_include_final_acceptance_commands() -> None:
    text = linux_support_text()

    assert "./bin/basectl check --ci base --format text" in text
    assert "./bin/basectl check base --format text" in text
    assert "./bin/basectl doctor base --format text" in text
    assert "env -u BASE_HOME ./bin/base-test" in text
    assert "base-bash-libs" in text
