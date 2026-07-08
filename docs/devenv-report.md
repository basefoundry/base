# Nix/devenv Compatibility Report

`basectl devenv-report [project]` reads a Base project manifest and reports how
its fields map to a possible Nix/devenv setup. It does not generate Nix files,
invoke Nix, install packages, or execute project commands.

```bash
basectl devenv-report demo
basectl devenv-report demo --format json
```

The report classifies each present manifest field into one of four categories:

- `supported`: information Base can carry into Nix/devenv planning directly
- `unsupported`: host-specific or out-of-scope data that Base should not
  translate automatically
- `lossy`: information that might inform Nix/devenv, but needs explicit mapping
  policy before generation would be safe
- `project-owned`: commands, checks, demos, or shell behavior that should remain
  owned by the project manifest or project tools

JSON output is deterministic and includes per-classification counts:

```bash
basectl devenv-report demo --format json
```

Use this command when evaluating whether a Base-managed project is a good
candidate for Nix/devenv support. Treat it as a compatibility report, not as a
generator.
