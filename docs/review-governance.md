# Team Review Governance

Base's repository configuration keeps the existing solo-maintainer behavior
when no team policy is declared. Teams that adopt Base can opt into a stronger,
repository-owned review policy through `basectl repo configure`; the command
must never silently lower an existing GitHub protection.

The executable configuration contract and readback behavior are tracked in
[#2107](https://github.com/basefoundry/base/issues/2107). This page is the
governance boundary: a team chooses its policy explicitly, while GitHub remains
the enforcement authority.

Until the configurable contract is available, teams should apply their desired
ruleset directly in GitHub and record the effective setting in the repository's
contribution guidance. A missing policy is not evidence that review is not
valuable; it means Base must preserve backward compatibility for solo projects.
