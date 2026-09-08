# Base Stability Tiers

Status: maintained compatibility reference
Last reviewed: 2026-07-25

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

The `basectl ci setup|check|doctor` compatibility alias remains deprecated
through the v1.x compatibility window. New automation should use the primary
command form documented in the quick reference.

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
- redacted local config JSON documented in [Local Config](local-config.md);
- side-effect-free lifecycle listing payloads from `basectl run --list
  --format json` and `basectl build --list --format json`, documented in the
  [Command Quick Reference](command-reference.md);
- the shared v1 envelope and command-specific fields for read-only control-plane
  inspection JSON documented in [Inspection JSON](inspection-json.md).
- `basectl workspace agent-brief --format json`, whose schema version 1 is
  published at
  [`schemas/workspace-agent-brief.json`](schemas/workspace-agent-brief.json).
- `basectl workspace update --format json`, whose schema version 1 is published
  at [`schemas/workspace-update.json`](schemas/workspace-update.json).

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

## Automated Enforcement

The Stable command, JSON, schema, and finding-ID contracts are checked by the
`Stable compatibility` job in `.github/workflows/tests.yml`. The checker uses
the normalized fixture in `docs/stability-baseline/current.json`. Command flags
are read from the source-owned `basectl <command> --help` output during CI;
Markdown prose is not used as the command contract. The initial fixture records
`v1.8.0` as its provenance in `docs/stability-baseline/v1.8.0.json`, and the
accepted current fixture is compared against that provenance on every run.

The check allows additive commands, flags, object keys, enum values, schema
definitions, and finding IDs. It fails when an accepted command or flag is
removed, a documented option changes from value-taking to valueless (or the
reverse), a JSON field changes type, a stable enum value disappears, a
published schema field is removed, or a finding ID is reused with a different
meaning.

An intentional breaking change must update `current.json`, update this page
and the affected contract documentation with migration guidance, and add a
non-placeholder changelog bullet beginning exactly with
`Stability compatibility:`. The CI job checks that fixture updates include that
changelog marker. Changes from v1.8.0 must also be listed in
`current.json`'s `baseline_exceptions` with a reason; stale or unapproved
exceptions fail the check. The v1.8.0 provenance file is retained so the
accepted baseline remains auditable and is never rewritten as the current
compatibility fixture advances.

## Internal Surfaces

The following are internal unless another document explicitly promotes them:

- direct `base_cli` package standard options rejected by `basectl`, such as
  `--debug`, `--quiet`, `--log-file`, `--config`, and `--environment`;
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

The wrapper-level `basectl -x <command>` and `basectl --keep-temp <command>`
flags are public and stable; they are intentionally separate from the rejected
direct `base_cli` package options listed above.
