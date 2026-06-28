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
- imperative setup steps that are not yet covered by a typed Base manifest
  contract
- explaining next steps after setup succeeds or fails

The installer should not reimplement Base's setup logic. It should call Base.

## Recommended Flow

Start from Base's maintained template, then customize the project-owned copy:

```bash
basectl repo installer-template
basectl repo installer-template install.sh
basectl repo installer-template --print
basectl repo installer-template install.sh --pr --dry-run
```

With no path, the command writes an executable `install.sh` in the current
directory. With a path, it writes the template there. Use `--print` when you want
to inspect or pipe the maintained template. Existing files are left unchanged so
project customizations are not overwritten.

Use `--pr` when the generated installer should be reviewed before landing. The
target path must be inside a clean Git worktree, the GitHub repository is
inferred from `origin` unless `--repo <owner/name>` is provided, and Base opens
a draft pull request after committing only the generated installer file.

For a project such as Banyan Labs, the generated script should change the
project-owned values at the top:

```bash
PROJECT_NAME="${PROJECT_NAME:-banyanlabs}"
PROJECT_REPO_URL="${PROJECT_REPO_URL:-https://github.com/basefoundry/banyanlabs.git}"
WORKSPACE_DIR="${WORKSPACE_DIR:-$HOME/work}"
BASE_DIR="${BASE_DIR:-$WORKSPACE_DIR/base}"
PROJECT_DIR="${PROJECT_DIR:-$WORKSPACE_DIR/$PROJECT_NAME}"
BASE_INSTALL_URL="${BASE_INSTALL_URL:-https://raw.githubusercontent.com/basefoundry/base/HEAD/install.sh}"
BASE_INSTALL_SHA256="${BASE_INSTALL_SHA256:-}"
RUN_UPDATE_PROFILE="${RUN_UPDATE_PROFILE:-true}"
```

`BASE_INSTALL_SHA256` is empty by default because the maintained template points
at Base's mutable `HEAD/install.sh`. When a project pins `BASE_INSTALL_URL` to a
tag, commit, or project-owned copy, set `BASE_INSTALL_SHA256` to that installer's
SHA-256 digest. The template verifies the downloaded installer before executing
it and stops immediately on a mismatch. Update the digest whenever the pinned
installer content changes:

```bash
curl -fsSL "$BASE_INSTALL_URL" | shasum -a 256
```

It should also replace the generic success text with project-specific next
steps, for example:

```bash
log "Banyan Labs setup is complete."
log "Next: open the project README and run the first Banyan Labs smoke test."
```

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

`basectl onboard [project]` should be a guided Base setup experience for
technically-adjacent users who want Base to reconcile its generic machine and
project primitives. A project installer should be a guided product setup
experience for users installing a particular project.

In short:

- use `basectl setup` for direct developer setup
- use `basectl onboard [project]` for guided Base setup and generic project reconciliation
- use `<project>/install.sh` for guided project setup

Keeping these layers separate lets Base stay small and reusable while each
project can speak naturally to its own users.
