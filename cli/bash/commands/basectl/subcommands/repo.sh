#!/usr/bin/env bash

[[ -n "${_base_repo_subcommand_sourced:-}" ]] && return
_base_repo_subcommand_sourced=1
readonly _base_repo_subcommand_sourced

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
  configure            Apply GitHub settings, labels, branch protection, and Project metadata.
  agent-guidance       Seed optional repo-local agent guidance files.
  installer-template   Print or write the maintained project installer template.

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
  --pr                          Commit the generated baseline on a branch and open a pull request.
  --description <text>          Repository description for generated README.
  --copyright-holder <name>     Copyright holder for generated AGPL license. Defaults to git config user.name.
  --private                     Create a private GitHub repository when needed. This is the default.
  --public                      Create a public GitHub repository when needed.
  --no-configure                Skip GitHub configuration during repo init.
  --no-protect-default-branch   Skip Base-managed default branch protection during repo configure.
  --project <title>             GitHub Project title to configure. Defaults to the repository name.
  --project-owner <login>       GitHub Project owner. Defaults to the repository owner.
  --project-schema <schema>     Project metadata schema. Defaults to base-roadmap.
  --initiative-option <name>    Initiative option to seed. May be repeated.
  --copy-project-fields-from <title>
                                Copy missing Project item field values from another Project.
  --no-project                  Skip GitHub Project metadata configuration.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Examples:
  basectl repo init bankbuddy --path . --repo codeforester/bankbuddy --pr
  basectl repo init base-demo --repo codeforester/base-demo --public

Creates the standard Base-managed repository baseline, including
.github/base-project.yml. With --pr, the first run opens a baseline PR when
files change; rerun the same command after merge to continue GitHub-side
configuration.
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
  basectl repo clone banyanlabs --owner codeforester
  basectl repo clone codeforester/bankbuddy
  basectl repo clone codeforester/base --path ~/work/base

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
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Verifies the standard Base-managed repository baseline at path, or the current
directory when path is omitted.
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
  --project-schema <schema>     Project metadata schema. Defaults to base-roadmap.
  --initiative-option <name>    Initiative option to seed. May be repeated.
  --copy-project-fields-from <title>
                                Copy missing Project item field values from another Project.
  --no-project                  Skip GitHub Project metadata configuration.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Applies GitHub-side repository settings, labels, branch protection, and
repo Project metadata. When .github/base-project.yml exists, repo configure
uses it for repo-specific GitHub Project taxonomy and issue defaults.
EOF
}

base_repo_installer_template_usage() {
    cat <<'EOF'
Usage:
  basectl repo installer-template [path] [options]

Options:
  --repo <owner/name>           GitHub repository for --pr. Defaults to the target origin remote.
  --pr                          Commit the generated installer template on a branch and open a draft pull request.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Prints the maintained project installer template, or writes it to path when a
path is provided. With --pr, path is required.
EOF
}

base_repo_usage_error() {
    base_repo_subcommand_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_repo_init_usage_error() {
    base_repo_init_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_repo_clone_usage_error() {
    base_repo_clone_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_repo_check_usage_error() {
    base_repo_check_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_repo_configure_usage_error() {
    base_repo_configure_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_repo_installer_template_usage_error() {
    base_repo_installer_template_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_repo_agent_guidance_usage() {
    cat <<'EOF'
Usage:
  basectl repo agent-guidance [path] [options]

Options:
  --repo <owner/name>           GitHub repository for --pr. Defaults to the target origin remote.
  --repo-name <name>            Repository name for generated agent guidance. Defaults to the target path basename.
  --default-branch <name>       Default branch for generated agent guidance. Defaults to main.
  --validation-command <cmd>    Validation command for generated agent guidance. Defaults to ./tests/validate.sh.
  --pr                          Commit generated guidance files on a branch and open a draft pull request.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Create optional repo-local agent guidance files for a Base-managed repository.
EOF
}

base_repo_agent_guidance_usage_error() {
    base_repo_agent_guidance_usage >&2
    printf 'ERROR: %s\n' "$*" >&2
    return 2
}

base_repo_default_description() {
    local name="$1"

    printf 'Base-managed project %s.\n' "$name"
}

base_repo_default_copyright_holder() {
    local holder=""

    holder="$(git config --global user.name 2>/dev/null || true)"
    if [[ -z "$holder" ]]; then
        holder="$(id -un 2>/dev/null || true)"
    fi
    if [[ -z "$holder" ]]; then
        holder="Unknown"
    fi

    printf '%s\n' "$holder"
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

    value="${value%%#*}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    case "$value" in
        \"*\")
            value="${value#\"}"
            value="${value%\"}"
            ;;
        \'*\')
            value="${value#\'}"
            value="${value%\'}"
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
            value="$(base_repo_strip_config_value "${BASH_REMATCH[1]}")"
            [[ -n "$value" ]] || {
                log_error "$config_path: workspace.root must be a non-empty path."
                return 2
            }
            value="$(base_repo_expand_path "$value")"
            [[ "$value" = /* ]] || {
                log_error "$config_path: workspace.root must be an absolute path or start with '~'."
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
            value="$(base_repo_strip_config_value "${BASH_REMATCH[1]}")"
            [[ -n "$value" ]] || {
                log_error "$config_path: github.$key must be a non-empty value."
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
        log_error "BASE_HOME is required to resolve the default repository path."
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
            log_error "$HOME/.base.d/config.yaml: github.clone_protocol must be 'ssh' or 'https'."
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

base_repo_baseline_year() {
    date +%Y
}

base_repo_create_directory() {
    local target_dir="$1"

    [[ -d "$target_dir" ]] && return 0

    if mkdir -p "$target_dir" 2>/dev/null; then
        return 0
    fi

    log_error "Failed to create parent directory '$target_dir'."
    return 1
}

base_repo_write_stream() {
    local dry_run="$1"
    local target="$2"
    local target_dir

    if [[ -e "$target" ]]; then
        log_info "File already exists at '$target'; leaving it unchanged."
        return 0
    fi

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create '%s'.\n" "$target"
        return 0
    fi

    target_dir="$(dirname -- "$target")"
    base_repo_create_directory "$target_dir" || return 1
    if ! cat 2>/dev/null > "$target"; then
        log_error "Failed to write '$target'."
        return 1
    fi
    printf "Created '%s'.\n" "$target"
}

base_repo_write_executable_stream() {
    local dry_run="$1"
    local target="$2"
    local target_dir

    if [[ -e "$target" ]]; then
        log_info "File already exists at '$target'; leaving it unchanged."
        return 0
    fi

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create executable '%s'.\n" "$target"
        return 0
    fi

    target_dir="$(dirname -- "$target")"
    base_repo_create_directory "$target_dir" || return 1
    if ! cat 2>/dev/null > "$target"; then
        log_error "Failed to write '$target'."
        return 1
    fi
    if ! chmod +x "$target" 2>/dev/null; then
        log_error "Failed to make '$target' executable."
        return 1
    fi
    printf "Created executable '%s'.\n" "$target"
}

base_repo_print_review_hint() {
    local target_dir="$1"

    printf "Run git -C '%s' status --short to review changes.\n" "$target_dir"
}

base_repo_installer_template_path() {
    [[ -n "${BASE_HOME:-}" ]] || {
        log_error "BASE_HOME is required to locate the project installer template."
        return 1
    }

    printf '%s/templates/project-install.sh\n' "$BASE_HOME"
}

base_repo_print_installer_template() {
    local template

    template="$(base_repo_installer_template_path)" || return 1
    [[ -f "$template" ]] || {
        log_error "Project installer template was not found at '$template'."
        return 1
    }

    cat "$template"
}

base_repo_write_installer_template() {
    local dry_run="$1"
    local target="$2"
    local template

    template="$(base_repo_installer_template_path)" || return 1
    [[ -f "$template" ]] || {
        log_error "Project installer template was not found at '$template'."
        return 1
    }

    base_repo_write_executable_stream "$dry_run" "$target" < "$template"
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

This repository is managed by [Base](https://github.com/codeforester/base).

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
2. Use one of the standard issue labels: \`bug\`, \`enhancement\`,
   \`documentation\`, \`ci\`, or \`security\`.
3. Create an issue-backed branch:

   \`\`\`text
   <category>/<issue>-<YYYYMMDD>-<slug>
   \`\`\`

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

base_repo_write_pull_request_template() {
    local dry_run="$1"
    local root="$2"

    base_repo_write_stream "$dry_run" "$root/.github/pull_request_template.md" <<'EOF'
## Summary

<!-- What changed and why. Focus on decisions and user impact, not just the diff. -->

## Issue

Closes #

## Validation

<!-- Commands run and relevant output. Include narrow checks and any broader suite used. -->

## Notes

<!-- Optional: tradeoffs, follow-up work, or reviewer context. -->

## Checklist

- [ ] Branch name follows `<category>/<issue>-<YYYYMMDD>-<slug>`.
- [ ] Pull request is scoped to one issue, unless a documented multi-issue exception applies.
- [ ] Pull request body explains what changed and how it was validated.
- [ ] Relevant project checks pass.
- [ ] Documentation is updated when behavior or user-facing commands change.
- [ ] CHANGELOG is updated for notable user-visible or release-worthy changes.
- [ ] Pull request includes `Fixes #<issue>` or `Closes #<issue>` when merge should close the issue.
EOF
}

base_repo_write_agent_instructions() {
    local default_branch="$3"
    local dry_run="$1"
    local repo_name="$2"
    local root="$5"
    local validation_command="$4"

    base_repo_write_stream "$dry_run" "$root/AGENTS.md" <<EOF
# Agent Instructions for $repo_name

Use this file for repository-local agent guidance. User instructions still take
precedence over this baseline.

## Workflow

1. Create or choose a GitHub issue before implementation work.
2. Use one standard issue label: \`bug\`, \`enhancement\`, \`documentation\`,
   \`ci\`, or \`security\`.
3. Branch from the issue with:

   \`\`\`text
   <category>/<issue>-<YYYYMMDD>-<slug>
   \`\`\`

4. Use a dedicated worktree for each pull request:

   \`\`\`bash
   git fetch origin
   git worktree add -b <branch> ../$repo_name-worktrees/<slug> origin/$default_branch
   \`\`\`

5. Keep the pull request scoped to the issue and link it with
   \`Fixes #<issue>\` or \`Closes #<issue>\` when merge should close the issue.
6. Preserve existing user changes. Do not overwrite project-owned files unless
   the user explicitly asks for that edit.

## Validation

Run the project validation command before publishing changes:

   \`\`\`bash
   $validation_command
   \`\`\`

Also run narrower tests for the files changed when available.

## Documentation

Update docs when behavior, commands, setup, or workflow expectations change.
Update \`CHANGELOG.md\` only for notable user-visible or release-worthy changes.

## Finish

After merge, sync $default_branch, remove the worktree, and delete merged local
and remote branches when safe.
EOF
}

base_repo_write_agent_skills() {
    local dry_run="$1"
    local repo_name="$2"
    local root="$3"

    base_repo_write_stream "$dry_run" "$root/skills.md" <<EOF
# Project Skills for $repo_name

Use this file as the repo-local index for project-specific agent workflows.
Keep entries short, concrete, and owned by this repository.

## Suggested Entries

- Development workflow: issue selection, branch naming, validation, PR creation,
  merge, and cleanup.
- Testing workflow: the commands that prove common changes are safe.
- Release workflow: version, changelog, tag, release, and package manager steps.
- Domain workflow: product-specific checks or demo expectations that agents
  should not have to rediscover.

## Boundaries

Do not vendor third-party methodology files here. Link to external guidance or
copy only repo-owned instructions that the project intends to maintain.
EOF
}

base_repo_write_agent_pull_request_template() {
    local dry_run="$1"
    local root="$2"

    base_repo_write_stream "$dry_run" "$root/.github/pull_request_template.md" <<'EOF'
## Summary

<!-- What changed and why. Focus on decisions and user impact, not just the diff. -->

## Issue

Closes #

## Validation

<!-- Commands run and relevant output. Include narrow checks and any broader suite used. -->

## Reviewer Notes

<!-- Optional: tradeoffs, follow-up work, or areas where reviewer attention would help. -->

## Checklist

- [ ] Branch name follows `<category>/<issue>-<YYYYMMDD>-<slug>`.
- [ ] Pull request is scoped to one issue, unless a documented multi-issue exception applies.
- [ ] Pull request body explains what changed and how it was validated.
- [ ] Relevant project checks pass.
- [ ] Documentation is updated when behavior or user-facing commands change.
- [ ] CHANGELOG is updated for notable user-visible or release-worthy changes.
- [ ] Pull request includes `Fixes #<issue>` or `Closes #<issue>` when merge should close the issue.
EOF
}

base_repo_write_agent_guidance() {
    local default_branch="$3"
    local dry_run="$1"
    local repo_name="$2"
    local root="$5"
    local status=0
    local validation_command="$4"

    base_repo_write_agent_instructions "$dry_run" "$repo_name" "$default_branch" "$validation_command" "$root" || status=1
    base_repo_write_agent_skills "$dry_run" "$repo_name" "$root" || status=1
    base_repo_write_agent_pull_request_template "$dry_run" "$root" || status=1

    return "$status"
}

base_repo_agpl_license_text() {
    local source_license="$1"

    awk '
        /^[[:space:]]*GNU AFFERO GENERAL PUBLIC LICENSE$/ { found = 1 }
        found { print }
        END { if (!found) exit 1 }
    ' "$source_license"
}

base_repo_write_license() {
    local canonical_license
    local copyright_holder="$2"
    local dry_run="$1"
    local root="$3"
    local source_license="${BASE_HOME:-}/LICENSE"
    local year

    [[ -f "$source_license" ]] || {
        log_error "Base AGPL license text '$source_license' was not found."
        return 1
    }

    canonical_license="$(base_repo_agpl_license_text "$source_license")" || {
        log_error "Base AGPL license text '$source_license' did not contain the canonical AGPL terms."
        return 1
    }

    year="$(base_repo_baseline_year)"
    {
        cat <<EOF
Copyright (C) $year $copyright_holder

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along
with this program. If not, see <https://www.gnu.org/licenses/>.
EOF
        printf '\n'
        printf '%s\n' "$canonical_license"
    } | base_repo_write_stream "$dry_run" "$root/LICENSE"
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

    base_repo_write_stream "$dry_run" "$root/base_manifest.yaml" <<EOF
schema_version: 1

project:
  name: $name

test:
  command: ./tests/validate.sh
EOF
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

jobs:
  validate:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate repository baseline
        run: ./tests/validate.sh
EOF
}

base_repo_write_project_intake_workflow() {
    local dry_run="$1"
    local root="$2"

    base_repo_write_stream "$dry_run" "$root/.github/workflows/project-intake.yml" <<'EOF'
name: Project Intake

on:
  issues:
    types: [opened, reopened, closed]
  workflow_dispatch:
    inputs:
      issue_number:
        description: Issue number to reconcile into the repo Project.
        required: true
        type: string

permissions:
  contents: read
  issues: read

jobs:
  sync:
    name: Sync issue Project fields
    runs-on: ubuntu-latest
    env:
      BASE_PROJECT_OWNER: ${{ github.repository_owner }}
      BASE_PROJECT_TITLE: ${{ github.event.repository.name }}
      BASE_PROJECT_ISSUE_NUMBER: ${{ github.event.issue.number || inputs.issue_number }}
      BASE_PROJECT_DEFAULT_OPEN_STATUS: Backlog
      BASE_PROJECT_DEFAULT_CLOSED_STATUS: Done
      BASE_PROJECT_DEFAULT_PRIORITY: P2
      BASE_PROJECT_DEFAULT_SIZE: S
      BASE_PROJECT_DEFAULT_AREA: Product
      BASE_PROJECT_DEFAULT_INITIATIVE: Adoption Polish
      GH_TOKEN: ${{ secrets.BASE_PROJECT_TOKEN || github.token }}
    steps:
      - name: Reconcile Project item
        shell: bash
        run: |
          set -euo pipefail

          issue_number="${BASE_PROJECT_ISSUE_NUMBER:-}"
          if [[ -z "$issue_number" ]]; then
            echo "::error::Issue number was not provided by the event or workflow_dispatch input."
            exit 1
          fi

          issue_json="$(gh issue view "$issue_number" --repo "$GITHUB_REPOSITORY" --json state,url)"
          issue_state="$(jq -r '.state' <<<"$issue_json")"
          issue_url="$(jq -r '.url' <<<"$issue_json")"

          project_number="$(
            gh project list --owner "$BASE_PROJECT_OWNER" --format json --limit 100 |
              jq -r --arg title "$BASE_PROJECT_TITLE" \
                '.projects[] | select(.title == $title) | .number' |
              head -n 1
          )"
          if [[ -z "$project_number" ]]; then
            echo "::error::GitHub Project '$BASE_PROJECT_TITLE' was not found for owner '$BASE_PROJECT_OWNER'."
            exit 1
          fi

          project_id="$(gh project view "$project_number" --owner "$BASE_PROJECT_OWNER" --format json --jq '.id')"
          item_id="$(gh project item-add "$project_number" --owner "$BASE_PROJECT_OWNER" --url "$issue_url" --format json --jq '.id')"
          item_json="$(
            gh project item-list "$project_number" --owner "$BASE_PROJECT_OWNER" --format json --limit 1000 |
              jq --arg id "$item_id" '.items[] | select(.id == $id)'
          )"
          fields_json="$(gh project field-list "$project_number" --owner "$BASE_PROJECT_OWNER" --format json)"

          field_id_for() {
            local field_name="$1"

            jq -r --arg name "$field_name" \
              '.fields[] | select(.name == $name) | .id' <<<"$fields_json" |
              head -n 1
          }

          option_id_for() {
            local field_name="$1"
            local option_name="$2"

            jq -r --arg name "$field_name" --arg option "$option_name" \
              '.fields[] | select(.name == $name) | .options[]? | select(.name == $option) | .id' \
              <<<"$fields_json" |
              head -n 1
          }

          set_single_select() {
            local field_name="$1"
            local option_name="$2"
            local field_id
            local option_id

            [[ -n "$option_name" ]] || return 0

            field_id="$(field_id_for "$field_name")"
            option_id="$(option_id_for "$field_name" "$option_name")"
            if [[ -z "$field_id" || -z "$option_id" ]]; then
              echo "::error::Project field '$field_name' option '$option_name' was not found."
              exit 1
            fi

            gh project item-edit \
              --id "$item_id" \
              --project-id "$project_id" \
              --field-id "$field_id" \
              --single-select-option-id "$option_id" \
              >/dev/null
          }

          set_single_select_if_missing() {
            local field_name="$1"
            local item_key="$2"
            local option_name="$3"
            local current_value

            current_value="$(jq -r --arg key "$item_key" '.[$key] // ""' <<<"$item_json")"
            if [[ -n "$current_value" ]]; then
              return 0
            fi

            set_single_select "$field_name" "$option_name"
          }

          status_value="$BASE_PROJECT_DEFAULT_OPEN_STATUS"
          if [[ "$issue_state" == "CLOSED" ]]; then
            status_value="$BASE_PROJECT_DEFAULT_CLOSED_STATUS"
          fi

          set_single_select Status "$status_value"
          set_single_select_if_missing Priority priority "$BASE_PROJECT_DEFAULT_PRIORITY"
          set_single_select_if_missing Size size "$BASE_PROJECT_DEFAULT_SIZE"
          set_single_select_if_missing Area area "$BASE_PROJECT_DEFAULT_AREA"
          set_single_select_if_missing Initiative initiative "$BASE_PROJECT_DEFAULT_INITIATIVE"

          printf 'Synced issue #%s into Project %s.\n' "$issue_number" "$BASE_PROJECT_TITLE"
EOF
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
    local copyright_holder="$4"
    local description="$3"
    local dry_run="$1"
    local name="$2"
    local root="$5"
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
    base_repo_write_license "$dry_run" "$copyright_holder" "$root" || status=1
    base_repo_write_gitignore "$dry_run" "$root" || status=1
    base_repo_write_manifest "$dry_run" "$name" "$root" || status=1
    base_repo_write_validate_script "$dry_run" "$root" || status=1
    base_repo_write_project_intake_workflow "$dry_run" "$root" || status=1
    base_repo_write_tests_workflow "$dry_run" "$root" || status=1

    return "$status"
}

base_repo_infer_github_repo() {
    local path="$1"
    local remote_url

    remote_url="$(git -C "$path" remote get-url origin 2>/dev/null || true)"
    [[ -n "$remote_url" ]] || return 1

    case "$remote_url" in
        git@github.com:*.git)
            remote_url="${remote_url#git@github.com:}"
            remote_url="${remote_url%.git}"
            ;;
        git@github.com:*)
            remote_url="${remote_url#git@github.com:}"
            ;;
        https://github.com/*.git)
            remote_url="${remote_url#https://github.com/}"
            remote_url="${remote_url%.git}"
            ;;
        https://github.com/*)
            remote_url="${remote_url#https://github.com/}"
            ;;
        *)
            return 1
            ;;
    esac

    [[ "$remote_url" == */* ]] || return 1
    printf '%s\n' "$remote_url"
}

base_repo_require_gh() {
    command -v gh >/dev/null 2>&1 || {
        log_error "GitHub CLI 'gh' is required for repository configuration."
        return 1
    }
    gh auth status -h github.com >/dev/null 2>&1 || {
        log_error "GitHub CLI authentication is not ready."
        log_error "Run 'gh auth login -h github.com' and retry."
        return 1
    }
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

base_repo_configure_label() {
    local color="$3"
    local description="$4"
    local dry_run="$1"
    local label="$2"
    local repo="$5"
    local quoted_description

    if [[ "$dry_run" == "1" ]]; then
        quoted_description="$(base_repo_pretty_quote "$description")"
        printf "[DRY-RUN] Would run: gh label create %s --repo %s --color %s --description %s --force\n" \
            "$label" "$repo" "$color" "$quoted_description"
        return 0
    fi

    gh label create "$label" --repo "$repo" --color "$color" --description "$description" --force
}

base_repo_ensure_github_repo() {
    local description="$3"
    local dry_run="$1"
    local repo="$2"
    local visibility="$4"

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create %s GitHub repository '%s' if it does not already exist.\n" "$visibility" "$repo"
        return 0
    fi

    base_repo_require_gh || return 1
    if gh repo view "$repo" >/dev/null 2>&1; then
        log_info "GitHub repository '$repo' already exists."
        return 0
    fi

    log_info "Creating $visibility GitHub repository '$repo'."
    gh repo create "$repo" "--$visibility" --description "$description"
}

base_repo_default_branch_ruleset_payload() {
    cat <<'JSON'
{"name":"Base default branch protection","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"allowed_merge_methods":["squash"],"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_approving_review_count":0,"required_review_thread_resolution":false}},{"type":"deletion"},{"type":"non_fast_forward"}]}
JSON
}

base_repo_rulesets_plan_gated_error() {
    local message="$1"

    [[ "$message" == *"Upgrade to GitHub Pro"* ]] &&
        [[ "$message" == *"make this repository public"* ]] &&
        [[ "$message" == *"(HTTP 403)"* ]]
}

base_repo_configure_default_branch_protection() {
    local dry_run="$1"
    local payload
    local repo="$2"
    local ruleset_lookup_output=""
    local ruleset_id=""

    payload="$(base_repo_default_branch_ruleset_payload)"

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create or update GitHub ruleset 'Base default branch protection' on '%s' targeting '~DEFAULT_BRANCH'.\n" "$repo"
        printf "[DRY-RUN] Would run: gh api repos/%s/rulesets --jq %s\n" \
            "$repo" \
            "$(base_repo_pretty_quote 'map(select(.name == "Base default branch protection" and .source_type == "Repository")) | .[0].id // ""')"
        printf "[DRY-RUN] Would run: gh api repos/%s/rulesets --method POST --input -\n" "$repo"
        printf "[DRY-RUN] Payload: %s\n" "$payload"
        return 0
    fi

    base_repo_require_gh || return 1
    ruleset_lookup_output="$(gh api "repos/$repo/rulesets" \
        --jq 'map(select(.name == "Base default branch protection" and .source_type == "Repository")) | .[0].id // ""' 2>&1)" || {
        if base_repo_rulesets_plan_gated_error "$ruleset_lookup_output"; then
            log_warn "Default branch protection skipped for '$repo'."
            log_warn "$ruleset_lookup_output"
            return 0
        fi
        [[ -z "$ruleset_lookup_output" ]] || log_error "$ruleset_lookup_output"
        log_error "Unable to inspect GitHub rulesets for '$repo'."
        return 1
    }
    ruleset_id="$ruleset_lookup_output"

    if [[ -n "$ruleset_id" ]]; then
        printf '%s\n' "$payload" | gh api "repos/$repo/rulesets/$ruleset_id" --method PUT --input - || {
            log_error "Unable to update Base default branch protection ruleset for '$repo'."
            return 1
        }
    else
        printf '%s\n' "$payload" | gh api "repos/$repo/rulesets" --method POST --input - || {
            log_error "Unable to create Base default branch protection ruleset for '$repo'."
            return 1
        }
    fi
}

base_repo_title_case_name() {
    local name="$1"

    printf '%s\n' "$name" |
        tr '._-' '   ' |
        awk '{ for (i = 1; i <= NF; i++) { $i = toupper(substr($i, 1, 1)) substr($i, 2) } print }'
}

base_repo_default_project_title() {
    local repo="$1"

    printf '%s\n' "${repo#*/}"
}

base_repo_project_owner_from_repo() {
    local repo="$1"

    printf '%s\n' "${repo%%/*}"
}

base_repo_project_config_path() {
    local root="$1"
    local path="$root/.github/base-project.yml"

    if [[ -f "$path" ]]; then
        printf '%s\n' "$path"
    fi
}

base_repo_configure_project_metadata() {
    local dry_run="$1"
    local config_path="$6"
    local copy_fields_from_project="$7"
    local option
    local owner="$4"
    local output=""
    local project_title="$3"
    local repo="$2"
    local schema="$5"
    local status=0
    local wrapper="${BASE_REPO_PROJECT_WRAPPER:-$BASE_HOME/bin/base-wrapper}"
    shift 7

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would configure GitHub Project '%s' for '%s'.\n" "$project_title" "$repo"
        printf "[DRY-RUN] Would copy GitHub Project 'base-project-template' to '%s' if missing.\n" "$project_title"
        printf "[DRY-RUN] Would link GitHub Project '%s' to repository '%s'.\n" "$project_title" "$repo"
        printf "[DRY-RUN] Would backfill issues from '%s' into GitHub Project '%s'.\n" "$repo" "$project_title"
        if [[ -n "$config_path" ]]; then
            printf "[DRY-RUN] Would read GitHub Project config from '%s'.\n" "$config_path"
            printf "[DRY-RUN] Would apply issue defaults from '%s' to missing Project item fields.\n" "$config_path"
        fi
        if [[ -n "$copy_fields_from_project" ]]; then
            printf "[DRY-RUN] Would copy missing Project item field values from '%s' into '%s'.\n" \
                "$copy_fields_from_project" \
                "$project_title"
        fi
        printf "[DRY-RUN] Would run: %s --project base base_github_projects project configure --project %s --owner %s --repo %s --schema %s" \
            "$wrapper" \
            "$(base_repo_pretty_arg "$project_title")" \
            "$owner" \
            "$repo" \
            "$schema"
        if [[ -n "$config_path" ]]; then
            printf " --config %s" "$(base_repo_pretty_arg "$config_path")"
        fi
        if [[ -n "$copy_fields_from_project" ]]; then
            printf " --copy-fields-from %s" "$(base_repo_pretty_arg "$copy_fields_from_project")"
        fi
        for option in "$@"; do
            printf " --initiative-option %s" "$(base_repo_pretty_arg "$option")"
        done
        printf "\n"
        printf "[DRY-RUN] Project fields: Status, Priority, Area, Size, Initiative\n"
        return 0
    fi

    [[ -x "$wrapper" ]] || {
        log_error "Base Python wrapper '$wrapper' is missing or is not executable."
        return 1
    }

    local command=(
        "$wrapper"
        --project base
        base_github_projects
        project
        configure
        --project "$project_title"
        --owner "$owner"
        --repo "$repo"
        --schema "$schema"
    )
    if [[ -n "$config_path" ]]; then
        command+=(--config "$config_path")
    fi
    if [[ -n "$copy_fields_from_project" ]]; then
        command+=(--copy-fields-from "$copy_fields_from_project")
    fi
    for option in "$@"; do
        command+=(--initiative-option "$option")
    done

    log_info "Configuring GitHub Project '$project_title' for '$repo'."
    log_info "Running: $(base_repo_pretty_command "${command[@]}")"
    output="$("${command[@]}" 2>&1)" || status=$?
    if [[ "$status" -eq 0 ]]; then
        [[ -z "$output" ]] || printf '%s\n' "$output"
        return 0
    fi
    if [[ "$status" -eq 3 ]]; then
        log_warn "GitHub Project metadata skipped for '$repo'."
        [[ -z "$output" ]] || log_warn "$output"
        return 0
    fi

    [[ -z "$output" ]] || log_error "$output"
    log_error "Unable to configure GitHub Project metadata for '$repo'."
    return 1
}

base_repo_configure_github() {
    local dry_run="$1"
    local protect_default_branch="${3:-1}"
    local repo="$2"
    local status=0

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would run: gh repo edit %s --enable-issues --enable-projects --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge --squash-merge-commit-message pr-title-description\n" "$repo"
    else
        base_repo_require_gh || return 1
        gh repo edit "$repo" \
            --enable-issues \
            --enable-projects \
            --enable-squash-merge \
            --enable-merge-commit=false \
            --enable-rebase-merge=false \
            --delete-branch-on-merge \
            --squash-merge-commit-message pr-title-description || return 1
    fi

    base_repo_configure_label "$dry_run" bug "d73a4a" "Something is not working" "$repo" || status=1
    base_repo_configure_label "$dry_run" enhancement "a2eeef" "New feature or product improvement" "$repo" || status=1
    base_repo_configure_label "$dry_run" documentation "0075ca" "Documentation improvements" "$repo" || status=1
    base_repo_configure_label "$dry_run" ci "0e8a16" "Continuous integration, tests, automation, or release workflows" "$repo" || status=1
    base_repo_configure_label "$dry_run" security "ee0701" "Security hardening or vulnerability work" "$repo" || status=1
    base_repo_configure_label "$dry_run" needs-demo "fbca04" "Change should update a project demo" "$repo" || status=1
    if [[ "$protect_default_branch" == "1" ]]; then
        base_repo_configure_default_branch_protection "$dry_run" "$repo" || status=1
    fi

    return "$status"
}

base_repo_pr_branch_name() {
    local name="$1"

    printf 'base/repo-baseline-%s\n' "$name"
}

base_repo_helper_pr_branch_name() {
    local kind="$1"
    local name="$2"

    printf 'base/%s-%s\n' "$kind" "$name"
}

base_repo_require_pr_worktree() {
    local command_label="${2:-repo init --pr}"
    local git_root
    local root="$1"

    [[ -d "$root" ]] || {
        log_error "$command_label requires '$root' to be an existing Git worktree."
        return 1
    }

    git_root="$(git -C "$root" rev-parse --show-toplevel 2>/dev/null)" || {
        log_error "$command_label requires '$root' to be an existing Git worktree."
        return 1
    }
    git_root="$(cd -- "$git_root" && pwd -P)" || return 1
    root="$(cd -- "$root" && pwd -P)" || return 1

    [[ "$git_root" == "$root" ]] || {
        if [[ "$command_label" == "repo init --pr" ]]; then
            log_error "repo init --pr expects --path to point at the repository root."
        else
            log_error "$command_label expects the target path to point at the repository root."
        fi
        return 1
    }

    [[ -z "$(git -C "$root" status --porcelain)" ]] || {
        log_error "$command_label requires a clean Git worktree at '$root'."
        return 1
    }
}

base_repo_default_branch_for_pr() {
    local default_branch
    local repo="$1"

    base_repo_require_gh || return 1
    default_branch="$(gh repo view "$repo" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null)" || {
        log_error "Unable to determine the default branch for GitHub repository '$repo'."
        return 1
    }
    [[ -n "$default_branch" ]] || {
        log_error "GitHub repository '$repo' does not report a default branch."
        return 1
    }

    printf '%s\n' "$default_branch"
}

base_repo_prepare_pr_branch() {
    local branch="$3"
    local command_label="${5:-repo init --pr}"
    local default_branch="$4"
    local dry_run="$1"
    local root="$2"
    local start_point

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create or use branch '%s' from default branch '%s'.\n" "$branch" "$default_branch"
        return 0
    fi

    if git -C "$root" show-ref --verify --quiet "refs/heads/$branch"; then
        git -C "$root" switch "$branch" || {
            log_error "Failed to switch to branch '$branch'."
            return 1
        }
    else
        if git -C "$root" show-ref --verify --quiet "refs/heads/$default_branch"; then
            start_point="$default_branch"
        elif git -C "$root" show-ref --verify --quiet "refs/remotes/origin/$default_branch"; then
            start_point="origin/$default_branch"
        else
            log_error "Unable to find default branch '$default_branch' in '$root'."
            return 1
        fi

        git -C "$root" switch -c "$branch" "$start_point" || {
            log_error "Failed to create branch '$branch'."
            return 1
        }
    fi

    [[ -z "$(git -C "$root" status --porcelain)" ]] || {
        log_error "$command_label requires branch '$branch' to have a clean Git worktree."
        return 1
    }
}

base_repo_stage_pr_files() {
    local description="$2"
    local files=()
    local rel
    local root="$1"
    shift 2

    for rel in "$@"; do
        [[ -e "$root/$rel" ]] && files+=("$rel")
    done

    ((${#files[@]})) || {
        log_error "No $description exist to stage."
        return 1
    }

    git -C "$root" add -- "${files[@]}" || {
        log_error "Failed to stage $description."
        return 1
    }
}

base_repo_stage_pr_baseline_files() {
    local root="$1"

    base_repo_stage_pr_files "$root" "repository baseline files" "${BASE_REPO_BASELINE_FILES[@]}"
}

base_repo_relative_path_under_root() {
    local path="$2"
    local path_dir
    local path_real
    local root="$1"
    local root_real

    root_real="$(cd -- "$root" && pwd -P)" || return 1
    path_dir="$(dirname -- "$path")"
    [[ -d "$path_dir" ]] || return 1
    path_real="$(cd -- "$path_dir" && pwd -P)/$(basename -- "$path")" || return 1

    case "$path_real" in
        "$root_real"/*)
            printf '%s\n' "${path_real#"$root_real"/}"
            ;;
        *)
            return 1
            ;;
    esac
}

base_repo_finish_generated_pr() {
    local body_file="$9"
    local branch="$4"
    local commit_message="$6"
    local default_branch="$5"
    local dry_run="$1"
    local file_description="$7"
    local pr_title="$8"
    local repo="$3"
    local root="$2"
    shift 9

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would commit generated %s with message '%s'.\n" "$file_description" "$commit_message"
        printf "[DRY-RUN] Would push branch '%s' to origin.\n" "$branch"
        printf "[DRY-RUN] Would open a draft pull request in '%s' from '%s' to '%s' with title '%s'.\n" \
            "$repo" "$branch" "$default_branch" "$pr_title"
        return 0
    fi

    base_repo_stage_pr_files "$root" "$file_description" "$@" || return 1
    if git -C "$root" diff --cached --quiet --; then
        log_info "No $file_description changes to commit; skipping pull request creation."
        return 0
    fi

    git -C "$root" commit -m "$commit_message" || {
        log_error "Failed to commit $file_description."
        return 1
    }
    git -C "$root" push -u origin "$branch" || {
        log_error "Failed to push branch '$branch' to origin."
        return 1
    }

    gh pr create \
        --repo "$repo" \
        --base "$default_branch" \
        --head "$branch" \
        --title "$pr_title" \
        --draft \
        --body-file "$body_file"
}

base_repo_create_baseline_pr_body() {
    local name="$1"
    local root="$2"
    local repo="$3"

    cat <<EOF
## Summary

- Add Base-managed repository baseline files.

## Validation

- ./tests/validate.sh

Generated by:

\`\`\`bash
basectl repo init $name --path $root --repo $repo --pr
\`\`\`
EOF
}

base_repo_create_agent_guidance_pr_body() {
    local default_branch="$3"
    local repo="$5"
    local repo_name="$1"
    local root="$2"
    local validation_command="$4"

    cat <<EOF
## Summary

- Add Base repo-local agent guidance files.

## Validation

- $validation_command

Generated by:

\`\`\`bash
basectl repo agent-guidance $(base_repo_pretty_arg "$root") --repo-name $(base_repo_pretty_arg "$repo_name") --default-branch $(base_repo_pretty_arg "$default_branch") --validation-command $(base_repo_pretty_arg "$validation_command") --repo $repo --pr
\`\`\`
EOF
}

base_repo_create_installer_template_pr_body() {
    local path="$1"
    local repo="$2"

    cat <<EOF
## Summary

- Add the maintained Base project installer template.

## Validation

- Not run. Generated installer-template change only.

Generated by:

\`\`\`bash
basectl repo installer-template $(base_repo_pretty_arg "$path") --repo $repo --pr
\`\`\`
EOF
}

base_repo_finish_pr_baseline() {
    local body_file
    local branch="$5"
    local default_branch="$6"
    local dry_run="$1"
    local name="$2"
    local repo="$4"
    local root="$3"
    local status

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would commit generated repository baseline files with message 'Add Base repository baseline'.\n"
        printf "[DRY-RUN] Would push branch '%s' to origin.\n" "$branch"
        printf "[DRY-RUN] Would open a pull request in '%s' from '%s' to '%s' with title 'Add Base repository baseline'.\n" "$repo" "$branch" "$default_branch"
        return 0
    fi

    base_repo_stage_pr_baseline_files "$root" || return 1
    if git -C "$root" diff --cached --quiet --; then
        log_info "No repository baseline changes to commit; skipping pull request creation."
        return 0
    fi

    git -C "$root" commit -m "Add Base repository baseline" || {
        log_error "Failed to commit repository baseline files."
        return 1
    }
    git -C "$root" push -u origin "$branch" || {
        log_error "Failed to push branch '$branch' to origin."
        return 1
    }

    body_file="$(mktemp "${TMPDIR:-/tmp}/base-repo-init-pr.XXXXXX")" || {
        log_error "Failed to create a temporary pull request body file."
        return 1
    }
    base_repo_create_baseline_pr_body "$name" "$root" "$repo" > "$body_file"
    gh pr create \
        --repo "$repo" \
        --base "$default_branch" \
        --head "$branch" \
        --title "Add Base repository baseline" \
        --body-file "$body_file"
    status=$?
    rm -f "$body_file"
    return "$status"
}

base_repo_finish_agent_guidance_pr() {
    local body_file
    local branch="$5"
    local default_branch="$6"
    local dry_run="$1"
    local repo="$4"
    local repo_name="$2"
    local root="$3"
    local status
    local validation_command="$7"

    if [[ "$dry_run" == "1" ]]; then
        base_repo_finish_generated_pr \
            "$dry_run" \
            "$root" \
            "$repo" \
            "$branch" \
            "$default_branch" \
            "Add Base agent guidance" \
            "agent guidance files" \
            "Add Base agent guidance" \
            "" \
            "${BASE_REPO_AGENT_GUIDANCE_FILES[@]}"
        return $?
    fi

    body_file="$(mktemp "${TMPDIR:-/tmp}/base-repo-agent-guidance-pr.XXXXXX")" || {
        log_error "Failed to create a temporary pull request body file."
        return 1
    }
    base_repo_create_agent_guidance_pr_body "$repo_name" "$root" "$default_branch" "$validation_command" "$repo" > "$body_file"
    base_repo_finish_generated_pr \
        "$dry_run" \
        "$root" \
        "$repo" \
        "$branch" \
        "$default_branch" \
        "Add Base agent guidance" \
        "agent guidance files" \
        "Add Base agent guidance" \
        "$body_file" \
        "${BASE_REPO_AGENT_GUIDANCE_FILES[@]}"
    status=$?
    rm -f "$body_file"
    return "$status"
}

base_repo_finish_installer_template_pr() {
    local body_file
    local branch="$5"
    local default_branch="$6"
    local dry_run="$1"
    local rel_path="$7"
    local repo="$4"
    local root="$3"
    local status
    local target_path="$2"

    if [[ "$dry_run" == "1" ]]; then
        base_repo_finish_generated_pr \
            "$dry_run" \
            "$root" \
            "$repo" \
            "$branch" \
            "$default_branch" \
            "Add Base installer template" \
            "installer template file" \
            "Add Base installer template" \
            "" \
            "$rel_path"
        return $?
    fi

    body_file="$(mktemp "${TMPDIR:-/tmp}/base-repo-installer-template-pr.XXXXXX")" || {
        log_error "Failed to create a temporary pull request body file."
        return 1
    }
    base_repo_create_installer_template_pr_body "$target_path" "$repo" > "$body_file"
    base_repo_finish_generated_pr \
        "$dry_run" \
        "$root" \
        "$repo" \
        "$branch" \
        "$default_branch" \
        "Add Base installer template" \
        "installer template file" \
        "Add Base installer template" \
        "$body_file" \
        "$rel_path"
    status=$?
    rm -f "$body_file"
    return "$status"
}

base_repo_pr_baseline_has_changes() {
    local root="$1"

    base_repo_stage_pr_baseline_files "$root" || return 2
    if git -C "$root" diff --cached --quiet --; then
        git -C "$root" reset --quiet || return 2
        return 1
    fi
    git -C "$root" reset --quiet || return 2
    return 0
}

base_repo_check_baseline() {
    local missing=0
    local path="$1"
    local rel

    for rel in "${BASE_REPO_BASELINE_FILES[@]}"; do
        if [[ ! -f "$path/$rel" ]]; then
            log_warn "Missing repository baseline file '$rel'."
            missing=1
        else
            log_info "Repository baseline file '$rel' exists."
        fi
    done

    if [[ -f "$path/tests/validate.sh" && ! -x "$path/tests/validate.sh" ]]; then
        log_warn "Repository baseline file 'tests/validate.sh' is not executable."
        missing=1
    fi

    if ((missing)); then
        log_warn "Repository baseline check found missing requirements."
        return 1
    fi

    log_info "Repository baseline check passed."
    return 0
}

base_repo_check_agent_guidance() {
    local missing=0
    local path="$1"
    local rel

    for rel in "${BASE_REPO_AGENT_GUIDANCE_FILES[@]}"; do
        if [[ ! -f "$path/$rel" ]]; then
            log_warn "Missing agent guidance file '$rel'."
            missing=1
        else
            log_info "Agent guidance file '$rel' exists."
        fi
    done

    if ((missing)); then
        log_warn "Agent guidance baseline check found missing requirements."
        return 1
    fi

    log_info "Agent guidance baseline check passed."
    return 0
}

base_repo_init() {
    local configure=1
    local baseline_change_status=0
    local copyright_holder=""
    local create_pr=0
    local default_branch=""
    local description=""
    local dry_run=0
    local github_repo=""
    local github_visibility="private"
    local github_visibility_explicit=0
    local name=""
    local path=""
    local project_owner=""
    local project_schema="base-roadmap"
    local project_title=""
    local copy_project_fields_from=""
    local protect_default_branch=1
    local pr_branch=""
    local requested_visibility=""
    local root
    local configure_project=1
    local initiative_options=()

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_init_usage
                return 0
                ;;
            --path)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--path' requires an argument."
                    return $?
                }
                path="$2"
                shift 2
                ;;
            --path=*)
                path="${1#--path=}"
                shift
                ;;
            --repo)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--repo' requires an argument."
                    return $?
                }
                github_repo="$2"
                shift 2
                ;;
            --repo=*)
                github_repo="${1#--repo=}"
                shift
                ;;
            --pr)
                create_pr=1
                shift
                ;;
            --description)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--description' requires an argument."
                    return $?
                }
                description="$2"
                shift 2
                ;;
            --copyright-holder)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--copyright-holder' requires an argument."
                    return $?
                }
                copyright_holder="$2"
                shift 2
                ;;
            --private|--public)
                requested_visibility="${1#--}"
                if ((github_visibility_explicit)) && [[ "$github_visibility" != "$requested_visibility" ]]; then
                    base_repo_init_usage_error "Options '--private' and '--public' cannot be used together."
                    return $?
                fi
                github_visibility="$requested_visibility"
                github_visibility_explicit=1
                shift
                ;;
            --no-configure)
                configure=0
                shift
                ;;
            --no-protect-default-branch)
                protect_default_branch=0
                shift
                ;;
            --project)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--project' requires an argument."
                    return $?
                }
                project_title="$2"
                shift 2
                ;;
            --project=*)
                project_title="${1#--project=}"
                shift
                ;;
            --project-owner)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--project-owner' requires an argument."
                    return $?
                }
                project_owner="$2"
                shift 2
                ;;
            --project-owner=*)
                project_owner="${1#--project-owner=}"
                shift
                ;;
            --project-schema)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--project-schema' requires an argument."
                    return $?
                }
                project_schema="$2"
                shift 2
                ;;
            --project-schema=*)
                project_schema="${1#--project-schema=}"
                shift
                ;;
            --initiative-option)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--initiative-option' requires an argument."
                    return $?
                }
                initiative_options+=("$2")
                shift 2
                ;;
            --initiative-option=*)
                initiative_options+=("${1#--initiative-option=}")
                shift
                ;;
            --copy-project-fields-from)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--copy-project-fields-from' requires an argument."
                    return $?
                }
                copy_project_fields_from="$2"
                shift 2
                ;;
            --copy-project-fields-from=*)
                copy_project_fields_from="${1#--copy-project-fields-from=}"
                shift
                ;;
            --no-project)
                configure_project=0
                shift
                ;;
            --dry-run)
                dry_run=1
                shift
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_init_usage_error "Unknown repo init option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$name" ]]; then
                    base_repo_init_usage_error "The 'repo init' command accepts exactly one repository name."
                    return $?
                fi
                name="$1"
                shift
                ;;
        esac
    done

    [[ -n "$name" ]] || {
        base_repo_init_usage_error "Repository name is required."
        return $?
    }
    base_repo_validate_name "$name" || return 2
    [[ -n "$path" ]] || path="$(base_repo_default_target_path "$name")"
    [[ -n "$description" ]] || description="$(base_repo_default_description "$name")"
    [[ -n "$copyright_holder" ]] || copyright_holder="$(base_repo_default_copyright_holder)"
    root="$(base_repo_target_path "$path")"

    if ((create_pr)); then
        if [[ -z "$github_repo" ]]; then
            github_repo="$(base_repo_infer_github_repo "$root" || true)"
        fi
        [[ -n "$github_repo" ]] || {
            base_repo_init_usage_error "Option '--pr' requires --repo <owner/name> or an inferable GitHub origin remote."
            return $?
        }
        if ((github_visibility_explicit)); then
            base_repo_init_usage_error "Options '--private' and '--public' cannot be used with '--pr'."
            return $?
        fi

        pr_branch="$(base_repo_pr_branch_name "$name")"
        if [[ "$dry_run" == "1" ]]; then
            default_branch="<default branch>"
        else
            base_repo_require_pr_worktree "$root" || return 1
            default_branch="$(base_repo_default_branch_for_pr "$github_repo")" || return 1
        fi
        base_repo_prepare_pr_branch "$dry_run" "$root" "$pr_branch" "$default_branch" || return 1
    fi

    base_repo_write_baseline "$dry_run" "$name" "$description" "$copyright_holder" "$root" || return 1

    if ((create_pr)); then
        if [[ "$dry_run" == "1" ]]; then
            base_repo_finish_pr_baseline "$dry_run" "$name" "$root" "$github_repo" "$pr_branch" "$default_branch"
            return $?
        fi
        if base_repo_pr_baseline_has_changes "$root"; then
            base_repo_finish_pr_baseline "$dry_run" "$name" "$root" "$github_repo" "$pr_branch" "$default_branch"
            return $?
        else
            baseline_change_status=$?
            case "$baseline_change_status" in
                1)
                    if ((configure)); then
                        log_info "No repository baseline changes to commit; continuing with GitHub repository configuration."
                    else
                        log_info "No repository baseline changes to commit; GitHub repository configuration skipped by --no-configure."
                    fi
                    ;;
                *)
                    return 1
                    ;;
            esac
        fi
    fi

    if ((configure)); then
        if [[ -z "$github_repo" ]]; then
            github_repo="$(base_repo_infer_github_repo "$root" || true)"
        fi
        if [[ -n "$github_repo" ]]; then
            base_repo_ensure_github_repo "$dry_run" "$github_repo" "$description" "$github_visibility" || return 1
            base_repo_configure_github "$dry_run" "$github_repo" "$protect_default_branch" || return 1
            if ((configure_project)); then
                [[ -n "$project_title" ]] || project_title="$(base_repo_default_project_title "$github_repo")"
                [[ -n "$project_owner" ]] || project_owner="$(base_repo_project_owner_from_repo "$github_repo")"
                base_repo_configure_project_metadata \
                    "$dry_run" \
                    "$github_repo" \
                    "$project_title" \
                    "$project_owner" \
                    "$project_schema" \
                    "$(base_repo_project_config_path "$root")" \
                    "$copy_project_fields_from" \
                    "${initiative_options[@]}" || return 1
            fi
        else
            if [[ "$dry_run" == "1" ]]; then
                printf "[DRY-RUN] Would not create or configure a GitHub repository because no GitHub repo was provided or inferred. Pass --repo <owner/name> to include GitHub repository creation and configuration.\n"
            else
                log_info "Skipping GitHub repository creation and configuration because no GitHub repo was provided or inferred."
            fi
        fi
    fi
}

base_repo_clone_check_destination() {
    local actual_repo=""
    local expected_repo="$1"
    local target="$2"

    [[ -e "$target" ]] || return 0

    if [[ ! -d "$target" ]]; then
        log_error "Destination '$target' already exists but is not a matching Git checkout."
        return 1
    fi

    actual_repo="$(base_repo_infer_github_repo "$target" || true)"
    if [[ "$actual_repo" == "$expected_repo" ]]; then
        printf "Repository '%s' already exists at '%s'.\n" "$expected_repo" "$target"
        return 2
    fi

    if [[ -n "$actual_repo" ]]; then
        log_error "Destination '$target' already points at GitHub repository '$actual_repo'."
        log_error "Expected '$expected_repo'."
        return 1
    fi

    log_error "Destination '$target' already exists but is not a matching Git checkout."
    return 1
}

base_repo_clone_with_gh() {
    local clone_url="$4"
    local dry_run="$1"
    local parent
    local repo="$2"
    local status
    local target="$3"

    base_repo_clone_check_destination "$repo" "$target"
    status=$?
    case "$status" in
        0)
            ;;
        2)
            return 0
            ;;
        *)
            return 1
            ;;
    esac

    if [[ "$dry_run" == "1" ]]; then
        printf "Repository: %s\n" "$repo"
        printf "Destination: %s\n" "$target"
        printf "Tool: gh repo clone\n"
        printf "Clone URL: %s\n" "$clone_url"
        printf "[DRY-RUN] Would run: "
        base_repo_pretty_command gh repo clone "$repo" "$target"
        printf "\n"
        return 0
    fi

    command -v gh >/dev/null 2>&1 || {
        log_error "GitHub CLI 'gh' is required for repository clone."
        return 1
    }

    parent="$(dirname -- "$target")"
    base_repo_create_directory "$parent" || return 1
    printf "Cloning GitHub repository '%s' into '%s'.\n" "$repo" "$target"
    gh repo clone "$repo" "$target" || {
        log_error "Failed to clone GitHub repository '$repo' into '$target'."
        return 1
    }
    printf "Run basectl repo check '%s' after the clone if the repository has adopted the Base baseline.\n" "$target"
}

base_repo_clone() {
    local clone_url
    local dry_run=0
    local github_repo
    local name=""
    local owner=""
    local path=""
    local protocol
    local spec=""
    local status
    local target

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_clone_usage
                return 0
                ;;
            --owner)
                [[ -n "${2:-}" ]] || {
                    base_repo_clone_usage_error "Option '--owner' requires an argument."
                    return $?
                }
                owner="$2"
                shift 2
                ;;
            --owner=*)
                owner="${1#--owner=}"
                shift
                ;;
            --path)
                [[ -n "${2:-}" ]] || {
                    base_repo_clone_usage_error "Option '--path' requires an argument."
                    return $?
                }
                path="$2"
                shift 2
                ;;
            --path=*)
                path="${1#--path=}"
                shift
                ;;
            --dry-run)
                dry_run=1
                shift
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_clone_usage_error "Unknown repo clone option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$spec" ]]; then
                    base_repo_clone_usage_error "The 'repo clone' command accepts exactly one repository name."
                    return $?
                fi
                spec="$1"
                shift
                ;;
        esac
    done

    [[ -n "$spec" ]] || {
        base_repo_clone_usage_error "Repository name is required."
        return $?
    }

    if [[ "$spec" == */* ]]; then
        [[ "$spec" != */*/* ]] || {
            base_repo_clone_usage_error "Repository must be '<name>' or '<owner>/<name>'."
            return $?
        }
        [[ -z "$owner" ]] || {
            base_repo_clone_usage_error "Option '--owner' cannot be used with '<owner>/<name>'."
            return $?
        }
        owner="${spec%%/*}"
        name="${spec#*/}"
    else
        name="$spec"
        if [[ -z "$owner" ]]; then
            owner="$(base_repo_default_github_owner)"
            status=$?
            case "$status" in
                0)
                    ;;
                1)
                    base_repo_clone_usage_error "Repository owner is required for short repo names. Pass --owner <owner> or set github.default_owner in ~/.base.d/config.yaml."
                    return $?
                    ;;
                *)
                    return "$status"
                    ;;
            esac
        fi
    fi

    base_repo_validate_owner "$owner" || return 2
    base_repo_validate_name "$name" || return 2
    github_repo="$owner/$name"
    protocol="$(base_repo_clone_protocol)" || return $?
    clone_url="$(base_repo_clone_url "$protocol" "$github_repo")" || return 1

    if [[ -z "$path" ]]; then
        path="$(base_repo_default_target_path "$name")" || return $?
    else
        path="$(base_repo_expand_path "$path")"
    fi
    target="$(base_repo_target_path "$path")"

    base_repo_clone_with_gh "$dry_run" "$github_repo" "$target" "$clone_url"
}

base_repo_check() {
    local agent_guidance=0
    local path="."
    local status=0

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_check_usage
                return 0
                ;;
            --agent-guidance)
                agent_guidance=1
                shift
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_check_usage_error "Unknown repo check option '$1'."
                return $?
                ;;
            *)
                if [[ "$path" != "." ]]; then
                    base_repo_check_usage_error "The 'repo check' command accepts at most one path."
                    return $?
                fi
                path="$1"
                shift
                ;;
        esac
    done

    path="$(base_repo_target_path "$path")"
    base_repo_check_baseline "$path" || status=1
    if ((agent_guidance)); then
        base_repo_check_agent_guidance "$path" || status=1
    fi
    return "$status"
}

base_repo_agent_guidance() {
    local create_pr=0
    local default_branch="main"
    local dry_run=0
    local github_repo=""
    local path="."
    local pr_branch=""
    local pr_default_branch=""
    local repo_name=""
    local root
    local validation_command="./tests/validate.sh"

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_agent_guidance_usage
                return 0
                ;;
            --repo)
                [[ -n "${2:-}" ]] || {
                    base_repo_agent_guidance_usage_error "Option '--repo' requires an argument."
                    return $?
                }
                github_repo="$2"
                shift 2
                ;;
            --repo=*)
                github_repo="${1#--repo=}"
                shift
                ;;
            --repo-name)
                [[ -n "${2:-}" ]] || {
                    base_repo_agent_guidance_usage_error "Option '--repo-name' requires an argument."
                    return $?
                }
                repo_name="$2"
                shift 2
                ;;
            --repo-name=*)
                repo_name="${1#--repo-name=}"
                shift
                ;;
            --default-branch)
                [[ -n "${2:-}" ]] || {
                    base_repo_agent_guidance_usage_error "Option '--default-branch' requires an argument."
                    return $?
                }
                default_branch="$2"
                shift 2
                ;;
            --default-branch=*)
                default_branch="${1#--default-branch=}"
                shift
                ;;
            --validation-command)
                [[ -n "${2:-}" ]] || {
                    base_repo_agent_guidance_usage_error "Option '--validation-command' requires an argument."
                    return $?
                }
                validation_command="$2"
                shift 2
                ;;
            --validation-command=*)
                validation_command="${1#--validation-command=}"
                shift
                ;;
            --pr)
                create_pr=1
                shift
                ;;
            --dry-run)
                dry_run=1
                shift
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_agent_guidance_usage_error "Unknown repo agent-guidance option '$1'."
                return $?
                ;;
            *)
                if [[ "$path" != "." ]]; then
                    base_repo_agent_guidance_usage_error "The 'repo agent-guidance' command accepts at most one path."
                    return $?
                fi
                path="$1"
                shift
                ;;
        esac
    done

    root="$(base_repo_target_path "$path")"
    [[ -n "$repo_name" ]] || repo_name="$(basename -- "$root")"
    [[ -n "$default_branch" ]] || {
        base_repo_agent_guidance_usage_error "Option '--default-branch' requires a non-empty value."
        return $?
    }
    [[ -n "$validation_command" ]] || {
        base_repo_agent_guidance_usage_error "Option '--validation-command' requires a non-empty value."
        return $?
    }
    base_repo_validate_name "$repo_name" || return 2

    if ((create_pr)); then
        if [[ -z "$github_repo" ]]; then
            github_repo="$(base_repo_infer_github_repo "$root" || true)"
        fi
        [[ -n "$github_repo" ]] || {
            base_repo_agent_guidance_usage_error "Option '--pr' requires --repo <owner/name> or an inferable GitHub origin remote."
            return $?
        }

        pr_branch="$(base_repo_helper_pr_branch_name "agent-guidance" "$repo_name")"
        if [[ "$dry_run" == "1" ]]; then
            pr_default_branch="<default branch>"
        else
            base_repo_require_pr_worktree "$root" "repo agent-guidance --pr" || return 1
            pr_default_branch="$(base_repo_default_branch_for_pr "$github_repo")" || return 1
        fi
        base_repo_prepare_pr_branch "$dry_run" "$root" "$pr_branch" "$pr_default_branch" "repo agent-guidance --pr" || return 1
    fi

    base_repo_write_agent_guidance "$dry_run" "$repo_name" "$default_branch" "$validation_command" "$root" || return $?
    if ((create_pr)); then
        base_repo_finish_agent_guidance_pr \
            "$dry_run" \
            "$repo_name" \
            "$root" \
            "$github_repo" \
            "$pr_branch" \
            "$pr_default_branch" \
            "$validation_command"
        return $?
    fi
    if [[ "$dry_run" != "1" ]]; then
        base_repo_print_review_hint "$root"
    fi
}

base_repo_configure() {
    local configure_project=1
    local copy_project_fields_from=""
    local dry_run=0
    local github_repo=""
    local initiative_options=()
    local path="."
    local project_owner=""
    local project_schema="base-roadmap"
    local project_title=""
    local protect_default_branch=1

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_configure_usage
                return 0
                ;;
            --repo)
                [[ -n "${2:-}" ]] || {
                    base_repo_configure_usage_error "Option '--repo' requires an argument."
                    return $?
                }
                github_repo="$2"
                shift 2
                ;;
            --repo=*)
                github_repo="${1#--repo=}"
                shift
                ;;
            --dry-run)
                dry_run=1
                shift
                ;;
            --no-protect-default-branch)
                protect_default_branch=0
                shift
                ;;
            --project)
                [[ -n "${2:-}" ]] || {
                    base_repo_configure_usage_error "Option '--project' requires an argument."
                    return $?
                }
                project_title="$2"
                shift 2
                ;;
            --project=*)
                project_title="${1#--project=}"
                shift
                ;;
            --project-owner)
                [[ -n "${2:-}" ]] || {
                    base_repo_configure_usage_error "Option '--project-owner' requires an argument."
                    return $?
                }
                project_owner="$2"
                shift 2
                ;;
            --project-owner=*)
                project_owner="${1#--project-owner=}"
                shift
                ;;
            --project-schema)
                [[ -n "${2:-}" ]] || {
                    base_repo_configure_usage_error "Option '--project-schema' requires an argument."
                    return $?
                }
                project_schema="$2"
                shift 2
                ;;
            --project-schema=*)
                project_schema="${1#--project-schema=}"
                shift
                ;;
            --initiative-option)
                [[ -n "${2:-}" ]] || {
                    base_repo_configure_usage_error "Option '--initiative-option' requires an argument."
                    return $?
                }
                initiative_options+=("$2")
                shift 2
                ;;
            --initiative-option=*)
                initiative_options+=("${1#--initiative-option=}")
                shift
                ;;
            --copy-project-fields-from)
                [[ -n "${2:-}" ]] || {
                    base_repo_configure_usage_error "Option '--copy-project-fields-from' requires an argument."
                    return $?
                }
                copy_project_fields_from="$2"
                shift 2
                ;;
            --copy-project-fields-from=*)
                copy_project_fields_from="${1#--copy-project-fields-from=}"
                shift
                ;;
            --no-project)
                configure_project=0
                shift
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_configure_usage_error "Unknown repo configure option '$1'."
                return $?
                ;;
            *)
                if [[ "$path" != "." ]]; then
                    base_repo_configure_usage_error "The 'repo configure' command accepts at most one path."
                    return $?
                fi
                path="$1"
                shift
                ;;
        esac
    done

    path="$(base_repo_target_path "$path")"
    if [[ -z "$github_repo" ]]; then
        github_repo="$(base_repo_infer_github_repo "$path" || true)"
    fi
    [[ -n "$github_repo" ]] || {
        log_error "Unable to infer GitHub repository from '$path'."
        log_error "Pass --repo <owner/name> to configure a GitHub repository explicitly."
        return 1
    }

    if ((configure_project)); then
        base_repo_write_project_support_files "$dry_run" "$path" || return 1
    fi

    base_repo_configure_github "$dry_run" "$github_repo" "$protect_default_branch" || return 1
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
            "${initiative_options[@]}"
    fi
}

base_repo_installer_template() {
    local create_pr=0
    local dry_run=0
    local github_repo=""
    local path=""
    local pr_branch=""
    local pr_default_branch=""
    local rel_path=""
    local repo_name=""
    local root=""

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_installer_template_usage
                return 0
                ;;
            --repo)
                [[ -n "${2:-}" ]] || {
                    base_repo_installer_template_usage_error "Option '--repo' requires an argument."
                    return $?
                }
                github_repo="$2"
                shift 2
                ;;
            --repo=*)
                github_repo="${1#--repo=}"
                shift
                ;;
            --pr)
                create_pr=1
                shift
                ;;
            --dry-run)
                dry_run=1
                shift
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_installer_template_usage_error "Unknown repo installer-template option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$path" ]]; then
                    base_repo_installer_template_usage_error "The 'repo installer-template' command accepts at most one path."
                    return $?
                fi
                path="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$path" ]]; then
        if ((create_pr)); then
            base_repo_installer_template_usage_error "Option '--pr' requires a path."
            return $?
        fi
        base_repo_print_installer_template
        return $?
    fi

    path="$(base_repo_target_path "$path")"
    root="$(dirname -- "$path")"
    repo_name="$(basename -- "$root")"

    if ((create_pr)); then
        if [[ -z "$github_repo" ]]; then
            github_repo="$(base_repo_infer_github_repo "$root" || true)"
        fi
        [[ -n "$github_repo" ]] || {
            base_repo_installer_template_usage_error "Option '--pr' requires --repo <owner/name> or an inferable GitHub origin remote."
            return $?
        }

        repo_name="${github_repo#*/}"
        pr_branch="$(base_repo_helper_pr_branch_name "installer-template" "$repo_name")"
        if [[ "$dry_run" == "1" ]]; then
            pr_default_branch="<default branch>"
            rel_path="$(basename -- "$path")"
        else
            base_repo_require_pr_worktree "$root" "repo installer-template --pr" || return 1
            pr_default_branch="$(base_repo_default_branch_for_pr "$github_repo")" || return 1
            rel_path="$(base_repo_relative_path_under_root "$root" "$path")" || {
                log_error "repo installer-template --pr expects path to be inside '$root'."
                return 1
            }
        fi
        base_repo_prepare_pr_branch "$dry_run" "$root" "$pr_branch" "$pr_default_branch" "repo installer-template --pr" || return 1
    fi

    base_repo_write_installer_template "$dry_run" "$path" || return $?
    if ((create_pr)); then
        base_repo_finish_installer_template_pr \
            "$dry_run" \
            "$path" \
            "$root" \
            "$github_repo" \
            "$pr_branch" \
            "$pr_default_branch" \
            "$rel_path"
        return $?
    fi
    if [[ "$dry_run" != "1" ]]; then
        base_repo_print_review_hint "$(dirname -- "$path")"
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
            base_repo_init "$@"
            ;;
        clone)
            shift
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
            base_repo_agent_guidance "$@"
            ;;
        installer-template)
            shift
            base_repo_installer_template "$@"
            ;;
        *)
            base_repo_usage_error "Unknown repo command '$repo_command'."
            ;;
    esac
}
