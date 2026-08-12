from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.forms import ProductImportSourceConfigForm
from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY
from climweb.pages.products.management.commands import (
    import_acmad_seasonal_verification as verification,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_seasonal_verification_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestSeasonalVerificationSources(SimpleTestCase):
    def test_asset_builder_classifies_type_season_and_archive(self):
        temperature = verification.build_asset(
            "https://rcc.acmad.org/cartelongerange/cartelongrange.php",
            2014,
            "hg",
            6,
            archived=True,
        )
        self.assertEqual(temperature["date"], date(2014, 6, 1))
        self.assertEqual(temperature["category"], "Temperature Verification")
        self.assertIn("May–June–July", temperature["name"])
        self.assertIn("/2014/hs_hg6.jpg", temperature["source_url"])

    def test_candidates_include_maps_and_evaluation_report(self):
        assets = verification.candidate_assets()
        current_maps = [
            asset
            for asset in assets
            if asset["date"].year == 2016 and asset["kind"] == "image"
        ]
        reports = [asset for asset in assets if asset["kind"] == "document"]
        self.assertEqual(len(assets), 45)
        self.assertEqual(len(current_maps), 24)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["date"], date(2016, 12, 1))

    def test_default_dashboard_source_schema_is_valid(self):
        defaults = PRODUCT_IMPORTS_BY_KEY["seasonal-verification"]["source_defaults"]
        form = ProductImportSourceConfigForm(
            data={
                **defaults,
                "allowed_extensions": ", ".join(defaults["allowed_extensions"]),
                "request_headers": "{}",
            }
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())


class TestAutomaticSeasonalVerificationImport(TestCase):
    @override_settings(
        ACMAD_SEASONAL_VERIFICATION_AUTO_IMPORT=True,
        ACMAD_SEASONAL_VERIFICATION_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_seasonal_verification_import.run()
        call_command.assert_called_once_with(
            "import_acmad_seasonal_verification",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_SEASONAL_VERIFICATION_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_seasonal_verification_import.run()
        call_command.assert_not_called()


class TestSeasonalVerificationHierarchy(TestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        ProductIndexPageFactory(parent=home_page)

    def test_destination_uses_rcc_service_and_three_categories(self):
        rcc_service = ServiceCategory.objects.create(
            name="Regional Climate Center", icon="cloud-sun-rain"
        )
        assets = [
            verification.build_asset(
                "https://example.com/index.php", 2016, "hg", 1
            ),
            verification.build_asset(
                "https://example.com/index.php", 2016, "md", 1
            ),
            verification.candidate_assets()[-1],
        ]
        destinations = verification.Command._get_or_create_destinations(assets)
        page = ProductPage.objects.get(slug="seasonal-forecast-verification")
        self.assertEqual(page.service, rcc_service)
        self.assertEqual(len(destinations), 3)
        self.assertEqual(page.product.categories.count(), 3)
