# Base Ecosystem Governance Implementation Plan

**Version:** 3.0, 8 November 2026
**Status:** Proposed sequence for review; no governance automation is authorized by this plan alone.
**Owner:** Ramesh (codeforester)
**Companion:** [Governance Design](DESIGN.md)
**Tracking issue:** [#2663](https://github.com/basefoundry/base/issues/2663)

This plan sequences the design into issue/PR trains. Each train receives its own reviewed issue, acceptance criteria, impact map, and PR. Existing candidate issues must be checked and respecified before use; this document does not assume an older issue still matches the design. The design and plan remain proposals until their PR is reviewed and merged by the maintainer.

## 1. Delivery principles

1. Make the governance design and this plan review-ready first. Claude reviews the open PR; the maintainer decides whether to merge it.
2. Keep the issue as the canonical planning and Project-metadata record. The normal unit is one issue and one PR. If an issue needs multiple PRs, enumerate the complete delivery set and each slice in the approved plan.
3. Keep the lifecycle Backlog → Triage → Ready → In Progress → In Review → Done. For a planned multi-PR issue, keep it In Progress until every planned PR exists; set In Review when all are Open or Merged; set Done when all are Merged or Closed, recording the disposition of unmerged closures.
4. Keep issue Project fields on the issue. Use GitHub linked PR relationships for navigation; do not add PR Project items to mirror fields.
5. Configure separate issue and PR review-round limits in a tracked repository file. Start both at three rounds. The first reviewer evaluation is round one; unresolved findings at the limit go to the maintainer.
6. Require an author response to every review finding. The reviewer verifies and resolves addressed threads. Disputes go to the maintainer. A PR approval applies to one head SHA; every later code push requires fresh review.
7. Update every affected durable document in the implementation PR or record a specific, evidence-backed no-impact disposition. No implementation train may mark documentation impact “none” solely because the change is called maintenance or refactoring.
8. Automate only after the manual workflow is demonstrated. Automated review and fixes follow the security boundary in Design §14.6. No agent merges, releases, or silently rewrites governance.
9. Do not remove checked-in `.ai-context/` files until the replacement export feature is released. Then remove them in separate repository issue/PR trains.
10. Leave Superpowers skills deferred until the pilot demonstrates a real gap in spec-driven development or drift prevention.

## 2. Rollout sequence

| Stage | Outcome | Exit gate |
|---|---|---|
| A. Review the proposal | Claude-reviewed Design and Plan committed through #2663 | All material review findings addressed; maintainer accepts the proposal PR. |
| B. Establish source contracts | Repository-owned loop configuration, issue/PR templates, and explicit lifecycle rules | Schema and templates pass validation; one real issue and PR use the manual process. |
| C. Pilot manual loops | Separate three-round issue and PR loops, documentation-impact review, reviewer thread resolution, SHA-bound approval | A small set of varied changes completes without bypass; maintainer reviews escalations and friction. |
| D. Build deterministic checks | Readiness, PR-policy, documentation inventory and generated/reference checks | Each check has evidence that it catches a real mismatch and does not make a model judgment. |
| E. Introduce guarded automation | Read-only review automation first; constrained fixes only after a separate security gate | Threat review, permissions test, fork isolation and rollback evidence pass. |
| F. Roll out to Base Foundry repos | Versioned defaults copied from Base; each repository adopts through its own PR | No live remote inheritance; each repository has an owner and verified config. |
| G. Replace repository context files | Implement and release generated context export, then remove `.ai-context/` from projects | Export verified in supported environments; each repository cleanup train passes its own checks. |

Stages may overlap only when their explicit dependencies are satisfied. Time estimates are intentionally omitted until the issues are sized from current code and maintainer capacity.

## 3. Issue/PR trains to create or rescope after proposal review

These are planning work packages, not yet implementation-authorized issues. Before creating each issue, inspect the current code, open issues, repository config, docs, and dependencies; reuse a live issue only when its current acceptance criteria match. Use plain issue and PR titles.

| Order | Work package | Main deliverable | Depends on |
|---|---|---|---|
| 1 | Governance proposal review (#2663) | This Design and Plan, with reviewer findings resolved and docs index linked | Current train |
| 2 | Documentation and decision-record contract | Repository document map, PR impact categories, ADR template/lifecycle, document ownership and source-of-truth map | 1 |
| 3 | Repository governance configuration | Root `base-governance.yml`, schema validation, distinct issue/PR round limits defaulting to 3, repository-scoped `basectl config` show/set behavior | 1 |
| 4 | Issue contract and Triage workflow | Type-specific forms plus shared Ready contract, issue review verdict, staleness and Triage/Ready transition | 2, 3 |
| 5 | PR template and review loop | Required impact matrix, author response per finding, reviewer resolution, round ledger, current-head SHA approval and escalation | 2, 3, 4 |
| 6 | Issue/PR lifecycle reconciliation | Reliable association with planned PR set and transitions through In Progress, In Review and Done, including multi-PR exception | 4, 5; GitHub feasibility evidence |
| 7 | Repository protection and safe review automation | Branch protection, least-privilege read-only reviewer, prompt-injection handling, trusted maintainer escalation | Manual pilot and security review |
| 8 | Documentation inventory and migration map | Evidence-backed crosswalk of PRD, area designs, user guides, README, FAQ, reference, release notes, operations docs, demos, decisions and templates | 2; refresh prior drift audit state |
| 9 | Area ownership and drift checks | Path-to-area map, tested references/examples, changed-path/document-impact checks, issue follow-ups for confirmed gaps | 8 |
| 10 | Generated context export | `basectl export-context` invokes a chosen supported AI CLI and writes an allowlisted, sourced artifact outside the repo | Security threat model and provider decision |
| 11 | Base Foundry context-file cleanup | Remove `.ai-context/`, scheduled jobs and stale references from each repository through separate trains | 10 released and proven |
| 12 | Base-supported project defaults | Versioned template distribution, opt-in/configure behavior, upgrade preview and PR-based adoption | 3, 4, 5, 6 validated in Base |

### 3.1 Configuration contract

The initial repository file is proposed as:

```yaml
governance:
  loops:
    issue_max_rounds: 3
    pull_request_max_rounds: 3
```

The implementation issue must decide a safe maximum and validation errors. `basectl config` must distinguish machine-local settings from repository settings; commands that request repository scope must read/write the tracked repository file and fail clearly if no repository is available. A change produces an ordinary diff. Do not repurpose the existing machine-local config or make a user's local setting silently override the committed policy.

Base-supported projects receive the defaults bundled with an installed Base release when they initialize or explicitly configure. They do not inherit a moving Base setting at runtime. Existing repositories see updates through a previewed, reviewable PR. A project may customize supported values within schema bounds.

### 3.2 Review-loop contract

For both issue and PR loops, the reviewer posts one consolidated review per round with numbered findings. The author replies to each finding as fixed or challenged, including evidence or a commit reference. The reviewer verifies and resolves addressed comments. The reviewer does not resolve a finding that is still disputed. Any unresolved dispute, security-sensitive decision, or exhausted round budget stops for maintainer review.

A round is one reviewer evaluation after the author has had an opportunity to respond to the prior evaluation. The initial evaluation is round one. The issue and PR budgets are independent values from repository config. A code push changes the PR head SHA and invalidates prior approval. CI records the reviewed SHA and must not report approval for another SHA.

## 4. Document and metadata decisions to carry into issues

### 4.1 Documentation-impact categories

Every implementation issue and PR considers these categories. Each receives canonical destination paths or a reasoned “No impact” disposition:

- Product intent and PRD.
- Area architecture and behavior contracts.
- User guide, top-level README and FAQ.
- CLI/API, manifest, repository config, schemas and generated reference.
- Security, privacy, operations, release and migration procedures.
- Demos, examples and downstream consumer guidance.
- Decision records and the generated decision index.
- CHANGELOG/release notes.
- Issue, PR, contributor, and maintainer templates/process docs.

This matrix is a review aid, not a requirement to edit every document kind on every change. An impact claim is checked against changed behavior and paths.

### 4.2 GitHub metadata

Use native issue Type for kind of work; Project custom fields for Base’s operational Status, Priority, Size, Area, Risk tier and Initiative; the native issue Milestone for release planning; and GitHub issue relationships for sub-issues/dependencies. Linked PRs show delivery. Do not duplicate those fields as Issue Fields or copy them to PRs. If Base later migrates a canonical value to an organization Issue Field, do so through a dedicated issue/PR train and retire the duplicate Project field in the same migration plan.

### 4.3 Titles

New titles use plain problem/change wording with no category, type, area, or workflow prefix. After templates and checks are adopted, one separate migration issue renames every currently open issue and open PR regardless of Project state or PR draft/ready state. Preserve closed issue and merged/closed PR titles as historical records by default. The migration PR lists old and new titles and verifies linked branch/issue references remain valid.

### 4.4 Public community triage

Keep the current public support and newcomer guidance available while the internal workflow is piloted. A dedicated documentation issue will decide whether and how public “Idea” or support states map to internal Backlog/Triage/Ready. Do not impose the implementation-ready contract on a question or discussion before it becomes planned work.

## 5. Security gates for automated review and fixes

1. Start with review-only automation using least-privilege read access and narrowly scoped comment permissions. No contents write, secrets, deployment credentials, branch-protection changes, merge, or release permission.
2. Never execute fork or other untrusted PR code under a privileged trigger. Do not use `pull_request_target` to check out or run PR code. Treat issue/PR text and repository content as untrusted instructions.
3. Keep provider CLI access and prompts out of privileged runners until data handling, retention, logging and network behavior are approved.
4. If automated fixes are later justified, require an explicit trusted maintainer action, ephemeral isolation, no secrets, and no network by default. Permit only a proposed patch and validation run; a separate reviewer evaluates the resulting SHA.
5. External/fork PRs receive no auto-fix. A maintainer may request a read-only review where privacy and permissions allow.
6. Record tool/model, rule version, commit SHA, actor, and result without persisting secrets or unnecessary private source text. Pin workflow dependencies and cap usage.

## 6. Context-export transition

The `basectl export-context` train defines source allowlists, supported AI CLI adapters, an explicit external output location, provenance (source commit/date/paths), contradiction reporting, secret exclusion, repository read-only behavior, and provider data disclosure. It verifies that output cannot be written within the repository. The user selects the tool/provider; Base does not silently invoke an unconfigured cloud service.

Only after the feature is released and a real export succeeds should cleanup begin. File deletion and reference updates are separate issue/PR trains for `base`, `base-cli`, `base-bash-libs`, `base-demo`, `homebrew-base`, and any other repository confirmed to contain these files. Each train checks scheduled jobs, prompts, docs, generated files, and consumer scripts before removal. If any repo still depends on the current files, defer that repo until migrated.

## 7. Review and rollout evidence

For each stage, record:

- Issues and PRs that completed the workflow, including round counts and head SHAs.
- Findings, author responses, reviewer resolutions, disputes and maintainer escalations.
- Documentation-impact dispositions and actual changed paths.
- Bypasses, false positives, missed findings, time/cost, and any behavior that encouraged bypass.
- Security evidence: workflow event types, permission grants, secret availability, fork behavior, sandbox/network policy, and model-provider data terms.

A stage advances only when the pilot evidence shows the gates are useful, failures are actionable, and no unresolved high-severity security finding remains. Any policy change discovered during the pilot returns through an issue/PR and updates this design before enforcement relies on it.

## 8. Deferred work

- Superpowers or other spec-driven skills: revisit only if the pilot identifies a concrete uncovered need.
- Dynamic live inheritance of Base policy into consumer repositories: not planned; use versioned defaults and explicit upgrade PRs.
- Mirroring issue Project fields onto PRs: rejected.
- Renaming closed issues or merged/closed PRs: preserve history unless a later, evidence-backed migration specifically requires it.
- Auto-merge and autonomous release: out of scope.
- RAG and a remote documentation MCP server: consider only after the canonical documents and drift checks are reliable.
