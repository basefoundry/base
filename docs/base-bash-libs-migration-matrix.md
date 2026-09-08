# Base Bash-Libs Migration Matrix

This matrix records the behavior boundaries for the remaining Base shell
dogfooding work tracked by [#2122](https://github.com/basefoundry/base/issues/2122)
and [#2127](https://github.com/basefoundry/base/issues/2127). It is an
implementation guide, not a change to the public `basectl` contract.

## Argument parsing

`base_arg_parse` is appropriate when Base owns the complete option grammar and
can preserve the command's help, error, and positional semantics. It is not a
drop-in replacement for commands that forward unknown options or arguments to
the Python project layer.

| Caller | Current contract | Migration decision |
| --- | --- | --- |
| `devcontainer.sh` | Base owns `--workspace`, `--format`, `--write`, `-v`, and one optional project; parser failures return usage status 2. | Already migrated; retain focused parser seam tests. |
| `devenv_report.sh` | Same ownership model as `devcontainer.sh`, without `--write`. | Already migrated; retain focused parser seam tests. |
| `export_context.sh` | Base owns format, output, print, list, workspace, debug, and one optional project. | Already migrated; retain focused parser seam tests. |
| `prompt.sh` | Base owns one prompt name plus `--output` and `-v`; help is prompt-name-sensitive, and `--output` consumes the next token even when it looks like an option. | Migrated in this slice through `base_arg_parse`; normalize `--output=<value>` for the shared parser while preserving left-to-right help and legacy error handling. |
| `docs.sh` | Base owns `--show-url`; `-h`, `--help`, and `help` exit immediately, while unknown options and positionals have distinct errors. A standalone `--` is an unknown option. | Migrated in this slice through `base_arg_parse`; retain the preflight validation because the shared parser intentionally normalizes `--` and does not own the command-specific error text. |
| `update_profile.sh` | Base owns flags with mutually exclusive combinations and a command-specific usage-error format. | Candidate for a later parser slice; preserve conflict and error output. |
| `test.sh`, `build.sh`, `demo.sh`, `run.sh` | Base parses project/setup flags, then passes arguments after `--` to a declared project command. | Defer; the `--` boundary and trust/runner behavior need dedicated tests. |
| `clean.sh`, `logs.sh`, `projects.sh` | Bash recognizes only a subset of options and forwards the remaining grammar to the Python layer. | Defer; a strict shared parser would change pass-through behavior. |
| `gh*.sh`, `repo*.sh`, `setup_diagnostics_fallback.sh` | Several nested commands have subcommand-specific grammars and forwarded GitHub/tool options. | Defer; migrate one leaf command at a time with runtime help baselines. |

Every parser migration must record accepted argv forms, duplicate-option
behavior, `--` handling, status codes, stdout/stderr ownership, and help
precedence before changing code.

## Command discovery

The shared `base_std_command_path` helper resolves external commands through
`PATH` without logging or exiting. It is the correct replacement when the
caller needs a path or a quiet predicate. `base_std_assert_command_exists`
remains appropriate only where its aggregate fatal message is acceptable.

| Area | Callers | Required semantics | Decision |
| --- | --- | --- | --- |
| Setup and update path resolution | `setup_common.sh`, `setup_linux_debian.sh`, `setup_macos_homebrew.sh`, `update.sh`, `projects.sh` | Resolve an external executable, preserve explicit test hooks and platform fallback paths, and return failure quietly. | Migrate to `base_std_command_path`. |
| Custom prerequisite errors | Linux `curl`/`dpkg`, repository `gh`, GitHub helper commands | Keep the existing command-specific error text and status. | Use `base_std_command_path` as the predicate, then retain the local error. |
| Browser and GitHub readiness predicates | `docs.sh`, `gh_branch_worktree.sh`, `repo_github_settings.sh` | Preserve ordered fallback selection and cached readiness state. | Use `base_std_command_path`; keep the local selection/cache behavior. |
| Explicit non-PATH fallbacks | Homebrew absolute candidates and project-local `~/.local/bin/uv` | Preserve absolute-path fallback and project-local runner semantics. | Keep the fallback after the shared PATH lookup. |
| Tests and fixtures | BATS helpers, runtime probes, secret scanners | Test infrastructure may intentionally use `command -v` to locate a real tool or skip a test. | Out of production migration scope. |

The command-discovery slice in the implementation PR covers all production
`command -v` sites in `cli/bash/commands/basectl/subcommands`. It does not
change installer first-mile fallbacks or test fixture discovery.
