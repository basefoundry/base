# Native Windows Support Contract

Status: proposal and implementation boundary; native Windows is not supported
by the current Base release.

This document defines the smallest credible path for bringing Base to native
Windows. It is intentionally a contract first. Git Bash and WSL2 are useful
development environments, but neither one is native Windows support and neither
one satisfies this proposal.

## Compatibility Matrix

| Environment | Current status | Runtime contract |
|---|---|---|
| macOS 14+ | Supported | Homebrew, Bash, Python, and Git |
| Ubuntu/Debian | Supported | Linux runtime with apt-backed setup |
| Ubuntu/Debian on WSL2 | Supported as Linux | `BASE_PLATFORM=linux-debian`, `BASE_HOST_ENV=wsl2` |
| Native Windows | Planned, not supported | PowerShell-first launcher and Windows-native adapters |
| Git Bash on Windows | Not a support tier | May run selected source scripts, but is not the native contract |

The README and release notes must keep native Windows in the planned column until
the Phase 1 acceptance criteria below pass on a clean `windows-latest` runner
and a clean supported Windows developer machine.

## Proposed Phase 1 Contract

The first native Windows slice targets Windows 11 22H2 or newer on x64 and
ARM64, with:

- PowerShell 7.4 or newer as the supported interactive shell;
- Git for Windows' native `git.exe` as the Git implementation;
- Python 3.10 through 3.13 from an installation managed by the user or the
  documented Windows installer route;
- GitHub CLI only for commands that explicitly need GitHub access;
- no Bash executable, Bash dotfiles, Homebrew, apt, or WSL2 dependency;
- a process launcher that passes argument arrays to child processes and does not
  reconstruct commands through a shell;
- no automatic profile mutation during install or first use.

`cmd.exe` is not a first-class interactive shell in Phase 1. It may invoke the
PowerShell entrypoint explicitly, but command completion and profile guidance
are PowerShell-specific until another shell contract is designed.

## Installation and State

The eventual clean-install route should use a versioned, signed Windows release
asset (MSI, MSIX, or an equivalently verifiable package) published with the
GitHub release. A network one-liner that downloads and executes an unpinned
script is not an acceptable installer contract.

The source checkout remains a supported contributor route. The release installer
must place the launcher and Base runtime in a versioned application location and
make updates replaceable without editing a user's project repositories.

Native Windows state is user-scoped:

| State | Location |
|---|---|
| Persistent Base state | `%LOCALAPPDATA%\Base` |
| Base cache | `%LOCALAPPDATA%\Base\Cache` |
| Temporary run data | `$env:TEMP` |
| Project checkout | User-selected workspace path; spaces are supported |

The implementation must not reuse the macOS `~/Library` or Linux `~/.cache`
locations on native Windows. A future state migration must be explicit and
backward-compatible.

## Initial Command Subset

Phase 1 is intentionally read-only or dry-run oriented. The supported subset is:

| Command surface | Phase 1 behavior |
|---|---|
| `basectl check` | Inspect the Windows runtime and report stable findings |
| `basectl doctor` | Explain readiness findings and recovery commands |
| `basectl projects list` | Discover projects under an explicit workspace path |
| `basectl projects status` | Report project state without mutation |
| `basectl projects manifest` | Parse and validate a project manifest |
| `basectl workspace status` | Report workspace membership and repository state |
| `basectl workspace check` | Run local workspace checks without credentials |
| `basectl workspace doctor` | Render workspace findings without mutation |
| `basectl setup --dry-run` | Describe planned setup without applying changes |
| `basectl gh auth status` | Report local GitHub CLI auth state when `gh` is installed |

Text and JSON output must preserve the existing inspection envelope and finding
semantics wherever the command is already a stable Base surface. Windows paths
may differ in representation, but they must remain unambiguous and parseable.

## Platform Boundary Rules

Windows-specific behavior belongs behind small platform adapters. The native
launcher and adapters own:

- `Path` and environment-variable resolution, including spaces and Unicode;
- process creation with `shell=False`-equivalent semantics;
- executable lookup and `.exe` resolution;
- UTF-8 text and CRLF/LF normalization at file boundaries;
- ACL-aware state-directory creation and permission diagnostics;
- the absence of POSIX executable bits and optional symlink privileges;
- Git's line-ending settings without rewriting repository-owned policy.

Command implementations must not scatter `if Windows` branches through their
business logic. The adapter should expose stable capabilities and return an
explicit unsupported result when a capability is not available.

The trust model remains unchanged: project-owned commands are still inspected
and explicitly approved before execution. Native Windows support must not weaken
that boundary just because process execution uses PowerShell.

## Staged Parity Model

| Phase | Outcome | Exit criteria |
|---|---|---|
| 0. Contract and CI | Make the target explicit and prevent documentation drift | This specification, visible matrix, and a Windows-hosted contract gate |
| 1. Native inspection | Ship the PowerShell launcher and read-only command subset | Clean install, `check`/`doctor`, manifest, workspace, and dry-run tests pass on Windows |
| 2. Setup and execution | Add Windows tool/runtime adapters and guarded project execution | Setup, trust, test/run, and failure recovery have native behavior and tests |
| 3. Developer parity | Add activation, demos, IDE integration, and release polish | Each feature has an explicit Windows adapter, docs, and hosted plus local validation |

The current repository is at Phase 0. This document and its CI gate do not claim
that a native Windows launcher or command subset has shipped. Phase 1 should be
implemented as a separate reviewable slice once the contract is approved.

## Explicit Deferrals

Until the required adapters exist, native Windows documentation must describe
these features as deferred:

- `basectl activate` and shell prompt integration;
- project `run`, `test`, `build`, and `demo` execution;
- manifest-declared setup mutation and package-manager adapters;
- IDE installation, extensions, and user settings;
- Bash completion, Bash startup sections, and `update-profile`;
- Homebrew and apt-backed artifacts;
- any claim that Git Bash or WSL2 is an equivalent runtime.

## Phase 1 Validation

The Windows job should run on `windows-latest` and prove the contract boundary
with no private credentials:

1. install the pinned Python test dependencies;
2. run the documentation/contract tests;
3. verify PowerShell, Python, and native Git discovery;
4. parse `base_manifest.yaml` and exercise the pure-Python manifest and workspace
   readers against paths containing spaces;
5. validate that no test invokes Bash, WSL2, Homebrew, or apt.

The job is a Phase 0 gate until the native launcher exists. It must be renamed
and expanded when Phase 1 lands so the workflow cannot be mistaken for full
Windows support.
