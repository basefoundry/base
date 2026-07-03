# Python Manifest Section

Base supports two Python project shapes.

The older Base-managed shape uses `python-package` artifact rows and installs
packages into Base's project virtual environment:

```yaml
artifacts:
  - type: python-package
    name: requests
    version: latest
```

That environment defaults to:

```text
~/.base.d/<project>/.venv
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

## Migration Paths

### Base-Managed Project Adopts uv

For a project that already uses Base's historical project virtual environment,
add the explicit uv contract to `base_manifest.yaml`:

```yaml
python:
  manager: uv
```

Move Python dependencies into `pyproject.toml`, create or refresh `uv.lock` with
uv, and run `uv sync` or `basectl setup <project>` from the project root. After
that, `basectl activate`, `basectl run`, `basectl test`, `basectl build`, and
`basectl demo` use `<project-root>/.venv` as the project environment unless the
caller explicitly sets `BASE_PROJECT_VENV_DIR`.

If the old Base-managed environment still exists at
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
`test.command`, `commands.*.command`, `build.targets.*.command`, and
`demo.script` is project-owned behavior. Review manifests from unfamiliar
repositories before running them, and use `--dry-run` or listing commands first
when you only need to inspect the resolved invocation.

## Relationship To `pyproject.toml`

`pyproject.toml` remains the Python project's packaging contract. Base observes
a same-directory `pyproject.toml` during diagnostics, reports whether it is
readable, summarizes standard `[project]` metadata, and warns when dependency
metadata or unsupported `[tool.base]` configuration is present.

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

`basectl activate <project>` uses the project-local `.venv` only when
`python.manager: uv` is present and the caller has not set
`BASE_PROJECT_VENV_DIR`. Base no longer infers uv activation from the mere
presence of `pyproject.toml` and `uv.lock`.

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
- `BASE-P160`: manifest command starts with an executable that is not available
  on PATH or in the project virtual environment
- `BASE-P161`: manifest command references a project script path that is
  missing, outside the project root, not a file, or not executable

These diagnostics are warning-oriented in `check` and `doctor`; they explain
readiness without performing dependency resolution or executing project command
strings. Command linting is advisory and does not replace reviewing manifests
from unfamiliar repositories before running their declared commands.

`basectl workspace status --format json` also includes a `python_runtime`
object for each ready, inspectable project environment. That summary reports
the environment manager, virtualenv path, interpreter path, and actual Python
minor version for both Base-managed and uv-managed projects.

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
