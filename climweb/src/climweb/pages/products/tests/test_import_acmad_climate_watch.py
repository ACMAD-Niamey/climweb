from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.forms import ProductImportSourceConfigForm
from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY
from climweb.pages.products.management.commands.import_acmad_climate_watch import (
    Command,
    parse_catalog,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_climate_watch_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestClimateWatchSources(SimpleTestCase):
    def test_catalog_parser_extracts_2022_and_2023_filename_variants(self):
        xml = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="Drought">
            <dataset name="Drought_and_Seasonal_Climate_Forecast_Bulletin_No.9_2022.pdf"
              urlPath="ACMAD/CDD/Drought/Bulletin_No.9_2022.pdf" />
            <dataset
              name="Drought_and_Seasonal_Climate_Forecast_Bulletin_8_August_2023.pdf"
              urlPath="ACMAD/CDD/Drought/Bulletin_8_August_2023.pdf" />
            <dataset name="notes.txt" urlPath="ACMAD/CDD/Drought/notes.txt" />
          </dataset>
        </catalog>"""

        assets = parse_catalog(
            xml,
            "https://sgbd.acmad.org/thredds/catalog/ACMAD/CDD/Drought/catalog.xml",
        )

        self.assertEqual(
            [asset["date"] for asset in assets],
            [date(2022, 9, 1), date(2023, 8, 1)],
        )
        self.assertTrue(assets[0]["source_url"].endswith("Bulletin_No.9_2022.pdf"))
        self.assertIn("/thredds/fileServer/", assets[0]["provenance_url"])

    def test_default_dashboard_source_schema_is_valid(self):
        defaults = PRODUCT_IMPORTS_BY_KEY["climate-watch"]["source_defaults"]
        form = ProductImportSourceConfigForm(
            data={
                **defaults,
                "allowed_extensions": ", ".join(defaults["allowed_extensions"]),
                "request_headers": "{}",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())


class TestAutomaticClimateWatchImport(TestCase):
    @override_settings(
        ACMAD_CLIMATE_WATCH_AUTO_IMPORT=True,
        ACMAD_CLIMATE_WATCH_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_climate_watch_import.run()

        call_command.assert_called_once_with(
            "import_acmad_climate_watch",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_CLIMATE_WATCH_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_climate_watch_import.run()

        call_command.assert_not_called()


class TestClimateWatchHierarchy(TestCase):
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
        self.assertEqual(product_page.title, "Climate Watch Bulletin")
        self.assertEqual(len(item_types), 2)
        self.assertEqual(
            ProductPage.objects.filter(service=rcc_service).live().count(), 1
        )
