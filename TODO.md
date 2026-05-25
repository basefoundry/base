# TODO

Action items from Claude's Base code analysis for version `0.1.0-dev`.

Use this as a commit-by-commit work queue. When an item is fixed, update the checkbox and add the commit hash or a short note.

## Bugs

- [x] Fix `_git_only_path_dirty` directory matching.
  - File: `lib/bash/git/lib_git.sh`
  - Problem: dirty files under an allowed directory such as `shared/foo.txt` are compared to `shared` exactly, so allowed dirty directories are rejected.
  - Expected fix: accept either the exact allowed path or paths prefixed by `allowed_path/`.
  - Add or update BATS coverage in `lib/bash/git/tests/lib_git.bats`.
  - Done.

- [x] Quote or array-encode `sort-in-place` flags.
  - File: `cli/bash/commands/sort-in-place/sort-in-place.sh`
  - Problem: `sort $unique_flag "$file"` violates the quoting standard and ShellCheck expectations.
  - Expected fix: use a flag array or `${unique_flag:+"$unique_flag"}`.
  - Verify existing `sort-in-place` BATS coverage still passes.
  - Done.

- [x] Ensure `update_file_section` cleans temp files on all write failures.
  - File: `lib/bash/file/lib_file.sh`
  - Problem: in the markers-not-found path, failures after creating the temp file can leave an orphan temp file.
  - Expected fix: centralize cleanup for copy, newline append, content write, and move failures.
  - Add focused failure-path coverage in `lib/bash/file/tests/lib_file.bats` if practical.
  - Done.

- [x] Fix Homebrew artifact version handling.
  - File: `cli/python/base_setup/engine.py`
  - Problem: `reconcile_homebrew_artifact` receives and logs an artifact version, but runs `brew install <package>` without honoring non-latest versions.
  - Expected fix: either implement supported Homebrew version handling or raise `ArtifactError` when a Homebrew artifact specifies anything other than `latest`.
  - Done.

- [ ] Deduplicate Base manifest discovery.
  - Files: `cli/python/base_setup/manifest.py`, `lib/python/base_cli/paths.py`
  - Problem: upward discovery for `base_manifest.yaml` is implemented in both modules.
  - Expected fix: keep the shared implementation in `base_cli.paths`, remove the duplicate from `base_setup.manifest`, and update imports/tests.

- [ ] Use `shlex.join` for setup command formatting.
  - File: `cli/python/base_setup/engine.py`
  - Problem: `_quote_arg` reimplements shell quoting and passes empty strings through unquoted.
  - Expected fix: replace `format_command`/`_quote_arg` internals with `shlex.join(command)` and cover empty-string formatting.

- [x] Honor `BASE_PROJECT_VENV_DIR` in Python artifact installs.
  - Files: `cli/python/base_setup/engine.py`, `bin/base-wrapper`
  - Problem: `base-wrapper` honors `BASE_PROJECT_VENV_DIR`, but `reconcile_python_artifact` hardcodes `~/.base.d/<project>/.venv`.
  - Expected fix: make Python artifact installation use `BASE_PROJECT_VENV_DIR` when present, falling back to the standard project venv path.
  - Done.

## Design Issues

- [x] Document wrapper runtime flags.
  - Files: `bin/basectl`, `cli/bash/commands/basectl/basectl.sh`, possibly `README.md`
  - Problem: `--debug-wrapper`, `--verbose-wrapper`, `--utc-wrapper`, and `--color` are consumed by the launcher but not documented.
  - Expected fix: document what each flag does and clarify the difference between `-v` and `--debug-wrapper`.
  - Done.

- [x] Reduce duplicated source-path resolution logic.
  - Files: `bin/basectl`, `base_init.sh`, `lib/shell/bashrc`, `lib/shell/bash_profile`, `lib/shell/zshrc`
  - Problem: symlink-resolving path normalization is copied in multiple places.
  - Expected fix: keep the launcher and runtime bootstrap self-contained, but simplify shell snippets for the current direct-source startup model.
  - Confirmed there are no symlinked snippets; `basectl update-profile` writes direct `source` lines to Base files.
  - Done.

- [x] Remove or consolidate duplicate `basectl_read_version`.
  - Files: `bin/basectl`, `cli/bash/commands/basectl/basectl.sh`
  - Problem: the version-reading function body exists in two layers.
  - Expected fix: decide whether duplication is required by startup ordering; if not, consolidate or rename responsibilities so the duplication is intentional and documented.
  - Verify both `basectl --version` and `basectl version`.
  - Done.

- [x] Consolidate setup dry-run state on `DRY_RUN`.
  - File: `cli/bash/commands/basectl/subcommands/setup_common.sh`
  - Problem: both local `dry_run` and exported `DRY_RUN` are maintained.
  - Expected fix: use exported `DRY_RUN` as the canonical state because `lib_std.sh` already consumes it.
  - Verify dry-run setup/check tests and inherited `DRY_RUN` behavior.
  - Done.

- [x] Remove interactive Bash upgrade behavior from `lib_std.sh`.
  - File: `lib/bash/std/lib_std.sh`
  - Problem: `__stdlib_init__` calls `check_bash_version_and_upgrade`, which can trigger interactive Homebrew/Bash installation from a library source path.
  - Expected fix: keep Bash version enforcement in the entrypoint layer; make the library non-interactive when sourced.
  - Review tests that cover `check_bash_version_and_upgrade` and adjust the public contract.
  - `bin/basectl` still auto-reexecs through an already-installed supported Bash and prints setup/manual-install guidance when none is found.
  - Done.

- [x] Avoid exporting multi-line `AWK_NEW_TEXT`.
  - File: `lib/bash/file/lib_file.sh`
  - Problem: `update_file_section` passes replacement content through an exported environment variable.
  - Expected fix: pass multi-line content through a temp file, stdin, or another scoped mechanism that does not leak into subprocess environments.
  - Preserve support for multi-line replacement sections.
  - Done.

- [x] Investigate and replace double `git pull` retry.
  - File: `lib/bash/git/lib_git.sh`
  - Problem: `git pull || git pull` hides the underlying failure or warning mode.
  - Expected fix: identify the root cause and use explicit git configuration or clearer failure handling.
  - Add tests around the intended retry or non-retry behavior.
  - Done.

- [x] Capture subprocess error output in artifact setup.
  - File: `cli/python/base_setup/engine.py`
  - Problem: failed subprocesses inherit stderr/stdout, so the persistent log only gets the command and exit code, not the tool's failure reason.
  - Expected fix: capture stderr in `run_command`, include it in `ArtifactError`, and log it before raising.
  - Done.

- [ ] Make `Context.cleanup` resilient to cleanup failures.
  - File: `lib/python/base_cli/context.py`
  - Problem: one failing cleanup hook can skip later hooks, log handler cleanup, and temp directory removal; `rmtree` failures can also mask the original command result.
  - Expected fix: catch and log cleanup hook and temp removal failures while continuing cleanup.

- [ ] Return unambiguous fallback source paths in Python logs.
  - File: `lib/python/base_cli/logging.py`
  - Problem: `_source_path` falls back to a bare filename when the log source is outside `BASE_HOME` and the current working directory.
  - Expected fix: return the resolved absolute path as the fallback.

- [ ] Remove or guard system-wide Base config loading.
  - File: `lib/python/base_cli/config.py`
  - Problem: `load_config` always reads `/etc/base.d/config.yaml`, which can unexpectedly affect local developer tooling.
  - Expected fix: either remove system config from v1 or gate it behind an explicit environment variable such as `BASE_SYSTEM_CONFIG`.

- [ ] Simplify PyYAML readiness state in setup.
  - File: `cli/bash/commands/basectl/subcommands/setup_common.sh`
  - Problem: `BASE_SETUP_PYYAML_READY` is exported and used as cross-function run state for dry-run gating.
  - Expected fix: inline the package-installed check in `setup_run_project_artifact_setup` instead of exporting a readiness flag.

- [ ] Capture `base_cli.testing` stderr separately.
  - File: `lib/python/base_cli/testing.py`
  - Problem: `CliRunner()` may mix stderr into stdout depending on Click behavior, while tests and callers expect `result.stderr`.
  - Expected fix: construct `CliRunner(mix_stderr=False)` when supported and keep tests explicit about stderr capture.

- [x] Clarify default-only artifact setup logging.
  - File: `cli/python/base_setup/engine.py`
  - Problem: `reconcile_manifest` logs that a project declares no artifacts even when default manifest artifacts are still merged and installed.
  - Expected fix: log based on the merged artifact list, or explicitly say that Base defaults are being installed.
  - Done.

- [x] Add PyYAML and Click checks to `basectl check`.
  - File: `cli/bash/commands/basectl/subcommands/setup_common.sh`
  - Problem: `basectl check` verifies the venv exists but not whether required bootstrap packages are installed.
  - Expected fix: check both `$(setup_pyyaml_package)` and `$(setup_click_package)` in text and JSON check modes.
  - Done.

- [ ] Deduplicate Zsh baserc protection.
  - Files: `lib/shell/zprofile`, `lib/shell/zshrc`
  - Problem: both files copy the same Base-owned variable snapshot/restore logic with different function prefixes.
  - Expected fix: create a shared Zsh guard helper and source it from both files.

- [ ] Add BATS coverage for Bash-to-Python setup handoff.
  - Files: `cli/bash/commands/basectl/tests/setup.bats`, `cli/bash/commands/basectl/subcommands/setup_common.sh`
  - Problem: `setup_run_project_artifact_setup` is not covered at the Bash layer.
  - Expected fix: mock `base-wrapper` or the Python boundary and verify argument passing, manifest/project environment handling, and non-zero exit propagation.

## Usability Issues

- [x] Make `basectl check` more automation-friendly.
  - Files: `cli/bash/commands/basectl/subcommands/check.sh`, `lib/bash/std/lib_std.sh`
  - Problem: all log output goes to stderr, so `basectl check > result.txt` captures nothing and scripting requires `2>&1`.
  - Expected fix: consider `--format json`, `--quiet`, or a documented stdout/stderr contract.
  - Add tests for any new output mode.
  - Done with `basectl check --format json`.

- [x] Add a CLI path to disable profile defaults.
  - File: `cli/bash/commands/basectl/subcommands/update_profile.sh`
  - Problem: after `basectl update-profile --defaults`, later runs preserve defaults; disabling requires manual `profile.conf` edits.
  - Expected fix: add `--no-defaults` or an equivalent explicit disable flag, and document the behavior.
  - Cover default enable, preserve, and disable flows.
  - Done.

- [x] Decide whether BATS is a required or dev-only dependency.
  - File: `cli/bash/commands/basectl/subcommands/setup_common.sh`
  - Problem: setup installs BATS unconditionally and check treats missing BATS as a failure.
  - Expected fix: either document BATS as a first-class dependency or make it optional via `--dev` or project metadata.
  - Update setup/check tests and README accordingly.
  - Done with BATS as an opt-in `--dev` dependency.

- [x] Make `caff` PID detection more robust.
  - File: `cli/bash/commands/caff/caff.sh`
  - Problem: parsing `ps -o args` assumes a fixed `caffeinate -iw <pid>` argument position, and `pgrep | head -1` hides non-not-found errors.
  - Expected fix: use a more reliable relationship check, or parse arguments defensively with error handling.
  - Add tests for alternate caffeinate argument shapes and pgrep failures if feasible.
  - Done.

- [x] Add `--version` to `basectl` help.
  - File: `cli/bash/commands/basectl/basectl.sh`
  - Problem: `version` is listed as a command, but the supported `--version` flag is omitted.
  - Expected fix: include `--version` in the help output and verify with existing help tests.
  - Done.

- [x] Decide how `basectl shell` handles arguments.
  - File: `cli/bash/commands/basectl/basectl.sh`
  - Problem: `basectl shell -c 'echo hello'` silently ignores arguments.
  - Expected fix: either reject unexpected args with usage, document that no args are accepted, or pass args through to the spawned shell.
  - Add tests for the chosen behavior.
  - Done.

- [x] Add schema documentation to `base_manifest.yaml`.
  - File: `base_manifest.yaml`
  - Problem: the root manifest is the first artifact schema many developers will see, but it has no comments explaining supported artifact types, version semantics, or the artifact registry.
  - Expected fix: add concise schema comments and point readers to `cli/python/base_setup/registry.py` for supported `(type, name)` pairs.
  - Done.

- [x] Document project virtual environment location.
  - Files: `docs/design.md`, `README.md`, possibly `base_manifest.yaml`
  - Problem: project virtual environments live at `~/.base.d/<project>/.venv`, but that convention is not easy for developers to discover.
  - Expected fix: document the venv location and how it relates to python-package artifacts.
  - Done.

- [ ] Add git branch context to Zsh defaults prompt.
  - File: `lib/shell/zsh_defaults.sh`
  - Problem: Bash defaults show git branch context in the prompt, but Zsh defaults do not.
  - Expected fix: add a Zsh git prompt helper and include it in `PROMPT`.

- [ ] Avoid subprocess-per-prompt host lookup.
  - File: `lib/bash/runtime/bashrc`
  - Problem: `_base_runtime_host_prompt` can run `scutil`/`hostname` on every prompt render.
  - Expected fix: compute the host prompt value once during runtime initialization and reference the cached variable in `PS1`.

## Base CLI Python Layer

- [x] Implement `base_cli` v1 for Python CLIs.
  - Files: `lib/python/base_cli/`, `docs/base-cli-design.md`, `cli/bash/commands/basectl/subcommands/setup_common.sh`
  - Goal: provide explicit `App`/decorator-driven initialization for Base and Base-supported project CLIs.
  - V1 scope: `Context`, Click wrapper decorators, standard options, `~/.base.d/cli/<name>` paths, user/file logging, temp/cache directories, sensitive option redaction for invocation logging, project manifest discovery, and a test helper.
  - Bootstrap: install Click into Base's Python virtual environment alongside PyYAML.
  - Add focused Python tests and keep existing setup tests passing.
  - Done.

- [x] Dogfood `base_cli` in `base_setup`.
  - Files: `cli/python/base_setup/engine.py`, `cli/python/base_setup/tests/test_engine.py`, `lib/python/base_cli/`
  - Goal: convert the manifest/artifact setup engine from hand-rolled argparse/print handling to `base_cli.App`, preserving the existing `python -m base_setup [project] --manifest <path> --dry-run` interface.
  - Use `base_cli.Context` logging and path initialization, and keep Bash `basectl setup` behavior unchanged.
  - Verify with Base's real virtual environment after `basectl setup` installs Click.
  - Done.

- [x] Add `base-wrapper` as the Python command execution wrapper.
  - Files: `bin/base-wrapper`, `cli/bash/commands/basectl/subcommands/setup_common.sh`, `lib/base/default_manifest.yaml`
  - Goal: expose one internal Python package execution path that selects `~/.base.d/<project>/.venv`, sets `BASE_HOME`, `BASE_PROJECT`, and `PYTHONPATH`, and runs `python -m <package>`.
  - Use `base` as the default project for now.
  - Standardize Base's venv on `~/.base.d/base/.venv`.
  - Add default artifact manifest using the same manifest shape as project manifests.
  - Done.

- [x] Dogfood the new Base project venv bootstrap.
  - Files: `cli/bash/commands/basectl/subcommands/setup_common.sh`, `cli/bash/commands/basectl/tests/setup.bats`
  - Goal: make non-dry `basectl setup` create/use `~/.base.d/base/.venv`, seed Base bootstrap packages there, and invoke the Python layer through `base-wrapper`.
  - Standardize on the project-scoped venv path without carrying compatibility code for older local bootstrap experiments.
  - Move any existing non-venv path aside as `.venv.backup.<timestamp>` before creating the project venv.
  - Verified locally with real `bin/basectl setup` and `bin/basectl setup --dry-run`.

- [x] Add an explicit project venv rebuild option.
  - Files: `cli/bash/commands/basectl/subcommands/setup.sh`, `cli/bash/commands/basectl/subcommands/setup_common.sh`, `cli/bash/commands/basectl/tests/setup.bats`
  - Goal: preserve idempotent setup by reusing valid venvs by default, while offering an intentional option such as `basectl setup --recreate-venv`.
  - Expected behavior: when requested, move the existing `~/.base.d/<project>/.venv` to `.venv.backup.<timestamp>` before creating a fresh venv.
  - Add dry-run and non-dry coverage.
  - Done.
