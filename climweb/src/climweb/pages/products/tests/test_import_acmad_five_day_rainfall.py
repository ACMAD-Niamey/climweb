from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.forms import ProductImportSourceConfigForm
from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY
from climweb.pages.products.management.commands.import_acmad_five_day_rainfall import (
    Command,
    parse_archive_catalog,
    parse_issue_catalog,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_five_day_rainfall_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestFiveDayRainfallSources(SimpleTestCase):
    def test_archive_and_issue_catalog_parsers(self):
        archive_xml = b"""<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
          xmlns:xlink="http://www.w3.org/1999/xlink">
          <catalogRef xlink:title="Current" xlink:href="Current/catalog.xml" />
          <catalogRef xlink:title="20220113" xlink:href="20220113/catalog.xml" />
        </catalog>"""
        catalogs = parse_archive_catalog(
            archive_xml, "https://example.com/5_Days/catalog.xml"
        )
        self.assertEqual(catalogs[0]["date"], date(2022, 1, 13))
        self.assertNotIn("Current", catalogs[0]["catalog_url"])

        issue_xml = b"""<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="20220113">
            <dataset name="Probability_25mm_5_Days1.jpeg" urlPath="ACMAD/20220113/Probability_25mm_5_Days1.jpeg" />
            <dataset name="Probability_150mm_5_Days2.jpeg" urlPath="ACMAD/20220113/Probability_150mm_5_Days2.jpeg" />
            <dataset name="unrelated.png" urlPath="ACMAD/20220113/unrelated.png" />
          </dataset>
        </catalog>"""
        assets = parse_issue_catalog(
            issue_xml, catalogs[0]["catalog_url"], catalogs[0]["date"]
        )
        self.assertEqual(
            [(asset["threshold"], asset["forecast_day"]) for asset in assets],
            [(25, 1), (150, 2)],
        )
        self.assertEqual(assets[0]["valid_until"], date(2022, 1, 18))
        self.assertIn("/thredds/fileServer/", assets[0]["provenance_url"])

    def test_default_dashboard_source_schema_is_valid(self):
        defaults = PRODUCT_IMPORTS_BY_KEY["five-day-rainfall"]["source_defaults"]
        form = ProductImportSourceConfigForm(
            data={
                **defaults,
                "allowed_extensions": ", ".join(defaults["allowed_extensions"]),
                "request_headers": "{}",
            }
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())


class TestAutomaticFiveDayRainfallImport(TestCase):
    @override_settings(
        ACMAD_FIVE_DAY_RAINFALL_AUTO_IMPORT=True,
        ACMAD_FIVE_DAY_RAINFALL_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_five_day_rainfall_import.run()
        call_command.assert_called_once_with(
            "import_acmad_five_day_rainfall",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_FIVE_DAY_RAINFALL_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_five_day_rainfall_import.run()
        call_command.assert_not_called()


class TestFiveDayRainfallHierarchy(TestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        ProductIndexPageFactory(parent=home_page)

    def test_destination_uses_existing_rcc_service(self):
        rcc_service = ServiceCategory.objects.create(
            name="Regional Climate Center", icon="cloud-sun-rain"
        )
        product_page, item_types = Command._get_or_create_destination()
        product_page.refresh_from_db()
        self.assertEqual(product_page.service, rcc_service)
        self.assertEqual(product_page.title, "5-Day Rainfall Probability Forecast")
        self.assertEqual(len(item_types), 10)
        self.assertEqual(ProductPage.objects.filter(service=rcc_service).live().count(), 1)
