# Base Governance Design

**Version:** 1.2 (review draft), 8 November 2026
**Owner:** Ramesh (codeforester)
**Status:** Revised design proposal for independent review; not yet adopted policy
**Intended home:** `docs/governance/DESIGN.md` in `basefoundry/base`
**Companion:** `docs/governance/IMPLEMENTATION-PLAN.md`, which sequences the proposed work

**Sources consolidated:** Base Direction Memo v12 (19 Oct 2026); Base Working Notes Parts 1–37 (22 Oct–2 Nov 2026); the supplied governance drafts (3 Nov 2026); current Base workflow, configuration, review and documentation contracts; and Ramesh's clarifications (7–8 Nov 2026).

### How to read this document

Each topic appears once, in its final form. Every section carries a status:

| Label | Meaning |
|---|---|
| **DECIDED** | Settled direction for this proposal. It becomes active policy only after the design PR is accepted and merged. |
| **PROPOSED** | Recommended design detail for review or a pilot. |
| **OPEN** | Not decided. Listed in §21. |
| **EXPLORATORY** | Ideas worth keeping, not commitments. |
| **DEFERRED** | Deliberately left for later (mostly Phase 2). |
| **NEW** | Added during the original consolidation. Appendix B records its origin; it is not a pending approval by itself. |

Appendix A lists earlier positions replaced by this revision. Appendices A and B are historical consolidation notes; the current body and Appendix E are authoritative. Reviewers should check that the current body and companion plan are internally consistent.

---

## 0. Summary

Base is built almost entirely by AI agents. Codex writes code, tests and docs; Claude Code reviews. Writing code is no longer the bottleneck. The bottleneck is knowing that what got built is what was meant, and keeping code, tests, docs, demos and decisions in agreement as the product grows. This design is Base's answer.

The core of it:

1. **The issue is the top of the flow.** Every change starts as a GitHub issue. The issue body holds the spec (what and why) and, after Triage, the plan (how). There are no spec files in the repo.
2. **Issues have a loop, like PRs.** A second, independent agent reviews the issue and its plan against the product's principles and active decisions before any code is written. Risk tier decides whether Ramesh must look too.
3. **The PR proves the issue's claims.** Every PR belongs to exactly one issue. Its sections answer what the issue promised, with evidence. Numbered acceptance criteria trace to tests.
4. **Fold-back.** Anything lasting reaches the repo's permanent documents in the same PR. The test: if the issue vanished tomorrow, would anything be lost?
5. **Six statuses:** Backlog → Triage → Ready → In Progress → In Review → Done. Triage is the active issue-analysis stage. Agents do not set Status; authorized maintainers or later automation do so from defined evidence.
6. **Area is the map of the product.** Every file maps to an area. Areas organize issues, design docs, decisions, reviews and drift checks.
7. **One home per kind of fact.** PRD for intent, area design docs for architecture and contracts, decision records for rationale, reference for exact facts, guides for how-to, and release notes for shipped change summaries.
8. **Governance lives in `governance/`** as definitions and plain-language rules. GitHub files are generated from it.
9. **Rollout in three stages,** split by automation level: run the loops by hand, then automate them, then add automated drift catching. A stage ends after about two weeks of real use without bypasses.
10. **Base proves the policy first.** Base's own repositories pilot it. Base-supported projects receive versioned defaults and opt in through repository-owned files; they do not inherit silent live changes from Base.

---

## 1. Purpose and scope

### 1.1 Problems this solves — DECIDED

From the Memo and the working notes:

1. **Review gap.** Since Claude Code began reviewing Codex PRs, about 60% have had at least one real issue. Earlier PRs were often merged after a glance.
2. **Drift.** Issues, PRs, design docs, user docs, tests, `demo.sh`, `base-demo` and `.ai-context/` fall out of sync. The nightly export of 2 Nov 2026 still described 1.10.5 as an active release line after it had shipped.
3. **Hidden requirements.** Agents miss rules that live only in the maintainer's head. The `basectl workspace test` trust case: the command warned about trust, then kept running tests on previously trusted projects with no per-project output. The missing piece was a product-wide convention, not a feature spec.
4. **Disconnect between intent and implementation.** Hand testing keeps finding gaps between what Ramesh meant and what was built, with no way to know how many remain.
5. **Incomplete and inconsistent metadata.** Issue Status transitions are skipped; Project field values accumulate with no retirement path; labels stand in for structured fields.
6. **Decisions lost in conversation.** Long chats get compacted and decisions vanish. Agents don't read past issues on their own.
7. **Human as glue.** Ramesh triggers agents and carries results between them by hand.

### 1.2 Scope — DECIDED

- **Phase 1 (this design's main subject):** Base's own governance, across `basefoundry/base` and its ecosystem repos (`base-cli`, `base-bash-libs`, `base-demo`, `homebrew-base`).
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
12. **One vocabulary.** One concept, one name: issue types and branch prefixes use the same names.
13. **Strict for insiders, welcoming for outsiders.**
14. **Use each GitHub feature for what it was built for.** Issue types classify, fields hold structured data, labels are plain cross-cutting tags.
15. **Inherit by reference, override by layering** (Phase 2).
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

1. **Conversation (free).** Ideas form in conversation with agents or on walks. No structure is imposed here.
2. **Issue.** The conversation produces an issue: the problem and what "done" looks like. This is the spec.
3. **Triage.** An agent writes the plan into the issue body. A second, independent agent reviews issue and plan. The risk tier decides whether Ramesh approves.
4. **PR.** Code, tests, docs and any decision record, in one change, as a draft.
5. **Review.** An independent agent checks that code, tests, docs and decisions match each other and the issue. The author and reviewer complete the bounded PR loop; the maintainer owns merge.
6. **Merge.** Decisions are accepted and frozen; docs are current; the issue becomes history.
7. **Release.** Release notes are assembled from the PRs' release-note lines.

Templates on that path: issue template (§4), plan (§4.3), PR template (§8.4), reviewer rule sets (§9), decision record (§11), area design doc (§12.6).

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
- A separate migration issue renames every currently open issue and open PR after the rule and templates are adopted, regardless of Project status or PR draft/ready state. Closed issues and merged/closed PR titles stay as historical records by default.
- Until the active-title migration is complete, readiness checks distinguish newly created items from existing open items; the migration exception is time-bounded and linked to its tracking issue.

### 4.2 Issue forms and implementation-ready contract — DECIDED

Keep type-specific GitHub issue forms for bug, feature, documentation, implementation, and support intake. Intake asks for information the reporter can reasonably know. During Triage, the owner and planner complete the shared contract for work that will be implemented:

| Section | Required content by Ready |
|---|---|
| **Problem** | What is missing or wrong, who is affected, and supporting evidence. Bugs include reproduction steps and actual versus expected behavior. |
| **Expected behavior** | Numbered, observable acceptance criteria. Use “When …, then …” where useful. |
| **Scope and non-goals** | Intended boundaries and explicit exclusions. |
| **Affected areas** | Each product area touched, with a short explanation. |
| **Impact and destination** | For each category, name the canonical file and section to update or state “No impact” with a reason: PRD/product intent; area design/contracts; user guide/README/FAQ; CLI/API/config/schema/reference; operations/security/privacy/migration; demos/examples; decision record; release notes. |
| **Validation impact** | Applicable unit, integration, contract/golden-output, end-to-end, and acceptance/dogfooding checks, with reasons for exclusions. |
| **Open questions** | Questions that block Ready; record rather than guess. |
| **Plan** | Approach, expected changes and PRs, confirmed impact dispositions, acceptance-to-test mapping, lasting decisions, risks, and questions for the maintainer. |

The contract is complete by Ready, not necessarily at intake. Before Ready, an impact may say “Unknown: reason.” At Ready, every category has a destination or a reasoned no-impact decision. Answers scale to the work; small changes can give brief, specific dispositions. Do not make a typo report complete a full test matrix before triage.

Compared with the current Base forms, the shared Ready contract normalizes Goal/Background into Problem, makes Expected behavior numbered, keeps Scope and Non-goals explicit, and turns Validation into planned evidence tied to acceptance criteria. The current body-level Project Fields section is removed because GitHub Project values are structured metadata on the issue, not prose to copy. Agent Assignment becomes role/actor provenance and is handled by the review process, not a field in the product specification. Type-specific intake prompts remain, then feed this common contract during Triage. This is the target layout; existing forms remain unchanged until an implementation PR updates them.

Bug reports should have a failing reproduction or regression check where practical. Each acceptance item maps to a test or an explicit acceptance check in the plan and PR.

### 4.3 The plan — DECIDED

The planner writes the plan in the issue body during Triage, not in a comment. It has six parts:

1. **Approach:** how the issue will be solved, prior art considered, and a meaningful alternative rejected with a reason.
2. **Delivery:** expected PRs and the outcome of each. One PR per issue is the default; if one issue needs several PRs, enumerate the complete planned PR set and the slice each will deliver.
3. **Impact, confirmed:** exact canonical files and sections, or evidence-backed no-impact decisions, plus the tests that cover each acceptance item.
4. **Lasting decision:** whether a decision record or area design/contract update is needed. A durable governance or product direction decision requires maintainer approval (§11).
5. **Risk:** likely blast radius, reversibility, risk tier, and mitigations.
6. **Questions for the maintainer:** anything requiring a human decision before implementation.

Once reviewed, the plan is frozen. A material change returns the issue to Triage and invalidates its previous approval (§5.4, §6.4). Ready requires the complete plan and a fresh approved verdict.

### 4.4 Readiness check — PROPOSED

The future basectl gh issue readiness contract should validate the mechanical portion before reviewer tokens are spent:

1. Applicable intake and implementation-ready sections are present and in the expected order.
2. The title follows §4.1, subject to the active-title migration exception.
3. Expected behavior is observable and numbered; bug reports contain reproduction and actual/expected behavior.
4. Every “None” has a reason; “Unknown” is allowed only before Ready.
5. The Area field matches at least one affected area, and every named area is active in the governed area map.
6. No retired field value or label is used on an open issue.
7. Risk tier meets the floor of every affected area.
8. For Ready, the plan is complete, the latest reviewer verdict is Approved, that verdict follows the last body edit, and its freshness period has not expired.

Issues created through the web UI, gh, or basectl must eventually receive the same readiness check. This is a design target; it does not claim the command or check exists today.

### 4.5 Issue Type and metadata — DECIDED

- GitHub’s native **Type** classifies the kind of work. Use the organization’s agreed issue types (Bug, Enhancement, Documentation, CI, Security, Task) and set the type through issue forms where supported.
- Type is distinct from the Project’s **Area**, which says where in Base the work belongs. Category labels remain only as a compatibility input while existing branch and intake tools depend on them; titles stay plain.
- GitHub organization-level **Issue Fields** are issue-only and cannot currently be prefilled by issue forms. Base will not create a second Issue Field for a value already represented by a Base Project field. Current Project metadata remains the operational source until a separate, evidence-backed migration is accepted (§10.1).
- Project metadata is set by the Project intake path, not inferred from free text in the issue body. Base-supported repositories can add optional custom fields without changing the meaning of native Type or GitHub issue fields.

### 4.6 Creating issues — DECIDED

- Any person or supported tool may create an issue; every issue follows the same readiness and review path.
- basectl gh issue create remains the preferred Base path for templates, category compatibility, Project intake, and provenance. Issue forms and direct GitHub creation remain valid entry points.
- A machine-owned provenance block may identify creator, planner, and reviewer. It must not claim a human reviewed work that was reviewed only by an automated agent.
- basectl does not own or invoke the chosen AI model merely to create an issue. Provider CLI invocation is explicitly scoped to generated context export (§12.9).
- Sweeps produce separate issues, not unreviewed PRs. Each issue passes through Triage and the same readiness bar.

---

## 5. Lifecycle

### 5.1 Statuses — DECIDED

The Base Project Status values remain **Backlog → Triage → Ready → In Progress → In Review → Done**. Triage is the analysis and issue-review stage; it is not renamed.

| Status | Meaning |
|---|---|
| **Backlog** | Captured but not yet selected for analysis. |
| **Triage** | Scope, acceptance criteria, impacts, risk and delivery plan are being completed and reviewed. |
| **Ready** | The issue contract and plan are approved; implementation may begin. |
| **In Progress** | Implementation is active, or at least one planned PR has not yet been opened. |
| **In Review** | Every PR in the approved delivery set exists and is GitHub Open or Merged. GitHub Open includes draft PRs. Review loops may still be active. |
| **Done** | Every PR in the approved delivery set is Merged or Closed. If any PR closed without merge, the issue records the outcome and resolution. |

Issue state (Open/Closed), Project Status, and PR state are related but distinct. The issue is the canonical owner of planning and Project metadata. The approved issue plan names the authoritative PR set; unrelated references do not change status derivation.

### 5.2 Status derivation — DECIDED

A maintainer may correct metadata. Agents do not directly choose Project Status. Later automation derives it from the issue plan and linked PR states:

| Evidence | Project Status |
|---|---|
| Issue created | Backlog |
| Work selected for analysis | Triage |
| Issue contract and plan approved | Ready |
| Implementation starts, or any planned PR is missing | In Progress |
| All planned PRs are Merged or Closed | Done |
| All planned PRs exist and each is Open or Merged | In Review |
| At least one planned PR is Closed while another remains Open or Merged | In Progress; the maintainer revises the delivery plan or records the disposition |
| Issue is closed as Not planned, Duplicate, or Cancelled | Done, with the close reason recorded |

A one-issue/multiple-PR delivery is listed in the approved plan before implementation. The issue remains In Progress while a planned PR has not been opened, or while the planned PR set has a closed-unmerged member and unfinished open work. It moves to In Review once all planned PRs are Open or Merged, and to Done once all are Merged or Closed. Evaluate completion before review: Done takes precedence over In Review. If no terminal or review condition applies, the issue stays In Progress. Intermediate PRs use a non-closing reference; only the final planned PR uses a closing reference when its merge completes the issue.

### 5.3 Completion and later work — DECIDED

Done is terminal for that issue history. A regression or follow-up discovered later gets a new issue linked to the completed issue. If all planned PRs close without merge, the issue may still become Done, but the maintainer records whether the work was cancelled, superseded, duplicate, or otherwise resolved; closed PRs alone do not imply successful delivery.

### 5.4 Returning to Triage — DECIDED

An implementation gap is fixed in its PR and does not change the approved issue plan. A material spec, scope, acceptance, or plan gap returns the issue to Triage and invalidates the issue approval. The plan is revised visibly, with a comment explaining why, and passes a fresh issue-review loop before work resumes. Existing PRs are moved to draft where appropriate; they stay linked and are not silently discarded.

Allowed backward moves are In Review to In Progress for implementation work, and Ready/In Progress/In Review to Triage for a material plan change. Backlog is not a reset state; abandoned work is closed with a reason. A code push after PR approval invalidates that approval and requires a fresh review of the new head SHA (§8.5).

---

## 6. Issue review loop

### 6.1 Roles and independence — DECIDED

The creator/planner proposes the issue contract and plan. An independent issue reviewer checks clarity, scope, acceptance criteria, documentation impact, security, risk, and conflicts with product principles or active decisions. The reviewer must not be the author of the content being reviewed; use a fresh session without authoring context. Medium and High risk work uses a different tool for review where available. A maintainer owns disputed direction and required escalations.

Tool and person assignments are repository policy, not product constants. Base may start with Codex as planner/implementer and Claude as reviewer; other Base-supported projects choose their own providers while keeping independence and evidence requirements.

### 6.2 Issue loop — DECIDED

1. Move the selected issue to Triage.
2. Complete the issue contract and delivery plan in the issue body.
3. The independent reviewer posts one consolidated review with numbered findings and a verdict.
4. The author responds to every finding, fixes it or explains the challenge, and updates the issue body when needed.
5. The reviewer verifies responses and posts a new verdict. A challenged finding that changes product direction or remains disputed goes to the maintainer.
6. Repeat for at most the repository-configured number of review rounds. The default is three. The initial reviewer evaluation is round one. If findings remain at the limit, stop and escalate to the maintainer; no implementation starts by timeout.
7. Only a current Approved verdict on the latest issue-body revision can move the issue to Ready.

### 6.3 Verdicts and staleness — DECIDED

The issue body is the current contract; comments are the review history. The author owns and edits the body. Reviewers do not rewrite it. Issue comments are not resolvable GitHub review threads, so each reviewer round ends with an explicit Approved or Changes requested verdict and numbered findings. An approval is stale after any substantive issue-body edit and must be renewed.

### 6.4 Ready approval — DECIDED

The planner never approves their own issue. Low-risk issues may be advanced by later automation after the readiness check and independent approval pass; in the manual pilot a maintainer performs the transition. Medium and High risk issues require maintainer review. Disputes, unresolved questions, new durable decisions, and changes to governance policy always go to the maintainer.

## 7. Risk tiers and priority

### 7.1 Risk tiers — DECIDED

Three tiers, named in plain words: **Low, Medium, High.** Three because there are exactly three handling paths (§6.4); a fourth tier would only make sense with a fourth behavior. Words, not R1–R4: numbers are ambiguous about direction and invite confusion with P1–P4.

Judged by **blast radius and reversibility:**

| Tier | Examples |
|---|---|
| **Low** | Docs, tests, internal refactors with no behavior change; one area; easy to undo. |
| **Medium** | A visible behavior change in one area (new command output, a new option); still easy to undo. A change to an area's Contracts is at least Medium. |
| **High** | Trust or security; deleting or changing user data; manifest schema; releases; CI gates; governance itself; several areas at once; anything hard to undo. |

**Rules:**

- When in doubt, pick the higher tier.
- **Ratchet:** the planner proposes; the reviewer may raise; only Ramesh may lower.
- **Area floor** (**NEW**, B6): each area may declare a minimum tier in `governance/areas.yaml`. The governance area is always High; trust, setup and release areas are expected to be High. The readiness check rejects a tier below the floor of any affected area.
- Phase 2: tier names and the ratchet are locked; per-tier examples are project-customizable.

### 7.2 Priority — DECIDED

**P1–P4. No P0.**

| Priority | Meaning |
|---|---|
| **P1** | Drop everything: main is broken, a release is blocked, or a security problem. |
| **P2** | Next up; needed for the current milestone. |
| **P3** | Should do, when time allows. |
| **P4** | Nice to have. |

- No P0: P0 comes from incident response ("production is down"). Base's tracker governs development, and P1 already means drop everything.
- **Agents propose a priority; Ramesh sets it.** Priority is a product judgment.

### 7.3 Priority and risk are independent — DECIDED

Priority decides **when** (the order of work). Risk decides **how carefully** (the path through review). A broken link on the front page can be P1/Low; a small cleanup in trust code can be P4/High.

---

## 8. Pull requests

### 8.1 Issue-to-PR relationship — DECIDED

The normal mapping is one issue to one PR. An issue may have multiple PRs only when the Ready plan enumerates the complete set, order/dependencies, and each PR's acceptance slice. Every PR belongs to exactly one issue; a PR never combines multiple issues. This keeps the planning and completion boundary auditable and avoids many-to-many delivery graphs.

The issue plan is authoritative for which PRs count toward lifecycle status. A missing planned PR keeps the issue In Progress. References in a PR description do not silently expand the approved delivery set.

### 8.2 Linking — DECIDED

Intermediate PRs use a non-closing reference such as “Part of #N”. The final PR uses “Fixes #N” only when its merge completes the full planned delivery. GitHub's linked-pull-request relationship is the navigational link; Project custom fields are not copied to PRs. The PR page and issue page remain distinct GitHub objects.

### 8.3 Draft and review state — DECIDED

A PR may start as draft so the author can develop and request an agent review before asking for human review. Draft is still GitHub state Open for issue lifecycle calculation. The PR review loop may proceed on a draft. Marking it ready for review indicates the author considers it ready for human attention; it does not itself change the issue's computed status. The maintainer is the merge authority. Agents do not merge or enable auto-merge.

### 8.4 Pull request template — DECIDED

The standard PR template has these sections, always present. A non-applicable item gives a brief reason:

| Section | Required content |
|---|---|
| **Summary** | Change and user/developer outcome. |
| **Issue and delivery slice** | Primary issue, whether this is the final PR, and links to other planned PRs when relevant. |
| **Plan followed** | Conformance or explained deviation; material plan changes return the issue to Triage. |
| **Validation** | Commands actually run and evidence; map checks to acceptance criteria. Mark checks not run and why. |
| **Documentation impact** | Design/contracts, user docs/FAQ/README, command/API/config/schema/reference, operations/security/privacy/migration, demos/examples, release notes; name changed paths or give reasoned no-impact. |
| **Decision record** | Record added/updated or reason none is needed. |
| **Demo impact** | Product demos and examples changed or reason none. |
| **Release note** | User-facing release line or reason no release note applies. |
| **Risk, rollback and notes** | Material risk, recovery path, and remaining tradeoffs. |

The template must not ask for duplicate Project metadata or a hand-maintained AI-context file. Provenance is recorded by GitHub actors and, if later adopted, a clearly marked automation footer. The template source and GitHub template are reconciled through a PR; generation is a future implementation choice, not an assumed current capability.

Compared with the current PR form, retain Summary, Issue, Validation, Demo impact, and Notes; make the issue link identify the delivery slice; add plan fidelity, documentation-impact categories, decision record, release-note disposition, and risk/rollback evidence. Remove any checklist item that asks the author to update a checked-in AI-context copy or repeat Project fields.

### 8.5 Review comments, responses and approval freshness — DECIDED

Each review round is one consolidated review with actionable findings. The author responds to every reviewer finding in its thread, stating what changed with a commit/reference or why it is challenged. The reviewer checks the response and resolves the thread only when the issue is addressed or the challenge is accepted as requiring no code change. A substantive dispute goes to the maintainer; the author cannot resolve their own reviewer thread. New findings from follow-up changes are recorded as additional review comments and return the PR to the author.

A review approval is bound to the exact PR head commit SHA. Any subsequent push invalidates that approval and requires a fresh review against the new head. Branch protection should dismiss stale approvals on code-changing pushes and require all review conversations resolved. If unresolved actionable findings remain after the configured number of rounds (default three), work pauses for maintainer judgment; unresolved comments are not auto-resolved to satisfy a gate.

### 8.6 Merge gate — DECIDED

Require passing checks and resolved review conversations. Require fresh approval bound to the current head SHA where GitHub's branch protection supports the selected reviewer identity. If automated approval cannot safely satisfy the branch rule, keep the independent review as a required human-operated gate during the pilot. No direct pushes to the protected branch, and no agent merge or auto-merge authority.

### 8.7 Project fields and linked PRs — DECIDED

Issues are the Project items and the canonical home for Status, Priority, Size, Area, Risk tier, Initiative, and Milestone tracking. Do not add PRs as separate Project items solely to mirror issue fields. Use GitHub's native linked-pull-request display on the issue to show delivery relationships. A PR keeps its own title, author, branch, checks, review state, and release evidence; there is no copied metadata to synchronize or reconcile.

## 9. Reviewer rule sets

### 9.1 Issue reviewer — PROPOSED

Mechanical readiness checks run first. The independent reviewer then checks problem clarity, observable acceptance criteria, truthful impact dispositions, fit with product principles and active decisions, plan soundness, risk tier, scope, security implications, and whether every lasting fact has a destination.

### 9.2 PR reviewer — PROPOSED

Mechanical checks cover the required PR sections, one primary issue, plain title, passing checks, acceptance-to-test traceability, release-note disposition, decision-record state, current-head approval, author responses, reviewer-resolved threads, and consistency between the planned PR set and issue status. Later drift checks compare changed paths, documentation claims, and affected areas. There is no PR-field mirroring check.

Judgment review covers plan fidelity, correctness and edge cases, meaningful tests, documentation fold-back, architecture and active decisions, and security. Reviewers classify each finding as an implementation gap or a spec/plan gap. A spec gap returns the issue to Triage; an implementation gap is corrected within the PR.

### 9.3 Review discipline — DECIDED

Every finding cites a rule and contains evidence, impact, and a requested action. The author responds to each finding; the reviewer determines whether it is addressed and resolves the corresponding thread. The configured round limits are separate for issues and PRs (§15.5). A material dispute or an unresolved finding at the limit goes to the maintainer. Rules that repeatedly catch the same defect should become deterministic tests or checks; rules that add friction without catching real defects are reviewed for retirement.

### 9.4 Coding and architecture standards — DECIDED

Use deterministic tools for formatting, lint, security scanning, schemas, generated files, and other checkable rules. Human or AI review focuses on architecture, behavior, edge cases, and judgment that tools cannot settle. Keep standards short and numbered; load only the sections relevant to changed paths. A recurring reviewer finding becomes a lint or test where practical. Specialist review passes may cover code, docs, tests, and demos, but report one consolidated review with one round number.

## 10. Metadata: fields, areas, initiatives, labels and relationships

### 10.1 GitHub metadata responsibilities — DECIDED

Use each GitHub construct for its purpose and avoid duplicate sources of truth:

| GitHub construct | Base use | Does not mean |
|---|---|---|
| **Type** | Native organization issue type classifies the kind of issue: Bug, Enhancement, Documentation, CI, Security, or Task. | Product area, priority, status, or PR category. |
| **Issue Fields** | Organization-defined structured metadata attached to issues. Use only when Base deliberately adopts a field as an organization-wide issue contract. | A Project view or a way to put fields on PRs. Do not create these as duplicates of existing Project fields. |
| **Projects** | Operational board and custom fields for planning. Each issue is one item in the repository Project. Existing Base custom fields remain canonical for Status, Priority, Size, Area, Risk tier, and Initiative; Milestone remains the native issue milestone. | A second issue or PR lifecycle, or the home of product requirements. |
| **Relationships** | Sub-issues express true issue decomposition; blocked-by/blocking relationships express dependencies; linked PRs show implementation delivery. | Initiative membership, duplicate Project items, or a replacement for the issue's delivery plan. |

A Project is a board over work items. Keep its custom fields when they serve Base's operational needs. Do not mirror them onto PRs. If Base later adopts an organization Issue Field for a value, migrate the canonical source through an explicit issue/PR train and remove the duplicate Project field; never maintain both as peer authorities. Native issue forms currently do not provide a general mechanism to prefill organization Issue Fields, so do not promise that intake experience until verified.

### 10.2 Field meanings — DECIDED

| Field | Where | Meaning |
|---|---|---|
| **Status** | Project field | Lifecycle state in §5. |
| **Priority** | Project field | Work order, P1–P4 under Base's current Project convention. |
| **Size** | Project field | Expected implementation size. |
| **Area** | Project field | Primary product/architecture area; full impact list remains in the issue body. |
| **Risk tier** | Project field | Review intensity floor and escalation path. |
| **Initiative** | Project field | Optional temporary goal grouping. |
| **Milestone** | Native issue milestone | Intended release or delivery window. |
| **Type** | Native issue type | Kind of work. |
| **Assignee** | Native issue assignment | Person accountable for issue outcome. PR author remains represented by PR authorship. |

Area answers where; Initiative answers which temporary goal; Milestone answers when. One issue has one primary Area and at most one Initiative. These are independent dimensions.

### 10.3 Areas and values — DECIDED

`governance/areas.yaml` is the proposed source for area names, descriptions, ownership, path patterns, minimum risk tiers, and active/retired state. It can later generate Project options and reviewer routing. Values are retired with a visible replacement path; they are not silently deleted while open issues still use them.

Labels remain cross-cutting tags such as needs-demo, help-wanted, and good-first-issue. Do not use labels to duplicate Type or structured Project fields. Project views group and filter issue items; standard views include Backlog, Triage, Ready, In Progress, In Review, and Done. Views do not add PRs as Project items for field mirroring.

## 11. Decision records

### 11.1 Format and ownership — DECIDED

Use lightweight Architecture Decision Records (ADRs): one durable decision per record, with context, decision, rationale and serious alternatives, consequences, status, area, date, and links to the originating issue/PR and affected design documents. The proposed home is `docs/decisions/`; exact directory and index layout are confirmed in the documentation inventory issue.

### 11.2 Lifecycle — DECIDED

- A decision record in an open PR is **Proposed** and carries no authority to implement the decision.
- A maintainer explicitly accepts the decision during review. The same PR updates the record to **Accepted** before merge; merge is the point at which it becomes active.
- Once accepted and merged, the decision content is immutable. Correct a typo without changing meaning if needed; a substantive change is a new record that links to and supersedes the old one. The old record receives only a status/link update.
- A rejected or abandoned proposal remains recorded as Rejected or Proposed with its disposition; an unmerged PR does not make a decision active.
- If a decision must be settled before implementation, use a decision-only issue/PR first; implementation follows under the accepted record.
- A generated index links active decisions by area and preserves historical records.

This lifecycle follows a common ADR pattern, not a universal standard. Fowler, MADR, and AWS guidance use proposed/accepted/rejected or superseded states and preserve accepted records rather than rewriting decisions. GDS guidance allows acceptance to be inferred from merge instead of an explicit status field. Base chooses explicit maintainer acceptance plus a same-PR Accepted status because it makes the human decision visible and testable.

### 11.3 Decision/document impact gate — DECIDED

The issue plan says whether the change introduces, changes, or supersedes a durable decision. The PR includes the record in the same delivery when acceptance and implementation are coupled, or links the earlier accepted record when implementation follows. The PR review verifies the status and linked impact destinations. An ADR records why; area design and user docs describe current architecture and behavior. They complement one another and are not substitutes.

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
| 6 | **Generated artifacts** | Release notes; exported AI context. | Nobody by hand. | Generated from their sources and written outside the repository |

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

- Command, option, manifest, configuration, and JSON reference should be generated from authoritative CLI help, schemas, or code where practical. Until a generator exists, a PR explicitly verifies reference changes against the shipped implementation.
- Every implementation PR supplies a user-facing release-note line or a reasoned “none.” Release preparation gathers those lines and checks completeness. `basectl release notes` automation is a target to verify and implement; this design does not claim that command exists today.

### 12.9 AI context — DECIDED

`.ai-context/` files are derived-context duplicates and will be removed from Base Foundry repositories only after the replacement `basectl export-context` is implemented and released. Until then, existing files remain available and are not removed as part of this design-document change.

The target `basectl export-context` invokes the selected installed AI tool's supported CLI to summarize relevant canonical repository documents and writes the result only to an explicit export location outside the repository. It does not maintain a second checked-in source of truth. The generated artifact identifies its source commit, generation date, and source paths; flags contradictions instead of resolving them silently; and excludes secrets and unapproved files. It is read-only with respect to the repository and must fail clearly if the selected tool is unavailable or the export destination is inside the repository. The command's provider interface, supported tools, privacy/data-transfer behavior, and offline/error semantics require an implementation issue and threat review.

After the released feature is proven, create separate issue/PR trains for removing `.ai-context/` from each Base Foundry repository, updating all references and any scheduled export jobs. Removal is a dependent rollout, not a prerequisite to shipping this design or implementation plan. A generated export is disposable output, not a tracked project document.

### 12.10 Catching drift, per kind — PROPOSED (**NEW**, B10)

Not discussed in detail yet. A first version for the review to react to:

| Kind | How drift is caught |
|---|---|
| PRD | Ramesh owns it; size check; High risk; reviewer flags PRD statements restated elsewhere. |
| README | Generated version and release links; quick-start commands run in CI; High risk. |
| Design docs | Fold-back check on every PR; reviewer; drift check scoped by area; area completeness check. |
| Decision records | Accepted entries may change only their status line (check); index regenerated and compared in CI. |
| Reference | Regenerated in CI and compared with the committed copy. |
| User guides | Examples run as doc tests; links checked. |
| FAQ | Each answer at most two sentences plus a link; links checked. |
| Release notes | Every merged PR has a release-note line or a reasoned "none"; release completeness check. |
| Exported context | Generated per run from allowlisted canonical files, stamped with source commit/date/paths, and written outside the repository. |
| AI context | Not stored, so it can't drift; each run is stamped and cites sources. |

### 12.11 When code and docs disagree — PROPOSED (from Codex's 1.11 draft)

- **Which source is authoritative for what:** code and tests for what the current build does (schemas and command definitions for exact fields and options); user docs for what users may rely on; area design docs for the implemented architecture; decision records for why; issues and PRs for how the work happened; the changelog for what a release contains.
- **Classify the mismatch first:** is the code wrong, is a document stale, or was the design deliberately changed? Then fix it in the same PR: fix the code, update the docs, add or replace a decision record, adjust tests.
- **If a known gap must ship,** open an owned follow-up issue that names the affected audience, the risk and the target release, so the gap is visible.
- **Never present a proposal as the implemented system.** Proposed designs are labeled as proposed.

### 12.12 Versioned docs — DEFERRED

Whether users of an older release see the docs for their version. Revisit when Base has more users.

---

## 13. Identities and attribution

### 13.1 Two situations — DECIDED

1. **Interactive agents on Ramesh's Mac** (Codex or Claude Code in a terminal or VS Code) act as Ramesh's account, `codeforester`. That's normal practice: the human started and supervises the session.
2. **Automated agents** (the loops in GitHub Actions, Stage 2) act as GitHub App bot identities, one per tool, for example `claude[bot]`. Narrow permissions, short-lived tokens, clearly not a person. Each tool's official GitHub App brings its own identity; Ramesh creates nothing. Codex's identity is to be verified.

**No machine account.** A second human-style account is allowed by GitHub if a person takes responsibility for it, but it's the older pattern. GitHub Apps are cleaner.

**The line:** a bot account means an automated agent; Ramesh's account means Ramesh, or an agent he is directly supervising.

### 13.2 Git history vs GitHub activity — DECIDED

- **Git history** lives in the repository and travels with every clone and mirror. Each commit records an author and committer (from the Git config of whoever made the commit) and optional trailers.
- **GitHub activity** (issues, comments, reviews, labels, fields, Actions) exists only on GitHub.

| | Stage 1 | Stage 2 |
|---|---|---|
| Commit author | Ramesh, including commits Codex makes locally | Ramesh for local work; the bot only if an agent commits from Actions |
| Agent attribution in Git | `Co-authored-by:` trailer naming the agent | Same |
| Agent attribution on GitHub | Provenance footer | Bot identity plus footer |
| Contributors graph | Ramesh only | Bots appear only if they author commits |

Co-authored-by trailers matter most, because they survive outside GitHub.

### 13.3 Provenance footer — DECIDED

GitHub records the account, not the tool. So issue and PR bodies end with a machine-owned footer:

- Issues: "Created by: Claude Code. Planned by: Codex. Reviewed by: Claude Code."
- PRs: "Written by: Codex. Reviewed by: Claude Code."

`basectl` stamps and extends it (`--created-by`, and equivalents per role). Only automation edits the footer. The footers feed the role-policy decisions (§6.1) and the proof metrics (which tool's issues needed the most rework).

---

## 14. Enforcement

### 14.1 Detect and correct, never silent — DECIDED

GitHub can't block a manual edit to an issue or Project field before it happens. Enforcement is a smoke detector, not a locked door:

1. **Event-triggered Action:** runs right after a change it can observe (issue closed, reopened, edited; PR events). If the change breaks a rule, it comments with the rule and the fix.
2. **Scheduled Action** (for example hourly): for changes Actions can't trigger on, likely Project field edits such as Status. Sweeps for violations and comments the same way.
3. Codex verifies which events GitHub Actions can trigger on for an organization Project, to decide what is instant and what is swept.

Rules enforced this way include: Done with an open linked PR; a Done issue with merged PRs reopened or moved back; a Status move with no matching signal; retired values on open items; a PR linked to zero or several issues.

### 14.2 Warn first, revert later — DECIDED

- **Stage 1: warn only.** The Action comments that a change breaks a rule; it doesn't revert.
- Reverting is switched on **per rule**, once that rule's warnings have proved accurate. A rule whose warnings turn out noisy stays warn-only until fixed.
- Why: automatically reverting a person's change goes beyond common practice and can feel heavy-handed; rules must earn it.

### 14.3 Override — DECIDED

- **The comment is the override.** No label. One comment grants permission and records the reason, so the two can't drift apart.
- **Format:** the comment's very first word is `Override:` (exact capitalization, with the colon), followed by a non-empty reason. "Override" anywhere else in a comment means nothing.
  > Override: closing without the second PR because the scope moved to #412.
- **Scope:** it allows only the next change that would otherwise be flagged or reverted. One use only.
- **Expiry:** unused overrides expire after 24 hours.
- **Only new comments count.** Editing an older comment to start with "Override:" does nothing.
- **Only non-bot accounts count.** In Stage 1, agents act as Ramesh's account, so the log is the safeguard.
- The Action records every override visibly so they're easy to find.

### 14.4 Pinned enforcement — DECIDED (Stage 2)

- Enforcement checks (readiness, PR checks, status rules) run a **pinned, released** version of Base, not whatever just merged to `main`. A bad merge can't break its own gate.
- The pin is upgraded deliberately, after a release proves itself.
- Same idea as the second laptop running only released Base: the checker isn't the thing being changed.

### 14.5 Branch protection — DECIDED

On `main`: required status checks (Tests, Security scanners, `base/issue-branch-policy`, governance checks as they arrive); require conversation resolution; no direct pushes; squash merge. Required approval per §8.6.

### 14.6 Automated review and fix security — DECIDED

Automation is untrusted-by-default and cannot turn review findings into privileged execution:

- Issue and PR review workflows use least-privilege tokens. Reviewers receive read-only repository contents and the narrow pull-request permission needed to post reviews and resolve addressed threads; they cannot push code, change branch protection, approve their own work, merge, release, or access deployment secrets.
- Do not use `pull_request_target` or another privileged event to check out, execute, install, or evaluate untrusted PR content. Fork PR workflows receive no secrets. Treat PR text, changed files, issue content, and generated context as prompt-injection-capable data.
- Any automated fix runs only after an explicit trusted maintainer trigger, in an ephemeral isolated environment, without secrets and without network access unless a reviewed step strictly requires it. It may produce a patch on the PR branch but cannot approve, resolve its own review threads, merge, or release.
- Validate the proposed patch in the same isolation. A fresh independent reviewer checks the resulting head SHA; any new push invalidates approval. Maintainer review remains mandatory for disputed findings, security-sensitive changes, and round-limit escalation.
- Pin workflow actions and model/tool versions where possible; cap usage; record actor, model/tool, commit SHA, prompt/rule version, and outcome without storing secrets or unnecessary private data. Document provider data handling and retention before sending private repository content to an external model.

---

## 15. Governance as code

### 15.1 Governance sources — DECIDED (layout PROPOSED)

Human-readable governance documents live in `docs/governance/`, including this Design and its implementation plan. Machine-consumable policy, templates, rule sets, and value definitions live in the root `governance/` directory. The root `base-governance.yml` contains the repository's selected runtime review-loop settings. `.github/` holds only files GitHub requires in fixed locations and should be generated from the relevant canonical sources when that generation exists. No generated copy becomes a second authority.

Proposed layout:

```
docs/governance/
  DESIGN.md
  IMPLEMENTATION-PLAN.md
  METHOD.md               plain-language process overview
governance/
  areas.yaml              areas, path patterns, minimum tiers, status
  fields.yaml             statuses, priorities, sizes, tiers
  initiatives.yaml        initiative values and status
  labels.yaml              labels and status
  roles.yaml               role policy and tool commands
  templates/
    issue.md               issue template source
    pull-request.md        PR template source
  rules/
    issue-review.md        issue reviewer rule set (numbered)
    pr-review.md           PR reviewer rule set (numbered)
  standards/
    architecture.md        numbered architecture rules
    bash.md                numbered Bash rules
    python.md              numbered Python rules
base-governance.yml        repository-selected governance settings
```

Generated from canonical sources: `.github/ISSUE_TEMPLATE/*`, `.github/pull_request_template.md`, labeler and CODEOWNERS-style config where used, and the Project's field options. A future CI check compares generated files against the source and reports the regeneration command. Existing `.github/base-project.yml` and `base_manifest.yaml` policy remain authoritative for current tooling until a migration issue and PR move each contract.

Governance stays inside Base while its boundaries are being proven. Phase 2 may package versioned defaults for Base-supported projects, but the repository keeps an auditable copy and receives updates through explicit PRs (§19). Skills are deferred (§16).

### 15.2 Phase-1 habits that keep Phase 2 cheap — DECIDED

Every Phase 1 PR is reviewed against these:

1. All governance source of truth lives in `governance/`; `.github/` files are generated, never hand-edited.
2. Values (areas, labels, field options, tiers, priorities, statuses) live in definition files, never hardcoded in Bash or Python.
3. Tier names and the ratchet are treated as locked from the start; per-tier examples are kept separate.
4. Base-specific content (Base's own areas, labels, examples) is kept apart from generic defaults.
5. Enforcement code reads definitions rather than embedding them, so the same checks can run against any project's files later.
6. Method prose stays tracker-neutral; GitHub specifics live only in generated files and adapters.

### 15.3 AGENTS.md — DECIDED

AGENTS.md is a **map, not a manual.** It holds only the rules an agent must follow in every session, and points to everything else:

- Issue first; use `basectl gh` for issues and PRs; never set Status.
- Plain titles; one issue per PR; "Part of" and "Fixes."
- Read the area's design doc and active decisions before changing it (§11.4).
- The decision-capture rule (§11.4).
- Standards: `governance/standards/`.
- Attribution: footer and Co-authored-by trailer.
- Ask before touching trust, release or governance paths.

It carries an owner and a last-reviewed date. A rule agents keep breaking becomes a check, not more text.

### 15.4 Tracker neutrality — DECIDED

The method, the template sections, the statuses and the gates stay the same on any platform. Supporting GitLab or Bitbucket means adapters that call different endpoints and generate different files. GitHub only for now; other adapters are built only when there is demand.

### 15.5 Repository-owned loop configuration — DECIDED

Review limits are configuration-as-code, shared in the repository and reviewed like other governance changes. They are not stored only in a maintainer's machine-local `~/.base.d/config.yaml`.

The proposed root file `base-governance.yml` has one independent limit for each loop:

```yaml
governance:
  loops:
    issue_max_rounds: 3
    pull_request_max_rounds: 3
```

Three is the initial default. The first reviewer evaluation is round one. Values must be positive bounded integers; exceeding the configured count escalates unresolved findings to a maintainer and never auto-approves or auto-resolves them. The exact upper bound is set by the implementation issue after a cost and usability review.

`basectl config` should gain an explicit repository scope for showing and changing these settings, while retaining the existing machine-local scope for user preferences. Repository commands read and validate the tracked file; a config change creates an ordinary diff for review. The exact CLI spelling is an implementation issue and must not silently fall back to local state when repository scope was requested.

Base-supported repositories receive versioned defaults from the Base release when initialized or explicitly configured. They do not dynamically inherit live values from Base. Existing projects receive a proposed update only through an explicit upgrade preview and PR; a project may override supported settings in its own file. This gives adopters a useful default while keeping their effective policy visible, reproducible, and under their control.

---

## 16. Skills — DEFERRED

Do not add Superpowers or another skill framework as part of the initial governance rollout. First pilot the issue and PR specifications, review loops, documentation-impact tracking, decision records, and drift checks using repository-owned templates, rules, and deterministic tooling. Revisit skills only if evidence from the pilot shows a concrete gap in spec-driven development or documentation-drift prevention that the governance design does not cover. Any later skill proposal must receive its own issue and security review.

## 17. Testing and proof

### 17.1 Test types — DECIDED

Unit; integration (`tests/integration/`, temporary homes and fake projects); contract and golden output; end-to-end (Base Demo E2E on macOS); acceptance and dogfooding. Static checks (ShellCheck, Bandit, pip-audit, Gitleaks, CodeQL, linters) run on every PR. Fast small tests on every PR; slower ones on `main` and nightly.

### 17.2 Testing rules — DECIDED (from Memo §13)

1. **Bug-first:** every user-found bug gets a failing test before the fix.
2. **Journey tests:** real demo flows end to end, plus failure journeys (untrusted project, invalid manifest, missing repo).
3. **Nightly run** on a clean macOS runner, with failures filed as issues automatically.
4. **Coverage audit** against the command surface and journeys.
5. **Intentional dogfooding** through BankBuddy, Bleach and Blend.
6. **Demo readiness:** the nightly journey suite is green before any demo.
7. **Workspace command contract:** fan-out workspace commands preflight the whole selection (trust, manifest validity, eligibility) before running anything, announce each project, and end with a summary, through one shared preflight helper, with a contract test.

### 17.3 The dogfooding machine — DECIDED

A second laptop runs **only released Base from Homebrew**, never a source checkout, for Bleach, BankBuddy and similar work. That exercises the release and upgrade path. A Base problem found there gets an issue filed there and fixed only on the main machine.

### 17.4 Proof plan and metrics — DECIDED

- Prove Base on projects of three sizes: simple (Blend, Bleach), medium (BankBuddy), complex (Banyan Labs). Roughly three to six months. Go public only when the proof is clear.
- **Metrics, defined before starting:**
  - drift incidents per month;
  - PRs needing rework after merge;
  - follow-up issues linked to a Done issue (problems that escaped review);
  - spec-gap rate (PR findings classified as spec gaps);
  - wrongly "small" claims caught by the PR-vs-issue check;
  - how often Ramesh had to step in by hand;
  - share of PRs with real review findings;
  - which tool's issues needed the most rework (from footers);
  - rules that never caught anything (monthly).
- **Baseline, captured now** so later results mean something: about 60% of Codex PRs had real review findings; the count of disconnects found by hand testing; the counts from the docs-vs-code drift audits.

### 17.5 Self-assessment and self-healing — DECIDED

- **Reflexes:** gate checks catch a problem the moment it appears.
- **Deliberate healing:** periodic audits find patterns, ask why, and add a new reflex. Over time each audit should find less.
- **Never silent:** every correction becomes an issue and goes through analysis and approval like any other change. A system that rewrites its own rules without oversight is how incidents happen.
- **Monthly review:** which rules caught nothing? Candidates for retirement.

---

## 18. Rollout

### 18.1 Two phases — DECIDED

- **Phase 1:** Base's own governance, across its ecosystem repos. Runs for real and matures.
- **Phase 2:** governance as a product for Base-managed projects (§19), designed after Phase 1 shows which rules needed to bend. Matches Base's existing decision to solve its author's real workflow well before generalizing.

### 18.2 Three stages, by automation level — DECIDED

Both loops exist from Stage 1; they're run by hand first. Prove the process before automating it.

| Stage | What switches on |
|---|---|
| **1. Foundation, run by hand** | Issue template (with numbered "When …, then …") and PR template (with traceability); readiness check; six statuses including Triage; reviewer verdict gating Ready; resolved conversations before merge; decision log; Risk tier field; warn-only status rules; overrides. Ramesh runs both loops by hand: Codex writes and fixes, Claude reviews, three rounds. About ten real issues. |
| **2. Loops automated** | GitHub Actions run the issue and PR loops with bot identities; role policy; Low tier reaches Ready automatically; enforcement on a pinned release; provenance footer automated; issue-owned Project fields with linked PR display; required bot approval if supported; reverting switched on per proven rule. |
| **3. Drift catching** | PR-vs-issue claim checks (changed files vs claims; computed areas vs Affected areas); fold-back check; fields, labels, areas and initiatives as code with retirement; issue-type migration; per-kind doc drift checks. |

**Leaving a stage:** after about two weeks of real use without anyone needing to bypass it. **Against rigidity:** don't switch everything on at once; retire rules that catch nothing.

The order of work, issue breakdown and exit reviews are in the implementation plan.

---

## 19. Phase 2: governance as a product — DEFERRED

Direction recorded so Phase 1 doesn't close doors.

### 19.1 Two kinds of governance

1. **Base's own:** how Base is built. Stays in the Base ecosystem.
2. **Governance as a product:** defaults Base offers to other projects.

### 19.2 The conduit

- Base-owned defaults, including the governance configuration schema and initial loop limits, ship as versioned templates with Base. Each adopting repository has a root `base-governance.yml` as its local, reviewable configuration source. `basectl repo configure` may create this file only when absent and must not silently overwrite project choices.
- `basectl repo configure` materializes selected defaults into the project repository, plus a pointer in the project's AGENTS.md. New projects receive the version bundled with their installed Base; existing projects receive updates only through an explicit upgrade preview and a PR. Projects do not inherit live values from Base.
- The project's agent never needs to know Base exists; it reads files in its own repo. Per-project values may customize supported settings, including loop counts, but are bounded and validated.
- The manifest **points, it doesn't dictate:** a `governance` entry in `base_manifest.yaml` names where the files live (default `governance/`). A project that doesn't declare it hasn't opted in.

### 19.3 Ownership classes

- **Managed:** Base owns and updates them (default templates, statuses).
- **Project-owned:** the project's own (areas, labels). Base never touches them.
- **Locked:** a small floor of rules that can only be tightened: human-only merge; independent review; trust gates; IDE mutation consent; secret scanning; reviewer least privilege; tier names and the ratchet; no label-as-field; issues pass the template check before Ready. What else goes in the locked set is OPEN; keep it small.

### 19.4 Overrides and upgrades

- A project-owned **overlay** file holds customizations ("use Base's defaults, except …"). Base reads it, never writes it. Each entry names a stable target, the kind of change, and a required reason.
- **Users never edit managed files.** `repo configure` never patches or merges: it takes Base's latest defaults, applies the overlay, and regenerates the managed files.
- Base fingerprints each generated file. A hand-edited managed file is detected, never overwritten, reported, and the change is suggested for the overlay.
- Upgrades arrive as a PR showing exactly what changed. Projects pin a Base contract version; `basectl repo upgrade --dry-run` previews changes and conflicts; `basectl repo config show --effective` shows where each setting came from.
- Proven patterns: ESLint configs extending a shared base; Kustomize patches over base files; Copier and cruft three-way updates.

### 19.5 Per-project choices

- Each project picks its AI tools through the role policy.
- Per-tier examples are customizable; tier names and the ratchet are locked.
- Every Base-managed project gets a governance area automatically.
- A project's manifest may declare which surfaces it has (demo script, demo repo, test types), so its generated templates include exactly those sections, consistently for every issue in that repo.
- Validate on BankBuddy first.

### 19.6 External contributors

- Branch-name rules apply only to same-repo branches. Fork PRs skip name checks and are validated on what matters: a linked issue with exactly one type. Failure messages say exactly what to fix; maintainers may create or link an issue for a newcomer; CONTRIBUTING.md explains kindly. Squash merge keeps fork branch names out of history.
- Agent loops don't run on fork PRs: fork workflows get no secrets, and untrusted content can carry prompt injection. Later, the `ai-review` label lets a maintainer request a read-only review. The auto-fix step never runs on external PRs.

---

## 20. Later and out of scope

- **Docs MCP server** (1.12 candidate): a remote server Claude can reach from a phone, with read-only tools (list active decisions, read a design doc section, search docs) and one write tool: create an issue in Backlog only. Ideas from walks then enter the normal loop; nothing bypasses the gate. Comes after the docs are trustworthy, since an MCP server serving drifted docs spreads drift faster.
- **RAG** (1.13 candidate): only if plain search falls short. Base's docs may be small enough that it's never needed.
- **Other trackers:** adapters only on demand (§15.4).
- **GitHub platform features:** Dependabot and CodeQL enabled; Discussions kept for questions and ideas; reusable workflows adopted and called at pinned versions; sub-issues used for genuine hierarchy, not for initiatives.

---

## 21. Open questions

| # | Question | When/how to settle |
|---|---|---|
| O1 | Which GitHub events reliably expose repository Project Status changes, and which require scheduled reconciliation? | Read-only implementation spike before status automation. |
| O2 | Can a GitHub App reviewer identity satisfy the configured required-approval rule while preserving head-SHA freshness? | Verify against a test repository before enabling automated approvals. |
| O3 | Which hosted AI actions/providers, credentials, data-retention terms, and usage controls are acceptable for Base? | Security review before any external-model workflow. |
| O4 | Which exact `basectl config` command syntax and schema bounds should expose repository-scoped loop settings? | Config implementation issue; preserve current local config behavior. |
| O5 | What provider CLIs and privacy/network modes will generated context export support? | Threat-model and implementation issue before build. |
| O6 | What is the final area list, owner map, and file mapping? | Area inventory issue. |
| O7 | Confirm decision-record, design, initiative, and guide directory locations against the documentation inventory. | Documentation migration issue. |
| O8 | Should the `blocked` label be replaced by GitHub issue dependency relationships? | Metadata migration issue after a live-use check. |
| O9 | What small set of rules is locked for Phase 2 adopters? | Phase 2 design, after Phase 1 pilot. |
| O10 | How should the existing community-triage guide and public intake stages map to the internal lifecycle without confusing newcomers? | Separate docs issue after the governance design is reviewed. |
| O11 | Does governance work move the 1.x freeze target? | Maintainer roadmap decision. |

---

## Appendix A. Superseded positions

This appendix lists earlier positions and the position adopted during the original 3 November consolidation. Its “Position at consolidation” column is historical, not current policy; the main body and Appendix E state the current proposal. "WN" means Working Notes; "Memo" means Base Direction Memo v12. Where a change happened in conversation without an explicit "supersedes" note, it is marked *(silent)*.

| # | Topic | Earlier position | Position at 3 November consolidation (historical) | Changed by |
|---|---|---|---|---|
| A1 | Reviewer identity | Claude Code reviews as Ramesh's second GitHub account, set up as a machine account (Memo §4.1, §11; WN2 §4). | No machine account. Stage 1: agents act as Ramesh's account, with attribution through the provenance footer and Co-authored-by trailers. Stage 2: automated loops run as each tool's GitHub App bot. | WN29, WN30 |
| A2 | Merge gate | Branch protection requires an approving review from an identity other than the author (Memo §4.1). | Stage 1: required checks plus resolved conversations; Ramesh merges. Required approval returns in Stage 2 only if bot approvals can satisfy branch protection. | Q4, 3 Nov 2026 |
| A3 | Project Status values | Backlog, Triage, Ready, In Progress, In Review, Done; new issues enter Triage (Memo §9). | Six statuses: Backlog, Triage, Ready, In progress, In review, Done. No Triage status. | WN2 §5 |
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

## Appendix B. Reconciliations made during the original consolidation

These entries explain the original 3 November choices. They are historical context only; the current body and Appendix E supersede them where they differ.

| # | Gap | Resolution in this document | Why |
|---|---|---|---|
| B1 | Bugs needed reproduction steps (WN1), but every issue must keep the same sections (WN9). | Bug-type issues put reproduction steps and actual vs expected behavior inside **Problem**. The readiness check enforces this for type Bug only. | Keeps one layout for every issue while still requiring what a bug needs. |
| B2 | "Every impact needs a reason" (WN1) vs Codex's 1.11 draft allowing "Unknown" at issue time. | "Unknown: reason" is allowed while an issue is in Backlog or Triage. Ready requires every impact to be Yes or None, each with a reason. | Issue authors often can't know impacts before anyone reads the code; analysis is where they get resolved. |
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

Carried from Memo v12 §21, unchanged, so it isn't lost. It finds durable decisions recorded in closed issues and merged PRs that never reached the docs. Run it after the docs-vs-code audit settles, with Codex and Claude Code independently, and compare: findings both report are high confidence. Confirmed findings become documentation issues and decision records (§11.5). Save it as a repo-owned prompt (rendered with `basectl prompt`); it may later become part of the drift-check skill (§16.5).

**Prompt (copy as-is):**

```text
You are auditing the Base repository (basefoundry/base) for drift between GitHub issue/PR history and the project's documentation. Do not modify any files, issues, or PRs. Produce a report only.

GOAL

Find durable decisions recorded in GitHub issues and pull requests that are missing from, or contradicted by, the current documentation. Documentation means: docs/ (design and user docs), README.md, CHANGELOG.md, AGENTS.md, CONTRIBUTING.md, and .ai-context/.

A "durable decision" is a choice about product scope, behavior, command semantics, flags, defaults, output formats, safety or trust rules, workflow conventions, naming, platform support, or architecture boundaries that should still guide future work. Bug fixes, refactors, typos, and one-off chores are NOT decisions unless their discussion established a rule (for example, "workspace commands must preflight all projects before executing").

SCOPE

1\. Use the GitHub CLI (gh) to list closed issues in basefoundry/base that were resolved by a merged PR (Fixes #N or Refs #N). Include the linked PR descriptions and review discussions.

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

## Appendix E. Maintainer clarifications recorded 8 November 2026

The following directions are incorporated into the current body and supersede earlier conflicting notes:

1. Keep Triage between Backlog and Ready. Use separate repository-configured issue and PR review limits, initially three rounds each.
2. Default to one issue per PR. If an approved issue needs multiple PRs, enumerate them in its plan. Keep the issue In Progress until all planned PRs exist; move it to In Review when all are Open or Merged; move it to Done when all are Merged or Closed, recording disposition for unmerged closures.
3. Require author responses to reviewer findings. The reviewer verifies and resolves addressed findings. Disputed findings and round-limit exhaustion go to the maintainer. Approvals are tied to the PR head SHA; a code push requires fresh review.
4. Keep issue Project fields canonical. Do not mirror them to PRs or create PR Project items for that purpose. Type, Issue Fields, Projects, and Relationships have distinct roles (§10).
5. Keep issue and PR titles plain. After adoption, rename every open issue and open PR regardless of Project status or draft state. Preserve closed issue and merged/closed PR titles as history by default.
6. Treat ADR preservation and supersession as common practice rather than a universal standard; Base requires explicit maintainer acceptance and an Accepted status in the PR that activates the decision.
7. Do not remove `.ai-context/` from Base Foundry repositories until the replacement `basectl export-context` is implemented and released. Then remove the files and update references through separate repository issue/PR trains.
8. Defer Superpowers skills until a manual governance pilot demonstrates a gap in spec-driven development or drift prevention.
