# Ecosystem release BOM

Base owns the cross-repository compatibility BOM contract. Repository-local
release policies remain authoritative for their own versioning, artifacts, and
publication, while the BOM records the exact combination that was tested.

For the Base 1.9.0 release train, `basefoundry/base` is the release owner. A
component release is independent: publishing `base-cli` or `base-bash-libs`
does not automatically require a new Base release. Base 1.9.0 may consume an
already-published compatible component release, or retain the previous
compatible pin. If Base adopts a newer component, the Base release BOM must
record that exact immutable tag and commit and the required compatibility
checks must pass. Once published, the BOM is immutable release provenance; a
later component release belongs in a later Base release BOM.

The contract is versioned at
[`docs/schemas/release-bom.schema.json`](schemas/release-bom.schema.json). A
release BOM contains:

- the releasing repository, SemVer version, immutable tag, and full commit;
- one row per participating repository with its API/schema contract, supported
  platforms, source mode, required/advisory status, result, and evidence; and
- one or more provider/consumer combinations with the platform, required flag,
  result, and reproducible evidence.

Required rows must use an immutable release or tag source, report `passed`, and
include evidence. Moving-source rows are allowed only as advisory rows and do
not block a release. The validator also rejects duplicate repositories, missing
participants, a release repository absent from the component list or required
combinations, single-repository combinations, mutable release identities, and
version or commit mismatches. Repository identity comparisons are
case-insensitive, while repository values must still use the schema's owner/name
form without `.` or `..` path segments, and commit values must be lowercase full
SHAs. All versions follow [SemVer 2.0.0](https://semver.org/), including the rule
against leading zeros in numeric version and prerelease identifiers. Released
and tagged rows retain Base's stable `vX.Y.Z` tag contract, and each tag must
match that row's version. Advisory moving rows can use valid SemVer prerelease
and build suffixes and omit the tag.

The release repository's component commit must equal `release.commit`.
Every combination's platform must appear in **every participant's** component
`platforms` array, including advisory combinations. Platform names match exactly;
repository identities match without case sensitivity. Schema patterns describe
the lexical rules; `validate_bom` also enforces these cross-field relationships.
Run the validator even when a document passes JSON Schema validation.
The BOM is not a local dependency resolver. In a source-development checkout,
Base still resolves providers in this order: explicit
`BASE_BASH_LIBS_DIR`/`BASE_CLI_SOURCE_DIR`, sibling `base-bash-libs` and
`base-cli` checkouts, then installed providers. Thus, a developer with all four
repositories checked out can intentionally run newer moving code than the
published BOM. That mode is useful for development but is not release evidence;
use the exact component tags or packages to reproduce a supported release.

Validate and fingerprint a BOM locally:

```bash
bin/base-release-bom validate path/to/release-bom.json \
  --repository basefoundry/base \
  --version 1.9.0 \
  --commit <reviewed-full-sha>
bin/base-release-bom digest path/to/release-bom.json
```

For Base 1.9.0, the release coordinator assembles rows for Base, base-cli,
base-bash-libs, and base-demo. The required release-stack combinations are
tested on Ubuntu 24.04 and macOS 14; both must report `passed`. Each combination
is a JSON object. Assembly writes canonical deterministic bytes and a matching
digest sidecar, so the sidecar can be verified directly with `sha256sum` and
the printed digest matches the attached BOM artifact:

```bash
bin/base-release-bom assemble \
  --repository basefoundry/base --version 1.9.0 \
  --commit <reviewed-full-sha> \
  --component /private/tmp/base-row.json \
  --component /private/tmp/base-cli-row.json \
  --component /private/tmp/base-bash-libs-row.json \
  --component /private/tmp/base-demo-row.json \
  --combination '{"name":"base-1.9.0-release-stack-ubuntu-24.04","participants":["basefoundry/base","basefoundry/base-cli","basefoundry/base-bash-libs","basefoundry/base-demo"],"platform":"ubuntu-24.04","required":true,"result":"passed","evidence":"run://123"}' \
  --combination '{"name":"base-1.9.0-release-stack-macos-14","participants":["basefoundry/base","basefoundry/base-cli","basefoundry/base-bash-libs","basefoundry/base-demo"],"platform":"macos-14","required":true,"result":"passed","evidence":"run://124"}' \
  --output /private/tmp/base-ecosystem-1.9.0.json
```

The release assistant can enforce the same gate:

```bash
basectl release check --version 1.9.0 \
  --manifest base_manifest.yaml \
  --bom path/to/release-bom.json
```

`release publish` rejects a supplied BOM that is invalid or does not match the
reviewed release identity. When the manifest sets `release.bom.required: true`,
it also refuses to publish when `--bom` is missing. Manifests without that
opt-in retain the backward-compatible optional BOM behavior.
The supplied BOM must be the exact canonical artifact produced by `assemble`;
pretty-printed or hand-edited JSON is rejected so its byte digest remains bound
to the reviewed artifact. `assemble` writes a matching `*.sha256` sidecar next
to its output. When supplied, `release publish` validates and reuses that
sidecar, then uploads `release-bom.json` and `release-bom.sha256` to the
GitHub Release and verifies both assets after publication. Direct callers that
supply a canonical BOM without a sidecar retain the compatibility fallback of
having the stable publish asset generated from the BOM bytes. A BOM remains
optional for manifests without the opt-in so historical releases remain
inspectable; Base's own `base_manifest.yaml` requires this governed release
path. Generate its artifact with the `Ecosystem Release BOM` workflow and pass
the downloaded `release-bom.json` to both `release check` and `release publish`.
