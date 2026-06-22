from __future__ import annotations

import unittest

import base_cli


class AppDryRunTests(unittest.TestCase):
    def test_rejects_duplicate_custom_dry_run_options(self) -> None:
        app = base_cli.App(name="duplicate-dry-run")

        with self.assertRaisesRegex(
            RuntimeError,
            "main.*only one option can be designated dry_run=True",
        ):

            @app.command()
            @base_cli.option("--preview", is_flag=True, dry_run=True)
            @base_cli.option("--plan", is_flag=True, dry_run=True)
            def main(ctx: base_cli.Context, preview: bool, plan: bool) -> None:
                del ctx, preview, plan


if __name__ == "__main__":
    unittest.main()
