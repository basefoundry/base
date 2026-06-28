# basectl check parallelism

`basectl check` parallelizes independent base-environment probes on macOS while
preserving deterministic text and JSON output. The command is called frequently
enough that reducing wall time matters, but the output order is part of the user
experience and the JSON order is useful to automation, so background jobs must
not print directly.

## Decision

Parallelize only independent probes, collect their results, and render them in
the existing deterministic order.

The shipped macOS base probes run concurrently for:

- Homebrew presence and path discovery
- Xcode Command Line Tools presence
- Homebrew Python formula presence
- Base virtual environment integrity
- Base bootstrap Python package checks

The parent shell then reads the probe result files in this order:

1. Homebrew
2. Base reusable Bash libraries
3. Xcode Command Line Tools
4. Python formula
5. Base virtual environment integrity
6. PyYAML
7. click
8. prerequisite profile checks, when `--profile` is set
9. project artifact checks, when a project is supplied

`setup_refresh_brew_path` still runs in the parent shell after the Homebrew
probe succeeds, because it mutates `PATH`. The Base reusable Bash libraries
check also remains parent-owned because it depends on the effective library
resolution path rather than an independent external probe.

## Implementation Shape

The background probe helpers write structured shell-safe result files:

```bash
setup_write_homebrew_check_probe "$tmpdir/homebrew" &
setup_write_xcode_check_probe "$tmpdir/xcode" &
setup_write_python_check_probe "$tmpdir/python" &
setup_write_virtualenv_check_probe "$tmpdir/base_virtualenv" &
setup_write_python_package_check_probe "$tmpdir/pyyaml" "pyyaml" "$pyyaml_package" &
setup_write_python_package_check_probe "$tmpdir/click" "click" "$click_package" &
```

Each result file uses key/value fields:

```text
name=homebrew
ok=true
message=Homebrew is installed.
recovery=
debug=Resolved Homebrew binary: /opt/homebrew/bin/brew
```

After all probe PIDs exit, the parent shell parses the files, validates required
fields, adds any parent-owned results, and only then renders text or calls the
Python JSON renderer.

## Constraints

- Preserve `basectl check --format json` schema and ordering.
- Preserve the text output order.
- Keep `setup_clear_run_state` before probe collection.
- Keep `setup_require_macos` before probe collection.
- Keep CI runtime-only checks serial unless the CI path gets its own result-file
  collector; the macOS background probe implementation is not reused there.
- Avoid background jobs for project artifact checks until the Python layer has
  an explicit concurrent check API.
- Avoid background jobs for prerequisite profile checks until `base_dev`
  exposes a result-only mode that can be merged deterministically.

## Test Coverage

The regression suite covers:

- deterministic text output order
- deterministic JSON output order
- overlapping base probes while text output remains ordered
- overlapping base probes while JSON findings remain ordered
- missing Homebrew with the remaining base probes still reported
- package checks that do not fail spuriously when the venv is absent
