from __future__ import annotations

import functools
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from .config import load_config, read_user_config
from .context import Context, reset_current_context, set_current_context
from .logging import configure_logger, log_invocation
from .paths import base_cache_root, discover_manifest, make_run_id, normalize_cli_name, resolve_base_home
from .redaction import parameter_name_from_decls


def _require_click():
    try:
        import click
    except ImportError as exc:
        raise RuntimeError("Click is required for base_cli. Run 'basectl setup' to install it.") from exc
    return click


def _empty_group() -> None:
    return None


class App:
    def __init__(
        self,
        name: str | None = None,
        version: str | None = None,
        log_to_file: bool = True,
        max_log_files: int | None = None,
    ) -> None:
        if max_log_files is not None and max_log_files < 1:
            raise ValueError("max_log_files must be greater than 0 when set.")
        self.name = normalize_cli_name(name or sys.argv[0])
        self.version = version
        self.log_to_file = log_to_file
        self.max_log_files = max_log_files
        self._click_command = None
        self._command_func: Callable[..., Any] | None = None
        self._command_args: tuple[Any, ...] = ()
        self._command_kwargs: dict[str, Any] = {}
        self._subcommands: list[tuple[tuple[Any, ...], dict[str, Any], Callable[..., Any]]] = []

    def command(self, *command_args: Any, **command_kwargs: Any):
        def decorator(func: Callable[..., Any]):
            if self._subcommands:
                raise RuntimeError(
                    f"App '{self.name}' already has registered subcommands. "
                    "Use @app.subcommand() for additional entry points."
                )
            if self._command_func is not None:
                raise RuntimeError(
                    f"App '{self.name}' already has a registered command. "
                    "Use subcommands for multiple entry points."
                )
            self._command_func = func
            self._command_args = command_args
            self._command_kwargs = command_kwargs
            return func

        return decorator

    def subcommand(self, *command_args: Any, **command_kwargs: Any):
        def decorator(func: Callable[..., Any]):
            if self._command_func is not None:
                raise RuntimeError(
                    f"App '{self.name}' already has a registered command. "
                    "Use @app.subcommand() only when building a command group."
                )
            self._subcommands.append((command_args, command_kwargs, func))
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
        if self._command_func is None and not self._subcommands:
            raise RuntimeError("No command has been registered on this base_cli.App.")

        click = _require_click()
        if self._command_func is not None:
            return self._build_lifecycle_command(
                click,
                self._command_func,
                self._command_args,
                self._command_kwargs,
                include_version=True,
            )

        group_func = _empty_group
        if self.version is not None:
            group_func = click.version_option(self.version)(group_func)
        group = click.group(name=self.name)(group_func)
        for command_args, command_kwargs, func in self._subcommands:
            command = self._build_lifecycle_command(
                click,
                func,
                command_args,
                command_kwargs,
                include_version=False,
            )
            if command.name in group.commands:
                raise RuntimeError(f"App '{self.name}' already has a subcommand named '{command.name}'.")
            group.add_command(command)
        return group

    def _build_lifecycle_command(
        self,
        click: Any,
        func: Callable[..., Any],
        command_args: tuple[Any, ...],
        command_kwargs: dict[str, Any],
        include_version: bool,
    ) -> Any:
        sensitive_options = set(getattr(func, "__base_cli_sensitive_options__", set()))
        dry_run_parameter = getattr(func, "__base_cli_dry_run_parameter__", "dry_run")

        @functools.wraps(func)
        def wrapper(**kwargs: Any):
            standard = _pop_standard_options(kwargs)
            context = self._create_context(standard, sensitive_options, dry_run=bool(kwargs.get(dry_run_parameter)))
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
        wrapper = _decorate_standard_options(click, wrapper, self.version if include_version else None)
        return click.command(*command_args, **command_kwargs)(wrapper)

    def _create_context(self, standard: dict[str, Any], sensitive_options: set[str], dry_run: bool = False) -> Context:
        del sensitive_options
        run_id = make_run_id()
        manifest_path = discover_manifest(Path.cwd())
        project_root = manifest_path.parent if manifest_path is not None else None
        explicit_config = Path(standard["config"]).expanduser() if standard.get("config") else None
        user_config = read_user_config()
        config = load_config(project_root, explicit_config)

        environment = standard.get("environment") or config.get("environment") or "dev"
        debug = bool(standard.get("debug") or str(config.get("log_level", "")).lower() == "debug")
        keep_temp = bool(standard.get("keep_temp") or config.get("keep_temp"))

        state_dir = base_cache_root() / "cli" / self.name
        log_dir = state_dir / "logs"
        cache_dir = state_dir / "cache"
        temp_dir = state_dir / "tmp" / run_id

        log_file = Path(standard["log_file"]).expanduser() if standard.get("log_file") else None
        uses_default_log_file = log_file is None
        if dry_run or not self.log_to_file:
            if log_file is not None:
                log_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            for directory in (log_dir, cache_dir, temp_dir):
                directory.mkdir(parents=True, exist_ok=True)
            if log_file is None:
                log_file = log_dir / f"{run_id}.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
        logger = configure_logger(self.name, log_file, debug)
        logger.debug("cli=%s run_id=%s environment=%s", self.name, run_id, environment)
        if self.max_log_files is not None and uses_default_log_file and log_file is not None:
            _prune_log_files(log_dir, log_file, self.max_log_files, logger)

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
            user_config=user_config,
            dry_run=dry_run,
        )


def command(*args: Any, **kwargs: Any):
    return App().command(*args, **kwargs)


def option(*param_decls: str, sensitive: bool = False, dry_run: bool = False, **attrs: Any):
    def decorator(func: Callable[..., Any]):
        specs = list(getattr(func, "__base_cli_param_specs__", []))
        specs.append(("option", param_decls, attrs))
        func.__base_cli_param_specs__ = specs
        if sensitive:
            options = set(getattr(func, "__base_cli_sensitive_options__", set()))
            options.add(parameter_name_from_decls(param_decls))
            func.__base_cli_sensitive_options__ = options
        if dry_run:
            func.__base_cli_dry_run_parameter__ = parameter_name_from_decls(param_decls)
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


def _prune_log_files(
    log_dir: Path,
    current_log_file: Path,
    max_log_files: int,
    logger: logging.Logger,
) -> None:
    candidates: list[tuple[float, str, Path]] = []
    for path in log_dir.glob("*.log"):
        if _same_path(path, current_log_file):
            continue
        try:
            stat = path.stat()
        except OSError as exc:
            logger.warning("Could not inspect log file '%s' for pruning: %s", path, exc)
            continue
        candidates.append((stat.st_mtime, path.name, path))

    excess_count = len(candidates) + 1 - max_log_files
    if excess_count <= 0:
        return

    for _, _, path in sorted(candidates)[:excess_count]:
        try:
            path.unlink()
        except OSError as exc:
            logger.warning("Could not prune log file '%s': %s", path, exc)


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()
