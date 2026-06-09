# Doctor Finding IDs

`basectl doctor` emits stable finding identifiers in both text and JSON output.
Automation, runbooks, and suppression policies should match on `id` instead of
human-readable messages. Findings that intentionally emit multiple instances
of the same rule should match on the tuple of `id` and `name`.

Finding IDs are never reused after they ship. A finding may change its message,
fix text, or severity over time, but its ID keeps the same meaning.
Every doctor finding implementation must provide an explicit ID; placeholder
IDs such as `BASE-P000` are invalid because they cannot support automation or
suppression policies.

## Principles

Doctor findings should be specific, actionable, and non-alarming. Text output
is for humans who need a safe next step; JSON output is for automation that
needs stable IDs, statuses, names, messages, and fix guidance.

`basectl doctor` should not mutate local state. A future fix path must be
explicit, reviewable, and paired with dry-run behavior before Base offers it as
part of the doctor workflow.

## Diagnostic JSON Contract

Base diagnostic JSON uses `schema_version: 1` for object-shaped payloads. This
contract was introduced before Base 1.0 and intentionally replaces the earlier
experimental check JSON shape that used per-item `ok` booleans.

Every diagnostic item emitted by `basectl check --format json` and
`basectl doctor --format json` has the same fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable finding ID, such as `BASE-D001` or `BASE-P050` |
| `status` | One of `ok`, `warn`, or `error` |
| `name` | Short machine-readable finding subject |
| `message` | Human-readable diagnostic detail |
| `fix` | Suggested remediation, or an empty string when no fix is needed |

Check commands that return an object include an aggregate `status` and a
`checks` array of diagnostic items:

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": []
}
```

`basectl check <project> --format json` and
`basectl check --profile <list> --format json` embed project/profile layer
results as nested diagnostic payload objects under `project_checks` and
`profile_checks`. Workspace check and doctor JSON keep their workspace/project
object shape and use the same diagnostic item fields inside each project's
`checks` array.

Doctor commands use the same diagnostic item fields. The top-level
`basectl doctor --format json` wrapper includes `schema_version` and aggregate
`status`, and keeps doctor-specific arrays named `findings`,
`profile_findings`, and `project_findings`.

## Namespaces

| Prefix | Scope |
| --- | --- |
| `BASE-D` | Base runtime and developer-prerequisite findings |
| `BASE-P` | Project manifest, artifact, IDE, and command-delegation findings |
| `BASE-H` | Project health declaration findings |

## Base Runtime Findings

| ID | Finding |
| --- | --- |
| `BASE-D001` | Homebrew availability and PATH refresh |
| `BASE-D002` | Xcode Command Line Tools availability |
| `BASE-D003` | Homebrew Python formula availability |
| `BASE-D004` | Base virtual environment integrity |
| `BASE-D005` | Base `PyYAML` package availability |
| `BASE-D006` | Base `click` package availability |
| `BASE-D101` | Unsupported prerequisite profile manager |
| `BASE-D102` | Unsupported prerequisite profile version |
| `BASE-D103` | Homebrew unavailable for prerequisite profile checks |
| `BASE-D104` | Prerequisite profile Homebrew package status |
| `BASE-D105` | GitHub CLI availability |
| `BASE-D106` | GitHub CLI authentication status |
| `BASE-D107` | AI developer tool availability and version status |

## Project Findings

| ID | Finding |
| --- | --- |
| `BASE-P001` | Empty project manifest artifact set |
| `BASE-P002` | Project manifest validity |
| `BASE-P010` | Brewfile path validity |
| `BASE-P011` | Homebrew unavailable for Brewfile checks |
| `BASE-P012` | Brewfile dependency status |
| `BASE-P020` | mise config path validity |
| `BASE-P021` | mise CLI availability |
| `BASE-P022` | mise trust and missing-tool status |
| `BASE-P030` | Unsupported artifact manager |
| `BASE-P031` | Unsupported Homebrew artifact version |
| `BASE-P032` | Homebrew unavailable for artifact checks |
| `BASE-P033` | Homebrew artifact package status |
| `BASE-P040` | Python package artifact status in the project virtual environment |
| `BASE-P050` | Project virtual environment readiness |
| `BASE-P060` | Project demo declaration |
| `BASE-P061` | Project demo script path and executable status |
| `BASE-P070` | Build target working directory status |
| `BASE-P080` | Project Git repository status |
| `BASE-P081` | Project Git `origin` remote status |
| `BASE-P082` | GitHub CLI authentication status for a GitHub-hosted project remote |
| `BASE-P100` | User config disables all IDE setup and checks |
| `BASE-P101` | User config disables setup and checks for one IDE |
| `BASE-P102` | User IDE setting conflicts with a project manifest setting |
| `BASE-P110` | IDE CLI unavailable for extension checks |
| `BASE-P111` | IDE extension listing failure |
| `BASE-P112` | IDE extension install status |
| `BASE-P120` | IDE settings file validity |
| `BASE-P121` | IDE setting presence |
| `BASE-P122` | IDE setting expected-value match |
| `BASE-P123` | IDE setting value differs from the Base manifest |
| `BASE-P130` | Homebrew unavailable for IDE app checks |
| `BASE-P131` | IDE app install status |
| `BASE-P132` | IDE CLI PATH status |
| `BASE-P140` | `pyproject.toml` presence and metadata summary |
| `BASE-P141` | `pyproject.toml` readability |
| `BASE-P142` | `pyproject.toml` dependency metadata observed but not reconciled |
| `BASE-P143` | Unsupported `[tool.base]` configuration |

`BASE-P050` is the stable project virtual-environment readiness finding. The
Bash setup/check path reports detailed venv health messages when a project venv
is missing, incomplete, or has a broken Python executable. Workspace-level
project discovery currently verifies that the expected project venv Python path
exists. The finding should be treated as the project-venv readiness contract,
not as a guarantee that every project dependency import succeeds.

`BASE-P140` through `BASE-P143` are read-only `pyproject.toml` diagnostics.
Base only inspects the `pyproject.toml` file beside the active
`base_manifest.yaml`. These findings do not make `pyproject.toml` a Base
configuration source and do not cause Base to install Python dependencies.
Warnings in this range should guide users toward a valid Python project file
without failing the Base manifest check by themselves.

`BASE-P080` through `BASE-P082` are read-only project Git remote diagnostics.
They report whether the project directory is inside a Git repository, whether
`origin` is configured and parseable, and whether GitHub CLI authentication is
ready when `origin` points at GitHub. Default project check and doctor do not
probe network remote reachability; that belongs behind an explicit opt-in path.

## Health Findings

| ID | Finding |
| --- | --- |
| `BASE-H001` | Required environment variable presence; each variable is keyed by `(id, name)`. |
| `BASE-H002` | Required TCP port listening/free state |
