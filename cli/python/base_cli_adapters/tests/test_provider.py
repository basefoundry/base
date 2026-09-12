from __future__ import annotations

from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from base_cli_adapters.provider import BaseCliCompatibilityError
from base_cli_adapters.provider import load_command_protocol


class BaseCliProviderTests(TestCase):
    def test_compatible_provider_loads(self) -> None:
        command_protocol = load_command_protocol()

        self.assertTrue(hasattr(command_protocol, "register_record_schema"))

    def test_missing_provider_has_actionable_error(self) -> None:
        with patch(
            "base_cli_adapters.provider.import_module",
            side_effect=ModuleNotFoundError("No module named 'base_cli'"),
        ):
            with self.assertRaisesRegex(
                BaseCliCompatibilityError,
                "Install or upgrade base-cli.*BASE_CLI_SOURCE_DIR",
            ):
                load_command_protocol()

    def test_missing_protocol_capability_has_actionable_error(self) -> None:
        command_protocol = ModuleType("base_cli.command_protocol")

        with patch(
            "base_cli_adapters.provider.import_module",
            return_value=command_protocol,
        ):
            with self.assertRaisesRegex(
                BaseCliCompatibilityError,
                "missing .*register_record_schema",
            ):
                load_command_protocol()


def test_public_context_contract_excludes_future_private_fields() -> None:
    from dataclasses import make_dataclass  # pylint: disable=import-outside-toplevel
    from base_cli_adapters.provider import public_context_field_names  # pylint: disable=import-outside-toplevel

    context = make_dataclass("FutureContext", ["project_root", "cleanup_hooks", "_future_provider_state"])
    assert public_context_field_names(context) == {"project_root"}


def test_provider_preflight_checks_runtime_and_history_capabilities() -> None:
    from importlib import import_module  # pylint: disable=import-outside-toplevel
    import pytest  # pylint: disable=import-outside-toplevel
    from base_cli_adapters.provider import validate_provider  # pylint: disable=import-outside-toplevel

    validate_provider()
    for module_name, symbol in (
        ("base_cli._runtime", "refresh_run_bundle_index"),
        ("base_cli.history", "update_run_metadata"),
    ):
        module = import_module(module_name)
        original = getattr(module, symbol)
        try:
            delattr(module, symbol)
            with pytest.raises(BaseCliCompatibilityError, match=f"missing {symbol}"):
                validate_provider()
        finally:
            setattr(module, symbol, original)
