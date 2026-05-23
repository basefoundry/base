from __future__ import annotations

import functools
import os
import sys
from pathlib import Path
from typing import Any, Callable

from .config import load_config
from .context import Context, reset_current_context, set_current_context
from .logging import configure_logger, log_invocation
from .paths import base_state_root, discover_manifest, make_run_id, normalize_cli_name, resolve_base_home
from .redaction import parameter_name_from_decls


def _require_click():
    try:
        import click
    except ImportError as exc:
        raise RuntimeError("Click is required for base_cli. Run 'basectl setup' to install it.") from exc
    return click


class App:
    def __init__(self, name: str | None = None, version: str | None = None) -> None:
        self.name = normalize_cli_name(name or sys.argv[0])
        self.version = version
        self._click_command = None
        self._command_func: Callable[..., Any] | None = None
        self._command_args: tuple[Any, ...] = ()
        self._command_kwargs: dict[str, Any] = {}

    def command(self, *command_args: Any, **command_kwargs: Any):
        def decorator(func: Callable[..., Any]):
            self._command_func = func
            self._command_args = command_args
            self._command_kwargs = command_kwargs
            return func

        return decorator

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.click_command(*args, **kwargs)

    @property
    def click_command(self) -> Any:
        if self._click_command is None:
            self._click_command = self._build_click_command()
        return self._click_command

    def _build_click_command(self) -> Any:
        if self._command_func is None:
            raise RuntimeError("No command has been registered on this base_cli.App.")

        click = _require_click()
        func = self._command_func
        sensitive_options = set(getattr(func, "__base_cli_sensitive_options__", set()))

        @functools.wraps(func)
        def wrapper(**kwargs: Any):
            standard = _pop_standard_options(kwargs)
            context = self._create_context(standard, sensitive_options)
            token = set_current_context(context)
            try:
                log_invocation(context.log, sys.argv, sensitive_options)
                if context.project_root is not None:
                    context.log.debug("project_root=%s", context.project_root)
                if context.manifest_path is not None:
                    context.log.debug("manifest_path=%s", context.manifest_path)
                return func(context, **kwargs)
            finally:
                reset_current_context(token)
                context.cleanup()

        for kind, param_decls, attrs in getattr(func, "__base_cli_param_specs__", []):
            if kind == "option":
                wrapper = click.option(*param_decls, **attrs)(wrapper)
            elif kind == "argument":
                wrapper = click.argument(*param_decls, **attrs)(wrapper)
        wrapper = _decorate_standard_options(click, wrapper, self.version)
        return click.command(*self._command_args, **self._command_kwargs)(wrapper)

    def _create_context(self, standard: dict[str, Any], sensitive_options: set[str]) -> Context:
        del sensitive_options
        run_id = make_run_id()
        manifest_path = discover_manifest(Path.cwd())
        project_root = manifest_path.parent if manifest_path is not None else None
        explicit_config = Path(standard["config"]).expanduser() if standard.get("config") else None
        config = load_config(project_root, explicit_config)

        environment = standard.get("environment") or config.get("environment") or "dev"
        debug = bool(standard.get("debug") or str(config.get("log_level", "")).lower() == "debug")
        keep_temp = bool(standard.get("keep_temp") or config.get("keep_temp"))

        state_dir = base_state_root() / "cli" / self.name
        log_dir = state_dir / "logs"
        cache_dir = state_dir / "cache"
        temp_dir = state_dir / "tmp" / run_id
        for directory in (log_dir, cache_dir, temp_dir):
            directory.mkdir(parents=True, exist_ok=True)

        log_file = Path(standard["log_file"]).expanduser() if standard.get("log_file") else log_dir / f"{run_id}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger = configure_logger(self.name, log_file, debug)
        logger.debug("cli=%s run_id=%s environment=%s", self.name, run_id, environment)

        return Context(
            cli_name=self.name,
            run_id=run_id,
            base_home=resolve_base_home(),
            project_root=project_root,
            manifest_path=manifest_path,
            state_dir=state_dir,
            log_dir=log_dir,
            cache_dir=cache_dir,
            temp_dir=temp_dir,
            log_file=log_file,
            config=config,
            environment=environment,
            debug=debug,
            keep_temp=keep_temp,
            log=logger,
        )


def command(*args: Any, **kwargs: Any):
    return App().command(*args, **kwargs)


def option(*param_decls: str, sensitive: bool = False, **attrs: Any):
    def decorator(func: Callable[..., Any]):
        specs = list(getattr(func, "__base_cli_param_specs__", []))
        specs.append(("option", param_decls, attrs))
        func.__base_cli_param_specs__ = specs
        if sensitive:
            options = set(getattr(func, "__base_cli_sensitive_options__", set()))
            options.add(parameter_name_from_decls(param_decls))
            func.__base_cli_sensitive_options__ = options
        return func

    return decorator


def argument(*param_decls: str, **attrs: Any):
    def decorator(func: Callable[..., Any]):
        specs = list(getattr(func, "__base_cli_param_specs__", []))
        specs.append(("argument", param_decls, attrs))
        func.__base_cli_param_specs__ = specs
        return func

    return decorator


def _decorate_standard_options(click: Any, func: Callable[..., Any], version: str | None):
    func = click.option("--log-file", type=click.Path(dir_okay=False), help="Override the persistent log file.")(func)
    func = click.option("--keep-temp", is_flag=True, help="Preserve this run's temp directory.")(func)
    func = click.option("--config", type=click.Path(dir_okay=False), help="Load an additional config file.")(func)
    func = click.option("--environment", help="Set the Base CLI environment.")(func)
    func = click.option("--debug", is_flag=True, help="Enable DEBUG logging on the user-facing stream.")(func)
    if version is not None:
        func = click.version_option(version)(func)
    return func


def _pop_standard_options(kwargs: dict[str, Any]) -> dict[str, Any]:
    standard = {}
    for key in ("debug", "environment", "config", "keep_temp", "log_file"):
        standard[key] = kwargs.pop(key, None)
    return standard
