"""Compatibility exports for shared manifest trust guidance."""

from __future__ import annotations

from base_setup.manifest_trust_guidance import (
    allow_command_text,
    print_blocked_command_text,
    print_identity,
    print_review_guidance,
    print_status_text,
    print_trust_scope_warning,
)

__all__ = [
    "allow_command_text",
    "print_blocked_command_text",
    "print_identity",
    "print_review_guidance",
    "print_status_text",
    "print_trust_scope_warning",
]
