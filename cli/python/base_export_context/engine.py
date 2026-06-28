from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import base_cli


app = base_cli.App(name="base_export_context")

CONTEXT_DIR_NAME = ".ai-context"
MARKDOWN_FORMAT = "markdown"
ZIP_FORMAT = "zip"
SUPPORTED_FORMATS = (MARKDOWN_FORMAT, ZIP_FORMAT)
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MARKDOWN_CODE_RE = re.compile(r"`([^`]+)`")


@dataclass(frozen=True)
class ContextFile:
    path: Path
    relative_path: PurePosixPath

    @property
    def display_path(self) -> str:
        return f"{CONTEXT_DIR_NAME}/{self.relative_path.as_posix()}"


class ExportContextError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExportContextOptions:
    project_name: str
    project_root: Path
    output_format: str
    output_path: str | None
    print_bundle: bool
    list_files: bool


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option("--project-name", required=True, help="Resolved Base project name.")
@base_cli.option("--project-root", required=True, help="Resolved Base project root.")
@base_cli.option("--format", "output_format", default=MARKDOWN_FORMAT, help="Output format: markdown or zip.")
@base_cli.option("--output", "output_path", help="Output path for the export bundle.")
@base_cli.option("--print", "print_bundle", is_flag=True, help="Print the Markdown bundle to stdout.")
@base_cli.option("--list-files", is_flag=True, help="Print the files in export order without writing a bundle.")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def run(
    ctx: base_cli.Context,
    project_name: str,
    project_root: str,
    output_format: str,
    output_path: str | None,
    print_bundle: bool,
    list_files: bool,
) -> int:
    options = ExportContextOptions(
        project_name=project_name,
        project_root=Path(project_root).expanduser().resolve(),
        output_format=output_format.lower(),
        output_path=output_path,
        print_bundle=print_bundle,
        list_files=list_files,
    )
    validation_error = validate_options(options, raw_output_format=output_format)
    if validation_error is not None:
        ctx.log.error(validation_error)
        return base_cli.ExitCode.USAGE_ERROR

    try:
        return export_context(options)
    except ExportContextError as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE


def validate_options(options: ExportContextOptions, raw_output_format: str) -> str | None:
    if options.output_format not in SUPPORTED_FORMATS:
        return f"Unsupported export format '{raw_output_format}'. Expected one of: markdown, zip."
    if options.print_bundle and options.output_format != MARKDOWN_FORMAT:
        return "Option '--print' only supports markdown exports."
    if options.print_bundle and options.output_path:
        return "Options '--print' and '--output' cannot be combined."
    if options.list_files and (options.print_bundle or options.output_path):
        return "Option '--list-files' cannot be combined with '--print' or '--output'."
    return None


def export_context(options: ExportContextOptions) -> int:
    if options.list_files:
        files = ordered_context_files(
            options.project_name,
            options.project_root,
            include_all=options.output_format == ZIP_FORMAT,
        )
        for context_file in files:
            print(context_file.display_path)
        return base_cli.ExitCode.SUCCESS

    if options.output_format == MARKDOWN_FORMAT:
        return export_markdown_context(options)

    files = ordered_context_files(options.project_name, options.project_root, include_all=True)
    destination = resolve_output_path(options.project_name, options.output_path, "zip")
    write_zip_file(destination, files)
    print(f"Wrote Zip AI context export for project '{options.project_name}' to {destination}")
    return base_cli.ExitCode.SUCCESS


def export_markdown_context(options: ExportContextOptions) -> int:
    files = ordered_context_files(options.project_name, options.project_root, include_all=False)
    content = render_markdown_bundle(options.project_name, files)
    if options.print_bundle:
        print(content, end="")
        return base_cli.ExitCode.SUCCESS
    destination = resolve_output_path(options.project_name, options.output_path, "md")
    write_text_file(destination, content)
    print(f"Wrote Markdown AI context export for project '{options.project_name}' to {destination}")
    return base_cli.ExitCode.SUCCESS


def resolve_output_path(project_name: str, output_path: str | None, extension: str) -> Path:
    if output_path:
        return Path(output_path).expanduser()
    return Path.cwd() / f"{project_name}-ai-context.{extension}"


def ordered_context_files(project_name: str, project_root: Path, include_all: bool) -> tuple[ContextFile, ...]:
    context_dir = project_root / CONTEXT_DIR_NAME
    if not context_dir.exists():
        raise ExportContextError(
            f"Project '{project_name}' does not have an .ai-context directory. "
            "Add .ai-context/README.md before exporting AI context."
        )
    if not context_dir.is_dir():
        raise ExportContextError(f"Project '{project_name}' has .ai-context, but it is not a directory.")

    files = discover_context_files(context_dir, include_all=include_all)
    if not files:
        if include_all:
            detail = "does not contain files"
        else:
            detail = "does not contain Markdown files"
        raise ExportContextError(f"Project '{project_name}' .ai-context directory {detail}.")

    by_relative_path = {context_file.relative_path.as_posix(): context_file for context_file in files}
    ordered_paths: list[str] = []
    for referenced_path in index_references(context_dir, by_relative_path):
        if referenced_path not in ordered_paths:
            ordered_paths.append(referenced_path)
    ordered_paths.extend(path for path in sorted(by_relative_path) if path not in ordered_paths)
    return tuple(by_relative_path[path] for path in ordered_paths)


def discover_context_files(context_dir: Path, include_all: bool) -> tuple[ContextFile, ...]:
    files: list[ContextFile] = []
    for path in context_dir.rglob("*"):
        if not path.is_file():
            continue
        if not include_all and path.suffix.lower() != ".md":
            continue
        relative_path = PurePosixPath(path.relative_to(context_dir).as_posix())
        files.append(ContextFile(path=path, relative_path=relative_path))
    return tuple(sorted(files, key=lambda context_file: context_file.relative_path.as_posix()))


def index_references(context_dir: Path, known_paths: dict[str, ContextFile]) -> tuple[str, ...]:
    index_path = context_dir / "INDEX.md"
    if "INDEX.md" not in known_paths or not index_path.is_file():
        return ()

    try:
        content = index_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ExportContextError("Unable to read .ai-context/INDEX.md as UTF-8.") from exc

    references: list[str] = []
    for _, raw_reference in sorted(markdown_reference_matches(content), key=lambda item: item[0]):
        normalized = normalize_index_reference(raw_reference)
        if normalized is not None and normalized in known_paths and normalized not in references:
            references.append(normalized)
    return tuple(references)


def markdown_reference_matches(content: str) -> tuple[tuple[int, str], ...]:
    matches: list[tuple[int, str]] = []
    matches.extend((match.start(1), match.group(1)) for match in MARKDOWN_LINK_RE.finditer(content))
    matches.extend((match.start(1), match.group(1)) for match in MARKDOWN_CODE_RE.finditer(content))
    return tuple(matches)


def normalize_index_reference(raw_reference: str) -> str | None:
    reference = raw_reference.strip().strip("<>")
    if not reference or "://" in reference or reference.startswith(("/", "#")):
        return None
    reference = reference.split("#", 1)[0].split("?", 1)[0]
    if not reference:
        return None
    pure_path = PurePosixPath(reference)
    if pure_path.is_absolute() or any(part == ".." for part in pure_path.parts):
        return None
    return pure_path.as_posix()


def render_markdown_bundle(project_name: str, files: tuple[ContextFile, ...]) -> str:
    parts = [
        f"# AI Context Export: {project_name}",
        "",
        "Files are exported from `.ai-context/` in deterministic order.",
        "",
    ]

    for context_file in files:
        parts.append(f"## `{context_file.display_path}`")
        parts.append("")
        try:
            content = context_file.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ExportContextError(f"Unable to read {context_file.display_path} as UTF-8.") from exc
        parts.append(content.rstrip("\n"))
        parts.append("")
        parts.append("")

    return "\n".join(parts)


def write_text_file(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def write_zip_file(destination: Path, files: tuple[ContextFile, ...]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for context_file in files:
            info = zipfile.ZipInfo(context_file.relative_path.as_posix(), ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, context_file.path.read_bytes())
