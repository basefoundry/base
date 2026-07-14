# Python Package Ownership

Base keeps Python code in focused packages under `cli/python/` and shared runtime
helpers under `lib/python/`. Package boundaries should follow product
responsibility, not file size.

## Current Boundaries

| Package | Primary responsibility | Notes |
| --- | --- | --- |
| `base_setup` | Setup reconciliation, manifest parsing, project diagnostics, project routing, and compatibility facades for older imports. | Keep setup/check/doctor behavior here. Do not add adapter-specific schema generation here when a focused package can own it. |
| `base_devcontainer` | Dev Containers export from Base manifests. | Owns generated `devcontainer.json` shape, unsupported/ambiguous field reporting, guarded writes, and text/JSON export rendering through `base_devcontainer.export`. |
| `base_devenv` | Not extracted yet. | #1576 should move Nix/devenv compatibility reporting here or to an equivalent focused package in a later slice. |

## Extraction Rules

- Preserve public `basectl` command behavior while moving implementation
  ownership.
- Keep compatibility facades in `base_setup` when existing internal callers may
  still import historical module names.
- Keep shared manifest models and loaders in `base_setup` until there is a
  broader manifest package boundary.
- Add structure tests when a package becomes the primary owner for a surface.
