# Why Base

Base exists for developers who keep multiple repositories checked out side by
side and want that workspace to behave like one coherent place to work.

Most developer-environment tools solve an important project-local problem:
install this language runtime, load these variables, enter this shell, run this
task, or manage these dotfiles. Base sits one level higher. It gives a
multi-repo workspace one shared control plane for setup, diagnostics, project
discovery, activation, tests, demos, repository baseline work, and release
support.

The goal is not to replace mature tools. The goal is to make them easier to use
consistently across a workspace.

## The Short Version

Use Base when your real development environment looks more like this:

```text
~/work/
  base/
  project-a/
  project-b/
  shared-tooling/
  reference-app/
```

and you want one predictable command surface:

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

Base is the layer that answers: "What projects are in this workspace, what do
they declare, what is ready, what is missing, and how do I run the common
workflow without relearning every repository from scratch?"

## What Base Gives You

- A macOS-first first-mile bootstrap path for getting a workstation to the point
  where `basectl setup` can take over.
- Workspace discovery for sibling repositories that opt in with
  `base_manifest.yaml`.
- A small manifest contract for setup, diagnostics, test, run, demo, build,
  activation, IDE, and release delegation.
- Human-readable and machine-readable readiness checks through `basectl check`,
  `basectl doctor`, and `basectl ci`.
- Explicit project activation that avoids hidden `cd`-driven environment
  changes.
- A shared shell and Python execution foundation for Base-aware scripts.
- Standard repository and GitHub workflow helpers for issue-backed work,
  repository baselines, Project metadata, and release support.

## Comparison Matrix

This table is intentionally feature-oriented. Many of these tools are excellent
inside their own domain; Base is useful when the missing piece is the layer that
connects those domains across several peer repositories.

| Need | Base | Adjacent tools |
|---|---|---|
| Multi-repo workspace discovery | Discovers sibling repositories under a shared workspace root when they opt in with `base_manifest.yaml`. | Most tools operate from the current project directory or a single repo-specific config. |
| One command surface across projects | Provides `basectl setup`, `check`, `doctor`, `test`, `run`, `demo`, `build`, and `activate` for participating projects. | Task runners and environment tools usually expose commands for one project at a time. |
| First-mile workstation bootstrap | Bootstraps macOS prerequisites such as Homebrew, Git, Bash, and Base before handing off to `basectl setup`. | Project environment tools generally assume the user already has the tool installed. |
| Tool version management | Delegates to project-owned tools such as `mise` instead of reimplementing version management. | `mise`, `asdf`, Nix, Devbox, and Dev Containers are stronger choices for pinning tools and runtimes. |
| Project environment isolation | Prepares Base-managed project virtualenvs where appropriate and keeps activation explicit, while delegating broader isolation when a project chooses another backend. | Devbox, Nix, and Dev Containers are stronger choices for fully isolated or reproducible project shells. |
| Directory-triggered environment loading | Avoids implicit activation on `cd`; project context changes through explicit `basectl activate`. | `direnv` and some `mise` workflows are better when automatic directory-based environment loading is the desired behavior. |
| Local services and containers | Can orchestrate project-declared checks and future Docker-backed service contracts without replacing Docker. | Docker, Docker Compose, Colima, and Dev Containers own container runtime and containerized development concerns. |
| Project tasks | Offers a consistent umbrella for test, run, demo, and build commands declared by the project. | `just`, Taskfile, `mise` tasks, Make, and language-native scripts are better for defining rich task logic inside one repo. |
| Dotfile management | Manages small marked shell-startup sections and keeps user-local Base preferences in `~/.baserc`. | `chezmoi`, dotbot, and private dotfile repos are better for broad dotfile templating, secrets, and machine-specific personalization. |
| Monorepo-style coordination | Gives sibling repos a common workflow without forcing them into one repository. | A monorepo is better when one source tree, one build graph, and tightly coupled code ownership are the actual product shape. |
| Diagnostics | Reports Base, workspace, and project readiness through check, doctor, JSON output, and stable finding IDs. | Adjacent tools usually diagnose their own domain, such as tool installs, env loading, container setup, or task execution. |
| Repository workflow | Helps standardize issue-backed branches, worktrees, PRs, repo baselines, Project metadata, and release handoffs. | General environment tools usually do not own repository governance or GitHub workflow conventions. |

## How To Decide

Base is a good fit when:

- your work spans multiple peer repositories;
- each repository should keep owning its own code, tests, services, and setup
  details;
- you want one workspace-level command surface for common operations;
- you want diagnostics that explain what is missing before a project runs;
- you prefer explicit activation over automatic shell state changes;
- you want Base to orchestrate mature tools rather than replace them.

Base is probably not the first tool you need when:

- you only work in one repository;
- you mainly need language version pinning;
- you mainly need a fully reproducible shell or containerized dev environment;
- you want automatic environment changes whenever you `cd`;
- you want a full dotfile manager;
- you want to consolidate everything into a monorepo.

## How Base Fits With Existing Tools

Base is designed to compose with the tools developers already use:

- Use [`mise`](https://mise.jdx.dev/) for project tool versions, environment
  variables, and tasks when that is the right substrate.
- Use [`direnv`](https://direnv.net/) when automatic directory-based environment
  loading is the desired local convenience.
- Use [Devbox](https://www.jetify.com/docs/devbox),
  [Nix](https://nix.dev/), or
  [Dev Containers](https://containers.dev/overview) when stronger environment
  reproducibility or containerized development is the center of the problem.
- Use [`just`](https://just.systems/man/en/), [Task](https://taskfile.dev/),
  Make, or language-native scripts for detailed task definitions inside a
  project.
- Use [`chezmoi`](https://www.chezmoi.io/) or another dotfile manager for broad
  personal configuration.
- Use Homebrew and Brewfiles for ordinary macOS packages and casks.

Base's job is to find the project, read its contract, invoke the right tool
openly, report failures in a Base-native way, and keep the workspace story
consistent.

For the deeper ecosystem boundary model, see
[Tool Boundaries](tool-boundaries.md).
