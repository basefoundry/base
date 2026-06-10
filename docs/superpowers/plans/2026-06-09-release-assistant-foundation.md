# Release Assistant Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the safe foundation for `basectl release`: typed manifest release metadata plus read-only `check`, `plan`, and `notes` commands.

**Architecture:** Extend `base_setup.manifest` with an optional `release:` section and keep release behavior in a focused `base_release` Python package. Add a thin Bash `basectl release` launcher that delegates to `base-wrapper --project base base_release`, mirroring other Python-backed subcommands. Keep publishing out of this slice.

**Tech Stack:** Bash subcommand dispatch, Python standard library, `base_cli.App`, `base_setup.manifest`, BATS, unittest.

---

### Task 1: Manifest Release Metadata

**Files:**
- Modify: `cli/python/base_setup/manifest.py`
- Modify: `cli/python/base_setup/tests/test_manifest.py`

- [ ] **Step 1: Write failing manifest tests**

Add tests that read a manifest containing:

```yaml
release:
  version_file: VERSION
  changelog: CHANGELOG.md
  tag_prefix: v
  github:
    repository: codeforester/base
    release_title: "Base v{version}"
  homebrew:
    required: true
    tap_repository: codeforester/homebrew-base
    formula_path: Formula/base.rb
    package: codeforester/base/base
```

Assert `manifest.release.github.repository == "codeforester/base"` and `manifest.release.homebrew.package == "codeforester/base/base"`. Add invalid-shape cases for non-mapping `release`, missing `github.repository`, invalid owner/name strings, absolute paths, and `homebrew.required: true` without tap fields.

- [ ] **Step 2: Verify RED**

Run:

```bash
BASE_HOME="$PWD" PYTHONPATH="$PWD/lib/python:$PWD/cli/python" python -m pytest cli/python/base_setup/tests/test_manifest.py -q
```

Expected: failures because `release` is an unsupported top-level key or `BaseManifest` has no `release` attribute.

- [ ] **Step 3: Implement manifest dataclasses and parser**

Add `ReleaseGithubConfig`, `ReleaseHomebrewConfig`, and `ReleaseConfig` dataclasses. Add `"release"` to allowed top-level keys. Implement `_read_release`, `_read_release_github`, `_read_release_homebrew`, path validation, repository identifier validation, and package validation. Add `release: ReleaseConfig | None` to `BaseManifest`.

- [ ] **Step 4: Verify GREEN**

Run the manifest tests again. Expected: all manifest tests pass.

### Task 2: Python Release Engine

**Files:**
- Create: `cli/python/base_release/__init__.py`
- Create: `cli/python/base_release/__main__.py`
- Create: `cli/python/base_release/engine.py`
- Create: `cli/python/base_release/tests/test_engine.py`

- [ ] **Step 1: Write failing engine tests**

Create tests for:

- `notes --version 1.2.3 --manifest <path>` prints the `CHANGELOG.md` section for `## [1.2.3] - ...`.
- `plan --version 1.2.3 --manifest <path>` prints the tag, GitHub repo, GitHub release title, and Homebrew handoff fields when present.
- `check --version 1.2.3 --manifest <path>` fails when `VERSION` does not match.
- `check --version 1.2.3 --manifest <path>` fails when the changelog section is missing.

- [ ] **Step 2: Verify RED**

Run:

```bash
BASE_HOME="$PWD" PYTHONPATH="$PWD/lib/python:$PWD/cli/python" python -m pytest cli/python/base_release/tests/test_engine.py -q
```

Expected: module import failure for `base_release`.

- [ ] **Step 3: Implement release engine**

Implement `base_cli.App(name="base_release")` with commands parsed as positional arguments. Support `check`, `plan`, and `notes`; require `--version`; accept `--manifest`. Read `VERSION`, extract changelog notes, build release title from `{version}`, check local worktree cleanliness with `git status --porcelain`, and check local/remote tag existence. Keep all behavior read-only.

- [ ] **Step 4: Verify GREEN**

Run the engine tests again. Expected: all release engine tests pass.

### Task 3: Bash Subcommand and Completions

**Files:**
- Modify: `cli/bash/commands/basectl/basectl.sh`
- Create: `cli/bash/commands/basectl/subcommands/release.sh`
- Create: `cli/bash/commands/basectl/tests/release.bats`
- Modify: `cli/bash/commands/basectl/tests/help.bats`
- Modify: `lib/shell/completions/basectl_completion.sh`
- Modify: `lib/shell/completions/basectl_completion.zsh`

- [ ] **Step 1: Write failing BATS tests**

Add tests that `basectl release --help` prints usage and that `basectl release plan --version 1.2.3 --manifest <manifest>` delegates to the Python release package and includes Homebrew handoff output.

- [ ] **Step 2: Verify RED**

Run:

```bash
BASE_HOME="$PWD" bats cli/bash/commands/basectl/tests/release.bats
```

Expected: command is unrecognized or subcommand module is missing.

- [ ] **Step 3: Implement Bash dispatch**

Add `release` to help, dispatch, Bash completion, and Zsh completion. Create a thin `release.sh` that forwards to `"$BASE_HOME/bin/base-wrapper" --project base base_release "$@"`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
BASE_HOME="$PWD" bats cli/bash/commands/basectl/tests/release.bats
```

Expected: release BATS tests pass.

### Task 4: Docs and Base Manifest

**Files:**
- Modify: `base_manifest.yaml`
- Modify: `README.md`
- Modify: `docs/release-process.md`

- [ ] **Step 1: Add release metadata to Base manifest**

Declare Base's release metadata with `VERSION`, `CHANGELOG.md`, `codeforester/base`, and `codeforester/homebrew-base`.

- [ ] **Step 2: Document the read-only release assistant**

Update README command list and release docs with `basectl release check`, `plan`, and `notes`. State that publishing and tap mutation are intentionally out of this first slice.

- [ ] **Step 3: Run focused docs checks**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

### Task 5: Final Verification

**Files:**
- All changed files.

- [ ] **Step 1: Run focused tests**

```bash
BASE_HOME="$PWD" PYTHONPATH="$PWD/lib/python:$PWD/cli/python" python -m pytest cli/python/base_setup/tests/test_manifest.py cli/python/base_release/tests/test_engine.py -q
BASE_HOME="$PWD" bats cli/bash/commands/basectl/tests/release.bats
```

- [ ] **Step 2: Run full validation**

```bash
env -u BASE_HOME ./bin/base-test
git diff --check
```

- [ ] **Step 3: Prepare PR**

Commit the release assistant foundation and open a PR that closes #541 and #542 and notes partial coverage for #544.
