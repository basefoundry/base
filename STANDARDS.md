# Standards followed in this framework

## 1. General shell coding standards

1. Use four spaces for indentation. No tabs.
2. Shell/local variables and function names follow `snake_case`:
   only lowercase letters, underscores, and digits.
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
9. In libraries, have top-level code that prevents the file from being sourced
   more than once. For example:

   ```bash
   [[ $__stdlib_sourced__ ]] && return
   __stdlib_sourced__=1
   ```

10. Make sure all local variables inside functions are declared `local`.
11. Use `__func__` naming convention for special-purpose variables and
    functions when a shared framework-level convention already exists.
12. Double-quote all variable expansions, except:
   - inside `[[ ]]` or `(( ))`
   - places where we need word splitting to take place
13. Use `[[ $var ]]` to check if `var` has non-zero length, instead of
    `[[ -n $var ]]`.
14. Use "compact" style for if statements and loops:

    ```bash
    if condition; then
        ...
    fi

    while condition; do
        ...
    done

    for ((i=0; i < limit; i++)); do
        ...
    done
    ```

15. Make sure the code passes ShellCheck checks.

## 2. Error-handling standards

1. Do not use `set -e` in Base shell scripts or libraries.
2. Do not rely on implicit shell exit behavior for control flow.
3. Prefer explicit error handling using helper functions such as:
   - `run`
   - `exit_if_error`
   - `fatal_error`
4. When a command may fail as part of normal flow, handle that failure
   intentionally with `if`, `case`, `||`, or an explicit return-code check.
5. A script should make its error-handling strategy obvious to the reader.

Rationale:

- `set -e` interacts poorly with conditionals, pipelines, subshells, and
  sourced code.
- Base is a runtime- and library-heavy shell framework, so implicit exit rules
  make control flow harder to reason about.
- Explicit error handling is more verbose, but much easier to debug and
  maintain.

## 3. Directory and module structure

### Commands

Base-owned CLIs should live in per-command directories.

Recommended layout:

```text
cli/bash/commands/
  setup/
    setup.sh
    README.md
    tests/
  doctor/
    doctor.sh
    README.md
    tests/
```

Why:

- command code, docs, and tests stay together
- each command can grow without cluttering a shared flat directory
- the structure scales cleanly as Base adds more commands

For umbrella commands such as `basectl`, keep the entry script in
the command directory itself and place internal subcommand modules underneath
that command. For example:

```text
cli/bash/commands/base/
  base.sh
  subcommands/
    setup.sh
    check.sh
```

`$BASE_HOME/bin` is the only public command surface that should be added to
`PATH`. Do not create separate public `cli/bash/bin` or `cli/python/bin`
surfaces. A direct public command in `bin/` should be a real launcher file, not
a symlink, and should delegate to `basectl` in this form:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/basectl" caff "$@"
```

The command implementation still lives under
`cli/bash/commands/<command>/<command>.sh` so code, docs, and tests stay with
the command module.

Command-level integration tests for those subcommands can live under a shared
directory such as `cli/bash/commands/tests/`.

### Libraries

Libraries should also live in per-library directories.

Recommended layout:

```text
lib/bash/
  std/
    lib_std.sh
    README.md
    tests/
  git/
    lib_git.sh
    README.md
    tests/
```

Why:

- each library is treated as a module
- the README can describe the module in detail
- tests live next to the library they validate

### Exceptions

Small framework-level singleton files may remain flat when they are not really
"modules" in the same sense. Examples include:

- `bin/basectl`
- `base_init.sh`

### Index documentation

Even though commands and libraries live in per-module directories, keep
high-level index READMEs at the parent level when helpful, for example:

- `lib/bash/README.md`
- `cli/bash/commands/README.md`

Those top-level READMEs should act as catalogs and maps, while each module's
local `README.md` should document the module itself.

## 4. Runtime standards

`bin/basectl` is the public entrypoint for Base runtime execution.

It owns three decisions:

- run the umbrella Base command under `cli/bash/commands/base/base.sh`
- run an explicit Bash script path inside the Base runtime
- start an interactive Bash shell with the Base runtime already loaded

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

Shebang-based Bash scripts may use `#!/usr/bin/env basectl`. In that mode,
`basectl` receives the script path as its first argument, establishes the Base
runtime, sources the script, and calls its `main` function.

## 5. Shell startup standards

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
