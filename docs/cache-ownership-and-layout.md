# Base Cache Ownership And Layout

> **STATUS** — Proposed runtime contract. This document defines the clean-slate
> layout that will be implemented next; the current `cli/` layout is not part
> of this contract.

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

## Proposed directory tree

With the cache root set to `~/Library/Caches/base`, the clean layout is:

```text
~/Library/Caches/base/
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
│       └── <base-run-id>/
│           ├── run.json
│           ├── logs/
│           │   ├── primary.log
│           │   └── internal/
│           │       ├── base_setup/
│           │       │   └── <child-run-id>.log
│           │       └── base_projects/
│           │           └── <child-run-id>.log
│           └── tmp/
│               └── <component>/<child-run-id>/
└── projects/
    ├── base-demo/
    │   └── <checkout-id>/
    │       ├── identity.json
    │       ├── cache/
    │       │   └── components/
    │       └── runs/
    │           └── <project-run-id>/
    │               ├── run.json
    │               ├── logs/
    │               │   ├── primary.log
    │               │   └── internal/
    │               └── tmp/
    ├── banyanlabs/
    │   └── <checkout-id>/...
    └── bankbuddy/
        └── <checkout-id>/...
```

There is deliberately no top-level `cli/` directory. Internal component names
are meaningful only inside a run's `logs/internal/` or persistent component
cache. They are not ownership roots.

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

One directory per Base control-plane invocation. `run.json` is written at the
start with `status: running` and finalized with timestamps, exit status,
project metadata, and child references. `primary.log` contains top-level Base
diagnostics. Normal command stdout remains stdout and is not captured here.

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

Run-oriented bundles for project-native commands. A project run can have its
own primary log and internal child logs. The parent Base run references the
project run through the history index and `run.json` metadata.

### `tmp/`

Temporary files scoped to one run and component. Successful runs remove these
directories automatically unless retention is requested. Failed or interrupted
runs retain them for diagnosis until cleanup removes the completed bundle.

## Runtime invariants

1. Every public invocation has one owner and one top-level run bundle.
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
another application's cache root. Persistent component caches may be pruned by
age, while history metadata is retained until an explicit history-retention
policy is applied.

## Implementation boundary

The runtime API should receive an explicit owner scope rather than deriving a
path from `App(name=...)`. Base components declare the Base owner. A
Base-compliant project runtime declares the project owner after manifest
validation. The resulting owner root, run root, component name, and checkout
identity are then passed through the Python context and delegated environment.
