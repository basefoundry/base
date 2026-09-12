from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import base_cli

# The outer Bash lifecycle owns Base's inherited bundle. base-cli owns the
# retention index that its delegated Python children update, so use its single
# lock-aware refresh implementation instead of editing that index in Bash.
from base_cli_adapters.provider import BaseCliCompatibilityError, load_run_index_runtime


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python -m base_cli_adapters.run_index <runs-root>", file=sys.stderr)
        return base_cli.ExitCode.USAGE_ERROR
    try:
        runtime = load_run_index_runtime()
    except BaseCliCompatibilityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return base_cli.ExitCode.FAILURE
    runtime.refresh_run_bundle_index(Path(args[0]))
    return base_cli.ExitCode.SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
