#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"

cd "$REPO_ROOT"

if [[ -z "${BASE_BASH_LIBS_DIR:-}" ]]; then
    for candidate in "$REPO_ROOT/../base-bash-libs/lib/bash" "$REPO_ROOT/../../base-bash-libs/lib/bash"; do
        if [[ -d "$candidate" ]]; then
            export BASE_BASH_LIBS_DIR="$candidate"
            break
        fi
    done
fi

if [[ -n "${PYTHON:-}" ]]; then
    PYTHON_BIN="$PYTHON"
elif [[ -x "$HOME/.base.d/base/.venv/bin/python" ]]; then
    PYTHON_BIN="$HOME/.base.d/base/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

export PYTHONPATH="$REPO_ROOT/cli/python:$REPO_ROOT/lib/python${PYTHONPATH:+:$PYTHONPATH}"

run_step() {
    printf '\n==> '
    printf '%q ' "$@"
    printf '\n'
    "$@"
}

run_step "$PYTHON_BIN" -m pytest tests/test_github_workflows.py
run_step "$PYTHON_BIN" -m pytest lib/python/base_cli/tests/test_logging.py
run_step "$PYTHON_BIN" -m pytest cli/python/base_projects/tests/test_workspace_manifest.py
run_step "$PYTHON_BIN" -m pytest cli/python/base_projects/tests/test_workspace_pull.py
run_step bats --filter "project installer template" cli/bash/commands/basectl/tests/repo.bats
run_step bats cli/bash/commands/basectl/tests/docs.bats
run_step bats cli/bash/commands/basectl/tests/help.bats
run_step bats cli/bash/commands/basectl/tests/completions.bats
