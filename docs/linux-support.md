# Linux support

Base is macOS-primary with a supported Ubuntu/Debian source-checkout path. Linux
support should continue to grow deliberately, with Ubuntu/Debian as the first
target because it covers GitHub Actions and a large share of developer machines.

## Supported Ubuntu/Debian Contract

This is Base's current Ubuntu/Debian source-checkout support contract:

- `bootstrap.sh --source --dry-run` prints the manual Ubuntu/Debian checkout
  path instead of running `sudo apt` from a piped script.
- `basectl check`, `basectl doctor`, and `--ci` mode report Ubuntu/Debian
  runtime readiness without requiring Homebrew or Xcode.
- `basectl setup --dry-run` previews supported apt-backed setup work before any
  mutation.
- `basectl setup` prompts before Ubuntu/Debian system changes, and
  `basectl setup --yes` is the non-interactive apply mode for reviewed setup.
- `basectl setup --profile dev` can install the Base-owned developer
  prerequisites that have explicit Ubuntu/Debian mappings.

Base does not ship a Debian package, own every project runtime dependency, or
claim support for every Linux distribution. Broader Linux families, WSL, native
Windows, GUI IDE setup on Linux, and project-specific dependency ownership need
separate product decisions and platform adapters.

## Target Scope

Start with Ubuntu/Debian runtime support:

- Base Python CLIs run under Linux.
- `base-wrapper` can select the project venv under `~/.base.d/<project>/.venv`.
- `basectl projects list`, `check`, `doctor`, and `ci` work when
  prerequisites are already installed.
- Setup installs conservative Ubuntu/Debian apt prerequisites after dry-run
  review plus either interactive consent or `--yes` for unattended runs.

## Setup Contract

Setup behavior should stay platform-invariant as Base adds more operating
systems:

- `basectl check` inspects and reports readiness without changing the machine.
- `basectl setup --dry-run` previews planned changes without changing the
  machine.
- `basectl setup` and `basectl setup --profile <name>` apply setup on supported
  platforms.
- `--yes` means non-interactive consent for unattended setup. It is not the
  switch that turns setup from dry-run to apply.

Platform-specific package manager work belongs behind this contract. macOS can
use Homebrew, Ubuntu/Debian can use apt, and future Red Hat, CentOS, Windows, or
other platform families should add their own installer/check adapters without
changing what these user-facing commands mean.

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

Ubuntu/Debian bootstrap is intentionally conservative. The first-mile
`bootstrap.sh` entry point detects Ubuntu/Debian Linux and prints the manual
source-checkout path instead of running `sudo apt` from a piped script:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source --dry-run
```

The printed path includes apt prerequisites, cloning Base and
`base-bash-libs`, `basectl setup --dry-run`, `basectl setup --yes`, and
`basectl update-profile`. The printed `setup --yes` handoff is for users who
want to paste the reviewed command sequence into an unattended shell; an
interactive user can run `basectl setup` after reviewing `--dry-run` and confirm
the Ubuntu/Debian system-change prompt.

The focused Bash prerequisite repair path is the one exception. When Base is
already present but the current shell is too old for `basectl`, review and run:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --ensure-bash --dry-run
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --ensure-bash --yes
```

On Ubuntu/Debian, `--ensure-bash` previews and then runs only:

```bash
sudo apt-get update
sudo apt-get install -y bash
```

It does not clone Base, install Python, create virtual environments, install
developer tools, or run project setup.

Ubuntu/Debian setup can install the simple apt prerequisites that Base knows
how to own. The mutation path is intentionally explicit: `basectl setup
--dry-run` prints the apt commands, interactive `basectl setup` prompts before
system changes, and non-interactive setup requires `--yes` before invoking
`apt`, writing keyrings/source lists, or running remote installer bootstraps.

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

## Source-Checkout Smoke Checklist

Run this checklist from a fresh Ubuntu/Debian source checkout after reviewing
the setup dry-run:

```bash
./bin/basectl setup --dry-run
./bin/basectl setup --yes
./bin/basectl setup --profile dev --dry-run
./bin/basectl setup --profile dev
./bin/basectl check --ci base --format text
./bin/basectl check base --format text
./bin/basectl doctor base --format text
env -u BASE_HOME ./bin/base-test
```

Expected result: setup reports reviewed Ubuntu/Debian apt-backed changes before
mutation, the check/doctor commands report runtime readiness or actionable
warnings, and `base-test` completes when the sibling `base-bash-libs` checkout
is available.

The Ubuntu/Debian setup path runs:

```bash
sudo apt-get update
sudo apt-get install -y bash git python3 python3-venv python3-pip bats shellcheck jq golang-go
```

`basectl check` and `basectl doctor` keep the basic Ubuntu/Debian runtime path
separate from contributor tooling. Missing `gh`, BATS, ShellCheck, `jq`, or Go
are advisory warnings unless another runtime prerequisite is also failing.

The `gh` package should come from GitHub CLI's official Debian/Ubuntu
signed apt repository/keyring, not the default distro package. Base setup uses
the current official repository shape documented at
https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian.

On Ubuntu/Debian, the `dev` prerequisite profile uses apt-backed developer
tools. `bats-core` maps to default apt package `bats`, and `shellcheck` maps to
default apt package `shellcheck`. `basectl setup --profile dev` does not install
`gh` from default apt repositories; it configures GitHub CLI's official
Debian/Ubuntu signed apt repository/keyring and then installs `gh` from that
source. Authentication remains user-owned. Once the apt-backed setup path has
installed the Base-owned tools, `./bin/basectl setup --profile dev` is
idempotent and does not require Homebrew.

Project-level `brewfile` delegates remain macOS/Homebrew-only. On
Ubuntu/Debian, Base validates the Brewfile path but skips `brew bundle` setup and
reports a warning from check/doctor instead of asking users to install Homebrew.
Linux project prerequisites should use a platform-native project path. For
projects that declare `python.manager: uv` or command-level `runner: uv`,
`basectl setup <project> --dry-run` shows the planned `uv` bootstrap when `uv`
is missing, and `basectl setup <project> --yes` installs `uv` before delegating
Python setup to `uv sync`. Base does not install `uv` for projects that have not
opted into the uv contract.

Projects that declare a `mise` config use the same Ubuntu/Debian review gate:
`basectl setup <project> --dry-run` shows the planned `mise` bootstrap when
`mise` is missing, and `basectl setup <project> --yes` installs `mise` before
delegating project tool setup to `mise install`. Base does not automatically
trust project-owned mise configs; if mise reports an untrusted config, review it
and run `mise trust <path-to-mise-config>` before retrying setup.

Project tool artifacts are still intentionally conservative on Linux. The first
platform-aware mapping is `tool:bats-core`: the manifest keeps the portable
artifact name, macOS continues to use Homebrew package `bats-core`, and
Ubuntu/Debian treats the artifact as satisfied by system package `bats`.

IDE extension checks are developer-workstation polish, not part of the default
Ubuntu/Debian runtime acceptance path. Default `basectl check` and
`basectl check --ci` runs do not fail solely because editor CLIs such as `code`
are absent; run with `--profile dev` when you want Base to validate declared IDE
extensions.

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
./bin/basectl check --ci base --format text
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

## macOS Linux Lab

Mac developers can use the optional `linux-lab` prerequisite profile to prepare
a local Ubuntu VM host without making Linux support part of the default
developer profile:

```bash
basectl setup --profile linux-lab --dry-run
basectl setup --profile linux-lab
basectl check --profile linux-lab
basectl doctor --profile linux-lab
```

The profile checks the `multipass` CLI and installs Multipass on macOS through
the Homebrew cask path when setup is run without `--dry-run`. It does not create
or mutate VM instances. After Multipass is installed, create a lab instance
explicitly:

```bash
multipass launch 24.04 \
  --name ubuntu-dev \
  --cpus 8 \
  --memory 16G \
  --disk 120G \
  --mount "$HOME/work:/home/ubuntu/work"
multipass shell ubuntu-dev
```

Apple Silicon Macs normally run ARM64 Ubuntu guests. That is useful for local
Linux preflight work, but hosted `ubuntu-latest` GitHub Actions runners remain
a separate validation target.

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
basectl check --ci base --format json
basectl doctor --ci base --format json
env -u BASE_HOME ./bin/base-test
```

The first CI-compatible milestone is live: workflows install their own
prerequisites before invoking Base, and `basectl check --ci`, `basectl check`,
and `basectl doctor --ci` run Linux runtime checks without requiring Homebrew or
Xcode.
The `ubuntu-source-checkout` job also runs the full source-checkout suite
through `bin/base-test` after preparing the Base-managed test virtual
environment and the sibling `base-bash-libs` checkout expected by source tests.

## Implementation Phases

| Phase | Status | Notes |
|---|---|---|
| 1. Split macOS-only setup checks from portable runtime checks. | Done | Initial support exists through `--ci` mode on setup/check/doctor, with `basectl ci` retained as a compatibility alias. |
| 2. Add platform detection and explicit unsupported-platform messages. | Done | `BASE_PLATFORM` classifies Ubuntu/Debian as `linux-debian`, keeps `BASE_OS=linux`, and fails unsupported platforms explicitly. |
| 3. Make `basectl check` and `doctor` report Linux prerequisite status without requiring Homebrew or Xcode. | Done | `check` and `doctor` report Ubuntu/Debian prerequisite findings with apt-oriented recovery hints. |
| 4. Add Ubuntu CI coverage for read-only commands and the source-checkout suite. | Done for source-checkout validation | The `ubuntu-source-checkout` job installs hosted-runner prerequisites, runs `basectl check --ci base --format json`, and runs `env -u BASE_HOME ./bin/base-test`. |
| 5. Add conservative Ubuntu setup guidance. | Done | `basectl setup --dry-run` previews Ubuntu/Debian apt prerequisites before mutation. |
| 6. Add apt-backed setup for simple prerequisites. | Done | `basectl setup --yes` runs `apt-get update`, installs the supported apt package list, creates the Base virtual environment, installs Base Python bootstrap packages, invokes the project setup layer, and seeds user config. |
| 7. Make `basectl setup --profile dev` use apt-backed developer tools on Ubuntu/Debian. | Done | The dev profile maps `bats-core` and `shellcheck` to apt-backed tools and skips them when already installed. |
| 8. Polish GitHub CLI install/auth guidance. | Done | Keep token handling user-owned; point Linux setup/check/docs to GitHub CLI's official Debian/Ubuntu install source and login/keyring recovery. |

## Non-Goals

- Do not support every Linux distribution in the first pass.
- Do not add a second manifest format for Linux.
- Do not use arbitrary `python3` silently on macOS to create Base-managed venvs.
- Do not attempt GUI IDE installation on Linux until a real project needs it.
