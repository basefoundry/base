# Parallel Base Check Probes Design

Issue: #510

## Goal

Make the Base environment portion of `basectl check` faster by running
independent probes in parallel while preserving the existing deterministic text
and JSON output order.

## Scope

This change is limited to the shared Base check collector in
`cli/bash/commands/basectl/subcommands/setup_common.sh`.

The affected paths are:

- `basectl check`
- `basectl check --format json`
- `basectl doctor --format json`, because it already reuses the same collector

The text `basectl doctor` path prints findings directly through separate helper
functions. It is intentionally left out of this slice so #510 can stay focused
on high-frequency `check` behavior and avoid a broader doctor refactor.

Prerequisite profile checks and project artifact checks remain serial after the
Base environment collector has finished.

## Current Behavior

`setup_collect_base_check_results()` clears the result arrays, runs each Base
probe serially, and appends findings directly to the arrays consumed by text and
JSON renderers.

The serial order is:

1. Homebrew presence and path discovery
2. Xcode Command Line Tools
3. Homebrew Python formula
4. Base virtual environment integrity
5. PyYAML in the Base virtual environment
6. click in the Base virtual environment

The output order is good, but the probe order is slower than necessary.

## Design

Add small result-producing probe helpers that write one structured result file
per check:

```text
name=homebrew
ok=true
message=Homebrew is installed.
recovery=
debug=Resolved Homebrew binary: /opt/homebrew/bin/brew
```

The parent collector will:

1. create a temporary directory
2. start one background probe per independent Base check
3. wait for all probes to finish
4. read result files in the existing display order
5. append findings to the existing `_BASE_SETUP_CHECK_*` arrays
6. remove the temporary directory

The renderers do not change. They continue to print from the result arrays in
array order, which keeps text and JSON deterministic even though probes complete
out of order.

## Homebrew PATH Boundary

`setup_refresh_brew_path` mutates the parent shell's `PATH`, so it must not run
inside a background probe. The Homebrew probe will only discover whether a brew
binary exists and record the debug path.

After all probes complete, the parent reads the Homebrew result first. If
Homebrew exists, the parent calls `setup_refresh_brew_path` before appending the
Homebrew finding. If refresh fails:

- `basectl check` text mode keeps the existing fatal behavior when the collector
  is called with `fatal`
- JSON/doctor collector callers keep the existing warning-style result

## Probe Independence

The first implementation parallelizes only probes that can produce independent
read-only observations:

- Homebrew discovery
- Xcode Command Line Tools presence
- Homebrew Python formula presence
- Base virtual environment health
- PyYAML package presence
- click package presence

The package probes may report missing packages when the venv is absent, but
they must not emit stderr or abort the collector. This preserves the existing
behavior where a missing venv and missing packages are both reported as
findings.

## Tests

Add BATS coverage in `cli/bash/commands/basectl/tests/check.bats` that proves:

- text output remains in the current order while probes are allowed to overlap
- JSON output remains in the current order while probes are allowed to overlap
- missing Homebrew still allows the other Base findings to be reported
- missing venv/package checks still produce structured output without stderr

Use a test-only Xcode stub mode that waits for a pip-show marker. Serial probe
collection fails that scenario because Xcode runs before package checks;
parallel collection passes because package probes can create the marker while
the Xcode probe is waiting.
