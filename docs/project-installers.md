# Project Installers

Base should stay a developer workspace engine. Project-specific installers should
own the friendlier, product-specific onboarding experience.

This is an intentional product boundary. Base should not add `basectl onboard
<project>` for now. That command would make Base responsible for every
project's product narrative, repository bootstrap choices, credentials, and
next-step guidance. Those concerns change per project and are better owned by
the project itself.

This distinction matters because Base and a project installer serve different
audiences:

- `basectl setup` is for developers and technically-adjacent users who are
  willing to run a terminal command and read setup output.
- A project installer is for someone who wants to use a specific project and
  should not need to understand Base first.

For example, a future `banyanlabs/install.sh` can present Banyanlabs-specific
language, explain what will happen, bootstrap Base if needed, and then call Base
internally. Base should provide the reliable mechanics; Banyanlabs should provide
the product-shaped welcome mat.

## Responsibilities

Base owns:

- macOS workstation bootstrap primitives
- Homebrew, Xcode Command Line Tools, Base Python, and Base venv setup
- project discovery through `base_manifest.yaml`
- artifact reconciliation through `basectl setup`
- diagnostics through `basectl check` and `basectl doctor`
- shell integration through `basectl update-profile`

A project installer owns:

- project-specific framing and instructions
- preflight messaging for that project's audience
- choosing where the project workspace should live
- cloning or updating the project repository
- installing or locating Base
- calling Base commands in the right order
- explaining next steps after setup succeeds or fails

The installer should not reimplement Base's setup logic. It should call Base.

## Recommended Flow

A project installer should be a thin Bash script with a predictable sequence:

```bash
#!/usr/bin/env bash
set -euo pipefail

project_name="banyanlabs"
workspace_dir="${HOME}/work"
base_dir="${workspace_dir}/base"
project_dir="${workspace_dir}/${project_name}"

mkdir -p "$workspace_dir"

if [[ ! -d "$base_dir/.git" ]]; then
    curl -fsSL https://raw.githubusercontent.com/codeforester/base/master/install.sh | BASE_INSTALL_DIR="$base_dir" bash
else
    git -C "$base_dir" pull --ff-only
fi

if [[ ! -d "$project_dir/.git" ]]; then
    git clone https://github.com/codeforester/banyanlabs.git "$project_dir"
else
    git -C "$project_dir" pull --ff-only
fi

"$base_dir/bin/basectl" setup --manifest "$project_dir/base_manifest.yaml" "$project_name"
"$base_dir/bin/basectl" update-profile
```

This is only a sketch. A real installer should add friendlier output, better
error handling, and project-specific next steps.

If a project installer uses Base's standalone installer, it should still avoid
reimplementing Base setup. Use `BASE_INSTALL_DIR` or `install.sh --dir <path>` to
choose the Base checkout location, and use `--no-profile` if the project
installer wants to defer shell startup integration until later.

## User Experience Guidelines

Project installers should:

- say what they are about to do before making changes
- keep project-specific language in the project, not in Base
- call `basectl check` or `basectl doctor` when setup fails
- point users to the project documentation for next steps
- avoid hiding the underlying Base command that failed

Project installers should not:

- duplicate Homebrew, Python, venv, or artifact reconciliation logic
- write directly into Base-managed shell startup sections
- make Base itself responsible for product-specific onboarding
- assume every Base-managed project has the same audience

## Relationship To `basectl onboard`

`basectl onboard` is still useful, but it should target a different layer. Its
command design is captured in [basectl-onboard.md](basectl-onboard.md).

`basectl onboard` should be a guided Base setup experience for
technically-adjacent users who are installing Base itself. A project installer
should be a guided product setup experience for users installing a particular
project.

In short:

- use `basectl setup` for direct developer setup
- use `basectl onboard` for guided Base setup
- use `<project>/install.sh` for guided project setup

Keeping these layers separate lets Base stay small and reusable while each
project can speak naturally to its own users.
