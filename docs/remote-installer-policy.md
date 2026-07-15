# Remote Installer Policy

Base may run remote shell installers only when they are defined by Base itself,
documented here, and reached through the setup surface that owns that trust
decision.

Consent and installer integrity are separate decisions. A setup flag authorizes
Base to take the documented install path; it does not authenticate bytes served
by a mutable URL. Base discloses that limitation whenever it uses an official
mutable installer without checksum verification.

## Allowed Remote Installers

| Installer | URL | Where Base may use it | Opt-in |
| --- | --- | --- | --- |
| Homebrew | `https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh` by default; managed environments may provide a pinned installer location with an expected SHA-256 | `bootstrap.sh`, `install.sh`, and `basectl setup` when Homebrew is missing on macOS | First-mile setup path; `bootstrap.sh --no-homebrew-install` can refuse this path |
| Codex CLI | `https://chatgpt.com/codex/install.sh` | `basectl setup --profile ai` | Explicit `--profile ai` |
| Claude Code | `https://claude.ai/install.sh` | `basectl setup --profile ai` | Explicit `--profile ai` |
| uv | `https://astral.sh/uv/install.sh` by default; managed environments may provide a local, mirrored, or pinned installer with an expected SHA-256 | `basectl setup <project>` on Debian-family Linux when a manifest declares `python.manager: uv` or a `runner: uv` command and uv is missing | Explicit `--yes`; `--dry-run` only previews |
| mise | `https://mise.run` by default; managed environments may provide a local, mirrored, or pinned installer with an expected SHA-256 | `basectl setup <project>` on Debian-family Linux when a manifest declares mise configuration and mise is missing | Explicit `--yes`; `--dry-run` only previews |

Project manifests cannot declare arbitrary remote shell installers.
Project-owned command strings remain governed by the separate manifest-command
trust boundary; they do not become Base-owned installers or extend this list.

The maintained `templates/project-install.sh` is copied into another project
and governed by the [Project Installer](project-installers.md) contract. It is
not a Base runtime installer entry point.

## Dry-Run And Non-Interactive Behavior

`--dry-run` prints planned remote installer commands without downloading or
executing installer content.

The `ai` profile does not prompt separately after `--profile ai` is selected.
That explicit profile flag is the opt-in boundary, so scripted and
non-interactive setup stays deterministic.

uv and mise bootstrap only after the project manifest requires the tool, the
tool is missing, the host is Debian-family Linux, and setup has received
`--yes`. Base clears inherited setup consent before parsing command-line flags,
so exporting `BASE_SETUP_YES` does not bypass that boundary.

## Managed Workstations And Pinned Installers

Base intentionally follows each tool's official mutable installer entry point
instead of pinning a reviewed commit by default. When Base uses a default path,
it identifies the URL as mutable and explicitly says that the script is not
checksum-verified. The Codex CLI and Claude Code paths do not currently expose
a Base-managed checksum override.

Teams that require pinned, mirrored, or managed Homebrew installer content can
opt in by setting both a
Homebrew installer location and its expected SHA-256 before running Base:

- all Homebrew entry points: `BASE_HOMEBREW_INSTALLER_URL` and
  `BASE_HOMEBREW_INSTALLER_SHA256`
- `install.sh` only: `BASE_INSTALL_HOMEBREW_INSTALLER_URL` and
  `BASE_INSTALL_HOMEBREW_INSTALLER_SHA256`
- `bootstrap.sh` only: `BASE_BOOTSTRAP_HOMEBREW_INSTALLER_URL` and
  `BASE_BOOTSTRAP_HOMEBREW_INSTALLER_SHA256`
- `basectl setup` only: `BASE_SETUP_HOMEBREW_INSTALLER_URL` and
  `BASE_SETUP_HOMEBREW_INSTALLER_SHA256`

When any pinned Homebrew installer variable is present, Base requires both the
installer location and expected SHA-256. Missing or mismatched values fail
closed before installer execution. Local file paths, `file://` URLs, and remote
URLs are accepted as installer locations.

Debian-family Linux setup provides equivalent paired overrides for uv and mise:

- uv: `BASE_SETUP_UV_INSTALLER_URL` and
  `BASE_SETUP_UV_INSTALLER_SHA256`
- mise: `BASE_SETUP_MISE_INSTALLER_URL` and
  `BASE_SETUP_MISE_INSTALLER_SHA256`

For uv and mise, either both variables must be present or neither may be
present. The URL may be a local path, a local `file://` URL, or an HTTPS URL;
HTTP and other schemes fail closed. Base fetches or copies the installer once
into a user-private temporary directory, verifies the expected SHA-256, runs
that same temporary file without interpolating its location into shell source,
and removes the temporary copy afterward. Tests exercise these paths without
network access.

The checksum covers the installer script bytes only. It does not authenticate
packages, binaries, or other content that the installer downloads afterward.
Managed environments that need end-to-end provenance should use a reviewed
installer which itself pins and verifies downstream artifacts.

Base does not provide a manifest field for arbitrary pinned remote installers.

## Logging And Redaction

Python-owned installers are registered in one code policy. AI profile
installers and the uv/mise verified-file path run through Base's Python command
runner, which preserves live output and writes redacted stdout/stderr tails to
persistent logs and failure summaries.

Homebrew first-mile installers run before the Python setup layer may exist.
Their output is shown live by the shell installer path and is not rewritten by
Base. Those standalone entry points remain independent of Python; contract
tests keep their default URL and this policy table synchronized.
