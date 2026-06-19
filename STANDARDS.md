# Base Standards

This document is the normative contributor standard for Base. It describes how
code should be organized, where logic should live, and how Base-owned Bash,
Python, Go, CLI, manifest, documentation, and test changes should behave.

For longer rationale, see:

- [Architecture](docs/architecture.md)
- [Execution Model](docs/execution-model.md)
- [Testing](docs/testing.md)
- [GitHub Workflow](docs/github-workflow.md)

## 1. Architecture Standards

Base is a layered developer-workspace tool. Contributors should preserve the
layer boundaries rather than placing logic wherever it is easiest to call.

### 1.1 Layer Responsibilities

| Need | Owning layer |
| --- | --- |
| Public user command surface | `bin/basectl` and small real launchers under `bin/` |
| Dispatch to Base subcommands | `cli/bash/commands/basectl/basectl.sh` |
| Host bootstrap such as Homebrew, Xcode CLT, Python, and venv creation | Bash setup layer |
| Shell runtime, prompt, activation, profile wiring, and dotfile guards | Bash runtime and shell layer |
| Manifest parsing and validation | Python layer |
| Artifact reconciliation, project discovery, project status, and structured project data | Python layer |
| Python package execution inside a project virtual environment | `bin/base-wrapper` |
| Project-owned Go CLIs and compiled binaries | Project repository, declared through manifest commands |
| Persistent Base state such as config and project venvs | `~/.base.d` |
| Ephemeral logs, temp files, and cache | Base cache root, normally `~/Library/Caches/base` on macOS |

### 1.2 Public Command Surface

`$BASE_HOME/bin` is the only public command surface that should be added to
`PATH`.

Public commands in `bin/` should be real launcher files, not symlinks. Keep them
small and delegate into the command implementation. For a hypothetical Bash
command:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/basectl" example "$@"
```

The implementation still belongs under:

```text
cli/bash/commands/<command>/<command>.sh
```

Python CLIs should not expose `#!/usr/bin/env python` or a venv-specific Python
path as their public execution contract. If a Python CLI needs a shebang-bearing
public executable, use a small launcher that execs `base-wrapper` so the package
runs in the selected project virtual environment:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/base-wrapper" --project "${BASE_PROJECT:-base}" example_cli "$@"
```

This keeps direct CLI execution aligned with the same venv and `PYTHONPATH`
rules that `basectl` uses internally.

### 1.3 `basectl` And `base-wrapper`

`bin/basectl` is the control plane. It decides whether the user asked to:

- run a Base command
- run an explicit Bash script path inside the Base runtime
- start an interactive Base runtime shell

`bin/base-wrapper` is the Python execution wrapper. It runs Python packages with:

- `BASE_HOME` set to the physical Base installation
- `BASE_PROJECT` set to the selected project
- `PYTHONPATH` containing Base's `lib/python` and `cli/python`
- Python resolved from `~/.base.d/<project>/.venv`, unless explicitly
  overridden for tests

Use `base-wrapper --project <project> <python-package>` whenever Bash needs to
call Base's Python layer.

## 2. General Code Standards

1. Prefer simple, explicit code over clever dispatch.
2. Keep changes scoped to the layer and module that own the behavior.
3. Use structured APIs over ad hoc text parsing when a reasonable parser or data
   model exists.
4. Keep stdout reserved for command output that users or automation may consume.
   Logs and diagnostics should go to stderr.
5. Destructive operations must be dry-run by default or require an explicit
   confirmation flag such as `--yes`.
6. Error messages should explain what failed and what the user can do next.
7. Add a new abstraction only when it removes real duplication or captures a
   stable product concept.
8. Do not introduce hidden import-time side effects. Registration of CLI command
   functions is acceptable; filesystem, network, and process mutations are not.

## 3. Bash Standards

### 3.1 Style

1. Use four spaces for indentation. No tabs.
2. Shell/local variables and function names follow `snake_case`.
3. Reserve all-uppercase names for:
   - exported environment variables
   - constants
   - globals intentionally shared across scripts, sourced modules, or subshells
4. Use a common prefix for exported environment variables whenever practical.
   For example: `BASE_HOME`, `BASE_HOST`, `BASE_OS`, `BASE_BASH_LIB_DIR`.
5. Do not use all-uppercase names for ordinary script-local variables.
6. Use a leading underscore for private variables and functions, especially in
   libraries or sourced modules where internal names might otherwise collide.
7. Avoid `camelCase` in shell code.
8. Place most code inside functions and invoke the main function at the bottom
   of the script.
9. Make sure all local variables inside functions are declared `local`.
10. Use `__func__` naming convention for special-purpose variables and functions
    when a shared framework-level convention already exists.
11. Double-quote all variable expansions, except:
    - inside `[[ ]]` or `(( ))`
    - places where word splitting is intentionally required
12. Use `[[ $var ]]` to check if `var` has non-zero length, instead of
    `[[ -n $var ]]`.
13. Use compact control-flow formatting:

    ```bash
    if condition; then
        ...
    fi

    while condition; do
        ...
    done

    for ((i = 0; i < limit; i++)); do
        ...
    done
    ```

14. Make sure shell code passes ShellCheck unless a documented exception is
    necessary.

### 3.2 Sourced Libraries

Libraries should guard against repeated sourcing:

```bash
[[ -n "${_base_example_lib_sourced:-}" ]] && return
_base_example_lib_sourced=1
readonly _base_example_lib_sourced
```

Prefer module-specific guard names to generic names that could collide across
sourced files.

### 3.3 Error Handling

1. Do not use `set -e`, `set -u`, or `set -o pipefail` in Base shell scripts
   or libraries.
2. Do not rely on implicit shell exit behavior for control flow.
3. Prefer explicit error handling using helper functions such as:
   - `run`
   - `exit_if_error`
   - `fatal_error`
4. When a command may fail as part of normal flow, handle that failure with
   `if`, `case`, `||`, or an explicit return-code check.
5. A script should make its error-handling strategy obvious to the reader.

Rationale:

- `set -e`, `set -u`, and `pipefail` interact poorly with conditionals,
  pipelines, subshells, sourced code, and scripts that are intended to be read
  as control-plane logic.
- Base is a runtime- and library-heavy shell framework, so implicit exit rules
  make control flow harder to reason about.
- Explicit error handling is more verbose, but much easier to debug and
  maintain.

### 3.4 Bash Layer Boundaries

Bash owns bootstrap and runtime coordination. Bash should:

- install or verify host prerequisites
- create and validate virtual environments
- update shell startup files
- start runtime shells
- call Python packages through `base-wrapper`

Bash should not:

- parse project manifests beyond passing manifest paths and project names
- reimplement artifact reconciliation that belongs in Python
- emit structured JSON by hand unless the format is tiny and well-tested
- call Python directly when `base-wrapper` is the intended path

## 4. Python Standards

Base Python code follows PEP 8 style in spirit and the repo's existing patterns
in practice.

### 4.1 Style And Structure

1. Use `from __future__ import annotations` in Python modules.
2. Prefer `pathlib.Path` over string path manipulation.
3. Use dataclasses for small structured records when they make behavior clearer.
4. Prefer explicit return values over mutation-heavy helper APIs.
5. Use `json.dumps` for JSON output. Do not assemble JSON with string
   concatenation.
6. Keep module-level side effects limited to cheap constants and CLI command
   registration.
7. Put CLI behavior in small command functions and pure helper functions where
   practical.
8. Avoid broad exception catches. Catch the error type that represents the
   expected failure and convert it into a clear user-facing message.

### 4.2 Python CLI Pattern

Base Python CLIs should use `base_cli.App`:

```python
from __future__ import annotations

import base_cli
import click


app = base_cli.App(name="example_cli")


def main(argv: list[str] | None = None) -> int:
    try:
        result = app.click_command.main(args=argv, standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return int(exc.exit_code)
    return int(result or 0)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option("--dry-run", is_flag=True, help="Preview changes without writing.")
def run(ctx: base_cli.Context, dry_run: bool) -> int:
    ctx.log.info("Running example_cli.")
    if dry_run:
        print("[DRY-RUN] Would do the work.")
        return 0
    return 0
```

Package entrypoints should provide `__main__.py`:

```python
from .engine import main


raise SystemExit(main())
```

### 4.3 Logging And Output

1. Use `ctx.log` for diagnostics.
2. Use stdout only for the command's primary output.
3. JSON output must be deterministic and parseable.
4. Redact sensitive option values using `base_cli.option(..., sensitive=True)`
   when an option may carry credentials, tokens, or secrets.
5. Python CLI log files are runtime artifacts and should remain under the Base
   cache root with user-only permissions.

### 4.4 Python Execution

Python packages for Base commands live under:

```text
cli/python/<package>/
```

Shared Python libraries live under:

```text
lib/python/<package>/
```

Bash should invoke these packages with:

```bash
"$BASE_HOME/bin/base-wrapper" --project base base_projects list
```

Project-specific Python commands should run through the project virtual
environment:

```bash
: "${BASE_HOME:?BASE_HOME is required. Run through basectl activate <project>.}"
"$BASE_HOME/bin/base-wrapper" --project "$project" project_cli "$@"
```

Do not hard-code `~/.base.d/base/.venv/bin/python` in command implementations.
Do not use `python -m <package>` directly from Bash unless the code is a narrow
test fixture or bootstrap exception.

## 5. Go CLI Standards

Base does not currently provide a Go CLI framework. For Go CLIs, Base should
standardize expectations and orchestration first, then consider helper packages
only after repeated real boilerplate appears.

### 5.1 CLI Framework

Use Cobra (`github.com/spf13/cobra`) as the default framework for non-trivial Go
CLIs. Cobra is widely used, supports subcommands, flags, help, and completions,
and fits Base's expectation for professional command surfaces.

Tiny one-command tools may use the Go standard library when Cobra would add more
structure than value. Once a tool has subcommands, completion needs, or shared
flag behavior, prefer Cobra.

Base should not create a `base-go-cli` package until Banyan Labs or another real
project shows repeated Go CLI boilerplate. If such a package becomes useful, it
should wrap Base conventions around Cobra rather than replace Cobra.

### 5.2 Go CLI Structure

Prefer conventional Go module layout:

```text
cmd/<tool>/main.go
internal/<domain>/
internal/cli/
```

Keep `main.go` thin:

```go
package main

import (
    "os"

    "example.com/project/internal/cli"
)

func main() {
    os.Exit(cli.Run(os.Args[1:]))
}
```

The command implementation should return an exit code instead of calling
`os.Exit` deep inside business logic.

### 5.3 Go CLI Behavior

Go CLIs should follow the same user-facing behavior standards as Base commands:

1. Logs and diagnostics go to stderr.
2. Primary command output goes to stdout.
3. JSON output uses `encoding/json`.
4. Destructive operations require `--yes` or are dry-run by default.
5. `--dry-run` prints what would change without changing state.
6. Exit codes follow Base conventions: `0` success, `1` operational failure,
   `2` usage or configuration error.
7. User-facing errors should be plain English and actionable.
8. Use `context.Context` for operations that may need cancellation, timeouts, or
   request-scoped values.
9. Avoid panics for normal user or environment errors.

### 5.4 Go And Base Orchestration

Go binaries are compiled executables. They do not use `base-wrapper`, and they
should not rely on Python virtual environments.

Base should orchestrate Go project commands through manifests:

```yaml
test:
  command: go test ./...

commands:
  lint: go vet ./...
  build: go build -o ./bin/mytool ./cmd/mytool
  mytool: ./bin/mytool --help
```

Use `basectl test <project>` and `basectl run <project> <command>` to invoke
those contracts. Let Go own Go modules, builds, and test execution; let Base own
workspace discovery, setup orchestration, and command delegation.

Project-owned Go binaries should be built into a project-local `bin/`
directory when they are meant to be run directly. For a richer public command,
use a thin Bash launcher in the project `bin/` that checks for the compiled
binary and `exec`s it with the original arguments:

```bash
#!/usr/bin/env bash

tool_dir="$(cd -- "$(dirname -- "$0")" && pwd -P)" || exit 1
exec "$tool_dir/mytool" "$@"
```

Do not route Go binaries through `base-wrapper`; that wrapper is only for
Python packages that need the selected Base project virtual environment.

Typical validation for Go changes:

```bash
gofmt -w .
go test ./...
go vet ./...
```

## 6. Directory And Module Structure

### 6.1 Bash Commands

Base-owned Bash CLIs should live in per-command directories:

```text
cli/bash/commands/
  example/
    example.sh
    README.md
    tests/
```

Umbrella commands such as `basectl` keep the entry script in the command
directory and place internal subcommand modules underneath:

```text
cli/bash/commands/basectl/
  basectl.sh
  subcommands/
    setup.sh
    check.sh
  tests/
    help.bats
    setup.bats
```

### 6.2 Bash Libraries

Reusable Bash libraries live in the standalone `base-bash-libs` repository.
Base keeps only Base-specific Bash runtime and version helpers under `lib/bash`:

```text
lib/bash/
  runtime/
    README.md
    tests/
  version/
    lib_version.sh
    README.md
    tests/
```

Base Bash command code should use `import_base_lib` for reusable libraries such
as `file/lib_file.sh` or `git/lib_git.sh`; `base_init.sh` resolves those imports
from `base-bash-libs`.

### 6.3 Python Packages

Base Python command packages should live under `cli/python`. Shared Python
libraries should live under `lib/python`.

Keep package tests next to the package:

```text
cli/python/base_projects/
  engine.py
  __main__.py
  tests/
```

### 6.4 Exceptions

Small framework-level singleton files may remain flat when they are not modules
in the same sense. Examples include:

- `bin/basectl`
- `bin/base-wrapper`
- `base_init.sh`
- `bootstrap.sh`

### 6.5 Index Documentation

Even though commands and libraries live in per-module directories, keep
high-level index READMEs at parent levels when helpful, for example:

- `lib/bash/README.md`
- `cli/bash/commands/README.md`

Top-level READMEs should act as catalogs and maps. Local module READMEs should
document the module itself.

## 7. CLI Behavior Standards

1. Help should be available through `-h` and `--help` when practical.
2. User-facing commands should return:
   - `0` for success
   - `1` for operational failure
   - `2` for usage or configuration errors
3. Destructive commands must be dry-run by default or require `--yes`.
4. `--dry-run` should print what would change without changing state.
5. `--format json` should be available when automation reasonably needs stable
   machine-readable output.
6. Text output should be readable, stable enough for humans, and not overly
   clever.
7. Commands should keep logs on stderr and primary output on stdout.
8. Commands that can run for a while should log progress at useful boundaries.
9. Help paths and lightweight diagnostics should avoid requiring the Python venv
   when Bash can answer directly.

## 8. Manifest And Artifact Standards

1. Project manifests are declarative.
2. The Python layer reads and validates manifests.
3. Bash setup owns only bootstrap prerequisites needed before Python can run.
4. Default project artifacts belong in `lib/base/default_manifest.yaml`.
5. Developer prerequisites belong in `lib/base/dev_manifest.yaml`.
6. Project-specific artifacts belong in the project's `base_manifest.yaml`.
7. Prefer delegation to established tools such as Brewfile and mise instead of
   reimplementing their dependency models.
8. Artifact setup should be idempotent. Running setup repeatedly should converge
   on the same state.
9. Unknown artifact types or unsupported curated artifacts should fail clearly.

## 9. Runtime And Shell Startup Standards

`base_init.sh` owns the runtime contract after `bin/basectl` chooses what should
run. It must be the single place that establishes convention-based Base paths
such as `BASE_HOME`, `BASE_BIN_DIR`, `BASE_BASH_COMMANDS_DIR`, and
`BASE_BASH_LIB_DIR`.

Bash scripts that run through Base should:

- define `main` as their entrypoint
- keep ordinary code inside functions
- call `import_base_lib path/to/lib.sh` for Base Bash libraries
- rely on exported `BASE_*` variables rather than reconstructing Base's repo
  layout locally

Shebang-based Bash scripts may use:

```bash
#!/usr/bin/env basectl
```

In that mode, `basectl` receives the script path as its first argument,
establishes the Base runtime, sources the script, and calls its `main` function.

Base-managed shell startup files follow this separation of concerns:

- `bash_profile` / `zprofile`
  - thin login-shell behavior
- `bashrc` / `zshrc`
  - interactive shell guards and dotfile-only behavior
  - Base `bin/` PATH availability for interactive shells
- `base_defaults.sh`
  - optional shell-neutral interactive defaults shared by Bash and Zsh
- `bash_defaults.sh` / `zsh_defaults.sh`
  - optional shell-specific interactive defaults

Startup files should stay thin and predictable. They must not source
`base_init.sh`; Base runtime setup belongs to the `basectl` command path.

`~/.baserc` is user-managed input for simple Base preferences such as
`BASE_DEBUG=1`. It must not set Base-owned runtime or profile state such as
`BASE_HOME`, `BASE_BIN_DIR`, `BASE_LIB_DIR`, `BASE_OS`, `BASE_SHELL`,
`BASE_PROFILE_VERSION`, `BASE_ENABLE_BASH_DEFAULTS`, or
`BASE_ENABLE_ZSH_DEFAULTS`. Shell startup code that sources `~/.baserc` should
reject attempts to change those variables and restore the previous values.

## 10. Testing Standards

1. Prefer the narrowest test that proves the behavior.
2. Use pytest for Python engines and helpers.
3. Use BATS for Bash commands, runtime behavior, shell startup, and Bash
   libraries.
4. Use `bin/base-test` as the full confidence gate before merging broad or
   cross-layer changes.
5. Add regression coverage for bug fixes when practical.
6. Avoid tests that depend on the user's real home directory, shell startup
   files, GitHub account state, or global config.
7. Prefer fake commands and temporary repositories for shell integration tests.
8. Keep test output deterministic.

Typical validation commands:

```bash
bats cli/bash/commands/basectl/tests/gh.bats
pytest cli/python/base_projects/tests
BASE_TEST_PYTHON="$HOME/.base.d/base/.venv/bin/python" \
  env -u BASE_HOME HOME=/private/tmp/base-review-home \
  bin/base-test
git diff --check
```

## 11. Documentation And GitHub Workflow Standards

1. Update docs for user-visible behavior changes.
2. Keep top-level README content focused on product usage and onboarding.
3. Keep detailed design and rationale under `docs/`.
4. Keep module-specific behavior in local module READMEs.
5. Use GitHub default-style labels:
   - `bug`
   - `enhancement`
   - `documentation`
   - `ci`
   - `security`
   - `needs-demo`
6. Issues created by Codex or other automation should be assigned to
   `codeforester`.
7. Pull request work should happen in a dedicated worktree.
8. Prefer `basectl gh` when it supports the workflow. Fall back to raw `gh`,
   the GitHub connector, or `git` when needed.
9. PR descriptions should include:
   - what changed
   - why it changed
   - validation commands
   - `Closes #<issue>` or `Fixes #<issue>` when appropriate
   - demo impact when relevant

## 12. Placement Checklist

Before adding code, ask where it belongs:

| Question | Put it here |
| --- | --- |
| Is this host bootstrap or shell runtime behavior? | Bash layer |
| Is this manifest parsing or project data? | Python layer |
| Is this artifact reconciliation? | Python layer, invoked by Bash through `base-wrapper` |
| Is this a public executable? | Small real launcher in `bin/` |
| Is this a Bash helper used by multiple commands? | `lib/bash/<module>/` |
| Is this a Python helper used by multiple CLIs? | `lib/python/<package>/` |
| Is this a project-owned Go CLI? | Project Go module under `cmd/<tool>/` and `internal/`, declared in `base_manifest.yaml` |
| Is this repeated Go CLI boilerplate? | Document the convention first; consider a shared Go helper only after real repetition |
| Is this command-specific behavior? | The command's module and tests |
| Is this a project-owned task? | `base_manifest.yaml` `test` or `commands` |
| Is this local machine preference? | `~/.base.d/config.yaml` or `~/.baserc`, depending on scope |
| Is this temporary runtime output? | Base cache root, not `~/.base.d` |

When in doubt, preserve the layer boundary first and make the call path explicit.
