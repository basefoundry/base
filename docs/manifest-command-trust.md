# Manifest Command Trust

Base project manifests can declare commands that run project-owned shell code.
Those declarations are useful because they make project workflows discoverable,
but they also create a local trust boundary: cloning or pulling a repository
should not by itself imply consent to execute that repository's commands.

This document defines the allow model for manifest-declared command execution.

## Goals

- Require explicit local approval before first execution of manifest-declared
  project code from an unfamiliar repository.
- Keep read-only inspection paths available before approval.
- Re-require approval when the manifest command contract changes.
- Store approval in Base-managed local state, not in the project repository.
- Behave predictably in non-interactive shells and CI.

## Non-Goals

- Do not sandbox project commands.
- Do not claim that linting or approval makes hostile project code safe.
- Do not block read-only manifest validation or workspace reporting.
- Do not make workspace clone or workspace pull imply command execution trust.

## Commands Covered

Base requires an allow record before commands that execute manifest-declared
project code:

- `basectl test [project]`
- `basectl run [project] <command>`
- `basectl build [project] [target...]`
- `basectl demo [project]`
- `basectl activate <project>` when it will source `activate.source` entries

These paths remain allowed before approval because they inspect or report
without executing project runtimes or delegated tool configuration:

- `basectl projects list`
- `basectl workspace status`, `check`, and `doctor`
- `basectl run [project] --list`
- `basectl build [project] --list`
- `basectl test [project] --dry-run`
- `basectl run [project] <command> --dry-run`
- `basectl build [project] [target...] --dry-run`
- `basectl demo [project] --dry-run`
- `basectl check [project]` and `basectl doctor [project]`
- `basectl export-context [project]`

Setup delegates such as Brewfiles, `mise install`, and artifacts are separate
trust boundaries. Project-originated IDE mutations have their own explicit
approval boundary: `basectl setup --dry-run` shows the complete app, extension,
and user-settings plan, and applying that plan requires
`--allow-project-ide-mutations`. `--yes` never supplies this approval. This
keeps command execution trust and machine-wide IDE mutation consent separate.

## Runtime verification consent

Project `check` and `doctor`, workspace `check` and `doctor`, and workspace
status/onboarding inspect manifests, files, and environment presence by default.
An executable file is reported as `present_unverified`, not proof of a working
runtime. Package inventories and Brewfile, mise, or uv configuration checks
remain unverified when they would execute project-controlled inputs.

After reviewing the project interpreter and tool configuration, opt in for one
invocation:

```bash
basectl check --manifest /absolute/project/base_manifest.yaml --verify-project-runtime
basectl workspace doctor --workspace /absolute/workspace --verify-project-runtime
```

`--verify-project-runtime` permits those probes to execute code. It is supported
only by project and workspace check/doctor. `--yes` and a saved manifest command
approval never enable it implicitly. Manifest approval records only the manifest
identity described below; it does not verify the integrity of interpreters,
installed packages, referenced scripts, or tool configuration. Test execution
requires manifest command approval before its executable requirements preflight.

Base-owned inspection modules run with Python's isolated import mode and the
selected Base/base-cli source roots. They preserve the current directory for
project discovery without importing modules from that directory or inherited
`PYTHONPATH`. Base uses its own interpreter even in an active project environment;
`BASE_SETUP_VENV_DIR` can select that Base environment. The selected Base runtime
and explicit provider source overrides remain trusted inputs.

## Trust Identity

An allow record binds approval to both repository identity and the manifest
command contract. The identity includes:

- canonical project root path
- canonical manifest path
- raw SHA-256 digest of `base_manifest.yaml`
- project name from the manifest
- Git repository root when available
- sanitized `origin` remote URL when available
- current Git HEAD when available, for display and audit metadata

The enforcement key includes the canonical project root, manifest path, and
manifest digest. The remote URL and Git HEAD are stored for display and audit,
but the manifest digest is the only repository input that forces re-approval
after command declarations change. Status, allow, and blocked-command output
prints the following warning so the boundary is visible:

> Approval is bound to the `base_manifest.yaml` SHA-256 only. Manifest changes
> invalidate approval; referenced scripts, direct executable files, Git HEAD,
> and uncommitted working-tree changes are not independently verified or bound
> to approval. Re-review those inputs before execution after repository changes.

This intentionally resembles `direnv allow`: approval is local to the machine
and is invalidated by a content change in the trusted file. It does not try to
prove that every script reachable from the manifest is unchanged.

## Local State

Base stores allow records under Base-managed local state:

```text
~/.base.d/trust/manifest-commands/
  <identity-key>.json
```

Each record uses schema version `1`:

```json
{
  "schema_version": 1,
  "allowed_at": "2026-07-03T12:00:00Z",
  "allowed_by": "local-user",
  "base_version": "1.5.0",
  "project": {
    "name": "demo",
    "root": "/Users/rameshhp/work/demo",
    "manifest": "/Users/rameshhp/work/demo/base_manifest.yaml",
    "manifest_sha256": "<sha256>",
    "git_root": "/Users/rameshhp/work/demo",
    "origin": "https://github.com/example/demo.git",
    "head": "<commit-sha>"
  },
  "allowed_commands": ["test", "run", "build", "demo", "activate"]
}
```

Writes should be atomic: write a temporary file in the same directory, then
rename it into place. Base should never write allow records into project
repositories.

## User-Facing Flow

Use the focused trust command to inspect, allow, or revoke approval:

```bash
basectl trust status [project] [--workspace <path>] [--format text|json]
basectl trust allow <project> [--workspace <path>] [--manifest-sha256 <sha256>]
basectl trust revoke <project> [--workspace <path>]
```

With a project, `trust status` reports that one manifest. Without a project, it
reports every discovered project whose manifest declares an executable test,
run, build, demo, or activation surface. Metadata-only manifests are omitted so
workspace onboarding does not suggest unnecessary approval.

For schema-v1 compatibility, explicit single-project JSON continues to report
the underlying allow-record state, including `status: blocked` and an
`allow_command` for a metadata-only manifest. Human text reports that approval
is not required, and the project-less workspace view omits that manifest. The
existing `status`, `reason`, and conditional `allow_command`/`record` meanings
are unchanged.

`basectl trust allow` prints the exact identity being approved and requires the
supplied `--manifest-sha256` to match when that option is present. That flag is
useful for scripted, non-interactive approval after a prior review step.

`basectl trust revoke` removes all local approval records for the resolved
canonical project root and manifest path, including earlier manifest and
declared test-requirements revisions. Same-named projects in other checkouts
retain their approvals. Repeating revocation is safe. Unidentified malformed
records are left untouched and cannot supply a valid approval; a record read
or deletion failure is reported as an error instead of successful revocation.

When execution is blocked, commands fail before project environment activation
and before changing into project directories:

```text
ERROR: Manifest-declared commands are not allowed for project 'demo' on this machine.
Project root: /Users/rameshhp/work/demo
Manifest: /Users/rameshhp/work/demo/base_manifest.yaml
Manifest SHA-256: <sha256>
Origin: https://github.com/example/demo.git

Review first:
  basectl run demo --list
  basectl build demo --list
  basectl test demo --dry-run
  basectl demo demo --dry-run
  Inspect activate.source entries in /Users/rameshhp/work/demo/base_manifest.yaml before running 'basectl activate demo'.

Allow after review:
  basectl trust allow demo --manifest-sha256 <sha256>
```

If a record exists for the same project root but a different manifest digest,
the error says the manifest command contract changed and shows both the recorded
and current digest.

## Non-Interactive And CI Behavior

Manifest command execution must fail closed in non-interactive shells when no
matching allow record exists. It should not prompt, wait for input, or infer
trust from `CI=true`.

CI jobs that intentionally execute manifest commands should add an explicit
allow step before execution:

```bash
basectl trust allow base-demo --manifest-sha256 "$EXPECTED_BASE_MANIFEST_SHA256"
basectl test base-demo
```

If a workflow cannot precompute the digest, it may run `basectl trust status
base-demo --format json` first, review the emitted `manifest_sha256` in a prior
step, and then call `trust allow` with that digest.

`basectl trust status <project> --format json` returns a structured payload:

```json
{
  "schema_version": 1,
  "status": "blocked",
  "reason": "not_allowed",
  "project": {
    "name": "demo",
    "root": "/Users/rameshhp/work/demo",
    "manifest": "/Users/rameshhp/work/demo/base_manifest.yaml",
    "manifest_sha256": "<sha256>",
    "origin": "https://github.com/example/demo.git",
    "head": "<commit-sha>"
  },
  "trust_scope": {
    "approval_basis": "base_manifest.yaml_sha256",
    "manifest_changes_invalidate": true,
    "referenced_script_changes_invalidate": false,
    "direct_executable_file_changes_invalidate": false,
    "git_head_changes_invalidate": false,
    "working_tree_changes_invalidate": false
  },
  "allow_command": "basectl trust allow demo --manifest-sha256 <sha256>"
}
```

The project-less workspace form preserves each project payload under a
versioned collection:

```json
{
  "schema_version": 1,
  "projects": [
    {
      "schema_version": 1,
      "status": "blocked",
      "reason": "not_allowed",
      "project": {
        "name": "demo",
        "manifest_sha256": "<sha256>"
      },
      "allow_command": "basectl trust allow demo --manifest-sha256 <sha256>"
    }
  ]
}
```

Execution commands print the text block above and exit non-zero; JSON remains on
`basectl trust status --format json`.

## Implementation Slices

1. [#1381](https://github.com/basefoundry/base/issues/1381): add trust identity
   computation, local JSON storage, and `basectl trust status|allow|revoke` with
   Python unit tests.
2. [#1382](https://github.com/basefoundry/base/issues/1382): add Bash
   enforcement before `test`, `run`, `build`, `demo`, and activation source
   execution. Preserve `--dry-run` and `--list` inspection paths.
3. [#1973](https://github.com/basefoundry/base/issues/1973): require explicit
   consent for project-originated IDE app, extension, and user-setting
   mutations; show the complete dry-run plan; and document that command trust
   is bound to the manifest digest only.
