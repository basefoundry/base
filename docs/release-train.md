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
   prerelease, or a newly published GitHub Release that is not reported
   immutable. A manifest may explicitly mark a pre-enforcement historical
   release as `legacy_mutable` for one train only; that produces a warning, not
   a pass, and repository-level immutable-release enforcement must still be on.
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
component release, full 40-character component commits, the expected milestones,
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

## Version-consistency contract

Every release-aware repository declares its authoritative version file and
required public version surfaces in
`.release/version-consistency.json`. Base runs the reusable checker on every
release-train pull request:

```bash
python3 tools/version_consistency_check.py
python3 tools/version_consistency_check.py --format json
```

The checker validates the authority, file-specific required text, and every
allowlist exception's rationale and expiry. It does not reject historical
examples merely because they contain an older version; such examples must be
listed explicitly as expiring exceptions. Registry or public-release
readback remains a separate hosted gate: `release_train_check.py --remote`
checks GitHub release/tag state, while package repositories must add their own
registry readback to the same release-prep workflow.

Adoption status is tracked here until each repository carries the same small
contract and workflow invocation:

| Repository | Current adoption |
| --- | --- |
| `base` | Implemented by `.release/version-consistency.json` and `Release Train Policy` |
| `base-cli` | Tracked for adoption in #2536 |
| `base-bash-libs` | Tracked for adoption in #2536 |
| `base-demo` | Tracked for adoption in #2536 |
| `base-cli-demo` | Tracked for adoption in #2536 |
| `base-bash-libs-demo` | Tracked for adoption in #2536 |

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

The `legacy_mutable` marker is a narrow migration aid for releases published
before GitHub immutability was enabled. It must not be copied to a new
component version: remove it when the next component release enters the
manifest, and require the new release to read back as immutable.

## Patch versus minor scope

The Base `1.10.2` recovery patch may contain documentation, CI, internal
preflight tooling, release manifests, and non-breaking AI harness fixtures. It
must not silently establish a new supported public command contract. The
stable `basectl release train` command surface, machine-readable contract, and
replayable AI harness are tracked for Base `1.11.0` in issue #2499.

## Patch-release dogfood sequence

Use this sequence to exercise the release process with progressively different
dependency inputs. Every component patch must have an issue-backed fix or
guardrail; version-only releases create noise without testing a real contract.

1. Recover Base with a patch release that keeps the latest released component
   pins unchanged. For the v1.10.2 recovery release, the selected pins are
   `base-cli` 0.5.1, `base-bash-libs` 2.2.2, and `base-demo` 0.2.1.
2. For a single-component exercise, publish the component patch first, verify
   its public tag, release, and peeled commit, then update the Base manifest and
   BOM inputs and repeat the full Base preflight, BOM, publication, and
   Homebrew readback. Do not use a component branch or local checkout as a
   released dependency.
3. Repeat the single-component exercise for each Base BOM participant. The
   companion demos remain independently aligned but are not Base BOM inputs.
4. For an all-component exercise after those single-component releases, publish
   another patch of each component so the final Base diff changes all three
   pins—for example `base-cli` 0.5.3, `base-bash-libs` 2.2.4, and `base-demo`
   0.2.3—then publish the next Base patch with all three exact refs.

Each cycle ends only after the immutable release assets, checksums, package or
installer metadata, downstream documentation, and Homebrew upgrade path have
been read back publicly. A green component workflow alone is not release
evidence.
