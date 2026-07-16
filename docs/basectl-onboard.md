# `basectl onboard`

`basectl onboard` is the guided setup experience for Base itself and for
Base-managed project setup primitives.

It helps technically-adjacent users through the first Base setup without
turning `basectl setup` into an interactive, hand-holding command. The setup
command remains the direct, scriptable reconciler. The onboard command is
slower, friendlier, and more explanatory because that is its purpose.

## What It Does

`basectl onboard` runs a checklist-style first-run flow around existing Base
commands:

1. runs `basectl check [project]`
2. prompts before running `basectl setup [project]`
3. prompts before running `basectl update-profile`, unless profile updates are
   disabled
4. runs `basectl doctor [project]`
5. lists discovered projects with `basectl projects list`
6. reports trust status for discovered manifests with executable command
   surfaces, without approving them
7. suggests the next interactive shell step after any required trust review

It keeps underlying command output visible and shows each Base command before it
runs it. Use it when you want a guided first setup. Use `basectl setup` directly
when you want the scriptable reconciler.

## Usage

```bash
basectl onboard [project] [options]
```

Options:

```text
  --profile <list> Include named prerequisite profiles.
  --dry-run        Explain and show planned actions without making changes.
  --yes            Accept setup/profile prompts; never approve manifest trust.
  --no-profile     Skip shell profile updates.
  -v               Enable DEBUG logging for underlying commands.
  -h, --help       Show help text.
```

The command defaults to the `base` project. Passing a project name threads that
project through `check`, `setup`, and `doctor`. Product-specific guided
onboarding remains a project installer responsibility.

## Scope Boundary

`basectl onboard [project]` is not a product-specific guided installer. It can
target Base's generic project setup/check/doctor flow, but product onboarding
belongs in the project repository, where the installer can speak in that
product's language, clone or update that product's repo, explain
product-specific prerequisites, and call Base for the workspace mechanics it
owns.

The stable split is:

- `basectl onboard [project]` guides first-run Base setup and optional
  Base-managed project reconciliation.
- `basectl setup <project>` reconciles a Base-managed project from its manifest.
- `<project>/install.sh` or a packaged project installer guides product-specific
  onboarding and calls Base internally.

Workspace or team onboarding starts from a workspace manifest, not from
project-specific product logic inside Base. The shipped
`basectl workspace onboarding` command provides a read-only summary of expected
repositories, local checkout and manifest state, and suggested next actions in
text or JSON. It does not clone repositories, run project setup, or execute
manifest-declared commands, so clone policy, explicit command trust, and
partial-failure handling remain separate concerns. See
[Workspace Manifest](workspace-manifest.md).

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

- `basectl check [project]` for quick environment state
- `basectl doctor [project]` for human-readable diagnosis and suggested fixes
- `basectl setup [project]` for actual reconciliation
- `basectl setup --profile <list>` when the user opts into Base prerequisite
  profiles
- `basectl update-profile` for shell startup integration
- `basectl projects list` to show discovered projects after setup
- `basectl trust status` to show digest-bound command trust for discovered
  projects without granting approval
- `basectl activate <project>` as the final suggested next step

It does not duplicate Homebrew, Python, venv, manifest, or shell-profile logic.
Those responsibilities already belong to the setup/check/profile commands.

## Command Shape

Command shape:

```bash
basectl onboard [project] [options]
```

Options:

```text
  --profile <list> Include named prerequisite profiles.
  --dry-run        Explain and show planned actions without making changes.
  --yes            Accept default answers for non-destructive prompts.
  --no-profile     Skip shell profile updates.
  -v               Enable DEBUG logging for underlying commands.
  -h, --help       Show help text.
```

The command defaults to the `base` project. Passing a project name targets the
Base-managed project checks and setup steps without making Base responsible for
product-specific onboarding.

## Experience Flow

The shipped flow is simple and checklist-oriented:

1. Print a short explanation of what Base is about to verify.
2. Run `basectl check`.
3. If checks fail, explain that setup can reconcile the missing pieces.
4. Ask for confirmation before running `basectl setup`.
5. If `--profile` was requested, include those prerequisite profiles in setup.
6. Ask for confirmation before running `basectl update-profile`, unless
   `--no-profile` was set.
7. Run `basectl doctor` to summarize the final state.
8. Print discovered projects with `basectl projects list` when available.
9. Run the read-only `basectl trust status` workspace view, which filters out
   manifests without executable command surfaces and prints exact review and
   digest-bound allow guidance for those that need it.
10. Suggest `basectl` or `basectl activate base` after any required trust
    review.

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
  safety checks such as unsupported operating systems or grant manifest
  command trust. It is forwarded to setup so package-manager consent does not
  unexpectedly remain interactive on Ubuntu/Debian.
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

Tests should cover:

- help text
- dry-run flow
- declined setup prompt
- accepted setup prompt
- `--yes` non-interactive flow
- `--profile <list>` passing through to setup and doctor
- `--no-profile` skipping profile updates
- setup failure stopping later steps
