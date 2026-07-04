# Base FAQ

## First-Time Installation

### What should I run on a blank macOS machine?

Use `bootstrap.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash
```

The bootstrapper verifies macOS, ensures Homebrew is available, installs Git and
a supported Bash when needed, installs or updates Base, and then prints the
exact `basectl` commands needed to finish setup.

### Why does bootstrap print commands instead of changing my shell automatically?

`bootstrap.sh` is the first-mile handoff into Base. It intentionally avoids
editing shell startup files so a user can see what was installed and choose when
Base should affect new shells. Shell integration is owned by:

```bash
basectl update-profile
```

For a source checkout that is not yet on `PATH`, use the absolute command that
bootstrap prints, typically:

```bash
~/work/base/bin/basectl update-profile
```

### When should I use bootstrap.sh, install.sh, Homebrew, or a source checkout?

Use `bootstrap.sh` on a new or uncertain macOS machine. It handles missing
first-mile prerequisites and then hands off to Base.

Use Homebrew when you already have Homebrew and Bash and want Base managed like
an ordinary installed tool:

```bash
brew trust basefoundry/base
brew install basefoundry/base/base
basectl setup
basectl update-profile
exec "$SHELL" -l
```

Use the full formula name `basefoundry/base/base` for installs and upgrades.
`basefoundry/base` is the tap name, not the formula, and bare `base` can resolve
to unrelated Homebrew formulae or casks.

Trusting the tap lets Homebrew load both the `base` formula and Base's
tap-owned `base-bash-libs` dependency. The command is safe to rerun on machines
that already trust `basefoundry/base`.

Use a source checkout when you are contributing to Base or want to inspect and
run the repository directly. This is also the preferred active install for a
Base development machine:

```bash
git clone https://github.com/basefoundry/base.git ~/work/base
~/work/base/bin/basectl setup
~/work/base/bin/basectl update-profile
exec "$SHELL" -l
```

Use `install.sh` when you specifically want the source-install path to clone or
update Base and then run setup/profile commands as one script.

### How do I choose source mode or Homebrew mode during bootstrap?

Pass an explicit mode:

```bash
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --source
curl -fsSL https://raw.githubusercontent.com/basefoundry/base/HEAD/bootstrap.sh | bash -s -- --brew
```

Without an explicit mode, bootstrap preserves an existing Homebrew Base install,
then an existing source checkout, and otherwise defaults to source mode.

## Homebrew And Source Coexistence

### Can Homebrew-installed Base and source-cloned Base coexist?

Yes. They can coexist because the active `basectl` is whichever executable your
shell resolves first. Coexistence is not dangerous, but it can make validation
ambiguous because both installs normally share user state under `~/.base.d`.

For a Base contributor machine, prefer one active owner: the source checkout.
Use Homebrew-installed Base when validating the consumer install or upgrade
experience, preferably in a test account, on a separate machine, or with an
isolated `HOME`.

A source checkout can always be run explicitly:

```bash
~/work/base/bin/basectl version
```

That does not require it to be first on `PATH`.

On Apple Silicon, a Homebrew install is usually available as:

```bash
/opt/homebrew/bin/basectl version
```

On Intel macOS, it is usually available as:

```bash
/usr/local/bin/basectl version
```

### Why does Homebrew install both basectl and base-wrapper?

`basectl` is the command users normally run. Homebrew also installs
`base-wrapper` because Base's Bash commands and project launchers use it to run
Python packages through the selected Base project virtual environment.

For example, Homebrew exposes both executables under the Homebrew prefix, but
`base-wrapper` is primarily an implementation bridge. Users should usually run
`basectl` or a project-owned launcher instead of invoking `base-wrapper`
directly.

`base-wrapper` answers "which Python environment should run this package?",
while `base_cli` answers "how should a Base Python CLI behave?" See the
`base_cli` question below for that package's role.

### Why does Base require an external base-bash-libs checkout or package?

Base's reusable Bash helpers live in the standalone
`basefoundry/base-bash-libs` repository so other scripts can reuse the logging,
command execution, filesystem, and Git conventions without depending on the
full Base workspace control plane.

That separation also keeps the Homebrew packaging path cleaner: `base-bash-libs`
can mature as its own formula, and a future Homebrew/core Base formula can
depend on it directly instead of bundling reusable library files inside Base.

Base resolves the libraries in this order:

1. `BASE_BASH_LIBS_DIR`, for tests and nonstandard source worktrees.
2. A sibling checkout at `~/work/base-bash-libs/lib/bash`.
3. The Homebrew `base-bash-libs` package when Base itself is Homebrew-managed.

If the library source is missing, clone the sibling repository or install the
tap formula:

```bash
git clone https://github.com/basefoundry/base-bash-libs.git ~/work/base-bash-libs
brew install basefoundry/base/base-bash-libs
```

`basectl check` and `basectl doctor` report the resolved source through the
`BASE-D007` finding. See [Base Bash Libraries](docs/base-bash-libs.md) for the
full resolution contract.

### How do I know which basectl is active?

Run:

```bash
command -v basectl
type -a basectl
```

`command -v basectl` shows the command your shell will run by default.
`type -a basectl` shows every matching command your shell can see.
When testing a specific install route, use the absolute `basectl` path for that
route instead of relying on `PATH`.

### How do I validate Homebrew Base from a source-managed shell?

Use an isolated `HOME` and clear the Base runtime contract before invoking the
Homebrew-managed executable. This keeps an active source checkout, runtime
shell, or project activation from leaking into the consumer install test:

```bash
brew_home=/tmp/base-brew-home
mkdir -p "$brew_home"

HOME="$brew_home" env -u BASE_HOME \
  -u BASE_PROJECT \
  -u BASE_PROJECT_ROOT \
  -u BASE_PROJECT_MANIFEST \
  -u BASE_PROJECT_VENV_DIR \
  /usr/local/bin/basectl setup

HOME="$brew_home" env -u BASE_HOME \
  -u BASE_PROJECT \
  -u BASE_PROJECT_ROOT \
  -u BASE_PROJECT_MANIFEST \
  -u BASE_PROJECT_VENV_DIR \
  /usr/local/bin/basectl test base
```

Use `/opt/homebrew/bin/basectl` on Apple Silicon Homebrew installs.

### If I have both installs, which one should bootstrap prefer?

Bootstrap should not silently take over an existing setup. If no mode is
specified, it preserves an existing Homebrew Base install first, then an
existing source checkout. Pass `--source` or `--brew` when you want a specific
route.

## Setup, Profile, And Diagnostics

### What is the difference between basectl setup and basectl update-profile?

`basectl setup` prepares Base and project prerequisites: Homebrew artifacts,
Python virtual environments, configured project artifacts, and other declared
setup requirements.

`basectl update-profile` updates shell startup files so `basectl` and Base shell
integration are available in new interactive shells.

### What is the difference between basectl setup, basectl onboard, and basectl doctor?

`basectl setup` makes the machine or project ready.

`basectl onboard` is the guided first-run flow for Base itself.

`basectl doctor` reports what is healthy, missing, or misconfigured. It is the
best command to run when something does not look right.

### What is the difference between basectl check and basectl doctor?

Both commands are read-only, but they serve different moments.

Use `basectl check [project]` when you want a quick status check that can be
used in scripts, CI, or a regular "is this ready?" workflow. It verifies the
same local prerequisites and project health contracts that setup manages, and
it can emit JSON when automation needs structured output.

Use `basectl doctor [project]` when something failed or feels confusing. Doctor
is the human-oriented diagnostic command: it reports `ok`, `warn`, and `error`
findings, includes stable finding IDs, and prints suggested fixes where Base
knows the recovery path.

### After Homebrew installation, why do I still need basectl setup?

Homebrew installs Base's files. `basectl setup` prepares the local Base runtime
under `~/.base.d/base/.venv` and reconciles other prerequisites that Base needs
to operate.

### Why can setup fail on a Homebrew `brew link` conflict?

Prerequisite profiles can install ordinary Homebrew tools and, for explicitly
selected host profiles, Homebrew casks such as Multipass. A tool can pull a
Homebrew dependency that needs to be linked into Homebrew's prefix. If files
such as `/usr/local/bin/python3`, `/usr/local/bin/pip3`, or
`/usr/local/bin/idle3` already point at another Python installation, Homebrew
may stop with:

```text
Error: The `brew link` step did not complete successfully
```

Base reports Homebrew's suggested dry-run command when it sees this failure.
Run the dry-run first and inspect the files Homebrew would overwrite:

```bash
brew link --overwrite python@3.13 --dry-run
```

If the dry-run only lists stale files you are comfortable replacing, run the
same command without `--dry-run`, then rerun the Base setup command:

```bash
brew link --overwrite python@3.13
basectl setup --profile sre
```

Do not run the overwrite command blindly on a machine where those Python shims
are intentionally managed outside Homebrew.

## Workspace Configuration

### How should I configure my workspace root?

On first setup, Base creates `~/.base.d/config.yaml` with:

```yaml
workspace:
  root: ~/work
```

If repositories live side by side under a different directory, edit:

```text
~/.base.d/config.yaml
```

Base does not overwrite existing config files or symlinks. The workspace root
helps commands such as `basectl projects list`, `basectl activate <project>`,
and `basectl test <project>` find participating repositories.

### What belongs in Base versus a project-owned installer?

Base owns workspace-level conventions: setup orchestration, diagnostics, project
discovery, shell integration, common helper libraries, and repeatable command
contracts.

A project-owned installer owns product-specific setup: credentials, service
accounts, domain data, app-specific local services, and any onboarding language
that belongs to that product rather than to Base.

Project installers should call Base when they need workspace primitives instead
of reimplementing them.

## Project Commands

### What is basectl demo?

`basectl demo <project>` runs the project-declared demo script from
`base_manifest.yaml`. A project declares the script under `demo.script`, and
Base runs it from the project root with the same project environment used by
other Base project commands. Use `-- --non-interactive` when the demo needs to
run in CI or another non-interactive context. See [Project Demo Workflow](docs/project-demo-workflow.md).

### What does basectl repo init do?

`basectl repo init <name>` creates the standard Base-managed repository
baseline: README, VERSION, CHANGELOG, CONTRIBUTING, LICENSE, `.gitignore`,
`base_manifest.yaml`, a validation script, and a GitHub Actions test workflow.
When a GitHub repo is provided or inferred, Base can also apply the standard
repository settings and labels; use `--dry-run` to preview everything first.
See [Repository Baseline](docs/repo-baseline.md).

### How do I see health across all workspace projects?

Use `basectl workspace status`, `basectl workspace check`, or
`basectl workspace doctor`. These commands discover projects under the
configured `workspace.root` in `~/.base.d/config.yaml`, falling back to
`BASE_HOME`'s parent when no workspace root is configured. Invalid manifests
show up as per-project findings so one broken project does not hide the rest of
the workspace.

### How do I inspect logs from a failed Base command?

Use `basectl logs` to list recent command runs and `basectl logs --tail` to
follow the newest log in real time. Filter by command name with
`basectl logs --command setup`, print only the matching path with
`basectl logs --path`, or open the newest matching log with
`basectl logs --open`. Base stores logs under the Base cache root, normally
`~/Library/Caches/base` on macOS, so they do not accumulate under `~/.base.d`.
Use command verbosity such as `basectl -v setup` when you want a new run to
capture DEBUG details before inspecting it with `basectl logs`. See
`basectl logs --help` for all options.

## Writing Base Scripts

### How should a project expose a Python CLI?

Expose a small executable launcher from the project's `bin/` directory and have
that launcher delegate to `base-wrapper`:

```bash
#!/usr/bin/env bash
exec "$BASE_HOME/bin/base-wrapper" --project "${BASE_PROJECT:-example}" example_cli "$@"
```

When `basectl activate <project>` starts a project shell, Base adds the
project's `bin/` directory to `PATH` if it exists. That lets users run the
launcher as an ordinary command while Base keeps Python execution tied to the
selected project virtual environment.

`base-wrapper` runs Python packages, not arbitrary `.py` file paths. The package
name in the launcher, `example_cli` above, is executed as `python -m
example_cli` using the Python interpreter from `~/.base.d/<project>/.venv`. The
wrapper also sets `BASE_HOME`, sets `BASE_PROJECT`, and adds Base's Python
library roots to `PYTHONPATH`.

### Should users invoke Python CLI packages directly?

Usually no. Treat Python packages as implementation details unless a
project-owned launcher exposes them from `bin/`.

Direct invocation makes users choose a Python interpreter, virtual environment,
and `PYTHONPATH` by hand. The launcher plus `base-wrapper` keeps those choices
consistent with `basectl setup`, project activation, and Base-managed project
virtual environments.

### Does base-wrapper work with uv-managed Python projects?

Yes, as long as Base has resolved the project virtual environment first.
`base-wrapper` does not call `uv` and does not read `base_manifest.yaml` by
itself. It runs the Python interpreter from `BASE_PROJECT_VENV_DIR` when that
variable is set, otherwise it falls back to `~/.base.d/<project>/.venv`.

For projects that declare `python.manager: uv`, Base project commands and
activated project shells set `BASE_PROJECT_VENV_DIR` to the project-local
`.venv` that uv owns. A launcher run from that context can still delegate to
`base-wrapper`:

```bash
#!/usr/bin/env bash
exec "$BASE_HOME/bin/base-wrapper" --project "${BASE_PROJECT:-example}" example_cli "$@"
```

If you invoke `base-wrapper` directly outside a resolved Base project context,
set `BASE_PROJECT_VENV_DIR` yourself or run through `basectl activate`,
`basectl run`, or another Base command that resolves the project first.

### What is the base_cli Python package for?

`base_cli` is Base's Python CLI framework. It wraps Click with Base conventions
so Base and Base-supported projects get the same command behavior without
rebuilding it for every Python command.

Use `base_cli.App` for Python CLIs that should have Base-style logging, standard
options such as `--debug` and `--log-file`, run-scoped temp/cache/log
directories, config loading, manifest-aware project discovery, sensitive
argument redaction, and test helpers.

`base-wrapper` answers "which Python environment should run this package?"
`base_cli` answers "how should this Python CLI behave once it starts?"

### How do I write a Bash script that uses Base's standard library?

Use `basectl` as the script interpreter:

```bash
#!/usr/bin/env basectl

main() {
    local project="${1:-}"

    if [[ -z "$project" ]]; then
        print_error "Project name is required."
        return 2
    fi

    log_info "Checking project '$project'."
    run git status --short
}
```

Make the script executable and run it directly:

```bash
chmod +x ./scripts/check-project.sh
./scripts/check-project.sh base
```

The shebang form requires `basectl` to be on `PATH`. If Base is not on `PATH`
yet, run the script explicitly through the installed `basectl`:

```bash
/path/to/base/bin/basectl ./scripts/check-project.sh base
```

In this mode, the script should define `main` and should not call `main "$@"`
itself. `basectl` receives the script path from the shebang, establishes the
Base runtime through `base_init.sh`, loads Base's Bash standard library, sources
the script, and then calls `main` with the user arguments.

That gives the script helpers such as `log_info`, `print_error`, `fatal_error`,
`run`, `assert_command_exists`, and `import_base_lib` without sourcing
`lib_std.sh` directly.

### When should I source lib_std.sh directly instead?

Source `lib_std.sh` directly only for standalone Bash scripts that are not
intended to run through `basectl`. Use the standalone `base-bash-libs` package:

```bash
#!/usr/bin/env bash
base_bash_libs_prefix="$(brew --prefix basefoundry/base/base-bash-libs)"
source "$base_bash_libs_prefix/libexec/lib/bash/std/lib_std.sh"

main() {
    run echo "hello"
}

main "$@"
```

Base-native scripts should prefer the `#!/usr/bin/env basectl` pattern because
it uses the same runtime bootstrap path as Base command implementations.

For deeper details, see [Execution Model](docs/execution-model.md), [Base
Standards](STANDARDS.md), and
[Base Bash Libraries](docs/base-bash-libs.md).

## More Information

Useful starting points:

- [README](README.md) for the product overview and first-run guide.
- [Documentation Map](docs/README.md) for architecture and design docs.
- [Project Installers](docs/project-installers.md) for project-owned installer
  boundaries.
- [Tool Boundaries](docs/tool-boundaries.md) for ecosystem ownership decisions.
