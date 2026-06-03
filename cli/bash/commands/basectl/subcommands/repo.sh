#!/usr/bin/env bash

[[ -n "${_base_repo_subcommand_sourced:-}" ]] && return
_base_repo_subcommand_sourced=1
readonly _base_repo_subcommand_sourced

BASE_REPO_BASELINE_FILES=(
    README.md
    VERSION
    CHANGELOG.md
    CONTRIBUTING.md
    LICENSE
    .gitignore
    base_manifest.yaml
    tests/validate.sh
    .github/workflows/tests.yml
)

base_repo_subcommand_usage() {
    cat <<'EOF'
Usage:
  basectl repo init <name> [options]
  basectl repo check [path] [options]
  basectl repo configure [path] [options]

Options:
  --path <path>                 Target path for repo init. Defaults to workspace root plus <name>.
  --repo <owner/name>           GitHub repository to configure.
  --description <text>          Repository description for generated README.
  --copyright-holder <name>     Copyright holder for generated LICENSE. Defaults to git config user.name.
  --no-configure                Skip GitHub configuration during repo init.
  --dry-run                     Print planned changes without applying them.
  -v                            Enable DEBUG logging for this subcommand.
  -h, --help                    Show this help text.

Create, check, and configure a standard Base-managed repository baseline.
EOF
}

base_repo_usage_error() {
    base_repo_subcommand_usage >&2
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

base_repo_target_path() {
    local path="$1"
    local parent name

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
        "~")
            printf '%s\n' "$HOME"
            ;;
        "~/"*)
            printf '%s/%s\n' "$HOME" "${path#~/}"
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

base_repo_baseline_year() {
    date +%Y
}

base_repo_write_stream() {
    local dry_run="$1"
    local target="$2"

    if [[ -e "$target" ]]; then
        log_info "Repository baseline file already exists at '$target'; leaving it unchanged."
        return 0
    fi

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create '%s'.\n" "$target"
        return 0
    fi

    mkdir -p "$(dirname -- "$target")"
    cat > "$target"
}

base_repo_write_executable_stream() {
    local dry_run="$1"
    local target="$2"

    if [[ -e "$target" ]]; then
        log_info "Repository baseline file already exists at '$target'; leaving it unchanged."
        return 0
    fi

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create executable '%s'.\n" "$target"
        return 0
    fi

    mkdir -p "$(dirname -- "$target")"
    cat > "$target"
    chmod +x "$target"
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
3. Use a focused branch and pull request for each issue.
4. Run the project checks before opening or updating a pull request.

Useful commands:

\`\`\`bash
basectl check $name
basectl doctor $name
basectl test $name
\`\`\`
EOF
}

base_repo_write_license() {
    local copyright_holder="$2"
    local dry_run="$1"
    local root="$3"
    local year

    year="$(base_repo_baseline_year)"
    base_repo_write_stream "$dry_run" "$root/LICENSE" <<EOF
MIT License

Copyright (c) $year $copyright_holder

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
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
  LICENSE
  base_manifest.yaml
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

base_repo_write_baseline() {
    local copyright_holder="$4"
    local description="$3"
    local dry_run="$1"
    local name="$2"
    local root="$5"
    local status=0

    if [[ "$dry_run" != "1" ]]; then
        mkdir -p "$root" || return 1
    fi

    base_repo_write_readme "$dry_run" "$name" "$description" "$root" || status=1
    base_repo_write_version "$dry_run" "$root" || status=1
    base_repo_write_changelog "$dry_run" "$name" "$root" || status=1
    base_repo_write_contributing "$dry_run" "$name" "$root" || status=1
    base_repo_write_license "$dry_run" "$copyright_holder" "$root" || status=1
    base_repo_write_gitignore "$dry_run" "$root" || status=1
    base_repo_write_manifest "$dry_run" "$name" "$root" || status=1
    base_repo_write_validate_script "$dry_run" "$root" || status=1
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

    if [[ "$dry_run" == "1" ]]; then
        printf "[DRY-RUN] Would create GitHub repository '%s' if it does not already exist.\n" "$repo"
        return 0
    fi

    base_repo_require_gh || return 1
    if gh repo view "$repo" >/dev/null 2>&1; then
        log_info "GitHub repository '$repo' already exists."
        return 0
    fi

    log_info "Creating GitHub repository '$repo'."
    gh repo create "$repo" --public --description "$description"
}

base_repo_configure_github() {
    local dry_run="$1"
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

    return "$status"
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

base_repo_init() {
    local configure=1
    local copyright_holder=""
    local description=""
    local dry_run=0
    local github_repo=""
    local name=""
    local path=""
    local root

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_subcommand_usage
                return 0
                ;;
            --path)
                [[ -n "${2:-}" ]] || {
                    base_repo_usage_error "Option '--path' requires an argument."
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
                    base_repo_usage_error "Option '--repo' requires an argument."
                    return $?
                }
                github_repo="$2"
                shift 2
                ;;
            --repo=*)
                github_repo="${1#--repo=}"
                shift
                ;;
            --description)
                [[ -n "${2:-}" ]] || {
                    base_repo_usage_error "Option '--description' requires an argument."
                    return $?
                }
                description="$2"
                shift 2
                ;;
            --copyright-holder)
                [[ -n "${2:-}" ]] || {
                    base_repo_usage_error "Option '--copyright-holder' requires an argument."
                    return $?
                }
                copyright_holder="$2"
                shift 2
                ;;
            --no-configure)
                configure=0
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
                base_repo_usage_error "Unknown repo init option '$1'."
                return $?
                ;;
            *)
                if [[ -n "$name" ]]; then
                    base_repo_usage_error "The 'repo init' command accepts exactly one repository name."
                    return $?
                fi
                name="$1"
                shift
                ;;
        esac
    done

    [[ -n "$name" ]] || {
        base_repo_usage_error "Repository name is required."
        return $?
    }
    base_repo_validate_name "$name" || return 2
    [[ -n "$path" ]] || path="$(base_repo_default_target_path "$name")"
    [[ -n "$description" ]] || description="$(base_repo_default_description "$name")"
    [[ -n "$copyright_holder" ]] || copyright_holder="$(base_repo_default_copyright_holder)"
    root="$(base_repo_target_path "$path")"

    base_repo_write_baseline "$dry_run" "$name" "$description" "$copyright_holder" "$root" || return 1

    if ((configure)); then
        if [[ -z "$github_repo" ]]; then
            github_repo="$(base_repo_infer_github_repo "$root" || true)"
        fi
        if [[ -n "$github_repo" ]]; then
            base_repo_ensure_github_repo "$dry_run" "$github_repo" "$description" || return 1
            base_repo_configure_github "$dry_run" "$github_repo" || return 1
        else
            if [[ "$dry_run" == "1" ]]; then
                printf "[DRY-RUN] Would not create or configure a GitHub repository because no GitHub repo was provided or inferred. Pass --repo <owner/name> to include GitHub repository creation and configuration.\n"
            else
                log_info "Skipping GitHub repository creation and configuration because no GitHub repo was provided or inferred."
            fi
        fi
    fi
}

base_repo_check() {
    local path="."

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_subcommand_usage
                return 0
                ;;
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_usage_error "Unknown repo check option '$1'."
                return $?
                ;;
            *)
                if [[ "$path" != "." ]]; then
                    base_repo_usage_error "The 'repo check' command accepts at most one path."
                    return $?
                fi
                path="$1"
                shift
                ;;
        esac
    done

    path="$(base_repo_target_path "$path")"
    base_repo_check_baseline "$path"
}

base_repo_configure() {
    local dry_run=0
    local github_repo=""
    local path="."

    while (($#)); do
        case "$1" in
            -h|--help|help)
                base_repo_subcommand_usage
                return 0
                ;;
            --repo)
                [[ -n "${2:-}" ]] || {
                    base_repo_usage_error "Option '--repo' requires an argument."
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
            -v)
                set_log_level DEBUG
                export LOG_DEBUG=1
                shift
                ;;
            -*)
                base_repo_usage_error "Unknown repo configure option '$1'."
                return $?
                ;;
            *)
                if [[ "$path" != "." ]]; then
                    base_repo_usage_error "The 'repo configure' command accepts at most one path."
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

    base_repo_configure_github "$dry_run" "$github_repo"
}

base_repo_subcommand_main() {
    local command="${1:-}"

    case "$command" in
        -h|--help|help|"")
            base_repo_subcommand_usage
            return 0
            ;;
        init)
            shift
            base_repo_init "$@"
            ;;
        check)
            shift
            base_repo_check "$@"
            ;;
        configure)
            shift
            base_repo_configure "$@"
            ;;
        *)
            base_repo_usage_error "Unknown repo command '$command'."
            ;;
    esac
}
