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

Text and JSON doctor findings are primary command output and are written to
stdout. Usage and validation errors, including unsupported `--format` values,
are diagnostics and must be written to stderr so scripts can safely parse
machine-readable stdout.

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
  "profiles": [],
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
| `BASE-W` | Workspace manifest and multi-repository findings |

## Base Runtime Findings

| ID | Finding |
| --- | --- |
| `BASE-D001` | Homebrew availability and PATH refresh |
| `BASE-D002` | Xcode Command Line Tools availability and Homebrew freshness |
| `BASE-D003` | Base Python runtime availability |
| `BASE-D004` | Base virtual environment integrity |
| `BASE-D005` | Base `PyYAML` package availability |
| `BASE-D006` | Base `click` package availability |
| `BASE-D007` | Base reusable Bash library source readiness |
| `BASE-D008` | Bash runtime version support |
| `BASE-D009` | Python `venv` module support |
| `BASE-D010` | Git CLI availability |
| `BASE-D011` | GitHub CLI availability on Ubuntu/Debian |
| `BASE-D012` | BATS availability on Ubuntu/Debian |
| `BASE-D013` | ShellCheck availability on Ubuntu/Debian |
| `BASE-D014` | jq availability on Ubuntu/Debian |
| `BASE-D015` | Go availability on Ubuntu/Debian source checkouts |
| `BASE-D101` | Unsupported prerequisite profile manager |
| `BASE-D102` | Unsupported prerequisite profile version |
| `BASE-D103` | Homebrew unavailable for prerequisite profile checks |
| `BASE-D104` | Prerequisite profile Homebrew package presence and freshness |
| `BASE-D105` | GitHub CLI availability |
| `BASE-D106` | GitHub CLI authentication status |
| `BASE-D107` | AI developer tool availability and version status |

## Project Findings

| ID | Finding |
| --- | --- |
| `BASE-P001` | Empty project manifest artifact set |
| `BASE-P002` | Project manifest validity |
| `BASE-P010` | Brewfile path validity |
| `BASE-P011` | Brewfile platform or Homebrew availability |
| `BASE-P012` | Brewfile dependency status |
| `BASE-P020` | mise config path validity |
| `BASE-P021` | mise CLI availability |
| `BASE-P022` | mise trust and missing-tool status |
| `BASE-P030` | Unsupported artifact manager |
| `BASE-P031` | Unsupported Homebrew artifact version |
| `BASE-P032` | Homebrew unavailable for artifact checks |
| `BASE-P033` | Homebrew artifact package presence and freshness |
| `BASE-P040` | Python package artifact status in the project virtual environment |
| `BASE-P050` | Project virtual environment readiness |
| `BASE-P060` | Project demo declaration |
| `BASE-P061` | Project demo script path and executable status |
| `BASE-P070` | Build target working directory status |
| `BASE-P080` | Project Git repository status |
| `BASE-P081` | Project Git `origin` remote status |
| `BASE-P082` | GitHub CLI authentication status for a GitHub-hosted project remote |
| `BASE-P083` | Opt-in project Git `origin` remote reachability status |
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
| `BASE-P150` | uv CLI availability for uv-managed projects or uv command runners |
| `BASE-P151` | uv-managed project `pyproject.toml` presence |
| `BASE-P152` | uv-managed project `uv.lock` presence |
| `BASE-P153` | Stale Base-managed project virtual environment ignored by a uv-managed project |
| `BASE-P154` | uv-managed project virtual environment readiness |
| `BASE-P160` | Manifest command executable availability |
| `BASE-P161` | Manifest command project script path readiness |
| `BASE-P170` | Project Python version requirement support window |
| `BASE-P171` | Selected project Python interpreter availability |
| `BASE-P172` | Actual inspectable project Python runtime: environment manager, virtualenv path, interpreter path, and Python minor version |

`BASE-P050` is the stable project virtual-environment readiness finding. The
Bash setup/check path reports detailed venv health messages when a project venv
is missing, incomplete, or has a broken Python executable. Workspace-level
project discovery verifies that the expected project venv Python executable can
start. The finding should be treated as the project-venv readiness contract, not
as a guarantee that every project dependency import succeeds.

`BASE-P140` through `BASE-P143` are read-only `pyproject.toml` diagnostics.
Base only inspects the `pyproject.toml` file beside the active
`base_manifest.yaml`. These findings do not make `pyproject.toml` a Base
configuration source and do not cause Base to install Python dependencies.
Warnings in this range should guide users toward a valid Python project file
without failing the Base manifest check by themselves.

`BASE-P150` through `BASE-P154` are uv support diagnostics. They are warnings
when uv tooling or expected uv project files are missing, because check/doctor
should explain readiness without performing dependency resolution. Command
invocation still fails hard when a command declares `runner: uv` and the `uv`
executable is unavailable.
For the full uv manifest contract, migration paths, and runner configuration,
see [Python Manifest](python-manifest.md).

`BASE-P160` and `BASE-P161` are advisory manifest command-lint diagnostics for
`test.command`, `commands.*.command`, and `build.targets.*.command`. They look
for obvious missing executables or missing/non-executable project script paths
without executing command strings or treating the manifest as safe. They should
not reject complex shell syntax or replace human review of unfamiliar
repositories.
For uv-backed command execution and `runner: uv` examples, see
[Python Manifest - Command Runners](python-manifest.md#command-runners).

`BASE-P170` and `BASE-P171` are project Python runtime diagnostics for
`python.requires_python`. `BASE-P170` validates the request against Base's
supported Python 3.10 through 3.13 window. `BASE-P171` reports whether the
selected supported interpreter is available locally. Setup uses the selected
interpreter when it creates a Base-managed project virtual environment and
requires `--recreate-venv` before replacing an existing venv with a different
Python minor.

`BASE-P172` reports the actual inspectable project Python runtime: environment
manager, virtualenv path, interpreter path, and Python minor version. Missing or
broken virtual environments continue to use their existing readiness findings
instead of emitting runtime version data.

`BASE-P080` through `BASE-P083` are read-only project Git remote diagnostics.
They report whether the project directory is inside a Git repository, whether
`origin` is configured and parseable, and whether GitHub CLI authentication is
ready when `origin` points at GitHub. Default project check and doctor do not
probe network remote reachability. The GitHub CLI authentication diagnostic is
bounded so a slow `gh auth status` call reports a warning instead of blocking
the check indefinitely.

`BASE-P083` appears only when the user explicitly opts in with
`--remote-network`. It delegates reachability to Git with a bounded
`git ls-remote` call, reports sanitized provider and transport details, and
does not print credential-bearing remote URLs.

## Workspace Findings

| ID | Finding |
| --- | --- |
| `BASE-W010` | Expected workspace repository presence |
| `BASE-W011` | Discovered Base-managed project outside the workspace manifest |
| `BASE-W012` | Present expected repository without a Base project manifest |

`BASE-W010` is emitted for every expected repository when workspace check or
doctor runs with `--manifest <path>`. It is `error` when a required repository
is missing, `warn` when an optional repository is missing, and `ok` when the
repository is present.

`BASE-W011` reports local Base-managed projects that were discovered under the
workspace root but are not listed in the supplied workspace manifest.

`BASE-W012` reports expected repositories that are present locally but do not
contain `base_manifest.yaml`. This is an `ok` finding because workspace
manifests do not require every repository to be Base-managed.

## Health Findings

| ID | Finding |
| --- | --- |
| `BASE-H001` | Required environment variable presence; each variable is keyed by `(id, name)`. |
| `BASE-H002` | Required TCP port listening/free state |

For `BASE-H001`, `id` is always `BASE-H001` and `name` is the environment
variable name from `health.required_env`. A suppression targeting a specific
missing-variable finding would match values such as `id: BASE-H001` and
`name: DATABASE_URL`.
