# Guarded Release Publish Design

## Goal

Add `basectl release publish` so Base can create an annotated Git tag and GitHub
Release from manifest-owned release metadata, while preserving the existing
release ceremony and its safety checks.

## Scope

This slice extends the release assistant from read-only inspection to guarded
GitHub publishing:

- `basectl release publish --version X.Y.Z --dry-run`
- `basectl release publish --version X.Y.Z`
- `basectl release publish --version X.Y.Z --yes`

The command reuses the same manifest, version file, changelog, Git worktree,
GitHub CLI, and tag readiness checks used by `release check`. It also verifies
that a GitHub Release for the tag does not already exist before publishing.

## Publish Flow

`publish` resolves the release context from `base_manifest.yaml`, extracts the
matching changelog section, renders the configured GitHub release title, and
then performs these guarded steps:

1. Refuse to continue when release readiness has errors or warnings.
2. Refuse to continue when a GitHub Release already exists for the tag.
3. In `--dry-run`, print the planned tag, push, and GitHub Release actions
   without mutating the repository or network state.
4. Without `--yes`, require an interactive confirmation prompt.
5. Create an annotated tag with `git tag -a <tag> -m "Release <tag>"`.
6. Push the tag with `git push origin <tag>`.
7. Create the GitHub Release with `gh release create <tag> --repo <owner/repo>
   --title <title> --notes-file <tempfile>`.
8. Print tag and release URLs plus any Homebrew handoff required by the
   manifest.

The command intentionally has no broad force or recovery mode. Existing tags,
existing releases, dirty worktrees, mismatched version files, and missing
changelog sections remain stop conditions.

## Homebrew Handoff

`release.homebrew` remains declarative metadata, not automation. Both `plan` and
successful `publish` output show the downstream tap work:

- tap repository
- formula path
- package name
- tag archive URL
- SHA256 command
- formula validation commands
- upgrade smoke commands

For `1.0.0` release candidates or the final `1.0.0`, the handoff also reminds
the operator to complete the Homebrew upgrade rehearsal tracked by #526.

## Non-Goals

- Do not update, clone, commit, or push the Homebrew tap.
- Do not create release-prep PRs.
- Do not support non-GitHub hosting in this slice.
- Do not add a force mode for replacing tags or releases.

## Testing

Python unit tests cover dry-run command assembly, non-interactive confirmation
guarding, successful publish with GitHub calls stubbed, readiness guard
failures, existing-release guard failures, and Homebrew handoff rendering for
GitHub-only and Homebrew-required manifests.

BATS tests cover the Bash dispatch and help/completion surface for `publish`.
