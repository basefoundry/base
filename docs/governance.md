# Maintainer Continuity and Contributor Governance

Base is currently maintained by one primary maintainer. That is a material
adoption risk for a tool that can be wired into shell startup, CI, and several
repositories. This page states the current position plainly and records the
smallest practical path toward a second trusted reviewer or co-maintainer.

## Current continuity position

- The primary maintainer owns normal merges, releases, security response, and
  repository administration.
- Public issues and pull requests are the durable record of technical context;
  important decisions should not remain only in private chat or local notes.
- Apache-2.0 licensing permits a user to fork and continue the project if the
  primary maintainer is unavailable. A fork is a legal fallback, not a
  substitute for a maintained upstream continuity plan.
- GitHub branch and workflow protections remain the source of truth for merge
  safety. A maintainer absence does not justify weakening them silently.

## Operational definition of unavailability

For planning purposes, the primary maintainer is considered unavailable when
there have been no merged commits, issue-triage updates, or release/security
responses for four consecutive weeks, unless a public notice names a different
date. A security report or active release incident should be treated as an
urgent exception and escalated through `SECURITY.md` rather than waiting for
the four-week threshold.

When the threshold is reached, adopters should:

1. preserve the last known-good release and its immutable BOM;
2. open a public continuity issue with the affected release and operational
   impact, without disclosing security-sensitive details;
3. use the documented fork path for urgent fixes; and
4. coordinate a proposed upstream handoff in the public issue before changing
   release or branch policy.

## Concrete onboarding path

The next continuity step is to invite one external contributor or trusted
reviewer to shadow a bounded release or compatibility change. The target role
does not initially require repository administration. It can begin with:

- reviewing one issue-backed compatibility or documentation PR;
- independently checking the release checklist and BOM evidence;
- participating in one security-triage rehearsal without seeing private
  report details; and
- documenting any missing runbook or access needed for a future backup role.

The release owner records the invitation, the issue/PR reviewed, the outcome,
and the next step in the linked issue. After two successful review cycles, the
project can evaluate a limited co-maintainer role such as release sign-off,
security-triage backup, or review of one repository area. Push and
administrator access remain separate decisions and are granted only when the
role has a demonstrated need.

## Decision record

This is a staged mitigation, not a claim that a second maintainer already
exists. The project should update this page when a reviewer accepts the
invitation, completes the shadow cycles, receives a scoped role, or becomes
unavailable. The [release stabilization policy](release-stabilization-policy.md)
defines the explicit waiver when an independent reviewer is not available for
a qualifying release.

For repository review settings and the no-weakening rule, see the
[team review policy](review-governance.md). For private vulnerability reports,
see [Security](../SECURITY.md).
