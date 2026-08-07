from unittest.mock import call, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


ALL_IMPORTS_ENABLED = {
    "ACMAD_INITIAL_IMPORT_ON_STARTUP": True,
    "ACMAD_MULTIHAZARD_AUTO_IMPORT": True,
    "ACMAD_MULTIHAZARD_IMPORT_LIMIT": 10,
    "ACMAD_RAINFALL_AUTO_IMPORT": True,
    "ACMAD_RAINFALL_IMPORT_LIMIT": 7,
    "ACMAD_DEKADAL_AUTO_IMPORT": True,
    "ACMAD_POLICY_BRIEFS_AUTO_IMPORT": True,
    "ACMAD_POLICY_BRIEFS_IMPORT_LIMIT": 5,
    "ACMAD_ATMOSPHERIC_ANALYSIS_AUTO_IMPORT": True,
    "ACMAD_HEAT_STRESS_AUTO_IMPORT": True,
    "ACMAD_HEAT_STRESS_IMPORT_LIMIT": 3,
}


class TestBootstrapAcmadProducts(SimpleTestCase):
    @override_settings(ACMAD_INITIAL_IMPORT_ON_STARTUP=False)
    @patch(
        "climweb.pages.products.management.commands."
        "bootstrap_acmad_products.call_command"
    )
    def test_disabled_bootstrap_does_not_run_importers(self, importer):
        call_command("bootstrap_acmad_products")

        importer.assert_not_called()

    @override_settings(**ALL_IMPORTS_ENABLED)
    @patch(
        "climweb.pages.products.management.commands."
        "bootstrap_acmad_products.call_command"
    )
    def test_enabled_bootstrap_runs_all_six_importers(self, importer):
        call_command("bootstrap_acmad_products")

        self.assertEqual(
            importer.call_args_list,
            [
                call(
                    "import_acmad_multihazard",
                    continue_on_error=True,
                    limit=10,
                ),
                call(
                    "import_acmad_daily_rainfall",
                    continue_on_error=True,
                    limit=7,
                ),
                call("import_acmad_dekadal_bulletin", continue_on_error=True),
                call(
                    "import_acmad_policy_briefs",
                    continue_on_error=True,
                    limit=5,
                ),
                call("import_acmad_atmospheric_analysis", continue_on_error=True),
                call(
                    "import_acmad_heat_stress",
                    continue_on_error=True,
                    limit=3,
                ),
            ],
        )

    @override_settings(**ALL_IMPORTS_ENABLED)
    @patch(
        "climweb.pages.products.management.commands."
        "bootstrap_acmad_products.call_command"
    )
    def test_failure_does_not_prevent_remaining_importers(self, importer):
        importer.side_effect = [
            CommandError("unavailable"),
            None,
            None,
            None,
            None,
            None,
        ]

        with self.assertRaises(CommandError):
            call_command("bootstrap_acmad_products")

        self.assertEqual(importer.call_count, 6)
