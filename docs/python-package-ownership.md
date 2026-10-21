# Python Package Ownership

Base keeps its Python packages and shared integration helpers under
`cli/python/`. There is no Base-local `lib/python/` source tree. The reusable `base_cli` framework is
maintained in the standalone `base-cli` repository; Base owns only its provider
selection and command integration. Package boundaries should follow product
responsibility, not file size.

## Current Boundaries

| Package | Primary responsibility | Notes |
| --- | --- | --- |
| `base_setup` | Setup reconciliation, manifest parsing, project diagnostics, project routing, and compatibility facades for older imports. | Keep setup/check/doctor behavior here. Do not add adapter-specific schema generation here when a focused package can own it. |
| `base_devcontainer` | Dev Containers export from Base manifests. | Owns generated `devcontainer.json` shape, unsupported/ambiguous field reporting, guarded writes, and text/JSON export rendering through `base_devcontainer.export`. |
| `base_devenv` | Nix/devenv compatibility reporting from Base manifests. | Owns supported/unsupported/lossy/project-owned classification, summary counts, and text/JSON report rendering through `base_devenv.report`. |
| `base_cli_adapters` | Base-specific provider selection, isolated module entrypoint, paths, config, command protocol, run indexes, and history integration. | Adapts the external `base_cli` framework; does not own that framework. |
| `base_projects` | Project discovery and command dispatch, workspace manifests, selection, reports, update/setup/test orchestration, and agent briefs. | Owns `projects`, workspace operations, and project lifecycle entrypoints; consumes manifest/routing policy from `base_setup`. |
| `base_config` | User-local config commands. | Uses shared config/path adapters; see [Local Config](local-config.md). |
| `base_dev` | Developer/SRE/AI/Linux-lab profile checks and profile reporting. | Uses setup diagnostics and platform helpers; see [Command Reference](command-reference.md). |
| `base_export_context` | AI context-pack selection, assembly, and export. | Owns `export-context`; honors the context index and cache output location. |
| `base_prompt` | Repository-owned prompt selection and rendering. | Owns `prompt`; does not implement an agent runtime. |
| `base_github_projects` | GitHub Project discovery, configuration, issue fields, readiness data, and REST/GraphQL transport. | Called by the Bash GitHub workflow layer; see [GitHub Workflow](github-workflow.md). |
| `base_pr_policy` | Rendering manifest-declared PR sections and issue links. | Used by PR creation; rendering is not a merge-enforcement check. |
| `base_release` | Release readiness, provenance, BOM validation, publication, dependency inputs, and downstream version bumps. | Owns release commands and BOM utilities; see [Release Process](release-process.md). |
| `base_trust` | Manifest-command approval records, verification, status, and revocation. | Owns `trust`; uses project resolution and manifest trust semantics from setup. |
| `base_uninstall` | Removal planning, managed-resource deletion, and verification. | Owns `uninstall`; see [Uninstall And Retention](uninstall.md). |
| `base_clean` | Run-bundle temporary/cache cleanup. | Owns `clean`; separate from uninstall's state-removal scope. |
| `base_history` | History selection, display, and recording commands. | Owns `history`; shared run-index/record adapters remain in `base_cli_adapters`. |
| `base_logs` | Run log selection and rendering. | Owns `logs`; consumes history/display helpers and shared run indexes. |
| `base_version` | Version and checkout identity resolution. | Provides helpers used by launchers and workspace code; it is not a separate public CLI. |

The table covers all 18 tracked package directories. The sibling module
`base_cli_profile.py` defines Base's consumer application profile and the
`base_cli_app` factory; it is not an additional package or a copy of the
framework.

## Entrypoints And Dependencies

Public launchers remain in `bin/`; Bash dispatch delegates Python work through
`base-wrapper`. Command packages with `__main__.py` expose internal module
entrypoints, not new public executables. `base_devcontainer`, `base_devenv`,
`base_version`, and `base_cli_adapters` are library/integration packages;
the setup CLI exposes the container/devenv report actions.

The main dependency relationships are:

- Command packages use `base_cli_profile` and the external `base_cli` provider
  for lifecycle and CLI behavior. `base_cli_adapters` supplies Base-owned
  paths, configuration, protocol, provider, and evidence integration.
- `base_setup` owns shared manifest models, parsing, routing, trust semantics,
  and diagnostics consumed by project, trust, release, config, and PR-policy
  packages. Setup delegates export/report generation to `base_devcontainer`
  and `base_devenv`, which consume the shared manifest model.
- `base_projects` supplies project/workspace resolution to trust, uninstall,
  and GitHub Project helpers. Uninstall also uses the trust-store location;
  logs uses history display helpers.
- These are existing module relationships, not a claim that package imports
  form a strict acyclic graph. In particular, setup and shared adapters have
  cross-package imports; future extraction must preserve their initialization
  and compatibility behavior.

The manifest facade and historical export/report imports in `base_setup`
remain compatibility surfaces for internal callers. A facade does not transfer
feature ownership back from the focused package. See [Runtime Environment](runtime-environment.md)
for provider resolution and [Manifest Command Trust](manifest-command-trust.md#runtime-verification-consent)
for Base interpreter isolation and explicit project-runtime inspection.

## Extraction Rules

- Preserve public `basectl` command behavior while moving implementation
  ownership.
- Keep compatibility facades in `base_setup` when existing internal callers may
  still import historical module names.
- Keep shared manifest models and loaders in `base_setup` until there is a
  broader manifest package boundary.
- Add structure tests when a package becomes the primary owner for a surface.
