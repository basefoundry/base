# IDE Diagnostic Cache Design

Issue: #509

## Goal

When `basectl check` or `basectl doctor` evaluates IDE requirements, Base should
probe each IDE once per diagnostic run and then produce the same per-extension
and per-setting findings from that cached state.

## Scope

This change is limited to read-only diagnostics for supported IDEs:

- extension checks using `<ide-cli> --list-extensions`
- user settings checks using the IDE `settings.json`

Setup behavior remains unchanged. Base will not persist diagnostic state across
runs, and it will not broaden IDE ownership beyond workstation readiness.

## Current Problem

`check_ide_extensions()` delegates to `check_ide_extension()` once per declared
extension. Each call checks CLI availability and lists installed extensions.

`check_ide_settings()` delegates to `check_ide_setting()` once per declared
setting. Each call resolves the settings file and reads/parses the JSON.

That keeps finding generation simple, but it repeats expensive and potentially
noisy probes when a manifest declares several extensions or settings for the
same IDE.

## Design

Add an in-memory `IdeDiagnosticSnapshot` for one IDE during one diagnostic
collection pass.

The snapshot will lazily cache:

- whether the IDE CLI is available on `PATH`
- the installed extension set or extension-listing error
- the resolved settings file path
- parsed settings JSON or settings-read error

`check_ide_extensions()` will create one snapshot per IDE that declares
extensions, then pass that snapshot to each per-extension finding builder.

`check_ide_settings()` will create one snapshot per IDE that declares settings,
then pass that snapshot to each per-setting finding builder.

The individual `check_ide_extension()` and `check_ide_setting()` helpers will
keep their public calling shape by creating a fresh snapshot when no snapshot is
provided. That preserves focused unit tests and any direct internal callers
while allowing collection-level code to reuse probe results.

## Output Contract

The output remains one `ArtifactCheck` per declared extension and one
`ArtifactCheck` per declared setting. Existing finding IDs, messages, fixes, and
ordering should remain stable except that repeated probes are eliminated.

## Error Behavior

If extension listing fails, every extension declared for that IDE receives the
same `BASE-P111` finding generated from the cached error.

If the settings file cannot be parsed, every setting declared for that IDE
receives the same `BASE-P120` finding generated from the cached error.

If the IDE CLI is missing, every extension declared for that IDE receives the
same `BASE-P110` finding generated from the cached CLI availability result.

## Tests

Add focused tests that prove:

- extension diagnostics call `process.command_exists()` and
  `list_ide_extensions()` once for one IDE with multiple extensions
- settings diagnostics call `ide_settings_file()` and `read_ide_settings()` once
  for one IDE with multiple settings
- the generated finding list still contains one finding per manifest entry in
  deterministic order

Run the focused IDE tests first, then the full `env -u BASE_HOME ./bin/base-test`
suite.
