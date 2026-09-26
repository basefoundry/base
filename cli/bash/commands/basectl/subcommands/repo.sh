#!/usr/bin/env bash

[[ -n "${_base_repo_subcommand_sourced:-}" ]] && return 0
_base_repo_subcommand_sourced=1
readonly _base_repo_subcommand_sourced

import_base_lib git/lib_git.sh
import_base_lib gh/lib_gh.sh
import_base_lib str/lib_str.sh
import_base_lib arg/lib_arg.sh

source "$BASE_HOME/cli/bash/commands/basectl/subcommands/github_policy.sh"
# shellcheck source=cli/bash/commands/basectl/subcommands/inspection_json.sh
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/inspection_json.sh"

BASE_REPO_BASELINE_FILES=(
    README.md
    VERSION
    CHANGELOG.md
    CONTRIBUTING.md
    .github/pull_request_template.md
    .github/base-project.yml
    LICENSE
    .gitignore
    base_manifest.yaml
    tests/validate.sh
    .github/workflows/issue-branch-policy.yml
    .github/workflows/project-intake.yml
    .github/workflows/tests.yml
)

BASE_REPO_AGENT_GUIDANCE_FILES=(
    AGENTS.md
    skills.md
    .github/pull_request_template.md
)

base_repo_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl repo init <name> [options]
  basectl repo clone <name-or-owner/name> [options]
  basectl repo check [path] [options]
  basectl repo configure [path] [options]
  basectl repo agent-guidance [path] [options]
  basectl repo installer-template [path] [options]

Commands:
  init                 Create baseline files and optionally configure GitHub.
  clone                Clone one GitHub repository into the Base workspace.
  check                Verify the local repository baseline.
  configure            Apply GitHub settings, labels, branch policies, and Project metadata.
  agent-guidance       Seed optional repo-local agent guidance files.
  installer-template   Write or print the maintained project installer template.

Run 'basectl repo <command> --help' for command-specific options.
EOF
}

base_repo_init_usage() {
    cat <<'EOF'
Usage:
  basectl repo init <name> [options]

Options:
  --path <path>                 Target path for repo init. Defaults to workspace root plus <name>.
  --repo <owner/name>           GitHub repository to configure.
  --issue <number>              Issue number for --pr. Required with --pr.
  --category <name>             Issue category for --pr --dry-run. Real PR runs derive or verify it.
  --pr                          Commit the generated baseline on a branch and open a pull request.
  --agent-ready                 Also seed repo-local agent guidance files.
  --release                     Seed the generic release contract and process documentation.
  --language <csv>              Add project language metadata; may be repeated.
  --description <text>          Repository description for generated README.
  --license <SPDX>              License for the generated repository (Apache-2.0).
  --private                     Create a private GitHub repository when needed. This is the default.
  --public                      Create a public GitHub repository when needed.
  --no-configure                Skip GitHub configuration during repo init.
  --no-protect-default-branch   Skip Base-managed default branch protection during repo configure.
  --project <title>             GitHub Project title to configure. Defaults to the repository name.
  --project-owner <login>       GitHub Project owner. Defaults to the repository owner.
  --project-schema <schema>     Project metadata schema. Defaults to base-project.
  --initiative-option <name>    Initiative option to seed. May be repeated.
  --copy-project-fields-from <title>
                                Copy missing Project item field values from another Project.
  --no-project                  Skip GitHub Project metadata configuration.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Examples:
  # Create a new public GitHub repo and configure it.
  basectl repo init base-demo --repo basefoundry/base-demo --public

  # Add or refresh the Base baseline in an existing checkout.
  basectl repo init bankbuddy --path . --repo codeforester/bankbuddy --issue 123 --category enhancement --pr

  # Seed a polyglot project profile (CSV and repeated forms are equivalent).
  basectl repo init platform --language go,javascript --language typescript

  # After the baseline PR is merged, apply or repair GitHub settings.
  basectl repo configure . --repo codeforester/bankbuddy

Ensures the standard local Base-managed repository baseline, including
.github/base-project.yml. Safe to run against an existing repository: existing
files are left unchanged and missing baseline files are added.

Safe to re-run: Base-managed settings are created or updated to the Base
standard. Settings added outside Base are not removed.

When --repo names a missing GitHub repo, repo init creates it using --private/--public
and bootstraps the local checkout: it attaches origin, creates the initial commit,
and pushes the current branch. This is the only repo init path that pushes without
--pr, and it is safe because the remote was just created by the same command. An
existing GitHub repo is never implicitly pushed; use --pr for an explicit baseline
push and pull request. Unless --no-configure is set, repo init also applies the
GitHub-side settings handled by repo configure.

For the current checkout, pass its repository name and --path .
Invalid configured workspace or GitHub defaults fail before any repository action.
Plain repo init writes local baseline files but does not commit or push them.
With --pr, repo init requires --issue, commits baseline changes on the canonical
issue branch, pushes that branch to origin, and opens a pull request.
With --pr --dry-run, pass --category because dry-run performs no GitHub reads.
Real PR runs derive the issue's standard category label and verify --category
when it is supplied.
Pass --agent-ready to include AGENTS.md and skills.md with the baseline.
With --release, the baseline also declares the generic release contract and
creates docs/release-process.md. Release standardization requires --repo or an
existing GitHub origin so the manifest can record the release repository.
EOF
}

base_repo_clone_usage() {
    cat <<'EOF'
Usage:
  basectl repo clone <name-or-owner/name> [options]

Options:
  --owner <owner>               GitHub owner for short repository names.
  --path <path>                 Clone destination. Defaults to workspace root plus repository name.
  --dry-run                     Print planned clone without modifying the filesystem.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Examples:
  basectl repo clone base
  basectl repo clone banyanlabs --owner basefoundry
  basectl repo clone codeforester/bankbuddy
  basectl repo clone basefoundry/base --path ~/work/base

Short repository names require --owner <owner> or github.default_owner in
~/.base.d/config.yaml. The optional github.clone_protocol value controls the
reported clone URL; Base delegates the clone itself to gh repo clone.
EOF
}

base_repo_check_usage() {
    cat <<'EOF'
Usage:
  basectl repo check [path] [options]

Options:
  --agent-guidance              Include optional agent guidance files in repo check.
  --agent-ready                 Include the agent-ready repo guidance contract in repo check.
  --release                     Include the release contract and process document in repo check.
  --format <text|json>          Select human text or stable inspection JSON. Defaults to text.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Verifies the standard Base-managed repository baseline at path, or the current
directory when path is omitted. Use --release to verify the opt-in release
contract as well.
EOF
}

base_repo_configure_usage() {
    cat <<'EOF'
Usage:
  basectl repo configure [path] [options]

Options:
  --repo <owner/name>           GitHub repository to configure.
  --no-protect-default-branch   Skip Base-managed default branch protection.
  --project <title>             GitHub Project title to configure. Defaults to the repository name.
  --project-owner <login>       GitHub Project owner. Defaults to the repository owner.
  --project-schema <schema>     Project metadata schema. Defaults to base-project.
  --initiative-option <name>    Initiative option to seed. May be repeated.
  --copy-project-fields-from <title>
                                Copy missing Project item field values from another Project.
  --replace-project             Replace a nonstandard existing Project from base-project-template.
  --no-project                  Skip GitHub Project metadata configuration.
  --release                     Seed the generic release contract and process documentation.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Examples:
  basectl repo configure . --repo codeforester/bankbuddy
  basectl repo configure . --copy-project-fields-from "Legacy Roadmap"

repo configure applies or repairs GitHub-side repository settings, labels,
default-branch protection, branch naming enforcement, Project metadata, and
repo-visible Project intake support. With --release, it also adds missing
release metadata and agent-facing release documentation without replacing an
existing release declaration.
Use it after a repo init --pr baseline PR is merged, after cloning an older
Base-managed repo, or whenever GitHub settings drift.

When .github/base-project.yml exists, repo configure uses it for repo-specific
GitHub Project taxonomy and issue defaults.

Safe to re-run: Base-managed settings are created or updated to the Base
standard. Settings added outside Base are not removed.

It does not create the full local baseline; run repo init first when the
Base-managed files are missing. Release standardization is opt-in because not
every repository publishes versioned artifacts.
EOF
}

base_repo_print_usage_error() {
    local help_command="$1"
    shift

    base_std_print_error "$*"
    printf "Run '%s --help' for usage.\n" "$help_command" >&2
    return 2
}

base_repo_usage_error() {
    base_repo_print_usage_error "basectl repo" "$@"
}

base_repo_init_usage_error() {
    base_repo_print_usage_error "basectl repo init" "$@"
}

base_repo_clone_usage_error() {
    base_repo_print_usage_error "basectl repo clone" "$@"
}

base_repo_check_usage_error() {
    base_repo_print_usage_error "basectl repo check" "$@"
}

base_repo_configure_usage_error() {
    base_repo_print_usage_error "basectl repo configure" "$@"
}

base_repo_installer_template_usage_error() {
    base_repo_print_usage_error "basectl repo installer-template" "$@"
}

base_repo_load_installer_template() {
    local module_path

    base_repo_load_pr || return 1

    if declare -F base_repo_installer_template >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/repo_installer_template.sh" || return 1
    [[ -f "$module_path" ]] || {
        base_std_log_error "repo installer-template helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo_installer_template.sh
    source "$module_path"
}

base_repo_load_agent_guidance() {
    local module_path

    base_repo_load_pr || return 1

    if declare -F base_repo_agent_guidance >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/repo_agent_guidance.sh" || return 1
    [[ -f "$module_path" ]] || {
        base_std_log_error "repo agent-guidance helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo_agent_guidance.sh
    source "$module_path"
}

base_repo_load_github_settings() {
    local module_path

    if declare -F base_repo_configure_github >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/repo_github_settings.sh" || return 1
    [[ -f "$module_path" ]] || {
        base_std_log_error "repo GitHub settings helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo_github_settings.sh
    source "$module_path"
}

base_repo_load_clone() {
    local module_path

    if declare -F base_repo_clone >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/repo_clone.sh" || return 1
    [[ -f "$module_path" ]] || {
        base_std_log_error "repo clone helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo_clone.sh
    source "$module_path"
}

base_repo_load_pr() {
    local module_path

    if declare -F base_repo_pr_branch_name >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/repo_pr.sh" || return 1
    [[ -f "$module_path" ]] || {
        base_std_log_error "repo pull request helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo_pr.sh
    source "$module_path"
}

base_repo_load_init() {
    local module_path

    base_repo_load_pr || return 1

    if declare -F base_repo_init >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/repo_init.sh" || return 1
    [[ -f "$module_path" ]] || {
        base_std_log_error "repo init helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo_init.sh
    source "$module_path"
}

base_repo_default_description() {
    local name="$1"

    printf 'Base-managed project %s.\n' "$name"
}

base_repo_validate_name() {
    local name="$1"

    [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || {
        printf 'Repository name must start with a letter or digit and contain only letters, digits, dot, underscore, and dash.\n' >&2
        return 1
    }
}

base_repo_validate_owner() {
    local owner="$1"

    [[ "$owner" =~ ^[A-Za-z0-9][A-Za-z0-9-]*$ ]] || {
        printf 'GitHub owner must start with a letter or digit and contain only letters, digits, and dash.\n' >&2
        return 1
    }
}

base_repo_target_path() {
    local path="$1"
    local parent name

    case "$path" in
        "."|"./")
            pwd -P
            return 0
            ;;
    esac

    if [[ "$path" = /* ]]; then
        printf '%s\n' "$path"
        return 0
    fi

    parent="$(dirname -- "$path")"
    name="$(basename -- "$path")"
    if [[ -d "$parent" ]]; then
        parent="$(cd -- "$parent" && pwd -P)"
    else
        parent="$(cd -- "$(pwd -P)" && pwd -P)/$parent"
    fi
    printf '%s/%s\n' "$parent" "$name"
}

base_repo_strip_config_value() {
    local value="$1"
    local quote character previous remainder
    local result=""
    local index length escaped=0 closed=0

    base_str_trim value

    quote="${value:0:1}"
    case "$quote" in
        \"|\')
            length="${#value}"
            for ((index = 1; index < length; index++)); do
                character="${value:index:1}"
                if [[ "$quote" == \" && "$character" == \\ && "$escaped" == "0" ]]; then
                    result+="$character"
                    escaped=1
                    continue
                fi
                if ((escaped)); then
                    result+="$character"
                    escaped=0
                    continue
                fi
                if [[ "$quote" == \' && "$character" == \' && "${value:index+1:1}" == \' ]]; then
                    result+="$character"
                    ((index++))
                    continue
                fi
                if [[ "$character" == "$quote" ]]; then
                    closed=1
                    remainder="${value:index+1}"
                    break
                fi
                result+="$character"
            done
            ((closed)) || return 2
            base_str_trim remainder
            [[ -z "$remainder" || "$remainder" == \#* ]] || return 2
            value="$result"
            ;;
        *)
            length="${#value}"
            for ((index = 0; index < length; index++)); do
                character="${value:index:1}"
                previous=""
                ((index > 0)) && previous="${value:index-1:1}"
                if [[ "$character" == "#" && ( -z "$previous" || "$previous" =~ [[:space:]] ) ]]; then
                    break
                fi
                result+="$character"
            done
            base_str_trim result
            value="$result"
            ;;
    esac

    printf '%s\n' "$value"
}

base_repo_expand_path() {
    local path="$1"

    case "$path" in
        \~)
            printf '%s\n' "$HOME"
            ;;
        \~/*)
            printf '%s/%s\n' "$HOME" "${path#\~/}"
            ;;
        *)
            printf '%s\n' "$path"
            ;;
    esac
}

base_repo_configured_workspace_root() {
    local config_path="$HOME/.base.d/config.yaml"
    local in_workspace=0 line value

    [[ -f "$config_path" ]] || return 1

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*(#.*)?$ ]] && continue

        if [[ "$line" =~ ^workspace:[[:space:]]*(#.*)?$ ]]; then
            in_workspace=1
            continue
        fi

        if ((in_workspace)) && [[ ! "$line" =~ ^[[:space:]] ]]; then
            return 1
        fi

        if ((in_workspace)) && [[ "$line" =~ ^[[:space:]]+root:[[:space:]]*(.*)$ ]]; then
            value="$(base_repo_strip_config_value "${BASH_REMATCH[1]}")" || {
                base_std_log_error "$config_path: workspace.root has invalid quoted YAML syntax."
                return 2
            }
            [[ -n "$value" ]] || {
                base_std_log_error "$config_path: workspace.root must be a non-empty path."
                return 2
            }
            value="$(base_repo_expand_path "$value")"
            [[ "$value" = /* ]] || {
                base_std_log_error "$config_path: workspace.root must be an absolute path or start with '~'."
                return 2
            }
            printf '%s\n' "$value"
            return 0
        fi
    done < "$config_path"

    return 1
}

base_repo_configured_github_value() {
    local config_path="$HOME/.base.d/config.yaml"
    local in_github=0
    local key="$1"
    local line value

    [[ -f "$config_path" ]] || return 1

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*(#.*)?$ ]] && continue

        if [[ "$line" =~ ^github:[[:space:]]*(#.*)?$ ]]; then
            in_github=1
            continue
        fi

        if ((in_github)) && [[ ! "$line" =~ ^[[:space:]] ]]; then
            return 1
        fi

        if ((in_github)) && [[ "$line" =~ ^[[:space:]]+${key}:[[:space:]]*(.*)$ ]]; then
            value="$(base_repo_strip_config_value "${BASH_REMATCH[1]}")" || {
                base_std_log_error "$config_path: github.$key has invalid quoted YAML syntax."
                return 2
            }
            [[ -n "$value" ]] || {
                base_std_log_error "$config_path: github.$key must be a non-empty value."
                return 2
            }
            printf '%s\n' "$value"
            return 0
        fi
    done < "$config_path"

    return 1
}

base_repo_default_workspace_root() {
    local configured_root status

    configured_root="$(base_repo_configured_workspace_root)"
    status=$?
    case "$status" in
        0)
            printf '%s\n' "$configured_root"
            return 0
            ;;
        1)
            ;;
        *)
            return "$status"
            ;;
    esac

    [[ -n "${BASE_HOME:-}" ]] || {
        base_std_log_error "BASE_HOME is required to resolve the default repository path."
        return 1
    }
    cd -- "$BASE_HOME/.." && pwd -P
}

base_repo_default_target_path() {
    local name="$1"
    local workspace_root

    workspace_root="$(base_repo_default_workspace_root)" || return $?
    printf '%s/%s\n' "$workspace_root" "$name"
}

base_repo_default_github_owner() {
    local owner status

    owner="$(base_repo_configured_github_value default_owner)"
    status=$?
    case "$status" in
        0)
            printf '%s\n' "$owner"
            return 0
            ;;
        1)
            return 1
            ;;
        *)
            return "$status"
            ;;
    esac
}

base_repo_clone_protocol() {
    local protocol status

    protocol="$(base_repo_configured_github_value clone_protocol)"
    status=$?
    case "$status" in
        0)
            ;;
        1)
            protocol="ssh"
            ;;
        *)
            return "$status"
            ;;
    esac

    case "$protocol" in
        ssh|https)
            printf '%s\n' "$protocol"
            ;;
        *)
            base_std_log_error "$HOME/.base.d/config.yaml: github.clone_protocol must be 'ssh' or 'https'."
            return 2
            ;;
    esac
}

base_repo_clone_url() {
    local protocol="$1"
    local repo="$2"

    case "$protocol" in
        ssh)
            printf 'git@github.com:%s.git\n' "$repo"
            ;;
        https)
            printf 'https://github.com/%s.git\n' "$repo"
            ;;
        *)
            return 1
            ;;
    esac
}

base_repo_create_directory() {
    local target_dir="$1"

    [[ -d "$target_dir" ]] && return 0

    if mkdir -p "$target_dir" 2>/dev/null; then
        return 0
    fi

    base_std_log_error "Failed to create parent directory '$target_dir'."
    return 1
}

base_repo_write_stream() {
    local dry_run="$1"
    local target="$2"
    local target_dir

    if [[ -e "$target" ]]; then
        base_std_log_info "File already exists at '$target'; leaving it unchanged."
        return 0
    fi

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create '%s'.\n" "$target"
        return 0
    fi

    target_dir="$(dirname -- "$target")"
    base_repo_create_directory "$target_dir" || return 1
    if ! cat 2>/dev/null > "$target"; then
        base_std_log_error "Failed to write '$target'."
        return 1
    fi
    printf "Created '%s'.\n" "$target"
}

base_repo_write_executable_stream() {
    local dry_run="$1"
    local target="$2"
    local target_dir

    if [[ -e "$target" ]]; then
        base_std_log_info "File already exists at '$target'; leaving it unchanged."
        return 0
    fi

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create executable '%s'.\n" "$target"
        return 0
    fi

    target_dir="$(dirname -- "$target")"
    base_repo_create_directory "$target_dir" || return 1
    if ! cat 2>/dev/null > "$target"; then
        base_std_log_error "Failed to write '$target'."
        return 1
    fi
    if ! chmod +x "$target" 2>/dev/null; then
        base_std_log_error "Failed to make '$target' executable."
        return 1
    fi
    printf "Created executable '%s'.\n" "$target"
}

base_repo_print_review_hint() {
    local target_dir="$1"

    printf "Run git -C '%s' status --short to review changes.\n" "$target_dir"
}

base_repo_write_readme() {
    local description="$3"
    local dry_run="$1"
    local name="$2"
    local root="$4"

    base_repo_write_stream "$dry_run" "$root/README.md" <<EOF
# $name

$description

## Base

This repository is managed by [Base](https://github.com/basefoundry/base).

Common commands:

\`\`\`bash
basectl setup $name
basectl check $name
basectl doctor $name
basectl test $name
\`\`\`
EOF
}

base_repo_write_version() {
    local dry_run="$1"
    local root="$2"

    base_repo_write_stream "$dry_run" "$root/VERSION" <<'EOF'
0.1.0
EOF
}

base_repo_write_changelog() {
    local dry_run="$1"
    local name="$2"
    local root="$3"

    base_repo_write_stream "$dry_run" "$root/CHANGELOG.md" <<EOF
# Changelog

All notable changes to $name will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions are tracked in the repo-root \`VERSION\` file.

## [Unreleased]

### Added

- Initialized the repository with the Base-managed repo baseline.
EOF
}

base_repo_write_contributing() {
    local dry_run="$1"
    local name="$2"
    local root="$3"

    base_repo_write_stream "$dry_run" "$root/CONTRIBUTING.md" <<EOF
# Contributing to $name

Thank you for improving this project.

## Workflow

1. Create or choose a GitHub issue before starting implementation work.
2. Use exactly one standard issue category label: \`bug\`, \`enhancement\`,
   \`documentation\`, \`ci\`, or \`security\`.
3. Create an issue-backed branch:

   \`\`\`text
   <category>/<issue>-<YYYYMMDD>-<slug>
   \`\`\`

   The category prefix must match the issue's single standard category label.
   This branch shape is tool-independent; \`feat/\`, \`agent/\`, \`codex/\`, and
   bare issue-number prefixes are invalid.

4. Use a dedicated Git worktree for each pull request so the main checkout can
   stay on the default branch:

   \`\`\`bash
   git fetch origin
   git worktree add -b <branch> ../$name-worktrees/<slug> origin/<default-branch>
   \`\`\`

5. Keep the pull request scoped to the issue and link it with
   \`Fixes #<issue>\` or \`Closes #<issue>\` when merge should close the issue.
6. Run the project checks before opening or updating a pull request.
7. Update \`CHANGELOG.md\` only for notable user-visible or release-worthy
   changes.
8. After merge, sync the default branch, remove the worktree, and delete merged
   local and remote branches when safe:

   \`\`\`bash
   git pull --ff-only origin <default-branch>
   git worktree remove ../$name-worktrees/<slug>
   git branch -d <branch>
   git push origin --delete <branch>
   \`\`\`

Useful commands:

\`\`\`bash
basectl check $name
basectl doctor $name
basectl test $name
\`\`\`
EOF
}

base_repo_pull_request_template_policy() {
    local comment_var="$3"
    local heading_var="$2"
    local policy_comment
    local policy_heading
    local variant="$1"

    case "$variant" in
        repo-init)
            policy_heading='Notes'
            policy_comment='Optional: tradeoffs, follow-up work, or reviewer context.'
            ;;
        agent-guidance)
            policy_heading='Reviewer Notes'
            policy_comment='Optional: tradeoffs, follow-up work, or areas where reviewer attention would help.'
            ;;
        *)
            base_std_log_error "Unknown pull-request template policy variant '$variant'."
            return 1
            ;;
    esac

    printf -v "$heading_var" '%s' "$policy_heading"
    printf -v "$comment_var" '%s' "$policy_comment"
}

base_repo_write_pull_request_template() {
    local dry_run="$1"
    local root="$2"
    local notes_comment
    local notes_heading
    local template

    base_repo_pull_request_template_policy repo-init notes_heading notes_comment || return 1
    [[ -n "${3:-}" ]] && notes_heading="$3"
    [[ -n "${4:-}" ]] && notes_comment="$4"

    template="$(cat <<'EOF'
## Summary

<!-- What changed and why. Focus on decisions and user impact, not just the diff. -->

## Issue

Closes #

## Validation

<!-- Commands run and relevant output. Include narrow checks and any broader suite used. -->

## @NOTES_HEADING@

<!-- @NOTES_COMMENT@ -->

## Checklist

- [ ] Branch name follows `<category>/<issue>-<YYYYMMDD>-<slug>`, and its category prefix matches the issue's single standard category label.
- [ ] Pull request is scoped to one issue, unless a documented multi-issue exception applies.
- [ ] Pull request body explains what changed and how it was validated.
- [ ] Relevant project checks pass.
- [ ] Documentation is updated when behavior or user-facing commands change.
- [ ] CHANGELOG is updated for notable user-visible or release-worthy changes.
- [ ] Pull request includes `Fixes #<issue>` or `Closes #<issue>` when merge should close the issue.
EOF
    )" || return 1
    local notes_heading_marker='@NOTES_HEADING@'
    local notes_comment_marker='@NOTES_COMMENT@'
    template="${template%%"$notes_heading_marker"*}${notes_heading}${template#*"$notes_heading_marker"}"
    template="${template%%"$notes_comment_marker"*}${notes_comment}${template#*"$notes_comment_marker"}"
    printf '%s\n' "$template" | base_repo_write_stream "$dry_run" "$root/.github/pull_request_template.md"
}

base_repo_license_is_supported() {
    case "$1" in
        Apache-2.0)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

base_repo_license_display() {
    printf 'Apache-2.0\n'
}

base_repo_write_license() {
    local dry_run="$1"
    local license_id="$2"
    local root="$3"
    local license_template="${BASE_HOME:-}/templates/licenses/Apache-2.0"

    [[ "$license_id" == "Apache-2.0" ]] || {
        base_std_log_error "Unsupported repository license '$license_id'. Expected: $(base_repo_license_display)"
        return 1
    }
    [[ -f "$license_template" ]] || {
        base_std_log_error "Apache-2.0 license template '$license_template' was not found."
        return 1
    }
    base_repo_write_stream "$dry_run" "$root/LICENSE" < "$license_template"
}

base_repo_write_gitignore() {
    local dry_run="$1"
    local root="$2"

    base_repo_write_stream "$dry_run" "$root/.gitignore" <<'EOF'
.DS_Store
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
dist/
build/
*.egg-info/
EOF
}

base_repo_write_manifest() {
    local dry_run="$1"
    local name="$2"
    local root="$3"
    local language
    local languages=("${@:4}")
    local has_python=0

    for language in "${languages[@]}"; do
        [[ "$language" == 'python' ]] && has_python=1
    done

    {
        printf 'schema_version: 1\n\n'
        printf 'project:\n  name: %s\n' "$name"
        if ((${#languages[@]})); then
            printf '  languages:\n'
            for language in "${languages[@]}"; do
                printf '    - %s\n' "$language"
            done
        fi
        if ((has_python)); then
            printf '\npython:\n  manager: uv\n'
        fi
        printf '\ntest:\n  command: ./tests/validate.sh\n'
    } | base_repo_write_stream "$dry_run" "$root/base_manifest.yaml"
}

base_repo_release_manifest_has_key() {
    local manifest_path="$1"

    awk '
        /^[^[:space:]#][^:]*:[[:space:]]*(#.*)?$/ {
            key = $0
            sub(/:.*/, "", key)
            if (key == "release") {
                found = 1
            }
        }
        END { exit(found ? 0 : 1) }
    ' "$manifest_path"
}

base_repo_write_release_manifest() {
    local dry_run="$1"
    local github_repo="$2"
    local manifest_path="$3/base_manifest.yaml"

    if [[ ! -f "$manifest_path" && "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would add the generic release contract to '%s'.\n" "$manifest_path"
        return 0
    fi

    [[ -f "$manifest_path" ]] || {
        base_std_log_error "Release standardization requires '$manifest_path'."
        printf "       Run 'basectl repo init' first to create the Base repository baseline.\n" >&2
        return 1
    }

    if base_repo_release_manifest_has_key "$manifest_path"; then
        printf "Release metadata: existing release contract found in '%s'; leaving it unchanged.\n" "$manifest_path"
        return 0
    fi

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would append the generic release contract to '%s'.\n" "$manifest_path"
        return 0
    fi

    {
        printf '\nrelease:\n'
        printf '  version_file: VERSION\n'
        printf '  changelog: CHANGELOG.md\n'
        printf '  tag_prefix: v\n'
        printf '  github:\n'
        printf '    repository: %s\n' "$github_repo"
        printf '    release_title: "{repository} v{version}"\n'
    } >> "$manifest_path" || {
        base_std_log_error "Unable to append release metadata to '$manifest_path'."
        return 1
    }
    printf "Created release metadata in '%s'.\n" "$manifest_path"
}

base_repo_write_release_process() {
    local dry_run="$1"
    local name="$2"
    local repo="$3"
    local root="$4"

    base_repo_write_stream "$dry_run" "$root/docs/release-process.md" <<EOF
# Release Process

This repository uses the Base release contract. The machine-readable release
metadata lives in \`base_manifest.yaml\`; the guarded \`basectl release\`
commands use that contract for readiness checks, notes, tags, and GitHub
Releases.

## Standard Sequence

1. Create or choose a release issue and keep its Project metadata current.
2. Create a release-preparation branch and dedicated worktree from
   \`origin/main\`.
3. Update \`VERSION\`, the README release reference, and \`CHANGELOG.md\`.
   Keep ordinary pull requests under \`[Unreleased]\`; only release-preparation
   work changes the published version.
4. Run the repository validation command, \`git diff --check\`, and any package
   or integration checks required by this repository.
5. Open and merge the release-preparation pull request.
6. Sync local \`main\`, then inspect the release:

   \`\`\`bash
   basectl release check --version X.Y.Z
   basectl release plan --version X.Y.Z
   basectl release notes --version X.Y.Z
   basectl release publish --version X.Y.Z --dry-run
   \`\`\`

7. Publish only after the checks pass. Use \`--yes\` only from a trusted
   non-interactive release shell:

   \`\`\`bash
   basectl release publish --version X.Y.Z --yes
   \`\`\`

8. Verify the annotated tag and GitHub Release for \`$repo\`.
9. Complete every declared downstream handoff. For Homebrew, update the tap
   formula to the published archive and checksum, run the formula tests and
   audit, publish required bottles, and verify install and upgrade paths. If a
   downstream repository pins this project by commit, update and validate that
   pin after the release.
10. Record the release and downstream URLs on the release issue, then remove
    the release worktree and merged branches when safe.

## Repository Contract

- Project: \`$name\`
- GitHub repository: \`$repo\`
- Version file: \`VERSION\`
- Changelog: \`CHANGELOG.md\`
- Tag prefix: \`v\`

Do not publish a release when the repository is dirty, the version metadata is
inconsistent, the changelog section is missing, or a required downstream handoff
has not been identified.
EOF
}

base_repo_configure_release() {
    local dry_run="$1"
    local github_repo="$2"
    local root="$3"

    [[ -n "$github_repo" ]] || {
        base_std_log_error "Release standardization requires a GitHub repository."
        return 1
    }
    base_repo_write_release_manifest "$dry_run" "$github_repo" "$root" || return 1
    base_repo_write_release_process "$dry_run" "$(basename -- "$root")" "$github_repo" "$root" || return 1
}

base_repo_check_release() {
    local manifest_path="$1/base_manifest.yaml"
    local release_doc="$1/docs/release-process.md"
    local status=0

    if [[ ! -f "$manifest_path" ]] || ! base_repo_release_manifest_has_key "$manifest_path"; then
        printf "Release contract: missing from '%s'.\n" "$manifest_path"
        status=1
    fi
    if [[ ! -f "$release_doc" ]]; then
        printf "Release process: missing '%s'.\n" "$release_doc"
        status=1
    fi
    if [[ "$status" -eq 0 ]]; then
        printf "Release contract: present.\n"
    fi
    return "$status"
}

base_repo_write_validate_script() {
    local dry_run="$1"
    local root="$2"

base_repo_write_executable_stream "$dry_run" "$root/tests/validate.sh" <<'EOF'
#!/usr/bin/env bash

required_files=(
  README.md
  VERSION
  CHANGELOG.md
  CONTRIBUTING.md
  .github/pull_request_template.md
  .github/base-project.yml
  LICENSE
  base_manifest.yaml
  .github/workflows/issue-branch-policy.yml
  .github/workflows/project-intake.yml
  .github/workflows/tests.yml
)

for file in "${required_files[@]}"; do
  [[ -f "$file" ]] || {
    printf 'Missing required file: %s\n' "$file" >&2
    exit 1
  }
done

printf 'Repository baseline is present.\n'
EOF
}

base_repo_write_tests_workflow() {
    local dry_run="$1"
    local root="$2"

    base_repo_write_stream "$dry_run" "$root/.github/workflows/tests.yml" <<'EOF'
name: Tests

on:
  push:
  pull_request:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  validate:
    runs-on: macos-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
      - name: Validate repository baseline
        run: ./tests/validate.sh
EOF
}

base_repo_project_intake_workflow_template_path() {
    [[ -n "${BASE_HOME:-}" ]] || {
        base_std_log_error "BASE_HOME is required to locate the Project Intake workflow template."
        return 1
    }

    printf '%s/templates/project-intake.yml\n' "$BASE_HOME"
}

base_repo_issue_branch_policy_workflow_template_path() {
    [[ -n "${BASE_HOME:-}" ]] || {
        base_std_log_error "BASE_HOME is required to locate the Issue Branch Policy workflow template."
        return 1
    }

    printf '%s/templates/issue-branch-policy.yml\n' "$BASE_HOME"
}

base_repo_write_issue_branch_policy_workflow() {
    local dry_run="$1"
    local root="$2"
    local template

    template="$(base_repo_issue_branch_policy_workflow_template_path)" || return 1
    [[ -f "$template" ]] || {
        base_std_log_error "Issue Branch Policy workflow template was not found at '$template'."
        return 1
    }

    base_repo_write_stream "$dry_run" "$root/.github/workflows/issue-branch-policy.yml" < "$template"
}

base_repo_write_project_intake_workflow() {
    local dry_run="$1"
    local root="$2"
    local template

    template="$(base_repo_project_intake_workflow_template_path)" || return 1
    [[ -f "$template" ]] || {
        base_std_log_error "Project Intake workflow template was not found at '$template'."
        return 1
    }

    base_repo_write_stream "$dry_run" "$root/.github/workflows/project-intake.yml" < "$template"
}

base_repo_write_project_config() {
    local dry_run="$1"
    local root="$2"

    base_repo_write_stream "$dry_run" "$root/.github/base-project.yml" <<'EOF'
project:
  areas: []
  initiatives: []
  issue_defaults:
    status: Backlog
    priority: P2
    area: Product
    initiative: Adoption Polish
    size: S
EOF
}

base_repo_write_project_support_files() {
    local dry_run="$1"
    local root="$2"
    local status=0

    base_repo_write_project_config "$dry_run" "$root" || status=1
    base_repo_write_project_intake_workflow "$dry_run" "$root" || status=1

    return "$status"
}

base_repo_write_baseline() {
    local description="$3"
    local dry_run="$1"
    local license_id="$5"
    local name="$2"
    local root="$4"
    local languages=("${@:6}")
    local status=0

    if [[ "$dry_run" != "1" ]]; then
        base_repo_create_directory "$root" || return 1
    fi

    base_repo_write_readme "$dry_run" "$name" "$description" "$root" || status=1
    base_repo_write_version "$dry_run" "$root" || status=1
    base_repo_write_changelog "$dry_run" "$name" "$root" || status=1
    base_repo_write_contributing "$dry_run" "$name" "$root" || status=1
    base_repo_write_pull_request_template "$dry_run" "$root" || status=1
    base_repo_write_project_config "$dry_run" "$root" || status=1
    base_repo_write_license "$dry_run" "$license_id" "$root" || status=1
    base_repo_write_gitignore "$dry_run" "$root" || status=1
    base_repo_write_manifest "$dry_run" "$name" "$root" "${languages[@]}" || status=1
    base_repo_write_validate_script "$dry_run" "$root" || status=1
    base_repo_write_issue_branch_policy_workflow "$dry_run" "$root" || status=1
    base_repo_write_project_intake_workflow "$dry_run" "$root" || status=1
    base_repo_write_tests_workflow "$dry_run" "$root" || status=1

    return "$status"
}

base_repo_infer_github_repo() {
    local path="$1"
    local github_repo

    base_gh_infer_repo_from_origin "$path" github_repo || return 1

    printf '%s\n' "$github_repo"
}

base_repo_bootstrap_github_checkout() {
    local dry_run="$1"
    local repo="$2"
    local root="$3"
    local branch=""
    local origin_repo=""
    local origin_url=""
    local protocol
    local remote_url

    protocol="$(base_repo_clone_protocol)" || return 1
    remote_url="$(base_repo_clone_url "$protocol" "$repo")" || return 1

    if [[ "$dry_run" == "1" ]]; then
        if [[ ! -d "$root/.git" ]]; then
            printf "[DRY-RUN] Would initialize a Git repository at '%s' on branch 'main'.\n" "$root"
        fi
        printf "[DRY-RUN] Would attach origin '%s' to '%s'.\n" "$remote_url" "$root"
        printf "[DRY-RUN] Would commit the initial repository contents with message 'Initial repository commit'.\n"
        printf "[DRY-RUN] Would push the initial branch to origin.\n"
        return 0
    fi

    if [[ ! -d "$root/.git" ]]; then
        git init -b main "$root" >/dev/null 2>&1 || {
            base_std_log_error "Failed to initialize Git repository at '$root'."
            return 1
        }
    fi

    if origin_url="$(git -C "$root" remote get-url origin 2>/dev/null)"; then
        origin_repo="$(base_repo_infer_github_repo "$root" 2>/dev/null || true)"
        if [[ "$origin_repo" != "$repo" ]]; then
            base_std_log_error "New GitHub repository '$repo' cannot be bootstrapped because '$root' already has origin '$origin_url'. Remove or correct that origin, then retry."
            return 1
        fi
    else
        git -C "$root" remote add origin "$remote_url" || {
            base_std_log_error "Failed to attach GitHub origin '$remote_url' to '$root'."
            return 1
        }
    fi

    # A newly created remote is empty. Stage the complete checkout so this
    # intent-driven path can publish an extracted project as one coherent
    # initial commit. Existing remotes never reach this function.
    git -C "$root" add -A || {
        base_std_log_error "Failed to stage the initial repository contents in '$root'."
        return 1
    }

    if git -C "$root" diff --cached --quiet --; then
        if git -C "$root" rev-parse --verify HEAD >/dev/null 2>&1; then
            branch="$(git -C "$root" branch --show-current)"
        else
            git -C "$root" checkout -b main >/dev/null 2>&1 || {
                base_std_log_error "Failed to select the initial 'main' branch in '$root'."
                return 1
            }
            branch="main"
        fi
    else
        if ! git -C "$root" rev-parse --verify HEAD >/dev/null 2>&1; then
            git -C "$root" checkout -b main >/dev/null 2>&1 || {
                base_std_log_error "Failed to select the initial 'main' branch in '$root'."
                return 1
            }
            git -C "$root" commit -m "Initial repository commit" || {
                base_std_log_error "Failed to create the initial repository commit."
                return 1
            }
        else
            git -C "$root" commit -m "Add Base repository baseline" || {
                base_std_log_error "Failed to commit the Base repository baseline."
                return 1
            }
        fi
        branch="$(git -C "$root" branch --show-current)"
    fi

    [[ -n "$branch" ]] || {
        base_std_log_error "Unable to determine the branch to publish from '$root'."
        return 1
    }
    git -C "$root" push -u origin "$branch" || {
        base_std_log_error "Failed to push the initial repository branch '$branch' to origin."
        return 1
    }
    base_std_log_info "Bootstrapped '$repo' from '$root' on branch '$branch'."
}

base_repo_require_gh() {
    base_gh_require_cli "GitHub CLI 'gh' is required for repository configuration." || return 1
    base_gh_auth_status_diagnostics "Run 'gh auth login -h github.com' and retry."
}

base_repo_pretty_quote() {
    local value="$1"

    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    value="${value//$'\n'/\\n}"
    value="${value//$'\r'/\\r}"
    value="${value//$'\t'/\\t}"
    printf '"%s"' "$value"
}

base_repo_pretty_arg() {
    local value="$1"

    if [[ "$value" =~ ^[A-Za-z0-9_./:=@+-]+$ ]]; then
        printf '%s' "$value"
    else
        base_repo_pretty_quote "$value"
    fi
}

base_repo_pretty_command() {
    local arg
    local first=1

    for arg in "$@"; do
        if ((first)); then
            first=0
        else
            printf ' '
        fi
        base_repo_pretty_arg "$arg"
    done
}

base_repo_normalize_language() {
    local language="$1"

    case "$language" in
        c|cpp)
            printf '%s\n' "$language"
            ;;
        c++)
            printf 'cpp\n'
            ;;
        go|golang)
            printf 'go\n'
            ;;
        java)
            printf 'java\n'
            ;;
        javascript|js)
            printf 'javascript\n'
            ;;
        python)
            printf 'python\n'
            ;;
        ts|typescript)
            printf 'typescript\n'
            ;;
        *)
            return 1
            ;;
    esac
}

base_repo_supported_languages_display() {
    printf '%s\n' 'c, c++, cpp, go, golang, java, javascript, js, python, ts, typescript'
}

base_repo_languages_csv() {
    local first=1
    local language

    for language in "$@"; do
        if ((first)); then
            first=0
        else
            printf ','
        fi
        printf '%s' "$language"
    done
    printf '\n'
}

base_repo_join_csv() {
    local joined=""
    # shellcheck disable=SC2034 # Passed by name to base_str_join.
    local values=("$@")

    base_str_join joined ", " values
    printf '%s' "$joined"
}

base_repo_title_case_name() {
    local name="$1"

    printf '%s\n' "$name" |
        tr '._-' '   ' |
        awk '{ for (i = 1; i <= NF; i++) { $i = toupper(substr($i, 1, 1)) substr($i, 2) } print }'
}

base_repo_write_init_agent_guidance() {
    local default_branch="$3"
    local dry_run="$1"
    local notes_comment
    local notes_heading
    local repo_name="$2"
    local root="$5"
    local validation_command="$4"

    base_repo_load_agent_guidance || return 1
    base_repo_pull_request_template_policy repo-init notes_heading notes_comment || return 1
    base_repo_write_agent_guidance \
        "$dry_run" "$repo_name" "$default_branch" "$validation_command" "$root" "$notes_heading" "$notes_comment" 0
}

base_repo_check_baseline() {
    local current_dir
    local fix_path
    local missing_files=()
    local path="$1"
    local rel
    local repo_name
    local required_files=()
    local required_count
    local validation_file
    local not_executable_files=()
    local command=()

    validation_file="$(base_repo_baseline_validation_file "$path")"
    mapfile -t required_files < <(base_repo_required_baseline_files "$path")
    required_count="${#required_files[@]}"
    for rel in "${required_files[@]}"; do
        if [[ ! -f "$path/$rel" ]]; then
            missing_files+=("$rel")
        fi
    done

    if [[ -f "$path/$validation_file" && ! -x "$path/$validation_file" ]]; then
        not_executable_files+=("$validation_file")
    fi

    if ((${#missing_files[@]} || ${#not_executable_files[@]})); then
        if ((${#missing_files[@]})); then
            printf "Repository baseline: %d of %d required files missing.\n" \
                "${#missing_files[@]}" \
                "$required_count"
        else
            printf "Repository baseline: all %d required files present, but some requirements failed.\n" \
                "$required_count"
        fi
        for rel in "${missing_files[@]}"; do
            printf "  Missing: %s\n" "$rel"
        done
        current_dir="$(pwd -P)"
        for rel in "${not_executable_files[@]}"; do
            printf "  Not executable: %s\n" "$rel"
            if [[ "$path" == "$current_dir" ]]; then
                fix_path="$rel"
            else
                fix_path="$path/$rel"
            fi
            printf "  Fix: chmod +x %s\n" "$(base_repo_pretty_arg "$fix_path")"
        done
        if ((${#missing_files[@]})) && [[ "$validation_file" != 'tests/validate.sh' ]]; then
            for rel in "${missing_files[@]}"; do
                if [[ "$rel" == "$validation_file" ]]; then
                    printf "  Fix: create executable %s as declared by base_manifest.yaml.\n" "$rel"
                fi
            done
        fi
        if ((${#missing_files[@]})) && {
            [[ "$validation_file" == 'tests/validate.sh' ]] ||
                ((${#missing_files[@]} > 1)) ||
                [[ "${missing_files[0]}" != "$validation_file" ]]
        }; then
            repo_name="$(basename -- "$path")"
            command=(basectl repo init "$repo_name" --path "$path")
            printf "Run '"
            base_repo_pretty_command "${command[@]}"
            printf "' to create the missing files.\n"
        fi
        return 1
    fi

    printf "Repository baseline: all %d required files present.\n" "$required_count"
    return 0
}

base_repo_check_agent_guidance() {
    local missing_files=()
    local path="$1"
    local rel
    local required_count="${#BASE_REPO_AGENT_GUIDANCE_FILES[@]}"
    local command=()

    for rel in "${BASE_REPO_AGENT_GUIDANCE_FILES[@]}"; do
        if [[ ! -f "$path/$rel" ]]; then
            missing_files+=("$rel")
        fi
    done

    if ((${#missing_files[@]})); then
        printf "Agent guidance: %d of %d files missing.\n" \
            "${#missing_files[@]}" \
            "$required_count"
        for rel in "${missing_files[@]}"; do
            printf "  Missing: %s\n" "$rel"
        done
        command=(basectl repo agent-guidance "$path")
        printf "Run '"
        base_repo_pretty_command "${command[@]}"
        printf "' to create the missing files.\n"
        return 1
    fi

    printf "Agent guidance: all %d files present.\n" "$required_count"
    return 0
}

base_repo_check_agent_ready() {
    local command=()
    local missing_files=()
    local path="$1"
    local rel
    local repo_name
    local required_count="${#BASE_REPO_AGENT_GUIDANCE_FILES[@]}"

    for rel in "${BASE_REPO_AGENT_GUIDANCE_FILES[@]}"; do
        if [[ ! -f "$path/$rel" ]]; then
            missing_files+=("$rel")
        fi
    done

    if ((${#missing_files[@]})); then
        printf "Agent readiness: %d of %d files missing.\n" \
            "${#missing_files[@]}" \
            "$required_count"
        for rel in "${missing_files[@]}"; do
            printf "  Missing: %s\n" "$rel"
        done
        repo_name="$(basename -- "$path")"
        command=(basectl repo init "$repo_name" --path "$path" --agent-ready)
        printf "Run '"
        base_repo_pretty_command "${command[@]}"
        printf "' to create the missing files.\n"
        printf "Existing files are left unchanged.\n"
        return 1
    fi

    printf "Agent readiness: all %d files present.\n" "$required_count"
    return 0
}


base_repo_check_format_error() {
    local output_format="$1"
    local message="$2"

    if [[ "$output_format" == "json" ]]; then
        base_inspection_json_emit_error "repo check" usage_error "$message" '{}'
        return 2
    fi
    base_repo_check_usage_error "$message"
}

base_repo_check_missing_files() {
    local path="$1"
    local rel
    shift

    for rel in "$@"; do
        [[ -f "$path/$rel" ]] || printf '%s\n' "$rel"
    done
}

base_repo_manifest_validation_file_from_python() {
    local manifest_path="$1"
    local python_bin
    local venv_python="${BASE_SETUP_VENV_DIR:-$HOME/.base.d/base/.venv}/bin/python"

    if [[ -x "$venv_python" ]]; then
        python_bin="$venv_python"
    else
        base_std_command_path python_bin python3 || return 1
    fi
    [[ -f "$manifest_path" ]] || return 1
    env BASE_HOME="$BASE_HOME" BASE_PROJECT=base PYTHONPATH="$BASE_HOME/cli/python" \
        "$python_bin" -I "$BASE_HOME/cli/python/base_cli_adapters/module_entrypoint.py" \
        base_projects.manifest_contract "$manifest_path" 2>/dev/null
}

base_repo_manifest_uses_base_test_fallback() {
    local manifest_path="$1"

    [[ -f "$manifest_path" ]] || return 1
    awk '
        function normalize(value) {
            sub(/[[:space:]]+#.*/, "", value)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
            if ((substr(value, 1, 1) == "\"" && substr(value, length(value), 1) == "\"") ||
                (substr(value, 1, 1) == "\047" && substr(value, length(value), 1) == "\047")) {
                value = substr(value, 2, length(value) - 2)
            }
            return value
        }
        $0 ~ /test:[[:space:]]*\{[^}]*command:[[:space:]]*/ {
            value=$0
            sub(/^.*command:[[:space:]]*/, "", value)
            sub(/\}.*/, "", value)
            if (normalize(value) == "\"./bin/base-test\"") found=1
            if (normalize(value) == "\047./bin/base-test\047") found=1
            if (normalize(value) == "./bin/base-test") found=1
        }
        $0 ~ /^test:[[:space:]]*$/ { in_test=1; next }
        in_test && $0 ~ /^[^[:space:]]/ { in_test=0 }
        in_test && $0 ~ /^[[:space:]]+command:[[:space:]]*/ {
            value=$0
            sub(/^.*command:[[:space:]]*/, "", value)
            if (normalize(value) == "./bin/base-test") found=1
        }
        END { exit !found }
    ' "$manifest_path"
}

base_repo_baseline_validation_file() {
    local path="$1"
    local validation_file

    if ! validation_file="$(base_repo_manifest_validation_file_from_python "$path/base_manifest.yaml")"; then
        if base_repo_manifest_uses_base_test_fallback "$path/base_manifest.yaml"; then
            validation_file='bin/base-test'
        else
            validation_file='tests/validate.sh'
        fi
    fi
    case "$validation_file" in
        bin/base-test|tests/validate.sh)
            printf '%s\n' "$validation_file"
            ;;
        *)
            base_std_log_error "Repository manifest selected unsupported validation file '$validation_file'."
            return 1
            ;;
    esac
}

base_repo_required_baseline_files() {
    local path="$1"
    local rel
    local validation_file

    validation_file="$(base_repo_baseline_validation_file "$path")" || return 1
    for rel in "${BASE_REPO_BASELINE_FILES[@]}"; do
        [[ "$rel" == 'tests/validate.sh' ]] && continue
        printf '%s\n' "$rel"
    done
    printf '%s\n' "$validation_file"
}

base_repo_check_json() {
    local path="$1"
    local release_contract="$2"
    local agent_guidance="$3"
    local agent_ready="$4"
    local agent_name agent_status baseline_status envelope_status="ok" release_status
    local baseline_json checks_joined data_json manifest_json missing_json not_executable_json path_json process_json
    local agent_json="" release_json=""
    local check_count=1 failed_count=0 passed_count=0
    local manifest_declared=false process_present=false
    local missing_files=() not_executable_files=() agent_missing_files=() checks_json=()
    local required_files=() required_count present_count validation_file

    validation_file="$(base_repo_baseline_validation_file "$path")" || {
        base_inspection_json_emit_error "repo check" usage_error "Unable to semantically parse repository manifest '$path/base_manifest.yaml'." '{}'
        return 2
    }
    mapfile -t required_files < <(base_repo_required_baseline_files "$path")
    mapfile -t missing_files < <(base_repo_check_missing_files "$path" "${required_files[@]}")
    if [[ -f "$path/$validation_file" && ! -x "$path/$validation_file" ]]; then
        not_executable_files+=("$validation_file")
    fi
    required_count="${#required_files[@]}"
    present_count=$((required_count - ${#missing_files[@]}))
    baseline_status=ok
    if ((${#missing_files[@]} || ${#not_executable_files[@]})); then
        baseline_status=error
        envelope_status=error
        failed_count=$((failed_count + 1))
    else
        passed_count=$((passed_count + 1))
    fi
    missing_json="$(base_inspection_json_string_array "${missing_files[@]}")"
    not_executable_json="$(base_inspection_json_string_array "${not_executable_files[@]}")"
    printf -v baseline_json \
        '{"name":"baseline","status":"%s","required_count":%d,"present_count":%d,"missing_files":%s,"not_executable_files":%s}' \
        "$baseline_status" "$required_count" "$present_count" "$missing_json" "$not_executable_json"
    checks_json+=("$baseline_json")

    if ((release_contract)); then
        check_count=$((check_count + 1))
        [[ -f "$path/base_manifest.yaml" ]] && base_repo_release_manifest_has_key "$path/base_manifest.yaml" && manifest_declared=true
        [[ -f "$path/docs/release-process.md" ]] && process_present=true
        release_status=ok
        if [[ "$manifest_declared" != true || "$process_present" != true ]]; then
            release_status=error
            envelope_status=error
            failed_count=$((failed_count + 1))
        else
            passed_count=$((passed_count + 1))
        fi
        manifest_json="$(base_inspection_json_string "$path/base_manifest.yaml")"
        process_json="$(base_inspection_json_string "$path/docs/release-process.md")"
        printf -v release_json \
            '{"name":"release","status":"%s","manifest_path":%s,"manifest_declared":%s,"process_document_path":%s,"process_document_present":%s}' \
            "$release_status" "$manifest_json" "$manifest_declared" "$process_json" "$process_present"
        checks_json+=("$release_json")
    fi

    if ((agent_ready || agent_guidance)); then
        check_count=$((check_count + 1))
        mapfile -t agent_missing_files < <(base_repo_check_missing_files "$path" "${BASE_REPO_AGENT_GUIDANCE_FILES[@]}")
        required_count="${#BASE_REPO_AGENT_GUIDANCE_FILES[@]}"
        present_count=$((required_count - ${#agent_missing_files[@]}))
        if ((agent_ready)); then
            agent_name=agent_readiness
        else
            agent_name=agent_guidance
        fi
        agent_status=ok
        if ((${#agent_missing_files[@]})); then
            agent_status=error
            envelope_status=error
            failed_count=$((failed_count + 1))
        else
            passed_count=$((passed_count + 1))
        fi
        missing_json="$(base_inspection_json_string_array "${agent_missing_files[@]}")"
        printf -v agent_json \
            '{"name":"%s","status":"%s","required_count":%d,"present_count":%d,"missing_files":%s}' \
            "$agent_name" "$agent_status" "$required_count" "$present_count" "$missing_json"
        checks_json+=("$agent_json")
    fi

    checks_joined="$(IFS=,; printf '%s' "${checks_json[*]}")"
    path_json="$(base_inspection_json_string "$path")"
    printf -v data_json \
        '{"path":%s,"summary":{"checks":%d,"passed":%d,"failed":%d},"checks":[%s]}' \
        "$path_json" "$check_count" "$passed_count" "$failed_count" "$checks_joined"
    base_inspection_json_envelope "repo check" "$envelope_status" "$data_json" null
    [[ "$envelope_status" == "ok" ]]
}

base_repo_check() {
    local agent_guidance=0
    local agent_ready=0
    local output_format="text" requested_format
    local release_contract=0
    local path=""
    local -a parser_args=() positionals=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "agent_guidance|flag|--agent-guidance"
        "agent_ready|flag|--agent-ready"
        "release|flag|--release"
        "format|value|--format"
        "verbose|flag|-v"
    )
    local -A parsed_options=()
    local status=0

    base_inspection_find_output_format output_format "$@"

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_check_usage
                return 0
                ;;
            --agent-guidance|--agent-ready|--release)
                parser_args+=("$1")
                shift
                ;;
            --format)
                [[ -n "${2:-}" ]] || {
                    base_repo_check_format_error "$output_format" "Option '--format' requires an argument."
                    return $?
                }
                requested_format="$2"
                case "$requested_format" in
                    text|json)
                        ;;
                    *)
                        base_repo_check_format_error "$output_format" "Unsupported repo check format '$requested_format'. Expected text or json."
                        return $?
                        ;;
                esac
                parser_args+=("--format=$requested_format")
                output_format="$requested_format"
                shift 2
                ;;
            -v)
                parser_args+=("$1")
                base_std_set_log_level DEBUG
                export BASE_BASH_LIBS_LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_check_format_error "$output_format" "Unknown repo check option '$1'."
                return $?
                ;;
            *)
                parser_args+=("$1")
                shift
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_repo_check_format_error "$output_format" "Could not parse repo check arguments."
        return $?
    fi
    if [[ -n "${parsed_options[format]+set}" ]]; then
        output_format="${parsed_options[format]}"
    fi
    if ((${#positionals[@]} > 1)); then
        base_repo_check_format_error "$output_format" "The 'repo check' command accepts at most one path."
        return $?
    fi

    agent_guidance="${parsed_options[agent_guidance]:-0}"
    agent_ready="${parsed_options[agent_ready]:-0}"
    release_contract="${parsed_options[release]:-0}"
    if ((${#positionals[@]} == 1)); then
        path="${positionals[0]}"
    fi

    [[ -n "$path" ]] || path="."
    path="$(base_repo_target_path "$path")"
    if [[ "$output_format" == "json" ]]; then
        base_repo_check_json "$path" "$release_contract" "$agent_guidance" "$agent_ready"
        return $?
    fi
    base_repo_check_baseline "$path" || status=1
    if ((release_contract)); then
        base_repo_check_release "$path" || status=1
    fi
    if ((agent_ready)); then
        base_repo_check_agent_ready "$path" || status=1
    elif ((agent_guidance)); then
        base_repo_check_agent_guidance "$path" || status=1
    fi
    return "$status"
}

base_repo_configure() {
    local configure_project=1
    local configure_release=0
    local copy_project_fields_from=""
    local dry_run=0
    local github_repo=""
    local initiative_options=()
    local path=""
    local project_owner=""
    local replace_project=0
    local project_schema="base-project"
    local project_title=""
    local protect_default_branch=1
    local -a parser_args=()
    # shellcheck disable=SC2034 # base_arg_parse receives caller-owned arrays by name.
    local -a option_specs=(
        "repo|value|--repo"
        "dry_run|flag|--dry-run"
        "no_protect_default_branch|flag|--no-protect-default-branch"
        "project|value|--project"
        "project_owner|value|--project-owner"
        "project_schema|value|--project-schema"
        "initiative_options|repeatable|--initiative-option"
        "copy_project_fields_from|value|--copy-project-fields-from"
        "replace_project|flag|--replace-project"
        "no_project|flag|--no-project"
        "release|flag|--release"
        "verbose|flag|-v"
    )
    local -a positionals=()
    local -A parsed_options=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_configure_usage
                return 0
                ;;
            --repo|--project|--project-owner|--project-schema|--initiative-option|--copy-project-fields-from)
                [[ -n "${2:-}" ]] || {
                    base_repo_configure_usage_error "Option '$1' requires an argument."
                    return $?
                }
                parser_args+=("$1" "$2")
                shift 2
                ;;
            --repo=*|--project=*|--project-owner=*|--project-schema=*|--initiative-option=*|--copy-project-fields-from=*)
                parser_args+=("$1")
                shift
                ;;
            --dry-run|--no-protect-default-branch|--replace-project|--no-project|--release)
                parser_args+=("$1")
                shift
                ;;
            -v)
                parser_args+=("$1")
                base_std_set_log_level DEBUG
                export BASE_BASH_LIBS_LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_configure_usage_error "Unknown repo configure option '$1'."
                return $?
                ;;
            *)
                parser_args+=("$1")
                shift
                ;;
        esac
    done

    if ! base_arg_parse parsed_options positionals option_specs -- "${parser_args[@]}"; then
        base_repo_configure_usage_error "Could not parse repo configure arguments."
        return $?
    fi
    if ((${#positionals[@]} > 1)); then
        base_repo_configure_usage_error "The 'repo configure' command accepts at most one path."
        return $?
    fi

    github_repo="${parsed_options[repo]:-}"
    dry_run="${parsed_options[dry_run]:-0}"
    protect_default_branch=$((1 - ${parsed_options[no_protect_default_branch]:-0}))
    project_title="${parsed_options[project]:-}"
    project_owner="${parsed_options[project_owner]:-}"
    project_schema="${parsed_options[project_schema]:-base-project}"
    copy_project_fields_from="${parsed_options[copy_project_fields_from]:-}"
    replace_project="${parsed_options[replace_project]:-0}"
    configure_project=$((1 - ${parsed_options[no_project]:-0}))
    configure_release="${parsed_options[release]:-0}"
    if ((${#positionals[@]} == 1)); then
        path="${positionals[0]}"
    fi

    [[ -n "$path" ]] || path="."
    path="$(base_repo_target_path "$path")"
    if [[ -z "$github_repo" ]]; then
        github_repo="$(base_repo_infer_github_repo "$path" || true)"
    fi
    [[ -n "$github_repo" ]] || {
        base_std_log_error "Unable to infer GitHub repository from '$path'."
        printf "       Inference requires a git remote named 'origin' that points to github.com.\n" >&2
        printf "       Pass --repo <owner/name> to configure explicitly, or run:\n" >&2
        printf "         git -C %s remote -v\n" "$(base_repo_pretty_arg "$path")" >&2
        printf "       to inspect the current remotes.\n" >&2
        return 1
    }

    if ((configure_release)); then
        base_repo_configure_release "$dry_run" "$github_repo" "$path" || return 1
    fi
    base_repo_write_issue_branch_policy_workflow "$dry_run" "$path" || return 1
    if ((configure_project)); then
        base_repo_write_project_support_files "$dry_run" "$path" || return 1
    fi

    base_repo_load_github_settings || return 1
    base_repo_configure_github "$dry_run" "$github_repo" "$protect_default_branch" "$path" || return 1
    if ((configure_project)); then
        [[ -n "$project_title" ]] || project_title="$(base_repo_default_project_title "$github_repo")"
        [[ -n "$project_owner" ]] || project_owner="$(base_repo_project_owner_from_repo "$github_repo")"
        base_repo_configure_project_metadata \
            "$dry_run" \
            "$github_repo" \
            "$project_title" \
            "$project_owner" \
            "$project_schema" \
            "$(base_repo_project_config_path "$path")" \
            "$copy_project_fields_from" \
            "$replace_project" \
            "${initiative_options[@]}" || return 1
    fi

    if [[ "$dry_run" != "1" ]]; then
        printf "Configuration complete.\n"
    fi
}

base_repo_subcommand_main() {
    local repo_command="${1:-}"

    case "$repo_command" in
        -h|--help|help|"")
            base_repo_subcommand_usage
            return 0
            ;;
        init)
            shift
            base_repo_load_init || return 1
            base_repo_init "$@"
            ;;
        clone)
            shift
            base_repo_load_clone || return 1
            base_repo_clone "$@"
            ;;
        check)
            shift
            base_repo_check "$@"
            ;;
        configure)
            shift
            base_repo_configure "$@"
            ;;
        agent-guidance)
            shift
            base_repo_load_agent_guidance || return 1
            base_repo_agent_guidance "$@"
            ;;
        installer-template)
            shift
            base_repo_load_installer_template || return 1
            base_repo_installer_template "$@"
            ;;
        *)
            base_repo_usage_error "Unknown repo command '$repo_command'."
            ;;
    esac
}
