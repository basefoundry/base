# Base-managed Demo Project

Base needs a real project that demonstrates the complete daily workflow without
requiring a reader to infer how the pieces fit together. The demo should be a
normal repository checked out next to Base, not synthetic fixtures inside the
Base repo.

## Current Reference Project

Use [`codeforester/base-demo`](https://github.com/codeforester/base-demo) as
the public reference project.

`base-demo` should be small, inspectable, and safe to run on a fresh supported
Mac. Its purpose is to show Base's project contract in a real repository, not
to become a broad sample app or a private-project stand-in.

Future domain-specific demos should be separate repositories when they need a
different setup story. For example, a Kubernetes walkthrough belongs in a
future `base-demo-kubernetes` repository rather than as a long-lived branch of
`base-demo`.

## Demo Goals

The demo project should prove these commands end to end:

```bash
basectl projects list
basectl setup <project>
basectl check <project>
basectl doctor <project>
basectl activate <project>
basectl test <project>
basectl demo <project>
```

It should also be useful as an interactive walkthrough. A new user should be
able to run the demo, inspect the repository, and understand the minimum shape
of a Base-managed project.

## Project Requirements

The demo project should include:

- `base_manifest.yaml` with `schema_version: 1` and the real project name.
- a `Brewfile` if it needs Homebrew tools.
- a `demo.script` declaration that points at an executable project-owned demo.
- a non-interactive demo path that can run in CI.
- Python artifacts only when the project actually needs a Base-managed venv.
- IDE settings or extensions only when they demonstrate a concrete workflow.
- a README section titled "Base setup" with the exact commands above.

The demo should avoid:

- private credentials
- cloud account assumptions
- long-running service dependencies
- project-specific installer logic inside Base

## Acceptance Criteria

A new developer should be able to:

1. Clone Base.
2. Run `basectl setup`.
3. Clone the demo project next to Base.
4. Run `basectl projects list` and see both repositories.
5. Run `basectl setup <project>`.
6. Run `basectl check <project>` and get a clean result.
7. Run `basectl doctor <project>` and get no error findings.
8. Run `basectl test <project>` successfully.
9. Run `basectl demo <project> -- --non-interactive` successfully.
10. Run `basectl activate <project>` and land in a project shell with the
   expected prompt and environment.

## Documentation Placement

Link the reference project from:

- Base's top-level README
- the demo project's README
- `docs/README.md`

The Base README should show the demo as proof of the workflow, not as a second
installation path.
