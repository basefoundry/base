# Base Ecosystem Governance Implementation Plan

**Version:** 3.1, 9 November 2026
**Status:** Proposed sequence for review; no governance automation is authorized by this plan alone.
**Owner:** Ramesh (codeforester)
**Companion:** [Governance Design](DESIGN.md)
**Tracking issue:** [#2663](https://github.com/basefoundry/base/issues/2663)

This plan turns the design into reviewed issue/PR trains. It is proposal-only until #2663 is accepted. Every implementation train gets its own reviewed issue, exact acceptance criteria, impact map and PR. Existing issues are reused only after their current contracts are reconciled with this design. A package may contain several small PR slices; the issue remains In Progress until each planned slice is ready for review, then In Review, and Done only after all slices merge or receive a recorded maintainer disposition.

There is no 1.x freeze or fixed delivery date. Packages carry relative order and S/M/L sizing so the maintainer can sequence them against capacity. No package is merged or deployed by an agent.

## 1. Delivery principles

1. Keep the lifecycle Backlog → Triage → Ready → In Progress → In Review → Done. Re-sequencing and redefining Triage requires a Project schema and documentation migration.
2. One issue and one PR is the normal train. For exceptional multi-PR work, the approved issue plan names slices `S1…Sn`; each PR declares one slice and uses `Part of #N`. Only a single-PR train uses `Fixes #N`.
3. Configure independent issue and PR review-round limits in `base_manifest.yaml` under `governance:`; both start at three. Templates and a manual pilot do not depend on config automation.
4. The reviewer is a separate fresh-session agent with no author transcript or persistent authoring memory. A repository setting selects `fresh-session` or `different-tool`; Base defaults to the latter and consumer projects to the former. Record author/reviewer tool, model and session in each verdict.
5. Every finding gets an author response and reviewer verification/resolution. Disputes and round-limit exhaustion go to the maintainer. PR verdicts cite the full head SHA; a changed code commit requires a fresh review. Base-only re-verification is tracked separately and does not consume a round when `git range-diff` proves the PR commits unchanged.
6. Required approving reviews remain zero while both agents use one GitHub identity. The maintainer manually audits reviewer responses/resolutions and merges. A separate reviewed branch-policy train enables required conversation resolution; it must not raise the approval count.
7. Issues and PRs use the same ten documentation-impact categories from Design §12.10. Every category has a destination or an evidence-based no-impact reason. Every PR has a release-note line or a reasoned `none`.
8. Every bug a user found gets a failing test before its fix. If testing is genuinely impossible, the PR explains why. Count these exceptions during the pilot.
9. Keep checked-in `.ai-context/` maintained until the replacement export command is released and proven. Remove it later through separate repository trains.
10. Keep Superpowers deferred unless the pilot shows a specific spec-driven development or drift-prevention gap.

## 2. Rollout and rollback

| Plan stage | Work | Maps to design | Exit evidence and rollback |
|---|---|---|---|
| **A. Accept the proposal** | Resolve review findings on #2664; maintainer accepts the design and plan. | Before Stage 1 | All review threads answered and resolved by reviewer; checks green. Rollback: leave proposal open or close as not planned; no policy is active. |
| **B. Establish source contracts** | ADR/document impact, single issue template, PR template, manifest governance schema and repository `basectl config`. Template work is independent of config implementation. | Stage 1 | One current issue and PR pass the manual checklist. Rollback: revert the template/config PR; retain the prior Project schema and config reader. |
| **C. Run manual loops** | Issue and PR review runbooks, response/resolution audit, SHA-bound verdicts, three-round cap and maintainer escalation. | Stage 1 | Pilot issues reach Ready and PRs reach merge without bypass; record exceptions/friction. Rollback: pause new intake under the new process, return to current documented workflow, and preserve all review evidence. |
| **D. Add deterministic checks** | Readiness fingerprints, round ledger, slice-based issue-status reconciliation, manifest validation and required conversation resolution. | Stage 2 | Dry-run results match maintainer decisions on a representative sample before enforcement. Rollback: disable the check/workflow and return to manual reconciliation; restore branch setting only through a reviewed policy PR. |
| **E. Add guarded AI automation** | Read-only review first; constrained fixes only after threat model and permission tests. | Stage 3 | Security gates in Design §14.6 pass; fork isolation, least privilege, audit trail and kill switch are demonstrated. Rollback: disable the workflow/app and revoke its write permission; manual review continues. |
| **F. Adopt across first-party repositories** | Apply already-accepted stages through separate repository trains. | Delivery rollout, not a separate design stage | Each repository has a recorded before/after schema and workflow check. Rollback: revert that repository's adoption PR or disable its automation; never silently overwrite project-specific configuration. |
| **G. Replace AI context files** | Release the new `export-context`, then remove `.ai-context/` and stale scheduled exports in separate repo trains. | Separate product-dependent work | Prove output location, sources, privacy, provider selection and failure behavior first. Rollback: keep or restore the maintained tracked files and scheduled export until the replacement works again. |

Stages may overlap only after dependencies are met. A rollback is itself a reviewed PR or an explicit maintainer-controlled GitHub setting change with an issue/evidence record.

## 3. Candidate issue/PR work packages

These are candidate issue trains, not implementation authorization. Create or rescope issues only after #2663 is accepted. The reviewer checks for duplicate live issues and preserves existing issue numbers when their scope matches. Sizes are relative: S = a few focused files; M = several files or one migration; L = cross-repository or stateful migration.

| Order | Work package | Main deliverable | Depends on | Size |
|---|---|---|---|---|
| 1 | Documentation and ADR contract | Confirm document locations; one canonical impact taxonomy; ADR template/index; decision-capture and area-reading instructions | A | M |
| 2 | Single issue form and Ready contract | One form; current-Type readiness behavior; bug reproduction contract; remove category title prefixes | A, 1 | M |
| 3 | Repository governance configuration | Manifest schema, distinct loop limits, reviewer independence, 30-day Ready freshness, `basectl config`; deprecate old review-policy reader safely | A | M |
| 4 | Manual issue-loop pilot | Fresh-session reviewer runbook, verdict/fingerprint record, three-round cap, maintainer escalation; no bot status writes | 2; may begin before 3's CLI exists using documented defaults | M |
| 5 | PR template and impact record | Single PR template, slice link, validation, exact impact categories, release note, risk/rollback/notes | 1; independent of 3 | S |
| 6 | Manual PR review loop | Finding-response procedure, reviewer thread resolution, full-head-SHA verdict, round tracking, re-verification distinction, maintainer merge gate | 5; round ledger may wait for 3 | M |
| 7 | Lifecycle and readiness automation | Issue contract fingerprint, freshness check, current-Type check, delivery-slice states, draft handling and status reconciliation | 2, 3, 4, 6 | L |
| 8 | GitHub Project migration | Re-sequence/redefine Status; migrate Priority P0→P1, P1→P2, P2→P3, P3→P4; add Risk tier; update every affected Project and schema/docs/forms | A; before full rollout | L |
| 9 | Branch policy and safe automation baseline | Keep required approvals at 0; enable conversation resolution; define least-privilege read-only review and later constrained-fix boundary | 6 and security review | M |
| 10 | Evidence-backed documentation inventory | Crosswalk PRD, area designs, code/reference, user guides, README/FAQ, operations/security, decisions, release notes, examples and templates to canonical owners | 1 | M |
| 11 | Area map and drift checks | Path-to-area map and tested per-kind checks; evidence-only findings create issues, not silent edits | 10; pilot evidence | L |
| 12 | First-party repository adoption | Migrate the accepted process in `base`, `base-cli`, `base-bash-libs`, `base-demo`, `base-bash-libs-demo`, `base-cli-demo`, `base-workspace`, `base-platform-tools`, `banyanlabs`, and `homebrew-base`; add the latter's minimal manifest | 3–9, rollout gate | L |
| 13 | Generated AI context | Implement `basectl export-context` through user-selected installed CLI, allowlist, external export location, source/date stamping, privacy disclosure and threat model | Separate product/security issue | L |
| 14 | Context-file cleanup | Remove checked-in `.ai-context/`, update `AGENTS.md`/`CONTRIBUTING.md`/manifest checklist and scheduled export paths, one repository train at a time | 13 released and proven | L |
| 15 | Consumer governance defaults | Decide which first-party rules generalize; versioned configure/upgrade PRs; no live inheritance and no required `governance/` folder | Exit evidence from B–F | L, deferred |

### 3.1 Repository configuration contract

The selected machine-readable home is the `governance:` section of each repository's existing `base_manifest.yaml`. The two loop limits are separate keys, both default to three. The same section carries reviewer mode, Ready freshness and the current review-policy value; existing GitHub PR requirements remain under `github.pr`. There is no `base-governance.yml` and no `.base/` directory.

`basectl config` must make repository scope explicit, validate the manifest schema, preserve machine-local config behavior, print a useful diff, and fail clearly outside a repository or when a setting is unsupported. Bounds and exact CLI syntax are fixed in the config issue. The `.github/base-review-policy.yml` path is migrated with a compatibility period; do not remove its reader until the repository config and docs are released. `.github/base-project.yml` remains the single current source for Project field options, areas, initiatives and issue defaults; do not create duplicate catalogs in `governance/`.

First-party repositories may put reviewer rules, standards and prompts in a modular `governance/` directory. Base-supported consumer projects need no new directory: Base defaults are materialized only through an explicit configure/upgrade operation and a reviewed PR. No value is inherited live from Base.

### 3.2 Issue and PR review-round contract

Each loop uses a separate repository-configured maximum; the initial evaluation is round one. One round is a reviewer evaluation after the author had an opportunity to respond to the previous findings. A round may contain multiple findings. A base-only update is a re-verification, not a round, only if `git range-diff` confirms the PR's commits are unchanged. Any code change requires fresh review at its new head. At the limit, unresolved findings stop for a maintainer; the process never approves by timeout.

For each finding, the author replies with a fix/commit or a challenge and evidence. The reviewer verifies the response and resolves the thread when justified; otherwise the thread remains open and goes to the maintainer if disputed. The GitHub identity is shared during the pilot, so this is a manual audit rule, not an enforceable author/reviewer identity distinction.

## 4. GitHub metadata and migration contract

- **Type:** use the current native values Task, Bug and Feature. Do not invent Documentation, CI, Security or Enhancement types. Decide separately whether Feature becomes Enhancement before changing the type set.
- **Fields:** issue Project fields are canonical. Status, Priority, Size, Area, Initiative and the proposed Risk tier are not copied to PRs. Do not duplicate them in organization Issue Fields.
- **Priority migration:** record counts for each old value on every affected Project, perform P0→P1 through P3→P4, and verify counts after. Old `Priority:` text in issue bodies is historical, not backfilled.
- **Risk:** create a new Low/Medium/High Project field; it does not exist today. No per-area floor until its use is proven.
- **Status migration:** update schema order/descriptions and `docs/github-workflow.md`; distinguish the public community-triage process pending O10. Record all values and issue counts before and after.
- **Labels:** preserve category labels because branch policy reads them today. `security` is a valid label; private vulnerability intake remains separate. `good first issue` and `help wanted` keep spaces.
- **Relationships:** use native linked PRs, sub-issues and blocked-by relationships where they express delivery or dependency; do not use PR Project cards as field mirrors.

The repository inventory package must inspect the live Projects for all first-party repositories named in package 12, record whether each has a Project schema, and capture counts before/after. It must not assume every repository has an identical Project or silently discard a value.

## 5. Existing issue crosswalk

Reconcile these known candidates before creating new issues. This table is a scope recommendation; issue status/body edits require their own authorized issue train after #2663 is accepted.

| Existing issue | Recommended disposition |
|---|---|
| #2571 readiness workflow | Rescope to packages 2 and 7; preserve its current acceptance criteria only where they match the fingerprint/Ready contract. |
| #2572 `.ai-context/` PR validator | Keep as a transition guard until package 13 ships; then remove the check in the same repository cleanup train as the checklist. |
| #2573 structured Agent Assignment | Close or rescope to verdict provenance outside the issue body; the assignment field is not part of the canonical issue contract. |
| #2574 PR classes allowed to merge without human review | Keep on hold while the governance proposal is reviewed; then close as superseded because the design requires a human maintainer to merge every PR. Preserve the never-automatic path list in package 9's security rule set. |
| #2576, #2599, #2580, #2581, #2584 | Crosswalk to packages 6, 7 and 9; split state-machine, authority, bounded repair and autonomy ceiling work into small trains. |
| #2627 `repo init --ai-context` | Already closed as not planned; do not revive. The new export derives context outside the repo. |
| #2631 and #2632 | Treat as duplicate drift-strategy candidates; choose one canonical issue under package 11 after checking live state. |
| #2663 | Remains the parent governance-design review issue. Do not expand its acceptance criteria to implementation. |

## 6. Security gates for automated review and fixes

Start with read-only analysis and no secrets in review jobs. Treat issue text, PR descriptions, diffs, comments, test output and artifacts as untrusted prompt input. Repository instructions and rule sets are policy; untrusted content cannot override them. Pin actions/dependencies, restrict permissions to the minimum, isolate fork workflows without secrets, and log the reviewed commit, model/tool, prompts/rules version, findings and outputs.

Constrained fixes are a separate gate: only an explicitly selected trusted same-repository PR, a dedicated short-lived write token with contents limited to the PR branch, no access to secrets/release credentials, a diff allowlist, no workflow/permission/branch-protection edits, required tests/scanners, and a kill switch. The agent cannot merge, release, publish, change policy, or self-approve. Any security-sensitive, trust, credential, installer, workflow/ruleset, release or MCP path always receives maintainer review and merge. Do a threat model and permission test before enabling hosted model calls; log provider/data disclosures and retention assumptions.

## 7. Manual pilot runbook and evidence

### 7.1 Issue loop

1. Start with the current issue and repository context. The planner completes the single contract and named slices; it does not change Project Status.
2. Run readiness manually: current Type requirements, all ten impact dispositions, acceptance-to-test map, risks and no blocking questions.
3. Start the reviewer in a genuinely new session. Do not include the author's chat or persistent memory. Give it the issue, repository, active decisions and rules. If configured `different-tool`, use that tool; if unavailable, wait or escalate.
4. Reviewer posts one consolidated result with numbered findings, contract fingerprint, tool/model/session provenance and round number. Initial result is round one.
5. Author replies to each finding; maintainer decides disputes. Reviewer verifies and records a new verdict. After three rounds, stop for maintainer decision.
6. Maintainer confirms the verdict matches the current contract fingerprint and sets Ready.

### 7.2 PR loop

1. The PR links one issue and declares one slice. It may start as draft; the issue remains In Progress.
2. Reviewer reads the issue, slice, PR diff, tests, docs and review rules in a new session. It records the complete current head SHA and provenance.
3. Author responds to every finding; reviewer verifies and resolves addressed threads. Challenges and unresolved findings go to the maintainer. Every follow-up review against changed code uses the next round.
4. If only the base branch moved, compare with `git range-diff`. When PR commits are unchanged, record a base-only re-verification separately; it does not consume a round. Otherwise run a fresh review at the new SHA.
5. After no actionable finding remains, reviewer posts `Verdict: Approved at <full-head-SHA>`. Approval here is a process verdict, not a GitHub approving-review event. Required approving reviews remain 0.
6. Maintainer checks the verdict SHA equals current head, required checks pass, all findings have valid reviewer resolution, impact categories and release note are complete, then merges. A maintainer—not an agent—resolves any disputed or exhausted case.

### 7.3 Pilot measures

Record issues/PRs attempted, rounds used, stale verdicts, disputes/escalations, closures/replacements by slice, doc impact dispositions changed in review, bypasses, and time to review. Count user-found bug PRs where test-first was impossible and the stated reason. Record workflow friction and surprises weekly. Review the exception rate and any repeated bypass before tightening automation.

## 8. Maintainer actions and deferred decisions

Before Stage 1, the maintainer should compare `docs/product-requirements.md` with current product intent and file any corrections through an issue. During the pilot, maintain a short weekly surprise/friction log and confirm that any external Claude Build project integration still points to the intended repository before using it; neither item blocks the proposal review. The decision-capture prompt belongs in the repository under package 1; it is not an instruction to edit the external project directly.

The public community-triage guide is not silently rewritten as the internal Triage status changes. O10 is settled through a separate review of contributor expectations, followed by its own doc issue/PR.

## 9. Deferred work

- Superpowers skills, until the manual pilot exposes a specific gap.
- Phase 2 consumer defaults and upgrade management, until first-party adoption provides evidence.
- Automated issue/PR review or fixes beyond read-only checks, until §6 security gates pass.
- Automated drift checks beyond links/schema/reference tests, until package 10 identifies canonical docs and owners.
- Any 1.x freeze, fixed schedule or release milestone commitment; the maintainer has confirmed the schedule is flexible.
