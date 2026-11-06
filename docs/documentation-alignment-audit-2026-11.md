# Documentation Alignment Audit (November 2026)

This is an evidence-backed crosswalk of the remaining candidate gaps raised in
Claude's documentation review and their related follow-up work. It is a dated
audit record, not a new product contract or an exhaustive line-by-line audit of
every Base source file.

**Source snapshot:** repository `main` at
`d676e258e9b227e5dfe5806b430e0b502cf304c0` (commit date 2026-11-02).
**Issue/PR state:** checked 2026-11-05; linked tracker state may move after
that date.

The review compared the candidate claims with the architecture and focused
design documents, implementation paths, the current `basectl --help` output,
command/runtime references, newcomer surfaces, release notes, and AI context.
Candidate gaps were checked against the live issue tracker. No overall drift
percentage is reported: the candidate set is not a measured inventory of every
code and documentation contract.

## Crosswalk

| Candidate | Implementation and documentation evidence | Finding and disposition |
| --- | --- | --- |
| Architecture coverage for `trust`, `gh`, and `repo`; launcher path | [Architecture](architecture.md#command-surface--basectl-as-control-plane) describes the product responsibility tiers, shows selected commands, and links the maintained [execution model](execution-model.md). Detailed domain contracts already exist in [manifest command trust](manifest-command-trust.md), [GitHub workflow](github-workflow.md), and [repository baseline](repo-baseline.md). The execution model describes public dispatch and Python-to-Bash command metadata; [architecture](architecture.md#L500-L505) mentions `bin/base-wrapper` for project-scoped Python packages, but the launcher path and its place in command-domain ownership are not mapped together. No dedicated contract test for this ownership map was found. | **Confirmed cohesion gap, P2.** The detailed contracts exist, but the top-level references do not provide one short ownership map across these command domains or connect the Python launcher path to dispatch. Follow-up: [#2651](https://github.com/basefoundry/base/issues/2651). |
| Release manifest keys | [`manifest_release.py`](../cli/python/base_setup/manifest_release.py#L24-L52) accepts `version_file`, `changelog`, `tag_prefix`, `github`, `bom`, `homebrew`, and `runner`; nested keys include `github.repository`, `github.release_title`, `bom.required`, and Homebrew `required`, `tap_repository`, `formula_path`, and `package`. Defaults include `VERSION`, `CHANGELOG.md`, `v`, `{repository} v{version}`, `bom.required: false`, and `homebrew.required: true` when that section exists. [Release Process](release-process.md#release-assistant) describes these fields by category and explains selected behavior, but it does not give a complete accepted-key/default reference. Parser coverage exists in [`base_setup/tests/test_manifest.py`](../cli/python/base_setup/tests/test_manifest.py) and release readiness tests. | **Confirmed key-level documentation gap, P2.** Link the key inventory and defaults to the existing [manifest JSON Schema issue #1613](https://github.com/basefoundry/base/issues/1613); do not create a duplicate schema issue. Check that the eventual schema and manifest guide together expose this contract. |
| Environment-variable inventory, estimated at about 55 undocumented names | [Runtime Environment](runtime-environment.md) identifies itself as the canonical runtime contract and explicitly excludes `BASE_TEST_*`, private `_BASE_*`, and unexported locals. It contains 54 named-variable rows and 53 distinct names (including `CI`; `BASE_CACHE_DIR` appears twice). Production-source review found several distinct classes: runtime variables; user-facing knobs already documented in specialized guidance, including installer pins in [Remote Installer Policy](remote-installer-policy.md#managed-workstations-and-pinned-installers); command handoffs that mirror CLI flags such as `BASE_SETUP_REMOTE_NETWORK` and `BASE_SETUP_VERIFY_PROJECT_RUNTIME`; internal history/provider metadata; and test/CI hooks. The [setup implementation](../cli/bash/commands/basectl/subcommands/setup_macos_homebrew.sh#L21-L42) also reads `BASE_SETUP_ALLOW_SYSTEM_PYTHON` and `BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL`, and tests cover both in [`setup.bats`](../cli/bash/commands/basectl/tests/setup.bats#L700-L710) and [system-Python fallback](../cli/bash/commands/basectl/tests/setup.bats#L860-L880). [`base_init.bats`](../tests/base_init.bats#L405-L424) checks that core runtime exports appear in the environment table, but it is not a complete source-to-doc check for command overrides. Their names and implications are absent from user-facing docs. | **The blanket count is unverified; a narrow safety-sensitive documentation gap is confirmed, P2.** The runtime table has 54 rows/53 unique names, but that count is not a denominator for undocumented code variables. These two setup values can affect system-Python selection and non-interactive Xcode installation. [#2654](https://github.com/basefoundry/base/issues/2654) will classify them and nearby Xcode path/wait overrides, keeping CLI-forwarded and test/internal values out unless they are supported user inputs. |
| Base Bash-libs 2.1.0 minimum | [Runtime Environment](runtime-environment.md#base-runtime-contract) states that Base requires the v2.1 `base_` API and applies the 2.1.0 floor. [Base Bash Libraries](base-bash-libs.md) records the same coordinated minimum. [`base_init.bats`](../tests/base_init.bats#L120-L160) exercises accepted and rejected library versions. | **Already documented; candidate is a false positive.** No follow-up needed. |
| Command reference coverage | The current [Command Quick Reference](command-reference.md) lists `grpcurl` in its tool profile and includes `basectl uninstall`; the executed `basectl --help` was checked as the current public command map. Existing [#2427](https://github.com/basefoundry/base/issues/2427) covered shipped flag reference coverage and is closed. `tests/test_command_reference_flags.py`, `tests/test_stability_tiers_docs.py`, and `tests/stability_compatibility.py` exercise command/flag coverage. | **No broad command-reference omission confirmed in this pass.** This is a spot check of the cited surface, not a fresh exhaustive leaf-flag audit; keep that distinction from user-facing overview omissions below. |
| SRE package and uninstall discoverability | The shipped SRE profile in `lib/base/sre_manifest.yaml` and `lib/base/artifact-registry.yaml` includes `grpcurl`. The [technical overview](technical-overview.md#ci) omits it from the SRE row and omits uninstall from its selected key-command tables. The top-level [README](../README.md) and [FAQ](../FAQ.md) do not link to uninstall guidance. [PR #2629](https://github.com/basefoundry/base/pull/2629) is open and introduces the focused uninstall guide; its landing path should be used after merge. Uninstall's command-reference behavior is covered by `tests/test_stability_tiers_docs.py` and `tests/test_command_reference_flags.py`; no overview/front-door coverage check was found. | **Confirmed overview/front-door gaps, P2.** Track the `grpcurl` correction and concise uninstall links in [#2652](https://github.com/basefoundry/base/issues/2652), dependent on #2629 for the canonical guide. The approved uninstall contract is that project run bundles are removed while Base-level run history is retained. |
| Uninstall retention claim in #2595 | The current body of [#2595](https://github.com/basefoundry/base/issues/2595) now says uninstall removes project run bundles while retaining Base-level run history, consistent with the approved behavior. | **Corrected in the issue tracker.** This statement is no longer the claimed future behavior “uninstall leaves no residue.” |
| AI status and current-release line | `VERSION`, [Release Process](release-process.md), and the [published v1.10.5 release](https://github.com/basefoundry/base/releases/tag/v1.10.5) identify 1.10.5 as the current published release. `.ai-context/STATUS.md` still says the 1.10.5 release line is active and points to [#2539](https://github.com/basefoundry/base/issues/2539), which is closed. No status freshness check was found. | **Confirmed stale status paragraph, P2.** Correct it in [#2653](https://github.com/basefoundry/base/issues/2653); retain the accurate current-version statement. |
| Changelog coverage for merged PRs after 1.10.5 | The changelog's Unreleased section does not clearly identify #2615 (AI context exports default to Base cache), #2617 (issue status sync when work starts), or #2621 (stale worktree metadata handling during prune). The published 1.10.5 entry already describes cross-surface release-version consistency and draft-first publication recovery, covering the #2550/#2552/#2554 release-recovery work cited in the review. `tests/stability_compatibility.py` checks required migration-note markers for compatibility changes, but no general change-to-changelog completeness test was found. | **Needs focused changelog disposition, P2.** [#2653](https://github.com/basefoundry/base/issues/2653) will check each post-release change against the repository's user-facing release-note convention and add only eligible entries. Do not duplicate the already-published 1.10.5 recovery note. |
| Other docs/code candidates from the active review trains | [#2629](https://github.com/basefoundry/base/pull/2629) and [#2630](https://github.com/basefoundry/base/pull/2630) remain open and are being reviewed by Claude. [#2649](https://github.com/basefoundry/base/issues/2649) separately tracks cleanup of Base-local `lib/python` paths. | These are in-flight issue/PR trains and are not counted as completed fixes in this snapshot. Keep the CI path cleanup separate from the docs crosswalk. |

## Environment-variable classification notes

The production-source review separates variable names by how Base uses them;
matching a `BASE_*` token in source is not enough to call it a supported user
setting:

- The documented runtime contract has 54 named rows and 53 distinct names.
  `BASE_TEST_*`, `_BASE_*`, and unexported locals are explicitly excluded.
- Installer pin inputs such as `BASE_HOMEBREW_INSTALLER_URL` and
  `BASE_SETUP_UV_INSTALLER_URL` are documented in the focused
  [Remote Installer Policy](remote-installer-policy.md).
- Values such as `BASE_SETUP_REMOTE_NETWORK`,
  `BASE_SETUP_VERIFY_PROJECT_RUNTIME`, and
  `BASE_SETUP_ALLOW_PROJECT_IDE_MUTATIONS` carry explicit CLI options into
  setup/check operations. Their public surfaces are the documented flags; the
  environment values are internal forwarding state.
- `BASE_CLI_RUN_ROOT`, `BASE_CLI_HISTORY_*`, and provider metadata are exported
  by Base for internal history and Python-provider coordination. They are not
  user configuration knobs.
- `BASE_SETUP_TEST_*` values are test hooks, while workflow credentials such
  as `BASE_PROJECT_TOKEN` belong to CI/Project operations rather than the shell
  runtime contract.
- `BASE_SETUP_ALLOW_SYSTEM_PYTHON` and
  `BASE_SETUP_ALLOW_NONINTERACTIVE_XCODE_INSTALL` are read by setup as inputs
  that can change host-level behavior. The Xcode tools path and wait-duration
  overrides are also candidates. Their support status and precise guidance are
  tracked in [#2654](https://github.com/basefoundry/base/issues/2654).

## Review boundaries

- The crosswalk records each candidate as confirmed, already documented, not
  reproduced, or still requiring classification, and links it to its evidence,
  known enforcement, and existing/focused issue. Priority is assigned only to
  confirmed work that needs an issue; already-correct and unverified candidates
  are not given invented priority scores.
- Release manifest-key coverage belongs with #1613's schema and manifest
  documentation deliverable. The stale #2595 wording was corrected in that
  issue; other document edits remain in their own issue/PR trains. The targeted
  setup-variable classification is tracked in #2654, rather than adopting the
  unverified 55-name estimate.
- The [Base Contracts](contracts.md) registry remains the maintained map for
  behavior promises and enforcement. The prevention-policy follow-up is tracked
  separately in [issue #2631](https://github.com/basefoundry/base/issues/2631)
  and [PR #2632](https://github.com/basefoundry/base/pull/2632); this audit does
  not duplicate that strategy work.
- No manual “Last reviewed” stamps were added. The snapshot date identifies the
  evidence boundary for this report; it is not a recurring freshness mechanism.
- FAQ heading capitalization was left out because it is optional style cleanup.
