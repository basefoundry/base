# Project Installer Template Design

Issue: #512

## Goal

Give Base-managed projects a maintained starter installer they can copy or
generate, while keeping project-specific language, credentials, and final
onboarding steps inside the project repository.

## Selected Approach

Use a command-backed template:

- add a checked-in `templates/project-install.sh`
- add `basectl repo installer-template [path]`
- print the template to stdout when no path is provided
- write an executable script when a path is provided

This is narrower than adding a full project installer generator with many
project-specific flags, but stronger than documentation-only guidance. Base owns
the reusable mechanics and a stable starting point; each project owns the copy
it publishes.

## Alternatives Considered

1. **Checked-in template only.** Lowest implementation cost, but users have to
   know where to find it and how to copy it correctly.
2. **`basectl repo init --installer`.** Convenient for new repos, but less
   useful for existing repos and expands `repo init` option scope.
3. **`basectl repo installer-template`.** Discoverable, works for existing and
   new repos, and keeps installer generation separate from baseline generation.

The third option is the chosen slice.

## Template Behavior

The template will be a valid Bash script with editable defaults at the top:

- `PROJECT_NAME`
- `PROJECT_REPO_URL`
- `WORKSPACE_DIR`
- `BASE_DIR`
- `PROJECT_DIR`
- `BASE_INSTALL_URL`
- `RUN_UPDATE_PROFILE`

The script will:

1. create or locate the workspace directory
2. install or update Base using Base's maintained `install.sh`
3. clone or update the target project repository
4. run `basectl setup --manifest "$PROJECT_DIR/base_manifest.yaml" "$PROJECT_NAME"`
5. optionally run `basectl update-profile`
6. run or recommend `basectl doctor "$PROJECT_NAME"` when project setup fails
7. leave success messaging and next steps as project-owned text

The template will preserve underlying command output by running commands
directly and printing the command before it runs. It will not reimplement
Homebrew, Python, virtualenv, or artifact reconciliation logic.

## Command Behavior

`basectl repo installer-template` with no path writes the template to stdout.

`basectl repo installer-template <path>` writes an executable file, creating
parent directories as needed. Like other repo baseline writers, it leaves an
existing file unchanged rather than overwriting local project customizations.

`--dry-run` with a path reports the planned executable creation and writes no
file.

## Documentation

Update `docs/project-installers.md` so the recommended flow points to the
template command first, then shows the kind of customization a project such as
Banyan Labs should make: project name, repo URL, workspace default, friendly
success message, and project-specific next steps.

Update `docs/README.md` only if needed; the existing Project Installers entry is
already present.

## Tests

Add BATS coverage for:

- repo help lists `installer-template`
- printing the template to stdout
- writing an executable installer template to a requested path
- leaving an existing installer unchanged
- dry-run not writing the file

Run ShellCheck on the checked-in template, then the full `env -u BASE_HOME
./bin/base-test` suite.
