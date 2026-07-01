# Source Control And Forge Support

Base is Git-based and GitHub-primary.

This page is the canonical contract for what that means. It separates the local
Base project loop, which is mostly forge-neutral once a Git checkout exists,
from the repository workflow automation that intentionally targets GitHub
today.

## Support Contract

Base assumes Git as the underlying source-control system.

Supported source-control baseline:

- Git repositories checked out on the local machine.
- Direct-child repository layouts under a shared workspace root.
- Project metadata declared through `base_manifest.yaml`.
- Git remotes hosted by GitHub, GitLab, Bitbucket, an internal Git server, or a
  local filesystem remote when the command only needs ordinary Git behavior.

Out of scope:

- Mercurial.
- Perforce.
- Subversion.
- Fossil.
- Other non-Git SCMs.

GitHub is the only first-class forge automation target today. Base can automate
GitHub repository creation and configuration, GitHub Issues, pull requests,
Projects, Actions-based intake, and GitHub Releases. It does not currently
provide equivalent automation for GitLab, Bitbucket, Azure DevOps, or other Git
forges.

## Command Compatibility

| Command area | Non-GitHub Git behavior |
|---|---|
| Local project loop: `projects list`, `setup`, `check`, `doctor`, `activate`, `run`, `test`, `build`, `demo`, `export-context` | Supported once the repository exists locally and has `base_manifest.yaml`. These commands use local files, project manifests, and ordinary process execution. |
| Git update: `update [project]` | Supported for ordinary Git checkouts when the repo is on its default branch and the worktree is clean enough for Base's update guardrails. |
| Remote diagnostics: `check [project]`, `doctor [project]` | Supported. Non-GitHub remotes are reported as non-GitHub providers and do not require GitHub CLI authentication. Optional network checks use Git reachability rather than forge APIs. |
| Workspace reports: `workspace status`, `workspace check`, `workspace doctor` | Supported. Workspace manifests can list GitLab, Bitbucket, internal Git, or local repository URLs as metadata for reporting. |
| Workspace manifest refresh: `workspace pull` | Supported for local paths, `file://` URLs, and raw `https://` manifest files. It updates the manifest file only; it does not clone or mutate project repositories. |
| Repository materialization: `repo clone`, `workspace clone`, `workspace init` when cloning repositories | GitHub-only today. These paths delegate to GitHub repository specs and should fail clearly when asked to materialize unsupported non-GitHub repositories. |
| Repository baseline: `repo init`, `repo check` | Local baseline files can be created and checked without GitHub, but the standard Base baseline is GitHub-flavored: `.github` workflows, pull request template, and Project intake files are part of that contract. |
| Repository automation: `repo configure`, `workspace configure` | GitHub-specific. `workspace configure` skips non-GitHub repositories, while `repo configure` requires an explicit or inferable GitHub repository. |
| GitHub workflow: `gh ...` | GitHub-specific by name and behavior. |
| Release publishing: `release publish` | GitHub Release publishing today. Release readiness commands also expect the manifest's current GitHub release metadata. |
| Documentation shortcut: `docs` | Opens the GitHub-hosted Base documentation entry point. |

## Non-GitHub Git Workspaces

A GitLab, Bitbucket, internal Git, or local Git repository can still use Base's
local control-plane loop:

1. Clone the repository with the normal Git tooling for that forge.
2. Place the checkout under `workspace.root`, or pass `--workspace <path>` when
   inspecting a different root.
3. Add a valid `base_manifest.yaml`.
4. Use `basectl projects list`, `basectl setup <project>`,
   `basectl check <project>`, `basectl doctor <project>`,
   `basectl test <project>`, `basectl run <project> <command>`, and related
   local project commands.

Workspace manifests may include non-GitHub Git URLs so reports can describe
the expected repository set. Today, those URLs are metadata for read-only
workspace reporting unless the materialization command explicitly documents
support for that URL shape. If a missing GitLab or Bitbucket repository needs
to be cloned, clone it manually with Git, then let Base discover and diagnose
the local checkout.

Avoid these commands unless GitHub is intentionally part of the repository
workflow:

- `basectl repo clone`
- `basectl repo configure`
- `basectl workspace clone`
- `basectl workspace init` when it must clone repositories
- `basectl workspace configure`
- `basectl gh ...`
- `basectl release publish`

## Future Forge Support

GitLab and Bitbucket are viable future support targets, but they should not be
added speculatively. The current product strategy is to prove the GitHub-first
model through real adoption before Base grows provider adapters.

If adoption proves the need, the right direction is a narrow forge-provider
boundary rather than scattered conditional logic. Likely adapter seams include:

- remote provider detection
- repository clone and creation
- issue and merge-request or pull-request workflows
- project or board metadata
- release publishing
- CI or workflow intake

Each provider should be added because a real workspace needs it, not because
Base wants to present itself as generally forge-independent.

## Clean Failure Expectations

GitHub-specific commands should not make a non-GitHub Git repository look
broken. They should either:

- skip that repository with an explicit non-GitHub explanation,
- fail with a direct "GitHub-only today" message, or
- point the user to the manual Git workflow when Base can still operate on the
  resulting local checkout.

The user should be able to distinguish "this repository is unhealthy" from
"this command is a GitHub automation surface and this repository uses another
forge."
