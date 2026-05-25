# TODO

Action items from Claude's Base code analysis for version `0.1.0`.

Use this as a commit-by-commit work queue. Completed items are removed after
they are merged.

## Design Issues — Python Layer

- [ ] Decide how artifact setup should handle subprocess stdout.
  - File: `cli/python/base_setup/engine.py`
  - Problem: `run_command` captures stderr but leaves stdout inherited from the parent process, so `brew` and `pip` output appears live in the terminal but is absent from the persistent Base log.
  - Expected fix: either capture and log stdout, stream it while also preserving it for the log, or document live-only stdout as intentional behavior.
