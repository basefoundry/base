# Demo dependency inputs v1

Base's updater and base-demo share `.release/supported-dependencies.json`.
This is an input selection, never a claim that a compatibility test passed.
The strict, dependency-free validator is
`cli/python/base_release/dependency_inputs.py`.

```json
{
  "schema_version": 1,
  "components": {
    "base": {
      "version": "1.9.0",
      "commit": "ac8d294421e1bfc14afa8c6a2a12f1affb5268ee",
      "installer_sha256": "f0522bf20b13e2f487767324f4688f1b1ed33b1c1bc1158a404f0e428ea3e993"
    },
    "base-cli": {
      "version": "0.4.3",
      "commit": "8a93d22156ba75a99965f7c355f867acba630069"
    },
    "base-bash-libs": {
      "version": "2.1.0",
      "commit": "36fec50c446dcea8c521a1ba3e7fee2394f169c0"
    }
  }
}
```

Only these keys are accepted. Versions are stable SemVer; tags derive as
`v<version>`. Commits are full lowercase SHAs and the Base installer digest is
SHA-256. CI and consistency checks read this record. The standalone installer
retains materialized Base defaults so it does not need Python or an extra
network fetch; its three defaults must agree with this record. The project
`base-cli` requirement in `pyproject.toml` must also agree. The downstream
workflow still runs `uv lock` for a changed Python provider.

The updater checks the complete input shape and materialized defaults before
staging any writes. It updates the selected component and its materialized
values, not arbitrary version prose. Dependency changes update the prepared
BOM identity and mark every component/combination `not_tested` with a pending
reason. They never relabel historical passing evidence as proof of new inputs.
No-op retries preserve evidence and produce no diff. All contract checks finish
before any write; an I/O failure during writing still requires normal Git
recovery, not a claim of filesystem transactionality.

For older consumers without the record, the bounded legacy transformations
remain supported and tested against captured demo source at `6c050bd9`.
The fixture records its exact source commit. Versioned dependency inputs are
the forward contract coordinated with base-demo #293; Base #2256 remains the
separate credential/hosted-verification prerequisite. This code does not
provision credentials, auto-merge downstream PRs, or publish releases.
