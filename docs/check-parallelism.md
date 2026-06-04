# basectl check parallelism

`basectl check` is called frequently enough that reducing wall time matters, but
the command also has to stay easy to reason about. The output order is part of
the user experience and the JSON order is useful to automation, so the command
should not print directly from background jobs.

## Decision

Parallelize only independent probes, collect their results, and render them in
the existing deterministic order.

Good candidates:

- Homebrew presence and path discovery
- Xcode Command Line Tools presence
- Homebrew Python formula presence
- Base virtual environment integrity
- Base bootstrap Python package checks

Do not parallelize steps that mutate process state or depend on an earlier
probe's side effect. In particular, `setup_refresh_brew_path` modifies `PATH`
and should remain in the parent shell after Homebrew discovery succeeds.

## Recommended Shape

Introduce small result-producing helpers instead of backgrounding the current
logging flow directly:

```bash
setup_check_homebrew_probe >"$tmpdir/homebrew" &
setup_check_xcode_probe >"$tmpdir/xcode" &
setup_check_python_probe >"$tmpdir/python" &
setup_check_venv_probe >"$tmpdir/venv" &
setup_check_python_package_probe "$pyyaml_package" >"$tmpdir/pyyaml" &
setup_check_python_package_probe "$click_package" >"$tmpdir/click" &
wait
```

Each probe should write structured shell-safe data such as:

```text
ok=true
message=Homebrew is installed.
recovery=
```

The parent should then read those files and emit text or JSON in the current
order:

1. Homebrew
2. Xcode Command Line Tools
3. Python formula
4. Base virtual environment integrity
5. PyYAML
6. click
7. prerequisite profile checks, when `--profile` is set
8. project artifact checks, when a project is supplied

## Constraints

- Preserve `basectl check --format json` schema and ordering.
- Preserve the text output order.
- Keep `setup_clear_run_state` before probe collection.
- Keep `setup_require_macos` before probe collection.
- Avoid background jobs for project artifact checks until the Python layer has
  an explicit concurrent check API.
- Avoid background jobs for prerequisite profile checks until `base_dev`
  exposes a result-only mode that can be merged deterministically.

## Follow-Up

The implementation should be a dedicated performance PR with focused tests for:

- deterministic text output order
- deterministic JSON output order
- missing Homebrew with other probes still reported
- package checks not failing spuriously when the venv is absent
