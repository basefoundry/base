---
name: base-release-train
description: Inspect and coordinate Base ecosystem release trains using the repository's versioned policy, milestone rules, immutable refs, BOM evidence, and public readback gates.
---

# Base Release Train

Use this skill for Base, base-demo, base-cli, base-bash-libs, and the two demo
repositories when the task concerns release readiness, release milestones,
cross-repository pins, BOM evidence, or publication follow-up.

## Source of truth

Read `docs/release-train.md` and `.release/release-train.json` in the Base
checkout before making a recommendation. Use
`python3 tools/release_train_check.py --format json` for deterministic local
preflight and add `--remote` for GitHub milestone/release readback.

Report separately:

- completed and publicly verified evidence;
- blockers that must be resolved before publication;
- warnings or stale issues that need triage;
- intentionally deferred work assigned to a later milestone.

Do not infer a release from `main`, a README version, green ordinary CI, or a
mutable branch. Require the public tag, peeled full commit, release assets,
checksums, required BOM platforms, and post-publication readback.

## Operating modes

- **assess**: read current repositories, milestones, pull requests, hosted
  checks, tags/releases, pins, lockfiles, docs, BOMs, and public metadata.
- **plan**: create or reconcile exact SemVer milestones and issue ledgers;
  default a missing future companion milestone to the next patch only when the
  issue is explicitly release work.
- **check**: run the local and hosted preflight and preserve machine-readable
  output in the release issue.
- **train**: implement issue-backed changes in canonical worktrees, validate,
  push, and open reviewable PRs. Keep the exact issue ledger.
- **readback**: verify tags, releases, assets, registries, checksums,
  immutable metadata, BOM contents, and public docs after publication.

## Safety boundaries

The skill is read-only by default. Before creating or editing issues,
milestones, Project fields, branches, PRs, releases, or Homebrew state, obtain
explicit authorization for that mutation. Never merge or publish just because
checks are green. Treat queued checks, unresolved review threads, stale
provenance, missing milestones, and non-immutable releases as blockers.

The `1.10.1` process-hardening patch may ship internal tooling, policy,
workflow checks, and harness fixtures. A new supported `basectl release train`
CLI contract belongs to the `1.11.0` release scope unless the maintainer
explicitly changes that version decision.
