# Uninstall And Retention

`basectl uninstall <project>|--all` removes the selected Base-managed local
state. It previews by default and applies only with `--yes`. The command is
Stable; its scope deliberately retains checkouts, external tools, and
Base-level execution history.

## Preview, Apply, And Verify

For one project, resolve its name from the workspace and review the plan:

```bash
basectl uninstall example --workspace ~/work
basectl uninstall example --workspace ~/work --yes
basectl uninstall example --workspace ~/work --verify
```

For workstation-wide state:

```bash
basectl uninstall --all --dry-run
basectl uninstall --all --yes
```

An applied `--all` operation runs verification automatically, while the
already-running Python process can still verify removal of Base's own runtime.
A later `basectl uninstall --all --verify` needs a usable Base interpreter and
may no longer launch after successful removal. Run a standalone `--verify`
before removal to inspect remaining state; a nonzero result is expected while
selected resources exist.

`--verify` does not remove anything. It cannot be combined with `--yes` or
`--dry-run`; `--yes` and `--dry-run` are also mutually exclusive. A project name
cannot be combined with `--all`.

## Resource Contract

`state` below means `~/.base.d`; `cache` means the resolved Base cache root,
including a `BASE_CACHE_DIR` override. See [Cache Ownership And Layout](cache-ownership-and-layout.md).

| Resource | Project uninstall | `--all` |
| --- | --- | --- |
| Manifest-command trust | Remove records matching the selected name, root, and manifest | Remove the manifest-command trust store |
| `state/<project>/checks` | Remove selected project's recorded checks | Remove check directories under managed project state |
| `state/<project>/.venv` | Remove selected external Base-managed environment | Remove external Base and project environments; defer Base's runtime until finalization |
| `cache/projects/<project-id>/` | Remove the entire selected project namespace | Remove all project namespaces |
| Project run bundles, logs, and checkout identity inside that namespace | Remove, including every checkout namespace under the selected project ID | Remove |
| `cache/base/cache/` | Retain | Remove |
| `cache/base/runs/` and `cache/base/history/` | Retain | Retain |
| `state/config.yaml` | Retain | Remove only its `workspace` mapping; preserve unrelated settings |
| `state/profile.conf` and managed shell-startup sections | Retain | Remove preferences and managed sections; preserve other shell-file content |
| Project checkout, manifest, and project-local `.venv` | Retain | Retain |
| Homebrew packages, installed external tools, Base source/package files, and unrelated user state | Retain | Retain |

Project caches and external state use project identity, not a separate removal
scope for each checkout. Uninstalling one selected checkout removes the cache
subtree for all checkout IDs under that project ID. Trust-record matching is
narrower: project name, root, and manifest must match. Export any project logs
you need before applying removal.

The retained Base history index can still describe project commands whose raw
project logs have been removed. History retention does not promise that those
log paths remain readable. Uninstall also does not remove installed package
manager software or delete the Base installation itself.

## Ordering, Failure, And Recovery

For `--all --yes`, Base first removes selected state other than its own runtime,
then removes managed shell-startup sections, then finalizes deferred runtime
removal and verifies the result. Finalization is attempted even if shell-profile
cleanup fails; a profile failure is still returned to the caller. Base's runtime
is kept available until the final Python invocation has started.

Removal refuses selected paths with symlinked state/cache ancestry and refuses
to rewrite a symlinked user config. Resolve the reported path ownership before
retrying; do not replace this check with an indiscriminate recursive deletion.

The operation is not transactional. A filesystem or profile error can leave
earlier removals applied. Inspect the error and retained evidence, correct the
cause, preview the remaining scope, and retry. Already absent resources do not
need removal again. If Base's interpreter has already been removed, restore a
usable Base runtime through the installation/setup path before retrying; setup
can recreate managed state that the next uninstall must remove.

Verification checks the resources in the table's removal scope, plus workspace
settings and managed shell sections for `--all`. Success does not claim that
all historical Base files or all tools installed through Base are absent.
