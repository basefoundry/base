# Homebrew Upgrade Rehearsal

Use this checklist before Base 1.0.0 to prove the consumer upgrade path from an
existing Homebrew install to a release candidate or equivalent test formula.
This is separate from the tap update checklist: the tap checklist proves the
formula can be published, while this rehearsal proves an existing user can
upgrade without losing local Base state.

## Preconditions

- Run on a macOS machine or test account that can install Homebrew packages.
- Start from an existing released Homebrew install of Base.
- Use a test `HOME` when possible so shell startup and `~/.base.d` preservation
  can be checked without mutating a personal account.
- Use a scratch workspace with a Base-managed project such as `base-demo`.
- Confirm Homebrew health before starting:

  ```bash
  brew update
  brew doctor
  brew info codeforester/base/base
  ```

Do not accept the rehearsal if Homebrew cannot install or upgrade packages on
the host. Fix the host prerequisite first, then rerun the rehearsal.

## Rehearsal Commands

Create an isolated test account shape:

```bash
TEST_ROOT="$(mktemp -d /private/tmp/base-homebrew-upgrade.XXXXXX)"
mkdir -p "$TEST_ROOT/home/.base.d" "$TEST_ROOT/work"
git clone https://github.com/codeforester/base-demo.git "$TEST_ROOT/work/base-demo"
printf 'workspace:\n  root: %s/work\n' "$TEST_ROOT" > "$TEST_ROOT/home/.base.d/config.yaml"
```

Install the current released formula and prepare local state:

```bash
brew install codeforester/base/base
env -u BASE_HOME -u BASE_PROJECT -u BASE_PROJECT_ROOT \
  HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl setup
env -u BASE_HOME -u BASE_PROJECT -u BASE_PROJECT_ROOT \
  HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl update-profile
```

Record the pre-upgrade state:

```bash
env HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl version
env HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl projects list
shasum -a 256 "$TEST_ROOT/home/.base.d/config.yaml"
test -x "$TEST_ROOT/home/.base.d/base/.venv/bin/python"
```

Upgrade through the tap path:

```bash
brew update
brew upgrade codeforester/base/base
```

For a pre-1.0.0 release candidate, use the candidate formula or tap branch that
will become the published formula. Record the exact command, tap ref, formula
path, and archive checksum used for the rehearsal.

Verify the upgraded install:

```bash
env HOME="$TEST_ROOT/home" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
  bash -lc 'command -v basectl && basectl version'
env HOME="$TEST_ROOT/home" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
  zsh -lc 'command -v basectl && basectl version'
env HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl check
env HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl doctor
env HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl setup base-demo
env HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl check base-demo
env HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl doctor base-demo
env HOME="$TEST_ROOT/home" PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  /usr/local/bin/basectl test base-demo
shasum -a 256 "$TEST_ROOT/home/.base.d/config.yaml"
```

Accept the rehearsal only when:

- `brew upgrade codeforester/base/base` exits zero.
- The `~/.base.d/config.yaml` checksum is unchanged.
- The Base virtual environment still exists and `basectl check` accepts it.
- Fresh Bash and Zsh login shells resolve `basectl` to the Homebrew install.
- `basectl projects list` still discovers the scratch project.
- `basectl setup`, `check`, `doctor`, and `test` pass for the scratch project.

If any Base-specific breakage appears, fix it or file a blocking follow-up
before 1.0.0. If a host prerequisite blocks the run, record it and rerun on a
qualified host; do not close the rehearsal issue.

## 2026-06-09 Run Record

Issue: #526

Result: blocked before Base could be installed through Homebrew.

Host facts:

- macOS: 26.5.1 x86_64
- Homebrew: 5.1.15-211-ge294979
- Homebrew prefix: `/usr/local`
- Xcode: 26.5
- CLT reported by Homebrew: 11.3.1
- Existing `basectl` on `PATH`: source checkout at `<workspace>/base/bin/basectl`
- Homebrew formula state before rehearsal: `codeforester/base/base` stable
  `0.3.0`, not installed

Commands attempted:

The local `base-demo` source path is elided in this public note.

```bash
TEST_ROOT="$(mktemp -d /private/tmp/base-526-homebrew-upgrade.XXXXXX)"
mkdir -p "$TEST_ROOT/work" "$TEST_ROOT/home/.base.d"
printf 'workspace:\n  root: %s/work\n' "$TEST_ROOT" > "$TEST_ROOT/home/.base.d/config.yaml"
git clone <local-base-demo-checkout> "$TEST_ROOT/work/base-demo"
brew install codeforester/base/base
brew install --ignore-dependencies codeforester/base/base
brew config
brew doctor
```

Observed result:

- `brew install codeforester/base/base` exited 1 before installing Base.
- `brew install --ignore-dependencies codeforester/base/base` also exited 1
  with the same host prerequisite failure.
- Homebrew reported: `Your Command Line Tools are too outdated` and instructed
  the operator to install Command Line Tools for Xcode 26.3.
- `brew doctor` reported the same CLT warning.

Commands not reached:

- `basectl setup`
- `basectl update-profile`
- `brew upgrade codeforester/base/base`
- post-upgrade Base and `base-demo` checks

Next action:

Update Command Line Tools on the rehearsal host, or rerun this checklist on a
host where `brew doctor` does not block package installation. Issue #526 should
remain open until the actual Homebrew upgrade command and post-upgrade checks
complete successfully.
