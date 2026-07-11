"""Local explanation catalog for stable Base finding IDs."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any


CATALOG_SCHEMA_VERSION = 1
SUCCESS = 0
FAILURE = 1
USAGE_ERROR = 2
FINDING_DOC_PATH = "docs/doctor-findings.md"


@dataclass(frozen=True)
class RelatedDoc:
    label: str
    path: str


@dataclass(frozen=True)
class FindingExplanation:
    finding_id: str
    title: str
    summary: str
    why_it_matters: str
    likely_causes: tuple[str, ...]
    fix_steps: tuple[str, ...]
    related_commands: tuple[str, ...]
    docs: tuple[RelatedDoc, ...]


def catalog_by_id(explanations: tuple[FindingExplanation, ...]) -> dict[str, FindingExplanation]:
    catalog: dict[str, FindingExplanation] = {}
    for explanation in explanations:
        if explanation.finding_id in catalog:
            raise ValueError(f"Duplicate finding explanation ID {explanation.finding_id}.")
        catalog[explanation.finding_id] = explanation
    return catalog


CATALOG = catalog_by_id(
    (
        FindingExplanation(
            finding_id="BASE-D001",
            title="Homebrew availability and PATH refresh",
            summary="Base could not confirm that Homebrew is installed and available on PATH.",
            why_it_matters=(
                "Homebrew is the primary package manager Base uses for macOS runtime prerequisites. "
                "When it is missing or not visible in PATH, setup and doctor cannot reliably install or "
                "inspect macOS tools."
            ),
            likely_causes=(
                "Homebrew is not installed on this machine.",
                "Homebrew is installed but the current shell has not loaded its shellenv output.",
                "The terminal is running under the wrong architecture for the installed Homebrew prefix.",
            ),
            fix_steps=(
                "Run `basectl setup --dry-run` to preview the Homebrew bootstrap path.",
                "Install or repair Homebrew, then restart the shell or source your profile.",
                "Run `basectl doctor` again and confirm `BASE-D001` reports `ok`.",
            ),
            related_commands=("basectl setup --dry-run", "basectl doctor", "brew --prefix"),
            docs=(RelatedDoc("Doctor Finding IDs", "docs/doctor-findings.md#base-runtime-findings"),),
        ),
        FindingExplanation(
            finding_id="BASE-D004",
            title="Base virtual environment integrity",
            summary="Base could not verify the Python virtual environment used by Base itself.",
            why_it_matters=(
                "Base Python subcommands depend on this virtual environment for local CLI modules and "
                "runtime packages. A broken environment can make setup, check, doctor, and project commands "
                "fail before project-specific diagnostics can run."
            ),
            likely_causes=(
                "The virtual environment under `~/.base.d/base/.venv` is missing or incomplete.",
                "The Python executable inside the virtual environment no longer starts.",
                "A macOS architecture change left the virtual environment pointing at an incompatible Python.",
            ),
            fix_steps=(
                "Run `basectl setup --dry-run` to review the repair actions.",
                "Run `basectl setup --recreate-venv` when the existing environment must be rebuilt.",
                "Run `basectl doctor` again and confirm the Base virtualenv finding is healthy.",
            ),
            related_commands=("basectl setup --dry-run", "basectl setup --recreate-venv", "basectl doctor"),
            docs=(RelatedDoc("Runtime Environment", "docs/runtime-environment.md"),),
        ),
        FindingExplanation(
            finding_id="BASE-D007",
            title="Base reusable Bash library source readiness",
            summary="Base could not confirm that the reusable Bash library source is available.",
            why_it_matters=(
                "The Bash command layer imports shared libraries for GitHub, string, logging, and shell "
                "behavior. If the library source is missing or mismatched, shell subcommands may fail before "
                "they can reach Python diagnostics."
            ),
            likely_causes=(
                "`BASE_BASH_LIBS_DIR` points at a missing or stale checkout.",
                "A source checkout is missing its sibling `base-bash-libs` repository.",
                "A Homebrew install cannot locate the packaged library path.",
            ),
            fix_steps=(
                "Run `basectl doctor` to see the resolved Bash library source.",
                "For source checkouts, place `base-bash-libs` next to `base` or set `BASE_BASH_LIBS_DIR`.",
                "For installed Base, reinstall or upgrade the Base package that provides the libraries.",
            ),
            related_commands=("basectl doctor", "basectl check", "basectl setup --dry-run"),
            docs=(RelatedDoc("Runtime Environment", "docs/runtime-environment.md"),),
        ),
        FindingExplanation(
            finding_id="BASE-D011",
            title="GitHub CLI availability on Ubuntu/Debian",
            summary="Base could not find the GitHub CLI on an Ubuntu/Debian host.",
            why_it_matters=(
                "Several Base workflows use `gh` for repository, issue, pull request, and project automation. "
                "On Linux, Base reports this as a diagnostic so setup can stay explicit about adding external "
                "package repositories."
            ),
            likely_causes=(
                "The `gh` executable is not installed.",
                "The GitHub apt repository has not been added to the host.",
                "`gh` is installed outside the PATH visible to the current shell.",
            ),
            fix_steps=(
                "Run `basectl setup --dry-run` to review the Linux setup guidance.",
                "Install GitHub CLI using GitHub's official Ubuntu/Debian instructions.",
                "Run `gh auth status -h github.com` when GitHub-backed workflows need authentication.",
            ),
            related_commands=("basectl setup --dry-run", "basectl doctor --ci", "gh auth status -h github.com"),
            docs=(RelatedDoc("Linux Support", "docs/linux-support.md"),),
        ),
        FindingExplanation(
            finding_id="BASE-P050",
            title="Project virtual environment readiness",
            summary="Base could not verify the Base-managed Python virtual environment for the project.",
            why_it_matters=(
                "Project artifact checks and Python-package reconciliation depend on a working project "
                "environment unless the manifest opts into another manager such as uv. A broken venv blocks "
                "reliable project setup and command execution."
            ),
            likely_causes=(
                "The project virtual environment has not been created yet.",
                "The environment exists but its Python executable is missing or broken.",
                "The project changed Python versions and the old virtual environment was not recreated.",
            ),
            fix_steps=(
                "Run `basectl setup <project> --dry-run` to preview project environment actions.",
                "Run `basectl setup <project>` to create missing project artifacts.",
                "Use `--recreate-venv` when Base reports that the existing venv must be replaced.",
            ),
            related_commands=(
                "basectl check <project>",
                "basectl setup <project> --dry-run",
                "basectl setup <project> --recreate-venv",
            ),
            docs=(RelatedDoc("Python Manifest", "docs/python-manifest.md"),),
        ),
        FindingExplanation(
            finding_id="BASE-P080",
            title="Project Git repository status",
            summary="Base could not confirm that the project directory is inside a Git repository.",
            why_it_matters=(
                "Git context lets Base connect local project state to remotes, pull requests, and workspace "
                "automation. Without it, source-control diagnostics and some GitHub-backed workflows cannot "
                "make reliable claims."
            ),
            likely_causes=(
                "The project directory was copied without its `.git` directory.",
                "The manifest points outside the intended repository checkout.",
                "The project is new and has not been initialized with Git yet.",
            ),
            fix_steps=(
                "Run `git status` from the project root to confirm repository state.",
                "Move into the intended checkout or initialize Git for the project.",
                "Run `basectl doctor <project>` again after the repository state is corrected.",
            ),
            related_commands=("git status", "basectl doctor <project>", "basectl workspace status"),
            docs=(RelatedDoc("Source Control And Forge Support", "docs/source-control-and-forge-support.md"),),
        ),
        FindingExplanation(
            finding_id="BASE-P081",
            title="Project Git origin remote status",
            summary="Base could not parse or find the project's `origin` remote.",
            why_it_matters=(
                "The `origin` remote is the anchor Base uses for repository identity and GitHub-oriented "
                "diagnostics. Missing or malformed remotes make project automation ambiguous."
            ),
            likely_causes=(
                "The project has no `origin` remote configured.",
                "`origin` points at a local path or unsupported URL shape.",
                "The repository was cloned from a temporary or renamed remote.",
            ),
            fix_steps=(
                "Run `git remote -v` from the project root.",
                "Set or repair `origin` with the canonical repository URL.",
                "Run `basectl doctor <project> --remote-network` only when you want an opt-in reachability probe.",
            ),
            related_commands=("git remote -v", "basectl doctor <project>", "basectl doctor <project> --remote-network"),
            docs=(RelatedDoc("Source Control And Forge Support", "docs/source-control-and-forge-support.md"),),
        ),
        FindingExplanation(
            finding_id="BASE-P150",
            title="uv CLI availability for uv-managed projects or uv command runners",
            summary="Base could not find `uv` where the project manifest expects uv-managed behavior.",
            why_it_matters=(
                "When a project declares uv-managed environments or uv command runners, Base needs the `uv` "
                "CLI to inspect lockfiles and execute those commands consistently."
            ),
            likely_causes=(
                "`uv` is not installed.",
                "`uv` is installed but not on PATH for the current shell or CI runner.",
                "The project manifest opted into uv before the host was prepared.",
            ),
            fix_steps=(
                "Run `basectl setup <project> --dry-run` to preview the uv setup path.",
                "Install uv using the project-supported package path.",
                "Run `basectl check <project>` again before invoking uv-backed project commands.",
            ),
            related_commands=("basectl setup <project> --dry-run", "basectl check <project>", "uv --version"),
            docs=(RelatedDoc("Python Manifest - Command Runners", "docs/python-manifest.md#command-runners"),),
        ),
        FindingExplanation(
            finding_id="BASE-P160",
            title="Manifest command executable availability",
            summary="Base found an obvious missing executable in a manifest-declared command.",
            why_it_matters=(
                "Manifest commands are project-owned shell commands. Base checks for missing leading "
                "executables so users see a fast, local warning before a test, run, build, or demo command "
                "fails deeper in the workflow."
            ),
            likely_causes=(
                "The tool named first in the command is not installed.",
                "The command relies on a project script that has not been created yet.",
                "The command is intended to run through a manager such as uv but the runner is not declared.",
            ),
            fix_steps=(
                "Inspect the command in `base_manifest.yaml`.",
                "Install the missing executable or update the command to use the intended runner.",
                "Run `basectl check <project>` to confirm the advisory warning is gone.",
            ),
            related_commands=("basectl check <project>", "basectl run <project> <command> --dry-run"),
            docs=(RelatedDoc("Python Manifest - Command Runners", "docs/python-manifest.md#command-runners"),),
        ),
    )
)


def normalize_finding_id(value: str) -> str:
    return value.strip().upper()


def explanation_to_json(explanation: FindingExplanation) -> dict[str, Any]:
    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "found": True,
        "id": explanation.finding_id,
        "title": explanation.title,
        "summary": explanation.summary,
        "why_it_matters": explanation.why_it_matters,
        "likely_causes": list(explanation.likely_causes),
        "fix_steps": list(explanation.fix_steps),
        "related_commands": list(explanation.related_commands),
        "docs": [{"label": doc.label, "path": doc.path} for doc in explanation.docs],
    }


def unknown_to_json(finding_id: str) -> dict[str, Any]:
    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "found": False,
        "id": finding_id,
        "message": "No local explanation is available for this finding ID.",
        "docs": FINDING_DOC_PATH,
        "known_ids": sorted(CATALOG),
    }


def render_text(explanation: FindingExplanation) -> str:
    lines = [
        f"{explanation.finding_id} - {explanation.title}",
        "",
        "Summary:",
        f"  {explanation.summary}",
        "",
        "Why it matters:",
        f"  {explanation.why_it_matters}",
        "",
        "Likely causes:",
    ]
    lines.extend(f"  - {cause}" for cause in explanation.likely_causes)
    lines.extend(("", "Fix steps:"))
    lines.extend(f"  {index}. {step}" for index, step in enumerate(explanation.fix_steps, start=1))
    if explanation.related_commands:
        lines.extend(("", "Related commands:"))
        lines.extend(f"  - {command}" for command in explanation.related_commands)
    if explanation.docs:
        lines.extend(("", "Docs:"))
        lines.extend(f"  - {doc.label}: {doc.path}" for doc in explanation.docs)
    return "\n".join(lines) + "\n"


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="base_setup.finding_explanations")
    parser.add_argument("finding_id", help="Stable finding ID, such as BASE-D001 or BASE-P050.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    finding_id = normalize_finding_id(args.finding_id)
    explanation = CATALOG.get(finding_id)
    if explanation is None:
        if args.format == "json":
            print(render_json(unknown_to_json(finding_id)), end="")
        else:
            print(
                f"No local explanation is available for {finding_id}. "
                f"See {FINDING_DOC_PATH} for documented finding IDs.",
                file=sys.stderr,
            )
        return FAILURE
    if args.format == "json":
        print(render_json(explanation_to_json(explanation)), end="")
    else:
        print(render_text(explanation), end="")
    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
