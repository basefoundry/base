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
   For example: `BASE_HOME`, `BASE_HOST`, `BASE_OS`, `BASE_SOURCES`.
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
- Base is a wrapper- and library-heavy shell framework, so implicit exit rules
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

For umbrella commands such as `base`, keep the wrapper-facing entry script in
the command directory itself and place internal subcommand modules underneath
that command. For example:

```text
cli/bash/commands/base/
  base.sh
  subcommands/
    setup.sh
    check.sh
```

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

- `cli/bash/bin/base-wrapper`
- `cli/env/baseenv.sh`

### Index documentation

Even though commands and libraries live in per-module directories, keep
high-level index READMEs at the parent level when helpful, for example:

- `cli/bash/bin/README.md`
- `lib/bash/README.md`
- `cli/bash/commands/README.md`

Those top-level READMEs should act as catalogs and maps, while each module's
local `README.md` should document the module itself.

## 4. Wrapper standards

Base should support two wrapper modes, but they serve different purposes.

### A. Symlink-dispatched wrapper mode

This is the default mode for commands owned by the Base repo.

Pattern:

- `cli/bash/bin/<command>.sh` is a symlink to `base-wrapper`
- `base-wrapper` resolves `<command>` by convention
- the real script lives at `cli/bash/commands/<command>/<command>.sh`

Use this mode for:

- commands that are part of Base itself
- commands that should appear as first-class Base entrypoints
- commands that benefit from command discovery, listing, and strict layout

Why this is the default:

- it gives Base a consistent command surface
- it works well with per-command docs and tests
- it keeps user-facing entrypoints separate from implementation files

### B. Shebang wrapper mode

This mode should be supported for wrapped Bash commands that live outside the
Base repo.

Pattern:

```bash
#!/usr/bin/env base-wrapper
```

Use this mode for:

- scripts in sibling repos that still want Base-managed execution behavior
- standalone wrapped scripts that should not be forced into Base's internal
  `commands/<name>/<name>.sh` layout

Why this mode matters:

- Base is intended to support multiple repos in one workspace
- not every wrapped command should have to live physically inside Base
- a shebang-based wrapper is the more portable cross-repo mechanism

### Wrapper design decision

The standard is:

1. Use symlink-dispatched wrapper mode as the default for Base-owned commands.
2. Support shebang wrapper mode for wrapped commands that live outside Base.
3. Do not force every wrapped command in the workspace to be relocated into the
   Base repo just to gain wrapper behavior.

In other words, the symlink convention is the preferred in-repo ergonomics,
while the shebang convention is the preferred cross-repo portability story.

## 5. Shell startup standards

Base-managed shell startup files follow this separation of concerns:

- `bash_profile` / `zprofile`
  - thin login-shell handoff
- `bashrc` / `zshrc`
  - interactive shell bootstrap
- `base_defaults.sh` / `zsh_defaults.sh`
  - optional shared interactive defaults
- `~/.baserc`
  - machine-local overrides

Startup files should stay thin and predictable. Interactive shell behavior
belongs in the rc files, not in the login profile files.
