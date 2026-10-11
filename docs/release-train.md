# Cross-Repository Release Train

This document defines the release-train contract for Base and its independently
released companion repositories. It complements [Release Process](release-process.md):
that page explains how to publish Base, while this page defines how to decide
whether the whole release state is coherent enough to begin publication.

## Version and milestone policy

Base always uses a GitHub milestone named exactly `vX.Y.Z` for the Base release
version. The companion repositories should use the same convention for their
own versions:

- `base-demo`
- `base-cli`
- `base-bash-libs`
- `base-cli-demo`
- `base-bash-libs-demo`

The latest released version comes from the public GitHub Release/tag, never
from `main`, `VERSION` in an untagged checkout, or a README badge. When a new
issue is intentionally assigned to a future release and its milestone does not
exist, release-aware intake creates the next patch milestone by default. Raw
issue creation remains neutral; it must not silently assign a release.

## Release blockers

A release train is not ready when any of these are true:

1. The release milestone is missing or contains an open issue or pull request.
2. A required pull request has unresolved review threads, conflicts, red checks,
   or queued required checks.
3. A version, changelog, README, context file, lockfile, dependency pin, or
   workflow default disagrees with the selected release state.
4. A component is represented by a branch name, short SHA, mutable ref, draft,
   prerelease, or a GitHub Release that is not reported immutable.
5. The release BOM is missing, does not use full 40-character SHAs, omits a
   required platform, or does not validate on Ubuntu 24.04 and macOS 14.
6. Public release assets, checksums, package metadata, or hosted readback have
   not been verified after publication.

The release issue may be the final tracking item in the milestone while work is
underway. It must be closed, or explicitly moved to another milestone with an
evidence-backed explanation, before the final empty-milestone preflight.

## Versioned state

`.release/release-train.json` is the machine-readable planning state. It records
the target Base version, the current version during planning, each selected
component release, full immutable component commits, the expected milestones,
and the BOM workflow inputs. The file is deliberately JSON so the preflight can
run without adding a new parser dependency.

Run the local, read-only preflight from the Base checkout:

```bash
python3 tools/release_train_check.py
python3 tools/release_train_check.py --format json
```

Run the hosted-state preflight when GitHub readback is needed:

```bash
python3 tools/release_train_check.py --remote --format json
```

During release preparation, after the release-prep PR has updated `VERSION`,
README, context metadata, and the changelog, add `--release-prep`:

```bash
python3 tools/release_train_check.py --remote --release-prep --format json
```

The checker is read-only. It never creates milestones or issues, changes a
Project field, pushes a branch, merges a pull request, creates a release, or
updates Homebrew.

## Lifecycle

1. Create or confirm the exact `vX.Y.Z` milestone in every repository that
   owns work for the train.
2. Review the open issues and pull requests in those milestones. Reassign
   unrelated work before implementation begins; do not hide it by closing it.
3. Complete component releases and record their public tags and peeled commits.
4. Update downstream pins and run the consumer checks required by the selected
   Base BOM.
5. Run the local and hosted preflight. Treat every error as a blocker and
   record warnings in the release issue.
6. Dispatch the BOM workflow at the exact reviewed Base commit. Require both
   Ubuntu 24.04 and macOS 14 jobs to pass and preserve the downloaded BOM.
7. Run the existing `basectl release check` and guarded publish flow with the
   same BOM. Do not publish merely because ordinary component CI is green.
8. Read back the tag, GitHub Release, assets, checksums, package registries,
   immutable-release metadata, and public documentation.
9. Close the release issue and milestone only after the public readback is
   complete. Preserve the evidence paths in the release issue.

## Patch versus minor scope

The Base `1.10.1` dogfood patch may contain documentation, CI, internal
preflight tooling, release manifests, and non-breaking AI harness fixtures. It
must not silently establish a new supported public command contract. The
stable `basectl release train` command surface, machine-readable contract, and
replayable AI harness are tracked for Base `1.11.0` in issue #2499.
