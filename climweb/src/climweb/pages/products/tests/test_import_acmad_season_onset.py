import re
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from climweb.base.models import ServiceCategory
from climweb.pages.home.tests.factories import get_or_create_homepage
from climweb.pages.products.forms import ProductImportSourceConfigForm
from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY
from climweb.pages.products.management.commands.import_acmad_season_onset import (
    Command,
    parse_catalog,
)
from climweb.pages.products.models import ProductPage
from climweb.pages.products.tasks import run_acmad_season_onset_import
from climweb.pages.products.tests.factories import ProductIndexPageFactory


class TestSeasonOnsetSources(SimpleTestCase):
    def test_catalog_parser_classifies_observed_and_forecast_maps(self):
        xml = b"""<?xml version="1.0"?>
        <catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
          <dataset name="Onset">
            <dataset name="ecowas_Seasonal_Onset_Obs_20260806.jpeg"
              urlPath="ACMAD/CDD/onset/ecowas_Seasonal_Onset_Obs_20260806.jpeg" />
            <dataset name="ecowas_Seasonal_Onset_Fcst_20260806.jpeg"
              urlPath="ACMAD/CDD/onset/ecowas_Seasonal_Onset_Fcst_20260806.jpeg" />
            <dataset name="season_onset_monitoring.html"
              urlPath="ACMAD/CDD/onset/season_onset_monitoring.html" />
          </dataset>
        </catalog>"""

        assets = parse_catalog(xml)

        self.assertEqual(len(assets), 2)
        self.assertEqual(
            {asset["key"] for asset in assets},
            {"observed-onset", "forecast-onset"},
        )
        self.assertTrue(
            all(asset["date"] == date(2026, 8, 6) for asset in assets)
        )
        self.assertTrue(
            all(asset["valid_until"] == date(2026, 8, 10) for asset in assets)
        )

    def test_default_dashboard_source_schema_is_valid(self):
        defaults = PRODUCT_IMPORTS_BY_KEY["season-onset"]["source_defaults"]
        form = ProductImportSourceConfigForm(
            data={
                **defaults,
                "allowed_extensions": ", ".join(defaults["allowed_extensions"]),
                "request_headers": "{}",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        match = re.search(
            defaults["filename_pattern"],
            "ecowas_Seasonal_Onset_Obs_20260806.jpeg",
        )
        self.assertEqual(match.group("date"), "20260806")


class TestAutomaticSeasonOnsetImport(TestCase):
    @override_settings(
        ACMAD_SEASON_ONSET_AUTO_IMPORT=True,
        ACMAD_SEASON_ONSET_IMPORT_LIMIT=4,
    )
    @patch("climweb.pages.products.tasks.call_command")
    def test_enabled_task_runs_import(self, call_command):
        run_acmad_season_onset_import.run()

        call_command.assert_called_once_with(
            "import_acmad_season_onset",
            limit=4,
            continue_on_error=True,
        )

    @override_settings(ACMAD_SEASON_ONSET_AUTO_IMPORT=False)
    @patch("climweb.pages.products.tasks.call_command")
    def test_disabled_task_skips_import(self, call_command):
        run_acmad_season_onset_import.run()

        call_command.assert_not_called()


class TestSeasonOnsetHierarchy(TestCase):
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
        self.assertEqual(product_page.title, "Rainfall and Seasonal Onset Monitoring")
        self.assertEqual(len(item_types), 2)
        self.assertEqual(
            ProductPage.objects.filter(service=rcc_service).live().count(), 1
        )
