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
    "ACMAD_MONTHLY_CLIMATE_AUTO_IMPORT": True,
    "ACMAD_MONTHLY_CLIMATE_IMPORT_LIMIT": 2,
    "ACMAD_SEASON_ONSET_AUTO_IMPORT": True,
    "ACMAD_SEASON_ONSET_IMPORT_LIMIT": 3,
    "ACMAD_CLIMATE_CHANGE_AUTO_IMPORT": True,
    "ACMAD_CLIMATE_CHANGE_IMPORT_LIMIT": 5,
    "ACMAD_ANNUAL_CLIMATE_AUTO_IMPORT": True,
    "ACMAD_ANNUAL_CLIMATE_IMPORT_LIMIT": 5,
    "ACMAD_CLIMATE_WATCH_AUTO_IMPORT": True,
    "ACMAD_CLIMATE_WATCH_IMPORT_LIMIT": 5,
    "ACMAD_RAINFALL_EXCEEDANCE_AUTO_IMPORT": True,
    "ACMAD_RAINFALL_EXCEEDANCE_IMPORT_LIMIT": 3,
    "ACMAD_FIVE_DAY_RAINFALL_AUTO_IMPORT": True,
    "ACMAD_FIVE_DAY_RAINFALL_IMPORT_LIMIT": 3,
    "ACMAD_SEASONAL_VERIFICATION_AUTO_IMPORT": True,
    "ACMAD_SEASONAL_VERIFICATION_IMPORT_LIMIT": 3,
    "ACMAD_CRYOSPHERE_AUTO_IMPORT": True,
    "ACMAD_CRYOSPHERE_IMPORT_LIMIT": 5,
    "ACMAD_POLICY_BRIEFS_AUTO_IMPORT": True,
    "ACMAD_POLICY_BRIEFS_IMPORT_LIMIT": 5,
    "ACMAD_ATMOSPHERIC_ANALYSIS_AUTO_IMPORT": True,
    "ACMAD_HEAT_STRESS_AUTO_IMPORT": True,
    "ACMAD_HEAT_STRESS_IMPORT_LIMIT": 3,
    "ACMAD_ITD_ITCZ_AUTO_IMPORT": True,
    "ACMAD_ITD_ITCZ_IMPORT_LIMIT": 3,
    "ACMAD_NOWCASTING_AUTO_IMPORT": True,
    "ACMAD_NOWCASTING_IMPORT_LIMIT": 3,
    "ACMAD_CLIMATE_HEALTH_AUTO_IMPORT": True,
    "ACMAD_CLIMATE_HEALTH_IMPORT_LIMIT": 5,
    "ACMAD_SEASONAL_FORECAST_AUTO_IMPORT": True,
    "ACMAD_SEASONAL_FORECAST_IMPORT_LIMIT": 5,
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
    def test_enabled_bootstrap_runs_all_nineteen_importers(self, importer):
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
                    "import_acmad_monthly_climate",
                    continue_on_error=True,
                    limit=2,
                ),
                call(
                    "import_acmad_season_onset",
                    continue_on_error=True,
                    limit=3,
                ),
                call(
                    "import_acmad_climate_change",
                    continue_on_error=True,
                    limit=5,
                ),
                call(
                    "import_acmad_annual_climate",
                    continue_on_error=True,
                    limit=5,
                ),
                call(
                    "import_acmad_climate_watch",
                    continue_on_error=True,
                    limit=5,
                ),
                call(
                    "import_acmad_rainfall_exceedance",
                    continue_on_error=True,
                    limit=3,
                ),
                call(
                    "import_acmad_five_day_rainfall",
                    continue_on_error=True,
                    limit=3,
                ),
                call(
                    "import_acmad_seasonal_verification",
                    continue_on_error=True,
                    limit=3,
                ),
                call("import_acmad_cryosphere", continue_on_error=True, limit=5),
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
                call(
                    "import_acmad_itd_itcz",
                    continue_on_error=True,
                    limit=3,
                ),
                call(
                    "import_acmad_thunderstorm_nowcasting",
                    continue_on_error=True,
                    limit=3,
                ),
                call(
                    "import_acmad_climate_health",
                    continue_on_error=True,
                    limit=5,
                ),
                call(
                    "import_acmad_seasonal_forecasts",
                    continue_on_error=True,
                    limit=5,
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
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ]

        with self.assertRaises(CommandError):
            call_command("bootstrap_acmad_products")

        self.assertEqual(importer.call_count, 19)
