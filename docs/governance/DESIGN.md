# Base Governance Design

**Version:** 1.3 (review draft), 9 November 2026
**Owner:** Ramesh (codeforester)
**Status:** Revised design proposal for independent review; not yet adopted policy
**Intended home:** `docs/governance/DESIGN.md` in `basefoundry/base`
**Companion:** `docs/governance/IMPLEMENTATION-PLAN.md`, which sequences the proposed work

**Sources consolidated:** Base Direction Memo v12 (19 Oct 2026); Base Working Notes Parts 1–37 (22 Oct–2 Nov 2026); the supplied governance drafts (3 Nov 2026); current Base workflow, configuration, review and documentation contracts; and Ramesh's clarifications (7–9 Nov 2026).

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

Appendices A and B preserve the original 3 November history verbatim. Appendix E records maintainer decisions made since then; Appendix F gives the disposition of each original B item. The current body and companion plan are authoritative.

---

## 0. Summary

Base needs a repeatable way to turn product intent into reviewed issues, tested implementation, accurate documentation, and recorded decisions. This proposal defines that governance contract for Base first, with a later path for Base-supported projects.

1. **Issues are the planning record.** Each issue contains a problem, observable acceptance criteria, document-impact decisions, and an implementation plan. One issue is the default for each PR; planned multi-PR work is tracked as named delivery slices.
2. **Both issues and PRs have bounded review loops.** Each repository configures separate limits, initially three rounds. An independent reviewer uses a fresh session; whether it must use a different AI tool is configurable. Unresolved findings go to a maintainer at the limit.
3. **PR review is evidence-based.** Authors respond to every finding; reviewers verify and resolve addressed threads. A current-head verdict is recorded manually while agents share one GitHub identity. Required approving reviews stay at zero.
4. **Documentation impact is explicit.** Issues and PRs use the same canonical impact categories. Every category names its destination or gives a reasoned no-impact disposition. Decisions, design, user guides, reference, release notes, tests and operational guidance each have a defined home.
5. **One status model drives work.** Backlog → Triage → Ready → In Progress → In Review → Done. Triage is explicitly re-sequenced and redefined from today's project schema. Draft PRs keep their issue In Progress; delivery slices determine later transitions.
6. **GitHub metadata has distinct roles.** Native Issue Type classifies work; Project fields track operational planning; labels support cross-cutting categories and current branch policy; milestones plan releases; relationships express dependencies and hierarchy. PRs do not mirror issue fields.
7. **Repository configuration is versioned.** Loop limits and small operational governance settings live in `base_manifest.yaml` under `governance:` and are changed through repository-scoped `basectl config`. First-party repositories may keep detailed rule sets and templates in `governance/`; consumer projects do not have to add that directory.
8. **The rollout is evidence-gated.** Start with a manual first-party pilot, automate deterministic checks next, and add bounded AI automation only after its security controls are proven. Consumer governance remains deferred until the pilot shows what should generalize.

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
- A separate migration issue renames every currently open issue and open PR after the rule and templates are adopted, regardless of Project status or PR draft/ready state. Closed issues and merged/closed PR titles remain historical by default.

### 4.2 Single issue form and Ready contract — DECIDED

Use one planned-work form with the same sections in the same order for every issue type and size. Support questions route to Discussions; vulnerability reports use private security advisories. The form is an intake aid, not the enforcement boundary: `gh issue create`, API-created issues, and blank issues may bypass GitHub forms, so the readiness check validates the issue body and its current native Type.

| Section | Required by Ready |
|---|---|
| **Problem** | What is missing or wrong, who is affected, and supporting evidence. A Bug includes steps to reproduce and actual versus expected behavior. |
| **Expected behavior** | Numbered, observable acceptance criteria; use “When …, then …” where it clarifies the contract. |
| **Scope and non-goals** | Intended boundaries and explicit exclusions. |
| **Affected areas** | Each product area touched, with a short explanation. |
| **Impact and evidence** | For every canonical category in §12.10, name the expected file/section or state “No impact” with a specific reason. Category 6 records tests and acceptance checks mapped to criteria, plus evidence-based reasons for exclusions. “Unknown: reason” is allowed only before Ready. |
| **Open questions** | Questions blocking Ready; do not guess. |
| **Plan** | Delivery slices, approach, exact file/section changes, decision impact, validation, risks, and maintainer questions. |

At Ready, the checker evaluates the issue's current type. Changing Type after Ready is a substantive contract edit and makes the Ready verdict stale. Bug-first is strict: every bug a user found gets a failing test before the fix. If a test genuinely cannot capture the bug, the implementation PR explains why; the pilot counts these exceptions so the rule can be reviewed against evidence.

### 4.3 The plan and delivery slices — DECIDED

The planner writes the plan in the issue body during Triage, not in a comment. It contains the approach and rejected alternative, scope, confirmed documentation impact, acceptance-to-validation mapping, decision impact, risk, and maintainer questions.

The plan names delivery slices `S1`, `S2`, … and the outcome of each. A slice is the unit of completion; it does not name a permanent PR number. Each PR declares its slice. One PR per issue is the default. A slice without a PR names its reviewable completion evidence and the maintainer who will accept it. A replacement PR may deliver the same slice after the earlier PR is explicitly marked superseded; changing a slice's outcome or acceptance criteria is a material plan change and returns the issue to Triage.

### 4.4 Readiness and issue approval — PROPOSED

The future readiness command validates the common section order, non-empty Problem and Expected behavior, current Type-specific requirements, affected areas, all impact dispositions, test/acceptance mapping in category 6, delivery slices, and open questions. A Bug always requires reproduction steps in the issue. The test-impossibility exception applies only to the failing-test rule for the implementation PR (§17.2). A proposed Risk tier must be present when the field is introduced; area floors are deferred until the field and pilot exist.

A Ready verdict cites a fingerprint of Problem, Expected behavior, Scope and non-goals, delivery-slice outcomes, and the current Type, excluding comments and machine-owned metadata. Editing those inputs or changing Type invalidates approval. A Ready issue older than the configured 30 days is returned for review; `governance.ready_approval_max_age_days` stores the value. New affected areas or documentation destinations found during implementation are recorded in the PR's actual-impact matrix and verified by its reviewer; they do not invalidate Ready by themselves. A maintainer can return an issue to Triage when new evidence materially changes the approved contract or plan.

### 4.5 Issue Type, category labels, and branch policy — DECIDED

The organization currently exposes native Issue Types **Task, Bug, and Feature**. Do not document or configure Bug, Enhancement, Documentation, CI, or Security as native types. GitHub type is the work classification. The accepted category labels (`bug`, `enhancement`, `documentation`, `ci`, `security`) are separate labels, not a second type system. The current branch policy reads exactly one category label to choose its branch prefix; notably `bug` overlaps semantically with the native Bug type. Keep that behavior explicit until a separately reviewed migration changes the policy.

Vulnerability reports go through private advisories, not public issues. Follow-up work is tracked as a Bug or Task. Whether `Feature` should be renamed/replaced by `Enhancement`, and whether branch policy should read Type instead of category labels, remains an implementation decision for a dedicated migration issue.

### 4.6 Creating issues — DECIDED

Conversation may produce an issue through the chosen AI tool or `basectl gh issue create`. Repository issue/PR operations do not invoke AI services. The explicit exception is the approved `basectl export-context` design: it may invoke a user-selected installed provider CLI under §12.9's privacy and security controls. The issue creator proposes no undocumented policy; the independent reviewer checks the issue against current docs and decisions.

## 5. Lifecycle

### 5.1 Statuses — DECIDED

The target sequence is **Backlog → Triage → Ready → In Progress → In Review → Done**. This deliberately re-sequences the current schema, where Triage precedes Backlog, and changes Triage from initial classification to active clarification, planning, and review. The schema option order and descriptions, `docs/github-workflow.md`, and internal lifecycle guidance must migrate together. Public community triage is a separate contributor-facing process; its relationship to the internal status is an open documentation question, not a silent rename.

- **Backlog:** accepted work not yet analyzed or scheduled.
- **Triage:** the issue contract and plan are being clarified and reviewed.
- **Ready:** the plan has a current approved verdict and can be implemented.
- **In Progress:** implementation is active, or any planned PR remains draft/not ready.
- **In Review:** every planned slice has reviewable evidence: a non-draft PR or an explicitly reviewable non-PR evidence item; merged slices also satisfy this condition.
- **Done:** every planned slice is merged or has an explicit maintainer-approved completion/cancellation disposition. A closed-unmerged PR alone never makes an issue Done.

### 5.2 Status derivation — DECIDED

The plan is authoritative for the approved set of delivery slices; PRs point to a slice, and the most recent non-superseded PR for that slice is current. Replacing a PR for the same slice does not change the plan or count as a new slice. Derivation begins only after implementation starts. Before then, Backlog, Triage, and Ready remain as explicitly set.

| Evidence across all planned slices | Derived issue Status |
|---|---|
| At least one slice is being implemented, has a draft/not-ready PR, or has no reviewable evidence yet | **In Progress** |
| Every slice has a non-draft PR or reviewable non-PR evidence, and none is blocked by an unresolved closed-unmerged PR | **In Review** |
| Every slice is merged or has an explicit maintainer-approved terminal disposition; all required evidence is recorded | **Done** |

A closed-unmerged PR blocks completion until the maintainer records `superseded`, `replanned`, or `cancelled` for that slice. If replacement work is planned, it remains In Progress until the replacement PR is ready. A material change to acceptance criteria or slice outcomes returns the issue to Triage and invalidates the prior issue verdict. GitHub close reasons are **Completed**, **Not planned**, and **Duplicate**; “cancelled” is a slice disposition, not a GitHub close reason. In Stage 1, the maintainer reconciles status manually; later automation must use the same rules.

### 5.3 Completion and later work — DECIDED

An issue is closed as completed only after every slice meets §5.2. New work discovered during implementation is a new issue unless it is a necessary correction to the approved acceptance criteria; material corrections return the issue to Triage.

### 5.4 Returning to Triage — DECIDED

A changed problem statement, expected behavior, scope/non-goals, delivery-slice outcome, or current Type invalidates Ready approval and returns the issue to Triage. If implementation has started, associated PRs return to draft while the revised issue contract is reviewed; they may resume review only after the issue is Ready again. Newly discovered affected areas or documentation destinations are routine implementation evidence: record them in the PR impact matrix and have the reviewer verify them without changing issue status. Machine-owned activity, comment replies, and those impact-matrix additions do not change the contract fingerprint. A maintainer can also return a Ready issue to Triage when new evidence materially changes its assumptions.

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

A maintainer is accountable for the Ready transition during the manual pilot. Agents provide the verdict and evidence but do not set Project Status. Later automation may apply the same deterministic gate. A changed contract or expired approval returns to Triage; being Ready is never inferred from the absence of comments.

## 7. Risk tiers and priority

### 7.1 Risk tiers — PROPOSED

Use **Low, Medium, High** to choose review intensity and maintainer involvement. A new Project Risk tier field is required; it does not exist today. The initial field proposal has plain-language descriptions and examples, and the planner proposes a tier from blast radius and reversibility. Reviewers may raise it; only a maintainer may lower it. Do not add per-area minimum tiers until the field is live and pilot data shows those floors are useful. The new field and its migration are a separately sized package.

### 7.2 Priority — DECIDED

Use **P1–P4**: P1 is the highest priority and P4 the lowest. The existing Base Projects and schema use P0–P3; this proposal intentionally changes the convention. A migration package adds P4, removes P0 from the active option set, updates option descriptions/forms/docs, and maps existing values P0→P1, P1→P2, P2→P3, P3→P4. It records before/after counts for every affected Project. The live Project field is authoritative; `Priority:` prose in old issue bodies remains historical and is not rewritten silently.

### 7.3 Priority and risk are independent — DECIDED

Priority describes when work should happen; Risk describes review and safety treatment. A P4 may still be High risk, and a P1 may be Low risk. Neither field is copied to PRs.

## 8. Pull requests

### 8.1 Issue-to-PR relationship — DECIDED

Every PR belongs to exactly one issue and declares one planned slice. One PR per issue remains the normal case. An approved issue may have several PRs when its plan enumerates the slices and evidence. A PR must not silently introduce unplanned scope.

### 8.2 Linking — DECIDED

For a single-PR issue, use `Fixes #N`. For a multi-PR issue, every PR uses `Part of #N`; none uses `Fixes`, because an early merge must not close the issue while other slices remain. The maintainer closes the issue when all slices satisfy §5.2; later automation may do so. A superseding PR links the same issue and slice and states which earlier PR it replaces.

### 8.3 Draft and review state — DECIDED

A draft PR is implementation in progress. It does not count toward In Review. The issue moves to In Review only when every planned slice has a non-draft PR or reviewable non-PR evidence, or is already merged. If a PR is converted back to draft, the issue returns to In Progress. The separate Project queue remains the canonical maintainer view; PRs are not Project items.

### 8.4 Pull request template — DECIDED

Use one PR template with these sections: Summary; linked issue and slice; plan/acceptance trace; the impact-and-evidence matrix using the exact §12.10 categories; risk, rollback and notes; and a release-note entry (or a reasoned “none”). Category 6 records validation commands/results and any test exclusions as well as test/CI impact, avoiding a second validation section. Decision records, demos/examples, docs and `.ai-context/` transition are handled inside the common matrix, not duplicated in separate impact sections. The template does not ask for project fields already present on the linked issue.

Until the generated-context feature ships and checked-in `.ai-context/` files are removed in their own repository trains, the PR must include an AI-context impact disposition under the current matrix. Keep the existing `.ai-context/` maintenance checklist during that transition; do not let those files become silently stale.

### 8.5 Review comments, responses and approval freshness — DECIDED

The reviewer posts actionable findings as review threads. The author responds to every thread with a commit/evidence or a challenge and rationale. The reviewer verifies the response and resolves the thread only when addressed or correctly challenged; unresolved disputes go to the maintainer. New findings in follow-up changes start the next bounded round. Neither author nor reviewer may silently resolve a finding to satisfy a gate.

Agents currently post as the same GitHub account, so GitHub cannot enforce which agent replied or resolved a thread. During Stage 1, the maintainer audits the responses and the reviewer's thread resolutions. The reviewer verdict includes the exact line `Verdict: Approved at <full-head-SHA>` plus author/reviewer tool, model and session. A new code push requires a new review against the new head. A base-only update may receive a fresh, full-head-SHA re-verification without consuming a review round only when all checks pass: (1) `git range-diff`, using the recorded old/new base and head SHAs, shows every non-merge PR commit unchanged; (2) every merge commit introduced is a base-update merge on the PR first-parent chain, and its second parent is an ancestor of the updated base head; and (3) `git show --remerge-diff <merge-commit>` is empty for every such merge. Any other merge, unavailable/uncertain evidence, or change—including hand-written conflict resolution—requires a full review round. The reviewer records the re-verification and its evidence separately from the round ledger.

### 8.6 Merge gate — DECIDED

Required approving reviews remain **0** while author and reviewer agents share one GitHub identity. The maintainer checks the current-head verdict, every finding response/resolution, required checks, documentation impact and any escalations, then performs the merge. No agent merges or enables auto-merge. Required conversation resolution should be enabled through a separate, reviewed branch-policy change; until that change is live, it is a manual gate rather than an asserted GitHub enforcement. The required approval count must not be raised as a substitute.

### 8.7 Project fields and linked PRs — DECIDED

Issues are the canonical Project items for Status, Priority, Size, Area, Risk tier, and Initiative. Milestone is native issue metadata, not a Project field to copy. Do not create PR Project items or copy issue fields onto PRs. Use GitHub's native linked-pull-request view and issue relationships. A PR retains its title, author, branch, checks, review state, slice identifier and release evidence.

## 9. Reviewer rule sets

### 9.1 Issue reviewer — PROPOSED

The issue reviewer checks the current Type and contract, testability, delivery slices, documentation dispositions, security/privacy, risk, current docs and decisions, and consistency with the repository's product principles. It cites evidence and assigns each finding an identifier and severity.

### 9.2 PR reviewer — PROPOSED

The PR reviewer checks the issue and slice, changed code and tests, documentation and decision fold-back, release-note line, security, and validation evidence. Changed paths may trigger specialist passes, but they produce one consolidated review and share one round count. The verdict must include the reviewed head SHA and provenance. A fresh-session reviewer is mandatory; `different-tool` applies when configured.

### 9.3 Review discipline — DECIDED

Findings describe the observed condition, evidence, consequence and requested outcome. The author replies in the thread. The reviewer confirms or disputes the response and owns resolution when justified. A reviewer does not silently rewrite the author's explanation or use “resolved” as a substitute for evidence. The maintainer decides disputes and exhaustion.

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
| **Status** | Current Project field; target order changes | Work lifecycle defined in §5. |
| **Priority** | Current Project field; target P1–P4 migration | Scheduling urgency, independent of risk. |
| **Size** | Current Project field | Relative implementation effort. |
| **Area** | Current Project field | Product/ownership surface; shared defaults are defined in `project_model.py` and repository-specific additions in `.github/base-project.yml`. |
| **Initiative** | Current Project field | A multi-milestone effort with a durable initiative document. |
| **Risk tier** | **Does not exist today; proposed new Project field** | Low/Medium/High review and safety intensity. |
| **Milestone** | Native issue milestone | Target release or planning window. |
| **Type** | Native issue Type | Task, Bug or Feature today; not a category label. |

Priority and Risk have no combined scale. Project fields remain canonical. The organization-level Issue Fields feature is not used to duplicate them.

### 10.3 Areas, labels, and views — DECIDED

Today, `cli/python/base_github_projects/project_model.py` defines the shared default Project fields and options, including the default Area options. Each repository's `.github/base-project.yml` adds repository-specific areas and initiatives and supplies issue defaults; those extra areas are merged with the shared defaults. Live GitHub Projects are inventoried before migration rather than assumed to match either source. Do not introduce duplicate catalogs in `governance/areas.yaml` or `initiatives.yaml`. The `security` label is a valid category label, not a native Issue Type; vulnerability disclosure remains private. GitHub's exact community label names are `good first issue` and `help wanted` (spaces, no hyphens).

Project **statuses** are not Project **views**. Standard views may include a full board, Backlog, Triage/analysis queue, current milestone, and review queue; each view filters canonical issue fields and does not create another status system. The Area inventory and eventual path mapping are separate from GitHub label names.

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

During documentation migration, review `.ai-context/DECISIONS.md` and relevant closed issues/merged PRs. Convert durable active decisions into ADRs with source links and current status; mark superseded choices with successor links. Preserve provenance and do not copy transient discussion as policy. Keep `.ai-context/` tracked and maintained until the replacement context-export feature is released (§12.9).

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

- Command, option, manifest, configuration, and JSON reference should be generated from authoritative CLI help, schemas, or code where practical. Until a generator exists, a PR explicitly verifies reference changes against the shipped implementation.
- Every implementation PR supplies a user-facing release-note line or a reasoned “none.” Release preparation gathers those lines and checks completeness. `basectl release notes` automation is a target to verify and implement; this design does not claim that command exists today.

### 12.9 AI context — DECIDED

`.ai-context/` files are currently tracked and must continue to be maintained. They will be removed from Base Foundry repositories only after the replacement `basectl export-context` feature is implemented, released, and proven. Until then, the existing PR impact checklist and scheduled export remain in place.

The target `basectl export-context` invokes only the user-selected, installed AI tool through its supported CLI to summarize relevant canonical repository documents and writes the result only to an explicit export location outside the repository. Base does not call provider APIs directly or manage provider credentials. It does not maintain a second checked-in source of truth. The generated artifact identifies its source commit, generation date, and source paths; flags contradictions instead of resolving them silently; and excludes secrets and unapproved files. It is read-only with respect to the repository and must fail clearly if the selected tool is unavailable or the export destination is inside the repository. The command's provider interface, supported tools, privacy/data-transfer behavior, and offline/error semantics require an implementation issue and threat review before release. It must disclose what repository content is sent to the selected provider, never silently select a cloud service, use an allowlist, exclude secrets and unapproved files, and fail if the destination is inside the repository.

After the released feature is proven, create separate issue/PR trains for removing `.ai-context/` from each Base Foundry repository, updating all references and any scheduled export jobs. Removal is a dependent rollout, not a prerequisite to shipping this design or implementation plan. A generated export is disposable output, not a tracked project document.

### 12.10 Documentation impact and drift checks — PROPOSED

The issue and PR templates use this one ordered list. Each item records the canonical destination(s), or `No impact` with an evidence-based reason. These are impact categories, not a requirement that every change edit every document.

1. **Product intent:** PRD, product principles and non-goals.
2. **Architecture and contracts:** area design documents and behavior promises.
3. **User guidance:** README, getting-started guide, FAQ and task guides.
4. **CLI/API and reference:** commands, options, manifest/config schema, generated reference and compatibility notes.
5. **Operations and safety:** security, privacy, trust, release, migration, support and rollback procedures.
6. **Validation and testing:** tests and fixtures, acceptance checks mapped to criteria, test/CI policy, validation commands and results, plus evidence-based reasons for exclusions.
7. **Examples and downstream use:** demos, samples and Base-supported consumer guidance.
8. **Governance and contributor process:** issue/PR templates, contribution/review instructions, maintainer procedures and AI-context transition while it exists.
9. **Decision records:** new, changed or superseded ADRs and their index.
10. **Release notes:** one user-facing line in the PR or a reasoned `none`; accepted lines are assembled into the repository's `CHANGELOG.md` during release preparation.

The initial drift-check plan is per document kind: PRD reviewed against intent; README quick-start commands tested; design/contracts checked against changed code and tests; ADR status and index validated; CLI/reference checked against schemas/help; guide examples executed; FAQ links checked; release-note completeness compared with merged PRs; and context exports generated from allowlisted sources. A finding is evidence-backed and becomes an issue; the checker does not silently rewrite policy. Until automation exists, the PR reviewer performs the same checks manually.

For the context transition, checked-in `.ai-context/` is still a maintained source surface until export is released. After release, remove those files and update scheduled exports and references through separate repo issue/PR trains; generated export output is disposable and outside the checkout.

### 12.11 When code and docs disagree — PROPOSED (from Codex's 1.11 draft)

- **Which source is authoritative for what:** code and tests for what the current build does (schemas and command definitions for exact fields and options); user docs for what users may rely on; area design docs for the implemented architecture; decision records for why; issues and PRs for how the work happened; the changelog for what a release contains.
- **Classify the mismatch first:** is the code wrong, is a document stale, or was the design deliberately changed? Then fix it in the same PR: fix the code, update the docs, add or replace a decision record, adjust tests.
- **If a known gap must ship,** open an owned follow-up issue that names the affected audience, the risk and the target release, so the gap is visible.
- **Never present a proposal as the implemented system.** Proposed designs are labeled as proposed.

### 12.12 Versioned docs — DEFERRED

Whether users of an older release see the docs for their version. Revisit when Base has more users.

---

## 13. Identities and attribution

### 13.1 Human-operated pilot — DECIDED

During the pilot, agents act through the maintainer's GitHub account. GitHub cannot distinguish author and reviewer agents and cannot enforce reviewer-only thread resolution. The process therefore depends on recorded tool/model/session provenance and a maintainer audit. Required approving reviews remain zero. No behavior described here should be presented as a GitHub-enforced identity check until distinct identities exist.

### 13.2 Git history and GitHub activity — DECIDED

Git author/committer identity follows the repository's existing contribution rules. GitHub comments and verdicts identify the human account used. Do not imply that a GitHub username proves which model or session produced a review; the verdict's provenance is an auditable declaration, not cryptographic attestation.

### 13.3 Verdict provenance — DECIDED

No machine-generated provenance footer is required in every PR. Each issue/PR verdict records author tool, model and session; reviewer tool, model and session; date; reviewed contract fingerprint or full PR head SHA; result; and findings. This is manually maintained during Stage 1 and can later be emitted by automation. Metrics use those verdict records and state their limits; provenance does not replace human accountability.

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

An override is an explicit maintainer decision with a reason, scope, expiry or recheck condition, and linked issue/PR. During the manual stage the maintainer records it in the review thread or issue. Agents may explain a proposed exception but must not create, approve, or post an override as if it were a maintainer decision. GitHub's shared account cannot enforce this distinction, so maintainers audit the actor and evidence. Do not use an `override` label.

### 14.4 Pinned enforcement — DECIDED (Stage 2)

- Enforcement checks (readiness, PR checks, status rules) run a **pinned, released** version of Base from their first automated use, not whatever just merged to `main`. A bad merge can't break its own gate. The first rollout remains warn-only; blocking or reverting is a separate, evidence-backed promotion for each rule under §14.2.
- The pin is upgraded deliberately, after a release proves itself.
- Same idea as the second laptop running only released Base: the checker isn't the thing being changed.

### 14.5 Branch protection — DECIDED

On `main`: required status checks (Tests, Security scanners, `base/issue-branch-policy`, governance checks as they arrive); require conversation resolution after the separate branch-policy train enables it; no direct pushes; squash merge; required approving reviews remain 0 under the shared agent identity. A human maintainer verifies the current-head verdict and resolved threads under §8.6.

### 14.6 Automated review and fix security — DECIDED

Automation is untrusted-by-default and cannot turn review findings into privileged execution:

- Issue and PR review workflows use least-privilege tokens. Reviewers receive read-only repository contents and the narrow pull-request permission needed to post reviews and resolve addressed threads; they cannot push code, change branch protection, approve their own work, merge, release, or access deployment secrets.
- Do not use `pull_request_target` or another privileged event to check out, execute, install, or evaluate untrusted PR content. Fork PR workflows receive no secrets. Treat PR text, changed files, issue content, and generated context as prompt-injection-capable data.
- Any automated fix runs only after an explicit trusted maintainer trigger, in an ephemeral isolated environment, without secrets and without network access unless a reviewed step strictly requires it. It may produce a patch on the PR branch but cannot approve, resolve its own review threads, merge, or release.
- Validate the proposed patch in the same isolation. A fresh independent reviewer checks the resulting head SHA; any new push invalidates approval. Maintainer review remains mandatory for disputed findings, security-sensitive changes, and round-limit escalation.
- Pin workflow actions and model/tool versions where possible; cap usage; record actor, model/tool, commit SHA, prompt/rule version, and outcome without storing secrets or unnecessary private data. Document provider data handling and retention before sending private repository content to an external model.

---

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

AGENTS.md is a map, not a manual. It points to the issue-first process, plain titles, the active area design and decisions, the documentation-impact categories, coding standards, issue/PR reviewer rules, and the decision-capture prompt (§11.4). It states that agents do not set Project Status, grant overrides, merge PRs, or silently choose an AI provider. It does not rely on a provenance footer.

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

- Prove Base on projects of different sizes and record pilot duration and friction; there is no fixed release freeze or calendar commitment.
- **Metrics, defined before starting:**
  - drift incidents per month;
  - PRs needing rework after merge;
  - follow-up issues linked to a Done issue (problems that escaped review);
  - spec-gap rate (PR findings classified as spec gaps);
  - wrongly "small" claims caught by the PR-vs-issue check;
  - how often Ramesh had to step in by hand;
  - share of PRs with real review findings;
  - author/reviewer tool and model outcomes, from verdict records (not GitHub usernames or footers);
  - number and proportion of user-found bug fixes using the test-impossibility exception, with reasons;
  - rules that never caught anything (monthly).
- **Pre-pilot baseline:** package 17 captures available measures before the manual pilot, using a declared historical sample. The current estimate is that about 60% of Codex PRs had real review findings; record the source and sample limits, along with available counts of disconnects found by hand testing and docs-vs-code drift audits. Mark unavailable measures as unavailable rather than estimating them without evidence.

### 17.5 Self-assessment and self-healing — DECIDED

- **Reflexes:** gate checks catch a problem the moment it appears.
- **Deliberate healing:** periodic audits find patterns, ask why, and add a new reflex. Over time each audit should find less.
- **Never silent:** every correction becomes an issue and goes through analysis and approval like any other change. A system that rewrites its own rules without oversight is how incidents happen.
- **Monthly review:** which rules caught nothing? Candidates for retirement.

---

## 18. Rollout

### 18.1 Two adoption phases — DECIDED

- **Phase 1:** Every repository in the `basefoundry` organization listed in §1.2 uses and refines the governance process through separate repository trains. The nine ecosystem repositories use ecosystem defaults; `banyanlabs` participates as a Base-supported project with consumer defaults.
- **Phase 2:** Base-supported consumer projects may opt in through versioned defaults and their existing manifests. This phase is deferred until Phase 1 evidence identifies stable defaults and necessary exceptions.

### 18.2 Three stages and their implementation-plan mapping — DECIDED

| Design stage | Intent | Implementation-plan work |
|---|---|---|
| **1. Foundation and manual operation** | Issue/PR contracts, ADR lifecycle, document-impact matrix, repository config, reviewer rules, baseline measures, manual readiness and review loops, response/resolution runbook, maintainer audit. | Plan stages B–C and work packages 1–6, 16–17. Pilot first in Base; rollout follows through separate repository trains. |
| **2. Deterministic governance** | Readiness and contract-fingerprint checks, round/status ledger, slice-based lifecycle reconciliation, Project-schema migration, warn-only enforcement and overrides, pinned released checker, branch conversation-resolution setting. | Plan stages D–E and work packages 7–9, 19–20; Project migration package 8 is applied to each repository before its dependent checks are enabled. |
| **3. Drift checks and guarded read-only review** | Per-kind documentation checks and a least-privilege, read-only reviewer under §14.6 security controls. Automated fixes remain separately gated and deferred. | Plan stage F and work packages 10–11, 21. |

First-party repository adoption and open-title migration (work packages 12 and 18) apply the accepted stages to every organization repository, including the consumer profile for `banyanlabs`; they are rollout, not separate automation stages. Project schema changes (package 8) are piloted in Base and applied repo by repo before each repo enables dependent checks. The context-export feature and subsequent `.ai-context/` removal (work packages 13–14) are a separate product-dependent train and are not a condition for beginning the manual pilot. Each stage exits only after its evidence and rollback path are recorded; no fixed two-week duration or release freeze is assumed.

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

- **Docs MCP server** (1.12 candidate): a remote server Claude can reach from a phone, with read-only tools (list active decisions, read a design doc section, search docs) and one write tool: create an issue in Backlog only. Ideas from walks then enter the normal loop; nothing bypasses the gate. Comes after the docs are trustworthy, since an MCP server serving drifted docs spreads drift faster.
- **RAG** (1.13 candidate): only if plain search falls short. Base's docs may be small enough that it's never needed.
- **Other trackers:** adapters only on demand (§15.4).
- **GitHub platform features:** Dependabot and CodeQL enabled; Discussions kept for questions and ideas; reusable workflows adopted and called at pinned versions; sub-issues used for genuine hierarchy, not for initiatives.

---

## 21. Open questions

| # | Question | When/how to settle |
|---|---|---|
| O1 | Which GitHub events expose Project field changes reliably, and which require scheduled reconciliation? | Read-only implementation spike before lifecycle automation. |
| O2 | Can a GitHub App identity satisfy any future required-approval rule while preserving current-head freshness? | Do not change the current zero-approval policy; test only if distinct identities are adopted. |
| O3 | Which hosted AI providers, credentials, data-retention terms and network controls are acceptable for automated review/fixes? | Security review before any hosted-model workflow. |
| O4 | What exact `basectl config` syntax and schema bounds should expose the repository governance settings? | Config implementation issue; preserve current local config behavior. |
| O5 | Which provider CLIs and privacy/offline modes will `export-context` support? | Threat model and implementation issue before release. |
| O6 | What is the final area list, ownership map and path mapping? | Inventory issue; preserve the shared defaults in `project_model.py` and repository-specific area/initiative extras and issue defaults in `.github/base-project.yml` until migration. |
| O7 | Confirm decision/design/initiative/guide locations against the documentation inventory. | Documentation migration issue. |
| O8 | Should the `blocked` label be replaced by native issue dependency relationships? | Metadata migration issue after live-use review. |
| O9 | Which governance defaults are stable enough for Base-supported projects? | Phase 2 design after first-party evidence. |
| O10 | How should the public community-triage guide explain the relationship between contributor triage and the internal Triage status? | Separate docs issue; keep public contributor guidance unchanged until reviewed. |
| O12 | Should native Issue Types replace any current category-label branch routing, and should `Feature` become `Enhancement`? | Dedicated migration decision; no type or branch-policy migration is implied here. |

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

## Appendix E. Maintainer clarifications recorded 8–9 November 2026

These decisions are incorporated in the current body and supersede any inconsistent statement in the earlier 3 November appendices.

1. Keep Triage between Backlog and Ready, and use separate repository-owned issue and PR round limits, each initially three.
2. Draft PRs keep the issue In Progress. Use delivery slices rather than fixed PR numbers. In Review requires reviewable evidence for every slice; Done requires every slice merged or an explicit maintainer-approved terminal disposition.
3. Authors respond to every review finding. The reviewer verifies and resolves addressed findings; disputes and round-limit exhaustion go to the maintainer. PR verdicts bind to the current head SHA. Required approving reviews stay at 0 while agents share one GitHub account.
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

## Appendix F. Disposition of original B1–B18 items

| Item | Disposition | Current treatment |
|---|---|---|
| B1 | Accept | One issue layout; Bug reproduction and actual/expected go inside Problem. |
| B2 | Accept | `Unknown: reason` is allowed before Ready; every category is resolved by Ready. |
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
| B14 | Confirm | Maintainer merges; required approvals remain zero; thread resolution is initially manual and later enabled in branch protection. |
| B15 | Accept | Ready freshness defaults to 30 days, stored in manifest governance settings. |
| B16 | Retire | No `.github/` generator is promised before a separate implementation and ownership design. |
| B17 | Accept | Preserve GitHub's exact `good first issue` and `help wanted` names with spaces. |
| B18 | Retire | Do not mirror Project values into organization Issue Fields or PR fields. |
