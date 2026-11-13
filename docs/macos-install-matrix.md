# Local macOS Install Matrix

Base's local install matrix runs controlled scenarios as four dedicated macOS
accounts:

| Cell | Account | Route | Login shell |
| --- | --- | --- | --- |
| `source-bash` | `base-source-bash` | source checkout | Homebrew Bash |
| `source-zsh` | `base-source-zsh` | source checkout | Zsh |
| `brew-bash` | `base-brew-bash` | Homebrew | Homebrew Bash |
| `brew-zsh` | `base-brew-zsh` | Homebrew | Zsh |

The matrix is local macOS validation, not hosted CI. It deliberately does not
create a second Homebrew prefix or mutate accounts during an ordinary test
run.

## One-time administrator setup

Review the machine changes first:

```bash
./tools/macos_matrix_admin.sh --dry-run
```

The applying command must run with administrator privileges. It:

- writes `/etc/sudoers.d/base-macos-install-matrix`, scoped to the current
  operator and the four named matrix accounts;
- registers the Homebrew Bash path in `/etc/shells` when needed;
- assigns the two Bash accounts to Homebrew Bash and leaves the two Zsh
  accounts on `/bin/zsh`; and
- records the prior login shells and whether it added the shell entry.

After reviewing the dry-run, apply it with:

```bash
sudo ./tools/macos_matrix_admin.sh
```

The setup is idempotent. To restore the recorded account and shell state:

```bash
sudo ./tools/macos_matrix_admin.sh --remove
```

`--remove` only removes the sudoers file, shell entry, and login-shell changes
recorded by this setup. It does not remove Homebrew, checkouts, or user data.

## Scenario runner

Validate a scenario without running it:

```bash
./bin/base-matrix validate --scenario tests/fixtures/macos_matrix/trivial.json
```

Run the trivial contract in all four cells:

```bash
./bin/base-matrix run \
  --scenario tests/fixtures/macos_matrix/trivial.json \
  --cells all \
  --output-dir /tmp/base-macos-matrix
```

The runner performs a non-interactive `sudo -n -u <account> -i` preflight before
running scenario steps. It refuses accounts outside the fixed matrix and
blocks before scenario execution when passwordless runas is unavailable. A
scenario is validated against
[`macos-matrix-scenario.json`](schemas/macos-matrix-scenario.json) before it is
accepted or run. It contains a version, preconditions, ordered steps, expected
exit codes, output assertions, optional finding IDs, timeouts, and an optional
working directory relative to the Base checkout. The runner applies that
directory after the login shell changes to the matrix account's home, and
rejects paths that resolve outside the checkout. Commands are argument arrays
rather than shell strings.

Cells run serially because scenario commands can mutate shared resources such
as the Homebrew prefix or the checkout, even though each cell uses a different
account and result directory.

Each cell produces a result JSON document validated by
`docs/schemas/macos-matrix-result.json`, plus mode `0600` logs. Captured output
is redacted before it is persisted. Results include the full Base commit,
route, shell, account, platform, preconditions, step durations, finding IDs,
and relative log paths so later matrix-evidence tooling can reject stale or
ambiguous runs. A step terminated by a signal reports the conventional shell
status `128 + signal` in `actual_exit` and records the signal in `error`.

The real Homebrew upgrade and account-state validation remains a maintainer-run
step. Attach the result JSON and the exact host context to the implementation
PR; do not put private account paths, credentials, or unredacted logs into
public release evidence.
