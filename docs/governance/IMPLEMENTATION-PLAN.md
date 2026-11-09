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
4. The reviewer is a separate fresh-session agent with no author transcript or persistent authoring memory. A repository setting selects `fresh-session` or `different-tool`; the nine Base ecosystem repositories default to the latter, while Base-supported projects such as `banyanlabs` use the former. Record author/reviewer tool, model and session in each verdict.
5. Every finding gets an author response and reviewer verification/resolution. Disputes and round-limit exhaustion go to the maintainer. PR verdicts cite the full head SHA; a changed code commit requires a fresh review. Base-only re-verification is tracked separately and does not consume a round only when `git range-diff`, using the recorded old/new base and head SHAs, shows every non-merge PR commit unchanged, and every merge commit introduced is a base-update merge on the PR first-parent chain whose second parent is an ancestor of the updated base; `git show --remerge-diff` must be empty for each. If a check is unavailable, uncertain, or shows a change, require a full review round.
6. Required approving reviews remain zero while both agents use one GitHub identity. The maintainer manually audits reviewer responses/resolutions and merges. A separate reviewed branch-policy train enables required conversation resolution; it must not raise the approval count.
7. Issues and PRs use the same ten documentation-impact categories from Design §12.10. Every category has a destination or an evidence-based no-impact reason. Every PR has a release-note line or a reasoned `none`.
8. Every bug a user found gets a failing test before its fix. If testing is genuinely impossible, the PR explains why. Count these exceptions during the pilot.
9. Keep checked-in `.ai-context/` maintained until the replacement export command is released and proven. Remove it later through separate repository trains.
10. Keep Superpowers deferred unless the pilot shows a specific spec-driven development or drift-prevention gap.

## 2. Rollout and rollback

| Plan stage | Work | Maps to design | Exit evidence and rollback |
|---|---|---|---|
| **A. Accept the proposal** | Resolve review findings on #2664; maintainer accepts the design and plan. | Before Stage 1 | All review threads answered and resolved by reviewer; checks green. Rollback: leave proposal open or close as not planned; no policy is active. |
| **B. Establish source contracts** | ADR/document impact, single issue and PR templates, manifest governance schema and repository `basectl config`, reviewer rules/prompts, and a pre-pilot baseline. Template work is independent of config implementation. | Design Stage 1; packages 1–3, 5, 16–17 | One current issue and PR pass the manual checklist; baseline method and limits are recorded. Rollback: revert the template/config PR; retain the prior Project schema and config reader. |
| **C. Run manual loops** | Issue and PR review runbooks, response/resolution audit, SHA-bound verdicts, three-round cap and maintainer escalation. | Design Stage 1; packages 4 and 6 | Pilot issues reach Ready and PRs reach merge without bypass; record exceptions/friction against the baseline. Rollback: pause new intake under the new process, return to current documented workflow, and preserve all review evidence. |
| **D. Build and dry-run deterministic checks** | Readiness fingerprints, round ledger, slice-based issue-status reconciliation, manifest validation, conversation-resolution policy, warn-only behavior and explicit maintainer overrides. No automated check is enabled before it can run from the pin in E. | Design Stage 2; packages 7, 9 and 19; Project schema package 8 is a prerequisite for each repo | Dry-run results match maintainer decisions on a representative sample. Rollback: discard the dry-run build and continue manual reconciliation; restore branch settings only through a reviewed policy PR. |
| **E. Pin and enable warn-only enforcement** | Run checks from a pinned, released Base version from first automated use; begin with non-blocking warnings, then promote individual rules to blocking/reversion only after their warnings prove reliable. | Design Stage 2; package 20 | Pin provenance, upgrade/rollback path and per-rule promotion evidence are recorded. Rollback: return affected rules to warn-only and the last known-good pin. |
| **F. Add drift checks and a read-only reviewer** | Evidence-backed document-kind checks and a least-privilege read-only review pilot; no automated fixes. | Design Stage 3; packages 10, 11 and 21 | Security gates in Design §14.6 pass; findings cite evidence and create issues rather than silently editing policy. Rollback: disable the workflow/app; manual review and documentation checks continue. |
| **G. Adopt across all organization repositories** | Apply the accepted stages through separate repository trains, migrate each live Project, and rename all open issue/PR titles after templates and rules are in place. | Repository rollout; packages 8, 12 and 18 | Every repository has a recorded before/after schema, governance profile, title inventory and workflow check. Rollback: revert that repository's adoption PR or disable its automation; never silently overwrite project-specific configuration. |
| **H. Replace AI context files** | Release the new `export-context`, then remove `.ai-context/` and stale scheduled exports in separate repo trains. | Separate product-dependent work; packages 13–14 | Prove output location, sources, privacy, provider selection and failure behavior first. Rollback: keep or restore the maintained tracked files and scheduled export until the replacement works again. |

Stages may overlap only after dependencies are met. A rollback is itself a reviewed PR or an explicit maintainer-controlled GitHub setting change with an issue/evidence record.

## 3. Candidate issue/PR work packages

These are candidate issue trains, not implementation authorization. Create or rescope issues only after #2663 is accepted. The reviewer checks for duplicate live issues and preserves existing issue numbers when their scope matches. Sizes are relative: S = a few focused files; M = several files or one migration; L = cross-repository or stateful migration.

| Order | Work package | Main deliverable | Depends on | Size |
|---|---|---|---|---|
| 1 | Documentation and ADR contract | Confirm document locations and ownership; one canonical impact taxonomy; ADR template/index; decision-capture and area-reading instructions; maintainer review of the PRD against intent, with any PRD correction filed separately | A | M |
| 2 | Single issue form and manual Ready contract | One form; current-Type requirements; Bug reproduction steps; category 6 validation mapping; manual readiness checklist; remove category title prefixes | A, 1 | M |
| 3 | Repository governance configuration | Manifest schema, distinct loop limits, reviewer independence, 30-day Ready freshness, `basectl config`; deprecate old review-policy reader safely | A | M |
| 4 | Manual issue-loop pilot | Fresh-session reviewer runbook, verdict/fingerprint record, three-round cap, maintainer escalation; no bot status writes | 2, 16, 17; may use documented defaults before package 3's CLI exists | M |
| 5 | PR template and release-note contract | Single PR template; issue/slice link; plan/acceptance trace; one ten-category impact-and-evidence matrix; release-note line; risk/rollback/notes; implement and test `basectl release notes` assembly | 1; independent of 3 | M |
| 6 | Manual PR review loop | Finding-response procedure, reviewer thread resolution, full-head-SHA verdict, round tracking and safe base-only re-verification, maintainer merge gate | 5, 16, 17; round ledger may wait for 3 | M |
| 7 | Lifecycle and readiness automation | Issue contract fingerprint, freshness check, current-Type check, delivery-slice states, draft handling, PR-body validation, and status reconciliation | 2, 3, 4, 6 | L |
| 8 | GitHub Project schema and data migration | Update shared defaults in `project_model.py`; migrate actual Project values; re-sequence/redefine Status; migrate Priority P0→P1, P1→P2, P2→P3, P3→P4; add Risk tier; record before/after values; retain repo-specific area/initiative extras and issue defaults | A; pilot in Base before its dependent automation, then per-repository rollout | L |
| 9 | Branch protection baseline | Keep required approvals at 0; enable required conversation resolution through a reviewed setting change; preserve human maintainer merge authority and never-automatic sensitive path list | 6 and maintainer review | M |
| 10 | Evidence-backed documentation inventory | Crosswalk PRD, area designs, code/reference, user guides, README/FAQ, operations/security, decisions, release notes, examples and templates to canonical owners; identify required migration, with README revised last | 1 | M |
| 11 | Area map and drift checks | Path-to-area map and tested per-kind checks; evidence-only findings create issues, not silent edits | 10; pilot evidence | L |
| 12 | First-party repository adoption | Apply accepted governance to every `basefoundry` repository: nine ecosystem repositories use ecosystem defaults; `banyanlabs` uses consumer defaults and needs no `governance/` directory; add `homebrew-base`'s minimal manifest | 3–9, 16–17, 19–20 as applicable; rollout gate | L |
| 13 | Generated AI context | Implement `basectl export-context` through user-selected installed CLI, allowlist, external export location, source/date stamping, privacy disclosure and threat model | Separate product/security issue | L |
| 14 | Context-file cleanup | Remove checked-in `.ai-context/`, update `AGENTS.md`/`CONTRIBUTING.md`/manifest checklist and scheduled export paths, one repository train at a time; remove only the `.ai-context/` validation from #2572's successor check | 13 released and proven; new PR contract in 5 and validator in 7 retained | L |
| 15 | Consumer governance defaults | Decide which first-party rules generalize; versioned configure/upgrade PRs; no live inheritance and no required `governance/` folder | Exit evidence from B–G | L, deferred |
| 16 | Reviewer rule sets, prompts and method map | Add versioned issue/PR reviewer rules and prompts under optional first-party `governance/`; add `METHOD.md` and an `AGENTS.md` map to canonical process, decision and area documents | 1; before packages 4 and 6 | M |
| 17 | Pre-pilot baseline | Capture the defined review, drift, rework, escape and manual-intervention measures on a declared historical sample; document missing data and limits before the manual pilot starts | Design §17.4; before packages 4 and 6 | S |
| 18 | Open-title migration | Inventory and rename every open issue and open PR, including drafts, to plain outcome/problem titles after the new templates and title rule are live; retain closed/merged titles | 2, 5, 12 | M |
| 19 | Warn-only rules and override record | Implement lifecycle checks with non-blocking, non-reverting behavior and a scoped, expiring, reasoned maintainer override record; keep automated execution disabled until package 20 establishes the pin | 7, 9 | M |
| 20 | Pinned enforcement and per-rule promotion | Run governance checks from a pinned released Base version at first automated use; document pin upgrades and rollback; begin in warning mode and promote individual rules only after evidence shows reliable results | 19 and a released checker | M |
| 21 | Read-only review automation pilot | Build a least-privilege reviewer that reads an exact issue/PR revision, cannot execute untrusted code or access secrets, records provenance, and posts evidence-backed findings; automated fixes stay deferred | 10, 11, 16, 20 and security/threat review; Stage 3 gate | L |

### 3.1 Repository configuration contract

The selected machine-readable home is the `governance:` section of each repository's existing `base_manifest.yaml`. The two loop limits are separate keys, both default to three. The same section carries reviewer mode, Ready freshness and the current review-policy value; existing GitHub PR requirements remain under `github.pr`. There is no `base-governance.yml` and no `.base/` directory.

`basectl config` must make repository scope explicit, validate the manifest schema, preserve machine-local config behavior, print a useful diff, and fail clearly outside a repository or when a setting is unsupported. Bounds and exact CLI syntax are fixed in the config issue. The `.github/base-review-policy.yml` path is migrated with a compatibility period; do not remove its reader until the repository config and docs are released. The shared Project schema/default options live in `cli/python/base_github_projects/project_model.py`; `.github/base-project.yml` contributes repository-specific `areas`, `initiatives` and `issue_defaults`, with repository areas extending the shared Area list. Migration inventories live Project values rather than assuming that either file alone describes them; do not create duplicate catalogs in `governance/`.

First-party repositories may put reviewer rules, standards and prompts in a modular `governance/` directory. Base-supported consumer projects need no new directory: Base defaults are materialized only through an explicit configure/upgrade operation and a reviewed PR. No value is inherited live from Base.

### 3.2 Issue and PR review-round contract

Each loop uses a separate repository-configured maximum; the initial evaluation is round one. One round is a reviewer evaluation after the author had an opportunity to respond to the previous findings. A round may contain multiple findings. A base-only update is a re-verification, not a round, only when `git range-diff`, using the recorded old/new base and head SHAs, shows every non-merge PR commit unchanged, and every merge commit introduced is a base-update merge on the PR first-parent chain whose second parent is an ancestor of the updated base head; `git show --remerge-diff <merge-commit>` must be empty for each. A conflict-resolution addition, non-base merge, any non-merge PR change, or an unavailable/uncertain check requires a new review round. Re-verification records the new full head SHA. At the limit, unresolved findings stop for a maintainer; the process never approves by timeout.

For each finding, the author replies with a fix/commit or a challenge and evidence. The reviewer verifies the response and resolves the thread when justified; otherwise the thread remains open and goes to the maintainer if disputed. The GitHub identity is shared during the pilot, so this is a manual audit rule, not an enforceable author/reviewer identity distinction.

## 4. GitHub metadata and migration contract

- **Type:** use the current native values Task, Bug and Feature. Do not invent Documentation, CI, Security or Enhancement types. Decide separately whether Feature becomes Enhancement before changing the type set.
- **Fields:** issue Project fields are canonical. Status, Priority, Size, Area, Initiative and the proposed Risk tier are not copied to PRs. Do not duplicate them in organization Issue Fields.
- **Priority migration:** record counts for each old value on every affected Project, perform P0→P1 through P3→P4, and verify counts after. Old `Priority:` text in issue bodies is historical, not backfilled.
- **Risk:** create a new Low/Medium/High Project field; it does not exist today. No per-area floor until its use is proven.
- **Status migration:** update schema order/descriptions and `docs/github-workflow.md`; distinguish the public community-triage process pending O10. Record all values and issue counts before and after.
- **Labels:** preserve category labels because branch policy reads them today. `security` is a valid label; private vulnerability intake remains separate. `good first issue` and `help wanted` keep spaces.
- **Relationships:** use native linked PRs, sub-issues and blocked-by relationships where they express delivery or dependency; do not use PR Project cards as field mirrors.

The repository inventory package must inspect the live Projects for all ten repositories named in package 12, record whether each has a Project, schema and distinct options, and capture counts before/after. `project_model.py` defines shared defaults; `.github/base-project.yml` adds repository-specific Area/Initiative values and issue defaults. It must not assume every repository has an identical Project or silently discard a value.

## 5. Existing issue crosswalk

Reconcile these known candidates before creating new issues. This table is a scope recommendation; issue status/body edits require their own authorized issue train after #2663 is accepted.

| Existing issue | Recommended disposition |
|---|---|
| #2571 readiness workflow | Rescope to packages 2 and 7; preserve its current acceptance criteria only where they match the fingerprint/Ready contract. |
| #2572 PR-body contract validator | Rescope it to validate the new PR template under packages 5 and 7: linked issue/slice, validation evidence, all ten impact categories (including Demo Impact in category 7), and release-note line or reasoned `none`. Package 14 removes only the obsolete `.ai-context/` item check; retain the validator and its other contract checks. |
| #2573 structured Agent Assignment | Close or rescope to verdict provenance outside the issue body; the assignment field is not part of the canonical issue contract. |
| #2574 PR classes allowed to merge without human review | Keep on hold while the governance proposal is reviewed; then close as superseded because the design requires a human maintainer to merge every PR. Preserve the never-automatic path list in package 9's branch/merge policy and package 21's reviewer boundaries. |
| #2576, #2599, #2580, #2581, #2584 | Crosswalk to packages 6, 7, 9, 19–21; split state-machine, authority, bounded repair and autonomy ceiling work into small trains. |
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
3. Start the reviewer in a genuinely new session. Do not include the author's chat or persistent memory. Give it the issue, repository, active decisions and the versioned rules/prompts from package 16. If configured `different-tool`, use that tool; if unavailable, wait or escalate.
4. Reviewer posts one consolidated result with numbered findings, contract fingerprint, tool/model/session provenance and round number. Initial result is round one.
5. Author replies to each finding; maintainer decides disputes. Reviewer verifies and records a new verdict. After three rounds, stop for maintainer decision.
6. Maintainer confirms the verdict matches the current contract fingerprint and sets Ready.

### 7.2 PR loop

1. The PR links one issue and declares one slice. It may start as draft; the issue remains In Progress.
2. Reviewer reads the issue, slice, PR diff, tests, docs and review rules in a new session. It records the complete current head SHA and provenance.
3. Author responds to every finding; reviewer verifies and resolves addressed threads. Challenges and unresolved findings go to the maintainer. Every follow-up review against changed code uses the next round.
4. If only the base branch moved, compare all non-merge PR commits with `git range-diff`, using the recorded old/new base and head SHAs, and inspect each merge commit introduced since the prior reviewed head with `git show --remerge-diff <merge-commit>`. Only unchanged non-merge commits plus merges on the PR first-parent chain whose second parents are ancestors of the updated base, with empty remerge diffs, qualify for a base-only re-verification; record its new head SHA separately without consuming a round. Any other result, including an unavailable or uncertain check, requires a fresh review at the new SHA and consumes a round.
5. After no actionable finding remains, reviewer posts `Verdict: Approved at <full-head-SHA>`. Approval here is a process verdict, not a GitHub approving-review event. Required approving reviews remain 0.
6. Maintainer checks the verdict SHA equals current head, required checks pass, all findings have valid reviewer resolution, impact categories and release note are complete, then merges. A maintainer—not an agent—resolves any disputed or exhausted case.

### 7.3 Pilot measures

Before the pilot, package 17 captures a baseline for the defined measures from a declared sample of existing issues/PRs and prior drift audits; it records sample boundaries, missing data and limits. During the pilot, record issues/PRs attempted, rounds used, stale verdicts, disputes/escalations, closures/replacements by slice, doc impact dispositions changed in review, bypasses, and time to review. Count user-found bug PRs where test-first was impossible and the stated reason. Record workflow friction and surprises weekly. Compare results with the baseline cautiously; do not imply causation from a small or incomplete sample.

## 8. Maintainer actions and deferred decisions

Before Stage 1, the maintainer compares `docs/product-requirements.md` with current product intent; any correction is filed through its own issue/PR. Package 10 inventories the README and other docs, then updates the README last after canonical detail has moved to its intended homes. During the pilot, maintain a short weekly surprise/friction log and confirm that any external Claude Build project integration still points to the intended repository before using it; neither item blocks the proposal review. The decision-capture prompt belongs in the repository under package 16; it is not an instruction to edit the external project directly.

The public community-triage guide is not silently rewritten as the internal Triage status changes. O10 is settled through a separate review of contributor expectations, followed by its own doc issue/PR.

## 9. Deferred work

- Superpowers skills, until the manual pilot exposes a specific gap.
- Phase 2 consumer defaults and upgrade management, until first-party adoption provides evidence.
- Automated fixes, until a separate authorization model, threat review and permission test pass. Package 21 is read-only and does not authorize code changes.
- Automated drift checks beyond links/schema/reference tests, until package 10 identifies canonical docs and owners.
- Any 1.x freeze, fixed schedule or release milestone commitment; the maintainer has confirmed the schedule is flexible.
