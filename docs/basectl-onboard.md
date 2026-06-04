# `basectl onboard`

`basectl onboard` is the guided setup experience for Base itself.

It helps technically-adjacent users through the first Base setup without
turning `basectl setup` into an interactive, hand-holding command. The setup
command remains the direct, scriptable reconciler. The onboard command is
slower, friendlier, and more explanatory because that is its purpose.

## What It Does

`basectl onboard` runs a checklist-style first-run flow around existing Base
commands:

1. runs `basectl check`
2. prompts before running `basectl setup`
3. prompts before running `basectl update-profile`, unless profile updates are
   disabled
4. runs `basectl doctor`
5. lists discovered projects with `basectl projects list`
6. suggests the next interactive shell step

It keeps underlying command output visible and shows each Base command before it
runs it. Use it when you want a guided first setup. Use `basectl setup` directly
when you want the scriptable reconciler.

## Usage

```bash
basectl onboard [options]
```

Options:

```text
  --dev            Include Base developer prerequisites.
  --dry-run        Explain and show planned actions without making changes.
  --yes            Accept default answers for setup/profile prompts.
  --no-profile     Skip shell profile updates.
  -v               Enable DEBUG logging for underlying commands.
  -h, --help       Show help text.
```

The command defaults to the `base` project. Project-specific guided onboarding
remains a project installer responsibility.

## Scope Boundary

Base should not grow `basectl onboard <project>` as a product-specific guided
installer. Project onboarding belongs in the project repository, where the
installer can speak in that product's language, clone or update that product's
repo, explain product-specific prerequisites, and call Base for the workspace
mechanics it owns.

The stable split is:

- `basectl onboard` guides first-run Base setup.
- `basectl setup <project>` reconciles a Base-managed project from its manifest.
- `<project>/install.sh` or a packaged project installer guides product-specific
  onboarding and calls Base internally.

Future workspace or team onboarding should start from a workspace manifest
design, not from project-specific product logic inside Base. A future command
such as `basectl onboard <workspace>` would need an explicit manifest location,
clone policy, trust model, partial-failure model, and dry-run story before it
becomes part of the product surface. See [Workspace Manifest](workspace-manifest.md).

## Audience

`basectl onboard` is for someone who can use a terminal but does not yet know
what Base will do to their machine.

Examples:

- a DevOps learner setting up a Mac for a Base-managed project
- a new developer joining a workspace that uses Base
- a technically-adjacent user who wants confirmation before each major setup
  step

It is not the right layer for product-specific onboarding. A project such as
Banyanlabs should still own its own `install.sh` or packaged installer and call
Base internally. See [Project Installers](project-installers.md) for that
boundary.

## Relationship To Existing Commands

`basectl onboard` orchestrates existing Base primitives:

- `basectl check` for quick environment state
- `basectl doctor` for human-readable diagnosis and suggested fixes
- `basectl setup` for actual reconciliation
- `basectl setup --dev` when the user opts into Base developer prerequisites
- `basectl update-profile` for shell startup integration
- `basectl projects list` to show discovered projects after setup
- `basectl activate base` as the final suggested next step

It does not duplicate Homebrew, Python, venv, manifest, or shell-profile logic.
Those responsibilities already belong to the setup/check/profile commands.

## Experience Flow

The shipped flow is simple and checklist-oriented:

1. Print a short explanation of what Base is about to verify.
2. Run `basectl check`.
3. If checks fail, explain that setup can reconcile the missing pieces.
4. Ask for confirmation before running `basectl setup`.
5. If `--dev` was requested, include developer prerequisites in setup.
6. Ask for confirmation before running `basectl update-profile`, unless
   `--no-profile` was set.
7. Run `basectl doctor` to summarize the final state.
8. Print discovered projects with `basectl projects list` when available.
9. Suggest `basectl` or `basectl activate base` as the next interactive step.

The command shows the exact Base command before it runs it. For example:

```text
Next: basectl setup
This installs or verifies Homebrew, Xcode Command Line Tools, Base Python, and
Base-managed artifacts.
Proceed? [y/N]
```

## Prompting Rules

Prompts should be explicit but sparse:

- Prompt before operations that can install software or edit shell startup files.
- Do not prompt before read-only checks.
- Treat Enter as the conservative answer when there is risk.
- `--yes` may accept normal setup/profile prompts, but should not bypass fatal
  safety checks such as unsupported operating systems.
- `--dry-run` should not prompt for actions it will not perform.

## Output Style

The command is friendly without hiding the mechanics:

- Use plain English headings such as `Check`, `Setup`, `Shell Profile`, and
  `Next Steps`.
- Keep underlying command output visible so users can see long-running progress.
- Keep logs on stderr, following Base's existing logging convention.
- Use `basectl doctor` output for final health reporting rather than inventing a
  separate diagnosis format.

## Failure Behavior

Failures are recoverable and specific:

- If `basectl check` fails, continue to the setup prompt.
- If `basectl setup` fails, run or recommend `basectl doctor` and stop before
  profile updates.
- If `basectl update-profile` fails, leave setup success intact and explain how
  to rerun that step.
- Preserve the failing command's exit status when onboarding cannot complete.

## Non-Goals

`basectl onboard` should not:

- become a replacement for `basectl setup`
- become a product-specific installer
- clone project repositories
- manage secrets or credentials
- hide underlying command output behind a full-screen interface in v1
- introduce a dependency on a TUI framework before the simple checklist version
  proves insufficient

## Implementation Notes

The implementation is a Bash subcommand under
`cli/bash/commands/basectl/subcommands/onboard.sh`.

That keeps it close to the setup/check/profile primitives it orchestrates and
avoids adding Python dependencies for interactive prompting. If a richer UI is
needed later, the Bash command can delegate to a Python package while preserving
the same public command.
