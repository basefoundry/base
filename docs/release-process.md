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
  Base releases, plus the Homebrew bottle artifacts for supported macOS hosts.

The Homebrew tap update happens after the Base tag and GitHub Release exist.
The formula points at a versioned tag archive and records that archive's
`sha256`, so the archive must be available before the formula can be updated and
validated. Supported macOS installs should use Homebrew bottles; source builds
remain a fallback for unsupported hosts or explicit source-build validation.

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

The inspection commands are read-only:

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

Complete these steps in `codeforester/homebrew-base` after the Base tag exists:

1. Create a Homebrew tap update issue or PR for the new Base version.
2. Create a tap release branch. Do not run the bottle workflow from `master`;
   it pushes the generated bottle stanza back to the branch that triggered it.
3. Update `Formula/base.rb`:
   - `url` to the new Base tag archive
   - `sha256` to the checksum of that archive
   - `version` to the new Base version
4. Compute the archive checksum from the published tag:

   ```bash
   curl -fsSL https://github.com/codeforester/base/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256
   ```

5. Validate the formula source-build path from the tap repository when the host
   can run Homebrew source builds:

   ```bash
   brew install --build-from-source Formula/base.rb
   brew test codeforester/base
   brew audit --new --formula Formula/base.rb
   ```

6. Run the `Build Base Bottles` GitHub Actions workflow from the tap release
   branch. The workflow builds bottles on supported macOS runners, uploads
   bottle tarballs to the tap GitHub Release named `base-vX.Y.Z`, merges the
   generated bottle JSON into `Formula/base.rb`, and pushes the bottle stanza
   back to the branch.
7. Confirm the tap PR includes a `bottle do` block for supported macOS targets
   before merging. The bottle `root_url` should point at the tap release created
   by the workflow.
8. Open or update the tap PR, wait for checks, and merge it.
9. Smoke-test the consumer bottle and upgrade paths:

   ```bash
   brew update
   brew install --force-bottle codeforester/base/base
   brew test codeforester/base
   brew upgrade codeforester/base/base
   ```

   Use `brew reinstall --force-bottle codeforester/base/base` when Base is
   already installed on the validation host.
10. Before 1.0.0, complete the
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
