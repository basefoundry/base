# Base Stability Tiers

Base exposes several surfaces that users and automation can depend on: CLI
commands, JSON payloads, finding IDs, manifest schemas, generated files, and
internal helper APIs. This page defines the stability vocabulary for those
surfaces.

## Tier Definitions

| Tier | Meaning | Change policy |
| --- | --- | --- |
| Stable | Intended for user workflows, scripts, CI, and Base-managed repositories. | Preserve compatibility within the current major version. Additive changes are preferred. Breaking changes need release notes, migration guidance, and a deliberate issue or design record. |
| Experimental | Shipped for early use, compatibility planning, or report-only exploration. | May change while the surrounding workflow matures. Prefer schema versions, explicit warnings, and changelog notes when changing user-visible behavior. |
| Internal | Implementation detail for Base itself, tests, or local development. | May change without compatibility guarantees. Do not script against it unless a separate document promotes it to stable or experimental. |

## Command Surface

Commands documented in [Command Quick Reference](command-reference.md) are
stable public CLI unless that document or a focused feature document explicitly
marks the command, flag, output shape, or generated artifact as experimental.
Stable command contracts include:

- command names and documented flags;
- long-option spacing with `--option value` rather than `--option=value`;
- the stdout/stderr split for machine-readable output and usage diagnostics;
- `--dry-run` preview behavior on mutating commands that document it;
- `--ci` behavior for setup, check, and doctor;
- documented `--format json` payload families.

Compatibility aliases such as `basectl ci setup|check|doctor` are stable as
aliases, but new automation should prefer the primary command form documented in
the quick reference.

Experimental command surfaces must say so in their feature document before
teams depend on them for CI or cross-repository automation. Report-only
compatibility surfaces, such as Dev Containers and Nix/devenv planning reports,
are stable as commands but may keep individual classification details
experimental while those ecosystems mature.

## JSON And Schema-Versioned Output

Base JSON intended for automation must carry a `schema_version` when the payload
is object-shaped. `schema_version: 1` means the current payload family is stable
unless the relevant feature document says otherwise.

Stable JSON contracts include:

- diagnostic item fields for `basectl check --format json` and
  `basectl doctor --format json`, documented in
  [Doctor Finding IDs](doctor-findings.md);
- workspace manifest and workspace report schema behavior documented in
  [Workspace Manifest](workspace-manifest.md);
- local trust status JSON documented in
  [Manifest Command Trust](manifest-command-trust.md);
- redacted local config JSON documented in [Local Config](local-config.md).
- the shared v1 envelope and command-specific fields for read-only control-plane
  inspection JSON documented in [Inspection JSON](inspection-json.md).

Additive keys are allowed when they do not change the meaning of existing keys.
Removing keys, renaming keys, changing value types, or changing enum meanings is
a breaking schema change.

Markdown reports, human-readable tables, logs, and help text are human-facing
surfaces. They should remain clear and reviewable, but automation should prefer
documented JSON when a command offers it.

## Stable Finding IDs

Doctor and check finding IDs are stable automation anchors. IDs such as
`BASE-D001`, `BASE-P050`, `BASE-H001`, and `BASE-W001` are never reused after
they ship. Messages, fix text, and severity can improve, but the ID keeps the
same meaning. See [Doctor Finding IDs](doctor-findings.md).

## Internal Surfaces

The following are internal unless another document explicitly promotes them:

- direct `base_cli` package standard options rejected by `basectl`, such as
  `--debug`, `--quiet`, `--config`, `--environment`, and `--keep-temp`;
- Bash helper functions and sourced subcommand modules under
  `cli/bash/commands/basectl/subcommands/`;
- Python modules that are not documented as a public package surface;
- files under `docs/superpowers/`, which are planning artifacts rather than
  shipped product contracts;
- test fixtures, generated temporary files, and local cache layouts not listed
  in [Runtime Environment](runtime-environment.md) or a feature document.

When a user-facing workflow starts depending on an internal surface, promote
that surface deliberately by documenting its tier and adding a focused test or
contract row.
