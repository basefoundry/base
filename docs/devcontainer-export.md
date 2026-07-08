# Devcontainer Export

`basectl devcontainer [project]` derives a minimal Dev Containers configuration
from a Base project manifest. The default mode is a dry-run preview: it reads
`base_manifest.yaml`, prints the generated `.devcontainer/devcontainer.json`
content, and reports which manifest fields were supported, unsupported, or
ambiguous.

```bash
basectl devcontainer demo
basectl devcontainer demo --format json
```

Use `--workspace <path>` when resolving a named project outside the configured
workspace. Use `--write` only after reviewing the preview:

```bash
basectl devcontainer demo --format json
basectl devcontainer demo --write
```

When writing, Base creates `.devcontainer/devcontainer.json` under the project
root and refuses to replace an existing file. There is no force flag; project
owned Dev Containers files remain project owned.

## Supported Fields

The current export supports:

- `project.name` as `name`
- `ide.vscode.extensions` as `customizations.vscode.extensions`
- `ide.vscode.settings` as `customizations.vscode.settings`

The JSON report includes the generated `devcontainer` object and the target path.
This makes the dry-run output stable enough for review and automation without
requiring a container runtime.

## Unsupported And Ambiguous Fields

Base deliberately does not guess container behavior for manifest fields that
carry host setup, project commands, diagnostics, or runtime policy. The export
reports those fields instead of silently dropping them.

Examples include:

- `brewfile`, `mise`, `artifacts`, `test`, `commands`, `build`, and activation
  sources as unsupported
- `python.manager` and `python.requires_python` as ambiguous until Base has an
  explicit image or feature policy
- non-VS Code IDE customizations as unsupported

This command does not build images, start containers, install packages, execute
project hooks, or replace Dev Containers as the owner of containerized
development behavior.
