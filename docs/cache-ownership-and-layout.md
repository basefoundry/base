# Base Cache Ownership And Layout

> **STATUS** — Implemented clean-slate runtime contract. The legacy `cli/`
> layout is intentionally unsupported; a cleared cache starts with this tree.

This document establishes the ownership boundary for files under
`BASE_CACHE_DIR`. Base owns the control-plane runtime. A Base-compliant project
owns its own runtime subtree. The distinction is made before choosing a
component name, log file, or run identifier.

The implementation baseline is an empty cache root. The first Base-owned
invocation creates `base/`; the first project-owned invocation creates only
that project's namespace under `projects/`. No directory is created merely
because a project is listed in a workspace manifest.

## Ownership model

| Owner | Root | Examples | Owns |
| --- | --- | --- | --- |
| Base control plane | `base/` | `basectl`, `base_setup`, `base_projects`, `base_release`, `base_history` | Base orchestration, discovery, GitHub/release operations, and Base-internal diagnostics |
| Base-compliant project | `projects/<project-id>/<checkout-id>/` | `base-demo`, `banyanlabs`, `bankbuddy` | Project-native commands, project-owned caches, and project execution evidence |

`base` is a reserved owner. Base's own repository and Base-internal CLIs do
not create a `projects/base` namespace. A project argument such as
`basectl setup banyanlabs` identifies the target project in metadata; it does
not make the Base setup implementation project-owned.

Ownership follows the executable, not the command-line argument:

- `basectl workspace status` writes only to the Base control-plane tree.
- `basectl setup banyanlabs` writes its orchestration bundle under `base/`.
- If setup launches a project-native process, that child process writes under
  `projects/banyanlabs/<checkout-id>/` and is linked to the parent Base run.
- `basectl test bankbuddy` has a Base parent run and a project-owned test run.
- A CLI shipped by `base-demo` writes under the `base-demo` project tree even
  when it is launched through a Base wrapper.

The Base history index may contain metadata for both owners so that
`basectl history` can provide one cross-project view. That index is metadata;
raw project logs and caches remain in the project-owned tree.

## Directory tree

The default cache root is `~/Library/Caches/base` on macOS and `~/.cache/base`
on Ubuntu/Debian. `BASE_CACHE_DIR` can override either default. The ownership
split is the same on both platforms; with `$BASE_CACHE_DIR` set to the resolved
cache root, the clean layout is:

```text
$BASE_CACHE_DIR/
├── base/
│   ├── history/
│   │   └── runs.jsonl
│   ├── cache/
│   │   ├── discovery/
│   │   └── components/
│   │       ├── base_projects/
│   │       ├── base_setup/
│   │       └── base_github_projects/
│   └── runs/
│       └── <base-run-id>__<command>__<project>/
│           ├── run.json
│           ├── logs/
│           │   └── primary.log
│           └── tmp/
│               └── <component>/<child-run-id>/
└── projects/
    ├── base-demo/
    │   └── <checkout-id>/
    │       ├── identity.json
    │       ├── cache/
    │       │   └── components/
    │       └── runs/
    │           └── <project-run-id>__<command>__<project>/
    │               ├── run.json
    │               ├── logs/
    │               │   └── primary.log
    │               └── tmp/
    ├── banyanlabs/
    │   └── <checkout-id>/...
    └── bankbuddy/
        └── <checkout-id>/...
```

There is deliberately no top-level `cli/` directory. Component names are
meaningful only inside persistent component caches; they are not ownership
roots or separate log identities.

## Directory meanings

### `base/`

The Base control-plane namespace. It contains only artifacts produced by Base
itself. `basectl`, its Bash dispatch layer, and Base-owned Python CLIs use this
root regardless of which project they inspect or modify.

### `base/history/`

The append-only cross-project command index. Each record includes the owner,
project identity when known, parent/child run relationship, status, and a path
to the relevant run bundle or log. It is not a raw log store.

### `base/cache/`

Reusable Base-owned state that can survive across runs. `discovery/` contains
Base's project-discovery cache. `components/` contains persistent caches owned
by individual Base components. This state is not tied to one diagnostic run.

### `base/runs/`

One directory per accepted Base control-plane invocation. The directory name
starts with the canonical run ID and adds sanitized command/project labels for
manual inspection, for example
`20260719T052536_37996_8494__setup__base`. The labels are filesystem display
context only; `run.json`, history, and CLI output retain the canonical run ID
without the suffix. `run.json` is written at the start with `status: running`
and finalized with timestamps, exit status, project metadata, command
arguments, and parent/child references when known. A recognized command may
create this directory temporarily while validating leaf arguments or a named
project, but a usage rejection removes the invocation-owned directory and does
not write history. An inherited parent run directory is outside that cleanup.
Run metadata and the primary log are private (`0600`). `primary.log` is the
single diagnostic stream for the invocation. Bash and Python children append
to this same file, which always captures DEBUG-level diagnostics even when the
terminal is showing INFO. Normal command stdout remains stdout and is not
captured here.

Base-internal children may reuse a parent bundle only after the Bash dispatcher
verifies that the inherited path is a real direct child of this `base/runs/`
root and that its run metadata and parent markers match. Arbitrary, symlinked,
completed, or mismatched inherited paths are never finalized; Base scrubs that
state and creates a fresh bundle instead.

An interactive `basectl activate` bundle remains `running` while the runtime
shell is open. Shell startup inherits that bundle's run context for its
diagnostics, but Base clears the context before the prompt so commands entered
in the shell follow the normal independent run and history policy for recordable
commands. The activation bundle is finalized and recorded after the runtime
shell exits.

### `projects/<project-id>/<checkout-id>/`

The runtime namespace for one canonical project checkout. The project ID comes
from the validated manifest name. The checkout ID is derived from the resolved
checkout path so separate worktrees do not share runtime state accidentally.
`identity.json` records the resolved project name, root, manifest, and identity
version used to derive the path.

### Project `cache/`

Persistent, recomputable state owned by that project. A project can use
component subdirectories without affecting Base's caches or another checkout's
caches.

### Project `runs/`

Run-oriented bundles for project-native commands. Each project invocation also
has one run ID and one `logs/primary.log`; the parent Base run references the
project run through the history index and `run.json` metadata.

### `tmp/`

Temporary files scoped to one run and component. Base removes the complete
`tmp/` tree, including empty component parents, after every run by default.
Pass the explicit `--keep-temp` wrapper option to preserve the complete tree
for diagnosis. Run metadata, history, and `primary.log` are retained
independently of this choice.

## Timestamps and permissions

Persisted history, run metadata, and primary run lifecycle entries use UTC.
Run IDs use UTC-based timestamps so bundle names remain sortable across hosts.
Python CLI log streams (stderr and the per-run log file) use the host's local
timezone by default, matching the Bash logger during local runs. The local
offset is included in Python log lines. Pass `basectl --utc-wrapper ...` to set
`BASE_BASH_LIBS_LOG_UTC=1` and render the Bash wrapper and library log streams in
UTC for CI, support, or cross-machine diagnostics. Python CLI logs retain their
normal Python logging timezone. `basectl history` keeps its existing UTC default
and can render human-readable views in local time with `--local-time`.

History and run artifacts are user-private by default. History and metadata
files are created with mode `0600`; raw log files use the same mode. Directory
permissions remain controlled by the host cache filesystem and do not change
the ownership boundary described above.

## Uninstall Retention

Uninstall is a separate lifecycle boundary from per-run temporary cleanup.
Project uninstall removes the whole selected `projects/<project-id>/` subtree,
including logs and run metadata for its checkout IDs. `--all` removes all
project namespaces and `base/cache/`, while retaining `base/runs/` and
`base/history/`. The history index may consequently refer to removed project
logs. See [Uninstall And Retention](uninstall.md) for verification and recovery.

## Runtime invariants

1. Every accepted public invocation has one owner and one top-level run bundle;
   rejected usage invocations leave no persistent run bundle or history row.
2. Base-owned processes always resolve the `base/` owner explicitly.
3. Project-owned processes resolve their project ID and checkout ID from the
   validated manifest and canonical project root.
4. Child processes inherit the owner and parent run ID; they cannot silently
   create a new top-level namespace.
5. `basectl logs` and `basectl clean` operate from run metadata and ownership
   roots. They do not scan arbitrary application directories.
6. `~/.base.d` remains durable user state and is outside this cache lifecycle.
7. A fresh cache starts with no migration or legacy-layout compatibility work.

## Retention and cleanup

`basectl clean` operates on completed run bundles, with optional project and
owner filters. It never removes an active run, durable `~/.base.d` state, or
another application's cache root. Cleanup rejects symlinks below the resolved
Base cache root and performs deletion relative to trusted directory descriptors
so an owner, category, or candidate path cannot redirect removal elsewhere.
Persistent component caches may be pruned by age, while history metadata is
retained until an explicit history-retention policy is applied. Cleanup previews
matches by default and requires `--yes` for deletion; active runs are reported
as retained and are never reclassified as stale by cleanup.

## Implementation boundary

The runtime API should receive an explicit owner scope rather than deriving a
path from `App(name=...)`. Base components declare the Base owner. A
Base-compliant project runtime declares the project owner after manifest
validation. The resulting owner root, run root, component name, and checkout
identity are then passed through the Python context and delegated environment.
