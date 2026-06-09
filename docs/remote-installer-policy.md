# Remote Installer Policy

Base may run remote shell installers only when they are defined by Base itself,
documented here, and reached through the setup surface that owns that trust
decision.

## Allowed Remote Installers

| Installer | URL | Where Base may use it | Opt-in |
| --- | --- | --- | --- |
| Homebrew | `https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh` | `bootstrap.sh`, `install.sh`, and `basectl setup` when Homebrew is missing on macOS | First-mile setup path; `bootstrap.sh --no-homebrew-install` can refuse this path |
| Codex CLI | `https://chatgpt.com/codex/install.sh` | `basectl setup --profile ai` | Explicit `--profile ai` |
| Claude Code | `https://claude.ai/install.sh` | `basectl setup --profile ai` | Explicit `--profile ai` |

Project manifests cannot declare arbitrary remote shell installers.

## Dry-Run And Non-Interactive Behavior

`--dry-run` prints planned remote installer commands without downloading or
executing installer content.

The `ai` profile does not prompt separately after `--profile ai` is selected.
That explicit profile flag is the opt-in boundary, so scripted and
non-interactive setup stays deterministic.

## Managed Workstations And Pinned Installers

Base intentionally follows Homebrew's official mutable installer entry point
instead of pinning a reviewed commit. Teams that require pinned, mirrored, or
managed installer content should install Homebrew and optional AI tools through
their workstation management system before running Base.

Base does not yet provide a manifest field for pinned remote installers.

## Logging And Redaction

AI profile installers run through Base's Python command runner, which preserves
live output and writes redacted stdout/stderr tails to persistent logs and
failure summaries.

Homebrew first-mile installers run before the Python setup layer may exist.
Their output is shown live by the shell installer path and is not rewritten by
Base.
