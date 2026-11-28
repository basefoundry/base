from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .project_config import ProjectConfig
from .project_git import checkout_root, infer_repo_from_git
from .project_model import ProjectArguments
from .project_schema import read_project_config


@dataclass(frozen=True)
class ResolvedProjectConfig:
    """A validated config and its authority to apply item defaults."""

    config: ProjectConfig = field(default_factory=ProjectConfig)
    path: Path | None = None
    explicit: bool = False
    reason: str = "no checkout"
    checkout_config: Path | None = None


def resolve_project_config(args: ProjectArguments, owner: str) -> ResolvedProjectConfig:
    """Discover schema settings only for the checkout's repo-named Project."""
    if args.config_path:
        path = Path(args.config_path)
        return ResolvedProjectConfig(config=read_project_config(path), path=path, explicit=True)
    root = checkout_root()
    repo = infer_repo_from_git() if root is not None else None
    if root is None or repo is None:
        return ResolvedProjectConfig(reason="no checkout with a GitHub origin")
    path = root / ".github" / "base-project.yml"
    checkout_config = path if path.exists() else None
    repo_owner, repo_name = repo.split("/", 1)
    mismatches: list[str] = []
    if owner != repo_owner:
        mismatches.append(f"Project owner '{owner}' differs from checkout owner '{repo_owner}'")
    if args.project_title != repo_name:
        mismatches.append(f"Project title '{args.project_title}' differs from checkout repository name '{repo_name}'")
    if args.command == "configure" and args.repo and args.repo != repo:
        mismatches.append(f"--repo '{args.repo}' differs from checkout repository '{repo}'")
    if mismatches:
        return ResolvedProjectConfig(reason="; ".join(mismatches), checkout_config=checkout_config)
    if checkout_config is None:
        return ResolvedProjectConfig(reason=f"no file at '{path}'")
    return ResolvedProjectConfig(config=read_project_config(path), path=path, checkout_config=path)


def render_config_resolution(resolved: ResolvedProjectConfig) -> None:
    if resolved.path is not None:
        source = "explicit --config" if resolved.explicit else "discovered; schema only"
        print(f"Config: {resolved.path} ({source}).")
    else:
        print(f"Config: no config ({resolved.reason}). Use --config <path> to apply a config deliberately.")
    if resolved.checkout_config is not None and not resolved.explicit:
        print("INFO    Item defaults apply only with explicit --config <path>.")
