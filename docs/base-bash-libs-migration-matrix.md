# Base Bash-Libs Migration Matrix

This matrix records the behavior boundaries for the Base shell dogfooding work
tracked by [#2122](https://github.com/basefoundry/base/issues/2122) and
[#2127](https://github.com/basefoundry/base/issues/2127). It is an
implementation guide, not a change to the public `basectl` contract.

## Current inventory

The inventory was reconciled with Base on 2026-09-09.

- All 15 production callers of `base_arg_parse` currently route through the
  shared helper. The rows below preserve the contract that future changes must
  protect; they do not authorize another parser rewrite.
- There are 21 direct production calls to `base_std_command_path` in the
  subcommands listed below. No production `command -v`, `type -P`, `type -p`,
  or `which` call remains in that directory.
- No production subcommand currently calls
  `base_std_assert_command_exists`. It remains available for callers that want
  its aggregate fatal error, but it is not interchangeable with a quiet path
  lookup.
- Command lookup in BATS helpers, runtime probes, and secret-scanner fixtures
  is intentional test infrastructure and is outside the production migration
  scope.

## Shared parser contract

`base_arg_parse` accepts exact flag and value-option specifications, supports
`--option=value` for value options, stops option parsing at `--`, and returns
usage status 2 for malformed or unknown options. A later occurrence of a
non-repeatable option replaces its earlier value; repeatable options must use
the repeatable output-array contract. A value supplied in space-separated form
must not be another recognized option. Callers remain responsible for their
own help precedence, positional grammar, forwarded-argument boundary, and
command-specific validation.

Every migration or parser-adjacent change must record:

- accepted space-separated and equals-separated forms;
- duplicate-option behavior and whether options may be combined;
- positional interpretation and `--` handling;
- status codes and whether usage goes to stdout or stderr;
- help precedence, including help with invalid or extra arguments;
- arguments forwarded to the Python or declared project command unchanged.

## Argument parsing matrix

| Caller | Bash-owned argv and boundary | Errors, output, and logging | Focused regression coverage | Disposition |
| --- | --- | --- | --- | --- |
| `devcontainer.sh` | Optional project positional; `-v`, `--workspace <path>`, `--format <format>`, and `--write`. No forwarded-argument boundary. | Help is immediate. Parser and positional failures print usage/error text and return 2. Formats are validated locally; normal results are delegated to the setup layer. | `cli/bash/commands/basectl/tests/devcontainer.bats` | Migrated; preserve the parser seam and workspace/project validation. |
| `devenv_report.sh` | Optional project positional; `-v`, `--workspace <path>`, and `--format <format>`. No forwarded-argument boundary. | Help is immediate. Parser, positional, format, and workspace/project failures return 2 with usage/error text; report output is delegated. | `cli/bash/commands/basectl/tests/devenv-report.bats` | Migrated; preserve the parser seam and workspace/project validation. |
| `export_context.sh` | Optional project positional; `-v`, `--workspace <path>`, `--format <markdown\|zip>`, `--output <path>`, `--print`, and `--list-files`. No forwarded-argument boundary. | Help is immediate. Invalid parser, positional, format, or project context returns 2 with usage/error text. Export content belongs to the delegated layer. | `cli/bash/commands/basectl/tests/export-context.bats` | Migrated; preserve output-mode and project-context validation. |
| `repo.sh` (`repo clone`) | Exactly one repository name positional; `--owner <owner>`, `--path <path>`, `--dry-run`, and `-v`. No forwarded-argument boundary; the top-level wrapper rejects equals-form options before delegation. | `-h`, `--help`, and `help` are immediate. Missing values, unknown options, and duplicate positionals return 2 with the existing usage/error text; duplicate values keep the last value and duplicate flags remain accepted. Clone URL/path resolution and `gh repo clone` delegation remain local. | `cli/bash/commands/basectl/tests/repo.bats` clone cases | Migrated in the #2144 leaf; preserve owner inference, destination safety, dry-run output, and GitHub delegation. |
| `repo.sh` (`repo check`) | At most one repository path positional; `--agent-guidance`, `--agent-ready`, `--release`, `--format <text\|json>`, and `-v`. No forwarded-argument boundary; the top-level wrapper rejects equals-form options before delegation. | Help remains immediate. Missing format values, unsupported formats, unknown options, and duplicate paths return 2 with the existing usage/error text; duplicate format values keep the last value and duplicate flags remain accepted. Baseline inspection, JSON envelopes, and status propagation remain local. | `cli/bash/commands/basectl/tests/repo.bats` check cases | Migrated in the #2144 leaf; preserve path resolution, format-aware usage errors, and repository inspection behavior. |
| `repo.sh` (`repo configure`) | At most one repository path positional; `--repo`, `--project`, `--project-owner`, `--project-schema`, `--initiative-option`, and `--copy-project-fields-from` take values; `--dry-run`, `--no-protect-default-branch`, `--replace-project`, `--no-project`, `--release`, and `-v` are flags. No forwarded-argument boundary; the pre-parser preserves legacy help, missing-value, unknown-option, and equals-form behavior. | Duplicate scalar values keep the last value; repeatable initiative options preserve order. Path/repository inference, dry-run mutation boundaries, GitHub settings, release support files, and Project metadata remain local. | `cli/bash/commands/basectl/tests/repo.bats` configure cases | Migrated in the #2144 leaf; preserve repository configuration safety and Project metadata handoff. |
| `repo_agent_guidance.sh` (`agent-guidance`) | At most one repository path positional; `--repo`, `--issue`, `--category`, `--repo-name`, `--default-branch`, and `--validation-command` take values; `--pr`, `--dry-run`, and `-v` are flags. No forwarded-argument boundary; the pre-parser preserves option-looking values and legacy help/error behavior before shared parsing. | Missing values, invalid issue/category/name values, and PR preconditions retain command-specific status and guidance. Duplicate scalar values keep the last value; path resolution, generated-file safety, and optional PR workflow remain local. | `cli/bash/commands/basectl/tests/repo.bats` agent-guidance cases | Migrated in the #2144 leaf; preserve generated guidance content and PR/worktree safety boundaries. |
| `repo_init.sh` (`repo init`) | Exactly one repository name positional; `--path`, `--repo`, `--issue`, `--category`, `--language`, `--description`, `--license`, `--project`, `--project-owner`, `--project-schema`, `--initiative-option`, and `--copy-project-fields-from` take values; `--pr`, `--agent-ready`, `--release`, visibility/configuration/protection flags, `--no-project`, `--dry-run`, and `-v` are flags. No forwarded-argument boundary; the pre-parser preserves legacy value/error behavior before shared parsing. | Duplicate scalar values keep the last value; repeatable language and initiative options preserve occurrence order. Language normalization, supported-language validation/deduplication, visibility conflicts, repository validation, baseline generation, and optional PR/configuration boundaries remain local. | `cli/bash/commands/basectl/tests/repo.bats` init cases | Migrated in the #2144 leaf; preserve generated baseline content, language metadata, visibility safety, and PR/worktree boundaries. |
| `gh.sh` (`issue create`) | No positionals; `--category`, `--repo`, `--title`, `--assignee`, `--body`, `--project`, `--project-owner`, and `--size` take values; `--no-assignee`, `--no-project`, and `--allow-cross-repo` are flags. No forwarded-argument boundary; the pre-parser preserves legacy help and unknown-option errors before shared parsing. | Missing values and unknown options retain the existing usage text and status 2. Duplicate values keep the last value; duplicate flags remain accepted. Category, size, repository inference, GitHub issue creation, and optional Project metadata updates remain local. | `cli/bash/commands/basectl/tests/gh.bats` issue-create cases | Migrated in the #2144 leaf; preserve issue labels, assignee defaults, cross-repository Project guard, and GitHub delegation. |
| `setup_diagnostics_fallback.sh` (`record-check`, project-venv JSON, check/doctor JSON) | Internal fallback leaves own value options for project/status/timestamps/paths, project-venv fields, and normalized repeated check/result/embedded records. No public forwarded-argument boundary. | Missing or unsupported fallback arguments remain fatal. Duplicate scalar values keep the last value; repeated records preserve their per-kind order. JSON payload, record persistence, and aggregate status remain local to the fallback. | `cli/bash/commands/basectl/tests/diagnostics-fallback.bats` | Migrated in the #2144 leaf; preserve Python-unavailable diagnostic rendering and record-write boundaries. |
| `gh.sh` (`auth status` / `auth refresh`) | `auth status` owns `--hostname <host>`. `auth refresh` owns `--hostname <host>`, repeatable `--scope <scope>`, comma-separated `--scopes <scope,...>`, and `--clipboard`; the pre-parser normalizes both scope spellings into the shared repeatable option. No forwarded-argument boundary. | Help remains command-scoped. Missing values and unknown options return 2 with the existing usage/error text; duplicate hostname values keep the last value; scope order is preserved. Unsupported equals-form options remain rejected, matching the legacy contract. GitHub CLI output and delegated status remain unchanged. | `cli/bash/commands/basectl/tests/gh.bats` auth cases | Migrated in the #2144 leaf; preserve hostname handling, scope ordering, and credential safety boundaries. |
| `gh_branch_worktree.sh` (`branch stale`) | No positionals; `--days <days>` and `--format <text\|json>`. No forwarded-argument boundary; the pre-parser preserves the legacy space-separated value forms before shared parsing. | Help is immediate. Duplicate values keep the last value. Invalid days and unsupported formats return 2; valid JSON format selection keeps usage and upstream failures inside the inspection envelope. Unsupported equals-form options remain rejected. | `cli/bash/commands/basectl/tests/gh-branch-worktree.bats` and `inspection-json.bats` | Migrated in the #2144 leaf; preserve stale-branch age validation, JSON envelope/status, and Git reference inspection boundaries. |
| `gh_branch_worktree.sh` (`branch prune`) | No positionals; `--dry-run`, `--yes`, `--remote`, and `--closed-unmerged`. No forwarded-argument boundary. | Help and unknown options remain immediate. Duplicate flags remain accepted. `--dry-run` and `--yes` remain mutually exclusive; dry-run is the default. Branch/worktree eligibility, GitHub verification, output, and deletion status remain local to the pruning layer. | `cli/bash/commands/basectl/tests/gh-branch-worktree.bats` prune cases | Migrated in the #2144 leaf; preserve default dry-run and all deletion safety boundaries. |
| `prompt.sh` | Exactly one `list` or prompt-name positional; `-v` and `--output <path>`. The legacy parser accepts an option-looking output value; the pre-parser encodes it as `--output=<value>`. No forwarded-argument boundary. | Help is prompt-sensitive and remains available before the Python environment is required. Unknown options and missing output paths return 2; rendered prompt content is delegated. | `cli/bash/commands/basectl/tests/prompt.bats` | Migrated; preserve help precedence and option-looking output paths. |
| `docs.sh` | No positionals; `--show-url`. A standalone `--` and all other options are rejected by the command-specific preflight. No forwarded-argument boundary. | `-h`, `--help`, and `help` print help and return 0. Invalid arguments return 2. `--show-url` prints the URL; browser-open failure returns 1 with a remediation message. | `cli/bash/commands/basectl/tests/docs.bats` | Migrated; preserve preflight error text and browser fallback behavior. |
| `update_profile.sh` | No positionals; `--defaults`, `--no-defaults`, `--remove`, `--dry-run`, and `-v`. | Help and unknown-option precedence is handled before shared parsing. Conflicting combinations return 2; debug uses the existing logging path; profile mutation remains local to this command. | `cli/bash/commands/basectl/tests/update-profile.bats` | Migrated; preserve duplicate compatible flags and conflict validation. |
| `test.sh` | Optional project positional; `-v`, `--workspace <path>`, `--project <name>`, and `--dry-run`; arguments after `--` are forwarded byte-for-byte to the declared test command. | Help and owned-option errors return 2 without running the project command. Dry-run output is shell-quoted; delegated command status is preserved. | `cli/bash/commands/basectl/tests/test.bats` | Migrated; preserve the explicit forwarding boundary and runner behavior. |
| `build.sh` | Project/target positionals; `-v`, `--workspace <path>`, `--project <name>`, `--dry-run`, `--list`, and `--format <text\|csv\|tsv\|yaml\|json>`; arguments after `--` are forwarded to each declared build command. | Help and owned-option errors return 2. List/dry-run/explicit-project combinations are validated locally; target and delegated-command output/status remain unchanged. | `cli/bash/commands/basectl/tests/build.bats` | Migrated; preserve target interpretation and forwarding boundary. |
| `demo.sh` | Optional project positional; `-v`, `--workspace <path>`, `--project <name>`, and `--dry-run`; arguments after `--` are forwarded to the declared demo script. | Help and owned-option errors return 2. Positional/explicit-project conflicts are local usage errors; dry-run and delegated demo status/output remain unchanged. | `cli/bash/commands/basectl/tests/demo.bats` | Migrated; preserve runner selection and forwarding boundary. |
| `run.sh` | Project/command positionals; `-v`, `--workspace <path>`, `--project <name>`, `--dry-run`, `--list`, and `--format <text\|csv\|tsv\|yaml\|json>`; arguments after `--` are forwarded to the declared command. | Help and owned-option errors return 2. List/dry-run/operand combinations are validated locally; dry-run and delegated command status/output remain unchanged. | `cli/bash/commands/basectl/tests/run.bats` | Migrated; preserve command interpretation and forwarding boundary. |
| `clean.sh` | Shell owns `-v`, `--older-than <age>`, and `--keep-last <count>`, including equals forms. `--dry-run`, `--yes`, unknown options, positionals, and `--` remain in the complete Python argv. | Help is local. Missing values, missing cleanup criteria, and shared-parser failures return 2 with usage/error text. The Python cleanup layer owns remaining validation and output. | `cli/bash/commands/basectl/tests/clean.bats` | Migrated with a filtered boundary; preserve the complete Python argv. |
| `logs.sh` | Shell owns `-v`, `--command <names>`, `--limit <count>`, `--latest`, `--tail`, `--open`, `--lines <count>`, and `--format <format>`, including equals forms. The command token `last-failed`, unknown options, and `--` remain in the Python argv. | Help is selected for the recent or `last-failed` scope before parsing. Missing values and shared-parser failures return 2; log listing, redaction, and delegated status/output remain Python-owned. | `cli/bash/commands/basectl/tests/logs.bats` | Migrated with a filtered boundary; preserve command-scoped help and the complete Python argv. |
| `projects.sh` | Bash owns only `-v` after the required `list` leaf. The `list` leaf's workspace, format, and all other arguments are forwarded to the Python layer, including `--`. | Area/leaf help is local. Unknown project commands and shared-parser failures return 2 with usage/error text. The command uses the Base venv when present and a source-checkout Python fallback before reporting setup guidance. | `cli/bash/commands/basectl/tests/projects.bats` | Migrated with a filtered boundary; preserve Python option ownership and source fallback. |
| `gh_issue_readiness.sh` | Exactly one numeric issue positional followed by `--repo <owner/name>`, `--project-owner <owner>`, `--project-number <number>`, and `--format <text\|json>`. No forwarded-argument boundary. | Help and format-aware usage errors are local. Invalid/missing values and incomplete Project selectors return 2; text/JSON output schemas and upstream GitHub failure handling remain unchanged. | `cli/bash/commands/basectl/tests/gh.bats` readiness cases | Migrated in the #2144 leaf; preserve runtime-help and option-looking-value coverage. |

The current parser rows are evidence for future changes, not a request to
reopen all parser migrations. The remaining work tracked by #2122/#2144 is
nested command parsing in other `gh*.sh`, `repo*.sh`, and setup-diagnostics
leaves. Each future leaf must establish its own runtime-help and argv baseline
before changing code.

## Command discovery matrix

`base_std_command_path <result-variable> <command>` resolves an executable
through the current `PATH` using Bash's external-command lookup semantics. It
is quiet on an ordinary miss, does not exit the caller, and returns a path for
callers that need to execute the command. It does not replace a Bash-function
check; callers that intentionally support functions must retain an explicit
`base_std_function_exists` or equivalent contract.

The 21 direct production calls fall into these contracts:

| Logical caller and exact call sites | Resolution contract | Error/status/output boundary | Platform fallback and tests | Disposition |
| --- | --- | --- | --- | --- |
| `docs.sh:34` (`base_docs_platform_opener`) | Resolve the first supported opener from `open`, `xdg-open`, or `wslview` without logging a miss. | If none is found, retain the local status-1 message directing users to `--show-url`; do not log a shared fatal error. | Ordered platform opener selection remains local. `cli/bash/commands/basectl/tests/docs.bats` covers URL-only and opener behavior. | Migrated in #2129; preserve selection order and fallback message. |
| `gh.sh:657` (`base_gh_require_command`) | Resolve the requested GitHub/tool executable quietly before use. | Keep the local installation/authentication guidance and caller status; do not replace it with the aggregate assertion message. | No absolute fallback is introduced by this helper. GitHub command behavior is covered by `cli/bash/commands/basectl/tests/gh.bats`. | Migrated in #2129; preserve custom prerequisite text. |
| `gh_branch_worktree.sh:225` | Resolve `gh` for branch/worktree readiness. | Preserve the local readiness/fallback result and status. | GitHub readiness remains separate from Git discovery and is covered by `cli/bash/commands/basectl/tests/gh.bats`. | Migrated in #2129; preserve readiness behavior. |
| `project_command_helpers.sh:190` | Resolve `uv` from `PATH` before invoking a project runner. | A miss continues through the existing runner-resolution path; it is not a fatal shared-library error. | Preserve the project-local `$HOME/.local/bin/uv` fallback and manager-specific routing. Runner behavior is covered by `build.bats`, `demo.bats`, `run.bats`, and `test.bats`. | Migrated in #2129; preserve local-runner fallback. |
| `projects.sh:61` | Resolve `python3` for the source-checkout pre-setup path. | A missing or unusable interpreter falls through to the existing setup guidance; normal list output/status belongs to Python. | Preserve the Base venv first choice and source-checkout `PYTHONPATH` fallback. Covered by project-list tests. | Migrated in #2129; preserve pre-setup fallback. |
| `repo.sh:2171` | Resolve `gh` before repository GitHub operations. | Keep the repository-specific prerequisite error and status. | No new platform fallback; repository GitHub behavior is covered by `cli/bash/commands/basectl/tests/repo.bats`. | Migrated in #2129; preserve custom prerequisite text. |
| `repo_github_settings.sh:21` | Resolve `brew` before checking the Homebrew-managed `gh` package. | A miss returns the existing quiet “not managed by Homebrew” result to the caller. | Preserve Homebrew package checks and macOS-only behavior. Covered by repository/setup tests. | Migrated in #2129; preserve Homebrew ownership check. |
| `setup_common.sh:301` | Resolve optional macOS `osascript` notification support. | A miss is non-fatal and emits the existing warning only when notification was requested. | No Linux fallback is implied; notification remains optional. Covered by setup tests. | Migrated in #2129; preserve optional notification behavior. |
| `setup_common.sh:336,348` (`setup_command_path`, file prerequisite) | Resolve generic setup prerequisites and `file` without logging on ordinary misses. | The wrapper returns failure so each caller can retain its own error/status text. | No platform fallback is added by the generic wrapper. Covered by setup tests. | Migrated in #2129; preserve caller-owned errors. |
| `setup_common.sh:490` | Resolve `python3` for setup diagnostics/routing. | Preserve the existing fallback and diagnostic status when Python is unavailable. | Platform-specific setup layers remain responsible for their own fallback/install paths. Covered by setup tests. | Migrated in #2129; preserve diagnostics behavior. |
| `setup_linux_debian.sh:69,98` | Resolve `python3` and arbitrary prerequisite names on Debian/Ubuntu. | Ordinary misses remain quiet until the Debian setup layer emits its command-specific result. | Preserve distro-specific discovery and package-install routing; do not claim support for other Linux flavors. Covered by setup tests. | Migrated in #2129; preserve Debian routing. |
| `setup_linux_debian.sh:311` | Resolve `dpkg-query` before package-state inspection. | A missing tool returns the existing prerequisite failure. | Keep Debian package semantics and the existing architecture/package probes. Covered by setup tests. | Migrated in #2129; preserve package-state behavior. |
| `setup_linux_debian.sh:371,372` | Resolve `curl` and `dpkg` before configuring the GitHub CLI apt repository. | Retain the explicit fatal messages and statuses naming the missing command. | Keep the Ubuntu/Debian apt path and its dry-run/approval boundary. Covered by setup tests. | Migrated in #2129; preserve fatal prerequisite text. |
| `setup_macos_homebrew.sh:75` | Resolve `brew` before Homebrew setup. | Preserve the existing setup result and diagnostics. | Keep the test-only Homebrew prefix hook and real Homebrew prefix discovery. Covered by setup tests. | Migrated in #2129; preserve Homebrew fallback. |
| `setup_macos_homebrew.sh:212` | Resolve `curl` before downloading a pinned Homebrew installer script. | Missing `curl` returns the existing status 127 path; download and verification failures retain their local errors. | Preserve explicit pinned URL/SHA requirements and macOS-only installer behavior. Covered by setup tests. | Migrated in #2129; preserve installer first-mile behavior. |
| `setup_macos_homebrew.sh:400` | Resolve `python3` only when the system-Python policy permits it. | Preserve the existing setup fallback when system Python is unavailable or disallowed. | The policy gate remains separate from command lookup. Covered by setup tests. | Migrated in #2129; preserve policy gate. |
| `update.sh:227,359` | Resolve `python3` and `brew` for update routing. | Keep update-specific diagnostics and delegated statuses. | Preserve source-checkout/Homebrew handoff and Homebrew trust checks. Covered by `cli/bash/commands/basectl/tests/update.bats`. | Migrated in #2129; preserve update routing. |

The command-discovery migration is therefore complete for production
subcommands. Future changes must not migrate test-only probes merely to remove
the `command -v` spelling, and must not remove absolute or project-local
fallbacks that are part of a platform contract.

## Future leaf-PR acceptance checklist

Before a future implementation PR changes a remaining nested parser or
discovery boundary, it must include:

1. The caller row updated with exact argv, status, output, logging, and
   forwarding semantics.
2. Runtime `basectl <command> --help` output captured before and after the
   change, where the command is public.
3. Focused BATS coverage for help, invalid input, duplicates, value forms,
   `--`, option-looking values, and delegated argv/status as applicable.
4. A check that `PATH`, Bash-function support, and platform/project-local
   fallback behavior have not changed accidentally.
5. Full Base validation after the focused tests pass.

This issue is an inventory and sequencing gate. It does not authorize a
parser API change, a behavior change, a test-fixture rewrite, or an installer
fallback change by itself.
