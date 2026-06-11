# Base Project Context

## Identity

- Name: Base
- Repository: `github.com/codeforester/base`
- Current release: `0.4.2`
- Primary platform: macOS
- Future platform direction: Linux support is a design target; Windows is not
  currently in scope.

Base is a workspace control plane for developers who keep multiple repositories
checked out side by side. It provides a shared layer for setup, diagnostics,
project discovery, shell activation, project commands, test execution, release
readiness, and repository workflow without turning the workspace into a
monorepo.

## Why It Exists

Real engineering work often spans several peer repositories: one repo for shared
tooling, one or more product repos, demo repos, and local support repos. Base
gives that workspace one consistent interface while keeping each project repo
independent and responsible for its own product logic.

The short version: Base is the repo you check out once per workspace so that
the other repos in that workspace become easier to set up, easier to test, and
easier to run in a controlled shell environment.

## Product Loop

Base's coherent loop is:

```text
discover -> setup -> activate -> run -> test -> doctor -> fix -> onboard
```

Major features should strengthen that loop at the project or workspace level.
Unrelated commands belong outside Base core unless real use proves they need
Base's orchestration model.

## Current Shape

Base exposes `basectl` as the public control-plane command. `basectl` dispatches
to Bash command modules and delegates structured project logic to Python through
`base-wrapper`.

Participating projects declare `base_manifest.yaml`. Base discovers projects
under a shared workspace root, reads manifests, and orchestrates setup, checks,
activation, declared test commands, build targets, run commands, demos, and
workspace reports.

## Peer Projects

- `banyanlabs` - a realistic platform engineering learning environment that
  uses Base-managed setup and validation.
- `base-demo` - reference demo project for proving Base-managed workflows.
- `base-platform-tools` - optional sibling utilities repository. Base can add
  its `bin/` directory to PATH when present, but it is not required.
