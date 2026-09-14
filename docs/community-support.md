# Community Support

Base Discussions is the canonical public forum for the Base Foundry ecosystem:

<https://github.com/orgs/basefoundry/discussions>

Start with the [welcome post](https://github.com/orgs/basefoundry/discussions/2276)
for the short version of these boundaries.

The organization profile and repository README link to this same location so a
new adopter does not need to guess which repository owns an ecosystem-wide
question. The Base repository currently exposes public Discussions and public
Issues. Issues remain for scoped, actionable work; Discussions are for open-
ended questions, adoption help, design conversation, announcements, and
examples.

## Where a question belongs

| Need | Public path | What to include |
| --- | --- | --- |
| Usage or adoption help | [Q&A](https://github.com/orgs/basefoundry/discussions/categories/q-a) | Goal, repository or component, version, environment, and what you tried |
| An actual project or integration | [Show and tell](https://github.com/orgs/basefoundry/discussions/categories/show-and-tell) | What you built, the relevant Base boundary, and a link that is safe to share |
| An ecosystem design or compatibility proposal | [Ideas](https://github.com/orgs/basefoundry/discussions/categories/ideas) | User problem, desired outcome, alternatives, and compatibility constraints |
| Community priorities | [Polls](https://github.com/orgs/basefoundry/discussions/categories/polls) | The decision, options, and the evidence needed to interpret responses |
| Announcements or a question that does not fit another category | [General](https://github.com/orgs/basefoundry/discussions/categories/general) | A concise context, the intended audience, and the next action |
| A reproducible defect | [Base Issues](https://github.com/basefoundry/base/issues/new/choose) | Version or commit, environment, minimal reproduction, expected and actual behavior |
| A proposed implementation | [Base Issues](https://github.com/basefoundry/base/issues/new/choose), then a PR | Acceptance criteria first; implementation and validation in the PR |
| A vulnerability or private conduct concern | [Private security advisory](https://github.com/basefoundry/base/security/advisories/new) | Affected repository/component, version, impact, and safe contact method |

The five active categories are used with the meanings above. Category names and
descriptions are GitHub repository settings; if an administrator changes them,
update this table and the welcome discussion in the same change.

## Response and escalation

The project is maintained with finite capacity and does not promise a response
to every post. The working target is:

- acknowledge or triage a clear question within 7 calendar days when capacity
  allows;
- provide a substantive next step, request for evidence, or honest deferral
  within 14 calendar days; and
- use the same discussion for follow-up rather than opening duplicate threads.

If a clear question has no response after 14 days, add one concise follow-up
with the missing context and link it from a related issue or pull request when
one exists. If it still needs maintainer attention, reference the discussion in
the next relevant release or triage pass. Do not repeatedly mention individual
maintainers or promise a date that has not been accepted.

Security reports bypass this process and must use the private advisory path.
Conduct and privacy concerns must also remain private; do not use a public
discussion to escalate them.

## From discussion to issue

1. Start in Discussions when the question is exploratory, cross-repository, or
   needs community context.
2. Record the problem, affected component, desired outcome, and evidence in the
   discussion. Mark the answer when the question is resolved.
3. When the work is specific enough to own, open a scoped issue in the
   repository that owns the behavior. Link the discussion in the issue body and
   copy only the relevant, non-sensitive context.
4. Keep the discussion open as design context while the issue is implemented.
   The issue owns acceptance criteria, and the pull request owns implementation
   and validation evidence.
5. After the issue is resolved, return to the discussion with a short summary
   and links to the issue, PR, release, or documented workaround. Do not
   auto-close a question without a human-readable explanation.

## First-month prompts

Seed only prompts that reflect real maintainer work or an actual user question.
The sustainable first month is one useful prompt per week:

- Week 1: the welcome post and a source-checkout or installation question;
- Week 2: a real Base Demo or consumer walkthrough in Show and tell;
- Week 3: one narrowly framed cross-repository compatibility or RFC topic; and
- Week 4: one adoption-support question gathered from an actual onboarding
  attempt.

If there is no genuine material for a week, leave it unseeded. Empty space is
preferable to manufactured engagement.
