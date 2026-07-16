# Release Process

Base releases are explicit release ceremonies, not automatic side effects of
ordinary pull requests.

Use this checklist when preparing and publishing a new Base release such as
`0.3.1` or `0.4.0`.

## Ownership

The release spans two repositories:

- `basefoundry/base` owns Base source, release notes, `VERSION`, Git tags, and
  GitHub Releases.
- `basefoundry/homebrew-base` owns the Homebrew formula that installs published
  Base releases, plus the Homebrew bottle artifacts for supported macOS hosts.

The Homebrew tap update happens after the Base tag and GitHub Release exist.
The formula points at a versioned tag archive and records that archive's
`sha256`, so the archive must be available before the formula can be updated and
validated. Supported macOS installs should use Homebrew bottles; source builds
remain a fallback for unsupported hosts or explicit source-build validation.
Base's current supported macOS floor is macOS 14 Sonoma. Keep Homebrew bottle
workflows, formula validation, and Base's macOS CI floor aligned with that
support contract until the Compatibility section in the top-level README is
changed intentionally.

## Version Policy

Do not update `VERSION` on every merged pull request.

`VERSION` records the latest published Base release. Ordinary feature, fix,
documentation, and maintenance PRs leave it unchanged. A release-prep PR updates
`VERSION` once the next release number has been chosen.

Keep upcoming changes under the `Unreleased` section in `CHANGELOG.md` until a
release-prep PR moves them into a dated release section.

## Release Assistant

Base-managed repositories can declare a `release:` section in
`base_manifest.yaml` with the version file, changelog, tag prefix, GitHub
repository, GitHub Release title, and optional Homebrew handoff metadata.
For an existing repository, `basectl repo configure --release --repo
<owner/name>` adds the generic contract and a missing release guide without
overwriting an existing declaration or guide. Use `basectl repo check --release`
to verify adoption.

The inspection commands are read-only:

```bash
basectl release check --version X.Y.Z
basectl release check --version X.Y.Z --format json
basectl release plan --version X.Y.Z
basectl release notes --version X.Y.Z
```

Use `check` before publishing to validate the version file, changelog section,
Git worktree cleanliness, current branch, GitHub CLI authentication, and local
and remote tag availability. Use `plan` to print the GitHub release target and
downstream handoff requirements. Use `notes` to print the changelog body
intended for the GitHub Release.
The JSON check uses the stable shared v1 envelope documented in
[Inspection JSON](inspection-json.md); readiness blockers stay in `data.findings`
with `error: null`.

Publishing is guarded:

```bash
basectl release publish --version X.Y.Z --dry-run
basectl release publish --version X.Y.Z
basectl release publish --version X.Y.Z --yes
```

`publish` reuses the release checks, refuses existing tags or GitHub Releases,
creates an annotated tag, pushes the tag, and creates the GitHub Release from
the changelog section. It does not update the Homebrew tap; it prints the tap
handoff checklist when `release.homebrew` is declared.

## Base Release Checklist

Complete these steps in `basefoundry/base`:

1. Choose the release version and create or use a GitHub issue for the release
   artifact work.
2. Create a release-prep branch and worktree from `origin/main`.
3. Update release metadata:
   - `VERSION`
   - README version badge
   - README `Current Status` section current-release prose
   - `.ai-context/STATUS.md` `Current Release` section
   - `CHANGELOG.md`, moving relevant `Unreleased` entries into the new release
     section
4. Validate the release-prep PR:

   ```bash
   git diff --check
   bin/base-test
   ```

5. Merge the release-prep PR into `main`.
6. Sync local `main`.
7. Dry-run the guarded publish command:

   ```bash
   basectl release publish --version X.Y.Z --dry-run
   ```

8. Publish the GitHub-side release artifacts:

   ```bash
   basectl release publish --version X.Y.Z
   ```

   Use `--yes` only when running from a trusted non-interactive release shell.

9. Confirm the release tag and GitHub Release are visible on GitHub.

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
