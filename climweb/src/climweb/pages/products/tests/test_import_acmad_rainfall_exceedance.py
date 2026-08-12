from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.forms import ProductImportSourceConfigForm
from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY
from climweb.pages.products.management.commands.import_acmad_rainfall_exceedance import (
    Command,
    header_date,
    parse_catalog,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_rainfall_exceedance_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestRainfallExceedanceSources(SimpleTestCase):
    def test_catalog_parser_selects_only_supported_threshold_maps(self):
        xml = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="Probability">
            <dataset name="Excedence100mm.jpeg"
              urlPath="ACMAD/CDD/Probability/Excedence100mm.jpeg" />
            <dataset name="Excedence1000mm.jpeg"
              urlPath="ACMAD/CDD/Probability/Excedence1000mm.jpeg" />
            <dataset name="Probability_75mm_5_Days1.jpeg"
              urlPath="ACMAD/CDD/Probability/Probability_75mm_5_Days1.jpeg" />
          </dataset>
        </catalog>"""

        assets = parse_catalog(
            xml,
            "https://sgbd.acmad.org/thredds/catalog/ACMAD/CDD/Probability/catalog.xml",
        )

        self.assertEqual(
            [asset["threshold"] for asset in assets],
            [100, 1000],
        )
        self.assertIn("/thredds/fileServer/", assets[0]["provenance_url"])

    def test_last_modified_header_supplies_issue_date(self):
        self.assertEqual(
            header_date({"Last-Modified": "Wed, 05 Jan 2022 16:47:30 GMT"}),
            date(2022, 1, 5),
        )
        self.assertIsNone(header_date({}))

    def test_default_dashboard_source_schema_is_valid(self):
        defaults = PRODUCT_IMPORTS_BY_KEY["rainfall-exceedance"]["source_defaults"]
        form = ProductImportSourceConfigForm(
            data={
                **defaults,
                "allowed_extensions": ", ".join(defaults["allowed_extensions"]),
                "request_headers": "{}",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())


class TestAutomaticRainfallExceedanceImport(TestCase):
    @override_settings(
        ACMAD_RAINFALL_EXCEEDANCE_AUTO_IMPORT=True,
        ACMAD_RAINFALL_EXCEEDANCE_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_rainfall_exceedance_import.run()

        call_command.assert_called_once_with(
            "import_acmad_rainfall_exceedance",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_RAINFALL_EXCEEDANCE_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_rainfall_exceedance_import.run()

        call_command.assert_not_called()


class TestRainfallExceedanceHierarchy(TestCase):
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
        self.assertEqual(
            product_page.title,
            "Seasonal Rainfall Probability of Exceedance",
        )
        self.assertEqual(len(item_types), 10)
        self.assertEqual(
            ProductPage.objects.filter(service=rcc_service).live().count(), 1
        )
