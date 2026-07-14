# `basectl repo` Ownership Map

Status: maintained implementation boundary map
Last reviewed: 2026-07-14

`basectl repo` has grown from local baseline generation into a mixed local and
GitHub workflow surface. This page maps the current responsibilities so future
refactors can reduce `repo.sh` safely without changing public command behavior.

## Current Responsibility Map

| Responsibility | Current public commands | Current owner | Direction |
|---|---|---|---|
| Command dispatch and usage routing | `basectl repo ...` | Bash | Keep in Bash as the thin public front-end. |
| Local path, config, and dry-run plumbing | all repo commands | Bash | Keep small shared Bash helpers until a broader repo command parser exists. |
| Local baseline file generation | `repo init`, `repo check` | Bash | Keep file writes in Bash for now; extract stable writer groups only when the file set is already well-covered by BATS. |
| Agent guidance generation | `repo agent-guidance` | Bash helper | Extracted to `repo_agent_guidance.sh`; it still uses shared repo path, write, and PR helpers from `repo.sh`. |
| Installer template generation | `repo installer-template` | Bash helper | Extracted to `repo_installer_template.sh`; it still uses shared repo path, write, and PR helpers from `repo.sh`. |
| GitHub repository settings and labels | `repo init`, `repo configure` | Bash helper | Extracted to `repo_github_settings.sh`; keep `gh` orchestration in Bash short-term and move structured payload construction behind Python only when behavior needs richer validation or reusable JSON construction. |
| Default branch protection | `repo configure` | Bash helper calling `gh api` | Extracted to `repo_github_settings.sh`; still a Python candidate if ruleset payloads grow or need deeper schema tests. |
| GitHub Project metadata | `repo init`, `repo configure` | Bash helper delegating to Python Project engine | `repo_github_settings.sh` owns wrapper handoff and messaging. Continue moving Project semantics into `base_github_projects`; Bash should only collect flags, locate repo config, and report wrapper output. |
| PR branch and generated PR creation | `repo init --pr`, `repo agent-guidance --pr`, `repo installer-template --pr` | Bash | Keep shared PR worktree and branch mechanics in Bash while Git remains the underlying tool. Extract generated PR body helpers by command as each command moves out. |
| Clone planning and `gh repo clone` handoff | `repo clone` | Bash | Keep in Bash unless clone config parsing moves into a general repo config parser. |

## Extraction Rules

- Preserve the existing `basectl repo` command surface and exit statuses.
- Prefer one command-specific extraction at a time.
- Leave shared path, Git, dry-run, logging, and PR worktree primitives in
  `repo.sh` until multiple extracted commands need a smaller common helper.
- Move structured GitHub Project behavior to Python, not to another Bash file.
- Add or keep focused BATS coverage for each extracted command before moving
  code.

## Completed Extractions

The first split moves `repo installer-template` implementation into
`cli/bash/commands/basectl/subcommands/repo_installer_template.sh`.

This is intentionally a Bash helper, not a Python rewrite. The command mostly
copies a maintained shell template, parses repo-specific flags, and optionally
uses the existing generated-PR helper path. Keeping it in Bash avoids changing
runtime behavior while proving that `repo.sh` can source command-owned helpers.

The second split moves `repo agent-guidance` generation into
`cli/bash/commands/basectl/subcommands/repo_agent_guidance.sh`. The helper owns
the generated guidance file content, command parsing, generated PR body, and
agent-guidance PR finish path while still reusing shared repo path, Git,
dry-run, logging, and PR worktree primitives from `repo.sh`.

The third split moves GitHub repository settings, labels, Base-managed default
branch protection ruleset handling, repository creation, and Project metadata
delegation into `cli/bash/commands/basectl/subcommands/repo_github_settings.sh`.
The helper still reuses shared repo formatting, `gh` readiness, path, and
project-support file helpers from `repo.sh`; this keeps `repo init` and
`repo configure` behavior unchanged while separating GitHub-side configuration
from local baseline generation.

Follow-up candidates:

- Continue reducing Project-specific logic in Bash by delegating schema and
  field behavior to the Python Project engine.
