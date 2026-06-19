# Project Demo Workflow

Base demos are project-owned walkthrough scripts that Base can discover,
validate, and run through a common command:

```bash
basectl demo <project>
```

The demo feature is intentionally small. Base does not define a demo language,
dependency model, shell selector, or hidden setup hook. A project declares one
script, keeps that script in its repository, and tests a non-interactive path
for CI.

There are two demo layers:

- Base's self-demo lives in this repository and demonstrates Base itself.
- `basefoundry/base-demo` is a separate peer repository that demonstrates how a
  normal Base-managed project participates in the workflow.

Those layers should stay separate. `basectl demo base` must not depend on the
external `base-demo` repository, and `base-demo` should remain a normal project
rather than a hidden Base test fixture.

## Manifest Contract

Projects opt in through `base_manifest.yaml`:

```yaml
demo:
  script: ./demo/demo.sh
  description: Interactive walkthrough of this project
```

`demo.script` is required when `demo` is present. It must be a non-empty string,
relative to the project root, stay inside the project, point to a file, and be
executable.

`demo.description` is optional. It is human-facing metadata for documentation
and future listing surfaces; Base does not currently display it in command
output.

Unsupported `demo` keys fail manifest parsing. Keep project-specific setup,
dependency installation, and product logic inside existing Base contracts such
as `brewfile`, `artifacts`, `activate.source`, `commands`, and `test`.

## Command Behavior

`basectl demo [project]`:

1. Resolves the project through the same workspace discovery path as
   `basectl test` and `basectl run`. When the project is omitted, Base resolves
   the nearest `base_manifest.yaml` from the current directory.
2. Reads `demo.script` from the project manifest.
3. Validates that the script exists, is a file, is executable, and stays inside
   the project root.
4. Exports `BASE_PROJECT`, `BASE_PROJECT_ROOT`, `BASE_PROJECT_MANIFEST`, and
   `BASE_PROJECT_VENV_DIR`.
5. Prepends the project virtualenv `bin` directory to `PATH` when it exists.
6. Runs the script from the project root and returns the script exit status.

Useful forms:

```bash
basectl demo base-demo
basectl demo
basectl demo base-demo --dry-run
basectl demo base-demo -- --non-interactive
basectl demo base-demo --workspace ~/work -- --non-interactive
```

Arguments after `--` are passed to the demo script unchanged.

When no demo is declared, Base exits with a clear message telling the project to
add `demo.script` to its manifest.

## Writing Demo Scripts

A good project demo should:

- explain one workflow at a time
- run real project commands rather than only printing instructions
- stop on errors with a useful recovery hint
- avoid heavyweight installs, external accounts, and long-running services
- support `--non-interactive` so CI can run it without prompts
- reuse current Base contracts instead of inventing private setup hooks

For shell demos, the common shape is:

```bash
#!/usr/bin/env bash

non_interactive=0

while (($#)); do
  case "$1" in
    --non-interactive) non_interactive=1 ;;
    -h|--help) echo "Usage: demo/demo.sh [--non-interactive]"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

pause() {
  ((non_interactive)) && return 0
  printf 'Press Enter to continue...'
  read -r _ || return 1
}
```

Tests should cover at least:

- the demo script exists and is executable
- `base_manifest.yaml` declares the same script path
- `demo/demo.sh --non-interactive` runs without blocking
- meaningful demo steps call the expected project commands

## Base Self-Demo

Base has its own self-demo:

```bash
basectl demo base -- --non-interactive
```

That script lives in the Base repository at `demo/demo.sh`. It demonstrates the
Base control-plane workflow using Base itself and does not depend on the
external reference repository.

## Reference Project

The public reference repository is
[`basefoundry/base-demo`](https://github.com/basefoundry/base-demo).

`base-demo` serves two roles:

- a reference implementation for the files and conventions a small
  Base-managed repository should carry
- an interactive walkthrough that a new user can run to see the workflow in
  action

It is not primarily a test harness. Its tests prove that the walkthrough stays
executable, but its product role is onboarding and inspection.

Clone it next to Base:

```bash
git clone https://github.com/basefoundry/base.git
git clone https://github.com/basefoundry/base-demo.git
```

Then run:

```bash
basectl projects list
basectl setup base-demo
basectl check base-demo
basectl doctor base-demo
basectl test base-demo
basectl demo base-demo -- --non-interactive
```

`base-demo` is the reference implementation for a normal Base-managed project.
Base's self-demo is for the Base repository itself; `base-demo` is the separate
peer project that shows how another repository should participate.

Future specialized demos should use separate repositories, such as
`base-demo-kubernetes` or `base-demo-services`, when they need different
dependencies or storylines. Avoid using long-lived demo branches for distinct
demo products.

## Maintenance

When a Base change affects the demos, label the issue or PR with `needs-demo`
and include a `Demo Impact` section in the PR body. See
[Demo Maintenance](demo-maintenance.md).
