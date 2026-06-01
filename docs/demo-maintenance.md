# Demo Maintenance

Base demos are executable onboarding material. They should move when the product
contract moves, but the process should stay lightweight until automation is
worth the complexity.

## `needs-demo` Label

Apply the `needs-demo` label to issues or pull requests that should change a
Base demo, the `base-demo` reference project, or demo documentation.

Use the label when work changes:

- public `basectl` commands, flags, output, or workflow order
- `base_manifest.yaml` contracts that a demo should teach
- setup, check, doctor, run, test, activate, or project-discovery behavior
- repository baseline expectations for Base-managed projects
- onboarding guidance that should be reflected in an interactive walkthrough

Do not use the label for internal-only refactors, test-only changes, copyedits
that do not alter demo behavior, or implementation details that a new user
should not see in a walkthrough.

## PR Convention

When a PR closes or materially advances a `needs-demo` issue, include a
`Demo Impact` section in the PR body:

```markdown
## Demo Impact

- Demo target: `base`, `base-demo`, or both
- Needed change: one short sentence
- Suggested location: script, README, docs page, or "none"
```

Use `Suggested location: none` when the change was evaluated and does not need a
demo update after all. That keeps the label useful without forcing noisy demo
edits.

## `base-demo` Repository

`codeforester/base-demo` should use the same `needs-demo` label with the same
color and description as this repository:

- color: `fbca04`
- description: `Change should update a project demo`

Cross-repository work should link the Base issue or PR that caused the demo
change. Base remains the source of truth for product behavior; `base-demo`
shows that behavior in a small reference project.

## Automation Boundary

For now, the process is manual: label the issue or PR, describe the demo impact,
and update the relevant demo in the same PR train or a follow-up PR.

Do not add generated weekly demo sync, LLM-based patch generation, or
cross-repository automation until the manual label process proves useful and the
`base-demo` repository has stable scripts and tests.
