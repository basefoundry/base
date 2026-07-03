# Setup Hooks Boundary

Base should not support arbitrary setup hooks in `base_manifest.yaml` right now.

This is a deliberate safety and product-boundary decision. Base setup should be
declarative, inspectable, idempotent, and diagnosable. Arbitrary hooks would let
projects run imperative shell code during setup before Base has a clear contract
for timing, dry-run behavior, interactivity, logging, failure handling, and
security review.

## Current Decision

Do not add fields such as:

```yaml
hooks:
  post_setup:
    - ./scripts/bootstrap.sh
```

Instead, use the typed contracts Base already understands:

- `brewfile` for ordinary macOS/Homebrew packages and casks
- `mise` for language runtimes, tool versions, environment variables, and tasks
- `ide` for supported IDE app, extension, and settings bootstrap
- `artifacts` for Base-managed artifacts
- `activate.source` for explicit activation-time shell scripts that run inside
  the interactive project runtime shell
- `test.command` or `test.mise` for project-owned test execution

`activate.source` is intentionally not a setup hook: it does not run during
`basectl setup`, `basectl check`, or `basectl doctor`, and it exists only for
shell state that must affect the activated interactive subshell.
See the `activate.source` field in [Architecture - Project Manifest](architecture.md#project-manifest)
for the full shell activation contract, including when it runs and its scope
relative to setup.

The `brewfile` delegate is platform-aware. Base runs `brew bundle` on macOS, but
on Ubuntu/Debian it treats Brewfiles as unsupported macOS package declarations
and continues through platform-native project setup such as `python.manager: uv`
or `mise: .mise.toml`.

When a project needs a product-specific guided installer or imperative
bootstrap, that logic should live in the project repository, for example:

```text
<project>/install.sh
```

That installer can explain product-specific context, clone or update repos,
handle project-specific credentials, and call Base commands in the right order.
See [project-installers.md](project-installers.md).

## Rationale

Unconstrained hooks create ambiguity Base cannot currently resolve:

- `basectl setup --dry-run` would need to know whether a hook is safe to skip,
  print, partially inspect, or emulate.
- `basectl check` and `basectl doctor` would need structured diagnostics for
  hook-owned state.
- Interactive hooks could block non-interactive setup and future CI flows.
- Shell snippets can hide package installs, credential prompts, network calls,
  long-running services, and state writes outside Base's ownership boundary.
- Hook ordering can become a hidden dependency system that is harder to reason
  about than explicit manifest fields.

Base should bias toward adding narrow, typed delegation points instead of a
generic escape hatch.

## Future Reconsideration Criteria

If a real project needs hooks and typed delegation is insufficient, Base should
first define a constrained contract. That contract must specify:

- allowed phases such as `pre_setup`, `post_setup`, or `verify`
- working directory and environment
- whether commands are lists of arguments or shell strings
- dry-run behavior
- interactivity rules
- timeout and signal behavior
- how setup, check, doctor, and future CI report hook state
- how failures are surfaced and whether later setup steps continue
- whether hooks are allowed to install software, start services, or request
  credentials

Until those semantics are explicit, project-owned installers remain the correct
place for imperative setup.
