# Base FAQ

## First-Time Installation

### What should I run on a blank macOS machine?

Use `bootstrap.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash
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

Use Homebrew when you want Base managed like an ordinary installed tool:

```bash
brew install codeforester/base/base
basectl setup
basectl update-profile
```

Use a source checkout when you are contributing to Base or want to inspect and
run the repository directly:

```bash
git clone https://github.com/codeforester/base.git ~/work/base
~/work/base/bin/basectl setup
~/work/base/bin/basectl update-profile
```

Use `install.sh` when you specifically want the source-install path to clone or
update Base and then run setup/profile commands as one script.

### How do I choose source mode or Homebrew mode during bootstrap?

Pass an explicit mode:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash -s -- --source
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash -s -- --brew
```

Without an explicit mode, bootstrap preserves an existing Homebrew Base install,
then an existing source checkout, and otherwise defaults to source mode.

## Homebrew And Source Coexistence

### Can Homebrew-installed Base and source-cloned Base coexist?

Yes. They can coexist because the active `basectl` is whichever executable your
shell resolves first. A source checkout can always be run explicitly:

```bash
~/work/base/bin/basectl version
```

That does not require it to be first on `PATH`.

### How do I know which basectl is active?

Run:

```bash
command -v basectl
type -a basectl
```

`command -v basectl` shows the command your shell will run by default.
`type -a basectl` shows every matching command your shell can see.

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

### After Homebrew installation, why do I still need basectl setup?

Homebrew installs Base's files. `basectl setup` prepares the local Base runtime
under `~/.base.d/base/.venv` and reconciles other prerequisites that Base needs
to operate.

## Workspace Configuration

### How should I configure my workspace root?

If repositories live side by side under a directory such as `~/work`, configure:

```yaml
workspace:
  root: ~/work
```

in:

```text
~/.base.d/config.yaml
```

This helps commands such as `basectl projects list`, `basectl activate
<project>`, and `basectl test <project>` find participating repositories.

### What belongs in Base versus a project-owned installer?

Base owns workspace-level conventions: setup orchestration, diagnostics, project
discovery, shell integration, common helper libraries, and repeatable command
contracts.

A project-owned installer owns product-specific setup: credentials, service
accounts, domain data, app-specific local services, and any onboarding language
that belongs to that product rather than to Base.

Project installers should call Base when they need workspace primitives instead
of reimplementing them.

## More Information

Useful starting points:

- [README](README.md) for the product overview and first-run guide.
- [Documentation Map](docs/README.md) for architecture and design docs.
- [Project Installers](docs/project-installers.md) for project-owned installer
  boundaries.
- [Tool Boundaries](docs/tool-boundaries.md) for ecosystem ownership decisions.
