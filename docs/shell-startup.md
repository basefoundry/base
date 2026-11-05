# Shell Startup Files

Base integrates with Bash and Zsh through small managed sections in the user's
real dotfiles. Base does not take over whole dotfiles.

The command that installs or refreshes those sections is:

```bash
basectl update-profile
```

By default it updates all four startup files:

- `~/.bash_profile`
- `~/.bashrc`
- `~/.zprofile`
- `~/.zshrc`

Missing files are created. Existing files keep their non-Base content; Base only
adds or replaces its marked section. Before changing an existing startup file,
`basectl update-profile` writes a timestamped sibling backup such as
`~/.bashrc.backup.YYYYMMDDTHHMMSS`.

To remove Base from shell startup files without hand-editing dotfiles, run:

```bash
basectl update-profile --remove
```

This removes only Base-managed marked sections from Bash and Zsh startup files.
Use `basectl update-profile --remove --dry-run` to preview the planned backups
and removals.

`basectl update-profile` also creates `~/.base.d/profile.conf`, which records
whether the user has opted into Base's optional shell defaults. The managed
dotfile sections stay minimal and defer PATH/default handling to the sourced
Base snippets. The same sourced snippets also register `basectl` shell
completions, so future completion improvements arrive when Base is updated
without rewriting user dotfiles.

Run `basectl update-profile --defaults` to enable those optional defaults, and
run `basectl update-profile --no-defaults` to disable them again. Plain
`basectl update-profile` preserves the existing preference.

`BASE_PROFILE_VERSION` records the schema version of this Base-managed file. It
is reserved for future migrations and is not intended to be edited by users.

For Base and consumer-project upgrades, follow the [Upgrade Contract](upgrading.md).
It distinguishes Homebrew, mutable default-branch source checkouts, and stable
source tags. Current Homebrew updates reconcile setup even when the formula
version is unchanged; ordinary Git updates run setup only when the revision
changes. Stable Base source upgrades use `update --release` when supported by
the installed version.

`basectl update-profile` only refreshes managed shell integration. Run it when
the selected installation path or shell configuration changes, then open a
fresh shell and confirm the active `basectl`. It does not replace upgrading
Base or reconciling its runtime with setup.

Base also reads `~/.baserc` when it exists. Unlike `profile.conf`, `~/.baserc`
is user-managed and may be hand-edited. It is intended for simple,
shell-startup-safe Base preferences such as `BASE_DEBUG=1`; it should not become
a second `.bashrc` with arbitrary setup logic. See
[Runtime Environment](runtime-environment.md) for the full variable
contract and mutability policy.

`~/.baserc` must not set Base-owned runtime or profile variables such as
`BASE_HOME`, `BASE_BIN_DIR`, `BASE_LIB_DIR`, `BASE_BASH_LIBS_DIR`,
`BASE_BASH_LIBS_SOURCE`, `BASE_OS`, `BASE_PLATFORM`, `BASE_HOST_ENV`, `BASE_SHELL`,
`BASE_PLATFORM_TOOLS_HOME`, `BASE_PLATFORM_TOOLS_BIN_DIR`,
`BASE_PROFILE_VERSION`, `BASE_ENABLE_BASH_DEFAULTS`, or
`BASE_ENABLE_ZSH_DEFAULTS`. Base startup snippets reject and restore those
variables if `~/.baserc` tries to change them.

Base-managed sections use explicit markers such as:

```bash
# >>> base: bashrc managed >>>
# ... Base-managed content ...
# <<< base: bashrc managed <<<
```

### Base Snippets

The managed sections source matching snippets under `lib/shell/`:

- `lib/shell/bash_profile` for `~/.bash_profile`
- `lib/shell/bashrc` for `~/.bashrc`
- `lib/shell/zprofile` for `~/.zprofile`
- `lib/shell/zshrc` for `~/.zshrc`

The names intentionally mirror the dotfiles they support, without leading dots
inside the repository.

Bash snippets and the Bash runtime rcfile share `lib/shell/baserc_guard.sh` for
safe `~/.baserc` loading. Zsh snippets keep their own guard logic for now.

### Login Profiles

`bash_profile` and `zprofile` stay thin.

For Bash, Base makes the login-shell bridge explicit: the Bash profile snippet
sources `~/.bashrc` with a guardrail. Bash needs this because login Bash shells
do not automatically read `~/.bashrc`.

For Zsh, Base does not source `~/.zshrc` from `zprofile`. Zsh already reads
`~/.zshrc` for interactive shells.

### Interactive RC Files

`bashrc` and `zshrc` are where interactive shell behavior belongs.

They are responsible for:

- guarding against non-interactive execution
- guarding against repeated sourcing
- deriving and exporting `BASE_HOME` from the sourced Base snippet
- adding Base's `bin/` directory to `PATH` so `basectl` is available after login
- adding an optional sibling `base-platform-tools/bin` directory to `PATH` when
  that repo is present
- keeping dotfile integration separate from the full Base runtime bootstrap
- optionally enabling shared shell defaults when `basectl update-profile --defaults` is used

They do not source `base_init.sh`. Base runtime setup happens only when the
`basectl` command runs a Base command, runs an explicit script path, or starts a
Base-enabled Bash shell.

When `basectl activate <project>` starts an interactive Bash runtime shell, it
uses Base's runtime rcfile rather than making Bash read `~/.bashrc` directly.
That runtime rcfile loads `base_init.sh`, sources the user's `~/.bashrc` once
with guardrails, activates the project virtual environment, and finally sets the
Base runtime prompt. This keeps user aliases and normal interactive Bash
behavior available while making Base stdlib functions such as `import_base_lib`
available during user Bash startup.

### Debugging Shell Startup

Set `BASE_DEBUG=1` to make Base-managed shell startup snippets print diagnostic
messages while they run. This is intentionally independent of `base_init.sh` and
stdlib logging, because dotfile debugging can happen before the Base runtime is
loaded.

For normal terminal startup, put this in `~/.baserc`:

```bash
BASE_DEBUG=1
```

For one-off checks, use an environment variable:

```bash
BASE_DEBUG=1 bash --rcfile ~/.bashrc -i
BASE_DEBUG=1 zsh -i
BASE_DEBUG=1 basectl
```

Diagnostics are printed to stderr and show which Base snippet loaded, how
`BASE_HOME` was derived, whether `$BASE_HOME/bin` was added to `PATH`, whether
optional shell defaults were enabled, and how the Base runtime shell was layered.

For command debugging, `basectl -v <command>` enables DEBUG logs after the Base
runtime is loaded and the selected command is dispatched. For earlier startup
debugging, use wrapper options that are consumed by `bin/basectl` before
`base_init.sh` is sourced:

- `--debug-wrapper` enables `BASE_BASH_LIBS_LOG_DEBUG=1` before runtime
  initialization, including DEBUG diagnostics from reusable Bash libraries.
- `--utc-wrapper` enables `BASE_BASH_LIBS_LOG_UTC=1` before runtime
  initialization for Bash wrapper and library log timestamps. It does not
  change Python CLI log timestamps.
- `--color` preserves color-aware wrapper argument handling while keeping the flag
  out of command arguments.

Prefer `-v` unless the problem happens before the command implementation starts.

### Standard Shell Defaults

Base can provide optional, opinionated shell defaults, but they are not enabled
by plain `basectl update-profile`.

Current default-setting scripts are:

- `lib/shell/base_defaults.sh` for shell-neutral defaults shared by Bash and Zsh
- `lib/shell/bash_defaults.sh` for Bash-specific defaults
- `lib/shell/zsh_defaults.sh` for Zsh-specific defaults

Users can opt in during profile updates with:

```bash
basectl update-profile --defaults
```

Users can opt out again with:

```bash
basectl update-profile --no-defaults
```

Those defaults are intended to stay conservative:

- aliases like `rm -i`, `cp -i`, `mv -i`
- vi-style command editing
- completion ergonomics
- editor defaults
- pager defaults
- prompt defaults
- terminal usability behavior
- history behavior, including duplicate suppression, timestamped history, and
  multi-line command preservation

The defaults should not become a personal dotfile bundle. The following remain
outside `basectl update-profile --defaults` unless Base adds a separate,
explicit opt-in:

- color or listing aliases for tools such as `ls`, `grep`, or `diff`
- navigation shortcuts, `CDPATH`, auto-directory changes, or spelling
  correction
- signing and agent helpers such as `GPG_TTY`
- strict shell modes such as global `errexit`, `nounset`, or `pipefail`
- prompt features that run expensive checks, such as dirty Git status

Those settings are platform-sensitive, workflow-specific, or more likely to
change command behavior in surprising ways. Keep personal aliases and functions
in normal shell dotfiles, and keep simple Base preferences in `~/.baserc`.
