#!/usr/bin/env bash

[[ -n "${_base_repo_subcommand_sourced:-}" ]] && return 0
_base_repo_subcommand_sourced=1
readonly _base_repo_subcommand_sourced

import_base_lib gh/lib_gh.sh
import_base_lib str/lib_str.sh

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
  --pr                          Commit the generated baseline on a branch and open a pull request.
  --agent-ready                 Also seed repo-local agent guidance files.
  --language <csv>              Add project language metadata; may be repeated.
  --description <text>          Repository description for generated README.
  --copyright-holder <name>     Copyright holder for generated AGPL license. Defaults to git config user.name.
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
  basectl repo init bankbuddy --path . --repo codeforester/bankbuddy --pr

  # Seed a polyglot project profile (CSV and repeated forms are equivalent).
  basectl repo init platform --language go,javascript --language typescript

  # After the baseline PR is merged, apply or repair GitHub settings.
  basectl repo configure . --repo codeforester/bankbuddy

Ensures the standard local Base-managed repository baseline, including
.github/base-project.yml. Safe to run against an existing repository: existing
files are left unchanged and missing baseline files are added.

Safe to re-run: Base-managed settings are created or updated to the Base
standard. Settings added outside Base are not removed.

When --repo names a missing GitHub repo, repo init creates it using --private/--public.
Unless --no-configure is set, repo init also applies the GitHub-side settings
handled by repo configure. With --pr, the first run opens a baseline PR when
files change; rerun the same command after merge to continue GitHub-side
configuration.

For the current checkout, pass its repository name and --path .
Plain repo init writes local baseline files but does not commit or push them.
With --pr, repo init commits baseline changes on a branch, pushes that branch to origin, and opens a pull request.
Pass --agent-ready to include AGENTS.md and skills.md with the baseline.
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
  --project-schema <schema>     Project metadata schema. Defaults to base-project.
  --initiative-option <name>    Initiative option to seed. May be repeated.
  --copy-project-fields-from <title>
                                Copy missing Project item field values from another Project.
  --replace-project             Replace a nonstandard existing Project from base-project-template.
  --no-project                  Skip GitHub Project metadata configuration.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Examples:
  basectl repo configure . --repo codeforester/bankbuddy
  basectl repo configure . --copy-project-fields-from "Legacy Roadmap"

repo configure applies or repairs GitHub-side repository settings, labels,
branch protection, Project metadata, and repo-visible Project intake support.
Use it after a repo init --pr baseline PR is merged, after cloning an older
Base-managed repo, or whenever GitHub settings drift.

When .github/base-project.yml exists, repo configure uses it for repo-specific
GitHub Project taxonomy and issue defaults.

Safe to re-run: Base-managed settings are created or updated to the Base
standard. Settings added outside Base are not removed.

It does not create the full local baseline; run repo init first when the
Base-managed files are missing.
EOF
}

base_repo_print_usage_error() {
    local help_command="$1"
    shift

    print_error "$*"
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

    if declare -F base_repo_installer_template >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/repo_installer_template.sh" || return 1
    [[ -f "$module_path" ]] || {
        log_error "repo installer-template helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo_installer_template.sh
    source "$module_path"
}

base_repo_load_agent_guidance() {
    local module_path

    if declare -F base_repo_agent_guidance >/dev/null 2>&1; then
        return 0
    fi

    module_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/repo_agent_guidance.sh" || return 1
    [[ -f "$module_path" ]] || {
        log_error "repo agent-guidance helper was not found at '$module_path'."
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
        log_error "repo GitHub settings helper was not found at '$module_path'."
        return 1
    }
    # shellcheck source=cli/bash/commands/basectl/subcommands/repo_github_settings.sh
    source "$module_path"
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
    local year

    printf -v year '%(%Y)T' -1 || return 1
    printf '%s\n' "$year"
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
        log_error "BASE_HOME is required to locate the Project Intake workflow template."
        return 1
    }

    printf '%s/templates/project-intake.yml\n' "$BASE_HOME"
}

base_repo_write_project_intake_workflow() {
    local dry_run="$1"
    local root="$2"
    local template

    template="$(base_repo_project_intake_workflow_template_path)" || return 1
    [[ -f "$template" ]] || {
        log_error "Project Intake workflow template was not found at '$template'."
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
    local copyright_holder="$4"
    local description="$3"
    local dry_run="$1"
    local name="$2"
    local root="$5"
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
    base_repo_write_license "$dry_run" "$copyright_holder" "$root" || status=1
    base_repo_write_gitignore "$dry_run" "$root" || status=1
    base_repo_write_manifest "$dry_run" "$name" "$root" "${languages[@]}" || status=1
    base_repo_write_validate_script "$dry_run" "$root" || status=1
    base_repo_write_project_intake_workflow "$dry_run" "$root" || status=1
    base_repo_write_tests_workflow "$dry_run" "$root" || status=1

    return "$status"
}

base_repo_infer_github_repo() {
    local path="$1"
    local github_repo

    gh_infer_repo_from_origin "$path" github_repo || return 1

    printf '%s\n' "$github_repo"
}

base_repo_require_gh() {
    gh_require_cli "GitHub CLI 'gh' is required for repository configuration." || return 1
    gh_auth_status_diagnostics "Run 'gh auth login -h github.com' and retry."
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
    # shellcheck disable=SC2034 # Passed by name to str_join.
    local values=("$@")

    str_join joined ", " values
    printf '%s' "$joined"
}

base_repo_title_case_name() {
    local name="$1"

    printf '%s\n' "$name" |
        tr '._-' '   ' |
        awk '{ for (i = 1; i <= NF; i++) { $i = toupper(substr($i, 1, 1)) substr($i, 2) } print }'
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

base_repo_print_pr_worktree_root_hint() {
    local command_label="$1"
    local provided_path="$2"
    local repository_root="$3"

    if [[ "$command_label" == "repo init --pr" ]]; then
        log_error "repo init --pr expects --path to point at the repository root."
    else
        log_error "$command_label expects the target path to point at the repository root."
    fi
    printf "  Provided path: %s\n" "$provided_path" >&2
    printf "  Repository root: %s\n" "$repository_root" >&2
    if [[ "$command_label" == "repo init --pr" ]]; then
        printf "  Fix: pass --path %s\n" "$(base_repo_pretty_arg "$repository_root")" >&2
    else
        printf "  Fix: pass %s as the target path.\n" "$(base_repo_pretty_arg "$repository_root")" >&2
    fi
}

base_repo_print_pr_worktree_dirty_hint() {
    local dirty_count=0
    local dirty_word
    local line
    local root="$1"
    local shown_count=0
    local status_output="$2"

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -n "$line" ]] || continue
        dirty_count=$((dirty_count + 1))
    done <<< "$status_output"

    dirty_word="files"
    [[ "$dirty_count" == "1" ]] && dirty_word="file"

    printf "  Uncommitted changes detected (%d %s).\n" "$dirty_count" "$dirty_word" >&2
    printf "  Dirty paths:\n" >&2
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -n "$line" ]] || continue
        if ((shown_count >= 5)); then
            break
        fi
        printf "    %s\n" "$line" >&2
        shown_count=$((shown_count + 1))
    done <<< "$status_output"
    if ((dirty_count > shown_count)); then
        printf "    ... (%d more)\n" "$((dirty_count - shown_count))" >&2
    fi
    printf "  Fix: commit or stash your changes before running this command.\n" >&2
    printf "    git -C %s status --short\n" "$(base_repo_pretty_arg "$root")" >&2
    printf "    git -C %s stash\n" "$(base_repo_pretty_arg "$root")" >&2
    printf "    git -C %s commit -am \"WIP\"\n" "$(base_repo_pretty_arg "$root")" >&2
}

base_repo_require_pr_worktree() {
    local command_label="${2:-repo init --pr}"
    local dirty_status
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
        base_repo_print_pr_worktree_root_hint "$command_label" "$root" "$git_root"
        return 1
    }

    dirty_status="$(git -C "$root" status --porcelain)"
    [[ -z "$dirty_status" ]] || {
        log_error "$command_label requires a clean Git worktree at '$root'."
        base_repo_print_pr_worktree_dirty_hint "$root" "$dirty_status"
        return 1
    }
}

base_repo_default_branch_for_pr() {
    local base_remote_default_branch
    local repo="$1"

    base_repo_require_gh || return 1
    if ! gh_repo_default_branch "$repo" base_remote_default_branch; then
        log_error "Unable to determine the default branch for GitHub repository '$repo'."
        return 1
    fi

    printf '%s\n' "$base_remote_default_branch"
}

base_repo_detect_default_branch() {
    local base_default_branch
    local root="$1"

    if gh_detect_default_branch "$root" base_default_branch; then
        printf '%s\n' "$base_default_branch"
        return 0
    fi

    return 1
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
    local agent_ready="${2:-0}"
    local files=("${BASE_REPO_BASELINE_FILES[@]}")
    local root="$1"

    if [[ "$agent_ready" == "1" ]]; then
        files+=(AGENTS.md skills.md)
    fi

    base_repo_stage_pr_files "$root" "repository baseline files" "${files[@]}"
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
    local repo="$3"
    local root="$2"
    local command_hint="${4:-basectl repo init $name --path $root --repo $repo --pr}"

    cat <<EOF
## Summary

- Add Base-managed repository baseline files.

## Validation

- ./tests/validate.sh

Generated by:

\`\`\`bash
$command_hint
\`\`\`
EOF
}

base_repo_print_init_pr_next_steps() {
    local command_hint="$2"
    local pr_output="$1"
    local pr_url=""

    pr_url="$(printf '%s\n' "$pr_output" | awk '/^https?:\/\/github.com\/.+\/pull\/[0-9]+/ { print; exit }')"
    if [[ -n "$pr_url" ]]; then
        printf "Baseline PR opened: %s\n" "$pr_url"
    else
        [[ -z "$pr_output" ]] || printf '%s\n' "$pr_output"
        printf "Baseline PR opened.\n"
    fi
    printf "\n"
    printf "Next steps:\n"
    printf "  1. Review and merge the pull request.\n"
    printf "  2. Re-run this command after merge to complete GitHub configuration:\n"
    printf "     %s\n" "$command_hint"
}

base_repo_print_init_github_skip_notice() {
    local dry_run="$1"
    local name="$2"
    local root="$3"
    local pretty_root

    pretty_root="$(base_repo_pretty_arg "$root")"

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would not create or configure a GitHub repository because no GitHub repo was provided or inferred. Pass --repo <owner/name> to include GitHub repository creation and configuration.\n"
        printf "[DRY-RUN] To include GitHub setup, run:\n"
        printf "  basectl repo init %s --path %s --repo <owner/%s>\n" \
            "$(base_repo_pretty_arg "$name")" \
            "$pretty_root" \
            "$name"
        return 0
    fi

    printf "Baseline files written to '%s'.\n" "$root"
    printf "\n"
    printf "GitHub repository not configured (no --repo provided and no origin remote found).\n"
    printf "To complete GitHub setup, run:\n"
    printf "  basectl repo configure %s --repo <owner/%s>\n" "$pretty_root" "$name"
    printf "\n"
    printf "Or to create the GitHub repository and configure it now:\n"
    printf "  basectl repo init %s --path %s --repo <owner/%s>\n" \
        "$(base_repo_pretty_arg "$name")" \
        "$pretty_root" \
        "$name"
}

base_repo_init_pr_rerun_command() {
    local agent_ready="${11}"
    local configure="$4"
    local configure_project="$6"
    local copy_project_fields_from="${10}"
    local name="$1"
    local option
    local project_owner="$8"
    local project_schema="$9"
    local project_title="$7"
    local protect_default_branch="$5"
    local repo="$3"
    local root="$2"
    local command=(basectl repo init "$name" --path "$root" --repo "$repo" --pr)
    local languages_csv="${12}"
    shift 12

    [[ "$configure" == "1" ]] || command+=(--no-configure)
    [[ "$agent_ready" == "1" ]] && command+=(--agent-ready)
    [[ "$protect_default_branch" == "1" ]] || command+=(--no-protect-default-branch)
    [[ "$configure_project" == "1" ]] || command+=(--no-project)
    [[ -z "$project_title" ]] || command+=(--project "$project_title")
    [[ -z "$project_owner" ]] || command+=(--project-owner "$project_owner")
    [[ "$project_schema" == "base-project" ]] || command+=(--project-schema "$project_schema")
    [[ -z "$copy_project_fields_from" ]] || command+=(--copy-project-fields-from "$copy_project_fields_from")
    [[ -z "$languages_csv" ]] || command+=(--language "$languages_csv")
    for option in "$@"; do
        command+=(--initiative-option "$option")
    done

    base_repo_pretty_command "${command[@]}"
}

base_repo_finish_pr_baseline() {
    local agent_ready="${8:-0}"
    local body_file
    local branch="$5"
    local command_hint="${7:-}"
    local default_branch="$6"
    local dry_run="$1"
    local name="$2"
    local output_file
    local pr_output=""
    local repo="$4"
    local root="$3"
    local status

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would commit generated repository baseline files with message 'Add Base repository baseline'.\n"
        printf "[DRY-RUN] Would push branch '%s' to origin.\n" "$branch"
        printf "[DRY-RUN] Would open a pull request in '%s' from '%s' to '%s' with title 'Add Base repository baseline'.\n" "$repo" "$branch" "$default_branch"
        return 0
    fi

    base_repo_stage_pr_baseline_files "$root" "$agent_ready" || return 1
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

    std_make_temp_file body_file base-repo-init-pr || {
        log_error "Failed to create a temporary pull request body file."
        return 1
    }
    std_make_temp_file output_file base-repo-init-pr-output || {
        log_error "Failed to create a temporary pull request output file."
        return 1
    }
    base_repo_create_baseline_pr_body "$name" "$root" "$repo" "$command_hint" > "$body_file"
    gh pr create \
        --repo "$repo" \
        --base "$default_branch" \
        --head "$branch" \
        --title "Add Base repository baseline" \
        --body-file "$body_file" > "$output_file" 2>&1
    status=$?
    pr_output="$(cat "$output_file")"
    rm -f "$body_file"
    rm -f "$output_file"
    if [[ "$status" -eq 0 ]]; then
        base_repo_print_init_pr_next_steps "$pr_output" "${command_hint:-basectl repo init $name --path $root --repo $repo --pr}"
        return 0
    fi
    [[ -z "$pr_output" ]] || printf '%s\n' "$pr_output"
    return "$status"
}

base_repo_pr_baseline_has_changes() {
    local agent_ready="${2:-0}"
    local root="$1"

    base_repo_stage_pr_baseline_files "$root" "$agent_ready" || return 2
    if git -C "$root" diff --cached --quiet --; then
        git -C "$root" reset --quiet || return 2
        return 1
    fi
    git -C "$root" reset --quiet || return 2
    return 0
}

base_repo_write_init_agent_guidance() {
    local agents_existed=0
    local default_branch="$3"
    local dry_run="$1"
    local pr_template_existed=0
    local repo_name="$2"
    local root="$5"
    local skills_existed=0
    local status=0
    local summary_args=()
    local validation_command="$4"

    base_repo_load_agent_guidance || return 1

    if [[ "$dry_run" != "1" ]]; then
        [[ -e "$root/AGENTS.md" ]] && agents_existed=1
        [[ -e "$root/skills.md" ]] && skills_existed=1
        [[ -e "$root/.github/pull_request_template.md" ]] && pr_template_existed=1
    fi

    base_repo_write_agent_instructions "$dry_run" "$repo_name" "$default_branch" "$validation_command" "$root" || status=1
    base_repo_write_agent_skills "$dry_run" "$repo_name" "$root" || status=1

    if [[ "$dry_run" != "1" && "$status" -eq 0 ]]; then
        if ((agents_existed)); then
            summary_args+=(--unchanged "AGENTS.md")
        else
            summary_args+=(--created "AGENTS.md")
        fi
        if ((skills_existed)); then
            summary_args+=(--unchanged "skills.md")
        else
            summary_args+=(--created "skills.md")
        fi
        if ((pr_template_existed)); then
            summary_args+=(--unchanged ".github/pull_request_template.md")
        else
            summary_args+=(--created ".github/pull_request_template.md")
        fi
        base_repo_print_agent_guidance_summary "${summary_args[@]}"
    fi

    return "$status"
}

base_repo_check_baseline() {
    local current_dir
    local fix_path
    local missing_files=()
    local path="$1"
    local rel
    local repo_name
    local required_count="${#BASE_REPO_BASELINE_FILES[@]}"
    local not_executable_files=()
    local command=()

    for rel in "${BASE_REPO_BASELINE_FILES[@]}"; do
        if [[ ! -f "$path/$rel" ]]; then
            missing_files+=("$rel")
        fi
    done

    if [[ -f "$path/tests/validate.sh" && ! -x "$path/tests/validate.sh" ]]; then
        not_executable_files+=(tests/validate.sh)
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
        if ((${#missing_files[@]})); then
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

base_repo_init() {
    local agent_default_branch="main"
    local agent_ready=0
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
    local project_schema="base-project"
    local project_title=""
    local copy_project_fields_from=""
    local protect_default_branch=1
    local pr_branch=""
    local pr_rerun_command=""
    local requested_visibility=""
    local root
    local configure_project=1
    local initiative_options=()
    local language_fields=()
    local language_options=()
    local language_option
    local language_field
    local language
    local normalized_language
    local language_seen

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
            --agent-ready)
                agent_ready=1
                shift
                ;;
            --language)
                [[ -n "${2:-}" ]] || {
                    base_repo_init_usage_error "Option '--language' requires a comma-separated language list."
                    return $?
                }
                language_option="${2//[[:space:]]/}"
                if [[ -z "$language_option" || "$language_option" == ,* || "$language_option" == *, || "$language_option" == *,,* ]]; then
                    base_repo_init_usage_error "Option '--language' must not contain empty entries."
                    return $?
                fi
                str_split language_fields "$language_option" ","
                for language_field in "${language_fields[@]}"; do
                    normalized_language="$(base_repo_normalize_language "$language_field" || true)"
                    if [[ -z "$normalized_language" ]]; then
                        base_repo_init_usage_error "Unsupported language '$language_field'. Expected one of: $(base_repo_supported_languages_display)."
                        return $?
                    fi
                    language_seen=0
                    for language in "${language_options[@]}"; do
                        if [[ "$language" == "$normalized_language" ]]; then
                            language_seen=1
                            break
                        fi
                    done
                    ((language_seen)) || language_options+=("$normalized_language")
                done
                shift 2
                ;;
            --language=*)
                language_option="${1#--language=}"
                if [[ -z "$language_option" ]]; then
                    base_repo_init_usage_error "Option '--language' requires a comma-separated language list."
                    return $?
                fi
                language_option="${language_option//[[:space:]]/}"
                if [[ "$language_option" == ,* || "$language_option" == *, || "$language_option" == *,,* ]]; then
                    base_repo_init_usage_error "Option '--language' must not contain empty entries."
                    return $?
                fi
                str_split language_fields "$language_option" ","
                for language_field in "${language_fields[@]}"; do
                    normalized_language="$(base_repo_normalize_language "$language_field" || true)"
                    if [[ -z "$normalized_language" ]]; then
                        base_repo_init_usage_error "Unsupported language '$language_field'. Expected one of: $(base_repo_supported_languages_display)."
                        return $?
                    fi
                    language_seen=0
                    for language in "${language_options[@]}"; do
                        if [[ "$language" == "$normalized_language" ]]; then
                            language_seen=1
                            break
                        fi
                    done
                    ((language_seen)) || language_options+=("$normalized_language")
                done
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
        pr_rerun_command="$(
            base_repo_init_pr_rerun_command \
                "$name" \
                "$root" \
                "$github_repo" \
                "$configure" \
                "$protect_default_branch" \
                "$configure_project" \
                "$project_title" \
                "$project_owner" \
                "$project_schema" \
                "$copy_project_fields_from" \
                "$agent_ready" \
                "$(base_repo_languages_csv "${language_options[@]}")" \
                "${initiative_options[@]}"
        )"
        base_repo_prepare_pr_branch "$dry_run" "$root" "$pr_branch" "$default_branch" || return 1
    fi

    base_repo_write_baseline "$dry_run" "$name" "$description" "$copyright_holder" "$root" "${language_options[@]}" || return 1
    if ((agent_ready)); then
        if [[ -n "$default_branch" && "$default_branch" != "<default branch>" ]]; then
            agent_default_branch="$default_branch"
        elif [[ "$dry_run" != "1" ]]; then
            agent_default_branch="$(base_repo_detect_default_branch "$root" 2>/dev/null || true)"
            [[ -n "$agent_default_branch" ]] || agent_default_branch="main"
        fi
        base_repo_write_init_agent_guidance "$dry_run" "$name" "$agent_default_branch" "./tests/validate.sh" "$root" || return 1
    fi

    if ((create_pr)); then
        if [[ "$dry_run" == "1" ]]; then
            base_repo_finish_pr_baseline "$dry_run" "$name" "$root" "$github_repo" "$pr_branch" "$default_branch" "$pr_rerun_command" "$agent_ready"
            return $?
        fi
        if base_repo_pr_baseline_has_changes "$root" "$agent_ready"; then
            base_repo_finish_pr_baseline "$dry_run" "$name" "$root" "$github_repo" "$pr_branch" "$default_branch" "$pr_rerun_command" "$agent_ready"
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
            base_repo_load_github_settings || return 1
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
                    0 \
                    "${initiative_options[@]}" || return 1
            fi
        else
            base_repo_print_init_github_skip_notice "$dry_run" "$name" "$root"
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
        printf "To update: git -C %s pull --ff-only\n" "$(base_repo_pretty_arg "$target")"
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
        printf "[DRY-RUN] Would clone %s (%s) into %s.\n" \
            "$repo" \
            "$clone_url" \
            "$(base_repo_pretty_arg "$target")"
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
    printf "Cloned '%s' to '%s'.\n" "$repo" "$target"
    if [[ -f "$target/base_manifest.yaml" ]]; then
        printf "Run 'basectl repo check %s' to verify the Base baseline.\n" \
            "$(base_repo_pretty_arg "$target")"
    fi
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
    local agent_ready=0
    local path=""
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
            --agent-ready)
                agent_ready=1
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
                if [[ -n "$path" ]]; then
                    base_repo_check_usage_error "The 'repo check' command accepts at most one path."
                    return $?
                fi
                path="$1"
                shift
                ;;
        esac
    done

    [[ -n "$path" ]] || path="."
    path="$(base_repo_target_path "$path")"
    base_repo_check_baseline "$path" || status=1
    if ((agent_ready)); then
        base_repo_check_agent_ready "$path" || status=1
    elif ((agent_guidance)); then
        base_repo_check_agent_guidance "$path" || status=1
    fi
    return "$status"
}

base_repo_configure() {
    local configure_project=1
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
            --replace-project)
                replace_project=1
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
                if [[ -n "$path" ]]; then
                    base_repo_configure_usage_error "The 'repo configure' command accepts at most one path."
                    return $?
                fi
                path="$1"
                shift
                ;;
        esac
    done

    [[ -n "$path" ]] || path="."
    path="$(base_repo_target_path "$path")"
    if [[ -z "$github_repo" ]]; then
        github_repo="$(base_repo_infer_github_repo "$path" || true)"
    fi
    [[ -n "$github_repo" ]] || {
        log_error "Unable to infer GitHub repository from '$path'."
        printf "       Inference requires a git remote named 'origin' that points to github.com.\n" >&2
        printf "       Pass --repo <owner/name> to configure explicitly, or run:\n" >&2
        printf "         git -C %s remote -v\n" "$(base_repo_pretty_arg "$path")" >&2
        printf "       to inspect the current remotes.\n" >&2
        return 1
    }

    if ((configure_project)); then
        base_repo_write_project_support_files "$dry_run" "$path" || return 1
    fi

    base_repo_load_github_settings || return 1
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
