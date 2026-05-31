# Base-managed demo project

Base needs a real project that demonstrates the complete daily workflow without
requiring a reader to infer how the pieces fit together. The demo should be a
normal repository checked out next to Base, not synthetic fixtures inside the
Base repo.

## Candidate

Use Banyanlabs when it is ready to be public enough for documentation. Until
then, keep the demo plan project-neutral and avoid hard-coding private
repository assumptions into Base.

## Demo Goals

The demo project should prove these commands end to end:

```bash
basectl projects list
basectl setup <project>
basectl check <project>
basectl doctor <project>
basectl activate <project>
```

The same demo should include `basectl test <project>` once it declares a
manifest `test.command`.

## Project Requirements

The demo project should include:

- `base_manifest.yaml` with `schema_version: 1` and the real project name.
- a `Brewfile` if it needs Homebrew tools.
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
8. Run `basectl activate <project>` and land in a project shell with the
   expected prompt and environment.

## Documentation Placement

Once the real project is selected, link it from:

- Base's top-level README
- the demo project's README
- `docs/README.md`

The Base README should show the demo as proof of the workflow, not as a second
installation path.
