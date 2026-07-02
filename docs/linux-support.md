# Linux support plan

Base is currently Mac-first. Linux support should be added deliberately, with
Ubuntu/Debian as the first target because it covers GitHub Actions and a large
share of developer machines.

## Target Scope

Start with Ubuntu/Debian runtime support:

- Base Python CLIs run under Linux.
- `base-wrapper` can select the project venv under `~/.base.d/<project>/.venv`.
- `basectl projects list`, `check`, `doctor`, and `ci` work when
  prerequisites are already installed.
- Setup installs conservative Ubuntu/Debian apt prerequisites only after the
  user reviews `--dry-run` output and passes `--yes`.

## Platform Detection

Use `/etc/os-release` for Linux distribution detection and expose the result
through `BASE_PLATFORM`. Keep `BASE_OS` coarse: `BASE_OS=linux` on Linux, with
`BASE_PLATFORM` carrying the supported distribution family.

```bash
if [[ -r /etc/os-release ]]; then
    source /etc/os-release
fi
```

The setup layer should classify platforms into:

- `macos`
- `linux-debian`
- `linux-unknown`
- `unsupported`

Unsupported platforms should fail with explicit guidance rather than falling
through to macOS assumptions.

Do not add public `BASE_DISTRO_ID` or `BASE_ARCH` until diagnostics or package
selection need them. Distribution ID and CPU architecture are separate axes:
`BASE_PLATFORM` answers "which supported platform family is this?", while a
future `BASE_ARCH` would answer "which binary/package architecture is this?".

## Platform Policy Boundary

`BASE_PLATFORM` is an input to centralized platform policy, not a general
branch condition for feature code. `base_init.sh` owns detection and exports
`BASE_OS` / `BASE_PLATFORM`; it must not decide installer, package-manager, or
diagnostic behavior.

Setup and check behavior should inspect `BASE_PLATFORM` only through explicit
platform boundary helpers. The intended shell setup/check shape is:

- `setup_current_platform` resolves the supported platform name from the
  runtime contract.
- `setup_platform_supported` reports whether the current platform has a
  supported setup/check path.
- `setup_collect_platform_base_check_results` dispatches Base environment
  checks to platform-specific collectors.
- `setup_run_platform_install` dispatches setup/install behavior to
  platform-specific installers.

Leaf helpers should stay platform-specific rather than internally branching on
every platform. Prefer names such as `setup_collect_macos_base_check_results`,
`setup_collect_linux_debian_base_check_results`, `setup_run_macos_install`, and
`setup_run_linux_debian_install`.

Package-manager selection belongs behind this boundary. macOS setup uses
Homebrew-specific helpers, and Ubuntu/Debian setup uses apt-specific helpers,
but ordinary command, diagnostic, and artifact code should call the platform
boundary instead of checking `BASE_PLATFORM` directly.

Python project artifact management has a separate future seam. If system
packages become project artifacts on Linux, the Python artifact registry should
learn platform-aware providers instead of inheriting the shell setup/check
dispatch directly.

## Package Manager Mapping

Initial Ubuntu/Debian mappings:

| Base prerequisite | macOS source | Ubuntu/Debian source |
| --- | --- | --- |
| Bash 4.2+ | Homebrew `bash` | `apt install bash` |
| Python 3 | Homebrew `python@3.13` | `apt install python3` |
| Python venv support | Homebrew `python@3.13` | `apt install python3-venv` |
| Git | Xcode Command Line Tools or Homebrew `git` | `apt install git` |
| BATS | Homebrew `bats-core` | `apt install bats` when available |
| GitHub CLI | Homebrew `gh` | official GitHub CLI Debian/Ubuntu apt repository |
| ShellCheck | Homebrew `shellcheck` | `apt install shellcheck` |
| jq | Homebrew `jq` | `apt install jq` |
| Go for source-checkout tests | Homebrew `go` | `apt install golang-go` |

Python remains conservative by platform. macOS setup uses Base-managed
Homebrew Python. Ubuntu/Debian setup uses the platform `python3` package after
the apt-backed setup path has installed `python3` and `python3-venv`.

## Ubuntu Bootstrap

For v1.6.0, Ubuntu/Debian setup can install the simple apt prerequisites that
Base knows how to own. The mutation path is intentionally explicit:
`basectl setup --dry-run` prints the apt commands, and `basectl setup --yes`
applies them. Without `--yes`, Linux setup fails before invoking `apt`.

Use native Linux filesystem paths for source checkouts. In Parallels, keep Base
under `~/work`, not under mounted macOS shared folders, so file permissions,
line endings, symlinks, and test paths behave like a normal Linux checkout.

```bash
mkdir -p ~/work
cd ~/work
git clone https://github.com/basefoundry/base.git
git clone https://github.com/basefoundry/base-bash-libs.git
cd base

./bin/basectl setup --dry-run
./bin/basectl setup --yes
./bin/basectl setup --profile dev --dry-run
./bin/basectl setup --profile dev
```

The Ubuntu/Debian setup path runs:

```bash
sudo apt-get update
sudo apt-get install -y bash git gh python3 python3-venv python3-pip bats shellcheck jq golang-go
```

The `gh` package should come from GitHub CLI's official Debian/Ubuntu
signed apt repository/keyring when the configured distro repositories do not
provide a current package. Follow the current official instructions at
https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian, then rerun
`./bin/basectl setup --yes`.

On Ubuntu/Debian, the `dev` prerequisite profile uses apt-backed developer
tools for the initial supported set: `bats-core` maps to `bats`, `gh` maps to
`gh`, and `shellcheck` maps to `shellcheck`. Once the apt-backed setup path has
installed those tools, `./bin/basectl setup --profile dev` is idempotent and
does not require Homebrew.

GitHub CLI authentication remains a user-owned step. After `gh` is installed,
run the browser-backed flow when you need GitHub access:

```bash
gh auth login --web --git-protocol https
```

Base should check and report GitHub CLI readiness, but it should not handle
tokens or credentials. Base does not store GitHub tokens in Base-managed config.

Ubuntu desktop VMs can surface a GNOME keyring prompt such as "The password you
use to log in to your computer no longer matches that of your login keyring."
If the keyring cannot be unlocked and the VM is disposable or otherwise
acceptable for lower-security local storage, `gh` can use its documented
plain text fallback explicitly:

```bash
gh auth login --web --git-protocol https --insecure-storage
```

Use that fallback only when you accept the tradeoff: the credential is written
outside the system credential store and should be treated as a local secret.
Prefer fixing or unlocking the desktop keyring for long-lived machines.

Then run:

```bash
./bin/basectl ci check base --format text
./bin/basectl check base --format text
./bin/basectl doctor base --format text
env -u BASE_HOME ./bin/base-test
```

`base-test` expects the sibling `base-bash-libs` checkout when running from a
source checkout. If it lives somewhere else, export `BASE_BASH_LIBS_DIR` to the
directory containing its reusable Bash libraries before running the suite.

GitHub Actions hosted Ubuntu runners use the same runtime contract but prepare
prerequisites in the workflow instead of asking `basectl setup` to mutate the
machine. Apple Silicon Macs running Ubuntu in Parallels should follow the same
`basectl setup --dry-run` / `basectl setup --yes` flow; `golang-go`, `bats`,
`shellcheck`, `jq`, and `gh` are available from the hosted runner and Ubuntu
ARM64 package archives used by Parallels when the configured apt repositories
provide them.

## Shell Startup

Linux shell startup differs from macOS:

- interactive Bash usually reads `~/.bashrc`
- login Bash may read `~/.bash_profile`, `~/.bash_login`, or `~/.profile`
- Zsh behavior is broadly portable but file locations remain user-specific

The existing managed-section model should remain the abstraction. Platform
support should change which dotfiles are touched, not the managed-section
format.

## Runtime Paths

Existing path behavior already points in the right direction:

- state and venvs: `~/.base.d`
- runtime cache on Linux: `~/.cache/base`

Linux support should preserve those defaults and continue to honor the existing
environment overrides.

## CI Relationship

Linux support should make GitHub Actions a first-class validation target:

```bash
basectl ci check base --format json
basectl ci doctor base --format json
env -u BASE_HOME ./bin/base-test
```

The first CI-compatible milestone is live: workflows install their own
prerequisites before invoking Base, and `basectl ci`, `basectl check`, and
`basectl doctor` run Linux runtime checks without requiring Homebrew or Xcode.
The `ubuntu-source-checkout` job also runs the full source-checkout suite
through `bin/base-test` after preparing the Base-managed test virtual
environment and the sibling `base-bash-libs` checkout expected by source tests.

## Implementation Phases

| Phase | Status | Notes |
|---|---|---|
| 1. Split macOS-only setup checks from portable runtime checks. | Done | Initial support exists through the live `basectl ci` entry point. |
| 2. Add platform detection and explicit unsupported-platform messages. | Done | `BASE_PLATFORM` classifies Ubuntu/Debian as `linux-debian`, keeps `BASE_OS=linux`, and fails unsupported platforms explicitly. |
| 3. Make `basectl check` and `doctor` report Linux prerequisite status without requiring Homebrew or Xcode. | Done | `check` and `doctor` report Ubuntu/Debian prerequisite findings with apt-oriented recovery hints. |
| 4. Add Ubuntu CI coverage for read-only commands and the source-checkout suite. | Done for source-checkout validation | The `ubuntu-source-checkout` job installs hosted-runner prerequisites, runs `basectl ci check base --format json`, and runs `env -u BASE_HOME ./bin/base-test`. |
| 5. Add conservative Ubuntu setup guidance. | Done | `basectl setup --dry-run` previews Ubuntu/Debian apt prerequisites before mutation. |
| 6. Add apt-backed setup for simple prerequisites. | Done | `basectl setup --yes` runs `apt-get update`, installs the supported apt package list, creates the Base virtual environment, installs Base Python bootstrap packages, invokes the project setup layer, and seeds user config. |
| 7. Make `basectl setup --profile dev` use apt-backed developer tools on Ubuntu/Debian. | Done | The dev profile maps `bats-core`, `gh`, and `shellcheck` to apt-backed tools and skips them when already installed. |
| 8. Polish GitHub CLI install/auth guidance. | Future | Keep token handling user-owned; add clearer setup/check/docs guidance for official `gh` install sources and login/keyring recovery. |

## Non-Goals

- Do not support every Linux distribution in the first pass.
- Do not add a second manifest format for Linux.
- Do not use arbitrary `python3` silently on macOS to create Base-managed venvs.
- Do not attempt GUI IDE installation on Linux until a real project needs it.
