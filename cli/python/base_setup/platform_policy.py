from __future__ import annotations

import os


def current_base_platform() -> str:
    return os.environ.get("BASE_PLATFORM", "")


def platform_label() -> str:
    return current_base_platform() or "unspecified"


def brewfile_delegates_supported() -> bool:
    return current_base_platform() in {"", "macos"}
