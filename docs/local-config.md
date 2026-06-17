# Local Config

Base reads machine-local user configuration from:

```text
~/.base.d/config.yaml
```

`basectl setup` creates this file with a small first-run default when it is
missing:

```yaml
workspace:
  root: ~/work
```

Base still treats a missing file as an empty YAML mapping so read-only commands
and partial installations can run before setup has seeded the file.

Inspect it with:

```bash
basectl config path
basectl config show
basectl config doctor
```

`basectl config path` prints the default path without requiring the Base Python
environment. `show` prints the parsed config as JSON. `doctor` reports whether
the file exists, whether it is valid YAML, whether it is a mapping, and whether
the path is a symlink.

## Ownership Boundary

Base owns the meaning of `~/.base.d/config.yaml`.

The user owns how that file is edited, backed up, copied, or synced. After Base
creates the first-run default, Base does not overwrite existing config files or
symlinks.

Base does not automate iCloud, dotfile, or backup setup. Developers can edit the
YAML directly.

Good ways to keep this file across machines include:

- iCloud Drive, if the user chooses to keep a symlink there
- chezmoi or another dotfile manager
- a private dotfiles repository
- Time Machine
- manual copy during machine setup

Base should tolerate ordinary filesystem choices such as symlinks, but it should
not assume a specific sync provider. Work machines, personal machines, and
managed corporate environments can have very different policies around iCloud
and cloud sync.

## Config Precedence

For Python commands built on `base_cli.App`, configuration is loaded in this
order:

1. user config: `~/.base.d/config.yaml`
2. project config: `<project>/.base/config.yaml`
3. explicit config from `--config`
4. recognized environment variables
5. direct command-line standard options

Later layers override earlier layers for the same key.

Recognized environment variables include:

- `BASE_CLI_ENVIRONMENT`
- `BASE_CLI_LOG_LEVEL`
- `BASE_CLI_KEEP_TEMP`

`BASE_CACHE_DIR` separately controls the runtime cache/log/temp root; it is not
stored in the user config.

## Workspace Root

`workspace.root` tells Base where to discover project repositories when a command
needs a workspace scan:

```yaml
workspace:
  root: ~/work
  manifest: ~/work/base-workspace/workspace.yaml
```

Project discovery uses this order:

1. explicit `--workspace <path>` for the current command
2. `workspace.root` from `~/.base.d/config.yaml`
3. the parent directory of `BASE_HOME`

This distinction matters for Homebrew installs. In a source checkout,
`BASE_HOME` is usually the `base` repository inside a shared directory such as
`~/work/base`, so `BASE_HOME`'s parent is a reasonable fallback. In a Homebrew
install, `BASE_HOME` points to the stable Homebrew install location, such as
`/usr/local/opt/base/libexec` or `/opt/homebrew/opt/base/libexec`, not the
developer's workspace. The first-run default sets `workspace.root` to `~/work`;
edit that value to make commands such as
`basectl projects list`, `basectl activate <project>`, and
`basectl test <project>` independent of how Base itself was installed.

`workspace.manifest` is optional. When set, `basectl workspace status`,
`check`, `doctor`, and `clone` use that manifest unless the command supplies
`--manifest <path>`. The command-line flag always takes precedence.

`workspace.manifest_source` is optional. When set, `basectl workspace pull`
uses it as the canonical manifest source unless the command supplies
`--source <url-or-path>`. Supported sources are local paths, `file://` URLs, and
`http://` or `https://` raw file URLs. Pull validates fetched content as a
workspace manifest before updating `workspace.manifest`.

`workspace.root` and `workspace.manifest` must be absolute paths or start with
`~`. `workspace.manifest_source` must be a non-empty string when provided.
Base does not create the workspace directory automatically; `basectl config
doctor` reports whether the configured path exists.

## GitHub Defaults

User-local GitHub defaults reduce repeated flags for workspace repository
commands:

```yaml
github:
  default_owner: codeforester
  clone_protocol: ssh
```

`github.default_owner` lets short repository names resolve during
`basectl repo clone <name>`. Without it, short names require
`--owner <owner>`.

`github.clone_protocol` controls the clone URL shown in dry-run and planning
output. Supported values are `ssh` and `https`; when omitted, Base reports SSH
URLs. The actual clone delegates to `gh repo clone <owner/repo> <path>` so the
GitHub CLI remains responsible for GitHub authentication and its own transport
behavior.

`basectl config doctor` validates these GitHub defaults before clone time. It
reports invalid owner names or unsupported clone protocols as config schema
errors while treating omitted GitHub defaults as valid.

## IDE Preferences

User-local IDE preferences can add machine-specific IDE behavior without
changing a project's `base_manifest.yaml`:

```yaml
ide:
  enabled: true

  vscode:
    enabled: true
    install: false
    extra_extensions:
      - eamodio.gitlens
    settings:
      editor.fontSize: 14

  cursor:
    enabled: false
```

The design decision is to keep IDE preferences inside the existing
`~/.base.d/config.yaml` file instead of introducing `~/.base.d/ide.yaml`.
IDE choices are machine-local Base configuration, and the existing config
commands already give users a stable path, JSON inspection, and diagnostics:

```bash
basectl config path
basectl config show
basectl config doctor
```

The project manifest remains authoritative for project requirements. User
settings are additive:

- user `extra_extensions` are appended to project extensions
- user settings are applied only when the project does not declare the same key
- project settings win when both layers declare the same setting
- users can disable IDE handling for one machine with `ide.enabled: false` or
  `ide.<name>.enabled: false`
- user `install` can opt a machine into or out of IDE app installation without
  changing the project's extension or settings requirements

If a user setting conflicts with a project setting, Base reports a warning and
uses the project setting.

Supported IDE preference keys are intentionally narrow:

- `ide.enabled`
- `ide.vscode.enabled`
- `ide.vscode.install`
- `ide.vscode.extra_extensions`
- `ide.vscode.settings`
- `ide.cursor.enabled`
- `ide.cursor.install`
- `ide.cursor.extra_extensions`
- `ide.cursor.settings`

Unknown IDE names and unsupported keys are rejected. Settings values must be
JSON-serializable because Base writes them to IDE `settings.json` files.

Aside from the first-run seed, Base does not edit this file. There is no
`basectl config set` or IDE preference editor command by design; developers can
edit YAML directly, and Base keeps the runtime behavior inspectable through
`basectl config show` and `basectl config doctor`.

## Sync Guidance

iCloud can be useful for a single developer's multi-Mac setup, but it is not a
Base feature. Base should not create iCloud folders, move config into iCloud, or
automatically symlink config into iCloud Drive.

Users who want iCloud sync can create their own symlink from
`~/.base.d/config.yaml` to a file in iCloud Drive. `basectl config doctor` will
surface that the config path is a symlink.

This boundary keeps Base focused on workstation bootstrap and project
orchestration rather than backup, sync, or dotfile management.
