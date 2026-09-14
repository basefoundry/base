# Community Triage

This is the shared triage contract for Base, base-cli, and base-bash-libs. It
turns a public question into an issue that a contributor can understand, claim,
implement, and hand off for review. It complements the [public support and
discussion policy](community-support.md); it does not replace repository-specific
bug, security, release, or test requirements.

## Response target

The working target is to acknowledge or triage a clear public question within 7
calendar days when capacity allows, and to provide a substantive next step,
evidence request, or honest deferral within 14 calendar days. These are service
targets, not a promise that every issue will be answered.

If a question is unanswered after 14 days, add one concise follow-up with the
missing context. At the next monthly review, either keep it open with an
explicit next step, request reproduction evidence, move it to design, or close
it with a human-readable reason. Do not auto-close an issue solely because it is
old.

## Labels

Use the existing repository category label (`bug`, `enhancement`,
`documentation`, `ci`, or `security`) as the primary classification. The shared
community labels are:

| Label | Meaning | Use it when |
| --- | --- | --- |
| `good first issue` | A narrow task that an outside contributor can complete with public documentation and tools | Acceptance criteria and validation are explicit; no private architecture or cross-repository setup is required |
| `help wanted` | Maintainers welcome an outside contribution | The work is contribution-ready, even when it is not a first issue |
| `needs design` | An explicit design decision is still required | Do not advertise the issue as starter work until the decision is recorded |
| `needs reproduction` | Evidence is insufficient to triage behavior | Request version, environment, and minimal reproduction without requesting secrets |
| `adoption support` | The issue concerns onboarding, usage, or an adopter-facing support gap | Route broad questions to Discussions first |
| `area: docs` | Documentation and public guidance ownership | Use for docs, templates, and public policy work |
| `area: runtime` | Runtime, lifecycle, execution, or process-boundary ownership | Use for behavior in those surfaces |
| `area: release` | Release, packaging, provenance, or distribution ownership | Use for release and installer surfaces |
| `area: community` | Community health, triage, support, or contributor experience ownership | Use for community operations |

Repository-specific area or Project fields remain authoritative where they
already exist. Do not add a maintainer as the default assignee to a community
report; assignment means someone has explicitly accepted the next action.

## Issue lifecycle

| State | Entry bar | Exit evidence |
| --- | --- | --- |
| Idea | A question, proposal, or reported need exists | The owner and desired outcome are clear, or the item is redirected to Discussions |
| Ready | Goal, scope, acceptance criteria, validation, and non-goals are present | A contributor or maintainer claims the next action |
| In progress | The claimant has commented, opened the issue branch, or linked a draft PR | A focused PR or an explicit decision is ready for review |
| Review | The PR links the issue, explains validation, and has the repository's checks running | Review comments are resolved and the PR is merged or superseded |
| Done | The change or decision is complete | The issue is closed with the merged PR, release, workaround, or reason |

### Claiming work

Before starting, search open branches and pull requests for the issue number and
comment with the intended scope. A maintainer can acknowledge the claim, point
to an existing effort, or identify a dependency. Do not create a second PR when
one is already active. If no acknowledgement arrives, keep the claim in the
issue and make the smallest visible draft or evidence update; do not assume
exclusive ownership indefinitely.

## Starter queue baseline

As of 2026-09-14, the initial outside-contributor queue contains eight open,
focused issues. Each has `documentation`, `good first issue`, `help wanted`, and
`area: docs`; none requires private workspace knowledge.

| Repository | Issue | Contribution shape | Focused validation |
| --- | --- | --- | --- |
| Base | [#2278](https://github.com/basefoundry/base/issues/2278) | First-run troubleshooting decision tree | Internal-link review and `git diff --check` |
| Base | [#2279](https://github.com/basefoundry/base/issues/2279) | Focused JSON output example | Documented read-only command and link review |
| Base | [#2280](https://github.com/basefoundry/base/issues/2280) | Downstream release smoke test | Public release-doc review and `git diff --check` |
| base-cli | [#344](https://github.com/basefoundry/base-cli/issues/344) | Five-minute `run_app` consumer recipe | Recipe run, focused test, and `git diff --check` |
| base-cli | [#345](https://github.com/basefoundry/base-cli/issues/345) | Strict Node JSON consumer validation | Node contract command and link review |
| base-cli | [#346](https://github.com/basefoundry/base-cli/issues/346) | Optional output-format dependency guide | Metadata/message review and `git diff --check` |
| base-bash-libs | [#491](https://github.com/basefoundry/base-bash-libs/issues/491) | Bash 4.2 support and validation quickstart | Focused help/validation command and link review |
| base-bash-libs | [#492](https://github.com/basefoundry/base-bash-libs/issues/492) | Consumer-kit contribution path | Focused consumer-kit BATS test and link review |

The queue is deliberately documentation-heavy for its first pass. Promote a
code issue to `good first issue` only after its acceptance criteria, test
fixture, and public setup path are equally explicit. Remove the label if a task
turns out to need private architecture knowledge or cross-repository changes.

## Monthly review

The first monthly triage review is scheduled for 2026-10-01. The review output
belongs in a dated comment on this issue (#2268) and should link every decision
back to the affected issue or discussion. The baseline to carry into that
review is:

- eight starter issues listed above, all open and unassigned;
- the shared labels present in Base, base-cli, and base-bash-libs;
- public Discussions enabled at the organization front door; and
- no response-time promise beyond the 7/14-day working targets.

At each review, record the number of new, ready, claimed, blocked, in-review,
and done issues; identify one or two next actions; remove stale `good first
issue` labels; and note any intentional closure or deferral. A useful review
can report that no change was needed. Do not manufacture prompts, comments, or
activity to make the numbers look healthier.

## Discussion handoff

Use the [community support workflow](community-support.md#from-discussion-to-issue)
when a Discussion becomes actionable. The issue owns acceptance criteria; the PR
owns implementation and validation; the original discussion remains linked as
design context. Security reports bypass public triage and use a private advisory.
