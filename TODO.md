# TODO

Action items from Claude's Base code analysis for version `0.1.0`.

Use this as a commit-by-commit work queue. Completed items are removed after
they are merged.

## Design Issues — Python Layer

- [ ] Fix `run_command` double-logging of stderr.
  - File: `cli/python/base_setup/engine.py`
  - Problem: `run_command` logs stderr directly, then embeds the same stderr in `ArtifactError`; the top-level handler logs that exception again.
  - Expected fix: surface failed command stderr exactly once, preferably by including it in the exception message and letting the top-level error handler log it.

- [ ] Decide how artifact setup should handle subprocess stdout.
  - File: `cli/python/base_setup/engine.py`
  - Problem: `run_command` captures stderr but leaves stdout inherited from the parent process, so `brew` and `pip` output appears live in the terminal but is absent from the persistent Base log.
  - Expected fix: either capture and log stdout, stream it while also preserving it for the log, or document live-only stdout as intentional behavior.

## Design Issues — Bash Layer

- [ ] Avoid duplicate `pip show` calls in `basectl check`.
  - File: `cli/bash/commands/basectl/subcommands/setup_common.sh`
  - Problem: package checks call `setup_base_python_package_installed`, then `setup_base_python_package_check_message` calls it again, causing two `pip show` invocations per package.
  - Expected fix: compute package presence once and pass the known status into message formatting.
