# Copilot Cloud-Agent Guardrails

Base supports GitHub Copilot cloud-agent work as an optional hosted agent
surface. It does not require Copilot for local development, does not store
personal credentials for agents, and does not replace normal CI or human review.

## Setup Workflow

`.github/workflows/copilot-setup-steps.yml` follows GitHub's special
`copilot-setup-steps` workflow shape. Copilot cloud agent runs the job before
starting work, while GitHub Actions also runs it when the workflow file changes
so the setup can be reviewed like normal CI.

The Base workflow is intentionally small:

- checks out the repository
- installs Python development dependencies from `requirements-dev.txt`
- compiles Python sources and tests
- runs the workflow-policy and bootstrap-doc tests

It does not install Homebrew packages, clone sibling repositories, use personal
tokens, or run Base's full Bats suite. Those checks remain normal CI and review
responsibilities for the pull request.

## Hooks Decision

Base does not add `.github/hooks/*` in this slice. GitHub Copilot hooks can run
custom shell commands at agent lifecycle points, but Base does not yet have a
repository policy for which hook triggers are appropriate, how hook output
should be interpreted, or how hook failures should guide hosted agents.

Until that policy exists, the safer guardrail is the bounded setup workflow plus
the existing repository instructions in `.github/copilot-instructions.md`.

## Verification

For Copilot-created pull requests:

1. Review the draft PR like any other Base PR.
2. Check that normal CI still runs and passes.
3. Look for the `Copilot setup steps` workflow result when the setup workflow
   itself changes or when manually testing it from the Actions tab.
4. Confirm the PR body lists the focused local validation the agent ran.

If Copilot cloud-agent setup fails, the agent still starts with the environment
state available at that point. Treat setup failure as a signal to inspect the
PR more carefully, not as a merge decision by itself.
