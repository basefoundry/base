# Linux support plan

Base is currently Mac-first. Linux support should be added deliberately, with
Ubuntu/Debian as the first target because it covers GitHub Actions and a large
share of developer machines.

## Target Scope

Start with Ubuntu/Debian runtime support:

- Base Python CLIs run under Linux.
- `base-wrapper` can select the project venv under `~/.base.d/<project>/.venv`.
- `basectl projects list`, `check`, `doctor`, and future `ci` work when
  prerequisites are already installed.
- Setup gives clear guidance instead of invoking macOS-only installers.

Full bootstrap support can come after runtime support is stable.

## Platform Detection

Use `/etc/os-release` for Linux distribution detection:

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

## Package Manager Mapping

Initial Ubuntu/Debian mappings:

| Base prerequisite | macOS source | Ubuntu/Debian source |
| --- | --- | --- |
| Bash 4.2+ | Homebrew `bash` | `apt install bash` |
| Python 3.13 | Homebrew `python@3.13` | documented manual install first |
| BATS | Homebrew `bats-core` | `apt install bats` when available |
| GitHub CLI | Homebrew `gh` | GitHub CLI apt repository |

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
```

The first CI-compatible milestone documents manual prerequisite setup in the
workflow before invoking Base. `basectl ci` then runs runtime checks without
requiring Homebrew or Xcode on Linux.

## Implementation Phases

1. Split macOS-only setup checks from portable runtime checks. Initial support
   exists through `basectl ci`.
2. Add Linux platform detection and explicit unsupported-platform messages.
3. Make `basectl check` and `doctor` report Linux prerequisite status without
   requiring Homebrew or Xcode.
4. Add Ubuntu CI coverage for read-only commands.
5. Add apt-backed setup for simple prerequisites.
6. Revisit Python installation once the desired Linux Python distribution
   strategy is clear.

## Non-Goals

- Do not support every Linux distribution in the first pass.
- Do not add a second manifest format for Linux.
- Do not use arbitrary `python3` silently to create Base-managed venvs.
- Do not attempt GUI IDE installation on Linux until a real project needs it.
