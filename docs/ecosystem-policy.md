# Base Ecosystem Platform, License, and Release Policy

This document is the canonical cross-repository policy for the Base ecosystem.
It keeps the four repositories' public descriptions aligned without making
their release schedules or support boundaries identical.

## Ownership and dependency direction

| Repository | Owns | Relationship to the ecosystem |
| --- | --- | --- |
| `base` | `basectl`, the local operating contract, and coordinated release BOMs | The release coordinator for a tested Base ecosystem combination |
| `base-cli` | The reusable Python CLI lifecycle framework | An independently released framework consumed by Base and other CLIs |
| `base-bash-libs` | Reusable Bash libraries and the `base-bash` launcher | An independently released library consumed by Base and other Bash tools |
| `base-demo` | The public reference project and representative demo | An independently released consumer and cross-repository validation fixture |

`base-cli`, `base-bash-libs`, and `base-demo` remain independently versioned.
Publishing one of them does not force a Base release. A later Base release may
adopt a component release only after its exact tag and commit have passed the
required compatibility checks and have been recorded in the Base-owned BOM.

Base resolves development providers in this order when the command path needs
them: an explicit `BASE_CLI_SOURCE_DIR` or `BASE_BASH_LIBS_DIR`, the expected
sibling checkout, and then the installed provider. A sibling or explicit source
checkout is moving development input, not release evidence. Stable ecosystem
consumption uses a published release asset or an immutable tag resolved to its
full commit.

## Platform boundaries

The coordinated Base release matrix is intentionally small and current:

| Repository or combination | Current contract | Not implied by this contract |
| --- | --- | --- |
| Base on macOS 14 | Full Base setup, diagnostics, shell integration, and project workflow are release-supported | Older macOS versions are not the tested floor |
| Base on Ubuntu 24.04 | Runtime checks, diagnostics, apt-backed prerequisites, and source-checkout validation are release-supported | Full macOS-style project setup and interactive demo parity |
| Base under WSL2 | Future platform expansion; existing Linux guidance is read-only/development guidance only | A supported native-Windows or coordinated WSL2 Base release |
| Base on native Windows | Out of scope | Git Bash, WSL2, or `base-cli` support does not make `basectl` native Windows support |
| `base-cli` alone | Its own documented framework matrix, including native Windows core and WSL2 when Python runs inside the Linux distribution | Native Windows support for Base or `basectl` |
| `base-bash-libs` alone | Bash 4.2+ on supported Unix-like environments; WSL2 follows the Linux-shell boundary | A native Windows Bash runtime contract |
| `base-demo` | Full interactive demo on macOS; Ubuntu 24.04 read-only CI validation | Full demo setup, activation, or service parity on Ubuntu, WSL2, or native Windows |

The required Base release-stack combinations are `ubuntu-24.04` and
`macos-14`. Adding WSL2, native Windows, another Linux family, or another
macOS runner requires an explicit support-matrix update and corresponding
immutable hosted evidence. Component-level support must not be presented as
support for the coordinated Base stack.

## License history

License claims are repository- and release-specific:

- Base is Apache-2.0 starting with `v1.9.0`. Earlier Base releases retain the
  license stated in their release documentation, including the earlier MIT and
  AGPL release lines.
- `base-cli` is Apache-2.0 under its current release line. Its release metadata
  and license file are authoritative for a particular version.
- `base-bash-libs` is Apache-2.0 under its current release line. Its release
  documentation is authoritative for historical release boundaries.
- `base-demo` remains MIT so the small reference project can be copied and
  adapted as a Base-managed example.

Do not infer one repository's license from another repository's license. New
generated repository baselines should use the license documented by the
owning repository and the requested release policy.

## Release and artifact immutability

Every published ecosystem release uses an annotated version tag created from a
reviewed commit. Published tags, GitHub Release assets, package versions, and
checksums are immutable. A correction after publication requires a new patch
version; maintainers do not retag a published version or replace its release
assets.

Build jobs may retry temporary CI artifacts before publication. That temporary
retry behavior does not authorize overwriting a published GitHub Release asset.
If a release already exists, the release job must fail closed and require an
explicit new version or a documented recovery procedure.

The Base release BOM is the provenance record for a coordinated combination.
It must contain the exact component versions and full commit identities, and
every required platform combination must report `passed`. A moving source
provider may be useful for development but cannot satisfy a release BOM row.

## Maintenance rule

This page is the canonical policy. The four repository READMEs and release
guides should link here and summarize their repository-specific boundary. Any
change to the coordinated platform matrix, license history, or immutability
rule must update this page, the affected repository documentation, and the
focused documentation checks in the same reviewed change.
