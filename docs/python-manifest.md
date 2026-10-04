# Python Manifest Section

Base supports two Python project shapes.

## When A Project Python Runtime Is Required

Base treats project Python as explicit. A manifest requires a project Python
runtime when either of these is present:

- a top-level `python:` mapping, including `python: {}`
- at least one `python-package` artifact

The empty mapping is a compatibility opt-in to Base's default managed project
venv. `project.languages: [python]` is classification metadata only and does
not independently request an environment.

A manifest with neither contract is shell-only for Base setup and diagnostics.
`basectl setup`, `basectl check`, and `basectl doctor` run Base-owned manifest
parsing and reconciliation from `~/.base.d/base/.venv`; they do not copy
Click, PyYAML, tomli, or other Base bootstrap packages into the project and do
not create `<project-root>/.venv` solely for Base. Workspace status and
onboarding expose the venv state as `not_applicable` and can report the project
healthy without a project interpreter.

This is a scoped boundary, not the complete migration tracked in
[#1611](https://github.com/basefoundry/base/issues/1611). Project-owned
activation, run, test, build, and demo command routing keeps its existing
environment behavior for now. Future work should move more Base-owned control
plane execution to the Base runtime while preserving environments explicitly
owned by projects.

The Base-managed shape uses `python-package` artifact rows and installs
packages into the project's virtual environment:

```yaml
artifacts:
  - type: python-package
    name: requests
    version: latest
```

For non-Base projects, that environment defaults to:

```text
<project-root>/.venv
```

Projects can also declare the Python runtime they need:

```yaml
python:
  requires_python: "3.12"
```

`requires_python` accepts an exact Python minor, such as `3.10`, `3.11`,
`3.12`, or `3.13`, or a simple comma-separated range such as
`>=3.11,<3.14`. Base's supported project runtime window is Python 3.10 through
Python 3.13. `basectl check` and `basectl doctor` report requests outside that
window as errors before project virtualenv checks hide the real cause.

When a Base-managed project venv must be created, `basectl setup` uses the
selected supported Python minor instead of blindly inheriting Base's own
interpreter. For a range, Base selects the highest supported minor that matches
the range. If the selected interpreter is unavailable, setup/check/doctor report
that separately from an unsupported requirement. Base looks for
`BASE_PROJECT_PYTHON_BIN`, common Homebrew `python@<major.minor>` locations,
matching `python<major.minor>` commands on `PATH`, and finally the current
interpreter when its minor matches.

If an existing Base-managed project virtual environment uses a different Python
minor than `python.requires_python` selects, setup stops and asks the user to
rerun with `--recreate-venv`. Base does not rewrite an existing virtual
environment in place.

Projects that need to preserve the historical external Base-managed project
venv can opt in explicitly:

```yaml
python:
  venv_location: external
```

That keeps the project venv at:

```text
~/.base.d/<project>/.venv
```

`python.venv_location: external` is only for Base-managed project venvs. It
cannot be combined with `python.manager: uv`.

The uv-managed shape is explicit:

```yaml
python:
  manager: uv
```

When a project declares `python.manager: uv`, Base delegates Python environment
work to uv instead of reconciling `python-package` artifacts. `basectl setup`
runs `uv sync` from the project root, and Base treats the project-local uv
environment as the project virtual environment:

```text
<project-root>/.venv
```

`basectl setup --upgrade-pip <project>` does not mutate a uv-managed project
environment. Base reports that pip is owned by uv and recommends `uv sync`.
Use a project-specific uv bootstrap decision only when the project explicitly
requires pip; do not use the general Base maintenance flag to bypass uv's
lockfile ownership.

## Migration Paths

### Historical External Venv Migration

For a project that already uses Base's historical external project virtual
environment, the lowest-friction migration is to rerun setup and let Base
create `<project-root>/.venv`. To keep the historical location instead, add:

```yaml
python:
  venv_location: external
```

### Base-Managed Project Adopts uv

For a project that is adopting uv, add the explicit uv contract to
`base_manifest.yaml`:

```yaml
python:
  manager: uv
```

Move Python dependencies into `pyproject.toml`, create or refresh `uv.lock` with
uv, and run `uv sync` or `basectl setup <project>` from the project root. After
that, `basectl activate`, `basectl run`, `basectl test`, `basectl build`, and
`basectl demo` use `<project-root>/.venv` as the project environment unless the
caller explicitly sets `BASE_PROJECT_VENV_DIR`.

If the old external Base-managed environment still exists at
`~/.base.d/<project>/.venv`, Base reports it as stale and ignores it. Base does
not delete that directory automatically because it may contain local state,
debugging context, or artifacts a user still wants. Once `basectl check
<project>` reports the uv project virtual environment as healthy, users may
remove the stale Base-managed project environment manually if they no longer
need it.

### Existing uv Project Adopts Base

For an existing uv project, keep `pyproject.toml`, `uv.lock`, and the repo-local
`.venv` under uv ownership. Add a small Base manifest that opts into uv-managed
Python:

```yaml
project:
  name: example

python:
  manager: uv
```

Run `basectl setup <project>` to let Base delegate Python setup to `uv sync`.
Add `runner: uv` only for manifest commands that should execute through
`uv run -- ...`; command runner selection is independent from
`python.manager: uv`.

Base does not infer uv ownership from `pyproject.toml` or `uv.lock` alone. The
manifest opt-in is what lets Base choose the repo-local `.venv` and report uv
diagnostics.

On Ubuntu/Debian, the same manifest opt-in also lets Base bootstrap the `uv`
tool when it is missing: review the planned installer with
`basectl setup <project> --dry-run`, then rerun with `--yes` to allow the
mutation before Base delegates to `uv sync`.

## Command Runners

Command execution is independent from the project-level Python manager. Any
project command surface may opt into uv execution with `runner: uv`:

```yaml
test:
  command: pytest
  runner: uv

commands:
  taxbuddy:
    command: taxbuddy
    runner: uv

build:
  default:
    - package
  targets:
    package:
      command: python -m build
      runner: uv

demo:
  script: ./demo/demo.sh
  runner: uv
```

`runner: uv` executes the declared command through:

```bash
uv run -- <command>
```

When a uv-backed test command needs optional dependency groups, declare them
in the manifest instead of asking each contributor to install them manually:

```yaml
test:
  command: ./tests/full_validate.sh
  runner: uv
  uv_extras:
    - dev
    - benchmark
```

For a project with `python.manager: uv`, Base selects those extras for setup
and readiness checks (`uv sync --extra dev --extra benchmark`) and for test
execution (`uv run --extra dev --extra benchmark -- ...`). Extra names must
match the project's `pyproject.toml`; `test.uv_extras` cannot be combined with
`test.requirements` and is only valid for a uv-managed project or a test using
`runner: uv`.

This lets a composite project keep most commands in Go, Node, shell, `mise`, or
other tools while routing only selected Python commands through uv. It also lets
a fully uv-based Python project declare both:

```yaml
python:
  manager: uv

test:
  command: pytest
  runner: uv
```

Base validates runner values when reading the manifest. `basectl check` and
`basectl doctor` warn if `uv` is unavailable. Actual command invocation fails
clearly when `runner: uv` is selected and `uv` is not on `PATH`.

Command strings remain trusted project code with or without a runner. Base
does not parse them into a restricted argument array; shell syntax in
`test.command`, `commands.*.command`, and `build.targets.*.command` is
project-owned behavior. `demo.script` is different: it must be a relative,
project-owned executable file path, not a shell command string. Base validates
that the file exists, is executable, and stays inside the project root before
running it. See the [Project Demo Workflow](project-demo-workflow.md) for the
complete `demo.script` contract and passthrough argument behavior.

Review manifests from unfamiliar repositories before running project-owned
commands, and use `--dry-run` or listing commands first when you only need to
inspect the resolved invocation.

## Relationship To `pyproject.toml`

`pyproject.toml` remains the Python project's packaging contract. Base observes
a same-directory `pyproject.toml` during diagnostics, reports whether it is
readable, and summarizes standard `[project]` metadata. For projects without
an explicit supported Python manager, Base warns when dependency metadata or
unsupported `[tool.base]` configuration is present. When `python.manager: uv`
is declared, uv owns Python dependency synchronization and the dedicated uv
diagnostics report project-file, environment, and lockfile readiness instead.

Base does not treat `pyproject.toml` as an alternate Base manifest. It does not
solve dependencies, execute build backend hooks, generate lockfiles, or install
from `[project].dependencies` directly. For uv-managed projects, those actions
belong to uv.

## Relationship To `python-package` Artifacts

`python-package` artifacts remain supported for simple Base-managed Python
project environments. They should not be used as the steady-state dependency
model for a project that declares `python.manager: uv`.

When `python.manager: uv` is present, Base skips Base-managed
`python-package` reconciliation, including Base's default project Python
artifacts. Non-Python delegates keep their own platform policy: for example,
project Brewfiles still run through Homebrew on macOS, but Base skips `brew
bundle` on Ubuntu/Debian and lets uv-owned Python setup proceed through
`uv sync`.

## Activation

`basectl activate <project>` uses `<project-root>/.venv` for non-Base projects
unless the caller sets `BASE_PROJECT_VENV_DIR` or the manifest declares
`python.venv_location: external`. Base no longer infers uv ownership from the
mere presence of `pyproject.toml` and `uv.lock`.

If the uv environment does not exist yet, activation asks the user to run
`uv sync` in the project root.

## Diagnostics

Python manifest support adds these project diagnostics:

- `BASE-P170`: project `python.requires_python` compatibility with Base's
  supported Python runtime window
- `BASE-P171`: selected project Python interpreter availability
- `BASE-P172`: actual project Python runtime path and version when the project
  virtual environment can be inspected
- `BASE-P150`: uv CLI availability for uv-managed projects or uv runners
- `BASE-P151`: uv-managed project `pyproject.toml` presence
- `BASE-P152`: uv-managed project `uv.lock` presence
- `BASE-P153`: stale Base-managed project virtual environment ignored by a
  uv-managed project
- `BASE-P154`: uv-managed project virtual environment readiness
- `BASE-P155`: uv-managed project virtual environment synchronization
- `BASE-P160`: manifest command starts with an executable that is not available
  on PATH or in the project virtual environment
- `BASE-P161`: manifest command references a project script path that is
  missing, outside the project root, not a file, or not executable

The file and readiness diagnostics are warning-oriented in `check` and
`doctor`; they explain readiness without mutating the project or executing
project command strings.
When the uv project files and environment are present, `BASE-P155` performs an
offline `uv sync --check` probe and reports drift as an error. When uv provides
structured changes, the finding identifies missing, unexpected, or
version-mismatched packages in human-readable output and in the optional
`details.package_changes` JSON field. Command linting is advisory and does not
replace reviewing manifests from unfamiliar repositories before running their
declared commands.

### Workspace status `python_runtime`

`basectl workspace status --format json` includes a `python_runtime` object for
each ready, inspectable project environment. That summary reports the
environment manager, virtualenv path, interpreter path, and actual Python minor
version for both Base-managed and uv-managed projects. Shell-only projects
instead report `venv: "not_applicable"` and omit `python_runtime`.

## Non-Goals

Base should not:

- replace uv, Poetry, PDM, Hatch, pip-tools, setuptools, or pip
- solve dependency versions
- generate or own `uv.lock`
- infer uv behavior just because `pyproject.toml` or `uv.lock` exists
- automatically wrap commands in `uv run` unless the command declares
  `runner: uv`
- install every Python minor a project may request
- support multiple project virtual environments in one Base manifest

Base owns project discovery, activation, setup/check/doctor orchestration, and
the manifest command surface. Python packaging tools own Python dependency and
lockfile semantics.
