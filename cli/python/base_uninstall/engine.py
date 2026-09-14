from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import base_cli
from base_cli.paths import runtime_slug
from base_cli_adapters.config import load_user_config
from base_cli_adapters.config import user_config_path
from base_cli_adapters.paths import base_cache_root
from base_cli_adapters.paths import base_state_root
from base_cli_profile import base_cli_app
from base_projects import engine as project_engine
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_setup.manifest_loader import ManifestError
from base_trust.trust_store import TRUST_RELATIVE_ROOT


PROFILE_FILES = (".bash_profile", ".bashrc", ".zprofile", ".zshrc")
PROFILE_MARKERS = tuple(
    (
        f"# >>> base: {name.removeprefix('.')} managed >>>",
        f"# <<< base: {name.removeprefix('.')} managed <<<",
    )
    for name in PROFILE_FILES
)


app = base_cli_app(
    name="base_uninstall",
    help="Remove Base-managed local state and verify the result.",
)


class UninstallError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectTarget:
    name: str
    root: Path
    manifest_path: Path


@dataclass(frozen=True)
class Resource:
    path: Path
    description: str


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("project", required=False)
@base_cli.option("--all", "all_projects", is_flag=True, help="Remove all Base-managed local state.")
@base_cli.option("--workspace", help="Workspace directory used to resolve the project name.")
@base_cli.option("--dry-run", is_flag=True, help="Preview removal without changing files.")
@base_cli.option("--yes", is_flag=True, help="Apply the removal after reviewing the plan.")
@base_cli.option("--verify", is_flag=True, help="Verify that the selected Base-managed state is absent.")
def run(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements
    ctx: base_cli.Context,
    project: str | None,
    all_projects: bool,
    workspace: str | None,
    dry_run: bool,
    yes: bool,
    verify: bool,
) -> int:
    if all_projects and project is not None:
        ctx.log.error("Option '--all' cannot be combined with a project name.")
        return base_cli.ExitCode.USAGE_ERROR
    if not all_projects and project is None:
        ctx.log.error("Provide a project name or use '--all'.")
        return base_cli.ExitCode.USAGE_ERROR
    if dry_run and yes:
        ctx.log.error("Options '--dry-run' and '--yes' cannot be used together.")
        return base_cli.ExitCode.USAGE_ERROR
    if verify and (dry_run or yes):
        ctx.log.error("Option '--verify' cannot be combined with '--dry-run' or '--yes'.")
        return base_cli.ExitCode.USAGE_ERROR

    target: ProjectTarget | None = None
    if project is not None:
        try:
            resolved = project_engine.resolve_named_project(ctx, project, workspace)
        except (ProjectDiscoveryError, ManifestError) as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.FAILURE
        target = ProjectTarget(resolved.name, resolved.root, resolved.manifest_path)

    try:
        if verify:
            return verify_state(target)
        return uninstall_state(target, apply=yes, dry_run=dry_run)
    except (OSError, RuntimeError, ValueError, UninstallError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE


def uninstall_state(target: ProjectTarget | None, *, apply: bool, dry_run: bool) -> int:
    home = Path.home()
    cache_root = base_cache_root()
    resources = resources_for_target(target, home, cache_root)
    workspace_config = workspace_config_present(home) if target is None else False

    if target is None:
        print("Base uninstall --all")
        if apply:
            print("Shell startup: basectl update-profile --remove")
        else:
            print("Shell startup: would run basectl update-profile --remove --dry-run")
        if workspace_config:
            print(f"{'Removing' if apply else 'Would remove'} workspace settings from '{user_config_path(home)}'.")
    else:
        print(f"Base uninstall: {target.name}")
        print(f"Project manifest: {target.manifest_path}")

    if apply:
        validate_removal(resources, home, cache_root, clear_workspace=workspace_config)
        for resource in resources:
            remove_resource(resource)
        if workspace_config:
            clear_workspace_config(home)
        print(f"Removed {len(resources)} Base-managed resource(s).")
        return base_cli.ExitCode.SUCCESS

    if not resources and not workspace_config:
        print("No Base-managed state matched the uninstall scope.")
    else:
        for resource in resources:
            print(f"Would remove\t{resource.description}\t{resource.path}")
        if workspace_config:
            print(f"Would remove\tworkspace settings\t{user_config_path(home)}")
    print("[DRY-RUN] No files were changed." if dry_run or not apply else "")
    return base_cli.ExitCode.SUCCESS


def resources_for_target(target: ProjectTarget | None, home: Path, cache_root: Path) -> tuple[Resource, ...]:
    if target is None:
        return all_resources(home, cache_root)
    return project_resources(target, home, cache_root)


def project_resources(target: ProjectTarget, home: Path, cache_root: Path) -> tuple[Resource, ...]:
    resources: list[Resource] = []
    trust_root = base_state_root(home) / TRUST_RELATIVE_ROOT
    for path in matching_trust_records(trust_root, target):
        resources.append(Resource(path, "manifest command trust record"))

    project_state = base_state_root(home) / target.name
    add_existing_resource(resources, project_state / "checks", "project manifest/check state")
    add_existing_resource(resources, project_state / ".venv", "external Base-managed project virtualenv")
    add_existing_resource(
        resources,
        cache_root / "projects" / runtime_slug(target.name),
        "project runtime cache namespace",
    )
    return tuple(resources)


def all_resources(home: Path, cache_root: Path) -> tuple[Resource, ...]:
    resources: list[Resource] = []
    state_root = base_state_root(home)
    add_existing_resource(resources, state_root / TRUST_RELATIVE_ROOT, "all manifest command trust records")
    add_existing_resource(resources, state_root / "profile.conf", "Base profile preferences")

    if state_root.is_dir() and not state_root.is_symlink():
        for child in sorted(state_root.iterdir(), key=lambda path: path.name):
            if child.name == "trust" or not child.is_dir() or child.is_symlink():
                continue
            add_existing_resource(resources, child / "checks", f"{child.name} manifest/check state")
            add_existing_resource(resources, child / ".venv", f"{child.name} external Base-managed virtualenv")

    add_existing_resource(resources, cache_root / "base" / "cache", "Base persistent cache")
    add_existing_resource(resources, cache_root / "projects", "all project runtime cache namespaces")
    return tuple(resources)


def matching_trust_records(trust_root: Path, target: ProjectTarget) -> tuple[Path, ...]:
    if not trust_root.is_dir() or trust_root.is_symlink():
        return ()
    matches: list[Path] = []
    for path in sorted(trust_root.glob("*.json"), key=str):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        project = payload.get("project")
        if not isinstance(project, dict):
            continue
        if (
            project.get("name", project.get("project_name")) == target.name
            and project.get("root") == str(target.root)
            and project.get("manifest") == str(target.manifest_path)
        ):
            matches.append(path)
    return tuple(matches)


def add_existing_resource(resources: list[Resource], path: Path, description: str) -> None:
    if path.exists() or path.is_symlink():
        resources.append(Resource(path, description))


def validate_removal(
    resources: tuple[Resource, ...],
    home: Path,
    cache_root: Path,
    *,
    clear_workspace: bool,
) -> None:
    for resource in resources:
        if path_has_symlink(resource.path, (base_state_root(home), cache_root)):
            raise UninstallError(f"Refusing to remove symlinked Base state '{resource.path}'.")
    if clear_workspace and user_config_path(home).is_symlink():
        raise UninstallError(f"Refusing to rewrite symlinked Base config '{user_config_path(home)}'.")


def remove_resource(resource: Resource) -> None:
    path = resource.path
    if path.is_symlink():
        raise UninstallError(f"Refusing to remove symlinked Base state '{path}'.")
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def path_has_symlink(path: Path, roots: tuple[Path, ...]) -> bool:
    for root in roots:
        try:
            path.absolute().relative_to(root.absolute())
        except ValueError:
            continue
        current = path
        while True:
            if current.is_symlink():
                return True
            if current == root:
                break
            current = current.parent
    return False


def workspace_config_present(home: Path) -> bool:
    path = user_config_path(home)
    try:
        config = load_user_config(home)
    except (RuntimeError, ValueError) as exc:
        raise UninstallError(f"Unable to read Base config '{path}': {exc}") from exc
    return isinstance(config.get("workspace"), dict)


def clear_workspace_config(home: Path) -> None:
    path = user_config_path(home)
    try:
        config = load_user_config(home)
    except (RuntimeError, ValueError) as exc:
        raise UninstallError(f"Unable to read Base config '{path}': {exc}") from exc
    if "workspace" not in config:
        return
    config.pop("workspace", None)
    write_yaml_atomically(path, config)


def write_yaml_atomically(path: Path, payload: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise UninstallError(
            "PyYAML is required to update Base config. Run 'basectl setup' before uninstalling workspace state."
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        mode = 0o600
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            yaml.safe_dump(payload, handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.chmod(mode)
        os.replace(temp_path, path)
    except OSError as exc:
        raise UninstallError(f"Unable to update Base config '{path}': {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def verify_state(target: ProjectTarget | None) -> int:
    home = Path.home()
    cache_root = base_cache_root()
    resources = resources_for_target(target, home, cache_root)
    failures = [resource for resource in resources if resource.path.exists() or resource.path.is_symlink()]

    if target is None:
        if workspace_config_present(home):
            failures.append(Resource(user_config_path(home), "workspace settings"))
        if profile_residue(home):
            failures.append(Resource(home, "managed shell startup section"))

    scope = "all Base-managed state" if target is None else f"project '{target.name}' Base-managed state"
    if failures:
        print(f"Verification failed for {scope}:")
        for resource in failures:
            print(f"Remaining\t{resource.description}\t{resource.path}")
        return base_cli.ExitCode.FAILURE
    print(f"Verification passed: no {scope} remains.")
    return base_cli.ExitCode.SUCCESS


def profile_residue(home: Path) -> bool:
    for filename, (start, end) in zip(PROFILE_FILES, PROFILE_MARKERS, strict=True):
        path = home / filename
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if start in text or end in text:
            return True
    return False


__all__ = [
    "app",
    "main",
    "profile_residue",
    "verify_state",
]
