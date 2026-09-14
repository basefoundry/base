# Base Adopter Golden Path

Status: maintained adoption recipe
Last validated: 2026-09-14

This is the shortest supported path from installing Base to a verified project
pull request. It makes the important decisions visible in order:

```text
install -> prepare -> inspect -> trust -> validate -> hand off
```

The path is intentionally small. Advanced profiles, workspace fan-out,
environment exports, release checks, and IDE integrations come after the first
verified project change.

## Definition Of Done

An adopter has completed the path when all of the following are true:

- Base and its reusable Bash library are available from an intentional install
  route.
- `basectl check` and `basectl doctor` have no blocking findings.
- The project manifest has been reviewed, and command trust was granted only
  for the reviewed manifest digest.
- The project's declared validation command completes successfully.
- `basectl repo check .` passes for a repository using the Base baseline, or the
  project has recorded an equivalent repository validation command.
- The working tree passes `git diff --check`, and the issue-backed PR is opened
  from a canonical Base branch with hosted checks visible.

Warnings remain visible and actionable. They are not silently converted into a
green result; resolve them or record why they are outside the selected path.

## Choose The Install Route

Use one route per rehearsal. Do not let an existing Homebrew install silently
choose a different `basectl` than the one being validated.

### macOS source checkout

This is the recommended route for a new adopter evaluating the moving source
checkout or contributing to Base:

```bash
mkdir -p ~/work
cd ~/work
git clone --branch main https://github.com/basefoundry/base.git base
git clone https://github.com/basefoundry/base-bash-libs.git base-bash-libs
cd base

./bin/basectl setup --dry-run
./bin/basectl setup
./bin/basectl update-profile
exec "$SHELL" -l
```

Review the setup preview before applying it. `update-profile` is a separate,
explicit step because it changes user-owned shell startup files.

### macOS Homebrew

Use this route when Base should be consumed as a normal Homebrew package:

```bash
brew trust basefoundry/base
brew install basefoundry/base/base
basectl setup --dry-run
basectl setup
basectl update-profile
exec "$SHELL" -l
```

The reusable `base-bash-libs` package is still required by the source-checkout
test contract. A packaged consumer can use the installed package instead of a
source sibling when the package supplies the same library contract.

### Ubuntu/Debian source checkout

On Ubuntu/Debian, `bootstrap.sh` prints the manual source path rather than
running `sudo apt` from a piped script. Review that output, install the listed
prerequisites, clone Base and `base-bash-libs` under the native Linux
filesystem, and then run:

```bash
./bin/basectl setup --dry-run
./bin/basectl setup --yes
./bin/basectl check --ci base --format json
./bin/basectl doctor --ci base --format json
```

The supported Linux adopter boundary is the source-checkout runtime,
apt-backed setup, and CI-safe readiness/doctor path. Native Windows, non-
Debian Linux, and WSL distributions other than the supported Ubuntu/Debian
contract are outside this recipe. Full interactive `base-demo` setup,
activation, and demo expectations remain macOS-only today.

## Adopt An External-Style Project

The public `basefoundry/base-demo` repository is the reference project for
this walkthrough. A real adopter can substitute another Git repository that
contains a reviewed `base_manifest.yaml`.

From a workspace with no contributor worktrees, the guided path is:

```bash
cd ~/work
git clone https://github.com/basefoundry/base-demo.git base-demo
cd base-demo

~/work/base/bin/basectl onboard base-demo
```

`onboard` runs the existing check, setup, shell-profile, doctor, project
discovery, and read-only trust-status steps. It never grants manifest command
trust for the user. If the project requests IDE changes, review the exact plan
and pass `--allow-project-ide-mutations` only when those changes are intended.

For a scriptable or worktree-heavy rehearsal, use the explicit manifest and
current-directory forms below. They avoid ambiguous project-name discovery:

```bash
~/work/base/bin/basectl setup \
  --manifest "$PWD/base_manifest.yaml" --dry-run
~/work/base/bin/basectl setup \
  --manifest "$PWD/base_manifest.yaml"
~/work/base/bin/basectl check --ci \
  --manifest "$PWD/base_manifest.yaml" --format text
~/work/base/bin/basectl doctor --ci \
  --manifest "$PWD/base_manifest.yaml" --format text
~/work/base/bin/basectl repo check .
~/work/base/bin/basectl test --dry-run
~/work/base/bin/basectl run --list
```

The setup preview may list project-originated IDE mutations, package installs,
or runtime synchronization. Those are separate consent decisions. The
manifest and project commands remain project-owned code; inspect them before
execution.

## Review Trust, Then Validate

Do not approve a project manifest merely because the repository is familiar.
List the command surfaces first and approve the exact digest shown by Base:

```bash
~/work/base/bin/basectl trust status base-demo
~/work/base/bin/basectl run base-demo --list
~/work/base/bin/basectl build base-demo --list

# Copy the exact digest-bound command printed by trust status.
~/work/base/bin/basectl trust allow base-demo \
  --manifest-sha256 <reviewed-manifest-sha256>
```

After trust review, run the project contract. On macOS, the reference project
path is:

```bash
~/work/base/bin/basectl check base-demo --verify-project-runtime
~/work/base/bin/basectl doctor base-demo
~/work/base/bin/basectl test base-demo
~/work/base/bin/basectl demo base-demo -- --non-interactive
```

Use `basectl check --ci` and `basectl doctor --ci` on Ubuntu/Debian for the
readiness boundary documented above. If the project declares a Linux-safe test
command, run it from the project checkout after the CI-safe checks; do not
infer full macOS activation or demo parity from a green Linux readiness check.

## Handoff To A Verified PR

The PR is the final handoff record, not a replacement for local validation:

```bash
cd ~/work/base-demo
git status --short
git diff --check

~/work/base/bin/basectl gh issue readiness <issue-number> \
  --repo basefoundry/base-demo \
  --project-owner basefoundry --project-number 9 --format json
~/work/base/bin/basectl gh issue start <issue-number>

# Make the focused project change in the issue-backed worktree.
~/work/base/bin/basectl repo check .
~/work/base/bin/basectl check base-demo --verify-project-runtime
~/work/base/bin/basectl test base-demo
git diff --check
~/work/base/bin/basectl gh pr create
~/work/base/bin/basectl gh pr checks
```

`basectl gh issue start` creates the canonical
`<category>/<issue>-<YYYYMMDD>-<slug>` branch. `basectl gh pr create` validates
that branch, preserves the issue link, and hands the change to the repository's
hosted checks. Keep the PR scoped to the issue; use a follow-up issue for
unrelated findings.

## Recovery Without Private Maintainer Knowledge

| Symptom | Recovery |
| --- | --- |
| Base cannot find reusable Bash libraries | Clone `base-bash-libs` next to Base, or set `BASE_BASH_LIBS_DIR` to its `lib/bash` directory. |
| Duplicate project names appear | Run setup/check/doctor with `--manifest "$PWD/base_manifest.yaml"`; run `test` and `run --list` from the project root without a positional project name. |
| Trust is `not_allowed` | Re-run `trust status`, inspect `run --list`/`build --list`, then approve only the printed manifest digest. |
| Check or doctor reports a blocking finding | Run `doctor`, follow its `Fix:` command, and repeat the check. Keep the finding ID in the PR or adopter notes when the issue is intentionally deferred. |
| Setup wants shell or IDE changes | Keep the dry-run output, approve the shell-profile step explicitly, and use `--allow-project-ide-mutations` only for reviewed project-originated changes. |
| The PR branch is rejected | Start work with `basectl gh issue start <issue-number>` and keep one issue per branch/PR. |
| Ubuntu bootstrap proposes `sudo apt` | Use the printed manual commands, review them, then run `basectl setup --yes` only after the prerequisite plan is understood. |

For a clean exit after a rehearsal, use the verified removal path:

```bash
~/work/base/bin/basectl uninstall base-demo
~/work/base/bin/basectl uninstall --all
```

Removal previews by default. Use `--yes` only after reviewing the plan; an
applied `--all` removal runs its verification check automatically.

## Validation Record

The 2026-09-14 rehearsal used the current Base `main` source snapshot and the
`base-demo` reference checkout. The deterministic portions completed as
follows:

| Slice | Observed result |
| --- | --- |
| Source setup dry-run with an explicit manifest | Passed; the plan resolved `base-demo` and showed project-owned mutations without applying them. |
| `basectl projects list --workspace ~/work` | Passed; `base-demo` was discoverable. |
| `basectl repo check <base-demo>` | Passed; all 13 required repository baseline files were present. |
| `basectl trust status base-demo` | Passed as a read-only command; the fresh isolated state was `not_allowed`, as expected before approval. |
| `basectl test --dry-run` from the project root | Passed; it resolved the declared `mise run validate` command. |
| `basectl run --list` from the project root | Passed; it listed the manifest command surfaces without executing them. |
| `basectl doctor --ci --manifest ...` | Passed with no blocking findings after supplying the isolated test settings fixture; authentication and runtime-verification warnings remained visible. |

The full runtime verification was intentionally not reported as green: the
existing local `base-demo` environment had stale `base-cli==0.4.2` state while
the manifest requires `0.4.3`, and the isolated home did not contain the
project's mise-managed tools. The recovery is the documented setup/sync path,
followed by `check --verify-project-runtime` and the project test. This keeps
the recipe honest about the difference between deterministic Base-path smoke
coverage and a clean-machine adopter rehearsal.
