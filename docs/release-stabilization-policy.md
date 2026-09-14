# Release Stabilization and Independent Review Policy

This policy makes release ceremony proportional to compatibility risk. It is
the decision record used by `basectl release check`, the release checklist,
and the release issue. Automated checks remain the normal gate; this policy
adds candidate time and independent judgment where those checks cannot prove
upgrade behavior or reviewer independence.

## Release classes

| Release class | Candidate or bake expectation | Independent review | Required evidence |
| --- | --- | --- | --- |
| Patch (`X.Y.Z`) | Direct publication is allowed after the normal release checks when the change is low-risk and does not alter a public compatibility, installer, trust, manifest, or release-artifact boundary. | Recommended; a maintainer records a waiver when no independent reviewer is available. | Passing release check, focused regression evidence, and a release issue or equivalent record. |
| Patch with a high-impact change | At least one reviewable candidate window on `main`; the release issue records the start and end time and any compatibility findings. | Required where an independent reviewer is available; otherwise record the waiver and the missing evidence. | The normal BOM and platform checks plus the high-impact checklist below. |
| Minor (`X.Y.0`) | Release candidate or beta, followed by a compatibility bake before publication. | Required where available; a documented waiver is permitted for a solo-maintainer release. | Candidate tag or equivalent reviewed commit, upgrade evidence, BOM, and release issue decision. |
| Major (`X.0.0`) | Release candidate or beta with an explicit migration review and a longer bake appropriate to the change surface. | Required where available; a waiver must name the unavailable reviewer and the residual risk. | Migration notes, compatibility evidence, BOM, and release issue decision. |
| Urgent security or availability patch | Use the shortest safe path. Do not wait for a normal bake when delay increases user risk. | Post-release independent review is acceptable when pre-release review is not possible. | Security or incident record, focused validation, and a follow-up review date. |

The default bake expectation is one full working day for a high-impact patch,
three full working days for a minor release, and five full working days for a
major release. A release owner may choose a longer window. A security or
availability response may choose a shorter window, but the exception and
follow-up review must be recorded.

## High-impact change checklist

Treat a release as high-impact when it changes any of these boundaries:

- manifest parsing, command trust, or execution authorization;
- installer, shell-profile, environment, or destructive cleanup behavior;
- workspace, cross-repository, GitHub, or release-BOM contracts;
- platform support, package metadata, Homebrew, or license declarations; or
- a stable JSON schema, finding ID, public flag, or compatibility promise.

For a high-impact release, the release issue records:

1. the reviewed commit and candidate or bake window;
2. the focused compatibility and upgrade commands that were run;
3. the independent reviewer, or the explicit reason a waiver was needed;
4. unresolved findings and the decision to fix, defer, or accept each one; and
5. the exact BOM and hosted evidence used for publication.

## Review and waiver rules

Independent review means a person who did not author the relevant change and
who can evaluate its compatibility or operational risk. Automated CI is
necessary but does not count as independent judgment. A waiver is valid only
when the release issue names the unavailable reviewer, explains why release is
still justified, identifies the residual risk, and records a follow-up review
date or the next release in which the review will occur.

The policy does not require a large governance organization. Until additional
maintainers exist, the release owner may publish a qualifying release with a
clear waiver. The waiver makes the missing evidence visible; it does not make
the release appear independently reviewed.

## Tool and checklist integration

`basectl release check` remains the mechanical readiness gate for version,
changelog, provenance, tags, GitHub, and BOM evidence. `basectl release plan`
and [the release process](release-process.md) point to this policy so the
release owner can classify the change before running the gate. The release
issue is the source of truth for the candidate window, review or waiver, and
the objective evidence that cannot be inferred from repository state alone.

Rehearse this policy against the next eligible release without changing
published history. If the release is high-impact, add the classification and
waiver fields to the release issue before the candidate window starts.
