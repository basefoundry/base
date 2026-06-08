# Python Manifest Section

Base currently supports Python dependencies through `python-package` artifact
entries:

```yaml
artifacts:
  - type: python-package
    name: requests
    version: latest
```

That contract remains valid. It is simple, implemented, and maps directly to the
Base-managed project virtual environment at:

```text
~/.base.d/<project>/.venv
```

## Decision

Base should grow a structured `python:` manifest section only when the Python
contract needs to express more than a small package list. The structured section
is the right long-term shape because it makes the project virtual environment,
requirement files, and inline package requirements explicit instead of encoding
all Python behavior as generic artifact rows.

The future shape should be:

```yaml
python:
  venv: default
  requirements:
    - requirements.txt
  packages:
    - requests
    - pytest==8.4.1
```

This is a design target, not the current manifest contract.

## Field Semantics

`venv` should default to `default`, meaning Base's current project venv location:

```text
~/.base.d/<project>/.venv
```

A custom venv path should be deferred until a real project needs it. If Base
adds it later, the path should be relative to the project root, must stay inside
the project root unless explicitly allowed, and must not silently change the
activation or `basectl test` contract.

`requirements` should be a list of requirement file paths relative to the
project root. Base should install them with `pip install -r <file>` and reject
paths outside the project root.

`packages` should use normal pip requirement strings such as:

```text
requests
pytest==8.4.1
rich>=13,<14
```

Using pip requirement strings avoids inventing a parallel Python package syntax.

## Relationship To Current Artifacts

`python-package` artifacts should remain supported during and after the first
structured `python:` implementation. A migration can translate:

```yaml
artifacts:
  - type: python-package
    name: requests
    version: latest
  - type: python-package
    name: pytest
    version: 8.4.1
```

into:

```yaml
python:
  packages:
    - requests
    - pytest==8.4.1
```

The implementation should reject duplicate requirements only when it can do so
without guessing. Exact duplicate strings can be de-duplicated; semantically
overlapping requirement ranges should be left to pip.

## Relationship To `pyproject.toml`

Base observes a same-directory `pyproject.toml` during project diagnostics when
one exists beside `base_manifest.yaml`. This diagnostic support is read-only:
Base reports whether the file is readable, summarizes standard `[project]`
metadata, and warns when Python dependency metadata or unsupported `[tool.base]`
configuration is present.

`base_manifest.yaml` remains the Base source of truth. Base does not install
packages from `[project].dependencies`, does not execute build backend hooks,
and does not treat `[tool.base]` as an alternate manifest.

Future uv-managed Python support should use an explicit `python:` manifest
contract, tracked separately from the first read-only diagnostics slice.

## Non-Goals

The structured Python section should not turn Base into a Python packaging
manager. Base should not:

- generate or own `requirements.txt`
- replace Poetry, PDM, Hatch, uv, pip-tools, or setuptools
- solve dependency versions
- support multiple project virtual environments in one Base manifest
- automatically migrate manifests without an explicit user action

Base owns the project venv convention and setup/check/doctor orchestration.
Python packaging tools own dependency resolution and lockfile semantics.
