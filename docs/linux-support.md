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
- Setup gives clear guidance instead of invoking macOS-only installers.

Full bootstrap support can come after runtime support is stable.

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

Package-manager selection belongs behind this boundary. macOS setup can use
Homebrew-specific helpers, and Ubuntu/Debian setup can later use apt-specific
helpers, but ordinary command, diagnostic, and artifact code should call the
platform boundary instead of checking `BASE_PLATFORM` directly.

Python project artifact management has a separate future seam. If system
packages become project artifacts on Linux, the Python artifact registry should
learn platform-aware providers instead of inheriting the shell setup/check
dispatch directly.

## Package Manager Mapping

Initial Ubuntu/Debian mappings:

| Base prerequisite | macOS source | Ubuntu/Debian source |
| --- | --- | --- |
| Bash 4.2+ | Homebrew `bash` | `apt install bash` |
| Python 3.13 | Homebrew `python@3.13` | documented manual install first |
| Python venv support | Homebrew `python@3.13` | `apt install python3-venv` |
| Git | Xcode Command Line Tools or Homebrew `git` | `apt install git` |
| BATS | Homebrew `bats-core` | `apt install bats` when available |
| GitHub CLI | Homebrew `gh` | GitHub CLI apt repository |
| ShellCheck | Homebrew `shellcheck` | `apt install shellcheck` |
| jq | Homebrew `jq` | `apt install jq` |
| Go for source-checkout tests | Homebrew `go` | `apt install golang-go` |

Python should be the conservative piece. Do not silently use arbitrary system
Python for Base setup unless Linux support explicitly opts into that behavior.

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
prerequisites before invoking Base, and `basectl ci` runs non-interactive
runtime checks without requiring Homebrew or Xcode on Linux. The
`ubuntu-source-checkout` job also runs the full source-checkout suite through
`bin/base-test` after preparing the Base-managed test virtual environment and
the sibling `base-bash-libs` checkout expected by source tests.

## Implementation Phases

| Phase | Status | Notes |
|---|---|---|
| 1. Split macOS-only setup checks from portable runtime checks. | Done | Initial support exists through the live `basectl ci` entry point. |
| 2. Add platform detection and explicit unsupported-platform messages. | Done for macOS setup boundaries | `basectl setup` fails clearly outside the supported macOS setup contract. Linux runtime support remains narrower than setup support. |
| 3. Make `basectl check` and `doctor` report Linux prerequisite status without requiring Homebrew or Xcode. | Future | `basectl ci` is the current Linux-friendly read-only path; broader Linux prerequisite reporting still needs implementation. |
| 4. Add Ubuntu CI coverage for read-only commands and the source-checkout suite. | Done for source-checkout validation | The `ubuntu-source-checkout` job installs hosted-runner prerequisites, runs `basectl ci check base --format json`, and runs `env -u BASE_HOME ./bin/base-test`. |
| 5. Add apt-backed setup for simple prerequisites. | Future | Keep setup conservative until the first supported Linux distribution contract is finalized. |
| 6. Revisit Python installation once the desired Linux Python distribution strategy is clear. | Future | Do not silently fall back to arbitrary system Python. |

## Non-Goals

- Do not support every Linux distribution in the first pass.
- Do not add a second manifest format for Linux.
- Do not use arbitrary `python3` silently to create Base-managed venvs.
- Do not attempt GUI IDE installation on Linux until a real project needs it.
