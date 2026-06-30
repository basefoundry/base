from __future__ import annotations

import functools
import logging
import os
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable

from .config import load_config, read_user_config
from .context import Context, reset_current_context, set_current_context
from .exit_codes import ExitCode
from .history import utc_now, write_finished_record
from .logging import configure_logger, log_invocation
from .paths import (
    base_cache_root,
    current_working_dir,
    discover_manifest,
    make_run_id,
    normalize_cli_name,
    resolve_base_home,
)
from .redaction import parameter_name_from_decls

_STANDARD_OPTION_KEYS = ("debug", "quiet", "environment", "config", "keep_temp", "log_file")
_GROUP_STANDARD_OPTIONS_KEY = "base_cli_standard_options"
DISPLAY_COMMAND_ENV = "BASE_CLI_DISPLAY_COMMAND"
_INVOCATION_ARGV: ContextVar[list[str] | None] = ContextVar("base_cli_invocation_argv", default=None)


def _require_click():
    try:
        import click
    except ImportError as exc:
        raise RuntimeError("Click is required for base_cli. Run 'basectl setup' to install it.") from exc
    return click


class App:
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        name: str | None = None,
        version: str | None = None,
        help: str | None = None,  # pylint: disable=redefined-builtin
        log_to_file: bool = True,
        max_log_files: int | None = None,
    ) -> None:
        if max_log_files is not None and max_log_files < 1:
            raise ValueError("max_log_files must be greater than 0 when set.")
        self.name = normalize_cli_name(name or sys.argv[0])
        self.version = version
        self.help = help
        self.log_to_file = log_to_file
        self.max_log_files = max_log_files
        self._click_command = None
        self._command_func: Callable[..., Any] | None = None
        self._command_args: tuple[Any, ...] = ()
        self._command_kwargs: dict[str, Any] = {}
        self._subcommands: list[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]] = []

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
                    "Use either @app.command() or @app.subcommand(), not both."
                )
            self._subcommands.append((func, command_args, command_kwargs))
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
            wrapper = self._build_command_wrapper(click, self._command_func, include_version=True)
            command_kwargs = dict(self._command_kwargs)
            if self.help is not None:
                command_kwargs.setdefault("help", self.help)
            return click.command(*self._command_args, **command_kwargs)(wrapper)

        group_wrapper = _decorate_standard_options(click, _build_group_wrapper(click), self.version)
        group = click.group(name=self.name, help=self.help)(group_wrapper)
        for func, command_args, command_kwargs in self._subcommands:
            wrapper = self._build_command_wrapper(click, func, include_version=False)
            group.add_command(click.command(*command_args, **command_kwargs)(wrapper))
        return group

    def _build_command_wrapper(self, click: Any, func: Callable[..., Any], include_version: bool) -> Callable[..., Any]:
        sensitive_options = set(getattr(func, "__base_cli_sensitive_options__", set()))
        dry_run_parameter = getattr(func, "__base_cli_dry_run_parameter__", "dry_run")

        @functools.wraps(func)
        def wrapper(**kwargs: Any):
            standard = _merge_standard_options(
                _group_standard_options(click),
                _pop_standard_options(kwargs),
            )
            _validate_standard_options(click, standard)
            try:
                context = self._create_context(standard, sensitive_options, dry_run=bool(kwargs.get(dry_run_parameter)))
            except (RuntimeError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc
            token = set_current_context(context)
            started_at = utc_now()
            exit_code = ExitCode.SUCCESS
            invocation_argv = _current_invocation_argv()
            try:
                log_invocation(context.log, invocation_argv, sensitive_options)
                if context.project_root is not None:
                    context.log.debug("project_root=%s", context.project_root)
                if context.manifest_path is not None:
                    context.log.debug("manifest_path=%s", context.manifest_path)
                result = func(context, **kwargs)
                exit_code = int(result or ExitCode.SUCCESS)
                return result
            except Exception:
                exit_code = ExitCode.FAILURE
                raise
            finally:
                write_finished_record(context, invocation_argv, sensitive_options, started_at, exit_code)
                reset_current_context(token)
                context.cleanup()

        for kind, param_decls, attrs in getattr(func, "__base_cli_param_specs__", []):
            if kind == "option":
                wrapper = click.option(*param_decls, **attrs)(wrapper)
            elif kind == "argument":
                wrapper = click.argument(*param_decls, **attrs)(wrapper)
        wrapper = _decorate_standard_options(click, wrapper, self.version if include_version else None)
        return wrapper

    def _create_context(self, standard: dict[str, Any], sensitive_options: set[str], dry_run: bool = False) -> Context:
        del sensitive_options
        run_id = make_run_id()
        manifest_path = discover_manifest(current_working_dir())
        project_root = manifest_path.parent if manifest_path is not None else None
        explicit_config = Path(standard["config"]).expanduser() if standard.get("config") else None
        user_config = read_user_config()
        config = load_config(project_root, explicit_config)

        environment = standard.get("environment") or config.get("environment") or "dev"
        debug = bool(standard.get("debug") or str(config.get("log_level", "")).lower() == "debug")
        quiet = bool(standard.get("quiet"))
        keep_temp = bool(standard.get("keep_temp") or config.get("keep_temp"))

        cache_root = base_cache_root()
        state_dir = cache_root / "cli" / self.name
        log_dir = state_dir / "logs"
        cache_dir = state_dir / "cache"
        temp_dir = state_dir / "tmp" / run_id

        log_file = Path(standard["log_file"]).expanduser() if standard.get("log_file") else None
        uses_default_log_file = log_file is None
        if dry_run or not self.log_to_file:
            if log_file is not None:
                _create_runtime_directory(log_file.parent, cache_root)
        else:
            for directory in (log_dir, cache_dir, temp_dir):
                _create_runtime_directory(directory, cache_root)
            if log_file is None:
                log_file = log_dir / f"{run_id}.log"
            _create_runtime_directory(log_file.parent, cache_root)
        logger = configure_logger(self.name, log_file, debug, quiet=quiet)
        logger.debug("cli=%s run_id=%s environment=%s", self.name, run_id, environment)
        if self.max_log_files is not None and uses_default_log_file and log_file is not None:
            _prune_log_files(log_dir, log_file, self.max_log_files, logger)

        return Context(
            cli_name=self.name,
            run_id=run_id,
            base_home=resolve_base_home(),
            project_root=project_root,
            workspace_root=user_config.workspace.root,
            manifest_path=manifest_path,
            state_dir=state_dir,
            log_dir=log_dir,
            cache_dir=cache_dir,
            temp_dir=temp_dir,
            log_file=log_file,
            config=config,
            environment=environment,
            debug=debug,
            quiet=quiet,
            keep_temp=keep_temp,
            log=logger,
            user_config=user_config,
            dry_run=dry_run,
        )


def _create_runtime_directory(path: Path, cache_root: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(_runtime_directory_error(path, cache_root, exc)) from exc


def _runtime_directory_error(path: Path, cache_root: Path, exc: OSError) -> str:
    return (
        f"Unable to create Base runtime directory '{path}': {exc}. "
        f"Check permissions on that directory. If the Base cache root '{cache_root}' is unusable, "
        "set BASE_CACHE_DIR to a writable directory."
    )


def run_app(app: App, argv: list[str] | None = None) -> int:
    try:
        click = _require_click()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return ExitCode.FAILURE

    explicit_argv = argv is not None
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        _reject_equals_option_values(click, args)
        display_command = delegated_display_command()
        invocation_argv = _effective_invocation_argv(app, args, explicit_argv, display_command)
        invocation_token = _INVOCATION_ARGV.set(invocation_argv)
        try:
            if display_command:
                result = app.click_command.main(args=args, prog_name=display_command, standalone_mode=False)
            else:
                result = app.click_command.main(args=args, standalone_mode=False)
        finally:
            _INVOCATION_ARGV.reset(invocation_token)
    except click.ClickException as exc:
        exc.show()
        return int(exc.exit_code)
    return int(result or 0)


def _effective_invocation_argv(
    app: App,
    args: list[str],
    explicit_argv: bool,
    display_command: str | None,
) -> list[str]:
    if not explicit_argv:
        return list(sys.argv)
    return [display_command or app.name, *args]


def _current_invocation_argv() -> list[str]:
    invocation_argv = _INVOCATION_ARGV.get()
    if invocation_argv is not None:
        return list(invocation_argv)
    return list(sys.argv)


def delegated_display_command(default: str | None = None) -> str | None:
    display_command = os.environ.get(DISPLAY_COMMAND_ENV, "").strip()
    if display_command:
        return display_command
    return default


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
            dry_run_parameter = parameter_name_from_decls(param_decls)
            existing_dry_run_parameter = getattr(func, "__base_cli_dry_run_parameter__", None)
            if existing_dry_run_parameter is not None:
                raise RuntimeError(
                    f"{func.__name__} already designates '{existing_dry_run_parameter}' as dry-run. "
                    "only one option can be designated dry_run=True."
                )
            func.__base_cli_dry_run_parameter__ = dry_run_parameter
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
    func = click.option("--keep-temp", is_flag=True, default=None, help="Preserve this run's temp directory.")(func)
    func = click.option("--config", type=click.Path(dir_okay=False), help="Load an additional config file.")(func)
    func = click.option("--environment", help="Set the Base CLI environment.")(func)
    func = click.option(
        "--debug",
        is_flag=True,
        default=None,
        help="Enable DEBUG logging on the user-facing stream.",
    )(func)
    func = click.option(
        "--quiet",
        "-q",
        is_flag=True,
        default=None,
        help="Suppress INFO logs on the user-facing stream.",
    )(func)
    if version is not None:
        func = click.version_option(version)(func)
    return func


def _pop_standard_options(kwargs: dict[str, Any]) -> dict[str, Any]:
    standard = {}
    for key in _STANDARD_OPTION_KEYS:
        standard[key] = kwargs.pop(key, None)
    return standard


def _merge_standard_options(group_standard: dict[str, Any], command_standard: dict[str, Any]) -> dict[str, Any]:
    merged = {}
    for key in _STANDARD_OPTION_KEYS:
        value = command_standard.get(key)
        merged[key] = group_standard.get(key) if value is None else value
    return merged


def _validate_standard_options(click: Any, standard: dict[str, Any]) -> None:
    if standard.get("debug") and standard.get("quiet"):
        raise click.UsageError("--debug and --quiet cannot be used together.")


def _reject_equals_option_values(click: Any, argv: list[str]) -> None:
    for token in argv:
        if token == "--":
            return
        if token.startswith("--") and "=" in token and len(token) > 2:
            option_name, value = token.split("=", 1)
            if value:
                raise click.UsageError(
                    f"Option '{option_name}' uses unsupported equals syntax. Use '{option_name} {value}' instead."
                )
            raise click.UsageError(
                f"Option '{option_name}' uses unsupported equals syntax. Pass its value as the next argument."
            )


def _group_standard_options(click: Any) -> dict[str, Any]:
    context = click.get_current_context(silent=True)
    parent = context.parent if context is not None else None
    if parent is None or not isinstance(parent.obj, dict):
        return {}
    standard = parent.obj.get(_GROUP_STANDARD_OPTIONS_KEY)
    return dict(standard) if isinstance(standard, dict) else {}


def _build_group_wrapper(click: Any) -> Callable[..., None]:
    @click.pass_context
    def group_wrapper(context: Any, **kwargs: Any) -> None:
        obj = dict(context.obj) if isinstance(context.obj, dict) else {}
        obj[_GROUP_STANDARD_OPTIONS_KEY] = _pop_standard_options(kwargs)
        context.obj = obj

    return group_wrapper


def _prune_log_files(
    log_dir: Path,
    current_log_file: Path,
    max_log_files: int,
    logger: logging.Logger,
) -> None:
    candidates: list[tuple[str, Path]] = []
    for path in log_dir.glob("*.log"):
        if _same_path(path, current_log_file):
            continue
        candidates.append((path.name, path))

    excess_count = len(candidates) + 1 - max_log_files
    if excess_count <= 0:
        return

    for _, path in sorted(candidates)[:excess_count]:
        try:
            path.unlink()
        except OSError as exc:
            logger.warning("Could not prune log file '%s': %s", path, exc)


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()
