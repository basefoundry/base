# Release Process

Base releases are explicit release ceremonies, not automatic side effects of
ordinary pull requests.

Use this checklist when preparing and publishing a new Base release such as
`1.10.2` or `1.11.0`.

## Ownership

The release spans two repositories:

- `basefoundry/base` owns Base source, release notes, `VERSION`, Git tags, and
  GitHub Releases.
- `basefoundry/homebrew-base` owns the Homebrew formula that installs published
  Base releases, plus the Homebrew bottle artifacts for supported macOS hosts.

Base also owns the cross-repository release BOM. Releases of `base-cli`,
`base-bash-libs`, or `base-demo` remain independently versioned and do not
force a Base release. A Base release chooses the exact compatible component
tags it will support and records those tags, commits, contract versions, and
Ubuntu 24.04/macOS 14 support-platform validation evidence in its BOM. The
macOS 14 evidence is executed on GitHub's pinned macOS 15 runner because the
macOS 14 hosted image is being retired. A later component release is eligible for a
later Base BOM after the required compatibility checks pass.
See the [Ecosystem Platform, License, and Release Policy](ecosystem-policy.md)
for the shared platform boundaries, license history, provider precedence, and
published-artifact immutability rule.

Before choosing a release date, classify the change with the [Release
Stabilization and Independent Review Policy](release-stabilization-policy.md).
That policy determines whether a patch can proceed directly, whether a
candidate or bake window is required, and how an unavailable independent
reviewer is recorded. `basectl release check` remains the mechanical gate; the
release issue records the policy decision and evidence that repository state
cannot prove by itself.

The Homebrew tap update happens after the Base tag and GitHub Release exist.
The formula points at a versioned tag archive and records that archive's
`sha256`, so the archive must be available before the formula can be updated and
validated. Supported macOS installs should use Homebrew bottles; source builds
remain a fallback for unsupported hosts or explicit source-build validation.
Base's current supported macOS floor is macOS 14 Sonoma. Keep Homebrew bottle
workflows, formula validation, and Base's macOS CI floor aligned with that
support contract; hosted CI currently exercises it on the pinned macOS 15
runner. Do not treat the runner image as a support-floor change until the
Compatibility section in the top-level README is changed intentionally.

## Version Policy

The latest published Base release is `1.10.5`. The release-prep PR changes the
authoritative version and every configured public version surface together;
`tools/version_consistency_check.py` blocks publication when one is stale.

Base keeps two related version identities during development:

- `VERSION` records the latest published Base release. Ordinary feature, fix,
  documentation, and maintenance PRs leave it unchanged.
- `DEVELOPMENT_VERSION` records the numeric next development line. An untagged
  Git checkout reports it as `DEVELOPMENT_VERSION-dev+g<short-sha>` and appends
  `.dirty` when the checkout has local changes.

A clean exact `vX.Y.Z` checkout and a packaged install report `VERSION` without
a development suffix. A dirty checkout, including one based on a release tag,
reports the development identity with its revision and `.dirty`. This keeps a
published release such as `1.10.2` distinct from mutable `main` work targeting
`1.11.0`.

Stable consumer installs must use Homebrew or an explicit release tag. Source
checkout and `main` installs are contributor or dogfood paths and must name the
branch or ref intentionally. Do not make a mutable default branch the implicit
stable consumer input.

At release preparation time, update `VERSION` to the clean release number and
run the release checks against that exact number. Do not put a development
suffix or Git revision in a published tag. After the release, update
`DEVELOPMENT_VERSION` to the next development line on `main`.

Keep upcoming changes under the `Unreleased` section in `CHANGELOG.md` until a
release-prep PR moves them into a dated release section.

## Release Assistant

Base-managed repositories can declare a `release:` section in
`base_manifest.yaml` with the version file, changelog, tag prefix, GitHub
repository, GitHub Release title, optional BOM enforcement, and optional
Homebrew handoff metadata. Set `release.bom.required: true` when the release
must use the governed cross-repository BOM path. When enabled, both
`release check` and `release publish` require the exact BOM artifact through
`--bom`.
For an existing repository, `basectl repo configure --release --repo
<owner/name>` adds the generic contract and a missing release guide without
overwriting an existing declaration or guide. Use `basectl repo check --release`
to verify adoption.

The inspection commands are read-only:

```bash
basectl release check --version X.Y.Z
basectl release check --version X.Y.Z --bom path/to/release-bom.json
basectl release check --version X.Y.Z --format json
basectl release plan --version X.Y.Z
basectl release notes --version X.Y.Z
```

For a high-impact change, run the release check at the beginning and end of
the candidate window, and attach both outputs to the release issue. The check
does not replace the policy record: it verifies reproducible repository and
artifact state, while the release issue records the bake interval, independent
reviewer or waiver, and unresolved-risk decisions.

Use `check` before publishing to validate the version file, changelog section,
Git worktree cleanliness, GitHub CLI authentication, and local and remote tag
availability. It also requires every `origin` fetch and push URL to identify
`release.github.repository`, resolves the live remote default branch through
`git ls-remote --symref`, and requires the checked-out branch and full local
`HEAD` SHA to match that current remote commit exactly. A stale local
`origin/<branch>` tracking ref is not accepted as release evidence. Use `plan`
to print the GitHub release target and downstream handoff requirements. Use
`notes` to print the changelog body intended for the GitHub Release.
The JSON check uses the stable shared v1 envelope documented in
[Inspection JSON](inspection-json.md); readiness blockers stay in `data.findings`
with `error: null`.

Publishing is guarded:

```bash
basectl release publish --version X.Y.Z --bom path/to/release-bom.json --dry-run
basectl release publish --version X.Y.Z --bom path/to/release-bom.json --yes
```

For first-time publication, `publish` reuses the release checks and rechecks
the repository, branch, and full commit SHA immediately before its first
mutation. It creates an annotated
tag, verifies the local peeled SHA, pushes the tag, verifies the remote peeled
SHA, and creates a mutable GitHub draft through the REST API. It then verifies
GitHub's annotated tag object, uploads only missing assets, downloads each
required asset again, and compares its bytes with the reviewed staged input.
Only after those checks pass does it publish the draft, making the release
immutable. A rerun safely resumes an existing draft and never overwrites an
existing asset. Bounded rate-limit retries and REST readback make interrupted
creation, upload, and publication recoverable without creating a second
release. This ordering is required for immutable releases: never create an
empty immutable release and attempt to upload the BOM afterward. It does not
update the Homebrew tap; it prints the tap handoff checklist when
`release.homebrew` is declared.

### Recovering A Tagged Release After Main Advances

Publication has a narrow recovery path for a release whose annotated tag was
already pushed before publication tooling advanced the default branch. This
is the accepted exception from [#2551](https://github.com/basefoundry/base/issues/2551),
implemented in [#2552](https://github.com/basefoundry/base/pull/2552); it does
not permit first-time tagging from an arbitrary historical checkout.

| State | Publication authority and action |
| --- | --- |
| No readiness blockers, no existing release/tag conflict | Use the current remote default-branch commit and the normal guarded publication sequence. |
| Tag already exists, main advanced, GitHub release absent or draft | Resume only when the original canonical, sidecar-verified BOM names the same commit as both local and remote annotated tags. Reuse that commit and those tags. |
| GitHub release is already published | Recovery is not accepted; do not replace an immutable release. |
| Any other readiness failure or mismatched/unverifiable BOM/tag | Stop and resolve the failure; do not retag or regenerate evidence to bypass it. |

Recovery accepts readiness blockers only in the `bom`, `release_commit`,
`local_tag`, and `remote_tag` categories, and then independently validates the
original BOM and matching annotated tags. All other readiness requirements,
including repository identity, branch, cleanliness, version, and changelog,
still apply. `release check` may therefore report the advanced-HEAD/tag
blockers even when `release publish` can safely resume this specific state.

Retain the original reviewed BOM and checksum sidecar. From the clean tooling
checkout, preview and then resume the same version:

```bash
basectl release publish --version X.Y.Z --bom path/to/original-release-bom.json --dry-run
basectl release publish --version X.Y.Z --bom path/to/original-release-bom.json --yes
```

The preview identifies the reviewed commit and that the verified annotated tag
will be reused. Recovery does not create or move that tag. The remaining draft,
asset-upload, byte-readback, and immutable-publication checks are unchanged:
upload only missing assets and reject conflicting existing bytes. Preserve the
reviewed release notes in the version's changelog section; recovery is not an
opportunity to change the release payload. If the prerequisites do not hold,
leave the existing tag/draft intact and investigate the reported failure.

## Downstream Version-Bump Automation

The `Downstream Version Bumps` workflow checks published `base`, `base-cli`,
and `base-bash-libs` releases and opens an issue-backed pull request in the
known downstream consumer, `base-demo`. Base releases trigger the workflow
immediately; an hourly schedule covers independently published component
releases, and `repository_dispatch` plus `workflow_dispatch` are available for
an explicit release notification or replay.

Each run resolves the published `vX.Y.Z` tag to its full commit. Base bumps
also resolve and record the `install.sh` SHA-256. The generated PR updates the
downstream source, CI, documentation, and test assertions as one fail-closed
change; a `base-cli` bump refreshes `uv.lock`. A marker containing the
component, version, and commit is deduplicated across downstream issues and
pull requests. If a run fails after issue creation, it comments the failure on
the preserved issue; a retry reuses that issue and repairs the partial state.
The workflow never merges or force-updates a downstream branch; the downstream
checks and normal review remain the merge gate.

Cross-repository writes require the explicitly configured
`BASE_DOWNSTREAM_TOKEN` Actions secret. It must be limited to the known
downstream repositories with permission to create issues, branches, and pull
requests. The workflow fails closed when the secret is absent and never uses
the Base repository's read-only `GITHUB_TOKEN` as an implicit substitute.

The automation covers released component pins only. It does not make a
component release force a new Base release, update Homebrew, or treat a
mutable source checkout as release evidence; those remain governed by the
[ecosystem policy](ecosystem-policy.md) and the Base-owned BOM.

## Base Release Checklist

Complete these steps in `basefoundry/base`:

1. Choose the release version and create or use a GitHub issue for the release
   artifact work.
2. Classify the release with [the stabilization policy](release-stabilization-policy.md).
   Record the candidate/bake window and independent review or waiver in the
   release issue before publication work begins.
3. Create a release-prep branch and worktree from `origin/main`.
4. Update release metadata:
   - `VERSION`
   - README version badge
   - README `Current Status` section current-release prose
   - `.ai-context/STATUS.md` `Current Release` section
   - `CHANGELOG.md`, moving relevant `Unreleased` entries into the new release
     section
   - maintained product and context docs: reconcile `Last reviewed`, `Base era
     reviewed`, and `Current release` claims with `VERSION` and `CHANGELOG.md`
5. Validate the release-prep PR:

   ```bash
   git diff --check
   bin/base-test
   ```

6. Merge the release-prep PR into `main`.
7. Sync local `main` and confirm `HEAD` exactly matches the current live
   `origin/main`. Do not publish from a feature branch, detached checkout,
   ahead/behind/diverged branch, stale remote-tracking ref, or a checkout whose
   `origin` does not match `release.github.repository`.
8. Dispatch the `Ecosystem Release BOM` workflow at the exact reviewed release
   commit, wait for both required platform jobs to pass, and download the
   `base-release-bom-X.Y.Z` artifact. Supply the exact component versions and
   refs selected for this release:

   ```bash
   gh workflow run ecosystem-release-bom.yml \
     --ref main \
     -f base_version=X.Y.Z \
     -f base_ref="$(git rev-parse HEAD)" \
     -f base_cli_version=<version> -f base_cli_ref=<ref> \
     -f base_bash_libs_version=<version> -f base_bash_libs_ref=<ref> \
     -f base_demo_version=<version> -f base_demo_ref=<ref>
   gh run download <run-id> --name base-release-bom-X.Y.Z \
     --dir /private/tmp/base-release-bom-X.Y.Z
   ```

9. Dry-run the guarded publish command with the downloaded BOM:

   ```bash
   basectl release publish --version X.Y.Z \
     --bom /private/tmp/base-release-bom-X.Y.Z/release-bom.json --dry-run
   ```

10. Publish the GitHub-side release artifacts with the same immutable BOM:

   ```bash
   basectl release publish --version X.Y.Z \
     --bom /private/tmp/base-release-bom-X.Y.Z/release-bom.json
   ```

   Use `--yes` only when running from a trusted non-interactive release shell.

11. Confirm the release tag, GitHub Release, and `release-bom.json` plus
    `release-bom.sha256` assets are visible on GitHub.

## Homebrew Tap And Bottle Checklist

Complete these steps in `basefoundry/homebrew-base` after the Base tag exists:

1. Create a Homebrew tap update issue or PR for the new Base version.
2. Create a tap release branch. Do not run the bottle workflow from `main`;
   it pushes the generated bottle stanza back to the branch that triggered it.
3. Update `Formula/base.rb`:
   - `url` to the new Base tag archive
   - `sha256` to the checksum of that archive
   - `version` to the new Base version
4. Compute the archive checksum from the published tag:

   ```bash
   curl -fsSL https://github.com/basefoundry/base/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256
   ```

5. Validate the formula source-build path from the tap repository when the host
   can run Homebrew source builds:

   ```bash
   brew install --build-from-source Formula/base.rb
   brew test basefoundry/base/base
   brew audit --new --formula basefoundry/base/base
   ```

6. Confirm the tap-owned `base-bash-libs` formula remains Homebrew/core-ready.
   The formula should keep its stable release archive, SPDX license metadata,
   `bash` dependency, test block, and `base-bash-libs` package name so a future
   `basefoundry` Homebrew/core formula can depend on it directly:

   ```bash
   brew test basefoundry/base/base-bash-libs
   brew audit --new --formula basefoundry/base/base-bash-libs
   ```

7. Run the `Build Base Bottles` GitHub Actions workflow from the tap release
   branch. The workflow builds bottles on supported macOS runners, uploads
   bottle tarballs to the tap GitHub Release named `base-vX.Y.Z`, merges the
   generated bottle JSON into `Formula/base.rb`, and pushes the bottle stanza
   back to the branch.
8. Confirm the tap PR includes a `bottle do` block for supported macOS targets
   before merging. The bottle `root_url` should point at the tap release created
   by the workflow.
9. Open or update the tap PR, wait for checks, and merge it.
10. Smoke-test the consumer bottle and upgrade paths:

   ```bash
   brew update
   brew trust basefoundry/base
   brew install --force-bottle basefoundry/base/base
   brew test basefoundry/base/base
   brew upgrade --no-ask basefoundry/base/base
   ```

   Use `brew reinstall --force-bottle basefoundry/base/base` when Base is
   already installed on the validation host.
11. Before 1.0.0, complete the
   [Homebrew Upgrade Rehearsal](homebrew-upgrade-rehearsal.md) against a
   release candidate or equivalent test formula. Record the exact commands,
   host facts, pre-upgrade state, post-upgrade checks, and any follow-up issues.
   Do not close the rehearsal issue until
   `brew upgrade --no-ask basefoundry/base/base` and the post-upgrade Base
   project checks pass on a qualified host.

### Common Failures And Recovery

If Homebrew tap or bottle validation fails, check the
[Homebrew Upgrade Rehearsal](homebrew-upgrade-rehearsal.md) for historical run
records before retrying. Known recovery patterns include:

- Outdated Command Line Tools: stop the release host validation, update Xcode
  Command Line Tools until `brew doctor` no longer blocks package installation,
  then rerun the Homebrew checklist from the failed step.
- Stale versioned Cellar paths after upgrade: clear the shell command cache with
  `hash -r`, rerun `/usr/local/bin/basectl update-profile` or
  `/opt/homebrew/bin/basectl update-profile` with inherited `BASE_*` variables
  unset, then start a fresh login shell before rechecking `basectl version`.
- Homebrew source-build sandbox path failures: do not treat user-directory
  cleanup as the release fix. Prefer bottle publishing for supported macOS
  hosts, rerun the `Build Base Bottles` workflow, and retry consumer validation
  with `brew install --force-bottle basefoundry/base/base`.

## Cleanup

After the Base release PR and Homebrew tap PR are merged, clean up their
worktrees and branches. Keep the release issue or linked issue comments updated
with the Base release URL and Homebrew tap PR URL so the release record has both
halves of the ceremony.
