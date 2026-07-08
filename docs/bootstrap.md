# First-Mile Bootstrap

`bootstrap.sh` is Base's preferred entry point for a new or uncertain macOS
machine. It handles the minimum prerequisites needed before `basectl` can take
over: Homebrew, Git, Bash 4.2+, and either a source checkout or Homebrew
installation of Base.

On Ubuntu/Debian Linux, `bootstrap.sh` stays conservative: it does not run
`sudo apt` from a piped script. Instead, it detects the platform and prints the
manual source-checkout commands, including apt prerequisites and the
`basectl setup --yes` handoff for unattended paste-and-run flows.

When only the supported Bash prerequisite is missing, use the focused
`--ensure-bash` path instead of the full install bootstrap. It verifies Bash
4.2+ and installs only the platform Bash package when needed.

## Quick Start

Run the bootstrapper from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

For a verified first run, pin reviewed Homebrew installer content before
executing the bootstrapper:

```bash
BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL=file:///path/to/homebrew-install.sh \
BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256=<sha256> \
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

Use `BASE_HOMEBREW_INSTALLER_URL` and `BASE_HOMEBREW_INSTALLER_SHA256` instead
when the same pin should apply to all Base Homebrew entry points.

On macOS, the bootstrapper verifies macOS, installs missing first-mile
prerequisites, and then prints the exact commands needed to finish setup. For
the default source checkout path, the handoff usually looks like:

```bash
~/work/base/bin/basectl setup
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

`bootstrap.sh` does not edit shell startup files automatically. Shell profile
integration remains an explicit `basectl update-profile` step so the user can
see what was installed before Base changes future interactive shells.

If `basectl` reports that the current Bash is too old, repair just that first:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --ensure-bash --dry-run
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --ensure-bash --yes
```

On macOS this path uses Homebrew Bash. On Ubuntu/Debian it previews and then
runs only `sudo apt-get update` and `sudo apt-get install -y bash`.

On Ubuntu/Debian, inspect the manual path first:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source --dry-run
```

The output includes `sudo apt-get update`, the supported apt prerequisite list,
the sibling `base-bash-libs` clone, and the source checkout `setup --dry-run`,
`setup --yes`, and `update-profile` commands. Interactive users can run plain
`setup` after reviewing `setup --dry-run`; Ubuntu/Debian setup prompts before
apt, keyring, repository, or remote-installer changes, while non-interactive
runs use `--yes`.

## Install Mode

Choose a mode explicitly when the default should not infer one:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --brew
```

Without an explicit mode, bootstrap uses this order:

1. `BASE_BOOTSTRAP_MODE`
2. an existing Homebrew-installed Base formula
3. an existing source checkout
4. source mode at `~/work/base`

This keeps an existing Homebrew install from being silently displaced by a
source checkout. Homebrew and source installs can coexist; the active `basectl`
is whichever executable the shell finds first on `PATH`.

## Common Options

```bash
bootstrap.sh --source
bootstrap.sh --brew
bootstrap.sh --install-dir ~/work/base
bootstrap.sh --repo-url https://github.com/basefoundry/base.git
bootstrap.sh --branch <name>
bootstrap.sh --no-homebrew-install
bootstrap.sh --ensure-bash
bootstrap.sh --dry-run
bootstrap.sh --yes
```

Use `--dry-run` to inspect the planned prerequisite installs and Base install
route without changing the machine. On Ubuntu/Debian, the bootstrapper always
prints manual commands rather than mutating apt state itself, except for the
focused `--ensure-bash --yes` path that installs only Bash.

## Contributor Path

Contributors should prefer source mode:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source
git clone https://github.com/basefoundry/base-bash-libs.git ~/work/base-bash-libs
~/work/base/bin/basectl setup --profile dev
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

The sibling `base-bash-libs` checkout gives the source-tree BATS suite the
reusable Bash libraries it validates against. If that checkout already exists,
update it before running the full contributor test contract. The `dev` profile
installs contributor prerequisites such as BATS, ShellCheck, and GitHub CLI. On
Ubuntu/Debian, GitHub CLI is installed through GitHub CLI's official
Debian/Ubuntu apt repository/keyring, while authentication remains user-owned.
After that, use `basectl test base` for the dogfood test contract.

Named profiles compose when a contributor also wants site-reliability tools:

```bash
~/work/base/bin/basectl setup --profile dev,sre
```

The `sre` profile installs local diagnostic tools only. It does not configure
cloud accounts, kube contexts, credentials, or production access.

AI coding tools stay behind an explicit opt-in profile:

```bash
~/work/base/bin/basectl setup --profile ai
```

The `ai` profile installs Codex CLI and Claude Code with their official
installers. Base checks tool availability and version output, but it does not
configure accounts, credentials, model access, or organization policy. See
[Remote Installer Policy](remote-installer-policy.md) for the allowed URLs,
dry-run behavior, non-interactive behavior, and managed-device guidance.

## Relationship To Other Install Paths

Use `bootstrap.sh` when the machine may not have Homebrew, Git, or a supported
Bash yet. Homebrew bootstrap follows the remote installer trust model described
in [Remote Installer Policy](remote-installer-policy.md).

Use Homebrew directly when Homebrew is already installed and Base should be
managed like a normal formula:

```bash
brew trust basefoundry/base
brew install basefoundry/base/base
basectl setup
basectl update-profile
exec "$SHELL" -l
```

Use `install.sh` when you specifically want the source-install script to clone
or update Base and run setup/profile commands in one path. `bootstrap.sh` is the
more complete first-mile path for blank machines.

## Boundaries

`bootstrap.sh` is intentionally small. It does not configure project
repositories, install project dependencies, manage IDE settings, or update shell
startup files. Those steps belong to `basectl setup`, `basectl repo`,
`basectl update-profile`, and the project manifest workflow. When a repository
already exists and the Base baseline should go through review, use
`basectl repo init <name> --path <path> --repo <owner/name> --pr` after
bootstrap and setup are complete.
