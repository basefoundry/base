# basectl setup parallelism

`basectl setup` is slower than `basectl check`, but it also mutates shared
machine and project state. The setup path should optimize only where Base can
keep idempotency, deterministic dry-run output, useful logs, and clear recovery
semantics.

This document records the first setup-parallelism evaluation. It deliberately
compares setup with [`basectl check` parallelism](check-parallelism.md), because
read-only probes and mutating installers have different risk profiles.

## Decision

Do not parallelize mutating setup work broadly yet.

The current setup implementation should remain serial for installs and writes
that share package managers, virtual environments, IDE state, shell startup
files, user config files, or terminal progress output. Broad background setup
would make failures harder to diagnose, make dry-run output less predictable,
and risk concurrent writes through tools that already own their own locking and
progress behavior.

Setup parallelism is still worth revisiting, but the first shippable slice
should be a deterministic setup plan and preflight layer, not concurrent
install execution. That slice should identify independent work, print the same
ordered plan in dry-run mode, and record timing so Base can prove where parallel
execution would actually help.

## Current Setup Shape

The Base setup command currently runs in ordered phases:

1. First-mile Base prerequisites:
   - require macOS, except for CI runtime-only setup;
   - install or find Homebrew;
   - install Xcode Command Line Tools;
   - install the configured Homebrew Python formula;
   - create or recreate the Base virtual environment;
   - install Base bootstrap Python packages.
2. Optional prerequisite profiles:
   - delegate to the Python `base_dev` layer for profiles such as `dev`, `sre`,
     and `ai`.
3. Project setup:
   - seed project bootstrap artifacts when a project uses the Base-managed venv;
   - delegate to the Python `base_setup` layer through the selected project
     environment;
   - reconcile `brewfile`, `mise`, IDE app installs, IDE extensions, IDE
     settings, uv-managed projects, and Base-managed artifacts;
   - batch Python package artifacts into one pip command where possible.
4. User-local Base config seeding.

The slowest likely operations are external tools: Homebrew installs and
upgrades, Xcode Command Line Tools installation, `brew bundle`, `mise install`,
IDE cask and extension installs, `uv sync`, and pip installs. These are also
the operations with the strongest shared-resource and progress-output concerns.

## Resource Boundaries

Treat these resources as exclusive until Base has stronger evidence and
tool-specific contracts:

- `homebrew`: `brew install`, `brew upgrade`, `brew bundle`, cask installs, and
  Homebrew-backed IDE installs should not run concurrently with each other.
- `xcode-command-line-tools`: the interactive installer and wait loop should
  remain single-owner.
- `base-venv`: Base virtualenv creation and Base bootstrap pip installs are an
  ordered chain.
- `project-venv:<project>`: project venv recreation, creation, and pip installs
  should stay ordered; Python artifacts are already batched into one pip
  invocation where possible.
- `project-manager:<project>`: `mise install` and `uv sync` own project-specific
  environment state and should remain visible as direct external commands.
- `ide:<name>`: IDE extension setup depends on the IDE app and CLI being
  present; extension installs should remain ordered per IDE until tested
  against real CLI behavior.
- `user-config`: writes to `~/.base.d/config.yaml`, IDE settings, and shell
  startup files should remain explicit foreground writes.
- `terminal-output`: long-running installers keep stdout attached so users can
  see progress; backgrounding them would require a tee-style transcript model
  before it is user-friendly.

## Candidate Work

Good near-term candidates are read-only or planning work:

- build a setup plan from the manifest and user config;
- resolve which phase owns each action and resource;
- check command presence and existing state before mutation;
- record per-step timing for serial setup;
- render dry-run output from the plan in deterministic order;
- expose enough plan metadata for future tests to assert ordering and resource
  exclusivity.

Poor first candidates are mutating installers:

- running multiple Homebrew commands at once;
- running Homebrew while `mise`, `uv`, or pip is also installing dependencies;
- creating or recreating a venv while another task may inspect or use it;
- installing IDE extensions before app and CLI availability are known;
- writing IDE settings or Base user config in background jobs.

## First Implementation Slice

If setup parallelism is picked up for implementation, start with a serial setup
plan rather than concurrent execution.

The first slice should:

1. Model project setup work as ordered plan actions with fields such as
   `phase`, `resource`, `description`, `dry_run_command`, and `mutates`.
2. Preserve current text output and command behavior while allowing tests to
   inspect the plan.
3. Keep all mutating actions serial.
4. Add timing around each action in the persistent log or local history once
   the command-history surface exists.
5. Mark only read-only plan/preflight actions as candidates for future
   concurrency.

The first parallelizable classes, after the plan exists, should be limited to
read-only setup preflight checks:

- command availability checks;
- manifest and user-config resolution;
- existing-state checks that do not invoke mutating package-manager commands;
- dry-run plan construction.

Mutating installs should not run concurrently until a later design names the
exact tool, resource lock, cancellation behavior, output transcript behavior,
and failure aggregation contract.

## Output, Failure, And Cancellation Rules

Any future concurrent setup runner must keep these contracts:

- Dry-run output remains deterministic and follows the setup plan order.
- User-facing text output remains grouped by action, not interleaved by
  background job completion.
- Persistent logs include start time, end time, exit status, and underlying
  command for each action.
- A failed action prevents dependent actions from starting.
- Independent background preflight failures are collected and rendered in plan
  order.
- Cancellation should terminate outstanding child processes and return the
  primary failing or interrupted status.
- Setup should not hide the underlying external command or its stderr.

## Revisit Criteria

Reconsider mutating setup parallelism only after Base has:

- per-action setup timing that shows a meaningful bottleneck;
- a plan model that can express dependencies and exclusive resources;
- tests for deterministic dry-run text and JSON or structured output;
- a transcript model for long-running commands that keeps progress visible; and
- at least one real project where serial setup time is a recurring pain.
