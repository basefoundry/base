# Clean macOS Install Validation

Use this checklist to validate that Base installs cleanly on supported macOS
machines. It complements Intel Mac user testing and release-specific Homebrew
tap validation, but it is not a substitute for either one.

The checklist has two goals:

- prove that a new user can install Base through the supported Homebrew and
  source checkout paths
- keep the boundary between automated CI checks and manual macOS user testing
  explicit

If a checklist step exposes a missing automated check, file a focused follow-up
issue instead of expanding this checklist into a second test suite.

## Validation Record

Record this context for each run:

- Base ref, tag, or release version
- install route: Homebrew, bootstrap `--brew`, bootstrap `--source`, or manual
  source clone
- macOS version and hardware architecture
- default interactive shell
- whether Homebrew and Xcode Command Line Tools existed before the run
- whether the run is a clean install, upgrade, or reinstall
- links to any follow-up issues opened from the run

Avoid recording machine-specific absolute paths in the expected output. When a
path matters, record whether it matches the chosen install route, such as a
Homebrew prefix for Homebrew installs or the selected source checkout for source
installs.

## Automation Boundary

| Check | Where it belongs | Notes |
| --- | --- | --- |
| `git diff --check` | CI and local PR validation | Required for documentation-only updates to this checklist. |
| `bin/base-test` | CI and local source checkout validation | Exercises the hermetic test contract without installing real Homebrew packages. |
| `bootstrap.sh --dry-run` | CI or local source checkout validation | Confirms the planned first-mile route without mutating the machine. |
| Real Homebrew install or upgrade | Manual macOS validation | Requires the real package manager, network access, and user-owned install state. |
| Real shell profile update and terminal restart | Manual macOS validation | Requires the user's interactive shell startup files and a fresh login shell. |
| Real project activation | Manual macOS validation | Requires an interactive runtime shell; record the observed environment contract and exit cleanly. |
| Reference project setup, test, and demo | Manual today unless a focused automation issue exists | Use `base-demo` as the neutral project smoke test outside a source checkout. |

Do not run mutating Homebrew, shell profile, or user-project checks in ordinary
CI unless the runner is explicitly dedicated to this purpose.

## Clean-Machine Preconditions

Before starting either install path:

1. Use a supported macOS account that can install developer tools and Homebrew
   packages.
2. Open a fresh terminal without inherited Base variables such as `BASE_HOME`,
   `BASE_PROJECT`, `BASE_PROJECT_ROOT`, or `PYTHONPATH`.
3. Confirm network access to GitHub and Homebrew.
4. Decide whether this is a clean install, upgrade, or reinstall. For a clean
   install, remove or avoid previous Base shell startup sections and managed
   state before beginning.
5. Choose a scratch workspace that does not contain production project changes.
6. If both Homebrew and source checkouts are present, write down which
   `basectl` executable should win on `PATH`.

The run is acceptable only when failures are actionable and tied to the chosen
route. For example, an Xcode Command Line Tools prompt is acceptable only if the
checklist records that manual installation was required and the retry passed.

## Homebrew Install Path

Use this path when validating the consumer install experience.

### Install

For a machine that already has Homebrew:

```bash
brew install codeforester/base/base
basectl setup
basectl update-profile
exec "$SHELL" -l
```

For a first-mile bootstrap run that should choose the Homebrew route:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash -s -- --brew
```

Then run the handoff commands printed by `bootstrap.sh`. They should include
the Homebrew-managed `basectl` setup and profile steps:

```bash
basectl setup
basectl update-profile
exec "$SHELL" -l
```

Accept the install when:

- every command exits zero
- `command -v basectl` resolves to the Homebrew-managed install selected for
  the run
- `basectl version` and `basectl --version` report the expected Base version
- setup output contains no traceback, fatal shell error, or unresolved
  prerequisite

### Base Health

Run:

```bash
basectl check
basectl doctor
basectl logs --path
basectl logs --command setup
```

Accept the health checks when:

- `basectl check` exits zero
- `basectl doctor` reports no error findings
- `basectl logs --path` prints the log directory path
- `basectl logs --command setup` can read recent setup logs without a traceback

### Reference Project Smoke Test

Use `base-demo` to prove project discovery and project commands from a Homebrew
install:

```bash
cd <scratch-workspace>
git clone https://github.com/codeforester/base-demo.git
basectl projects list
basectl setup base-demo
basectl check base-demo
basectl doctor base-demo
basectl test base-demo
basectl demo base-demo -- --non-interactive
basectl activate base-demo
# exit the activated shell
```

If the scratch workspace is not discovered automatically, configure the local
workspace root as described in the top-level README, then rerun
`basectl projects list`.

Accept the smoke test when:

- `basectl projects list` includes `base-demo`
- setup, check, doctor, test, and demo all exit zero
- doctor reports no project error findings
- activation opens a project runtime shell with `BASE_PROJECT=base-demo` and a
  project root matching the scratch checkout
- exiting the runtime shell returns to the caller cleanly

## Source Checkout Install Path

Use this path when validating the contributor and dogfood experience.

### Install

For bootstrap source mode:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash -s -- --source
```

Then run the handoff commands printed by `bootstrap.sh`. They should point at
the selected source checkout:

```bash
<source-checkout>/bin/basectl setup --profile dev
<source-checkout>/bin/basectl update-profile
exec "$SHELL" -l
```

For a manual source clone:

```bash
git clone https://github.com/codeforester/base.git <source-checkout>
<source-checkout>/bin/basectl setup --profile dev
<source-checkout>/bin/basectl update-profile
exec "$SHELL" -l
```

Use plain `basectl setup` instead of `--profile dev` when the run is limited to
the first-run user path. Use `--profile dev` when the run must validate
`basectl test base`.

Accept the install when:

- every command exits zero
- `command -v basectl` resolves to the selected source checkout
- `basectl version` and `basectl --version` report the expected Base version
- setup output contains no traceback, fatal shell error, or unresolved
  prerequisite

### Base Dogfood Smoke Test

Run:

```bash
basectl projects list
basectl check
basectl doctor
basectl check base
basectl doctor base
basectl logs --path
basectl logs --command setup
basectl test base
basectl demo base -- --non-interactive
basectl activate base
# exit the activated shell
```

Accept the smoke test when:

- `basectl projects list` includes `base`
- Base and project checks exit zero
- doctor reports no Base or project error findings
- logs are readable without a traceback
- `basectl test base` completes the dogfood test contract
- `basectl demo base -- --non-interactive` exits zero
- activation opens a Base runtime shell with `BASE_PROJECT=base`; exiting that
  shell returns to the caller cleanly

## Follow-Up Issues

Open a focused issue when a run discovers one of these gaps:

- a manual-only checklist step that should become hermetic automation
- a repeated setup, check, doctor, log, test, demo, or activation failure
- an expected output that is ambiguous or too path-specific to validate
  consistently
- a CI failure that does not map to one checklist step
- a platform-specific result, such as an Apple Silicon and Intel difference,
  that needs separate testing

Each follow-up issue should name the install route, the failing command, the
actual result, the expected result, and whether the next fix is product code,
test coverage, release automation, or documentation.
