import re
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
SKIPPED_SCHEMES = ("data:", "http:", "https:", "mailto:", "tel:")


def markdown_files() -> list[Path]:
    return sorted(path for path in REPO_ROOT.rglob("*.md") if ".git" not in path.parts)


def without_fenced_code(text: str) -> str:
    lines: list[str] = []
    in_fence = False

    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)

    return "\n".join(lines)


def local_link_targets(path: Path) -> list[tuple[int, str]]:
    text = without_fenced_code(path.read_text(encoding="utf-8"))
    targets: list[tuple[int, str]] = []

    for match in MARKDOWN_LINK.finditer(text):
        target = unquote(match.group(1)).strip("<>")
        if not target or target.startswith("#") or target.startswith("//"):
            continue
        if target.lower().startswith(SKIPPED_SCHEMES):
            continue

        target_path = target.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0]
        if not target_path:
            continue
        line_number = text.count("\n", 0, match.start()) + 1
        targets.append((line_number, target_path))

    return targets


def test_markdown_local_links_resolve_to_repository_paths() -> None:
    broken: list[str] = []

    for document in markdown_files():
        for line_number, target in local_link_targets(document):
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(REPO_ROOT.resolve())
            except ValueError:
                broken.append(f"{document.relative_to(REPO_ROOT)}:{line_number}: {target}")
                continue
            if not resolved.exists():
                broken.append(f"{document.relative_to(REPO_ROOT)}:{line_number}: {target}")

    assert not broken, "broken local Markdown links:\n" + "\n".join(broken)
