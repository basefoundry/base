from __future__ import annotations

import contextvars
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import UserConfig, UserIdeConfig


_current_context: contextvars.ContextVar[Context | None] = contextvars.ContextVar(
    "base_cli_current_context",
    default=None,
)


def _default_user_config() -> UserConfig:
    return UserConfig(raw={}, ide=UserIdeConfig(enabled=None, preferences={}))


@dataclass
class Context:
    """Runtime state and cleanup hooks available to an active Base CLI command."""

    cli_name: str
    run_id: str
    state_dir: Path
    log_dir: Path
    cache_dir: Path
    temp_dir: Path
    log_file: Path | None
    config: dict
    environment: str
    debug: bool
    keep_temp: bool
    log: logging.Logger
    dry_run: bool = False
    base_home: Path | None = None
    project_root: Path | None = None
    manifest_path: Path | None = None
    project_name: str | None = None
    history_scope: str = "primary"
    history_parent_run_id: str | None = None
    user_config: UserConfig = field(default_factory=_default_user_config)
    cleanup_hooks: list[Callable[[], None]] = field(default_factory=list)
    workspace_root: Path | None = None
    quiet: bool = False
    runtime_owner: str = "base"
    owner_root: Path | None = None
    run_root: Path | None = None

    def on_cleanup(self, hook: Callable[[], None]) -> None:
        self.cleanup_hooks.append(hook)

    def bind_project(self, project_name: str | None, project_root: Path, manifest_path: Path | None = None) -> None:
        """Bind the selected project to this invocation's history context."""
        self.project_name = project_name
        self.project_root = project_root.resolve()
        self.manifest_path = manifest_path.resolve() if manifest_path is not None else None

    def cleanup(self) -> None:
        for hook in self.cleanup_hooks:
            try:
                hook()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.log.warning("Cleanup hook failed: %s", exc)
        if not self.keep_temp and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                for parent in (self.temp_dir.parent, self.temp_dir.parent.parent):
                    try:
                        parent.rmdir()
                    except OSError:
                        break
            except OSError as exc:
                self.log.warning("Temp directory cleanup failed for '%s': %s", self.temp_dir, exc)
        for handler in list(self.log.handlers):
            try:
                handler.flush()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.log.warning("Log handler flush failed: %s", exc)
            try:
                handler.close()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.log.warning("Log handler close failed: %s", exc)
            self.log.removeHandler(handler)


def set_current_context(context: Context | None) -> contextvars.Token[Context | None]:
    return _current_context.set(context)


def reset_current_context(token: contextvars.Token[Context | None]) -> None:
    _current_context.reset(token)


def get_current_context() -> Context:
    context = _current_context.get()
    if context is None:
        raise RuntimeError("base_cli context is not active. Run inside a base_cli.App command.")
    return context
