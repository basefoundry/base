"""Run Base-owned modules without adding the caller's directory to imports.

Launch this file by absolute path with Python's isolated (-I) option. The
selected provider and Base command source roots are the only injected paths;
the caller's working directory is preserved for project discovery.
"""

from __future__ import annotations

import sys


def main() -> int:
    if not sys.flags.isolated:
        print("Base module entrypoint requires Python's -I option.", file=sys.stderr)
        return 2
    if len(sys.argv) < 2:
        print("Usage: module_entrypoint.py <module> [arguments...]", file=sys.stderr)
        return 2
    import os
    import runpy
    from pathlib import Path

    command_root = Path(__file__).resolve().parents[1]
    source_roots = [str(command_root)]
    provider_root = os.environ.get("BASE_CLI_RUNTIME_SOURCE_ROOT")
    if provider_root:
        source_roots.insert(0, str(Path(provider_root).resolve()))
    sys.path[:0] = source_roots
    module = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
