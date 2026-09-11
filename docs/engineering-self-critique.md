# Engineering Self-Critique: Evidence, Threat Models, and Provenance

Status: maintained public engineering note
Last reviewed: 2026-09-11

Public engineering work should explain not only what a project does, but how
its maintainers test the story they tell about it. This note describes the
review habit used across the Base ecosystem: state the product thesis, inspect
the trust boundaries, verify the release evidence, publish the limits, and
turn unresolved gaps into issue-backed work.

This is an engineering practice, not a claim that the projects are complete,
secure in every environment, or widely adopted.

## The review loop

The loop is deliberately repetitive:

1. **State the product thesis and non-goals.** Say what the project owns, who
   it serves, and which adjacent problems it intentionally leaves to other
   tools.
2. **Separate assertions from evidence.** For each important statement, link
   to current code, tests, documentation, release artifacts, or a permissioned
   usage record. A test result, a fixture, and a customer outcome are different
   kinds of evidence.
3. **Model the trust boundaries.** Identify the assets, inputs, process
   authority, persistence paths, external commands, plugins, and network
   boundaries. Record both controls and residual risk.
4. **Verify the exact release path.** Check that the reviewed source, build
   outputs, checksums, SBOM, and provenance or attestation records refer to the
   same intended revision and artifact bytes.
5. **Publish limitations with the strengths.** A useful review says where the
   controls stop, what evidence is missing, and which claims are deliberately
   not being made.
6. **Create follow-up issues.** If the evidence exposes a product, security,
   compatibility, or documentation gap, record it in the public backlog rather
   than hiding it in a private review note.

The loop is most useful when it runs against the current implementation. A
dated review delta is evidence of what was inspected at that point in time; it
is not a permanent guarantee about future releases.

## Four evidence categories

| Question | Evidence surface | What it can support | What it cannot support |
| --- | --- | --- | --- |
| Is the product problem and boundary clear? | The [Base Product Assessment](product-assessment.md), [Product Requirements](product-requirements.md), and [Tool Boundaries](tool-boundaries.md) | A maintained explanation of the target user, product thesis, non-goals, and current reasoning | Independent market validation or proof that the product is the right choice for every team |
| What can go wrong at runtime? | The [`base-cli` runtime threat model](https://github.com/basefoundry/base-cli/blob/main/docs/security-threat-model.md) and [`base-bash-libs` threat model](https://github.com/basefoundry/base-bash-libs/blob/main/docs/threat-model.md) | A map of assets, trust boundaries, controls, residual risks, and consumer responsibilities | A sandbox, encryption guarantee, or protection from a same-user process, a malicious dependency, or a compromised interpreter |
| Did the published artifact come from the reviewed source? | [`base-cli` release guidance](https://github.com/basefoundry/base-cli/blob/main/docs/releasing.md), [`base-bash-libs` single-file distribution contract](https://github.com/basefoundry/base-bash-libs/blob/main/docs/single-file-distribution.md), and Base's [ecosystem release policy](ecosystem-policy.md) | Artifact identity, deterministic metadata, checksums, SBOM/provenance relationships, and release-process evidence | Proof that the code has no defects or that downstream consumers configured it safely |
| Who uses it and what happened? | [`base-cli` adoption evidence](https://github.com/basefoundry/base-cli/blob/main/docs/adoption-evidence.md) and [`base-bash-libs` validation register](https://github.com/basefoundry/base-bash-libs/blob/main/docs/who-uses-base-bash.md) | Permissioned, reproducible compatibility results and explicitly approved adopter outcomes | Adoption claims based on stars, downloads, first-party fixtures, internal use, or an unconsented private conversation |

Keeping these categories separate prevents a common failure mode: presenting a
strong engineering control as if it were product-market evidence, or presenting
an internal fixture as if it were an independent customer.

## What the Base ecosystem publishes

The practice is visible in several maintained documents:

- Base's [Product Assessment](product-assessment.md) keeps a dated history of
  product reviews, records the current ratings and reasoning, and names the
  evidence still needed before those ratings should change.
- `base-cli` publishes a [runtime threat model](https://github.com/basefoundry/base-cli/blob/main/docs/security-threat-model.md)
  with assets, boundaries, controls, residual risks, secure defaults, and
  consumer responsibilities.
- `base-cli` publishes [adoption and compatibility evidence](https://github.com/basefoundry/base-cli/blob/main/docs/adoption-evidence.md)
  that currently distinguishes reference fixtures from independently confirmed
  adopters and keeps the public adopter target permissioned.
- `base-bash-libs` publishes a [threat model](https://github.com/basefoundry/base-bash-libs/blob/main/docs/threat-model.md),
  an intentionally empty [public consumer register](https://github.com/basefoundry/base-bash-libs/blob/main/docs/who-uses-base-bash.md),
  and a [single-file distribution contract](https://github.com/basefoundry/base-bash-libs/blob/main/docs/single-file-distribution.md)
  covering deterministic bundles, content hashes, SBOMs, and provenance.
- Base's [contract registry](contracts.md) maps selected public promises to
  their source documents and executable enforcement checks, making documentation
  drift a reportable failure rather than an editorial preference.

Together these documents make the self-critique inspectable. They do not turn a
maintainer's assessment into an independent audit.

## Claims this practice refuses to make

The following distinctions are part of the public contract:

- A green test suite means the tested behavior passed for that revision and
  environment. It is not proof of production safety or external adoption.
- A maintained consumer fixture proves that a known shape is exercised. It is
  not a customer, deployment, revenue signal, or independent outcome.
- A checksum, SBOM, or attestation helps verify what was built or published.
  It does not prove that the reviewed code is vulnerability-free.
- A threat model records boundaries and mitigations. It is not a sandbox and
  cannot remove the authority of the caller, shell, operating system, plugin,
  dependency, or external service.
- A product rating is a documented judgment with stated evidence and limits.
  It is not a survey, analyst report, or market-size estimate.
- A public engineering note can explain the work without publishing private
  adopter identities, credentials, support conversations, or unapproved case
  studies.

These limits are not disclaimers added after the fact. They define what each
evidence type is allowed to mean.

## A reusable public-review template

Other maintainers can adapt the same structure without copying Base's product
claims:

```markdown
# [Project] engineering review

## Product thesis and non-goals

## Current implementation evidence

## Assets and trust boundaries

## Controls and residual risks

## Release, checksum, SBOM, and provenance evidence

## Adoption and compatibility evidence

## Missing evidence and next issue-backed actions
```

Each section should link to a concrete source and include a date or revision
when the claim can drift. If evidence is unavailable, say so plainly. If a
result requires permission, keep the record private until that permission is
explicit and keep the public wording within the approved scope.

## Maintaining the note

This page should change when the review practice changes, not every time a
project receives an ordinary patch. The dated product assessment, threat
models, release documents, adoption records, and contract registry remain the
canonical evidence surfaces. The public note explains how to read them and how
to avoid overstating what they prove.

For Base's current product-specific conclusions, start with the [Product
Assessment](product-assessment.md). For a first-run description of Base itself,
start with [Why Base](why-base.md).
