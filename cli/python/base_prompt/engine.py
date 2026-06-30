from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import base_cli


app = base_cli.App(name="base_prompt", log_to_file=False)

PROMPTS_DIR = Path(".ai-context") / "prompts"


class PromptUsageError(RuntimeError):
    pass


class PromptError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptDefinition:
    name: str
    description: str
    relative_path: Path


PROMPTS: tuple[PromptDefinition, ...] = (
    PromptDefinition(
        name="product-self-review",
        description="Periodic Base product self-review",
        relative_path=PROMPTS_DIR / "product-self-review.md",
    ),
)


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.argument("prompt_name", required=False)
def run(ctx: base_cli.Context, prompt_name: str | None) -> int:
    try:
        if prompt_name == "list":
            return list_prompts()
        if not prompt_name:
            raise PromptUsageError("The 'prompt' command requires 'list' or a prompt name.")
        prompt = prompt_definition(prompt_name)
        print(render_prompt(ctx.base_home, prompt), end="")
        return base_cli.ExitCode.SUCCESS
    except PromptUsageError as exc:
        print_usage(file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return base_cli.ExitCode.USAGE_ERROR
    except PromptError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return base_cli.ExitCode.FAILURE


def print_usage(file=sys.stdout) -> None:
    command = base_cli.delegated_display_command("base_prompt")
    print(
        f"""Usage:
  {command} list
  {command} <name>

Prompts:
  product-self-review  Periodic Base product self-review

Purpose:
  Print repo-owned Markdown prompts for AI-assisted Base workflows. Base
  renders the prompt; an AI tool performs the review.""",
        file=file,
    )


def list_prompts() -> int:
    for prompt in PROMPTS:
        print(f"{prompt.name}\t{prompt.description}")
    return base_cli.ExitCode.SUCCESS


def prompt_definition(name: str) -> PromptDefinition:
    for prompt in PROMPTS:
        if prompt.name == name:
            return prompt
    raise PromptUsageError(f"Unknown prompt '{name}'.")


def render_prompt(base_home: Path, prompt: PromptDefinition) -> str:
    template_path = base_home / prompt.relative_path
    try:
        template = template_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptError(f"Prompt template '{prompt.relative_path}' was not found.") from exc
    except UnicodeDecodeError as exc:
        raise PromptError(f"Prompt template '{prompt.relative_path}' is not valid UTF-8.") from exc

    values = {
        "generated_date": date.today().isoformat(),
        "project_name": "base",
        "version": read_version(base_home),
    }
    return render_template(template, values)


def read_version(base_home: Path) -> str:
    version_path = base_home / "VERSION"
    try:
        version = version_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise PromptError("VERSION was not found in Base home.") from exc
    return version or "unknown"


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
    return rendered
