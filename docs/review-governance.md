# Team Review Governance

Base's repository configuration keeps the existing solo-maintainer behavior
when no team policy is declared. Teams that adopt Base can opt into a stronger,
repository-owned review policy through `basectl repo configure`; the command
must never silently lower an existing GitHub protection.

The implemented configuration contract and readback behavior are documented in
[Repository Baseline](repo-baseline.md). This page is the
governance boundary: a team chooses its policy explicitly, while GitHub remains
the enforcement authority.

The implementation was delivered under
[#2107](https://github.com/basefoundry/base/issues/2107).

Declare `.github/base-review-policy.yml` with `required_approving_reviews`
(0 through 6) and `require_code_owner_review` (`true` or `false`). Preview with
`basectl repo configure --dry-run`, then apply with `basectl repo configure`.
Configuration preserves stronger existing settings and verifies the effective
GitHub result; it fails when it cannot establish or read back that result.

Record the effective policy in the repository's contribution guidance.
A missing policy preserves the existing solo-maintainer default; it is not
evidence that review is unimportant. A CODEOWNERS file identifies ownership,
but code-owner approval is enforced only when the corresponding GitHub rule
is enabled.
