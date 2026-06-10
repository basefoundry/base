# Release Process

Base releases are explicit release ceremonies, not automatic side effects of
ordinary pull requests.

Use this checklist when preparing and publishing a new Base release such as
`0.3.1` or `0.4.0`.

## Ownership

The release spans two repositories:

- `codeforester/base` owns Base source, release notes, `VERSION`, Git tags, and
  GitHub Releases.
- `codeforester/homebrew-base` owns the Homebrew formula that installs published
  Base releases.

The Homebrew tap update happens after the Base tag and GitHub Release exist.
The formula points at a versioned tag archive and records that archive's
`sha256`, so the archive must be available before the formula can be updated and
validated.

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

The first `basectl release` implementation is read-only:

```bash
basectl release check --version X.Y.Z
basectl release plan --version X.Y.Z
basectl release notes --version X.Y.Z
```

Use `check` before publishing to validate the version file, changelog section,
Git worktree cleanliness, current branch, GitHub CLI authentication, and local
and remote tag availability. Use `plan` to print the GitHub release target and
downstream handoff requirements. Use `notes` to print the changelog body
intended for the GitHub Release.

This command does not create tags, publish GitHub Releases, or update the
Homebrew tap yet. The checklist below remains authoritative for those mutation
steps until guarded publish behavior is implemented.

## Base Release Checklist

Complete these steps in `codeforester/base`:

1. Choose the release version and create or use a GitHub issue for the release
   artifact work.
2. Create a release-prep branch and worktree from `origin/master`.
3. Update release metadata:
   - `VERSION`
   - README version badge and current-release text
   - `CHANGELOG.md`, moving relevant `Unreleased` entries into the new release
     section
4. Validate the release-prep PR:

   ```bash
   git diff --check
   bin/base-test
   ```

5. Merge the release-prep PR into `master`.
6. Sync local `master`.
7. Create an annotated tag from the merged release commit:

   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

8. Publish the GitHub Release from the corresponding changelog section.
9. Confirm the release tag and GitHub Release are visible on GitHub.

## Homebrew Tap Checklist

Complete these steps in `codeforester/homebrew-base` after the Base tag exists:

1. Create a Homebrew tap update issue or PR for the new Base version.
2. Update `Formula/base.rb`:
   - `url` to the new Base tag archive
   - `sha256` to the checksum of that archive
   - `version` to the new Base version
3. Compute the archive checksum from the published tag:

   ```bash
   curl -fsSL https://github.com/codeforester/base/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256
   ```

4. Validate the formula from the tap repository:

   ```bash
   brew install --build-from-source Formula/base.rb
   brew test codeforester/base
   brew audit --new --formula Formula/base.rb
   ```

5. Open and merge the tap PR.
6. Smoke-test the consumer upgrade path:

   ```bash
   brew update
   brew upgrade codeforester/base/base
   ```

7. Before 1.0.0, complete the
   [Homebrew Upgrade Rehearsal](homebrew-upgrade-rehearsal.md) against a
   release candidate or equivalent test formula. Record the exact commands,
   host facts, pre-upgrade state, post-upgrade checks, and any follow-up issues.
   Do not close the rehearsal issue until `brew upgrade codeforester/base/base`
   and the post-upgrade Base project checks pass on a qualified host.

## Cleanup

After the Base release PR and Homebrew tap PR are merged, clean up their
worktrees and branches. Keep the release issue or linked issue comments updated
with the Base release URL and Homebrew tap PR URL so the release record has both
halves of the ceremony.
