# Base Governance Design

**Version:** 1.4, 20 November 2026
**Owner:** Ramesh (codeforester)
**Status:** Accepted through PR #2699; implementation proceeds through the companion plan's issue/PR trains
**Intended home:** `docs/governance/DESIGN.md` in `basefoundry/base`
**Companion:** `docs/governance/IMPLEMENTATION-PLAN.md`, which sequences the proposed work

**Sources consolidated:** Base Direction Memo v12 (19 Oct 2026); Base Working Notes Parts 1–37 (22 Oct–2 Nov 2026); the supplied governance drafts (3 Nov 2026); current Base workflow, configuration, review and documentation contracts; Ramesh's clarifications (7–19 Nov 2026); and accepted implementation plan v4.2.

### How to read this document

Each topic appears once, in its final form. The historical rows in Appendices A and B remain verbatim; their current introductions and headings are editorial framing. Every section carries a status:

| Label | Meaning |
|---|---|
| **DECIDED** | Settled direction for this proposal. It becomes active policy only after the design PR is accepted and merged. |
| **PROPOSED** | Recommended design detail for review or a pilot. |
| **OPEN** | Not decided. Listed in §21. |
| **EXPLORATORY** | Ideas worth keeping, not commitments. |
| **DEFERRED** | Deliberately left for later (mostly Phase 2). |
| **NEW** | Added during the original consolidation. Appendix B records its origin; it is not a pending approval by itself. |

The historical rows in Appendices A and B are preserved verbatim. Their headings and introductions are current framing, not historical source text. Appendix E records later maintainer decisions; Appendix F records current dispositions of B1–B18; Appendix G cross-checks A1–A36 and links the 49-issue crosswalk. The current body and companion plan are authoritative.

---

## 0. Summary

This design describes how Base turns proposed work into a reviewed change, keeps its documentation current, and records why lasting decisions were made. The issue holds the problem, expected result, scope, risks, document impact and delivery slices. Each PR implements one slice; work without a PR still needs reviewable evidence.

1. **Start with analysis.** New work moves from Backlog to Triage. A separate reviewer checks the issue and plan. A maintainer sets Ready after findings are handled and the approved contract is current.
2. **Implement the approved plan.** The default is one issue and one PR. When an issue needs several PRs, named slices keep them connected. A closed, unmerged PR does not finish a slice.
3. **Review each change in a loop.** Issue and PR loops have separate repository settings, each initially limited to three rounds. Authors answer every finding. Reviewers verify the answer and identify the exact revision; authors resolve confirmed or withdrawn threads. Disputes and exhausted loops go to the maintainer.
4. **Carry lasting facts into the repository.** Issues identify documentation and decision impacts. PRs update the relevant design, user guidance, reference, tests, examples, operations and release-note record before merge.
5. **Give every status an owner.** Project Intake sets Backlog on open/reopen; the author agent records Triage when it starts the issue plan, In Progress after the maintainer authorizes work, and In Review when each slice has reviewable evidence. The maintainer owns Ready and Done, plus overrides and manual corrections. Stage 1 audits the agent transitions and observes existing writers; post-reconciler ownership remains open until its design and rollback are approved.
6. **Use GitHub fields for distinct purposes.** Issue Type classifies the work; Project fields track it; labels remain flat cross-cutting tags; milestones plan releases; relationships express dependencies and decomposition. Issue fields are not copied to PRs.
7. **Record who reviewed what.** Reviewers use a new session without the author's context. From Stage 1, the reviewer App has a distinct GitHub identity; the author agent and maintainer still use `codeforester`. Verdicts identify tools, models, sessions and the reviewed issue fingerprint or PR head SHA. Account names alone are attribution, not proof.
8. **Roll out by evidence.** Base 1.11 is the foundation; governance stages ship in 1.12–1.15. Replacement AI-context export follows those stages, and tracked .ai-context files stay until replacement is released and proven.

The contributor/agent map issue [#2681](https://github.com/basefoundry/base/issues/2681) should link here. Its current contract still requests a separate METHOD.md, so that issue must be reconciled in its own train to make the map link to this summary instead; no METHOD.md is planned. This plain-language summary is the method overview.

## 1. Purpose and scope

### 1.1 Problems this solves — DECIDED

From the Memo and the working notes:

1. **Review gap.** Since Claude Code began reviewing Codex PRs, the estimate is that about 60% had at least one real review finding. Earlier PRs were often merged after a glance; package 17 records the source and historical sample limits.
2. **Drift.** Issues, PRs, design docs, user docs, tests, `demo.sh`, `base-demo` and `.ai-context/` fall out of sync. The nightly export of 2 Nov 2026 still described 1.10.5 as an active release line after it had shipped.
3. **Hidden requirements.** Agents miss rules that live only in the maintainer's head. The `basectl workspace test` trust case: the command warned about trust, then kept running tests on previously trusted projects with no per-project output. The missing piece was a product-wide convention, not a feature spec.
4. **Disconnect between intent and implementation.** Hand testing keeps finding gaps between what Ramesh meant and what was built. The pre-pilot baseline records the available historical count and source; if the count cannot be reconstructed, it is marked unavailable rather than estimated.
5. **Incomplete and inconsistent metadata.** Issue Status transitions are skipped; Project field values accumulate with no retirement path; labels stand in for structured fields.
6. **Decisions lost in conversation.** Long chats get compacted and decisions vanish. Agents don't read past issues on their own.
7. **Human as glue.** Ramesh triggers agents and carries results between them by hand.

### 1.2 Scope — DECIDED

- **Phase 1 (this design's main subject):** governance across every repository in the `basefoundry` organization: the nine Base ecosystem repositories `base`, `base-cli`, `base-bash-libs`, `base-demo`, `base-bash-libs-demo`, `base-cli-demo`, `base-workspace`, `base-platform-tools`, and `homebrew-base`, plus `banyanlabs`, a Base-supported project. `banyanlabs` participates in Phase 1 using the consumer defaults (`fresh-session` reviewer and no required `governance/` directory), so the rollout tests both profiles. The inventory verifies which repositories have a Project and which shared defaults apply; the organization-level `.github` repository is not a product repository.
- **Phase 2 (DEFERRED, §19):** governance offered as a product to Base-managed projects, through `basectl repo configure`.
- GitHub is the only platform supported for now. The method is written so that GitLab or Bitbucket would need adapters, not a new method (§15.4).

### 1.3 Base case for the recursion — DECIDED

Banyan Labs needed Base; Base needed governance; governance needs an issue system. To stop the recursion, the governance layer is "done enough" when its minimal version (template, six statuses, issue loop, fold-back) works end to end on one real feature. After that, real use drives refinements.

---

## 2. Principles

### 2.1 Governance principles — DECIDED

These govern how the governance layer itself is designed. They merge Memo §3 with the principles added in the working notes. Duplicates are combined.

1. **Guardrails over full specs.** Write cross-cutting conventions once; every command inherits them.
2. **Every incident becomes a permanent guardrail.** A fix isn't complete until a convention, test, lint or checklist item stops that class of problem from recurring.
3. **Make drift mechanically detectable.** Prefer generated docs, then docs checked by tests, then human or agent checklists.
4. **Plan before code.** The plan is written and approved before implementation starts.
5. **Contain, don't just prevent.** Assume some mistakes ship. Design for small blast radius and clear diagnostics.
6. **Issue is the unit of planning; PR is the unit of change.**
7. **Events, not memory.** Metadata, status changes and agent runs are driven by events and verified by checks, never left to someone remembering.
8. **Agents are prompts plus triggers.** A reviewer "agent" is a repo-owned rule set and prompt run by an event.
9. **Deterministic gates route; AI handles the routine middle; humans own judgment and risk.**
10. **Automated tests over manual testing.** Manual use finds bugs; automation keeps them found.
11. **Configuration as code; retire, never delete.**
12. **One vocabulary, migrated deliberately.** Native Issue Types classify work; category labels remain distinct while current branch policy reads them. Any type/label convergence requires a migration and a decision about Feature versus Enhancement.
13. **Strict for insiders, welcoming for outsiders.**
14. **Use each GitHub feature for what it was built for.** Issue types classify, fields hold structured data, labels are plain cross-cutting tags.
15. **Versioned inheritance, explicit review.** Consumer defaults are materialized through reviewed repository changes; no runtime setting silently follows Base.
16. **Nothing is decided until it is written outside the chat.** The repo, not chat history, is the memory.
17. **One home per kind of fact.** No fact is stored twice. Code holds behavior; decision records hold why; the PRD holds intent.
18. **KISS. More moving parts mean more drift.**
19. **Same in kind, different in intensity.** The same templates, statuses, gates and document kinds apply to a small tool and a large product; only the amount of content changes. Risk tiers vary intensity, never structure.
20. **Consistency serves both readers.** The same sections in the same order every time. Humans skim faster; agents make fewer mistakes.
21. **Guardrails are invisible during the conversation and firm at the gates.** Ramesh talks to agents freely; structure begins when a conversation produces an output (an issue, a decision, a PRD change). A ride doesn't start until everyone is buckled in; nobody lectures the rider.
22. **The tool adapts to the human,** not the human to the tool. No ceremony of commands to type.
23. **Self-assessment and self-healing, never silent.** Base checks itself and proposes corrections, and every correction goes through the same gates as any other change. Reflexes (gate checks) catch problems instantly; deliberate healing (audits) turns recurring findings into new reflexes.
24. **Rules must earn their keep.** A rule that never catches anything is reviewed for retirement. A rule that only adds friction is drift in the process.
25. **Relaxing a rule means less writing, never less checking.**
26. **The checker is not the thing being changed.** Enforcement runs a pinned, released Base (Stage 2).

### 2.2 Candidate product principles for the PRD — PROPOSED

Ramesh named these as candidates for Base's "constitution". They belong in the PRD's Principles section, which only Ramesh writes. Listed here so they aren't lost:

1. Be immersed in existing wisdom, push it forward, find new arenas, and contribute back. Follow established practice humbly where it is better; innovate only where it falls short ("no new religion").
2. Problem first, technology next. Every problem is mostly a human problem.
3. The tool adapts to the human.
4. Guardrails invisible in conversation, firm at the gates.
5. Same in kind, different in intensity.
6. One home per kind of fact.
7. KISS.
8. Self-assessment and self-healing, never silent.
9. Consistency serves both readers.

---

## 3. The flow

### 3.1 One path for every change — DECIDED

The normal path applies to behavior, public contracts, architecture, security, releases and workflow policy:

1. **Conversation (free).** Ideas form in conversation. No form is imposed here.
2. **Issue.** Record the problem, expected behavior, scope, approach, rejected alternative, risks, document impacts, decisions and named delivery slices.
3. **Triage.** When the author agent starts the issue plan, it records Triage. A genuinely separate reviewer checks the contract against relevant code, docs and standards. The maintainer resolves disputes and sets Ready only after the reviewer verdict is current.
4. **Implementation.** Only after the maintainer sets Ready and directs the work does the author agent run `basectl gh issue start <N>` without `--no-project` to record In Progress. Each PR declares one issue and one slice. When every planned slice has a non-draft PR or reviewable non-PR evidence, the author agent records In Review. A slice may omit a PR only if it changes no repository content; its evidence is attached to the issue, accepted by the maintainer, and the maintainer closes the issue as Done.
5. **Review.** A separate reviewer examines the diff and relevant rules, tests, docs and decisions. The author responds to every finding. Review cycles repeat within the configured limit; the maintainer handles disputes and exhaustion.
6. **Merge and release.** A human maintainer merges. The release process assembles reviewed PR release-note entries and checks completeness.

**Light path.** A typo, wording correction, or comment-only change may use one review pass and reduced issue/impact detail only when it changes no behavior, architecture, safety property, or public contract. It remains issue-first. The reviewer decides whether it qualifies and whether it stays light; a finding alone does not promote it. Fix in-scope findings in the same change. Security, trust, credentials, installers, workflows or rulesets, releases, and MCP are never light-path work. This path does not depend on the Risk field.

Templates on this path: planned-work issue form and readiness contract (§4.2), plan (§4.3), PR template (§8.4), reviewer rules (§9), decision record (§11), and area design doc (§12.6).

### 3.2 The issue is the top of the flow — DECIDED

- Every piece of work starts with a GitHub issue.
- **Why issues:** every developer understands them; they come with UI, notifications, search, assignees, fields and PR links; outside contributors need to learn nothing new.
- **The issue is an incidental reality, not a transcendental one.** It is true for one stretch of work and drives that work to closure. After closing it is archaeology, never the source of current truth.

### 3.3 The spec and plan live in the issue body — DECIDED

- The spec and the plan are sections of the issue body, with the same first-class treatment as every other section. The plan is never a comment.
- **Why not spec files in the repo** (the Spec Kit and Kiro pattern):
  - Those tools keep specs as files mainly because agents read local files natively, they support about 30 agents and any Git host, and Spec Kit treats the spec as the source code is regenerated from. Base is spec-anchored, not spec-as-source, and its agents have GitHub access through `gh`.
  - Neither tool does anything with past specs after merge. Feature folders pile up and drift. A stale spec file looks authoritative and misleads agents; Martin Fowler's site documents an agent treating existing specs as new requirements and duplicating classes.
  - Agents rarely and unreliably read historic specs. What they read every time is AGENTS.md and the files a task leads them to.
- **What the issue approach gains:** nothing piles up; fewer moving parts; universal; discussion, plan, reviews and approval in one place; built-in workflow; no confusion about what is current.
- **Accepted risks and mitigations:**
  - *GitHub lock-in:* the method is written tracker-neutral in `governance/` (§15.4). GitHub is where it runs, not what it depends on.
  - *Network dependency:* only during implementation; after merge nothing needs the network.
  - *Weak versioning and platform risk:* acceptable, because the issue is disposable by design, provided fold-back happens.

### 3.4 Fold-back — DECIDED

- If the work was done properly, losing the issue loses nothing. Everything lasting reaches the repo **in the same PR**: behavior into user docs and tests, rules and contracts into the area design doc, the why and rejected alternatives into a decision record.
- **The test question:** "If this issue vanished tomorrow, would anything be lost?" If yes, the PR isn't done.
- **Destinations are decided up front, not inferred.** Agents write an update well once told where it goes, and decide unreliably where it belongs. So:
  1. The issue names a destination for each lasting fact (Documentation impact).
  2. The plan names exact files and sections.
  3. The PR review checks each one off.
- Expected-behavior items that became lasting promises move into the area design doc's **Contracts** section, keeping the "When …, then …" wording (§12.6).
- "Fold-back" is this design's own term. In the PR template the headings are **Documentation impact** and **Decision record**.

### 3.5 Relationship to Spec Kit and Kiro — DECIDED

Base adopts their ideas, not their tools. A fixed sequence of slash commands intrudes on the natural dialogue with the agent and applies the same ceremony to a typo and a subsystem. The burden of keeping agents consistent belongs to the system, not the programmer.

| Spec Kit / Kiro idea | Base equivalent |
|---|---|
| Spec Kit constitution | PRD principles, plus the issue reviewer's fit-with-principles check |
| Spec Kit clarify / analyze | The issue loop with an independent reviewer (a required gate, not an optional command) |
| Spec Kit plan | The Plan section of the issue body |
| Kiro steering files | AGENTS.md, `governance/` and skills |
| Kiro design.md | Area design docs, permanent rather than per feature |
| Kiro EARS requirements | Numbered "When …, then …" expected behavior (§4.2) |
| Kiro task-to-requirement links | Test-to-criterion traceability in the PR's Validation section (§8.4) |
| After-merge staleness (unsolved in both) | Fold-back (§3.4) |

Base-specific practices that need evidence in the pilot include required independent issue and PR review loops, computed affected-area checks, and document-impact fold-back on each implementation PR. The design follows GitHub's native issue and Project boundaries; it does not mirror issue metadata onto PRs.

---

## 4. Issues

### 4.1 Titles — DECIDED

- Titles describe the problem or requested change in plain language. They do not repeat category, type, area, priority, or workflow metadata.
- New issue and PR titles have no category prefixes, brackets, or word-label prefixes.
- A separate migration issue renames every currently open issue and open PR after the rule and templates are adopted, regardless of Project status or PR draft/ready state. Closed issues and merged/closed PR titles remain historical by default.

### 4.2 Single issue form and Ready contract — DECIDED

Use one planned-work form with the same sections in the same order for every planned issue, regardless of Type or size. It is an intake aid, not the enforcement boundary: blank issues, CLI/API issue creation and connectors can bypass forms, so readiness validates the issue body and its current native Type. Keep public support intake and private security advisories separate from planned work.

The form migration preserves useful information in today's sources:
- .github/ISSUE_TEMPLATE/bug_report.yml: version/commit, environment, reproduction, expected/actual behavior and secret-redaction guidance move into Problem and evidence.
- .github/ISSUE_TEMPLATE/feature_request.yml: User problem, Desired outcome, alternatives and context map to Problem, Expected behavior, Scope and Plan.
- .github/ISSUE_TEMPLATE/implementation.yml: Goal, Background, Scope, Acceptance Criteria, Validation and Non-Goals map to the common contract.
- .github/ISSUE_TEMPLATE/documentation.yml: location, reader problem and suggestion map to Problem, Expected behavior and documentation impact.
- .github/ISSUE_TEMPLATE/support.yml and config.yml: remain separate support and private-security entry paths; support questions route to the organization Discussions forum and support is not internal Triage.
- Existing `bug:`, `feature:`, `docs:`, `[Implementation]:`, and `support:` title prefixes are removed by the separately planned title policy. A category label is not a native Issue Type.

| Section | Required by Ready |
|---|---|
| **Problem** | What is missing or wrong, who is affected, and supporting evidence. A Bug includes reproduction steps and actual versus expected behavior. |
| **Expected behavior** | Numbered, observable acceptance criteria; use “When …, then …” where it clarifies the contract. |
| **Scope and non-goals** | Intended boundaries and explicit exclusions. |
| **Affected areas** | Each product area touched, with a short explanation. |
| **Impact and evidence** | For every canonical category in §12.10, name the expected file/section or state “No impact” with an evidence-based reason. Category 6 maps tests and acceptance checks to criteria and explains exclusions. “Unknown: reason” is allowed during Backlog and Triage, not at Ready. |
| **Open questions** | Questions blocking Ready; do not guess. |
| **Plan** | Fixed subheadings Approach, Rejected alternative and Risks, plus delivery slices, exact file/section changes, decision impact and validation. |

At Ready, the checker evaluates the issue's current native Type. Changing Type after Ready is a substantive contract edit and makes the verdict stale. Every user-found bug gets a failing test before its fix unless a test genuinely cannot capture it; the implementation PR explains why, and the pilot counts these exceptions.

### 4.3 The plan and delivery slices — DECIDED

The planner writes the plan in the issue body during Triage, not in a comment. It contains the approach and rejected alternative, scope, confirmed documentation impact, acceptance-to-validation mapping, decision impact, risk, and maintainer questions.

The plan names delivery slices `S1`, `S2`, … and the outcome of each. A slice is the unit of completion; it does not name a permanent PR number. Each PR declares its slice. One PR per issue is the default. A slice may omit a PR only if it changes no repository content; the plan names its reviewable completion evidence and the maintainer who will accept it. The author attaches evidence and records In Review; the maintainer accepts it and closes the issue as Done. A replacement PR may deliver the same slice after the earlier PR is explicitly marked superseded; changing a slice's identifier, outcome or acceptance criteria is a material plan change and returns the issue to Triage.

### 4.4 Readiness and issue approval — PROPOSED

The future readiness command validates the common section order, non-empty Problem and Expected behavior, current Type-specific requirements, affected areas, every impact disposition, test/acceptance mapping in category 6, delivery slices and open questions. A Bug always requires reproduction steps in the issue. The test-impossibility exception applies only to the failing-test rule for implementation PRs (§17.2). A proposed Risk tier must be present when the field is introduced; area floors remain deferred until the field and pilot exist.

The Ready fingerprint covers the exact text of:
- Problem;
- Expected behavior;
- Scope and non-goals;
- the Plan's fixed Approach, Rejected alternative and Risks subheadings;
- each delivery-slice identifier and outcome; and
- the current native Issue Type.

File lists, validation commands, comments and machine-owned metadata are outside the fingerprint. A change to any fingerprint input, including Rejected alternative, invalidates Ready, returns the issue to Triage and returns associated PRs to draft (§5.4). The verdict line is exactly “Verdict: Ready at <fingerprint>” or “Verdict: Changes needed at <fingerprint>”; the verdict body records reviewer evidence, findings, Type, author/reviewer provenance and date (§6.3).

The Ready freshness period defaults to 30 days and is configurable in repository governance settings. The maintainer sets Ready for every issue until the Risk field exists. When that field is introduced, whether an author agent may set Ready for a Low-risk issue after a current Ready verdict remains open (§21). New affected areas or document destinations discovered during implementation are recorded in the PR's actual-impact matrix and verified by its reviewer; they do not stale the issue fingerprint by themselves. A maintainer returns an issue to Triage when new evidence materially changes a fingerprinted contract or its assumptions.

### 4.5 Issue Type, category labels, and branch policy — DECIDED

The organization currently exposes native Issue Types **Task, Bug, and Feature**. Do not document or configure Bug, Enhancement, Documentation, CI, or Security as native types. GitHub type is the work classification. The accepted category labels (`bug`, `enhancement`, `documentation`, `ci`, `security`) are separate labels, not a second type system. The current branch policy reads exactly one category label to choose its branch prefix; notably `bug` overlaps semantically with the native Bug type. Keep that behavior explicit until a separately reviewed migration changes the policy.

Vulnerability reports go through private advisories, not public issues. Follow-up work is tracked as a Bug or Task. Whether `Feature` should be renamed/replaced by `Enhancement`, and whether branch policy should read Type instead of category labels, remains an implementation decision for a dedicated migration issue.

### 4.6 Creating issues — DECIDED

Conversation may produce an issue through the chosen AI tool or `basectl gh issue create`. Repository issue/PR operations do not invoke AI services. The explicit exception is the approved `basectl export-context` design: it may invoke a user-selected installed provider CLI under §12.9's privacy and security controls. The issue creator proposes no undocumented policy; the independent reviewer checks the issue against current docs and decisions.

## 5. Lifecycle

### 5.1 Statuses — DECIDED

The intended order is **Backlog → Triage → Ready → In Progress → In Review → Done**. Backlog is queued work; Triage is internal analysis and readiness work; Ready is an approved, current issue contract; In Progress means at least one planned slice is being implemented; In Review means each slice has reviewable implementation or other evidence; Done means every slice is merged or has a maintainer-approved terminal disposition. Public community-support intake is distinct from internal Triage; #2671 decides how its public wording and handoff are described (§21). Before migration, inventory existing Project values; package 8 reorders Status only after #2671 settles the support-language dependency. No transition is inferred from silence.

### 5.2 Status derivation and ownership — DECIDED

The approved issue plan is authoritative for delivery slices. Each PR names one slice; the latest non-superseded PR for that slice is current. Status is not inferred from silence. Project Intake writes Backlog on open/reopen; the author agent records Triage when it starts the issue plan, In Progress only after the maintainer has set Ready and directed the work, and In Review when every planned slice has reviewable evidence. The maintainer owns Ready and Done, plus every override and manual Status correction. Existing automation may also write Status as described below; during Stage 1, the maintainer audits agent transitions and the pilot records unexpected automation changes.

**Current writers and evidence.** During the Stage 1 pilot, account for every existing writer and record unexpected transitions:

| Current writer | Observed behavior |
|---|---|
| basectl gh issue start | Sets In Progress unless --no-project is passed. |
| basectl gh project issue set-fields --status | Manual Status mutation. |
| .github/workflows/project-intake.yml | Runs on issue opened, reopened and closed. It sets Backlog for opened/reopened issues and Done for closed issues, overwriting the current Status whatever the close reason. |
| Base Project #10 built-in workflows | All six are enabled: Item added to project; Item closed; Pull request linked to issue; Pull request merged; Auto-close issue; Auto-add sub-issues to project. Apart from the separately evidenced Pull request linked to issue behavior below, verify their Status effects in the pilot rather than inferring them from their names. |
| Pull request linked to issue | Sets In Progress. GitHub's API does not expose this setting. Timelines show github-project-automation changed #2620, #2612, #2604, #2598 and #2596 from Backlog to In Progress within about four seconds of linked-PR creation on 16–19 October 2026. If issue start already set In Progress, this workflow makes no further change. This workflow stays enabled during Stage 1. |

The owner of each transition is:

| Status | Owner and authorization |
|---|---|
| **Backlog** | Project Intake sets it on opened or reopened issues. In the lifecycle, only a Triage issue may return to Backlog, when the maintainer defers its analysis; it never returns from Ready, In Progress or In Review. A reopen-triggered write from another status is automation behavior, not authorization, and the maintainer corrects it under this rule. |
| **Triage** | The author agent records it with `basectl gh project issue set-fields --status` when it starts the issue plan. The maintainer resolves disputes and owns any manual correction. |
| **Ready** | The maintainer sets it only after a current reviewer Ready verdict, answered blocking questions, resolved findings, and a matching contract fingerprint. The maintainer sets Ready for all issues until the Risk field exists; whether the author agent may set it for Low-risk issues after that field is introduced remains open (§7.1, §21). |
| **In Progress** | After the maintainer has set Ready and directed work, the author agent runs `basectl gh issue start <N>` without `--no-project`. If evidence later regresses while that work remains authorized (for example, a PR returns to draft), the author agent records In Progress with the manual `set-fields --status` command. If `github-project-automation` sets In Progress after a linked PR opens before the issue-start command ran, the Stage 1 pilot records a process miss: the start step was skipped. |
| **In Review** | The author agent records it with `basectl gh project issue set-fields --status` when every planned slice has a non-draft PR or reviewable non-PR evidence. A possible but unobserved edge case is a new linked PR moving an already In Review issue back to In Progress; the maintainer restores In Review when the evidence still satisfies this rule. |
| **Done** | The maintainer closes the issue only after every slice is merged or has an explicitly approved terminal disposition and required evidence is recorded. Since close-trigger automation can set Done regardless of close reason, the maintainer verifies the reason and resulting Status. |

**Work without a PR.** A slice may omit a PR only if it changes no repository content. The issue plan names the reviewable evidence and its acceptance owner. After the maintainer sets Ready and directs the work, the author agent runs `basectl gh issue start <N>` to record In Progress. The author attaches the evidence to the issue, answers reviewer findings through the same bounded review loop, and records In Review when every planned slice has reviewable evidence. The maintainer accepts the evidence and closes the issue as Done, or records an approved terminal disposition. Any repository change requires a PR.

**After the reconciler exists — PROPOSED; writer ownership remains open.** The reconciler may become the sole automatic writer of derived In Progress, In Review and Done, but the reconciler design (O15) must decide the owner of each transition and the disposition of each current writer before implementation. Triage and Ready continue under the manual ownership rules above, subject to the open Low-risk Ready question. The start command may record a start event/request instead of writing Status if that design is approved. No `project-intake.yml` Status write or built-in Project workflow is disabled until its behavior, migration and rollback are verified and the maintainer approves the writer map. Keep manual `set-fields --status` as a maintainer-only, audited override. If Stage 2 Status reconciliation is rolled back, restore the manual process with `project-intake.yml` and the built-in Project workflows running, then audit their transitions against the manual ownership table.

| Evidence across all planned slices after implementation starts | Derived issue Status |
|---|---|
| At least one slice is being implemented, has a draft/not-ready PR, or has no reviewable evidence yet | **In Progress** |
| Every slice has a non-draft PR or reviewable non-PR evidence, and no slice is blocked by an unresolved closed-unmerged PR | **In Review** |
| Every slice is merged or has an explicit maintainer-approved terminal disposition and all required evidence is recorded | **Done** |

A closed-unmerged PR does not complete its slice. The maintainer records superseded, replanned or cancelled. If replacement work is planned, the author agent records In Progress with `basectl gh issue start <N>` while the original maintainer Ready authorization remains current, until the replacement PR is ready or its non-PR evidence is reviewable. An issue may return to Backlog only from Triage when the maintainer defers analysis; it never returns from Ready, In Progress or In Review. Abandoned work is closed as Not planned. A Done issue whose PRs merged is never reopened or moved back; later work gets a new linked issue.

### 5.3 Completion and later work — DECIDED

An issue is closed as completed only after every slice meets §5.2. New work discovered during implementation is a new issue unless it is a necessary correction to approved acceptance criteria; material corrections return the issue to Triage. GitHub close reasons are Completed, Not planned and Duplicate; cancelled is a slice disposition, not a GitHub close reason.

### 5.4 Returning to Triage — DECIDED

Changing Problem, Expected behavior, Scope and non-goals, Approach, Rejected alternative, Risks, a delivery-slice identifier or outcome, or current Type invalidates Ready and returns the issue to Triage. If implementation has started, associated PRs return to draft while the revised issue contract is reviewed; they resume only after a maintainer restores Ready. New affected areas or document destinations are recorded in the PR impact matrix and verified without changing the fingerprint. Comment replies and machine-owned activity also do not change it. A maintainer may return an issue to Triage when evidence materially changes the approved contract.

## 6. Issue review loop

### 6.1 Roles and reviewer independence — DECIDED

An issue author/planner and reviewer are separate agents. The reviewer starts a genuinely new session with no access to the author's transcript, session state, or persistent authoring memory. It reads only the issue, the repository and code relevant to the issue, the active decisions, and the repository's review rules. A fork or subagent inheriting the author's context is not independent.

`governance.reviewer_independence` controls whether the tools must also differ: `fresh-session` or `different-tool`. The nine Base ecosystem repositories listed in §1.2 default to `different-tool`; `banyanlabs` uses the Base-supported-project default, `fresh-session`, so a single-tool team can participate. Every verdict records author and reviewer tool, model, and session identifiers. If `different-tool` is configured and that tool is unavailable, the review waits or escalates to a maintainer; it never falls back to the same tool. A fresh session reduces anchoring on the author's reasoning; a different model can also reduce shared model blind spots.

### 6.2 Issue loop — DECIDED

1. The planner completes the issue contract and slice plan in Triage.
2. A separate reviewer evaluates scope, acceptance criteria, impact map, evidence, security, risk, existing decisions, and contradictions.
3. The author replies to every finding with a fix/evidence or a challenge and rationale.
4. The reviewer verifies each response. It marks a finding addressed only when its evidence is sufficient; disputed findings go to the maintainer.
5. The reviewer posts new findings discovered during revision. The author responds and the loop continues.
6. Count the initial evaluation as round one. Stop after the repository-configured limit (default three); remaining findings go to the maintainer. No timeout or exhausted limit implies approval.
7. Only a current approved verdict allows Ready. A material contract change restarts approval.

### 6.3 Verdicts and staleness — DECIDED

The verdict names the contract fingerprint, reviewed issue Type, result, findings, author/reviewer provenance, and date. It becomes stale when a fingerprinted contract section or current Type changes. Source evidence is not part of the fingerprint: a reviewer or maintainer records whether new evidence materially changes the approved contract or plan, and §5.4 governs a return to Triage. The Ready freshness period defaults to 30 days and is configurable in the repository manifest. Pure metadata/comment edits do not stale it.

### 6.4 Ready approval — DECIDED

A maintainer owns the Ready transition during the manual pilot and sets it for every issue until the Risk field exists. Agents record Triage, In Progress and In Review only as authorized by §5.2; they do not set Ready, Done or overrides. Whether an author agent may set Ready for Low-risk work after the Risk field is introduced remains open (§7.1, §21). Later automation may apply the same deterministic gate after its writer is decided. A changed contract or expired approval returns to Triage; being Ready is never inferred from the absence of comments.

## 7. Risk tiers and priority

### 7.1 Risk tiers — PROPOSED

Use **Low, Medium, High** to choose review intensity and maintainer involvement. A new Project Risk tier field is required; it does not exist today. The initial field proposal has plain-language descriptions and examples, and the planner proposes a tier from blast radius and reversibility. Reviewers may raise it; only a maintainer may lower it. The maintainer sets Ready for every issue until the Risk field exists. When it is introduced, whether the author agent may set Ready for Low-risk work after a current Ready verdict is an open decision (§21). Do not add per-area minimum tiers until the field is live and pilot data shows those floors are useful. The new field and its migration are a separately sized package.

### 7.2 Priority — DECIDED

Use **P1–P4** only for scheduling urgency: P1 urgent/highest, P2 high, P3 normal, and P4 lowest/opportunistic. These values create no response-time or service-level promise. The current Project uses P0–P3; package 8 migrates it one step (P0→P1, P1→P2, P2→P3, P3→P4), preserving meaning and recording before/after counts. The live Project field is authoritative; old Priority prose remains historical.

### 7.3 Priority and risk are independent — DECIDED

Priority describes when work should happen; Risk describes review and safety treatment. A P4 may still be High risk, and a P1 may be Low risk. Neither field is copied to PRs.

## 8. Pull requests

### 8.1 Issue-to-PR relationship — DECIDED

Every PR belongs to exactly one issue and declares one planned slice. One PR per issue remains the normal case. An approved issue may have several PRs when its plan enumerates the slices and evidence. A PR must not silently introduce unplanned scope.

### 8.2 Linking — DECIDED

For a single-PR issue, use `Fixes #N`. For a multi-PR issue, every PR uses `Part of #N`; none uses `Fixes`, because an early merge must not close the issue while other slices remain. The maintainer closes the issue when all slices satisfy §5.2; later automation may do so. A superseding PR links the same issue and slice and states which earlier PR it replaces.

### 8.3 Draft and review state — DECIDED

A draft PR is implementation in progress. It does not count toward In Review. The issue moves to In Review only when every planned slice has a non-draft PR or reviewable non-PR evidence, or is already merged. If a PR is converted back to draft or its evidence otherwise regresses, the author agent records In Progress under §5.2 while the maintainer's original Ready authorization remains current. The separate Project queue remains the canonical maintainer view; PRs are not Project items.

### 8.4 Pull request template — DECIDED

Use one PR template with these sections: Summary; linked issue and slice; plan/acceptance trace; the impact-and-evidence matrix using exact §12.10 categories; risk, rollback and notes; and a release-note entry or reasoned none. Category 6 carries validation commands/results and test exclusions, so it does not create a second validation section. Decision records, demos/examples, docs and the current .ai-context transition are handled in the common matrix. Do not ask authors to copy Project fields from the linked issue.

The current .github/pull_request_template.md already asks for issue linkage, validation commands, tests, bug regression proof, documentation, AI-context disposition, demo impact and release-note linkage. Keep those useful checks in the revised sections; replace the old Closes-only wording with the single-issue Fixes #N or multi-PR Part of #N rule. Until the context replacement ships and tracked .ai-context is removed in separate trains, retain an explicit impact disposition for it. The generator/CLI PR-body contract in base_manifest.yaml must converge on the same required sections.

### 8.5 Review comments, responses and approval freshness — DECIDED

The reviewer posts actionable findings as review threads. The author responds to every thread with a fix/evidence or a challenge and rationale. Once the reviewer verifies a fix, the reviewer replies exactly: Fixed at <full-head-SHA>. Only after that confirmation may the author agent resolve the thread. The author must not resolve an unconfirmed finding. If the reviewer withdraws a finding, the reviewer replies: Withdrawn at <full-head-SHA>: <reason>. The author may resolve it after that explicit withdrawal. The maintainer resolves directly only when overriding a finding and records the rationale. Unresolved disputes go to the maintainer.

During the 1.11 foundation pilot, author and reviewer agents act through the shared maintainer account `codeforester`; GitHub cannot distinguish which agent replied or resolved a thread. Beginning in Stage 1, the reviewer App has a distinct identity, while the author agent and maintainer still use `codeforester`. GitHub can therefore attribute reviewer confirmations to the App, but it cannot distinguish an author resolution from a maintainer override. The maintainer audits that each author resolution follows the App's `Fixed at` or `Withdrawn at` confirmation. The reviewer verdict includes `Verdict: Approved at <full-head-SHA>` plus author/reviewer tool, model and session. A new code push needs fresh review at the new head. A base-only update may get full-head re-verification without consuming a round only when all checks pass: (1) `git range-diff`, using recorded old/new base and head SHAs, shows each non-merge PR commit unchanged; (2) each introduced merge commit is a base-update merge on the PR's first-parent chain and its second parent is an ancestor of the updated base; and (3) `git show --remerge-diff <merge-commit>` is empty for each such merge. Any other merge, uncertainty, hand-written conflict resolution or code change requires a full review round. Record re-verification and evidence separately from the round ledger.

### 8.6 Merge gate — DECIDED

Required approving reviews remain **0** during Stage 1 because the reviewer App is comment-only. Do not use formal App APPROVE or REQUEST_CHANGES reviews until a ruleset test and a new maintainer decision establish their behavior. The maintainer checks the current-head verdict, every finding response/resolution, required checks, documentation impact and any escalations, then performs the merge. No agent merges or enables auto-merge. Required conversation resolution should be enabled through a separate, reviewed branch-policy change; until that change is live, it is a manual gate rather than an asserted GitHub enforcement. The required approval count must not be raised as a substitute.

### 8.7 Project fields and linked PRs — DECIDED

Issues are the canonical Project items for Status, Priority, Size, Area, Risk tier, and Initiative. Milestone is native issue metadata, not a Project field to copy. Do not create PR Project items or copy issue fields onto PRs. Use GitHub's native linked-pull-request view and issue relationships. A PR retains its title, author, branch, checks, review state, slice identifier and release evidence.

## 9. Reviewer rule sets

### 9.1 Issue reviewer — PROPOSED

The issue reviewer checks the current Type and contract, testability, delivery slices, documentation dispositions, security/privacy, risk, current docs and decisions, and consistency with the repository's product principles. It cites evidence and assigns each finding an identifier and severity.

### 9.2 PR reviewer — PROPOSED

The PR reviewer checks the issue and slice, changed code and tests, documentation and decision fold-back, release-note line, security, and validation evidence. Changed paths may trigger specialist passes, but they produce one consolidated review and share one round count. The verdict must include the reviewed head SHA and provenance. A fresh-session reviewer is mandatory; `different-tool` applies when configured.

### 9.3 Review discipline — DECIDED

Findings state the observed condition, evidence, consequence and requested outcome. The author replies in each thread. The reviewer verifies; when fixed, it posts Fixed at <full-head-SHA>, after which the author resolves. When the reviewer withdraws a finding, it posts Withdrawn at <full-head-SHA>: <reason>, after which the author may resolve. The author never resolves an unconfirmed finding. Only the maintainer resolves directly when overriding, with a recorded rationale. Resolution is not a substitute for evidence. Disputes and exhausted rounds go to the maintainer.

### 9.4 Coding and architecture standards — DECIDED

Existing language-specific and architectural rules remain in their canonical standards documents. Review prompts link to those sources; they do not copy mutable standards into every issue or PR.

## 10. Metadata: fields, areas, initiatives, labels and relationships

### 10.1 GitHub metadata responsibilities — DECIDED

| GitHub feature | Canonical purpose | Base use |
|---|---|---|
| **Issue Type** | Classifies the kind of work | Native `Task`, `Bug`, `Feature` today; assess any additional types only through a separate migration. |
| **Project fields** | Operational tracking across issues | Status, Priority, Size, Area, Initiative, and proposed Risk tier. Issues remain the Project items. |
| **Issue Fields** | Organization-level structured metadata, where configured | Not a second copy of Project fields. Revisit only through a dedicated migration with a source-of-truth and retirement plan. |
| **Labels** | Cross-cutting tags and repository workflow signals | Current category labels drive branch policy; other labels such as `good first issue` and `help wanted` remain plain labels. |
| **Milestone** | Release planning | Native issue milestone; not copied to PR Project fields. |
| **Relationships** | Work hierarchy and dependencies | Use sub-issues for real decomposition and native blocked-by relationships for dependencies; do not use labels as a substitute when native relationships fit. |
| **Linked PRs** | Delivery navigation | Native issue-to-PR relationship; no issue fields copied onto the PR. |

### 10.2 Field meanings and current schema — DECIDED

| Field | Current/target state | Meaning |
|---|---|---|
| **Status** | Current Project field; target order changes | Work lifecycle and ownership defined in §5. |
| **Priority** | Current Project field; target P1–P4 migration | Scheduling urgency, independent of risk. |
| **Size** | Current Project field | Relative implementation effort. |
| **Area** | Current Project field; redesigned in package 22 | Product/ownership surface. Shared defaults are in cli/python/base_github_projects/project_model.py; repository-specific additions and issue defaults are in .github/base-project.yml. |
| **Initiative** | Current Project field | A multi-milestone effort with a durable initiative document. |
| **Risk tier** | Does not exist today; proposed new Project field | Low/Medium/High review and safety intensity. |
| **Milestone** | Native issue milestone | Repository-local release or planning window. |
| **Issue Type** | Native issue Type: Task, Bug, Feature | Classifies work; it is not a category label. |

Package 22 remaps Area options in the 1.11 foundation before package 8 migrates the Base Project schema in 1.12. Package 8 inventories the Base Project template and live items; the independent Priority/Risk slice may happen first. Complete package 25 (#2671) before changing Status order in #2672. For each migration, record a reversible before-state and counts; never copy issue fields to PRs. The organization-level Issue Fields feature is not a duplicate source for Project fields.

### 10.3 Areas, labels, and views — DECIDED

Today, cli/python/base_github_projects/project_model.py defines shared defaults and Area options; .github/base-project.yml adds repository-specific Areas and Initiatives and issue defaults. Live Projects are inventoried before migration. Do not create duplicate governance/areas.yaml or initiatives.yaml catalogs. Package 22 proposes one Area vocabulary, one-line purposes and a path map before changing values.

**Flat labels and migration.** Labels are plain cross-cutting tags, not encoded fields. Do not encode fields or sub-fields with prefixes or separators such as type:, area: or kind/. Plain-language labels such as needs decision, needs design and good first issue remain valid. Retire the old type:* and area:* labels only after setting an appropriate active native field on each open issue. Map type:feat to Feature; type:fix to Bug; type:chore to generic Task; and type:docs to generic Task because GitHub has no Documentation Issue Type. Retain the separate documentation category label where applicable. If a valid Type is already set and conflicts, do not overwrite it automatically: keep the label and send the issue through human Triage.

Map area: docs to the current Area Docs and area: runtime to Runtime. There is no current Area named Release or Community, so area: release and area: community have no automatic mapping. Keep those labels and current Area values on open items until package 22 supplies an approved active option or a maintainer selects an existing valid Area with a recorded rationale. Then remove the legacy label. Stop assigning retired labels, remove them from open issues after mapping, and preserve their associations on closed issues. Do not delete a repository label if that erases closed-issue history.

Project field-option retirement is separate: first move every open item carrying the old option to an active option. Prefer keeping the unused option as retired; if deleting it is necessary, export and preserve the item/value mapping first, and state that GitHub clears the option from both open and closed items. A value remap such as P0→P1 is a migration, not retirement. Before deleting any Project option, verify the backup and rollback map.

Dependabot's generated python:uv label is not an exception to the flat-label rule. Override it in base-cli/.github/dependabot.yml with the existing plain dependencies label; verify that config in its own migration.

**Escalation label and view — PROPOSED.** Use the plain `needs decision` label only for maintainer escalation. Issue-loop exhaustion/dispute applies it to the issue. PR-loop escalation applies it to the PR and linked issue. Remove it when the maintainer decides. The shared Project template includes a view filtered to this label and showing Status; `basectl setup` adds the view to existing Projects, including Base Project #10. GraphQL `CreateProjectV2ViewInput` has no filter field, but `UpdateProjectV2ViewInput` accepts `filter` and `ProjectV2View` exposes it for readback. Setup should create the view, set `label:"needs decision"` with `updateProjectV2View`, then read the filter back. The implementing package tests this sequence on a scratch Project before changing Project #10; use the Project UI only if testing shows the API update does not take effect.

**Relationships and hierarchy.** Use native blocked-by relationships for dependencies and sub-issues only for real decomposition. Base Foundry guidance permits at most one parent/child level and no grandchildren; this is guidance only, with no enforcement check and no Base-supported-project default. Public support intake remains distinct from the internal Triage status.

## 11. Decision records

### 11.1 Format and ownership — DECIDED

Use lightweight Architecture Decision Records (ADRs): one durable decision per record, with context, decision, rationale, serious alternatives, consequences, status, area, date, originating issue/PR and affected design documents. The proposed home is `docs/decisions/`; confirm the exact directory and index during the documentation inventory package.

### 11.2 Lifecycle — DECIDED

- A record in an open PR is **Proposed** and does not authorize implementation.
- A maintainer explicitly accepts it during review. The same PR changes it to **Accepted** before merge; merge activates the decision.
- Accepted content is immutable. Correct a typo without changing meaning; a substantive change creates a new record linked to the prior one. Only the old record's status and successor link may change.
- A rejected or abandoned proposal is preserved as **Rejected** only if a maintainer accepts that historical record in a merged PR. An unmerged PR is not an archival record.
- If a decision must be settled before implementation, use a decision-only issue/PR first. A generated index links active and historical decisions.

This is a common ADR pattern, not a universal industry standard. Fowler, MADR and AWS guidance use proposed/accepted/rejected or superseded states and preserve accepted records; GDS allows acceptance to be inferred from merge. Base chooses explicit maintainer acceptance in the same PR so the human decision is visible and reviewable.

### 11.3 Decision/document impact gate — DECIDED

The issue plan says whether the change introduces, alters, or supersedes a durable decision. The PR includes the record when acceptance and implementation are coupled, or links the earlier accepted record when implementation follows. The reviewer checks its status and all affected documentation categories. An ADR explains why; area design and user docs state current behavior.

### 11.4 Decision capture — DECIDED

When a conversation reaches a durable product or governance decision, the agent asks: **“This looks like a decision. Should I record it in [document]?”** At the end of a session that produced durable decisions, list any that remain unrecorded and the reason. Before changing an area, read its active decision records and current design document. The issue/PR train remains the approval path; the prompt is a capture aid, not authority to commit policy.

### 11.5 Existing decision material — DECIDED

Package 10 (#2675, in the 1.11 foundation) inventories document locations. Package 23, a new Step 5 issue, reorganizes the documents and identifies durable-decision candidates; it does not perform the ADR migration and does not depend on #2666. Package 1 (#2666, Stage 1 in 1.12) establishes the ADR template/index and migrates maintainer-approved durable decisions with source links and status. Until that migration is accepted and merged, keep .ai-context/DECISIONS.md maintained as the current decision list. Preserve provenance and do not turn transient discussion into policy. Other tracked .ai-context files remain until the replacement export ships and is proven (§12.9).

## 12. Documentation design

### 12.1 Why this shape — DECIDED

The old waterfall chain (user requirements, then high-level design, then detailed design) was written once, signed off, and abandoned while the code moved on. Agile cut most of it, sometimes too far. What survived and improved: docs as code, decision records (2011), Diátaxis (~2017), and arc42 and C4 for living architecture. Detailed design moved into code, types, tests and comments, which is current best practice.

Base's design maps onto that:

| Old document | Base equivalent |
|---|---|
| User requirements | The PRD |
| High-level design | Area design docs, one per area |
| Detailed design | Code, tests and comments |
| (none) | Decision records, generated reference, Diátaxis-style guides, generated release notes |

Every individual piece is mature and widely used. What's new, and has to be proven, is the glue: areas as the single backbone, file-to-area mapping, and fold-back enforced on every PR. If the glue fails, a conventional documentation system remains underneath.

### 12.2 Kinds of documents — DECIDED

Sorted by **who may change it** and **how it stays true**. Adapted from Diátaxis (tutorials, how-to guides, reference, explanation).

| # | Kind | What it holds | Who changes it | How it stays true |
|---|---|---|---|---|
| 1 | **Intent (PRD)** | Problem, who it's for and not for, principles, non-goals, major capabilities, success measures. One per product. | Ramesh only. Agents propose. | Ramesh's review; High risk; size check |
| 2 | **Design docs** | How one area works and what it promises. One per area, common template. | Agents draft; Ramesh approves. | Fold-back in every PR; reviewer; drift check |
| 3 | **Decision records** | Why a choice was made. Short, numbered, frozen once merged. | Agents draft in the same PR; frozen on merge. | Freeze check; generated index |
| 4 | **Reference** | Commands, options, manifest fields, config samples. | Nobody by hand. | Generated from code wherever possible |
| 5 | **User guides** | Getting started and task how-tos, by area. | Agents write. | Examples are tested |
| 6 | **Generated artifacts** | Release notes in `CHANGELOG.md`; exported AI context outside the repository. | Release notes are reviewed in-repository; context output is generated outside the repository. | Release entries come from merged PR release-note lines; context is generated from allowlisted sources |

**Outside the six:**

- **README:** the front door (§12.4).
- **Process docs** (GitHub workflow, release process, testing policy): belong to the governance area.
- **Code comments:** the non-obvious "why" at that spot only.
- **Issues and PRs:** the history of the work, never the source of current truth.

### 12.3 What links to what — DECIDED

**Links point up, toward the why, and down, toward the details. Each fact lives in one place.**

- **PRD** (top): links down to each area's design doc.
- **Design doc:** links up to the PRD lines it serves, sideways to the decision records that shaped it, down to the reference for its commands.
- **Decision record:** links to the design doc it affects and the PR that made it.
- **User guide:** links to the reference for exact details instead of repeating them. Rarely links to design docs; users want how, not why.
- **Reference:** the bottom layer, generated. Links to nothing.

Two paths: the **user path** is guide → reference; the **builder path** is PRD → design doc → decision records. The area ties both together.

### 12.4 README — DECIDED

**Its job is to orient and route, not to explain.** Four questions, in order:

1. **What problem does this solve?** Problem first, before any install command.
2. **Is it for me?** Who it's for and not for. Non-goals help.
3. **How do I try it?** The shortest path to a first success; points to the installation chooser.
4. **Where do I go next?** User guide, reference, design docs and PRD, release notes, contributing.

- **Must not contain:** full command lists, architecture explanations, feature tours. They have homes elsewhere; copying them is how READMEs go stale. Today's long command overview is an example to remove.
- **Protection:** belongs to the intent layer with the PRD; owned by Ramesh; any change is High risk. Small parts are generated (current version, latest release link). Quick-start commands are tested.

### 12.5 PRD — DECIDED

- **One PRD per product, a single short document** (about four to six pages, readable in fifteen minutes). No hierarchy: the area design docs already are the hierarchy below it.
- **Fixed sections:** the problem; who it's for and not for; principles; non-goals; major capabilities (roughly one per area); how success is measured.
- **What vs how:** the PRD says what and why at product level ("workspace commands never run untrusted code"). The design doc says how one area achieves it ("the trust preflight checks every selected project before running any") and links up to the PRD line instead of restating it. The reviewer flags restated PRD statements.
- **Safety valve:** a check flags the PRD if it passes the size limit. The first response is to move detail down into design docs. Only if it is genuinely all intent and still too long does it become a small folder, one file per section.
- Today's `docs/product-requirements.md` is the starting point. Ramesh reads it against his own intent before migration; until now, AI passes have checked docs against code, but nobody has checked them against him.

### 12.6 Area design doc template — DECIDED (to revisit in use)

Living documents: they describe **how an area works today**, only what is implemented. Based on **arc42**, trimmed to eight sections. Every section is always present, with "None" plus a reason where it doesn't apply.

| # | Section | Content |
|---|---|---|
| 1 | **Purpose** | What the area is responsible for; links up to the PRD lines it serves. |
| 2 | **Boundaries** | What is in and explicitly not in the area; which neighbouring areas own the rest. |
| 3 | **Concepts** | Key terms and ideas needed to understand the area. |
| 4 | **How it works** | Main flow and important parts, at design level, not code. |
| 5 | **Contracts** | What other areas and users rely on: commands, file formats, outputs, exit codes. Lasting "When …, then …" promises land here. Links to the reference instead of repeating it. |
| 6 | **Decisions** | Links to the decision records that shaped the area, each with a one-line summary. |
| 7 | **Known limits and open questions** | What doesn't work yet; what's undecided. |
| 8 | **Testing** | How the area's behavior is verified and where the tests live. |

- **No "alternatives considered" section.** Rejected alternatives live permanently in decision records. That's the improvement over the Google-style design doc, which describes a proposal and goes stale.
- **The key line is between How it works and Contracts.** "How it works" may change freely during refactors. A change to "Contracts" means something others depend on is changing: at least Medium risk. That lets risk tiers tell a refactor from a breaking change.
- The same template serves a small area and a large product; only the depth changes.
- Proposed location: `docs/design/<area>.md` (**NEW**, B13). Today's `docs/architecture.md` becomes a short overview linking to the area docs, or is absorbed during migration.

### 12.7 User guides, installation and FAQ — DECIDED

- **User guides** are organized by area: getting started and task how-tos. Their examples are tested.
- **Installation** is the first section of the user guide. A short chooser at the top, then one page per path:
  - **Cold start:** the bootstrap script on a brand-new machine.
  - **Homebrew:** for machines already set up.
  - **Source checkout:** for contributors.
  The README's quick start points to the chooser, so install commands live in one place.
- **FAQ:** not a separate kind of content. A short index of common questions, each answered in one or two sentences plus a link to the real home.
  - Audience: people **using or choosing** Base. If only a contributor would ask it, it belongs in a design doc or decision record.
  - Two kinds: user questions (link to the user guide); evaluator questions such as how Base differs from adjacent tools (link to the why-Base page).
  - A recurring question is a signal the guide is unclear: fix the guide, keep the FAQ pointing there.

### 12.8 Reference and release notes — DECIDED

Command, option, manifest, configuration and JSON reference should be generated from authoritative help, schemas or code where practical. Until a generator exists, each PR verifies reference changes against shipped implementation.

The existing basectl release notes --version <version> command is read-only: it prints/extracts the existing changelog section for that version. It does not assemble or write CHANGELOG.md. Package #2670 adds a separate assembly mode using reviewed PR release-note entries. Keep PR-entry validation (#2572), release completeness (#2670) and decision-link checking (#2679) distinct. Release preparation may improve wording but cannot invent unrecorded changes. Every implementation PR supplies a user-facing release-note line or a reasoned none.

### 12.9 AI context — DECIDED

**Current contract.** basectl export-context [project] reads the selected project's tracked .ai-context directory and bundles it as Markdown or ZIP. It supports --project, --workspace, --format, --output, --print and --list-files; by default it writes under Base's cache root. Today --output may point inside a project. It does not invoke an AI CLI to generate a summary.

**Target contract after all four governance stages.** Packages 13–14 (#2686–#2688 and consumer trains) are targeted after 1.15, with generation targeted for 1.16.0. It invokes only a user-selected, installed AI CLI to summarize allowlisted canonical repository documents; writes to an explicit export location outside the repository; identifies source commit, date and paths; flags contradictions; excludes secrets and unapproved files; and fails clearly if the tool is unavailable or output points inside the repository. Base does not call provider APIs directly or manage provider credentials. Supported tools/flags, consent, disclosure, privacy/data transfer, offline/failure behavior and source selection require a separate implementation issue and threat review.

Do not change the current bundle behavior until the replacement is implemented, released and proven. Keep .ai-context tracked and maintained, including its PR impact disposition and current export flow. Only then remove the tracked files and update references/scheduled exports in separate repository trains; cleanup follows the release, never the same release that introduces replacement. Generated output is disposable and stays outside the checkout.

### 12.10 Documentation impact and drift checks — PROPOSED

The issue and PR use one ordered list. Each category names canonical destinations or states No impact with an evidence-based reason. These are impact categories, not a demand that each change edits every document.

1. **Product intent:** PRD, principles and non-goals.
2. **Architecture and contracts:** area designs and behavior promises.
3. **User guidance:** README, getting-started guide, FAQ and task guides.
4. **CLI/API and reference:** commands, options, manifest/config schemas, generated reference and compatibility notes.
5. **Operations and safety:** security, privacy, trust, release, migration, support and rollback.
6. **Validation and testing:** tests/fixtures, acceptance-to-test mapping, test/CI policy, commands/results and evidence-based exclusions.
7. **Examples and downstream use:** demos, samples and Base-supported consumer guidance.
8. **Governance and contributor process:** issue/PR templates, contribution/review instructions, maintainer procedure and .ai-context while tracked.
9. **Decision records:** new, changed or superseded ADRs and index.
10. **Release notes:** a user-facing PR line or reasoned none; accepted lines are checked and assembled during release preparation.

Current-practice crosswalk for the planned migration:
| Current source | Keep / revise / retire | Destination and useful requirement retained |
|---|---|---|
| .github/ISSUE_TEMPLATE/bug_report.yml | Revise | Fold version, environment, reproduction, expected/actual behavior and secret-redaction guidance into Problem/evidence. |
| .github/ISSUE_TEMPLATE/feature_request.yml | Revise | Fold user problem, desired outcome, alternatives and context into the one planned-work form. |
| .github/ISSUE_TEMPLATE/implementation.yml | Revise | Map Goal, Background, Scope, Acceptance Criteria, Validation and Non-Goals to the common form and readiness check. |
| .github/ISSUE_TEMPLATE/documentation.yml | Revise | Retain location, reader problem and proposed correction in Problem, impact and Plan. |
| .github/ISSUE_TEMPLATE/support.yml, template config.yml, private advisory route | Keep separate | Preserve public support and private vulnerability intake; neither is internal issue Triage. |
| .github/pull_request_template.md | Revise | Retain issue/slice, validation, tests, regression proof, docs, AI-context disposition while tracked, demo impact and release-note evidence in the common sections. |
| STANDARDS.md | Keep | Remains the normative contributor standard; link it from issue/PR review rules. Do not create governance/standards/. |
| CONTRIBUTING.md, AGENTS.md, docs/github-workflow.md, docs/contributor-first-change.md | Revise links, preserve useful instructions | Point to one current workflow and canonical standards; do not duplicate mutable policy. The external contributor flow remains accessible and need not use maintainer-only commands. |
| docs/community-triage.md, docs/community-support.md | Revise after #2671 | Keep public intake distinct; document handoff and public term after the issue decides it. |
| README and current docs guides/reference | Revise during inventory | Preserve user orientation, tested quick start and existing command behavior; move content only through the inventory/reorganization train. |

The first drift-check design is per document kind: intent is reviewed against the PRD; README quick-start commands are tested; design/contracts are compared with changed code/tests; ADR status/index is validated; reference is checked against schemas/help; guide examples execute; FAQ links are checked; release-note completeness is compared with merged PRs; and context exports use allowlisted sources. Findings cite evidence and become issues; checks never rewrite policy silently. Until automation exists, the PR reviewer performs the same checks manually.

### 12.11 When code and docs disagree — PROPOSED (from Codex's 1.11 draft)

- **Which source is authoritative for what:** code and tests for what the current build does (schemas and command definitions for exact fields and options); user docs for what users may rely on; area design docs for the implemented architecture; decision records for why; issues and PRs for how the work happened; the changelog for what a release contains.
- **Classify the mismatch first:** is the code wrong, is a document stale, or was the design deliberately changed? Then fix it in the same PR: fix the code, update the docs, add or replace a decision record, adjust tests.
- **If a known gap must ship,** open an owned follow-up issue that names the affected audience, the risk and the target release, so the gap is visible.
- **Never present a proposal as the implemented system.** Proposed designs are labeled as proposed.

### 12.12 Versioned docs — DEFERRED

Whether users of an older release see the docs for their version. Revisit when Base has more users.

### 12.13 Interim document homes and ownership — DECIDED

Until package 10 (#2675) completes the 1.11 inventory and package 23's approved reorganization, existing files remain the canonical homes. Update the current home in the same PR; do not move or duplicate content just because a target home is proposed.

| Document kind | Current/interim home | Ownership and next step |
|---|---|---|
| Product intent | docs/product-requirements.md | Maintainer owns intent; reviewers check changes against it. |
| Architecture overview and current contracts | docs/architecture.md and area-specific docs | Area owner keeps implemented behavior current; target area documents are inventoried before migration. |
| Governance design/plan | docs/governance/DESIGN.md and IMPLEMENTATION-PLAN.md | Maintainer owns governance decisions; each change has its own issue/PR. |
| Normative contributor rules | STANDARDS.md, CONTRIBUTING.md, AGENTS.md | STANDARDS.md remains normative; the other files link to the canonical rule and workflow. |
| Contributor/agent map | #2681 and this §0 summary | Reconcile #2681's current METHOD.md request in its own issue train; the delivered map links to this summary rather than adding a separate method document. |
| User guides and public support | README.md, docs/* guides, docs/community-support.md, docs/community-triage.md | Area owner maintains tested guidance; public support terms wait for #2671. |
| Command/config reference | docs/command-reference.md and authoritative CLI/schema | Code/schema is exact behavior; reference is verified/generated as described in §12.8. |
| FAQ | No standalone canonical FAQ file is established today | Inventory decides whether a separate FAQ is needed; until then, answer in the user guide and link to that source. |
| Decision records | .ai-context/DECISIONS.md until #2666; proposed docs/decisions/ afterward | package 23 identifies durable-decision candidates; #2666 establishes the template/index and migrates approved decisions. |
| Release notes | CHANGELOG.md and PR release-note entries | PR line is reviewed evidence; #2670 adds assembly without changing the current read-only command. |
| Generated AI context | Tracked .ai-context/ until the post-1.15 replacement ships | Maintain current files/checklist until replacement is released and proven; exports then stay outside the repository. |

## 13. Identities and attribution

### 13.1 Human-operated pilot — DECIDED

During the 1.11 foundation, reviews use the shared maintainer account `codeforester` and declare author/reviewer provenance. Beginning in Stage 1 (1.12), a dedicated GitHub App identifies the reviewer role and posts comment-only reviews; the author agent and maintainer continue to use `codeforester`. Stage 3's hosted reviewer reuses the App. The App identity does not identify the model or session. Verdicts record author and reviewer tool, model and fresh-session identifiers, plus the issue fingerprint or full PR head SHA. A GitHub username is attribution only, not proof of which agent acted.

### 13.2 Git history and GitHub activity — DECIDED

Git author/committer identity follows repository contribution rules. GitHub comments and verdicts show the account or App. Do not imply that an account name proves which model or session produced a review.

### 13.3 Verdict provenance — DECIDED

Every verdict records author tool/model/session, reviewer tool/model/session, date, reviewed contract fingerprint or full PR head SHA, result and findings. The reviewer session is new and has no author transcript or persistent authoring memory; configured different-tool policy adds a distinct-tool requirement. Verdicts are declared evidence, not cryptographic attestation. During the 1.11 shared-account pilot, the maintainer audits provenance and the thread-resolution sequence. From Stage 1, the App identity separates the reviewer from the author/maintainer account, but GitHub still cannot distinguish author-agent activity from maintainer activity through `codeforester`.

## 14. Enforcement

### 14.1 Detect and correct, never silent — DECIDED

GitHub can't block a manual edit to an issue or Project field before it happens. Enforcement is a smoke detector, not a locked door:

1. **Event-triggered Action:** runs right after a change it can observe (issue closed, reopened, edited; PR events). If the change breaks a rule, it comments with the rule and the fix.
2. **Scheduled Action** (for example hourly): for changes Actions can't trigger on, likely Project field edits such as Status. Sweeps for violations and comments the same way.
3. Codex verifies which events GitHub Actions can trigger on for an organization Project, to decide what is instant and what is swept.

Rules enforced this way include: Done with an open linked PR; a Done issue with merged PRs reopened or moved back; a Status move with no matching signal; retired values on open items; a PR linked to zero or several issues.

### 14.2 Warn first, revert later — DECIDED

- The first automated enforcement rollout is **warn only**: the Action reports a rule violation and records the evidence; it does not revert or block.
- A rule may be promoted **per rule** only after its warnings prove accurate and the check runs from a pinned, released Base version (§14.4). A noisy rule stays warn-only until fixed.
- Why: automatically reverting a person's change goes beyond common practice and can feel heavy-handed; rules must earn it.

### 14.3 Override — DECIDED

An override is an explicit maintainer decision with a reason, scope, expiry or recheck condition, and linked issue/PR. During the manual stage the maintainer records it in the review thread or issue. Agents may explain a proposed exception but must not create, approve, or post an override as if it were a maintainer decision. Because the author agent and maintainer act through `codeforester`, GitHub cannot distinguish author-thread resolutions from maintainer overrides; the maintainer audits the actor sequence and evidence. The reviewer App is a separate identity from Stage 1 onward. Do not use an `override` label.

### 14.4 Pinned enforcement — DECIDED (Stage 2)

- Enforcement checks (readiness, PR checks, status rules) run a **pinned, released** version of Base from their first automated use, not whatever just merged to `main`. A bad merge can't break its own gate. The first rollout remains warn-only; blocking or reverting is a separate, evidence-backed promotion for each rule under §14.2.
- The pin is upgraded deliberately, after a release proves itself.
- Same idea as the second laptop running only released Base: the checker isn't the thing being changed.

### 14.5 Branch protection — DECIDED

On `main`: required status checks (Tests, Security scanners, `base/issue-branch-policy`, governance checks as they arrive); require conversation resolution after the separate branch-policy train enables it; no direct pushes; squash merge; required approving reviews remain 0 during Stage 1 because reviewer App reviews are comment-only. Formal App reviews require a ruleset test and a new maintainer decision. A human maintainer verifies the current-head verdict and resolved threads under §8.6.

### 14.6 Automated review and fix security — DECIDED baseline; proposed implementation architecture

Review content is untrusted by default. Issue text, PR descriptions, comments, diffs, test output, artifacts and generated context may contain prompt injection. No reviewer job executes PR-controlled code or gives the model general-purpose credentials. Never use `pull_request_target` or another privileged event to check out, execute, install or evaluate untrusted PR content. Security-sensitive changes and disputed findings require maintainer review; findings still unresolved at the configured round limit escalate to the maintainer. Automated fixes remain deferred under #2581; this design does not authorize them.

**Reviewer App baseline and observed limits.** The tested App is owned by basefoundry; the baseline is repository Contents read, Issues write and Pull requests write, plus GitHub's implicit Metadata read and no other granted permission. The tested installation was limited to private basefoundry/app-scratch, with webhooks off. Its installation token was limited to one repository and expired after one hour; the test could read public repositories and public Project #10 as an anonymous reader but could not write Project fields because it lacked Projects permission. See [Claude's scratch-App results on #2698](https://github.com/basefoundry/base/issues/2698#issuecomment-6973635209). These facts describe the test installation, not untested production setup.

With that baseline, the App can post issue/PR comments, edit its own comments, submit COMMENT reviews with inline findings, reply to review threads, and add/remove needs decision. It cannot resolve or unresolve review threads with these permissions. GraphQL viewerCanResolve returned false even when resolution succeeded after broader access; do not rely on this field. Adding Contents write allowed resolution, but also allowed code pushes and converting a PR to draft; therefore Contents stays read-only.

Reviewer credentials are not authorized to push code, change branch protection, approve the reviewer's own work, merge, release, or access deployment secrets. These are policy boundaries to test in addition to the observed App permissions; do not infer an untested capability from the scratch installation.

Any future automated-fix agent is also prohibited from approving its PR, resolving its own review threads, merging or releasing. Its patch must be reviewed independently at the exact patched head SHA; every new push invalidates the prior verdict and requires fresh review.

The App must not resolve findings. After it replies `Fixed at <full-head-SHA>`, the author agent resolves. After it replies `Withdrawn at <full-head-SHA>: <reason>`, the author may resolve. The author never resolves an unconfirmed finding. The maintainer resolves directly only when overriding a finding and records the rationale (§8.5). This is the maintainer-approved thread-resolution rule; it replaces the accepted-design sentence that gave the reviewer a pull-request permission to resolve threads.

**Proposed action broker.** The permission grants also technically permit editing issue/PR bodies, other users' comments, arbitrary labels, and opening/closing items. These are policy prohibitions, not GitHub permission boundaries. A narrow broker would expose only approved actions (comments, COMMENT review threads and `needs decision` add/remove), reject all other mutations, and emit an audit record for maintainer review. Baseline tests refused merge and push; merge with broader permissions was not tested.

**Stage 1 review mode — DECIDED.** The reviewer App posts comment-only reviews in Stage 1. Formal `APPROVE`, `REQUEST_CHANGES` or dismissal of the App's own review are not used until a ruleset test and a new maintainer decision establish their effect. The scratch test showed these formal operations are technically possible but did not test required-review/ruleset behavior.

The App operates as a dedicated reviewer for issue and PR loops beginning in 1.12, and is reused for the Stage 3 hosted reviewer. Installation is limited to the repository being reviewed. Until then, 1.11 review uses `codeforester` with declared provenance. If the App or a configured different review tool is unavailable, pause for it or escalate to the maintainer; do not fall back to the author session, a general workflow token, or a shared machine-user credential. The App is preferred to `GITHUB_TOKEN` or a machine-user account because it identifies the reviewer role and issues short-lived, repository-scoped tokens without Contents write. The scratch test did not compare operational security of these alternatives; that remains a rationale, not a measured result.

**Proposed credential and publisher architecture.** The App private key must not be present in the model/analysis job, repository, PR-controlled code, prompt, output or logs. Stage 1 local token minting is a maintainer operation through a narrowly scoped helper using protected local storage. For Stage 3, a separate trusted publisher job would obtain the key from protected Actions secret storage, mint a one-repository short-lived token, and pass it only to the action broker. The untrusted analysis job never receives the App key or write token. This storage/publisher architecture is not established by the scratch test; threat review, publisher permissions and token-delivery tests are required before Stage 3.

**Proposed provider gateway.** Hosted-model credentials are distinct from GitHub/App credentials. Provider keys would remain in a trusted provider gateway or protected secret store and would not be passed to PR code, arbitrary tools, test commands, artifacts or logs. The analysis agent would invoke a narrow model-call broker with least-privilege access; the broker would enforce provider, data-disclosure and retention policy and record usage without logging credentials. Fork PRs receive no secrets. If the approved provider cannot serve a fork without exposing credentials, skip automated review and wait for maintainer review or a safe explicitly configured provider; do not weaken isolation to avoid delay.

The scratch test did not establish required-review-rule behavior, private-key storage, Stage 3 publishing, provider credentials, fork behavior, the unavailable-App fallback, or a comparative test against GITHUB_TOKEN/machine-user accounts. Treat these as open implementation security gates, not verified capabilities. Pin workflow actions/tools where possible; cap usage; record actor, tool/model, commit SHA, prompt/rule version and outcome without storing secrets or unnecessary private data. No automated fix runs until a separate trusted trigger, isolated environment, no-secret/no-network policy (unless reviewed), patch validation, independent review and maintainer gate are approved.

## 15. Governance as code

### 15.1 Repository layout — DECIDED (details PROPOSED)

Use existing domain boundaries and keep one source for each setting:

```text
base_manifest.yaml             repository contract and small runtime settings
  github.pr.required_sections  GitHub PR contract (stays under github.pr)
  governance:                  loop limits, freshness, reviewer mode, review policy
.github/
  ISSUE_TEMPLATE/               GitHub's fixed-path issue intake surface
  pull_request_template.md      GitHub's fixed-path PR intake surface
  base-project.yml              repository-specific areas/initiatives and issue defaults
  base-review-policy.yml        legacy path during the documented migration window
governance/                     optional first-party policy content
  rules/                        issue and PR reviewer rule sets
  prompts/                       read-only audit/reviewer prompts
docs/governance/                human-readable design and rollout documentation
docs/decisions/                 proposed ADR home, pending inventory confirmation
docs/design/                    proposed area design docs
```

The `governance:` entry in `base_manifest.yaml` is actual configuration, not a pointer to another file. It holds small operational settings such as the independent loop limits, review freshness, reviewer independence and review-policy values. The existing `github.pr.required_sections` stays under `github.pr` because it is GitHub PR behavior. `cli/python/base_github_projects/project_model.py` defines shared default Project fields/options; `.github/base-project.yml` supplies repository-specific areas and initiatives plus issue defaults. The repository's extra areas extend the default Area list. These are distinct existing sources; do not duplicate them as `governance/areas.yaml` or `initiatives.yaml`.

For Base ecosystem repositories, use `governance/` to keep detailed human-maintained rules modular; GitHub-required files remain at their fixed paths and are hand-maintained until a separately justified generator exists. For Base-supported projects, a `governance/` directory is optional and not part of the minimum repository contract; ordinary settings can live in their existing `base_manifest.yaml`. Defaults arrive through an explicit versioned Base configure/upgrade PR, never live inheritance.

Move `.github/base-review-policy.yml` values into `base_manifest.yaml` `governance.review_policy` through a compatibility/deprecation issue, then remove the old reader after a documented transition. There are no known adopters today, but preserve the existing behavior until the change ships. `homebrew-base` receives a minimal `base_manifest.yaml` in its own Phase-1 repository train. No separate `base-governance.yml` and no `.base/` directory are introduced.

### 15.2 Phase-1 habits — DECIDED

1. Keep one canonical source for each value; do not create a second catalog while migrating.
2. Treat the manifest as the stable machine-readable entry point and keep rich rules in separate first-party files where that improves reviewability.
3. Do not call `.github/` files generated or forbid hand edits until a generator and drift check are implemented.
4. Keep Base-specific examples separate from defaults intended for consumers.
5. Document compatibility and deprecation before removing an existing config reader.
6. Keep method prose tracker-neutral; put GitHub endpoint details in the adapter and GitHub-specific docs.

### 15.3 AGENTS.md — DECIDED

AGENTS.md is a map, not a manual. It points to the issue-first process, plain titles, the active area design and decisions, the documentation-impact categories, coding standards, issue/PR reviewer rules, and the decision-capture prompt (§11.4). It states that agents record Triage, In Progress and In Review only as authorized in §5.2; they do not set Ready, Done or overrides, merge PRs, or silently choose an AI provider. It does not rely on a provenance footer.

### 15.4 Tracker neutrality — DECIDED

The issue contract, review loop, document-impact categories and decision lifecycle are tracker-neutral. GitHub-specific templates, fields, linked PRs and branch settings belong in an adapter. Other trackers are deferred until requested.

### 15.5 Repository-owned loop configuration — DECIDED

Repository-scoped `basectl config` reads/writes the tracked `base_manifest.yaml` and produces an ordinary diff. It must not confuse these settings with machine-local user configuration. The initial schema is:

```yaml
governance:
  issue_loop_round_limit: 3
  pr_loop_round_limit: 3
  ready_approval_max_age_days: 30
  reviewer_independence: different-tool # Ecosystem default; Base-supported projects use fresh-session
  review_policy:
    required_approving_reviews: 0
```

The field names and bounds are implementation details for the config issue; the two loop limits are separate and both start at three. The setting is repository-scoped and versioned. Base-supported projects receive the then-current default values only through an explicit configure/upgrade operation and reviewed PR; they do not inherit moving settings at runtime. Validate schema version and reject invalid ranges with a clear error.

## 16. Skills — DEFERRED

Do not add Superpowers or another skill framework as part of the initial governance rollout. First pilot the issue and PR specifications, review loops, documentation-impact tracking, decision records, and drift checks using repository-owned templates, rules, and deterministic tooling. Revisit skills only if evidence from the pilot shows a concrete gap in spec-driven development or documentation-drift prevention that the governance design does not cover. Any later skill proposal must receive its own issue and security review.

## 17. Testing and proof

### 17.1 Test types — DECIDED

Unit; integration (`tests/integration/`, temporary homes and fake projects); contract and golden output; end-to-end (Base Demo E2E on macOS); acceptance and dogfooding. Static checks (ShellCheck, Bandit, pip-audit, Gitleaks, CodeQL, linters) run on every PR. Fast small tests on every PR; slower ones on `main` and nightly.

### 17.2 Testing rules — DECIDED (from Memo §13)

1. **Bug-first:** every bug a user found gets a failing test before the fix. If a test genuinely cannot capture the bug, the PR explains why; count such exceptions during the pilot for later review.
2. **Journey tests:** real demo flows end to end, plus failure journeys (untrusted project, invalid manifest, missing repo).
3. **Nightly run** on a clean macOS runner, with failures filed as issues automatically.
4. **Coverage audit** against the command surface and journeys.
5. **Intentional dogfooding** through BankBuddy, Bleach and Blend.
6. **Demo readiness:** the nightly journey suite is green before any demo.
7. **Workspace command contract:** fan-out workspace commands preflight the whole selection (trust, manifest validity, eligibility) before running anything, announce each project, and end with a summary, through one shared preflight helper, with a contract test.

### 17.3 The dogfooding machine — DECIDED

A second laptop runs **only released Base from Homebrew**, never a source checkout, for Bleach, BankBuddy and similar work. That exercises the release and upgrade path. A Base problem found there gets an issue filed there and fixed only on the main machine.

### 17.4 Proof plan and metrics — DECIDED

- Prove Base on projects of different sizes; record pilot duration, friction and exceptions. No fixed freeze or calendar duration is assumed.
- **Metrics:** drift incidents per month; post-merge rework; follow-up issues linked to Done issues; spec-gap rate; small-change misclassification; maintainer interventions; share of PRs with real findings; reviewer/author tools and outcomes; user-found bug fixes using the test-impossibility exception and reasons; and rules that never caught anything.
- **Token economy:** use deterministic scripts and linters for mechanical checks. Reviewers inspect the diff and only relevant rules/standards. Loops stay capped. Eligible base-only updates are re-verified without another full round; light-path changes use one pass and less impact detail. Stage 1 records reported token use per issue/PR and per review round; if a CLI does not report it, mark it unavailable rather than estimate. The restored metrics-report issue owns ongoing data; it is not package 17's pre-pilot baseline or #2585's retrieval-eval baseline.
- Stage 2 derives a comparable-work warning threshold from Stage 1 observations (for example, above twice the median). It warns only; it never gates, cuts off or changes the review loop.
- **Pre-pilot baseline:** package 17 records available measures from a declared historical sample before pilots, including the source/sample limits, the starting estimate that about 60% of Codex PRs had real review findings, and counts of disconnects found by hand testing and docs-vs-code drift audits. If a historical count cannot be reconstructed from source records, mark it unavailable rather than estimate it.

### 17.5 Self-assessment and self-healing — DECIDED

- **Reflexes:** gate checks catch a problem the moment it appears.
- **Deliberate healing:** periodic audits find patterns, ask why, and add a new reflex. Over time each audit should find less.
- **Never silent:** every correction becomes an issue and goes through analysis and approval like any other change. A system that rewrites its own rules without oversight is how incidents happen.
- **Monthly review:** which rules caught nothing? Candidates for retirement.

---

## 18. Rollout

### 18.1 Foundation and staged releases — DECIDED

There is no feature freeze and no fixed calendar schedule. Base 1.11 is the foundation: plan adoption, milestone renumbering, this design correction, Area definition, document inventory/reorganization, base-demo lockstep and issue reconciliation. Governance then ships one stage per release, 1.12 through 1.15. Each release requires its exit evidence and maintainer authorization. Repository-local issues keep their own milestones; Base coordinates other repositories without assigning Base milestones to them.

### 18.2 Four governance stages and implementation-plan mapping — DECIDED

| Release | Stage | Intent and work |
|---|---|---|
| **1.12** | Stage 1: manual loops | Establish ADR/document contracts and templates, repository config, reviewer rules, baseline, manual readiness and issue/PR review loops. Migrate the Base Project schema (package 8), enable conversation resolution, and use the dedicated reviewer App for comment-only reviews. Run real issue and PR pilots. |
| **1.13** | Stage 2: deterministic checks | Implement readiness, PR contract, slice Status reconciliation and round ledger; dry-run, then warn-only rules and audited override. |
| **1.14** | Stage 3: drift checks and read-only review | Pin the released checker, run per-kind drift checks and the least-privilege read-only reviewer after security gates. Demonstrate rollback. |
| **1.15** | Stage 4: organization adoption | Adopt Base profile, organization templates and repository-local profiles across all basefoundry repositories, including consumer defaults in banyanlabs; migrate open titles after prerequisites. Each repository uses its own release system. |

The new export-context generation is after all four stages, targeted for 1.16.0. Keep tracked .ai-context until the replacement is shipped and proven; cleanup occurs afterward. A stage can develop local checks before a pin, but hosted enforcement waits for the required released artifact. No implementation starts from this design alone; each package needs its own reviewed issue/PR train and maintainer authorization.

## 19. Phase 2: governance as a product — DEFERRED

### 19.1 Purpose

After the first-party pilot, decide which defaults are stable enough to offer to Base-supported projects. This design does not require a consumer to create a `governance/` directory or adopt GitHub Project fields they do not use.

### 19.2 Configuration and inheritance

Base ships versioned default governance settings and templates. A supported project receives them only through an explicit `basectl repo configure` or upgrade operation that proposes a reviewable PR. The project may keep small repository settings in the `governance:` section of its existing `base_manifest.yaml`; an optional `governance/` directory holds richer customized rules when needed. There is no live remote inheritance, mandatory new directory, separate `base-governance.yml`, or `.base/` folder. `basectl config` shows effective values and their source; upgrades preview conflicts and do not overwrite project choices silently.

### 19.3 Ownership and upgrades

The implementation must distinguish Base defaults, project customizations, and GitHub-required generated/integration files. Any generated files need a generator, ownership marker and drift check before being described as managed. A hand edit to a managed file is surfaced and proposed as an overlay change; it is never silently overwritten. The upgrade is a PR showing the precise changes.

### 19.4 Per-project choices

A supported project may choose `fresh-session` or `different-tool` reviewer independence. The project uses the issue/PR loop and canonical impact list; details scale to its size. Area/risk catalogs, issue forms and branch policy remain optional until the pilot proves which pieces can be shared without imposing a Base-specific structure.

### 19.5 External contributors

Fork workflows receive no secrets and do not run auto-fix agents. Any later read-only review of untrusted external content must be explicitly requested by a maintainer and isolated from privileged write credentials. Failure messages should explain the correction in contributor-friendly language.

## 20. Later and out of scope

- **Current GitHub platform baseline:** Dependabot and CodeQL are enabled; Discussions is the public home for questions and ideas; reusable workflows are called at pinned versions. These platform features remain part of the operating context for the governance rules.
- **MCP server, retrieval and RAG:** separate product work outside governance releases 1.11–1.15. Keep #2585–#2591 and #2600 on their own release/milestone tracks. #2601 belongs to matrix/test-bed evidence and #2602 to the durable event ledger described below; generated context export does not replace retrieval or MCP.
- **Controller authoring, manifest agent policy, durable event ledger, replay and crash recovery:** preserve the original #2555 roadmap scope as separate work. Human issue/PR loops, the read-only reviewer, a review-round ledger, and baseline metrics do not implement those controllers or event stores. In particular, #2584's original `agent:` path/size/autonomy policy is not package 3's governance config or consumer defaults; keep it as a separate post-1.15 issue after a design names its scope and stage.
- **Base-supported consumer configurability:** after 1.15, offer a small set of light/standard/full presets plus independent switches; #2584's current consumer-defaults scope belongs here only if it remains distinct from the original manifest agent-policy work. Document interactions, reject incoherent combinations in plain language, and keep Stage 1–3 components separable. Do not implement these consumer presets in this rollout.
- **Other trackers:** adapters only on demand (§15.4).
- **Untrusted external contributions:** no secrets or auto-fix agents in fork workflows.

## 21. Open questions

| # | Question | When/how to settle |
|---|---|---|
| O1 | Which GitHub events expose Project field changes reliably, and which require scheduled reconciliation? | Read-only implementation spike before lifecycle automation. |
| O2 | Can GitHub rulesets safely enforce formal reviews from the reviewer App while preserving current-head freshness? | Stage 1 remains comment-only with zero required approvals. Test formal review/ruleset behavior and obtain a new maintainer decision before enabling it. |
| O3 | Which hosted AI providers, credentials, data-retention terms and network controls are acceptable for automated review/fixes? | Security review before any hosted-model workflow. |
| O4 | What exact `basectl config` syntax and schema bounds should expose the repository governance settings? | Config implementation issue; preserve current local config behavior. |
| O5 | Which provider CLIs and privacy/offline modes will `export-context` support? | Threat model and implementation issue before release. |
| O6 | What is the final area list, ownership map and path mapping? | Inventory issue; preserve the shared defaults in `project_model.py` and repository-specific area/initiative extras and issue defaults in `.github/base-project.yml` until migration. |
| O7 | Confirm decision/design/initiative/guide locations against the documentation inventory. | Documentation migration issue. |
| O8 | Should the `blocked` label be replaced by native issue dependency relationships? | Metadata migration issue after live-use review. |
| O9 | Which governance defaults are stable enough for Base-supported projects? | Phase 2 design after first-party evidence. |
| O10 | Which public wording should distinguish community intake from internal Triage: (1) retain “triage” publicly and explain the difference, (2) call it “community support” and document its handoff to internal Triage (recommended), or (3) choose another plain-language term with the same handoff? | #2671 decides; keep public guidance unchanged until its disposition is approved. |
| O12 | Should native Issue Types replace any current category-label branch routing, and should `Feature` become `Enhancement`? | Dedicated migration decision; no type or branch-policy migration is implied here. |
| O13 | After the Risk field exists, may an author agent set Ready for a Low-risk issue after a current Ready verdict, or does the maintainer retain every Ready transition? | Decide with the Risk-field migration and pilot evidence; until then the maintainer sets Ready for every issue. |
| O14 | How should the original #2555 controller work assign Status ownership, choose one or several ledgers, define controller levels and authoring authority, and stage MCP/retrieval? | Resolve each question in a reviewed issue/design amendment before assigning the affected original work to a release; see implementation plan §10. |
| O15 | After the Status reconciler is introduced, which component owns each Status transition, and which current Project Intake or built-in Project writers remain enabled? | Decide in the reconciler design after every current writer has been behavior-tested; specify migration, rollback and manual override behavior before disabling any writer. |

O11 is retired: it was used for the 1.x freeze question in an earlier review, which the maintainer resolved by confirming there is no freeze and the schedule is flexible (Appendix E, decision 13). Its identifier is not reused.

## Appendix A. Superseded positions

This appendix is a historical record of consolidation-era positions; later changes and maintainer decisions are recorded in the current body and Appendices E–F. Its “position at consolidation” column is not current policy. “WN” means Working Notes; “Memo” means Base Direction Memo v12. Where a change happened in conversation without an explicit “supersedes” note, it is marked *(silent)*.

| # | Topic | Earlier position | Position at consolidation | Changed by |
|---|---|---|---|---|
| A1 | Reviewer identity | Claude Code reviews as Ramesh's second GitHub account, set up as a machine account (Memo §4.1, §11; WN2 §4). | No machine account. Stage 1: agents act as Ramesh's account, with attribution through the provenance footer and Co-authored-by trailers. Stage 2: automated loops run as each tool's GitHub App bot. | WN29, WN30 |
| A2 | Merge gate | Branch protection requires an approving review from an identity other than the author (Memo §4.1). | Stage 1: required checks plus resolved conversations; Ramesh merges. Required approval returns in Stage 2 only if bot approvals can satisfy branch protection. | Q4, 3 Nov 2026 |
| A3 | Project Status values | Backlog, Triage, Ready, In Progress, In Review, Done; new issues enter Triage (Memo §9). | Six statuses: Backlog, In analysis, Ready, In progress, In review, Done. No Triage status. | WN2 §5 |
| A4 | Spec location | Open: issue, repo file, or middle path (WN1 §9). | The spec and the plan live in the issue body. | WN2 §2 |
| A5 | Plan location | Open: issue comment or repo file (WN1 §8). | Issue body, under a Plan heading filled during analysis. Never a comment. | WN2 §2, WN10 §2 |
| A6 | "Affected surfaces" | Issue section listing commands, modules, docs, demos touched (WN1 §7). | "Affected areas": every product area touched, each with a line on how. Docs, tests and demos keep their own impact sections. | WN10 §1 |
| A7 | Middle risk tier name | "Normal" (WN2 §4). | "Medium". | WN12 §1 *(silent rename)* |
| A8 | Issues to PRs | One PR may fix several issues (union of labels; milestones must match) (Memo §8.4). | Every PR belongs to exactly one issue. One issue may have several PRs. Many-to-many ruled out. | WN22 §1 |
| A9 | Intermediate PR keyword | "Refs #N" (Memo §8.4, §9). | "Part of #N". The final PR uses "Fixes #N". | WN22 §1 *(silent)* |
| A10 | PR planning fields | PR inherits labels and milestone only; Project fields not set; PR not a Project item (Memo §8.2). Later: PR leaves its copies empty (WN7 §3, WN22 §2). | Open PRs mirror the issue's Priority, Size, Area, Risk tier, Milestone and Initiative; merged PRs freeze. Issue always wins. Assignee is the PR's own. PRs become Project items; board views filter to issues. | WN23, Q2 |
| A11 | "Project boards track issues, not PRs" | PRs are not added as Project items (Memo §8.1). | PRs are Project items so their fields can be mirrored; standard views show issues only. | Q2, 3 Nov 2026 |
| A12 | PR template | Memo §8.5 checklist; then an eight-section proposal including "Affected areas" and "Fold-back" (WN14 §1). | Nine fixed sections: Summary, Issue, Plan followed, Validation, Docs and decisions, Demo impact, Release note, Risk and rollback, Notes. | WN31 §3 |
| A13 | Affected areas on PRs | A PR section that must match the issue's list (WN14, WN19 §1). | No PR section. The check computes touched areas from changed paths and compares them with the issue. | WN31 §5 |
| A14 | AI context | `.ai-context/` is a curated orientation layer updated by every meaningful PR; an "AI context" reviewer hat; AI context as a fold-back destination (Memo §8.5, §11.3; WN14; WN19). Codex's 1.11 draft keeps it as an index. | `.ai-context/` is deprecated. Orientation is generated on demand by `basectl export-context` from the real documents and never stored in the repo. The PR template has no AI-context section. | WN31 §6, WN34 §2 |
| A15 | Backward moves to Backlog | Allowed when deliberately parking or abandoning (WN14 §2). | Never back to Backlog. Abandoned work is closed as Not planned. | WN26 §1 |
| A16 | Backward transitions status | PROPOSED (WN14 §2). | DECIDED, extended to cover Ready. | WN26 |
| A17 | Rollout stages | Stage list with the decision log in Stage 3 (WN16 §4). | Three stages split by automation level, decision log in Stage 1. | WN20 §1, WN21 |
| A18 | Plan of work | WN21 §6 list. | Base Governance Implementation Plan (2 Nov 2026), now expanded in the companion implementation plan. | Implementation Plan |
| A19 | Override mechanism | A label named "override" plus a reason comment (WN27 §3). | A single comment starting with "Override:" and a reason. No label. | WN28 |
| A20 | Enforcement action in Stage 1 | Revert rule-breaking manual edits and comment (WN27 §2). | Stage 1 warns only. Reverting is switched on per rule once that rule's warnings prove accurate. | WN30 §6 |
| A21 | Initiative | Open: drop it, keep it optional, or make it a document (WN7 §6; Memo §14). | Optional field for efforts spanning several milestones, each backed by a short initiative document; the value is retired when the document is marked done. | WN25, WN26 §3 |
| A22 | Initiatives as parent issues | Proposed in conversation. | Rejected: it bends a hierarchy feature to work around a retirement gap. | WN7 §6 |
| A23 | Where definitions live | Fields and labels declared in `.github/base-project.yml` (Memo §14, §18; WN7 §9); area list "likely in the manifest" (WN7 §7). | Source of truth in `governance/` (for example `governance/areas.yaml`, `governance/labels.yaml`); `.github/` files are generated. `.github/base-project.yml` remains only for what existing tooling still reads until migrated. | WN13 §2, WN32 §5 *(silent)* |
| A24 | Per-repo template surfaces | The manifest declares a repo's surfaces and the issue template omits sections that do not apply (WN1 §7). | In Phase 1 every Base issue has every section; "None" plus a reason. Per-repo generation is a Phase 2 idea, consistent within each repo. | WN9 §2, WN31 §2 *(silent)* |
| A25 | Bug-specific sections | Bugs get extra sections: steps to reproduce, actual vs expected (WN1 §7). | No extra headings. For Bug-type issues, the Problem section must contain reproduction steps and actual vs expected behavior. | Consolidation (Appendix B, B1) |
| A26 | Expected behavior format | Free-form testable statements (WN1 §7). | Numbered items written as "When …, then …". | WN37 §1 |
| A27 | Validation section | Commands and output (WN31). | Commands and output, plus which test covers which numbered expected-behavior item. | WN37 §2 |
| A28 | Who plans | Codex writes the issue and plan; Claude reviews (WN2 §4). | Roles are a configurable policy (creator, planner, reviewer, implementer, PR reviewer). Base's defaults: Codex plans and implements, Claude reviews. The rule that matters: the reviewer is never the author of what it reviews. | WN10 §3, WN17 |
| A29 | Build order | Drift audit, then 1.11 governance, review loop first (Memo §4); then issue template and loop, PR loop, docs review, MCP, RAG (WN3 §1). | Implementation Plan order: finish drift PRs, consolidate, review the design, Stage 1 foundation, area refactor, doc migration plan, doc migration, Stages 2 and 3. MCP and RAG stay later. | Implementation Plan |
| A30 | Documentation design | Deferred (WN20 §3). | Decided direction: six kinds of documents, link rules, README, PRD, area design doc template, install chooser, FAQ. | WN34–WN37 |
| A31 | Risk tier assignment | Deterministic tiering by paths, diff size and public contract changes, planned for 1.12 (Memo §12). | Planner proposes a tier using blast-radius and reversibility definitions; reviewer may raise; only Ramesh lowers. A path-based floor is kept as a mechanical check (see B6). | WN11, WN12 |
| A32 | Label used as an example | "security" given as an example of a plain label (WN7 §8). | Not allowed: Security is an issue type, and labels must not duplicate issue types. | Consolidation (B4) |
| A33 | Issue types vs category labels | Category labels drive branch policy today. | Issue types (Bug, Enhancement, Documentation, CI, Security, Task) become the source of truth going forward; tooling reads type first, falls back to the legacy label. Scheduled with the Stage 3 metadata work. | Memo §15 (unchanged), scheduling by consolidation |
| A34 | Where agents look before changing an area | Search closed issues and merged PRs for the area, then read its decision entries (Memo §20.4). | Read the area's active decisions and design doc. Searching closed issues stays only until the documentation migration is complete, since issues are archaeology, not current truth. | WN2 §1, WN34 *(silent)* |
| A35 | Context digest | A hand-curated `.ai-context/` exported nightly; later, a scripted recent-activity digest (Memo §10.2; Context Digest v2). | `basectl export-context` uses AI to generate orientation from the real documents, under guardrails; read-only; never stored in the repo. Nightly generation on the Mac into Drive stays the delivery route. | WN1 §2, WN31 §6, WN34 §2 |
| A36 | Planner/reviewer independence | Separate tools always (WN2 §4). | Independent session always. Medium and High require a different tool from the author; Low may use the same tool in a fresh session. | WN17 §4 |

## Appendix B. Reconciliations made during consolidation

These are the consolidation-era resolutions of gaps between source notes. They record what the draft proposed at that point, not a requirement for new approval now. Current disposition of B1–B18 is recorded in Appendix F and the current body; later maintainer clarifications are in Appendix E.

| # | Gap | Resolution at consolidation | Why |
|---|---|---|---|
| B1 | Bugs needed reproduction steps (WN1), but every issue must keep the same sections (WN9). | Bug-type issues put reproduction steps and actual vs expected behavior inside **Problem**. The readiness check enforces this for type Bug only. | Keeps one layout for every issue while still requiring what a bug needs. |
| B2 | "Every impact needs a reason" (WN1) vs Codex's 1.11 draft allowing "Unknown" at issue time. | "Unknown: reason" is allowed while an issue is in Backlog or In analysis. Ready requires every impact to be Yes or None, each with a reason. | Issue authors often can't know impacts before anyone reads the code; analysis is where they get resolved. |
| B3 | "Never back to Ready" (WN26) vs "a PR closed without merging returns the issue to Ready or In progress" (WN2). | The "never back to Ready" rule applies when the plan changes. If a PR is closed unmerged and the approved plan still stands, the issue stays In progress when another PR will follow, or returns to Ready if work pauses. | Ready means "approved plan". An unchanged plan is still approved. |
| B4 | Label examples included "security" and "blocked". | "security" is not a label (Security is an issue type). "blocked" stays for now; Codex checks whether GitHub's native issue dependencies ("blocked by") should replace it. | Labels must not duplicate a native feature. |
| B5 | "In review" was never defined against draft PRs. | Draft PRs and the agent review loop keep the issue **In progress**. The issue moves to **In review** when its PR is marked ready for review, after the agent loop approves. | Matches Memo §9 ("non-draft PR opened") and the draft-then-ready pattern. |
| B6 | Memo §12 tiered by paths; WN12 tiers by blast radius. | The planner proposes a tier using the WN12 definitions. Each area in `governance/areas.yaml` may declare a minimum tier (trust, setup, release, governance: High). The readiness check rejects a tier below the floor of any affected area. | Keeps the judgment-based definitions and adds a cheap mechanical floor. Fits the ratchet: the floor only raises. |
| B7 | Field mirroring (WN23) has no stage. | Stage 1: `basectl gh pr create` copies the fields once at creation. Stage 2: automation keeps open PRs in sync. Stage 3: the merge check blocks on mismatch. | Delivers the rule early without waiting for automation. |
| B8 | Issue types (Memo §15) were never placed in a stage. | Scheduled in Stage 3 with fields, labels and areas as code. Stage 1 keeps the current category label, because the branch policy depends on it. | Changing the branch policy is High risk and doesn't belong in a one-week foundation. |
| B9 | Release notes "generated from merged PRs" (WN1) vs a hand-edited CHANGELOG.md in release-prep PRs today, and Codex's draft keeping a versioned changelog. | Each PR's **Release note** line is the source. `basectl release notes` assembles CHANGELOG.md entries for a release, grouped by issue type (Keep a Changelog style). The release-prep PR reviews the assembled text and may edit wording, never add unrecorded changes. | One source per fact, while keeping the human review a release deserves. |
| B10 | Drift catching per document kind was never designed (WN34 §8). | A PROPOSED first version is in §12.10. | Lets the Codex review react to something concrete. |
| B11 | Memo §11.3 had specialist reviewer "hats"; later notes describe one rule set per reviewer. | The PR reviewer may run specialist passes (code, docs, tests, demo, base-demo) chosen by changed paths, as a way to control tokens. All passes cite the same rule set and post one consolidated review. The AI-context hat is dropped. | Keeps the useful mechanism and drops the deprecated one. |
| B12 | Decision status vocabulary differed (Proposed/Accepted/Replaced vs Codex's Proposed/Accepted/Superseded/Rejected). | Proposed, Accepted, Replaced by #N, Rejected. | Adds Rejected for proposals that were recorded but not adopted. |
| B13 | Document locations were never fixed. | Proposed: `docs/decisions/NNNN-slug.md`, `docs/design/<area>.md`, `docs/initiatives/<slug>.md`, `docs/guides/…`. To be confirmed by the documentation migration plan. | Gives the migration a starting point. |
| B14 | Dropping the machine account left no second approver. | Stage 1 merge gate: required checks plus resolved conversations; Ramesh merges. | Ramesh's answer to the consolidation questions, 3 Nov 2026. |
| B15 | "Re-analyze if an issue sat in Ready a long time" (WN2) had no number. | 30 days. The readiness check warns when the latest approval is older than that. | Concrete enough to automate; adjustable in `governance/`. |
| B16 | Generated `.github/` files (WN13) before any generator exists. | Stage 1 includes a small renderer and a CI check that the committed `.github/` files match what `governance/` produces. | Makes the "never hand-edited" habit real from day one. |
| B17 | Label names: "single word" (WN7) vs GitHub's own `good first issue` and `help wanted`. | Plain names with no prefixes, colons or slashes. Spaces are allowed, so GitHub's default contributor labels keep their exact names, which GitHub's contributor features recognize. | Uses each GitHub feature as intended. |
| B18 | Issue fields (GA July 2026) weren't in any note. | The design stays on Project fields. Moving Priority, Size, Area and Risk tier to issue fields is an OPEN question for the Codex review. | Ramesh's answer to the consolidation questions, 3 Nov 2026. |

## Appendix C. Issue-history drift audit prompt

Carried from Memo v12 §21, unchanged, so it isn't lost. It finds durable decisions recorded in closed issues and merged PRs that never reached the docs. Run it after the docs-vs-code audit settles, with Codex and Claude Code independently, and compare: findings both report are high confidence. Confirmed findings become documentation issues and, when durable decisions are involved, decision records (§11.5). Keep it as a repo-owned read-only audit prompt. It may inform the drift-check work described in §12.10 after the documentation inventory is complete.

**Prompt (copy as-is):**

```text
You are auditing the Base repository (basefoundry/base) for drift between GitHub issue/PR history and the project's documentation. Do not modify any files, issues, or PRs. Produce a report only.

GOAL

Find durable decisions recorded in GitHub issues and pull requests that are missing from, or contradicted by, the current documentation. Documentation means: docs/ (design and user docs), README.md, CHANGELOG.md, AGENTS.md, CONTRIBUTING.md, and .ai-context/.

A "durable decision" is a choice about product scope, behavior, command semantics, flags, defaults, output formats, safety or trust rules, workflow conventions, naming, platform support, or architecture boundaries that should still guide future work. Bug fixes, refactors, typos, and one-off chores are NOT decisions unless their discussion established a rule (for example, "workspace commands must preflight all projects before executing").

SCOPE

1\. Use the GitHub CLI (gh) to list closed issues in basefoundry/base that were resolved by a merged PR (`Fixes #N`, `Part of #N`, or `Refs #N`). Include the linked PR descriptions and review discussions.

2\. Exclude issues closed as "not planned", duplicates, issues with no merged PR, and PRs that were closed without merging.

3\. Read the current documentation listed above on the main branch.

4\. Only consult source code to confirm whether a candidate decision actually shipped. Do not report general code-vs-docs gaps; that is a separate audit.

METHOD

1\. Group issues by area (for example: workspace commands, trust, setup/bootstrap, activation, manifest schema, release, GitHub workflow, CI, AI context, Linux, Windows). Use labels, issue types, paths touched by the merged PR, and titles to assign areas.

2\. Within each area, process issues in chronological order of merge. When a later issue or PR changes or reverses an earlier decision, the later one wins; record the earlier one as superseded, not as drift.

3\. For each candidate decision, find where the documentation covers it. Classify as:

- DOCUMENTED: docs state it accurately. Do not list these individually; give a count per area.
- MISSING: no doc states it.
- CONTRADICTED: a doc states something different from the latest decision.
- STALE: a doc still describes a superseded decision.
- UNCLEAR: you cannot tell whether it is a durable decision or whether it shipped.

4\. For MISSING, CONTRADICTED, and STALE items, confirm against code on main whether the decision is actually implemented. Record "shipped", "not shipped", or "partially shipped".

OUTPUT (Markdown)

1\. Summary: issues scanned, issues excluded (with reason counts), areas covered, and counts per classification per area.

2\. Findings table with columns: ID | Area | Classification | Decision (one sentence) | Source (issue #, PR #, date merged) | Doc location (file and section, or "none") | Shipped? | Confidence (high/medium/low) | Proposed fix (exact doc and the sentence to add or change).

3\. Superseded chains: for each area, list decisions that were later reversed, with the issue/PR that reversed them, so a human can confirm the docs reflect only the final state.

4\. Candidate decision-log entries: for every MISSING or CONTRADICTED finding with high or medium confidence, draft an entry with: date, decision, reason (quoted or paraphrased from the issue/PR), alternatives rejected (if discussed), linked issue and PR, affected docs.

5\. Open questions: anything you could not resolve, phrased as a yes/no question for the maintainer.

RULES

- Cite every finding with issue and PR numbers. Never report a finding without evidence.
- Quote the exact issue/PR text that establishes the decision, briefly.
- Prefer fewer, high-confidence findings over many speculative ones. When unsure, classify as UNCLEAR rather than MISSING.
- Do not propose code changes. Do not create issues. Do not edit files.
- If the issue volume is too large for one pass, process one area at a time, state which areas are complete, and stop with a clear list of remaining areas.
```

## Appendix D. References

Public sources behind the choices in this document:

- Diátaxis documentation framework — https://diataxis.fr/
- arc42 architecture template — https://arc42.org/overview/
- Architectural Decision Records — https://adr.github.io/
- Martin Fowler, Architecture Decision Record — https://martinfowler.com/bliki/ArchitectureDecisionRecord.html
- MADR template and status vocabulary — https://github.com/adr/madr/blob/develop/template/adr-template.md
- AWS Prescriptive Guidance, ADR process — https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
- GDS Way, documenting architecture decisions — https://gds-way.digital.cabinet-office.gov.uk/standards/architecture-decisions.html
- GitHub Actions secure use — https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
- GitHub protected branches and stale reviews — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- Keep a Changelog — https://keepachangelog.com/
- Google Engineering Practices (code review, small changes) — https://google.github.io/eng-practices/
- GitHub automatically generated release notes — https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes
- GitHub issue and PR templates — https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates
- GitHub issue fields, generally available 2 July 2026 — https://github.blog/changelog/2026-07-02-issue-fields-are-now-generally-available
- GitHub issue fields preview ("replace … label-based workarounds"), 12 March 2026 — https://github.blog/changelog/2026-03-12-issue-fields-structured-issue-metadata-is-in-public-preview/
- GitHub Spec Kit — https://github.com/github/spec-kit
- Kiro — https://github.com/kirodotdev/Kiro

Internal sources: Base Direction Memo v12; Base Working Notes Parts 1–37; Base Governance Implementation Plan (2 Nov 2026); Base Documentation Governance — Working Draft for 1.11 (Codex, 21 Oct 2026).

## Appendix E. Maintainer clarifications recorded 8–20 November 2026

These decisions are incorporated in the current body and supersede any inconsistent statement in the earlier 3 November appendices. Items 17–21 record later maintainer decisions.

1. Keep Triage between Backlog and Ready, and use separate repository-owned issue and PR round limits, each initially three.
2. Draft PRs keep the issue In Progress. Use delivery slices rather than fixed PR numbers. In Review requires reviewable evidence for every slice; Done requires every slice merged or an explicit maintainer-approved terminal disposition.
3. Authors respond to every review finding. The reviewer verifies and confirms fixes at the current full head SHA; the author resolves only after Fixed confirmation or an explicit reviewer withdrawal. The maintainer resolves directly only when overriding, with rationale. Disputes and round-limit exhaustion go to the maintainer. PR verdicts bind to the current head SHA. During Stage 1, the reviewer App posts comment-only reviews and required approving reviews stay at 0; formal reviews require a ruleset test and a new maintainer decision.
4. Keep issue Project fields canonical. Do not mirror them to PRs or add PR Project items to copy them. Native Type, Issue Fields, Project, labels, milestones and relationships have separate responsibilities (§10).
5. Keep issue and PR titles plain. After adoption, rename every open issue and open PR, including drafts, through a tracked migration; retain closed/merged titles as history by default.
6. Use explicit ADR acceptance in the implementation PR. This is a Base choice within common ADR practice, not a universal industry requirement.
7. Do not remove `.ai-context/` before the replacement `basectl export-context` feature is implemented, released and proven. Keep maintaining existing context files and checklist until then; cleanup occurs in separate repo trains.
8. Defer Superpowers skills until the manual governance pilot demonstrates a gap in spec-driven development or drift prevention.
9. Repository loop limits belong in the tracked `governance:` section of `base_manifest.yaml`; `basectl config` manages them. Do not add `base-governance.yml` or `.base/`. Detailed first-party rules may live in `governance/`; consumer projects need not create that directory. `homebrew-base` receives a manifest in its own train. Existing `github.pr` rules remain there.
10. Use one issue form where possible. Readiness checks validate the current native Type; changing Type after Ready invalidates the approval.
11. `basectl` may invoke a user-selected installed AI provider CLI for context export only under the privacy and security controls in §12.9. It does not directly call provider APIs or manage provider credentials.
12. B1–B18 dispositions appear in Appendix F. The `security` category label remains valid; security vulnerability reports use private advisories.
13. There is no 1.x freeze. The release schedule is flexible; this plan uses relative order and S/M/L sizing, not fixed dates.
14. D18: every user-found bug gets a failing test before the fix unless a test genuinely cannot capture it; the PR must explain why, and the pilot counts exceptions.
15. D19: every issue/PR review uses a separate agent in a new session with no author-session transcript or persistent authoring memory. Whether the tool must also differ is configurable. Base defaults to `different-tool`; supported consumer projects default to `fresh-session`. Verdicts record both tools, models and sessions. If a configured different tool is unavailable, wait or escalate—never fall back to the same tool.
16. Phase 1 includes every `basefoundry` repository. The nine Base ecosystem repositories use `different-tool`; `banyanlabs` is a Base-supported project and uses consumer defaults (`fresh-session`, no required `governance/` directory).
17. The reviewer App does not resolve review threads. After the reviewer replies Fixed at <full-head-SHA>, the author resolves; after Withdrawn at <full-head-SHA>: <reason>, the author may resolve. The author never resolves an unconfirmed finding. Only the maintainer resolves directly when overriding, with a recorded rationale. The App grants and observed capabilities are limited to the evidence in the scratch test; untested behavior remains a security gate.
18. During the Stage 1 pilot, the built-in Pull request linked to issue workflow stays enabled.
19. Status ownership: Project Intake sets Backlog on open/reopen. The author agent records Triage when it starts the issue plan, In Progress with `basectl gh issue start <N>` only after the maintainer sets Ready and directs work, and In Review when every planned slice has a non-draft PR or reviewable non-PR evidence. The maintainer owns Ready and Done, every override and manual Status correction, and audits the agent transitions during Stage 1. The maintainer sets Ready for every issue until the Risk field exists; whether the author agent may set it for Low-risk work after that field is introduced remains open (§7.1, §21). If the linked-PR workflow sets In Progress before issue start ran, that is a process miss recorded in §5.2.
20. An issue may return to Backlog only from Triage, when the maintainer defers its analysis. It never returns to Backlog from Ready, In Progress or In Review. A changed contract returns the issue to Triage (§5.4), and abandoned work is closed as Not planned.
21. The five new proposals in v1.4 are accepted as follows: §10.3's flat-label mapping and no-match handling are decided; base-cli overrides Dependabot's generated `python:uv` label with `dependencies` in its own migration; the reviewer App uses comment-only reviews in Stage 1, with formal reviews requiring a ruleset test and a new maintainer decision; §12.13's interim document-homes table is adopted after correcting package numbers; and a slice may omit a PR only when it changes no repository content, with the author attaching evidence and recording In Review and the maintainer accepting it and closing the issue as Done. Escalation-view implementation and post-reconciler ownership of each Status writer remain proposed pending verification or a separate decision.

## Appendix F. Disposition of original B1–B18 items

| Item | Disposition | Current treatment |
|---|---|---|
| B1 | Accept | One issue layout; Bug reproduction and actual/expected go inside Problem. |
| B2 | Accept | Unknown: reason is allowed while Backlog or Triage; every category is resolved by Ready. |
| B3 | Retire | Replaced by the slice/status rules in §5. |
| B4 | Correct | `security` remains a category label; vulnerability reports go through private advisories; follow-up work is Bug or Task. The label is not a native Issue Type. |
| B5 | Accept | Draft PRs keep the issue In Progress. |
| B6 | Defer | No per-area minimum risk floor until the Risk tier field and pilot evidence exist. |
| B7 | Retire | Issue fields are not copied to PRs. |
| B8 | Accept | Current branch policy reads category labels; native Issue Types are separate. Any migration is tracked. |
| B9 | Accept | Every PR has a release-note line or reasoned `none`; release preparation updates `CHANGELOG.md`. |
| B10 | Accept | Per-kind drift checks are proposed in §12.10 and implemented only after inventory. |
| B11 | Accept | Path-triggered specialist passes may produce one consolidated review; there is no AI-context reviewer pass. |
| B12 | Retire | The ADR lifecycle in §11 is authoritative. |
| B13 | Accept | Proposed document locations are confirmed through the inventory package. |
| B14 | Reconcile | The maintainer merges; Stage 1 reviewer App reviews are comment-only and required approvals remain zero. The reviewer verifies and replies Fixed or Withdrawn at the full head SHA; the author resolves afterward. The maintainer resolves directly only when overriding, with rationale. Do not claim branch protection enforces resolution until its separate policy change ships. |
| B15 | Accept | Ready freshness defaults to 30 days, stored in manifest governance settings. |
| B16 | Retire | No `.github/` generator is promised before a separate implementation and ownership design. |
| B17 | Accept | Preserve GitHub's exact `good first issue` and `help wanted` names with spaces. |
| B18 | Retire | Do not mirror Project values into organization Issue Fields or PR fields. |

## Appendix G. Current disposition of the historical A1–A36 positions

The rows in Appendix A remain the verbatim consolidation-era record. This table records what the current design does with each position; it does not rewrite those rows or turn a historical proposal into current policy. Appendix F performs the equivalent individual check for B1–B18. The detailed current-state crosswalk for all 49 original #2555 issues is [comment 7016911172 on #2555](https://github.com/basefoundry/base/issues/2555#issuecomment-7016911172).

| Row | Current disposition | Current design or rationale |
|---|---|---|
| A1 | Revise | Reviewer App role and declared tool/model/session provenance: §§13–14.6. |
| A2 | Retain | Maintainer merge; zero required approvals during Stage 1 because reviewer App reviews are comment-only: §§8.6, 14.6. |
| A3 | Supersede | Backlog, Triage, Ready, In Progress, In Review, Done and their owners: §5. |
| A4 | Retain | Spec stays in the issue body: §3.3. |
| A5 | Retain | Plan stays in the issue body and is completed during Triage: §§3.3, 4.3. |
| A6 | Revise | Affected Areas and separate document-impact evidence: §§4.2, 12.10. |
| A7 | Retain | Medium remains the middle Risk tier: §7.1. |
| A8 | Retain | One issue per PR by default; planned multi-PR slices are supported: §§4.3, 8.1. |
| A9 | Retain | Use Part of for multi-PR slices and Fixes for the single-PR case: §8.2. |
| A10 | Retire | PRs do not mirror issue planning fields or become Project items: §§8.7, 10.1. |
| A11 | Retire | Issue remains the canonical source for planning fields; use native linked-PR navigation: §§8.7, 10.1. |
| A12 | Revise | Keep useful current PR checks and map them into the one template: §8.4. |
| A13 | Revise | PRs record actual impact in the matrix and the reviewer verifies it; issue planning fields are not copied or synchronized: §§4.4, 8.4, 8.7, 10.1. |
| A14 | Supersede | AI-context is derived after 1.15; tracked files remain until replacement ships and is proven: §12.9. |
| A15 | Revise | Only a Triage issue may return to Backlog when the maintainer defers analysis; never from Ready, In Progress or In Review. Changed contracts return to Triage; abandoned work closes as Not planned: §§5.2–5.4. |
| A16 | Supersede | Fingerprint edits return Ready to Triage and linked PRs to draft: §§4.4, 5.4. |
| A17 | Supersede | Foundation 1.11 followed by governance releases 1.12–1.15: §18. |
| A18 | Supersede | The accepted v4.2 implementation plan, not the old list, sequences work: §§18, 20. |
| A19 | Retain | Overrides require maintainer rationale; no override label: §14.3. |
| A20 | Retain | Enforcement starts warn-only and is promoted per rule only after evidence: §§14.2, 14.4. |
| A21 | Retain | Initiative is optional and spans multiple milestones with a durable document: §§10.2, 10.3. |
| A22 | Retain | Use sub-issues only for real decomposition; no initiative parent issue workaround: §10.3. |
| A23 | Revise | Keep current shared/repository catalogs until reviewed migration; do not add duplicate catalogs: §§10.2–10.3, 15.1. |
| A24 | Retain | One planned-work form in Phase 1; optional consumer forms only after evidence: §§4.2, 19.4. |
| A25 | Retain | Bug reproduction and actual/expected behavior stay inside Problem: §§4.2, 17.2. |
| A26 | Retain | Acceptance criteria are numbered and observable, with When/then wording where useful: §4.2. |
| A27 | Retain | PR validation maps tests to acceptance criteria: §§4.2, 8.4. |
| A28 | Revise | Reviewer is separate and independent; roles are not fixed to named vendors: §§6.1, 13. |
| A29 | Supersede | The adopted v4.2 plan governs sequence; retrieval and MCP are later: §§18, 20. |
| A30 | Retain | PRD, area design, ADR, reference, guides, README and derived-artifact roles: §12. |
| A31 | Revise | Planner proposes Low/Medium/High from impact and reversibility; per-area floors are deferred: §7.1 and Appendix F B6. |
| A32 | Supersede | security remains a category label; advisories are private and follow-up work is Bug or Task: §§4.5, 10.3, Appendix F B4. |
| A33 | Revise | Current Issue Types are Task/Bug/Feature; category labels and branch routing remain separate pending migration: §§4.5, 10.3. |
| A34 | Revise | Read active decision records and area design; closed issues are archaeology, not current truth: §§3.2, 11.4, 12.13. |
| A35 | Supersede | Keep tracked context until the post-1.15 AI-generated export replacement ships and is proven: §12.9. |
| A36 | Revise | Fresh-session independence is required; different-tool is configurable and has repository-specific defaults: §6.1 and Appendix E 15–16. |

Appendix B's row dispositions are individually listed in Appendix F; the historical B rows above them are unchanged. In particular, B2 now refers to Backlog and Triage, and B14 follows the current reviewer-verifies/author-resolves rule in §§8.5, 9.3 and 14.6.
