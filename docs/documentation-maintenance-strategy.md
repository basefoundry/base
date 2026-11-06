# Documentation Maintenance Strategy

**Status: Proposed.** [Issue #2631](https://github.com/basefoundry/base/issues/2631)
owns this proposal; the maintainer owns acceptance. This page does not activate
a new workflow, CI gate, or GitHub ruleset. The current
[GitHub workflow](github-workflow.md) remains in force until an accepted policy
and its implementation land through their own issue/PR trains.

## Problem and Starting Point

The October 2026 audit found contradictory behavior descriptions, invalid
examples, and missing contracts despite passing existing documentation checks.
[PR #2629](https://github.com/basefoundry/base/pull/2629) reconciles the known
runtime, IDE, release, retention, workspace, and ownership descriptions.
[PR #2630](https://github.com/basefoundry/base/pull/2630) consolidates upgrade
guidance. Review and merge those corrections before adopting this strategy.
The remaining manifest-schema gap stays with
[#1613](https://github.com/basefoundry/base/issues/1613).

Base already has a PRD, architecture and feature documents, an issue/worktree
gate, and a [contract registry](contracts.md). Extend these assets. A passing
suite proves its covered assertions; it does not prove that all implementation
behavior is documented or that prose agrees with code.

## Documentation Layers and Authority

Keep existing topic paths. Each maintained document should identify its purpose,
status (proposed, accepted/current, or historical), owning area, and relevant
contract IDs. Release-specific behavior should identify the applicable version.

| Layer | Question it owns | Existing home and update trigger |
| --- | --- | --- |
| Product requirements | Who is this for, what outcome is promised, and what is excluded? | [Product Requirements](product-requirements.md); change when product intent, supported users, or durable requirements change. |
| High-level design | What are the components, responsibilities, trust boundaries, and dependencies? | [Architecture](architecture.md), [Execution Model](execution-model.md), and [Technical Overview](technical-overview.md); change for cross-component or platform decisions. |
| Detailed behavioral contract | What inputs, states, defaults, outputs, failures, persistence, and compatibility rules apply? | Topic documents such as [Python Manifest](python-manifest.md), [Workspace Manifest](workspace-manifest.md), and [Release Process](release-process.md); change for observable behavior. Avoid copying function internals. |
| Decision record | Why was a material choice accepted and what alternatives were rejected? | A decision section in the owning topic, or a linked dedicated record for cross-topic decisions; retain supersession history. |
| User guidance and reference | How does someone use, diagnose, recover, or migrate? | README, [FAQ](../FAQ.md), command reference, onboarding and task guides; change alongside affected user behavior. |
| Operations and security | What can execute, mutate, persist, fail, or require recovery? | Trust, uninstall, cache, bootstrap, release and support documents; assess even for changes with no new command. |
| Derived and consumer material | Where is the contract repeated or demonstrated? | `.ai-context/`, `skills.md`, templates, help/completions, demos, presentations and downstream repositories; update or regenerate affected surfaces. |

Accepted design describes intended behavior; implementation and reproducible
tests establish observed behavior. A disagreement requires classification and
maintainer resolution, not automatic rewriting of the design to match code.
Historical plans remain useful evidence but do not override current canonical
documents. The docs index should make both authority and status visible.

## Before Implementation and Before Merge

1. **Classify in the issue.** Identify affected contracts, owning documents,
   compatibility and user impact, proposed validation, and a human decision
   owner before dependent code starts.
2. **Draft the change first.** For material behavior or architecture changes,
   draft the affected design and user/operational documentation. Obtain recorded
   maintainer acceptance of the design revision in a design PR or linked issue
   before implementation. Mark future behavior as proposed until it ships.
3. **Keep small fixes proportionate.** A restoration fix can cite an existing
   accepted contract and a reproduction proving the deviation. It still needs
   an impact record and any affected documentation draft. An internal refactor
   can justify unchanged contracts; neither needs an invented architecture spec.
4. **Amend decisions as needed.** If implementation reveals a different contract,
   update the design and obtain acceptance before writing dependent behavior.
   Record the reviewed revision so earlier approval cannot cover a new design.
5. **Finish in the implementation PR.** Final design, examples, FAQ/user guidance,
   operational notes, release disposition, and derived material accompany the
   implementation before merge. A prior design PR does not replace this check.
   A necessary cross-repository doc change must be linked and ready before the
   corresponding behavior ships, with explicit merge/release ordering.

Under the proposed default, ordinary PRs cannot defer required docs to a later
issue. Any future emergency exception needs an explicit maintainer-owned policy,
recorded scope, and a bounded follow-up; this proposal creates no such bypass.

## Reviewable Impact Record

Every material PR should report all eight categories, including source-only PRs.
For each category, record `updated` with document paths/anchors and evidence, or
`no-impact` with a change-specific reason. Blank fields, template text, and
unexplained `N/A` are invalid. One unrelated Markdown edit is not evidence that
the affected contract was updated.

| Category | Required disposition |
| --- | --- |
| Product intent | PRD impact or why accepted requirements remain unchanged. |
| High-level design | Components, dependencies, platform/trust boundaries affected or unchanged. |
| Detailed design and decisions | Contract IDs, accepted design revision, and input/state/failure/retention changes. |
| User docs and examples | README, FAQ, task guides, troubleshooting and migration impact. |
| Interfaces and compatibility | CLI/help/completions, manifest/output schemas, stability and deprecation impact. |
| Operations and security | Setup, trust, permissions, persistence, uninstall, diagnosis and release operations. |
| Release communication | Unreleased entry or fragment, reference to an adequate existing entry, or a specific no-user-visible-change reason. |
| Derived material and consumers | AI context, skills, templates, demos, presentations, and downstream contracts. |

Start with a PR table while the policy is reviewed. The proposed automated form
is one versioned change record, for example `.changes/<issue>.yaml`, containing
these dispositions, contract IDs, design acceptance reference/revision, and
validation references. Generate the PR summary from it and validate agreement;
do not maintain two independent copies. Define the schema and its migration in
an implementation issue before introducing this path as a requirement.

The author owns completeness. The maintainer reviews semantic accuracy and
design acceptance, especially for trust, destructive operations, compatibility,
and release behavior. Additional domain reviewers should be used when available;
the process must state Base's actual maintainer capacity. AI review can assist
but cannot supply independent human acceptance or prove semantic completeness.

## Executable Traceability

Extend [the contract registry](contracts.md) with stable IDs, owning source
paths, canonical document anchors, responsible areas, validation references,
and coverage status. Start with the corrected audit domains, then expand across
the implementation inventory. New modules need a mapping or a reviewed internal
scope explanation. Keep a visible unverified queue; mapped files alone are not
a semantic coverage percentage.

Use the production parser to validate maintained current YAML examples. Label
complete examples, fragments requiring a fixture wrapper, and proposed syntax
separately. Exercise representative accepted and rejected fixtures against both
parser and published schema under #1613. Validate links and anchors, source-owned
help/completions, generated templates, and affected AI exports. Preserve targeted
behavior probes for runtime routing, IDE consent, release recovery, retention,
workspace cancellation, and upgrades rather than checking for words alone.

Generated views should have a declared source and deterministic freshness check.
Human-written summaries need explicit review because byte comparison cannot
prove their meaning. Tests referencing document paths prove those paths exist;
they do not prove the contract is complete.

## Enforcement and Release Handling

Implement one reusable local/CI validator that evaluates changed source against
the contract map and the impact record. Missing mappings, unexplained omissions,
invalid current examples, stale generated output, or missing release dispositions
should produce actionable findings. A reviewer still decides whether a
`no-impact` explanation is true and the documentation is adequate.

Run metadata validation from trusted base-branch code, treating PR content as
data. Run candidate-code/parser checks without privileged credentials. Bind
results to the current head and re-evaluate after code pushes, impact-record or
PR-body edits, relevant labels, and design-acceptance changes. Define event
coverage and stale-result invalidation before enabling a required check.

Prove the gate fails with known-bad canaries: omitted impact, placeholder reason,
unmapped public source, unrelated documentation, invalid example, missing release
disposition, and a skipped/failed child check. An unrelated-doc fixture can prove
path coverage fails; semantic evasion still needs human review. The aggregate
must not report success when a required child did not run. After a trial on at
least ten representative PRs with no unresolved false positives, verify the
canaries and enable a required check such as `base/documentation-impact` through
an explicitly authorized settings change. Read back the ruleset and demonstrate
that a failing current-head result prevents merge.

Keep `CHANGELOG.md` as the release-facing history. Issue-scoped news fragments
can reduce conflicts once their format and aggregation are implemented; until
then, use Unreleased entries. Documentation-only and internal changes can use a
reasoned no-impact disposition. A correction to an unreleased feature can point
to its still-accurate existing entry. At release time, reconcile entries with
the included PRs, compatibility/migration notes, and documentation for that
version. Do not silently rewrite published release history to describe main.

At each minor release, audit changed contracts and sample unchanged high-risk
contracts. Track unresolved drift by severity, unmapped domains, broken examples,
and stale derived surfaces. Report inspection breadth and behavioral coverage
separately; avoid an unsupported claim that all documentation is aligned.

## Issue-Backed Rollout

| Stage | Deliverable and existing work |
| --- | --- |
| 1. Correct the baseline | Review #2629 and #2630; retain #1613 as the explicit schema gap. |
| 2. Accept policy | Decide this proposal, then update AGENTS, contributor/workflow guidance and the PR template together in an issue-backed PR. Apply the impact table and pre-code design acceptance immediately after adoption. |
| 3. Map and validate | Extend the current contract registry and automate examples/freshness in bounded issue/PR slices; finish schema/parser parity through #1613. Record coverage limits. |
| 4. Integrate preflight and CI | Reuse [#2570](https://github.com/basefoundry/base/issues/2570)'s validator work. [#2572](https://github.com/basefoundry/base/issues/2572) currently covers presence/shape and is planned for v1.13.0; semantic documentation-impact coverage requires an agreed scope extension or separate linked issue. |
| 5. Promote after evidence | Coordinate negative canaries with [#2566](https://github.com/basefoundry/base/issues/2566), complete the trial, and authorize/read back required-check configuration. Feed claim/evidence coverage into [#2595](https://github.com/basefoundry/base/issues/2595). |

[#2573](https://github.com/basefoundry/base/issues/2573)'s machine-readable agent
assignment is related governance work and is already a prerequisite of #2572.
It does not supply documentation ownership or design acceptance. Manual policy
adoption and focused documentation checks can proceed without waiting for the
agent-loop rollout. This proposal does not reschedule those existing issues or
claim their implementation is complete.

## Industry Basis and Base-Specific Choices

These are selected practices, not a claim that every project uses one standard.
Sources were checked on 21 October 2026.

| Primary source | Practice and proposed Base adaptation |
| --- | --- |
| [Rust RFC process](https://rust-lang.github.io/rfcs/) | Substantial changes go through design consensus; many fixes and documentation improvements use ordinary PRs. Base can require accepted design for material behavior while keeping restoration fixes proportionate. |
| [CPython PR lifecycle](https://devguide.python.org/getting-started/pull-request-lifecycle/#updating-news-and-what-s-new-in-python) | Documentation accompanies changes; individual news entries describe user-visible effects, with explicit exceptions. Base can require a release disposition and introduce fragments without requiring notes for every typo. |
| [GitLab documentation workflow](https://docs.gitlab.com/development/documentation/workflow/) | Developers own feature documentation and should include it in the code MR when possible; linked documentation MRs are also supported. Base's proposed same-PR default is a stricter local choice to prevent its observed drift. |

[PR #521](https://github.com/basefoundry/base/pull/521) adapted selected
Superpowers practices into Base-native guidance. The current
[agent guidance](../AGENTS.md) favors Base-specific rules, and the
[docs index](README.md) treats `docs/superpowers/` as planning history.
Repository evidence does not explain whether a personal plugin was later
removed. Require reviewable design, impact, and validation outputs; skill
invocation alone is not an enforceable documentation contract.

## Decisions for Acceptance

The proposed defaults are the eight-category impact record, recorded acceptance
before material implementation, final affected docs in the implementation PR,
and staged enforcement with human semantic review. Acceptance should identify
the responsible maintainer, the first contract-map/validator slices, whether to
extend #2572 or create a linked earlier documentation gate, and the change-record
and news-fragment formats. Keep the page marked proposed until these decisions
are recorded; policy adoption and enforcement are separate deliverables.
