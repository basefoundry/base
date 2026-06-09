# Workspace Manifests Implementation Plan

Issue: #511
Branch: feature/511-20260609-workspace-manifests

## Scope

Add first runtime support for explicit local workspace manifests:

```bash
basectl workspace status --manifest <path>
basectl workspace check --manifest <path>
basectl workspace doctor --manifest <path>
```

The implementation is read-only. It must not clone, pull, reset, rewrite, or
otherwise mutate repositories.

## V1 Decisions

- `--manifest` is optional. Without it, existing discovered-only behavior and
  output stay compatible.
- Workspace manifests are local files only.
- `schema_version` is required and must be `1`.
- `workspace.name` is required.
- `repos` is a required list.
- `repos[].name` is required and is the direct child directory name under the
  workspace root.
- `repos[].required` defaults to `true`.
- `repos[].url` and `repos[].default_branch` are optional report metadata.
- A required repo missing from disk is an error.
- An optional repo missing from disk is a warning.
- A present expected repo without `base_manifest.yaml` is allowed and reported
  as present with Base project diagnostics not applicable.
- A discovered Base-managed project not listed in the manifest is a warning.
- Invalid local project manifests are reported per project without stopping the
  workspace scan.

## Steps

1. Add workspace manifest parser tests for valid manifests, defaults, unsupported
   schema versions, missing required fields, duplicate repo names, invalid repo
   names, unknown keys, and non-boolean `required`.
2. Implement `base_projects.workspace_manifest` with small immutable data
   classes and `read_workspace_manifest(path)`.
3. Add `--manifest <path>` to the Python command surface and shell help.
4. Add manifest-aware status/check/doctor planning that combines expected repos
   and discovered projects.
5. Add stable workspace finding IDs for missing required repos, missing optional
   repos, extra discovered projects, and present non-Base expected repos.
6. Extend JSON and text output only when `--manifest` is supplied, keeping the
   no-manifest shape stable.
7. Update docs and changelog.
8. Validate targeted tests, BATS wrapper tests, `git diff --check`, and
   `env -u BASE_HOME ./bin/base-test`.
