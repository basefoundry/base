# Upgrading Base

This is the upgrade contract for Homebrew, mutable source checkouts, and stable
tagged source checkouts. It describes current main. The `update --release`
option and Homebrew reconciliation when the formula version is unchanged were
added after v1.10.5; they must not be assumed available in that release. Check
`basectl update --help` on the executable you are actually running. Older
versions can use the explicit setup and pinned-checkout paths below.

## Choose The Installation You Intend To Upgrade

```bash
command -v basectl
type -a basectl
basectl version
```

Homebrew and source copies can coexist. `basectl update` targets the Base
installation containing that executable, not every Base copy on the machine.
Use an explicit executable path when the shell selects the wrong installation.
Homebrew usually exposes `/opt/homebrew/bin/basectl` on Apple Silicon or
`/usr/local/bin/basectl` on Intel macOS; a source checkout exposes its own
`bin/basectl`. See [Homebrew and source coexistence](../FAQ.md#homebrew-and-source-coexistence).

## Upgrade Matrix

| Installation / operation | Command | Setup behavior | Verification |
| --- | --- | --- | --- |
| Homebrew-managed Base | `basectl update` | Runs `brew upgrade basefoundry/base/base`, then setup through the newly linked executable with inherited Base/project variables cleared. Current main reconciles even when the formula version is unchanged. | Confirm active executable and version, then `basectl check base --verify-project-runtime`. |
| Mutable Base source checkout on its default branch | `basectl update` | Updates the checkout through Git and runs `basectl setup base` only when the revision changes. | Version and explicit runtime check; source contributors also run the Base test contract after trust review. |
| Stable detached Base source checkout, with `--release` support | `basectl update --release <tag>` | Moves to a later stable tag verified against `origin`, stays detached, then runs setup. Repeating the current tag reconciles setup without moving the checkout. | Confirm exact tag/commit and version, explicit runtime check, then appropriate tests after trust review. |
| Direct Homebrew operation | `brew upgrade basefoundry/base/base` followed by explicit setup | Package-manager upgrade alone does not reconcile the persistent Base environment. Use the sequence below. | Verify using the newly linked Homebrew executable. |
| Direct Git operation | Reviewed Git update followed by `basectl setup base` from that checkout | Git does not reconcile the environment. Run setup even if a subsequent `basectl update` says the revision is already current. | Confirm ref/version, runtime readiness, and applicable tests. |

`basectl update` without a project means `basectl update base`, including when
you are inside a consumer repository. `basectl update example` updates that
consumer project's default-branch checkout and runs its setup only if the
revision changes. It does not upgrade the Base installation. `--release` is
only for the Base source checkout, not Homebrew or consumer projects.

`basectl setup [project]` reconciles requirements at the already selected
revision; it does not select a newer release. `basectl update-profile` refreshes
shell integration; it is not an upgrade operation. Refresh the profile when
the installation path or managed shell configuration changes, then start a
fresh shell. An ordinary same-path upgrade does not require a profile rewrite.

## Homebrew

Preview, then apply through the Homebrew-managed executable:

```bash
basectl update --dry-run
basectl update
```

The preview does not run the package upgrade or setup. Apply performs both, so
an unchanged formula version can still repair missing or stale pinned runtime
requirements. If Homebrew reports a tap-trust requirement, review and run
`brew trust basefoundry/base`, then retry.

For a direct `brew upgrade`, or recovery after an older updater skipped setup,
use the newly linked executable rather than an old Cellar path:

```bash
brew upgrade basefoundry/base/base
env \
  -u BASE_HOME -u BASE_BIN_DIR -u BASE_CLI_DIR -u BASE_BASH_DIR \
  -u BASE_BASH_COMMANDS_DIR -u BASE_LIB_DIR -u BASE_BASH_LIB_DIR \
  -u BASE_SHELL_DIR -u BASE_OS -u BASE_HOST -u BASE_SHELL \
  -u BASE_PLATFORM_TOOLS_HOME -u BASE_PLATFORM_TOOLS_BIN_DIR \
  -u BASE_PROJECT -u BASE_PROJECT_ROOT -u BASE_PROJECT_MANIFEST \
  -u BASE_PROJECT_VENV_DIR \
  "$(brew --prefix base)/libexec/bin/basectl" setup
```

Stop if the upgrade fails and resolve Homebrew's reported problem before
continuing. See the [Homebrew Upgrade Rehearsal](homebrew-upgrade-rehearsal.md)
for release-validation evidence and preserved-state checks.

## Mutable Source Checkouts

Ordinary `basectl update` requires the selected repository's default branch
and clean tracked files. It leaves unrelated untracked files to Git's normal
overwrite protection. It does not switch away from a feature branch or
resolve local changes on your behalf.

```bash
~/work/base/bin/basectl update --dry-run
~/work/base/bin/basectl update
```

If Git changes the checkout but setup fails, the checkout remains updated.
Resolve the setup failure and rerun `basectl setup base`; another ordinary
update can skip setup because the revision is already current. Local
development validation uses [Contributor Setup](../CONTRIBUTING.md#contributor-setup)
and [Testing](testing.md), including the configured provider checkouts.

## Stable Tagged Source Checkouts

Use an explicitly reviewed published `vMAJOR.MINOR.PATCH` release tag in place
of `<tag>`:

```bash
~/work/base/bin/basectl update --release <tag> --dry-run
~/work/base/bin/basectl update --release <tag>
```

This path requires a clean tracked checkout detached at an exact stable tag.
A different target must be a later stable version; it does not follow `main`,
accept prerelease tags, or provide an automatic downgrade. Apply verifies the
target tag's commit against `origin`, refuses a conflicting local tag, fetches
the target when necessary, and refuses untracked or ignored paths overlapping
files changed by the target release. Unrelated local files are preserved.

The dry run queries the remote tag without fetching, changing refs, or running
setup. The real upgrade performs the additional local-path collision check.
A remote-tag match establishes the checkout target; it is not a replacement
for reviewing the published release and its immutable BOM evidence.

After a ref change, setup failure leaves the checkout at the target release.
Correct the error and run `basectl setup base`, or repeat the same-tag command
to reconcile the current environment. The updater does not roll back the ref
or erase persistent user configuration and trust state. Changed manifest or
test-requirement digests can invalidate approval, so review trust again.

### Older Versions Without `--release`

An older stable install must not be moved to `main` merely to obtain the new
upgrade option. Use the [Stable Source Install Recipe](bootstrap.md#stable-source-install-recipe)
with the desired published release ref. A separate pinned checkout is also a
way to preserve the original checkout while selecting the new release:

```bash
# Replace vX.Y.Z with the reviewed published target release.
TARGET_RELEASE=vX.Y.Z
git clone --branch "$TARGET_RELEASE" --single-branch \
  https://github.com/basefoundry/base.git "$HOME/work/base-$TARGET_RELEASE"
```

After cloning succeeds, confirm the tag and version in the new checkout, run
its `bin/basectl setup`, and verify readiness. Run that checkout's
`bin/basectl update-profile` only when choosing it as the shell's active Base,
then open a fresh shell and confirm `command -v basectl` again. The checkouts
share the user's managed Base environment; keeping an older checkout does not
create an isolated runtime or an automatic rollback guarantee.

## Readiness, Trust, And Recovery

After selecting the intended executable and reviewing its runtime inputs:

```bash
basectl version
basectl check base --verify-project-runtime
basectl trust status base
```

Default `check` performs static inspection; package readiness can remain
unverified. `--verify-project-runtime` explicitly permits executing runtime and
tool probes. It does not repair state or grant manifest-command approval.
If trust status reports changed manifest or declared test requirements, review
the new content and use the exact digest-bearing approval command it prints
before running tests. See [Manifest Command Trust](manifest-command-trust.md).

For source contributor validation, run `basectl test base` with the documented
developer prerequisites/provider checkouts. For consumer readiness, check the
consumer project and run its declared test contract after approving its own
manifest. Successful Base upgrade does not prove every consumer project is
ready, and upgrading Base does not implicitly update all consumer repositories.

| Failure | Recovery |
| --- | --- |
| Dirty tracked checkout | Save or commit the work deliberately, then retry. Do not discard it to satisfy the updater. |
| Mutable checkout on a non-default branch | Finish the branch's workflow and select the intended default-branch checkout. |
| Detached checkout without a stable exact tag | Identify its provenance; use a reviewed stable checkout or an intentional mutable default-branch checkout. |
| Target tag missing, conflicting, or remote unavailable | Check the intended remote/release and resolve the discrepancy; do not force-replace a tag. |
| Stable-upgrade local-path collision | Preserve and move the conflicting untracked/ignored content, then retry. |
| Setup failed after Git/Homebrew changed the installation | Keep the reported revision, fix the underlying dependency/configuration problem, and rerun setup through the selected executable. |
| Mixed Homebrew/source shell state | Use an explicit executable, refresh the intended profile when necessary, and verify in a fresh shell. |
