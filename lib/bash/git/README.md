# `lib_git.sh`

Git helpers for Bash commands that need lightweight repository inspection or update behavior.

## Dependency

Source `lib/bash/std/lib_std.sh` before this library so logging and shared error handling are available.

## Public API

- `git_update_repo`
  Update a repository on branch `master`, optionally allowing tracked changes in one specific path.
- `git_get_current_branch`
  Return the current branch name through a caller-provided variable, or `detached head`.
- `check_script_up_to_date`
  Check whether a tracked script appears current relative to its configured upstream.

## Internal Helper

- `_git_only_path_dirty`
  Internal predicate used by `git_update_repo` when an allowed dirty path is provided.

## Usage

```bash
source "/absolute/path/to/lib/bash/std/lib_std.sh"
source "/absolute/path/to/lib/bash/git/lib_git.sh"

branch=""
git_get_current_branch "$PWD" branch
log_info "Current branch: $branch"
```

## Behavior Notes

- `git_update_repo` currently only attempts updates when the checked-out branch is `master`.
- `check_script_up_to_date` treats missing git state, untracked scripts, or missing upstreams as skip conditions rather than hard failures.

## Tests

BATS coverage lives in `tests/lib_git.bats`.
