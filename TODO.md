# TODO

Action items from Claude's Base code analysis for version `0.1.0`.

Use this as a commit-by-commit work queue. Completed items are removed after
they are merged.

## Design Issues

- [ ] Design optional organization-wide Base config policy.
  - File: `docs/base-cli-design.md`
  - Goal: decide whether Base should support machine- or organization-managed config, where it should live, and how users can inspect or opt into it.
  - Note: v1 intentionally does not read `/etc/base.d/config.yaml` implicitly.
