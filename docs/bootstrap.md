# First-Mile Bootstrap

`bootstrap.sh` is Base's preferred entry point for a new or uncertain macOS
machine. It handles the minimum prerequisites needed before `basectl` can take
over: Homebrew, Git, Bash 4.2+, and either a source checkout or Homebrew
installation of Base.

## Quick Start

Run the bootstrapper from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash
```

The bootstrapper verifies macOS, installs missing first-mile prerequisites, and
then prints the exact commands needed to finish setup. For the default source
checkout path, the handoff usually looks like:

```bash
~/work/base/bin/basectl setup
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

`bootstrap.sh` does not edit shell startup files automatically. Shell profile
integration remains an explicit `basectl update-profile` step so the user can
see what was installed before Base changes future interactive shells.

## Install Mode

Choose a mode explicitly when the default should not infer one:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash -s -- --source
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash -s -- --brew
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
bootstrap.sh --repo-url https://github.com/codeforester/base.git
bootstrap.sh --branch <name>
bootstrap.sh --no-homebrew-install
bootstrap.sh --dry-run
```

Use `--dry-run` to inspect the planned prerequisite installs and Base install
route without changing the machine.

## Contributor Path

Contributors should prefer source mode:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash -s -- --source
~/work/base/bin/basectl setup --profile dev
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

The `dev` profile installs contributor prerequisites such as BATS, the GitHub
CLI, and ShellCheck. After that, use `basectl test base` for the dogfood test
contract.

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
brew install codeforester/base/base
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
