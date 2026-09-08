# Ecosystem release BOM

Base owns the cross-repository compatibility BOM contract. Repository-local
release policies remain authoritative for their own versioning, artifacts, and
publication, while the BOM records the exact combination that was tested.

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
form and commit values must be lowercase full SHAs.
Repository identity comparisons are case-insensitive, while repository values
must still use the schema's owner/name form and commit values must be lowercase
full SHAs.

Validate and fingerprint a BOM locally:

```bash
bin/base-release-bom validate path/to/release-bom.json \
  --repository basefoundry/base \
  --version 1.9.0 \
  --commit <reviewed-full-sha>
bin/base-release-bom digest path/to/release-bom.json
```

The release coordinator can assemble the complete record from repository-owned
component rows and explicit combination results. Each combination is a JSON
object; required combinations must already report `passed`. Assembly writes
canonical deterministic bytes, so the printed digest matches `sha256sum` of the
attached BOM artifact:

```bash
bin/base-release-bom assemble \
  --repository basefoundry/base-bash-libs --version 2.1.0 \
  --commit <reviewed-full-sha> \
  --component /private/tmp/base-bash-libs-row.json \
  --component /private/tmp/base-row.json \
  --combination '{"name":"release-stack","participants":["basefoundry/base-bash-libs","basefoundry/base"],"platform":"ubuntu-24.04","required":true,"result":"passed","evidence":"run://123"}' \
  --output /private/tmp/base-ecosystem-2.1.0.json
```

The release assistant can enforce the same gate:

```bash
basectl release check --version 1.9.0 \
  --manifest base_manifest.yaml \
  --bom path/to/release-bom.json
```

`release publish` accepts the same `--bom` option and refuses to publish when
the BOM is missing, invalid, or does not match the reviewed release identity.
Release workflows should attach the validated BOM and the printed SHA-256 as
release evidence. A BOM is intentionally opt-in for existing manifests so
historical releases remain inspectable; a repository entering the governed
release train should pass `--bom` from its release workflow.
