---
marp: true
paginate: true
---

# Base Newcomer Orientation

Workspace control plane for multi-repo development

Canonical product details live in the README and focused docs. This deck is an
orientation path for GitHub readers and live walkthroughs.

---

## The Problem

Most real engineering work is not one repository.

A developer may need:

- shared tooling checked out beside project repositories
- consistent setup across machines
- project-specific tests and tasks
- diagnostics that explain what is missing
- shell activation without copying private dotfile logic into every repo

Base gives that workspace a common operating layer.

---

## What Base Is

Base is a workspace control plane.

It discovers participating repositories, reads their Base contracts, and gives
the developer one command surface for setup, diagnostics, tests, demos,
activation, release support, and CI.

It does not turn sibling repositories into a monorepo.

Read more: [Architecture](../architecture.md)

---

## What Base Owns

Base owns the cross-repo workflow surface:

- workspace discovery
- first-mile bootstrap
- Base-managed shell runtime
- project virtualenv location
- manifest parsing
- setup/check/doctor/test/run/demo command routing
- standard repo and GitHub workflow helpers
- guarded release assistant commands

Read more: [Execution Model](../execution-model.md)

---

## What Projects Still Own

Project repositories keep authority over product behavior:

- source code and services
- language-native package files
- tests and build tasks
- project installers
- demos and walkthrough scripts
- Brewfiles, mise configs, and service definitions
- repo-specific contribution rules

Base orchestrates these contracts. It does not replace them.

Read more: [Tool Boundaries](../tool-boundaries.md)

---

## First-Mile Bootstrap

Base starts before the developer has a working Base environment.

On macOS, `bootstrap.sh` handles the first mile:

```bash
curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/bootstrap.sh | bash
```

It installs or checks the prerequisites needed to hand off to `basectl setup`.
Users can choose source checkout mode or Homebrew install mode explicitly.

Read more: [First-Mile Bootstrap](../bootstrap.md)

---

## Install Choices

Source checkout mode is best for contributors and local Base development.

Homebrew mode is best for users who want Base installed as a tool outside their
project workspace.

Both modes converge on the same daily command surface:

```bash
basectl setup
basectl update-profile
basectl check
basectl doctor
```

Read more: [Clean macOS Install Validation](../macos-install-validation.md)

---

## The Daily Loop

After installation, the common workflow is:

```bash
basectl projects list
basectl setup <project>
basectl check <project>
basectl doctor <project>
basectl test <project>
basectl run <project> <command>
basectl demo <project>
basectl activate <project>
```

The goal is one predictable loop across many repositories.

---

## Project Discovery

Base scans a workspace root and finds repositories with `base_manifest.yaml`.

The workspace root usually comes from `~/.base.d/config.yaml`:

```yaml
workspace:
  root: ~/work
```

Workspace manifests can add expected repositories to the same view so teams can
distinguish missing repos from broken repos.

Read more: [Workspace Manifest](../workspace-manifest.md)

---

## The Manifest Contract

`base_manifest.yaml` is the small project contract Base reads.

```yaml
schema_version: 1

project:
  name: example

brewfile: Brewfile
mise: .mise.toml

test:
  mise: test

commands:
  dev: mise run dev
```

The manifest says what Base should orchestrate, not every product detail.

---

## Setup, Check, Doctor

The setup and diagnostic commands answer different questions.

`basectl setup <project>` prepares Base and project-declared artifacts.

`basectl check <project>` gives a concise pass/fail readiness signal.

`basectl doctor <project>` explains findings and fix commands.

Machine-readable JSON output exists where CI or tools need structured results.

Read more: [Doctor Finding IDs](../doctor-findings.md)

---

## Test, Run, Demo, Activate

Base delegates work back to the project:

- `basectl test <project>` runs the declared test contract
- `basectl run <project> <command>` runs named manifest commands
- `basectl demo <project>` runs the project-owned walkthrough script
- `basectl activate <project>` opens a project shell with the Base runtime

Projects stay responsible for what those commands actually do.

Read more: [Project Demo Workflow](../project-demo-workflow.md)

---

## Base Self-Demo And Reference Project

There are two demo layers:

- `basectl demo base -- --non-interactive` demonstrates Base itself
- `codeforester/base-demo` demonstrates a normal Base-managed project

Clone `base-demo` beside Base to inspect a small reference project:

```bash
git clone https://github.com/codeforester/base-demo.git
basectl setup base-demo
basectl demo base-demo
```

Read more: [Base-managed demo project](../base-managed-demo-project.md)

---

## CI Posture

`basectl ci` is the non-interactive CI entry point.

```bash
basectl ci setup <project> --format json
basectl ci check <project> --format json
basectl ci doctor <project> --format json
```

It sets CI-safe defaults, avoids prompts, and reuses the same manifest and
diagnostic paths as local development.

Read more: [`basectl ci`](../basectl-ci.md)

---

## Release Posture

Base releases are explicit ceremonies.

`basectl release` validates release metadata, prints the release plan, extracts
release notes, and publishes guarded GitHub release artifacts.

Homebrew tap updates remain a separate handoff after the Base tag and GitHub
Release exist. The 1.0 upgrade rehearsal records the consumer upgrade proof.

Read more: [Release Process](../release-process.md)

---

## Contributor Workflow

Base work normally follows an issue-backed PR train:

1. pick or create the GitHub issue
2. create a branch/worktree from `origin/master`
3. make the narrow change
4. run the relevant validation
5. open the PR with issue closure text and validation evidence
6. merge when checks pass and clean up the worktree

Read more: [GitHub Workflow](../github-workflow.md)

---

## Where To Go Next

Start with:

- [README](../../README.md) for product overview and first-run commands
- [Documentation Map](../README.md) for the full doc set
- [Architecture](../architecture.md) for product direction
- [Tool Boundaries](../tool-boundaries.md) for ownership boundaries
- [First-Mile Bootstrap](../bootstrap.md) for install behavior
- [Project Demo Workflow](../project-demo-workflow.md) for demos

Then clone `base-demo` beside Base and run the daily loop.
