from __future__ import annotations


def decode_subprocess_output(output: bytes | str | None) -> str:
    """Decode child output without allowing invalid UTF-8 to abort orchestration."""

    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output
