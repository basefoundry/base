# Remote Installer Policy Design

Issue: #513

## Goal

Base should have one explicit policy for remote shell installers used during
bootstrap and prerequisite profile setup. Users should be able to see which
URLs Base may execute, what opt-in is required, how dry-run behaves, and what
logging/redaction guarantees apply.

## Scope

This change covers the remote installers Base currently owns:

- Homebrew official installer:
  `https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh`
- Codex CLI official installer:
  `https://chatgpt.com/codex/install.sh`
- Claude Code official installer:
  `https://claude.ai/install.sh`

It does not add arbitrary manifest setup hooks, project-defined remote
installers, pinned installer support, or managed-device provisioning
integration. Those remain future work.

## Policy

Base allows only documented, internally defined remote shell installers.
Project manifests cannot declare remote shell installers.

Homebrew is the only first-mile installer Base may run by default, and only
when Homebrew is missing on a macOS setup path. That trust decision stays
aligned with Homebrew's supported mutable `install/HEAD/install.sh` entry
point. Teams that need pinned or reviewed installer content should provision
Homebrew outside Base before running `basectl setup`.

AI tool installers are not part of default setup, `dev`, or `sre`. They require
explicit `--profile ai` selection. That explicit profile flag is the consent
boundary; Base will not add a second interactive prompt in this slice. Keeping
non-interactive behavior deterministic is more valuable than adding a prompt
that CI or scripted setup must bypass.

## Runtime Behavior

`basectl setup --profile ai --dry-run` shows the planned remote installer
commands and does not download or execute installer content.

`basectl setup --profile ai` may execute only allowlisted AI installer URLs. The
Python `base_dev` profile layer will derive installer commands from structured
tool metadata and reject any AI tool whose URL is not on the allowlist.

`basectl check --profile ai` and `basectl doctor --profile ai` remain read-only:
they check whether the tools exist and can report versions, but they do not
download or execute installers.

## Logging And Redaction

AI profile installer processes run through `base_setup.process.run_command()`.
Their live terminal output remains visible to the user. Persistent debug logs
and failure summaries use the redacted subprocess output added for #508.

Homebrew first-mile installers run in shell bootstrap/setup paths before the
Python setup layer may exist. Base dry-run output names the official installer
URL without downloading it. Live installer output is not rewritten by Base; a
managed-device or pinned-installer environment should install Homebrew before
Base if it needs stronger logging or review controls.

## Tests

Add focused `base_dev` tests for:

- AI installer URLs are centrally allowlisted.
- `--profile ai --dry-run` prints the allowlisted remote installer commands and
  policy context.
- Non-interactive setup remains deterministic when `--profile ai` is explicit.
- An AI tool with an unallowlisted remote installer URL fails before
  `run_command()` is called.
- Default `setup --dry-run` does not include AI remote installer URLs.

Run the focused `base_dev` tests first, then `env -u BASE_HOME ./bin/base-test`.
