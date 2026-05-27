# TODO

Action items from the May 2026 Base product review.

Use this as a commit-by-commit work queue. Completed items are removed after
they are merged.

## P2 — Adoption And Expansion

- [ ] Implement future `docker-service` artifact support when a real project needs it.
  - Goal: let Base orchestrate Docker Compose services without replacing Docker,
    Docker Compose, or project-owned Compose files.
  - Starting point: `docs/tool-boundaries.md` has the intended boundary and a
    possible future manifest shape.
  - Manifest design:
    - Add a `docker-service` artifact type only after field names are finalized
      against a real project.
    - Require `compose-file` paths to be relative to the project root and to
      stay inside that root.
    - Start with one named `service` per artifact; add service groups later only
      if needed.
    - Decide whether `version` should be accepted for schema consistency or
      omitted for this artifact type.
  - Setup behavior:
    - Validate Docker CLI availability and daemon reachability.
    - Run `docker compose -f <file> pull <service>` when enabled.
    - Run `docker compose -f <file> build <service>` when enabled.
    - Keep setup idempotent and avoid starting long-lived services during setup.
  - Check/doctor behavior:
    - Report missing Docker, missing daemon, missing Compose file, and missing
      service definitions as actionable findings.
    - Give Colima-specific recovery guidance such as `colima start` when useful.
    - Surface image/service status without hiding the underlying Docker command.
  - Activate behavior:
    - Optionally start opted-in services during `basectl activate <project>`.
    - Keep startup visible in logs and make health-check failures easy to
      understand.
  - Tests:
    - Cover manifest validation, dry-run command planning, daemon-check
      failures, Compose command failures, and activate-time startup behavior.

- [ ] Package Base as a Homebrew formula or tap.
  - Goal: make Base installation feel native on macOS.
  - Expected behavior: support an install path such as `brew install codeforester/base/basectl`.

- [ ] Implement `basectl onboard`.
  - Goal: provide the guided checklist-style Base setup experience described in
    `docs/basectl-onboard.md`.
  - Expected behavior: orchestrate existing setup, check, doctor, profile, and
    project-discovery primitives without duplicating their logic.
  - Starting point: implement the v1 Bash subcommand with dry-run, prompted,
    `--yes`, `--dev`, and `--no-profile` flows.

- [ ] Add initial Linux support plan.
  - Goal: define the first supported Linux target, likely Ubuntu/Debian.
  - Expected design topics: `/etc/os-release` detection, `apt` equivalents for Homebrew-managed bootstrap dependencies, shell startup differences, and CI implications.
