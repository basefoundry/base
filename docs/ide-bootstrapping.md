# IDE Bootstrapping

Base can bootstrap supported IDEs for Base-managed projects on macOS. This is
part of Base's workstation setup responsibility: a fresh machine should be able
to install the tools a project expects, validate that they are present, and
surface clear recovery guidance through `basectl check` and `basectl doctor`.

Base does not try to become a general IDE preference manager. It orchestrates
IDE readiness for project work.

## Scope

IDE bootstrapping is currently macOS-only. Linux IDE setup is not implemented
yet; see [Linux Support](linux-support.md) for the current Linux runtime-support
status and boundaries.

Base owns:

- installing supported IDEs through Homebrew casks when a project opts in
- installing declared IDE extensions through the IDE CLI
- adding missing user-level IDE settings required by a project
- resolving Base-owned paths such as the project virtual environment Python
- reporting IDE app, CLI, extension, and settings state through check/doctor

Base does not own:

- every personal editor preference
- extension version pinning
- workspace `.vscode/settings.json` generation
- JetBrains IDE configuration
- generic dotfile synchronization

## Manifest Schema

Projects opt in through `base_manifest.yaml`:

```yaml
project:
  name: example

ide:
  vscode:
    install: true
    extensions:
      - ms-python.python
      - ms-python.pylint
      - github.vscode-pull-request-github
    settings:
      python.defaultInterpreterPath: auto
      editor.formatOnSave: true

  cursor:
    install: true
    extensions:
      - ms-python.python
    settings:
      python.defaultInterpreterPath: auto
```

Supported IDE keys:

- `vscode`
- `cursor`

Supported fields:

- `install`: optional boolean. When true, `basectl setup` installs the IDE with
  Homebrew cask.
- `extensions`: optional list of extension IDs.
- `settings`: optional mapping of user-level IDE settings.

The only supported special setting value today is:

```yaml
python.defaultInterpreterPath: auto
```

Base resolves that to:

```text
~/.base.d/<project>/.venv/bin/python
```

or to `$BASE_PROJECT_VENV_DIR/bin/python` when that override is set.

## Setup Behavior

`basectl setup <project>` performs IDE work in this order:

1. Install opted-in IDE apps through Homebrew casks.
2. Install missing declared extensions through the IDE CLI.
3. Add missing declared user-level settings.

VS Code uses:

```text
brew install --cask visual-studio-code
code --install-extension <extension>
~/Library/Application Support/Code/User/settings.json
```

Cursor uses:

```text
brew install --cask cursor
cursor --install-extension <extension>
~/Library/Application Support/Cursor/User/settings.json
```

If an IDE app is installed but its CLI is not available on `PATH`, Base reports
that state. Extension setup is skipped until the CLI is available.

## Additive Settings

IDE settings are additive-only.

If a setting key is absent, Base writes the project-requested value. If the user
already has that key with a different value, Base leaves the user value intact
and reports the divergence through check/doctor.

To accept the Base value, remove the key from the IDE `settings.json` and rerun:

```bash
basectl setup <project>
```

Settings writes are atomic: Base writes a temporary JSON file in the same
directory and then replaces `settings.json`.

## Validation

Use:

```bash
basectl check <project>
basectl doctor <project>
basectl check <project> --profile dev
basectl doctor <project> --profile dev
```

Default project checks keep IDE extension CLI probes out of the core runtime
acceptance path. IDE extension diagnostics run when the developer prerequisite
profile is active, for example with `--profile dev`.

IDE checks can include:

- requested IDE app installed through Homebrew cask
- IDE CLI available on `PATH`
- declared extensions installed
- declared settings present and matching

`doctor` provides human-oriented fix guidance for missing or divergent state.

## User-Local Preferences

User-local IDE preferences live in `~/.base.d/config.yaml`; Base should not add
a separate `~/.base.d/ide.yaml` file. The user config layer is machine-local and
additive over project manifests:

- project manifests declare project requirements
- user config can add personal extensions and settings
- project settings take precedence over user settings for the same key
- user config can disable IDE handling globally or for one supported IDE on a
  machine

This lets a project keep its required IDE contract in version control while a
developer adds local preferences without changing shared project files. See
[local-config.md](local-config.md) for the schema and sync boundary.

## Future Work

Future IDE-related work should remain inside Base's boundary: workstation
bootstrap and diagnostics for Base-managed projects.

Candidate future work:

- workspace `.vscode` settings if a real project needs shared editor settings
- Windsurf support if its CLI and settings surface match the VS Code family
- JetBrains support only after a clean, scriptable configuration surface is
  identified
- extension pinning only if Base adopts a deliberate VSIX management strategy
