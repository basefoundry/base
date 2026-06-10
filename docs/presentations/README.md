# Base Presentations

This directory holds text-first presentation sources for Base. Presentations are
orientation material, not canonical product references. When slide content needs
implementation detail, link to the README or focused documentation page instead
of duplicating the reference text.

## Decks

- [Base Newcomer Orientation](base-newcomer-orientation.md) introduces Base as
  a workspace control plane for multi-repo development.

## Source Of Truth

The markdown file is the canonical deck source. Generated PDF or PPTX files are
not committed by default because they are derived artifacts and can drift from
the checked-in source.

Attach generated files to a release, workshop note, or external sharing surface
when needed. If generated artifacts are ever committed later, the PR should
state why, name the exact source revision, and update this policy.

## Export Path

Use Marp CLI when a shareable PDF or PPTX is needed. The commands below generate
artifacts from the checked-in markdown source without adding Marp to Base's
default setup path.

```bash
mkdir -p /tmp/base-presentations

npx --yes @marp-team/marp-cli \
  docs/presentations/base-newcomer-orientation.md \
  --pdf \
  --output /tmp/base-presentations/base-newcomer-orientation.pdf

npx --yes @marp-team/marp-cli \
  docs/presentations/base-newcomer-orientation.md \
  --pptx \
  --output /tmp/base-presentations/base-newcomer-orientation.pptx
```

For repeatable workshop or release exports, record the Marp CLI version used:

```bash
npx --yes @marp-team/marp-cli --version
```

## Validation

Ordinary documentation validation does not require export tooling:

```bash
git diff --check
```

When export tooling is available, smoke-test the export commands before sharing
generated files and inspect the resulting PDF or PPTX manually.
