# Base Ecosystem Governance Implementation Plan

**Version:** 4.1 draft, 12 November 2026
**Status:** Proposed rollout; this plan authorizes no implementation by itself.
**Owner:** Ramesh (codeforester)
**Companion:** [Base Governance Design](DESIGN.md), currently accepted as v1.3 by [PR #2664](https://github.com/basefoundry/base/pull/2664); Step 3 below proposes a separately reviewed v1.4 update.
**Implementation tracker:** [#2665](https://github.com/basefoundry/base/issues/2665)
**Plan-review issue:** [#2691](https://github.com/basefoundry/base/issues/2691)
**Design-review record:** [#2663](https://github.com/basefoundry/base/issues/2663), closed; it is not the implementation tracker.

This plan replaces v3.1 after review. It incorporates the v4.0 draft, the accepted decisions recorded with the design review, and the pre-Triage findings on issues #2666–#2690. It separates the 1.11 foundation from four governance releases and preserves the original scope of earlier work while that work is crosswalked.

Only Step 1 in §3 is active now. It replaces this file through one issue and one PR. No milestone migration, issue editing, design change, or later step is authorized until the maintainer directs it.

## 1. Purpose and operating rules

The rollout establishes a documented, evidence-based issue and PR lifecycle across Base and Base-supported projects. Every implementation change remains issue-backed and reviewed. A package can have several implementation issues; an issue can have several delivery slices only when the plan names each slice and its acceptance outcome. The planned slices, not the history of PR numbers, determine completion.

The rollout uses the lifecycle **Backlog → Triage → Ready → In Progress → In Review → Done**. Triage remains between Backlog and Ready. Draft PRs keep their issue In Progress. For a multi-PR issue, it stays In Progress while any planned slice has no current PR or only a draft PR. It becomes In Review when every planned slice has a current non-draft PR and at least one current PR is still open; merged slices may coexist with open slices. It becomes Done when every planned slice is merged or has a terminal maintainer disposition, such as cancelled or accepted with evidence. A closed-unmerged or superseded PR does not complete a slice by itself. If a slice is replaced or replanned, the issue stays In Progress until that replacement is ready or a terminal disposition is recorded. This avoids treating an old closed PR as completion when replacement work is still needed.

Each repository configures separate issue-loop and PR-loop limits, initially three rounds each. The initial review counts as round one. An author responds to every finding; the reviewer verifies and resolves findings that are addressed or correctly challenged. Disputes, unavailable required reviewers, and unresolved findings at the limit go to the maintainer. A PR verdict names the full head SHA. A new code push requires a fresh review; a narrowly verified base-only update can use the exception in the accepted design. Required approving reviews remain zero while author and reviewer share one GitHub identity. The maintainer retains merge and release authority.

A review uses a separate agent in a genuinely new session with no author transcript or persistent authoring memory. Repository configuration may require a different AI tool. Base ecosystem repositories default to `different-tool`; Base-supported projects default to `fresh-session`. If a configured different tool is unavailable, the work waits or escalates; it does not silently fall back to the author's tool. Verdicts record author and reviewer tool, model, and session. With one shared GitHub account, thread-resolution identity and overrides are manually audited; the plan does not claim GitHub enforces identities it cannot distinguish.

Every issue and PR uses the ten documentation-impact categories in the design. Each category names a destination or an evidence-based no-impact reason. Each implementation PR supplies a release-note line or a reasoned `none`. Every user-found bug gets a failing test before its fix unless the PR explains why a test is not possible; the pilot counts these exceptions. Any meaningful process change updates all documents that describe that process in the same PR.

Security-sensitive automation starts read-only. Issue text, PR descriptions, comments, diffs, test output, and artifacts are untrusted input. Reviewer jobs receive minimum permissions, no secrets, pinned actions/dependencies, and no ability to execute untrusted code. Hosted model calls require a threat review and permission test and must record provider, data disclosure, and retention assumptions. Automated fixes are not authorized by this plan. Any later repair capability needs its own authorization model, branch-scoped short-lived credentials, diff allowlist, tests/scanners, kill switch, and maintainer review; agents never merge, release, publish, or change policy.

## 2. Release sequence

Each governance stage is a release. There is no feature freeze or fixed calendar schedule. A release ships when its exit evidence is met and the maintainer chooses to cut it.

| Base release | Role | Scope and exit evidence |
|---|---|---|
| **1.11.0** | Foundation | Adopt this plan; renumber Base milestones; correct the design; define areas; inventory and reorganize Base documentation; bring `base-demo` into lockstep; reconcile governance issue scopes and dependencies. Use the accepted design as the interim document contract; the ADR template/index and conversion of durable decisions begin with #2666 in Stage 1. No new governance automation is enabled. |
| **1.12.0** | Stage 1: manual loops | Run #2666 through the first manual Ready review and implement the document/ADR contract; then migrate the Base Project schema and deliver work-item/PR contracts, repository governance configuration, reviewer rules, baseline, title migration, conversation-resolution setting, and manual issue/PR pilots. Exit when representative pilots complete the manual loops without bypass and evidence is recorded. |
| **1.13.0** | Stage 2: deterministic checks | Implement readiness/lifecycle checks and status reconciliation; dry-run first; introduce warn-only rules and the override record. Exit when dry-run results match maintainer decisions on a declared sample and warnings remain non-blocking. |
| **1.14.0** | Stage 3: drift checks and read-only review | Pin the checker from the released 1.13.0 artifact; run drift checks and the least-privilege read-only reviewer only after their security gates. Exit with reviewed evidence and rollback demonstrated. |
| **1.15.0** | Stage 4: organization adoption | Adopt the released profile repository by repository, including Base-supported `banyanlabs` and organization templates in `basefoundry/.github`. Each product repository keeps its own issue milestones and release; Base 1.15 coordinates and pins ecosystem releases. |
| **After 1.15.0** | AI-context replacement | Start packages 13–14 only after all four governance stages complete. Target the new export behavior for 1.16.0. Keep tracked `.ai-context/` until the replacement has shipped and been proven; cleanup cannot complete in the same release that first introduces the replacement. |

A work package belongs to one of these releases or is explicitly deferred. A dependency that requires a released artifact must wait for that release to ship; it cannot be declared complete in the same release that first creates the artifact. Base milestones are repository-scoped. Issues in another repository stay in that repository's milestone system and are coordinated through #2665 and the Base GitHub Project, not assigned a Base milestone.

## 3. Base 1.11 foundation sequence

Run these steps one at a time. The maintainer validates each result before the next begins. Every change after Step 1 has its own issue and PR. Step 1 is the only active step in this plan-review train.

### Step 1: adopt this plan — active now

Review the v4.0 draft against v3.1, the accepted design, and live issue state/comments. Resolve the findings captured here, then replace only `docs/governance/IMPLEMENTATION-PLAN.md` through issue #2691 and one PR. Claude reviews the PR. Do not edit the other issue bodies, milestones, Project fields, or `DESIGN.md` in that PR.

### Step 2: renumber Base milestones — not started

Create the future Base milestones required by the migration. Move each open Base issue from 1.12 to 1.16, 1.13 to 1.17, 1.14 to 1.18, 1.15 to 1.19, and each later numbered milestone up by four. Preserve descriptions and historical issue links. Record issue counts and values before and after, and retain closed issues in their historical milestones. Do not blindly copy due dates: the schedule is flexible and the current v1.11/v1.12 dates collide, so the maintainer must approve or clear each date after reviewing the new scope. Repurpose Base 1.12–1.15 for the four governance stages, with no date until one is agreed.

Do not renumber milestones in other repositories in this step. Inventory every open issue left in Base 1.11 that is not foundation work and present it to the maintainer for a decision; do not move it automatically. A Base milestone migration is an issue/PR train and must report per-milestone counts before and after.

### Step 3: revise the design to v1.4 — separate issue and PR

Use a separately reviewed design issue/PR to align `DESIGN.md` with this plan and resolve the accepted-design review follow-ups. Include the crosswalk outcome for #2555 before asserting that all agent-loop scope is covered. At minimum, address the interim document-home rule; Base Project migration order; delivery-slice derivation and closed-unmerged replacement behavior; the actual status writer; reviewer and author provenance; the current `basectl release notes` and `basectl export-context` contracts; document locations and ownership; and the items below. Preserve decisions that were already accepted unless a new decision is explicitly approved.

- Keep standards in `STANDARDS.md`; do not list a nonexistent `governance/standards/` directory.
- Say that the rows in appendices A and B are preserved verbatim, not their changed introductions and headings.
- Update the design version and status together; update the companion reference in this plan only when that PR merges.
- Define one status writer for each lifecycle transition. Existing `basectl gh` commands already set In Progress; the reconciler and any future controller must not compete with them.
- Keep the issue fingerprint and slice plan consistent with the approved contract; material edits or a changed Issue Type stale Ready approval.
- Keep public community-support intake distinct from the internal Triage status.
- Keep the accepted ADR lifecycle. Package 1 (#2666, Stage 1) establishes the ADR template/index and migrates durable decisions identified by package 23; `.ai-context/DECISIONS.md` remains maintained until then.

### Step 4: redefine Base areas — package 22

Propose the area vocabulary from the existing shared defaults in `project_model.py` and Base’s `.github/base-project.yml`; do not invent a second catalog. Provide one-line area purposes and a draft repository-path map. Update shared defaults and Base-specific options through their own issue/PR. Remap open Base issue Area values only after the maintainer approves the map, recording before/after counts.

### Step 5: inventory and reorganize Base documentation — packages 10 and 23; package 1 follows in Stage 1

1. Use the then-current accepted DESIGN as the source for document kinds, locations, owners and impact categories; package 1 (#2666) will establish the ADR template/index under the new manual Ready process in Stage 1.
2. Inventory every document and map it to its canonical kind and home: PRD, area design, decision record, generated reference, user guide, operational/security guide, or derived artifact. Start from existing audits rather than repeating a blind crawl.
3. Have the maintainer compare `docs/product-requirements.md` with current intent; revise it only after that review.
4. Write one area design document per approved area, using the accepted template.
5. Write/update user guides, install chooser, FAQ, references, operations and examples as the inventory requires. Leave `.ai-context/DECISIONS.md` as the maintained source until package 1 defines the ADR home; migrate durable decisions in Stage 1.
6. Revise README last, after its linked canonical documents have moved.

Until the area documents exist, record durable facts in the current canonical document. The first-party reviewer rules may live in `governance/rules/` and prompts in `governance/prompts/`; standards remain in `STANDARDS.md`. Do not create a required `governance/` directory for Base-supported projects.

### Step 6: bring `base-demo` into lockstep

After Base areas and canonical documents settle, update only references and contracts in `base-demo` that would otherwise be broken or stale: links to moved Base documents, README/guide references, its manifest, and its Base Demo E2E workflow. Write a short base-demo PRD that agrees with Base’s PRD. Its own area redesign and full documentation reorganization wait for Stage 4. Release the downstream version update after Base 1.11 ships.

### Step 7: reconcile issues and legacy scope — maintainer approval required

Build one reviewed crosswalk before changing any issue. Use the live comments on #2666–#2690 as pre-Triage evidence, not as issue-loop rounds. The comments do not consume the issue review limit. After the pre-Triage review, move an issue into Triage through the normal workflow to disposition its findings; before Ready, replace generic template text with its own scope, impact dispositions, real dependency issue numbers, open questions, and validation. Do not change those issue bodies or milestones in this plan PR.

The crosswalk must:

- Reconcile every governance package with the current issue that implements it, identify duplicates, and give every retained issue a real dependency link and a target stage.
- Preserve the original scope of issues whose bodies were rewritten. Use edit history and the #2555 crosswalk to restore the original work as a separate issue when it no longer matches the reused number. Never claim a partial pilot, baseline, threat model, or read-only reviewer covers an authoring controller or durable ledger.
- Link original dependents to the issue that actually owns their prerequisite. The known affected set includes #2575, #2577–#2579, #2582, #2587, #2590, #2592–#2595, and #2602; recalculate it from live relationships before editing.
- Keep #2665 as the implementation tracker and #2555 as the broader legacy roadmap until every listed scope has a disposition. Cross-link them; do not silently close or absorb #2555.
- Correct the inaccurate homebrew-base Project statement in the tracker through a separate authorized issue train. `homebrew-base` has no local Project; its issue items are in the Base Project.
- Keep milestone and metadata edits separate from this plan. The maintainer approves the complete issue/disposition list before any body, status, label, dependency, or milestone change. Claude reviews every new or changed issue before it can move to Ready.

#### #2555 and its original work

The accepted design governs human-reviewed issue/PR loops and a read-only reviewer. It does not by itself deliver every controller, ledger, replay, MCP, or retrieval item in #2555. The crosswalk must keep these boundaries explicit:

| Original scope | Current plan coverage | Required disposition before package milestones are assigned |
|---|---|---|
| #2576 state machine, event schema, autonomy levels, stop conditions | Manual issue-loop pilot and lifecycle rules cover only the human lifecycle and parts of the state transitions. | Preserve the event-schema/autonomy work separately unless the v1.4 design amendment explicitly adopts it. |
| #2573 structured Agent Assignment proposal | The accepted design rejects an Agent Assignment field in the issue contract; the current #2573 scope is the manual PR review loop. | Keep the current PR-loop scope in package 6. Record the original assignment proposal as rejected by the accepted design, and preserve any distinct authority requirement only through an explicit #2555/design decision. |
| #2577 ledger; #2578 controller L1; #2579 claim/lease; #2582 replay fixtures/evals; #2602 crash-safe ledger; #2575 worktree hygiene | Not delivered by a manual pilot, status reconciler, or pre-pilot baseline. | Keep original scope and dependencies; propose separate issues/packages only after the design states who owns Status, the ledger, controller authority, and stage gates. |
| #2580 controller L2 that verifies and proposes a draft PR | Package 21 is a read-only reviewer and does not author PRs. | Keep the authoring controller separate; require an amendment and its own issue/PR before implementation. |
| #2581 bounded repair | The accepted design defers automated fixes pending authorization, threat review and permission tests. | Keep as deferred security work; do not treat the deferred design gate as implementation completion. |
| #2574 PR classes that may merge without human review | Closed as superseded by the accepted design in #2664, which requires a human maintainer to merge every PR. | Do not implement an allow-list for merging without human review. Keep sensitive-path review boundaries in the relevant governance packages. |
| #2583 loop metrics report | Package 17 is a manually captured pre-pilot baseline, not an ongoing report. | Keep the report scope separate if still wanted; link baseline and report distinctly. |
| #2584 manifest `agent:` path/size/autonomy policy | Package 3’s `governance:` config and package 15 consumer defaults are not equivalent. | Preserve or recreate the original agent-policy scope; do not mark it covered by consumer defaults. |
| #2599 controller authority, credentials, approvals and audit | Package 21’s read-only threat model covers only a subset. | Keep the read-only and authoring-agent threat boundaries separate; get maintainer approval before authoring authority is designed. |
| #2592/#2593 pilots, #2595 scorecard, #2603 independent-adopter evidence | New feature/bug issues pilot the governance process, not the agent controller or adoption claims. | Retain these as distinct evidence work unless the crosswalk explicitly maps each original outcome. |
| #2570 branch-name/issue-link preflight; #2594 friction label and weekly log | #2570's branch/issue checks remain distinct from the PR-body validator #2572. Package 17 captures weekly governance-pilot friction but is not all of #2594's friction triage contract. | Preserve #2570's checks and keep its body-validation scope in #2572. Link #2594 to pilot evidence without silently closing or broadening it. |
| #2499 release train; #2601 matrix-evidence verifier | Governance stage sweeps use the existing release gate but do not replace release-train or matrix-evidence behavior. | Keep these scopes in the release/test-bed track; update only through their own reviewed issue trains. No freeze or fixed release dates are implied. |
| #2585–#2591 and #2600 MCP/retrieval, plus #2556–#2568/#747/#1606 and #2603 test-bed/adoption work | Outside releases 1.11–1.15; the new context export does not replace MCP/retrieval, the test matrix, or independent-adopter evidence. | Keep their original scope and links in #2555 or a separately approved roadmap; do not close them as covered by governance. |

The crosswalk also records the original scope of #1613’s full JSON Schema request. The governance config issue can validate governance keys through the existing runtime schema; it does not make the broader editor/schema request disappear. Preserve that full-schema work as a scope-matched issue if it remains wanted, and retain any true MCP dependency until the owning issue is changed through review.

### Step 8: prepare Stage 4 repository tracking

Review the nine repository-local adoption issues and eleven title-migration issues against the final design and Step 7 crosswalk. The organization contains eleven repositories in this rollout: Base, the nine other product repositories, and `basefoundry/.github`. The `.github` repository has Issues disabled and is handled through Base-owned issue #2685; its organization templates are consumed by seven repositories. `homebrew-base` has no manifest or local Project; its issue items are in the Base Project. `banyanlabs` is a Base-supported consumer: use the consumer defaults (`fresh-session`) without requiring a `governance/` directory.

Do not move another repository’s issue into a Base milestone. Each issue keeps its local status and milestone; the Base tracker/Project supplies the cross-repository view. At Stage 4, inventory live Project schemas before migrating each repository, then record counts and values before and after. Do not assume that all repositories have the same Project fields or options.

### Step 9: publish a one-page issue map

After issue review and stage assignment, produce a read-only dependency map for packages in 1.12–1.15. Show the first issues that can start, cross-release gates, local versus Base-owned issues, pilot selections, and any remaining gaps. The map is not approval to start an issue.

### Step 10: release Base 1.11

Run the foundation stage-end sweep in §8.3, verify every 1.11 issue is closed or explicitly moved with a maintainer-approved reason, confirm required checks have completed, and release only when the maintainer directs it. Stage 1 starts after 1.11 ships and the maintainer authorizes it.

## 4. Governance stage runbooks

### 4.1 Base 1.12 — Stage 1, manual loops

Run in this order:

1. Run #2666 through the first manual Ready review, using the then-current accepted design as the review rubric. Implement its document/ADR contract as the first Stage 1 train; this establishes the canonical rule set before dependent issues proceed.
2. Migrate Base Project schema and current values (package 8). The current organization Issue Types are Task, Bug and Feature; the current Priority options are P0–P3; there is no Risk tier field. Verify on the project template that schema changes preserve existing values. Map each issue's existing priority one step to the new scale (P0→P1, P1→P2, P2→P3, P3→P4), preserving its meaning and recording counts before and after; test the migration on the template first. Add Low/Medium/High Risk tier. `homebrew-base` issues are Base Project items and migrate here; do not duplicate this operation in homebrew-base#96.
3. Deliver the one planned-work issue form and Ready contract (package 2), and the PR template/release-note contract (package 5). The form is an intake aid, not the enforcement boundary: blank issues, CLI/API issues, and external connectors can bypass it. Keep support intake and private security advisories distinct. Triage assigns exactly one existing category label; native Issue Type and category label are separate. No category prefix is added to issue or PR titles.
4. Add repository governance config (package 3) and reviewer rules/prompts/method map (package 16). Bounds and exact CLI syntax remain explicit Triage decisions on the implementation issue; the plan does not invent them.
5. Capture the pre-pilot baseline (package 17) before running pilots.
6. Enable required conversation resolution through a reviewed setting change (package 9) before the PR pilot. Keep required approving reviews at zero. Because both agents share an identity, the maintainer manually audits who resolved each finding.
7. Migrate Base open issue/PR titles to plain outcome/problem wording after the new contract is in place (package 18); leave closed/merged titles historical.
8. Before the stage starts, have the maintainer select a few small real feature or bug issues from the normal product roadmap planned after 1.15.0, excluding governance packages, and assign them to v1.12 as pilots. Run a separate representative PR through the manual PR loop; the maintainer sets Ready after checking the reviewer verdict and current fingerprint. Agents do not write Project Status during the manual pilot.

Exit evidence: at least one representative issue and PR complete the loop; all findings have author responses and valid reviewer resolution, head SHA and provenance are current, three-round limits are honored, tests and release-note dispositions are present, and friction/exceptions are compared with the baseline.

### 4.2 Base 1.13 — Stage 2, deterministic checks

Implement issue readiness, PR-body validation, slice-based Status reconciliation and the round ledger (package 7). Name all existing status writers and choose one authoritative writer for each transition; do not let a controller, `basectl gh`, and reconciler fight. Run a read-only/dry-run sample first. Add warn-only behavior and an audit-only override while author and reviewer share one account (package 19, #2682). This package depends on #2571 and #2572. Warnings do not block, revert, or mutate Project state.

Before Stage 2 starts, have the maintainer select a few small feature/bug issues from the normal product roadmap planned after 1.15.0, excluding governance packages, assign them to 1.13, and use them to compare automated checks with manual decisions. Continue normal feature work outside the selected pilots; there is no feature freeze.

#2682 must ship in 1.13 before its released checker can be pinned. Do not close the pinning issue in the same release that first delivers the checker. Stage exit requires a declared sample, matching maintainer decisions, recorded false positives/negatives, and a rollback path. No hosted CI check uses an unpinned checker.

### 4.3 Base 1.14 — Stage 3, pinned checks and read-only review

After 1.13 ships, use its exact released tag and full commit SHA as the checker pin; record the release BOM and how CI obtains the artifact. Complete #2683/package 20 before CI relies on the pin. Build one shared path-map runner for the drift checks rather than three competing frameworks. Local and dry-run checks may precede the pin; hosted enforcement waits for it. Extend existing documentation/link tests rather than creating a parallel test system.

Before Stage 3 starts, have the maintainer select a few small feature/bug issues from the normal product roadmap planned after 1.15.0, excluding governance packages, assign them to 1.14, and use them to test the pinned checks and read-only review process.

Run per-kind checks and the read-only reviewer only after package 21’s threat review, least-privilege permissions, untrusted-input handling, provider disclosure, and no-code-execution tests pass. Findings cite evidence and create issues; they do not silently edit policy. Do not enable automated fixes. Stage exit includes a demonstrated pin rollback and reviewed pilot evidence.

### 4.4 Base 1.15 — Stage 4, repository adoption

After 1.14 ships, adopt the accepted profile one repository at a time. The Base repository is first (#2684); it must follow the released checker gate. Then update `basefoundry/.github` templates (#2685) and the nine other repositories through their own issue/PR trains. Apply the ecosystem defaults to Base ecosystem repositories and consumer defaults to `banyanlabs`. Update repo-specific Projects only after inventory and before/after evidence. Migrate issue templates and PR templates from their actual source; seven repos inherit organization issue forms, and homebrew-base also inherits the organization PR template.

Migrate open titles only after the relevant forms and rules exist. Each repository retains its own release and milestone system. Base 1.15 pins the new versions of Base ecosystem dependencies in its release BOM. Before adoption starts, have the maintainer select a few repository-local feature/bug issues from the normal product roadmap planned after 1.15.0, excluding governance packages; assign each to its repository's Stage 4 milestone and track it in #2665/Base Project.

Exit evidence: all eleven repositories have an accurate profile record, Project and milestone counts where applicable, governance settings, title/template inventory and workflow checks. A repository with no local Project or disabled Issues is recorded as an exception, not reported as incomplete adoption.

### 4.5 After Base 1.15 — AI context replacement

The existing `basectl export-context` command bundles checked-in `.ai-context/` files and has `--format`, `--output`, `--print`, and `--list-files` behavior. Preserve that behavior until a replacement is implemented, released and proven. The new generation mode may invoke a user-selected installed AI CLI. Before implementation, decide supported CLIs and non-interactive flags, explicit consent, data sent, privacy disclosure, failure/offline behavior, source selection, and output location. Maintain existing `.ai-context/` files and references until cleanup. Issue #2627, which proposed seeding tracked `.ai-context/` packs during `repo init`, is closed as not planned under this replacement approach.

Target package 13 (#2686 specification and #2687 implementation) for 1.16.0 after the five releases. Keep package 14 cleanup (#2688, base-cli#509, base-demo#374) blocked until the replacement is released and verified. Because #2688 cannot be complete in the same release that first ships #2687, assign cleanup to a post-1.16.0 patch/follow-up after the evidence exists. Remove only the obsolete `.ai-context/` check from the successor to #2572; keep its other PR checks. Update the actual in-repository references listed by #2688; do not claim a Base scheduled workflow exists unless one is identified.

## 5. Work-package crosswalk

The package number is an identifier, not execution order. Dependencies and the stage runbooks determine order. Existing issue numbers are reused only when their live scope matches. A package may use separate issue/PR trains for separate repositories.

| # | Package | Primary issue(s) / current crosswalk | Target |
|---:|---|---|---|
| 1 | Document kinds, owners, impact taxonomy, ADR contract | #2666; ADR template/index and decision migration; standards stay in `STANDARDS.md` | 1.12 |
| 2 | Single work-item form and manual Ready contract | #2667; readiness contract also feeds #2571 | 1.12 |
| 3 | Repository governance config and manifest validation | #2668; distinguish runtime schema work from #1613 full JSON Schema | 1.12 |
| 4 | Manual issue-loop pilot | #2576 only for its matching manual-pilot scope; preserve uncovered event/autonomy contract separately | 1.12 |
| 5 | PR template and release-note contract | #2669 and #2670; update both PR template and `github.pr.required_sections` | 1.12 |
| 6 | Manual PR review loop | #2573 where its live scope matches; reviewer rules in #2680 | 1.12 |
| 7 | Readiness, PR-body, slice Status and round-ledger checks | #2571, #2572, #2673 | 1.13 |
| 8 | Project schema and live-value migration | #2672; Base in 1.12, other local Projects in Stage 4 | 1.12 / 1.15 |
| 9 | Conversation-resolution setting and human merge boundary | #2674; approvals remain zero | 1.12 |
| 10 | Evidence-backed document inventory | #2675; reuse the 2026 audits and verify live org facts | 1.11 |
| 11 | Documentation path map and per-kind drift checks | #2676–#2679; distinct from the Project Area options in package 22; shared runner; CI waits for #2683 | 1.14 |
| 12 | First-party and consumer repository adoption | #2684, #2685 and nine repo-local adoption issues | 1.15 |
| 13 | AI context generation outside repository | #2686, #2687; current bundle behavior preserved through replacement | 1.16.0 target |
| 14 | Remove tracked context after replacement is proven | #2688, base-cli#509, base-demo#374 | After 1.16.0 release/proof |
| 15 | Consumer governance defaults and upgrades | #2584 only if it is re-scoped to this exact work; otherwise preserve its original `agent:` scope | Deferred pending evidence |
| 16 | Versioned reviewer rules, prompts and method map | #2680, #2681; keep `.ai-context/` pointers until cleanup | 1.12 |
| 17 | Pre-pilot baseline | #2583 only for the baseline scope; preserve its original metrics-report scope separately | 1.12 |
| 18 | Plain-language titles for open issues/PRs | #2689, #2690 and nine repo-local title issues | 1.12 Base / 1.15 others |
| 19 | Warn-only checks and auditable override | #2682; requires #2571 and #2572 | 1.13 |
| 20 | Pin released checker and promote rules by evidence | #2683; only after #2682 is released | 1.14 |
| 21 | Read-only reviewer pilot and threat model | #2599 and #2580 only for read-only review; preserve controller authoring scope | 1.14 |
| 22 | Redefine Base areas | New issue after plan acceptance; existing shared vocabulary remains source | 1.11 |
| 23 | Reorganize Base documents | New issue(s) after inventory; README last; `base-demo` has a separate downstream train; ADR conversion waits for package 1 | 1.11 |
| 24 | Renumber Base milestones | New issue after plan acceptance; count and verify every migration | 1.11 |

The dependency/release sequence is especially important:

- #2682 (warn-only checker) ships in 1.13; #2683 pins the released artifact in 1.14.
- #2684 (Base profile adoption) follows the released pin in 1.14; the remaining repositories adopt in 1.15.
- #2686/#2687 introduce and ship the replacement export after Stage 4; #2688 cleanup waits for that release and proof.
- #2677–#2679 may be developed and run locally before pinning, but hosted CI use waits for #2683. They share the same area map and runner.
- #2670 adds release-note assembly without changing the existing documented read-only `basectl release notes` command. Its entries come from reviewed PR text; it must define rate-limit/offline behavior and not invent changes. #2572 checks a PR’s release-note disposition; #2670 checks release completeness; #2679 checks decision-record links.
- #2669 updates both `.github/pull_request_template.md` and the CLI-generated body contract in `base_manifest.yaml` `github.pr.required_sections`. A multi-PR slice uses `Part of #N`; the CLI default must not inject `Fixes #N` for a slice.

## 6. GitHub metadata and repository boundaries

Use the native issue Type values Task, Bug and Feature. Do not invent Documentation, CI, Security, or Enhancement types. Type classifies work; category labels (`bug`, `enhancement`, `documentation`, `ci`, `security`) remain separate because current branch policy reads exactly one category label. Triage assigns the label; form submission is not assumed to assign a dynamic category. Private vulnerability reports stay in security advisories; follow-up work is a Bug or Task.

Project fields are canonical for issue planning: Status, Priority, Size, Area, Initiative and proposed Risk tier. Do not copy these values onto PRs, add PRs to Project as mirrors, or duplicate the fields as organization Issue Fields. Labels serve cross-cutting routing; milestones plan repository-local releases; native relationships express parent/child, blocking, and linked PR/slice delivery. Type and fields on an issue are not substitutes for those relationships.

Migrate Priority P0→P1, P1→P2, P2→P3 and P3→P4, preserving each issue's meaning and recording counts before and after. The proposed Risk field does not exist today; create Low/Medium/High only through the reviewed schema migration. Do not add a per-area risk floor before the field and pilot evidence exist. Reorder Status to Backlog, Triage, Ready, In Progress, In Review, Done and update descriptions and internal docs together. Public community-triage guidance stays separate until its own reviewed decision.

The machine-readable governance settings live under `governance:` in the existing `base_manifest.yaml` where a repository has one. There are separate issue/PR loop limits, each initially three. `basectl config` adds repository-scoped configuration without changing machine-local config behavior; exact command syntax and numeric bounds are resolved in #2668. Existing GitHub PR requirements remain under `github.pr`. The `.github/base-review-policy.yml` reader remains during a documented compatibility period and is removed only after replacement config and docs ship.

Base-supported projects do not need a new `governance/` folder and do not inherit live settings. Explicit configure/upgrade writes a reviewed PR. `banyanlabs` uses the consumer profile. `homebrew-base` receives a minimal manifest because it has none today. `basefoundry/.github` is an organization-template repository with Issues disabled; treat its defaults as part of the eleven-repository rollout without inventing a local Project.

## 7. Issue and PR review procedure

### 7.1 Issue loop

1. Intake may use the work-item form, `basectl gh issue create`, GitHub API, or an allowed blank issue. The current native Issue Type and one category label are verified at Triage.
2. The author writes the issue contract and delivery slices in the issue body. Before Ready, every impact category has a destination/reason, expected behavior is distinct from scope, dependencies use real issue numbers, bug reports include reproduction details, and open questions are real rather than a blanket `none`.
3. A separate fresh-session reviewer checks product and design contracts, scope, impacts, acceptance-to-validation mapping, slices, and risks. The issue limit is three rounds including initial review. Every finding receives an author response and reviewer verification/resolution; disputes or exhaustion go to the maintainer.
4. A Ready verdict records the current contract fingerprint. Changing Type or fingerprinted issue content makes it stale. At Ready, the maintainer confirms the verdict and sets Ready.

### 7.2 PR loop

1. The PR links one issue and names one planned slice. A single-PR train may use `Fixes #N`; a slice uses `Part of #N`. Draft PRs keep the issue In Progress.
2. A separate reviewer reads the issue, slice, current PR diff, tests, documentation, and versioned rules in a new session. It records the full head SHA, author/reviewer tool, model and session, rules version, findings and round.
3. The author responds to each finding with the fix or a challenge and evidence. The reviewer checks the response and resolves the thread if addressed or justified. A challenged finding that remains disputed goes to the maintainer. Changed code starts the next review round.
4. A base-only update skips a round only under the exact verified `git range-diff` and merge-diff criteria in the accepted design; any uncertainty, conflict-resolution addition or changed non-merge commit requires a full review.
5. When no actionable finding remains, the reviewer posts `Verdict: Approved at <full-head-SHA>`. This is a process verdict, not a GitHub approval event. Required approving reviews stay zero.
6. The maintainer checks the verdict SHA, checks, findings/resolutions, impact evidence, and release-note disposition, then merges. At the configured round limit, unresolved findings go to the maintainer; nothing approves by timeout.

### 7.3 Pilot evidence

Package 17 records baseline sample boundaries, missing data and limitations. During each stage pilot, record attempted issues/PRs, rounds, stale verdicts, disputes/escalations, slice replacements, changed impact dispositions, bypasses, time to review and bug-test exceptions. Record friction weekly. Compare results cautiously; small samples do not prove causation. Governance pilots measure the process and do not substitute for the distinct `bankbuddy`/`blend` agent-controller pilots or independent-adopter evidence from #2555.

### 7.4 Claude's pre-Triage findings on #2666–#2690

These comments are contract findings to resolve during Step 7. They are not PR-review rounds, and posting them does not move an issue to Ready. Use exact issue numbers and current repository behavior; do not change these contracts in Step 1.

| Issue(s) | Required correction or evidence before Ready |
|---|---|
| #2666 | Remove the ten D23 nits already fixed in merged design commit `f06a1178`; add the remaining package-1 follow-ups (standards stay in `STANDARDS.md`, appendices preserve rows rather than all prose verbatim, correct version/status references, rename the package-table `Order` column to `#`, and move provenance follow-up to #2680). Record ADR conversion in package 23. |
| #2667 | Keep one planned-work form distinct from support and security-advisory intake. Include blank/API/CLI intake in the readiness boundary; resolve the current-Type/category-label responsibility in Triage. Update or explicitly replace the old-section `basectl gh issue readiness` contract through #2571, add the template test, and link the organization-default work in #2685. |
| #2668 | Validate governance keys through the existing runtime schema and name the actual command implementation path. Preserve machine-local `basectl config`; specify repository scope, bounds, CLI syntax, reviewer-mode defaults, and the compatibility period for `.github/base-review-policy.yml`. Keep #1613's full JSON Schema scope separate unless restored as a matching prerequisite. |
| #2669 | Update both `.github/pull_request_template.md` and the CLI-generated PR body contract in `base_manifest.yaml` (`github.pr.required_sections`). Make `Fixes #N` versus `Part of #N` follow the single-issue/slice rule. Do not ask the author to fill reviewer provenance. Record that body enforcement arrives through #2572, and link org/repository adoption. |
| #2670 | Preserve the existing read-only `basectl release notes` contract; implement an additive assembly mode. Define merged-PR data source, offline/rate-limit behavior, release grouping, and the release-prep editor boundary. Separate PR-entry validation (#2572), release completeness (#2670), and ADR-link checking (#2679). |
| #2671 | Include `support.yml`, issue chooser links, public triage documentation and `tests/test_community_triage_docs.py`. Only the Status redefinition depends on this decision; Priority/Risk migration can proceed in a separate slice. |
| #2672 | Verify that Project option changes preserve values on the template Project before migrating Base. Preserve issue priority meaning when mapping P0–P3 to P1–P4, recording and restoring exact values if option changes do not preserve them. Include homebrew-base's issues as Base Project items, split Status work behind #2671, and set meaningful priorities for the critical path. |
| #2673 | Name existing `basectl gh` Status writers and designate one writer; do not let a controller and reconciler compete. Dry-run first and gate hosted writes on the released checker (#2683); use explicit dependency issue numbers. |
| #2674 | Name the actual branch-protection and branch-ruleset mechanisms and use #2569's investigation. The setting proves conversation resolution, not reviewer identity; the shared-account pilot relies on maintainer audit. Enable the setting before the PR pilot, with required approvals still zero. |
| #2675 | Start from the existing documentation audits. Correct the inventory: eleven repositories including `.github`; no local Project for homebrew-base; `.github` Issues disabled; seven repositories inherit organization issue forms and homebrew-base also inherits the PR template. Coordinate ADR migration with #2666. |
| #2676 | Use the existing area vocabulary and state where the path map lives; the destination remains an issue-level decision. |
| #2677–#2679 | Share one path-map/check framework. Local and dry-run checks may precede the pin, but hosted CI waits for #2683. #2678 reuses existing link and doc-contract tests and names per-kind checks. #2679 does not duplicate #2572's PR release-note check or #2670's release completeness check. |
| #2680 | Store rules under `governance/rules/` and prompts under `governance/prompts/`; record both author and reviewer tool/model/session; wait or escalate if a required reviewer is unavailable. During the shared-account phase, overrides are enforced by maintainer audit. Controller-authored PRs follow the same review rules. |
| #2681 | Keep `AGENTS.md` and workflow pointers to `.ai-context/` until cleanup after the replacement release. Decide whether `METHOD.md` lives at repository root or under `docs/governance/`. |
| #2682 | Add #2571 and #2572 dependencies. Treat overrides as audit-only while both agents share an account. Ship warn-only checker behavior before the pin issue can close. |
| #2683 | Depend on released #2682; record an immutable tag and full commit SHA, release-BOM provenance, and how CI obtains the artifact. |
| #2684 | Depend on #2571/#2572 and a released #2683. Correct adoption links to #2672, enumerate applicable packages (3–9, 16–17, 19–20), and link the nine local adoption issues. Remove homebrew-base's contradictory consumer-profile/no-`governance/` wording and migrate its Project items only in Base. |
| #2685 | Treat this as the source of organization-default issue/PR templates for seven repositories. Slice the template update separately so those repositories can adopt the templates before later enforcement; address category-label assignment consistently with #2667. |
| #2686–#2687 | State existing `export-context` bundle, format and output behavior. Keep it until replacement; define supported CLI/non-interactive flags, consent, privacy disclosure and external destination before implementation. Link the real cross-repository cleanup prerequisites. |
| #2688 | Depend on #2572's successor and the released/proven replacement, not #2673. Name actual references (`.github/pull_request_template.md`, manifest PR-path rules, `skills.yml`, `AGENTS.md`, `CONTRIBUTING.md`); do not claim an in-repository scheduled export workflow without evidence. |
| #2689–#2690 | Rename only open records and note that squash-merge subjects will lose category prefixes; no current CI parses title prefixes. #2690 depends on the template slice of #2685 and is a no-op if there are no open PRs at execution time. |

Before Ready, replace repeated generic Impact/Scope text in each issue with its own destinations and no-impact evidence, and replace placeholders such as “the P1 issue” with real issue numbers. A completed pre-Triage review permits normal Triage; it does not by itself approve an issue as Ready.

## 8. Document ownership, release notes and stage-end control

Package 10 maps the PRD, area designs, canonical command reference, user guides, README/FAQ, operational/security docs, tests, examples, templates, ADRs, release notes and generated/derived artifacts to an owner and source. The README is revised last. Existing audit findings are inputs, including `docs/documentation-alignment-audit-2026-11.md`, #2628, #2650, #2651 and the 2026-10-18 audit.

A process change updates every document that currently describes that process in the same PR. A changed implementation updates its source contract and every affected user/reference/operations/FAQ surface; evidence-based no-impact entries are allowed. Generated references remain derived from code/schema/help. `.ai-context/` remains a maintained derived-orientation layer until the replacement export ships; it is not the home for new durable decisions.

Before each release from 1.11 through 1.15, review docs, templates, prompts and `AGENTS.md` for superseded rules. Record gaps as issues and resolve them before the release. Verify package-specific release notes against merged PR entries; a release-preparation edit may improve wording but cannot add unrecorded changes.

## 9. Deferred scope and non-goals

- Superpowers skills stay deferred unless a manual pilot exposes a concrete spec-driven development or drift-prevention gap.
- Consumer governance defaults/upgrades stay deferred until first-party adoption provides evidence.
- Automated fixes stay deferred until their own authorization and security gates pass.
- MCP and retrieval, matrix/test-bed work, controller authoring, durable loop ledgers, crash recovery, and independent-adopter claims retain their original #2555 roadmap scope unless a reviewed crosswalk explicitly brings a bounded slice into this plan.
- No fixed date, feature freeze, automatic merge, auto-release, or agent authority to change Projects, workflow/ruleset policy, credentials, trust, installers or security controls is created by this plan.

## 10. Decisions that remain open for their own reviewed issues

The plan deliberately does not invent decisions that belong in the package contract or design amendment. Before an affected issue reaches Ready, its owner and reviewer resolve:

- exact loop-limit bounds and `basectl config` syntax;
- the path for the shared area-map artifact;
- exact export provider CLIs, non-interactive flags, consent and data disclosure;
- how the single work-item form and Triage set category labels while blank/API intake remains possible;
- the location of `METHOD.md`;
- the full #2555 disposition for controller Status ownership, one versus multiple ledgers, controller levels, authoring authority, MCP/retrieval timing, and the scope of agent-loop work included in governance;
- any issue-specific fields, dependency corrections, release note behavior and local milestone assignments identified in Claude's comments.

No issue moves to Ready with an unresolved blocking question. No design change is smuggled into an implementation package; if the accepted design must change, it gets its own issue, decision record and PR.
